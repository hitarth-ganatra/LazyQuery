from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=3, description="Natural language query")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ChartSpec(BaseModel):
    chart_type: str
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    title: str


class QueryResponse(BaseModel):
    intent: str
    sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    chart: ChartSpec
    warnings: list[str] = Field(default_factory=list)
