from __future__ import annotations

import re

import sqlglot
from sqlglot import exp


DISALLOWED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "execute",
    "call",
    "copy",
}


class SqlSafetyError(ValueError):
    pass


class SqlSafetyValidator:
    def __init__(self, max_rows: int) -> None:
        self.max_rows = max_rows

    def validate_and_rewrite(self, sql: str, limit: int, offset: int) -> tuple[str, list[str]]:
        normalized = sql.strip().rstrip(";")
        if not normalized:
            raise SqlSafetyError("Generated SQL is empty")

        if ";" in normalized:
            raise SqlSafetyError("Multiple statements are not allowed")

        lowered = normalized.lower()
        for keyword in DISALLOWED_KEYWORDS:
            if re.search(rf"\\b{keyword}\\b", lowered):
                raise SqlSafetyError(f"Disallowed SQL keyword detected: {keyword}")

        parsed = sqlglot.parse_one(normalized, read="postgres")
        if not isinstance(parsed, (exp.Select, exp.With, exp.Subquery, exp.Union, exp.Intersect, exp.Except)):
            raise SqlSafetyError("Only read-only SELECT queries are permitted")

        capped_limit = min(limit, self.max_rows)
        warnings: list[str] = []
        if limit > self.max_rows:
            warnings.append(f"Requested limit exceeded max_rows_per_query; capped to {self.max_rows}")

        wrapped_sql = f"SELECT * FROM ({normalized}) AS safe_query LIMIT {capped_limit} OFFSET {offset}"
        return wrapped_sql, warnings
