from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import sqlglot


@dataclass
class BenchmarkCase:
    prompt: str
    expected_sql: str
    predicted_sql: str


class BenchmarkRunner:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def _normalize(self, sql: str) -> str:
        parsed = sqlglot.parse_one(sql, read="postgres")
        return parsed.sql(dialect="postgres", pretty=False).lower()

    def run(self) -> dict:
        data = json.loads(self.fixture_path.read_text())
        cases = [BenchmarkCase(**item) for item in data["cases"]]

        exact_matches = 0
        results = []
        for case in cases:
            expected = self._normalize(case.expected_sql)
            predicted = self._normalize(case.predicted_sql)
            matched = expected == predicted
            exact_matches += int(matched)
            results.append({"prompt": case.prompt, "matched": matched})

        accuracy = (exact_matches / len(cases)) * 100 if cases else 0.0
        return {
            "total_cases": len(cases),
            "exact_matches": exact_matches,
            "accuracy_percent": round(accuracy, 2),
            "results": results,
        }
