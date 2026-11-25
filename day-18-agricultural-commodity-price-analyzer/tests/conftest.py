"""Pytest bootstrap for Day 18: make `src` importable from any cwd.

The orchestrator's `validate` re-runs pytest from the repo root, so the
day folder is not on sys.path there and `from src import ...` fails at
collection. Insert the day folder here, the way Day 15's test_pipeline.py
does inline, so the tests pass from any working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
