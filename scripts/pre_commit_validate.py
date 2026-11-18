# NOTE: no shebang on purpose — this file is committed non-executable
# (snapshot pushes cannot set the exec bit) and ruff rule EXE001 flags a
# shebang without the exec bit (broke CI run #100, 2026-11-18). Pre-commit
# invokes it as `python scripts/pre_commit_validate.py`, so no shebang
# is needed. Do not re-add one unless the file is made executable too.
"""Pre-commit local hook: validate every staged day folder.

Finds day folders among the staged files (``git diff --cached
--name-only``) and runs ``agents/orchestrator.py --day N validate``
for each one — the same secret scan, pinned-deps check, data-size rule
and screenshot check that CI enforces. Exits non-zero if any day fails
validation, which blocks the commit.

Standard library only. Run from the portfolio root (pre-commit does
that). If no day folder is staged, exits 0.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY_RE = re.compile(r"^day-(\d+)")


def staged_days() -> list[int]:
    """Day numbers with at least one staged file, sorted."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("pre-commit-validate: could not list staged files; skipping.")
        return []
    days = set()
    for line in proc.stdout.splitlines():
        match = DAY_RE.match(line.strip())
        if match:
            days.add(int(match.group(1)))
    return sorted(days)


def main() -> int:
    days = staged_days()
    if not days:
        print("pre-commit-validate: no day folder staged — nothing to check.")
        return 0
    failed = []
    for day in days:
        print(f"pre-commit-validate: validating day {day:02d} ...")
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "agents" / "orchestrator.py"),
                "--day",
                str(day),
                "validate",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            failed.append(day)
    if failed:
        print(
            "pre-commit-validate: FAILED for day(s) "
            + ", ".join(f"{d:02d}" for d in failed)
            + " — fix the failures above before committing."
        )
        return 1
    print("pre-commit-validate: all staged days passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
