from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ChartSpec(BaseModel):
    chart_type: Literal["table", "metric", "bar", "line", "scatter"]
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    title: str


class QueryResponse(BaseModel):
    intent: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    chart: ChartSpec
    warnings: list[str] = Field(default_factory=list)


class TableInfo(BaseModel):
    name: str
    columns: list[str]


class TablesResponse(BaseModel):
    tables: list[TableInfo]


class TableRowsResponse(BaseModel):
    table: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    total_rows: int


class ColumnMetadata(BaseModel):
    name: str
    type: str


class TableMetadata(BaseModel):
    name: str
    columns: list[ColumnMetadata]


class SchemaMetadata(BaseModel):
    tables: list[TableMetadata]
