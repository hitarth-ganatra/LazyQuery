from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.models import ChartSpec


NUMERIC_TYPES = (int, float)
TEMPORAL_TYPES = (date, datetime)


def _column_profile(rows: list[dict[str, Any]], column: str) -> str:
    values = [row.get(column) for row in rows if row.get(column) is not None]
    if not values:
        return "unknown"
    sample = values[0]
    if isinstance(sample, NUMERIC_TYPES):
        return "numeric"
    if isinstance(sample, TEMPORAL_TYPES):
        return "temporal"
    return "categorical"


def recommend_chart(rows: list[dict[str, Any]], columns: list[str]) -> ChartSpec:
    if not rows or not columns:
        return ChartSpec(chart_type="table", title="Table result")

    profiles = {col: _column_profile(rows, col) for col in columns}
    numeric_cols = [c for c, t in profiles.items() if t == "numeric"]
    temporal_cols = [c for c, t in profiles.items() if t == "temporal"]
    categorical_cols = [c for c, t in profiles.items() if t == "categorical"]

    if len(numeric_cols) == 1 and len(categorical_cols) >= 1:
        return ChartSpec(
            chart_type="bar",
            x_key=categorical_cols[0],
            y_keys=[numeric_cols[0]],
            title=f"{numeric_cols[0]} by {categorical_cols[0]}",
        )

    if len(numeric_cols) >= 1 and len(temporal_cols) >= 1:
        return ChartSpec(
            chart_type="line",
            x_key=temporal_cols[0],
            y_keys=[numeric_cols[0]],
            title=f"{numeric_cols[0]} over time",
        )

    if len(numeric_cols) >= 2:
        return ChartSpec(
            chart_type="scatter",
            x_key=numeric_cols[0],
            y_keys=[numeric_cols[1]],
            title=f"{numeric_cols[1]} vs {numeric_cols[0]}",
        )

    if len(numeric_cols) == 1:
        return ChartSpec(chart_type="metric", y_keys=[numeric_cols[0]], title=f"Key metric: {numeric_cols[0]}")

    return ChartSpec(chart_type="table", title="Table result")
