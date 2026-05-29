from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import asyncpg

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TEXT_LIKE_TYPES = {"varchar", "char", "character", "text", "citext", "name", "character varying"}


@dataclass
class TableColumn:
    table_name: str
    column_name: str
    data_type: str


class DatabaseService:
    def __init__(self, database_url: str, timeout_seconds: int) -> None:
        self.database_url = database_url
        self.timeout_seconds = timeout_seconds
        self.pool: asyncpg.Pool | None = None

    async def startup(self) -> None:
        self.pool = await asyncpg.create_pool(dsn=self.database_url, min_size=1, max_size=8)

    async def shutdown(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch_schema(self) -> dict[str, list[TableColumn]]:
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        sql = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql)

        schema: dict[str, list[TableColumn]] = {}
        for row in rows:
            table_name = row["table_name"]
            schema.setdefault(table_name, []).append(
                TableColumn(
                    table_name=table_name,
                    column_name=row["column_name"],
                    data_type=row["data_type"],
                )
            )
        return schema

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        if not IDENTIFIER_RE.fullmatch(identifier):
            raise ValueError("Invalid identifier")
        return f'"{identifier}"'

    async def fetch_table_rows(
        self,
        table_name: str,
        *,
        limit: int,
        offset: int,
        filter_column: str | None,
        filter_value: str | None,
    ) -> tuple[list[str], list[dict], int]:
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        schema = await self.fetch_schema()
        table_columns = schema.get(table_name)
        if table_columns is None:
            raise ValueError(f"Unknown table: {table_name}")

        column_types = {column.column_name: column.data_type for column in table_columns}
        if filter_column and filter_column not in column_types:
            raise ValueError(f"Unknown filter column: {filter_column}")

        quoted_table = self._quote_identifier(table_name)
        where_clause = ""
        params: list[object] = []

        if filter_column and filter_value:
            quoted_column = self._quote_identifier(filter_column)
            filter_type = column_types.get(filter_column, "").lower()
            is_text_like = filter_type in TEXT_LIKE_TYPES
            filter_expression = quoted_column if is_text_like else f"{quoted_column}::text"
            where_clause = f" WHERE {filter_expression} ILIKE $1"
            params.append(f"%{filter_value}%")

        limit_param = len(params) + 1
        offset_param = len(params) + 2

        data_sql = (
            f"SELECT * FROM {quoted_table}{where_clause} LIMIT ${limit_param} OFFSET ${offset_param}"
        )
        count_sql = f"SELECT COUNT(*) FROM {quoted_table}{where_clause}"

        async with self.pool.acquire() as conn:
            rows = await asyncio.wait_for(conn.fetch(data_sql, *params, limit, offset), timeout=self.timeout_seconds)
            total_rows = await asyncio.wait_for(conn.fetchval(count_sql, *params), timeout=self.timeout_seconds)

        if not rows:
            columns = [column.column_name for column in table_columns]
            return columns, [], int(total_rows)

        columns = list(rows[0].keys())
        data = [dict(row) for row in rows]
        return columns, data, int(total_rows)

    async def execute_readonly(self, sql: str) -> tuple[list[str], list[dict]]:
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await asyncio.wait_for(conn.fetch(sql), timeout=self.timeout_seconds)

        if not rows:
            return [], []

        columns = list(rows[0].keys())
        data = [dict(row) for row in rows]
        return columns, data
