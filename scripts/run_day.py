"""Thin wrapper around agents/orchestrator.py for one day's project.

Scaffolds the day folder if it does not exist yet, then runs that day's
pytest suite (in the day's .venv if present, else the current python).

Usage (from the portfolio root)::

    python scripts/run_day.py --day 2                 # validate + test day 2
    python scripts/run_day.py --day 2 --scaffold --slug crypto-risk-volatility

This script does NOT call an LLM and does NOT push to GitHub — it is a
scaffold + test runner. See agents/orchestrator.py and AGENTS.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PORTFOLIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTFOLIO_ROOT / "agents"))

import orchestrator


def run_pytest(day: int) -> int:
    """Run the day's pytest suite; return its exit code."""
    folder = orchestrator.day_dir(day, PORTFOLIO_ROOT)
    if folder is None:
        print(f"Day {day:02d}: no folder yet — run with --scaffold first.")
        return 2
    tests = folder / "tests"
    if not tests.exists() or not list(tests.glob("test_*.py")):
        print(f"Day {day:02d}: no tests in {tests} — nothing to run.")
        return 2
    venv_python = folder / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    print(
        f"Running pytest for {folder.name} "
        f"({'day venv' if venv_python.exists() else 'system python'}) ..."
    )
    proc = subprocess.run([python, "-m", "pytest", str(tests), "-q"], check=False)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold and/or test one day's project."
    )
    parser.add_argument("--day", type=int, required=True, help="Day number, e.g. 2")
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Create the day folder from the Day 1 template",
    )
    parser.add_argument(
        "--slug", help="Slug for --scaffold, e.g. " "'crypto-risk-volatility'"
    )
    parser.add_argument("--no-test", action="store_true", help="Skip the pytest run")
    args = parser.parse_args(argv)

    if args.scaffold:
        if not args.slug:
            print(
                "ERROR: --scaffold needs --slug, e.g. --slug "
                "'crypto-risk-volatility'."
            )
            return 2
        orchestrator.scaffold(args.day, args.slug, PORTFOLIO_ROOT)

    if args.no_test:
        return 0
    return run_pytest(args.day)


if __name__ == "__main__":
    raise SystemExit(main())
