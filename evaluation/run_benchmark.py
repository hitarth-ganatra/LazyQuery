from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.benchmark import BenchmarkRunner


if __name__ == "__main__":
    fixture = Path(__file__).parent / "fixtures" / "cases.json"
    runner = BenchmarkRunner(fixture)
    report = runner.run()
    print(json.dumps(report, indent=2))
