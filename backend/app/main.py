from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.db import DatabaseService
from app.services.groq_client import GroqClient
from app.services.nl2sql import NlToSqlService
from app.services.sql_safety import SqlSafetyValidator

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db_service = DatabaseService(settings.database_url, settings.query_timeout_seconds)
groq_client = GroqClient(
    settings.groq_api_key,
    settings.groq_base_url,
    settings.groq_model,
    settings.groq_timeout_seconds,
)
nl2sql_service = NlToSqlService(groq_client)
sql_validator = SqlSafetyValidator(settings.max_rows_per_query)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request_completed",
        extra={"request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


@app.on_event("startup")
async def startup_event() -> None:
    await db_service.startup()
    logger.info("database_pool_initialized")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await db_service.shutdown()
    logger.info("database_pool_closed")


app.include_router(router, prefix=settings.api_prefix)
