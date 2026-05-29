from __future__ import annotations

import asyncio
from dataclasses import dataclass

import asyncpg


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
