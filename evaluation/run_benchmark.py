from __future__ import annotations

import json
from pathlib import Path

from app.services.benchmark import BenchmarkRunner


if __name__ == "__main__":
    fixture = Path(__file__).parent / "fixtures" / "cases.json"
    runner = BenchmarkRunner(fixture)
    report = runner.run()
    print(json.dumps(report, indent=2))
