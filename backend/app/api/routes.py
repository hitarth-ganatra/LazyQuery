from __future__ import annotations

import asyncio

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import QueryRequest, QueryResponse, TableInfo, TableRowsResponse, TablesResponse
from app.services.analytics import recommend_chart
from app.services.db import DatabaseService
from app.services.nl2sql import NlToSqlService
from app.services.sql_safety import SqlSafetyError, SqlSafetyValidator

router = APIRouter()


def get_db_service() -> DatabaseService:
    from app.main import db_service

    return db_service


def get_nl2sql_service() -> NlToSqlService:
    from app.main import nl2sql_service

    return nl2sql_service


def get_sql_validator() -> SqlSafetyValidator:
    from app.main import sql_validator

    return sql_validator


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tables", response_model=TablesResponse)
async def list_tables(db: DatabaseService = Depends(get_db_service)) -> TablesResponse:
    schema = await db.fetch_schema()
    tables = [TableInfo(name=table_name, columns=[col.column_name for col in columns]) for table_name, columns in schema.items()]
    return TablesResponse(tables=tables)


@router.get("/tables/{table_name}/rows", response_model=TableRowsResponse)
async def get_table_rows(
    table_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    filter_column: str | None = Query(default=None),
    filter_value: str | None = Query(default=None),
    db: DatabaseService = Depends(get_db_service),
) -> TableRowsResponse:
    if bool(filter_column) != bool(filter_value):
        raise HTTPException(status_code=400, detail="Both filter_column and filter_value are required together")

    try:
        columns, rows, total_rows = await db.fetch_table_rows(
            table_name,
            limit=limit,
            offset=offset,
            filter_column=filter_column,
            filter_value=filter_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Table query timed out") from exc
    except asyncpg.PostgresError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

    return TableRowsResponse(
        table=table_name,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        total_rows=total_rows,
    )


@router.post("/query", response_model=QueryResponse)
async def query_data(
    request: QueryRequest,
    db: DatabaseService = Depends(get_db_service),
    nl2sql: NlToSqlService = Depends(get_nl2sql_service),
    validator: SqlSafetyValidator = Depends(get_sql_validator),
) -> QueryResponse:
    schema = await db.fetch_schema()
    if not schema:
        raise HTTPException(status_code=400, detail="No tables found in public schema")

    sql, intent, warnings = await nl2sql.generate_sql(request.prompt, schema, request.limit)

    try:
        safe_sql, guardrail_warnings = validator.validate_and_rewrite(sql, request.limit, request.offset)
        warnings.extend(guardrail_warnings)
    except SqlSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        columns, rows = await db.execute_readonly(safe_sql)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Query execution timed out") from exc
    except asyncpg.PostgresError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

    chart = recommend_chart(rows, columns)
    return QueryResponse(
        intent=intent,
        sql=safe_sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        warnings=warnings,
    )
