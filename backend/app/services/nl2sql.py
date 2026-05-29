from __future__ import annotations

import json
import logging

from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)


class NlToSqlService:
    def __init__(self, groq_client: GroqClient) -> None:
        self.groq_client = groq_client

    def classify_intent(self, prompt: str) -> str:
        lowered = prompt.lower()
        if any(word in lowered for word in ["trend", "over time", "monthly", "daily"]):
            return "timeseries"
        if any(word in lowered for word in ["compare", "versus", "vs", "top", "rank"]):
            return "comparison"
        if any(word in lowered for word in ["total", "sum", "count", "average", "avg"]):
            return "aggregation"
        return "lookup"

    def _schema_to_text(self, schema: dict) -> str:
        lines = []
        for table, columns in schema.items():
            column_text = ", ".join(f"{col.column_name} ({col.data_type})" for col in columns)
            lines.append(f"- {table}: {column_text}")
        return "\n".join(lines)

    def _fallback_sql(self, schema: dict, limit: int) -> str:
        first_table = next(iter(schema), None)
        if not first_table:
            raise ValueError("No tables found in schema")
        return f"SELECT * FROM {first_table} LIMIT {limit}"

    async def generate_sql(self, prompt: str, schema: dict, limit: int) -> tuple[str, str, list[str]]:
        intent = self.classify_intent(prompt)
        warnings: list[str] = []
        schema_text = self._schema_to_text(schema)

        if not self.groq_client.enabled:
            warnings.append("Groq API key missing; fallback SQL used")
            return self._fallback_sql(schema, limit), intent, warnings

        system_prompt = (
            "You are an NL-to-SQL engine for PostgreSQL. "
            "Return ONLY JSON with keys: sql and confidence. "
            "Generate a single read-only SELECT statement without comments."
        )
        user_prompt = (
            f"Intent: {intent}\n"
            f"Schema:\n{schema_text}\n\n"
            f"Question: {prompt}\n"
            f"Ensure SQL is valid for PostgreSQL and includes a useful LIMIT when appropriate."
        )

        try:
            raw = await self.groq_client.complete(system_prompt, user_prompt)
            payload = json.loads(raw)
            sql = payload.get("sql", "").strip()
            if not sql:
                raise ValueError("LLM returned empty SQL")
            return sql, intent, warnings
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq generation failed, using fallback", exc_info=exc)
            warnings.append("Groq generation failed; fallback SQL used")
            return self._fallback_sql(schema, limit), intent, warnings
