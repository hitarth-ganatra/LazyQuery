from __future__ import annotations

import asyncio

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.models import QueryRequest, QueryResponse
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
