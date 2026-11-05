"""Orchestrator for the 60-Day Data Analytics + AI Portfolio.

A small, documented CLI (standard library only — no LLM calls, no network).
It does three things for one day's project:

1. ``checklist``  — print the standard 6-stage handoff checklist
   (researcher -> planner -> coder -> tester -> optimizer ->
   publisher/reviewer) for a day, with each role's inputs, outputs and
   sign-off gates.
2. ``scaffold``   — create the day-NN folder from the Day 1 template file
   tree, with placeholders where the new day's content goes.
3. ``validate``   — check a day folder against the roadmap success criteria
   (README, data provenance, 2+ charts, tests, no secrets, pinned deps,
   .gitignore rule) and report PASS/FAIL per criterion.

Usage (from the portfolio root)::

    python agents/orchestrator.py --day 2 checklist
    python agents/orchestrator.py --day 2 --slug "crypto-risk-volatility" scaffold
    python agents/orchestrator.py --day 1 validate
    python agents/orchestrator.py --day 2 validate   # after the day is built

See AGENTS.md at the portfolio root for the workflow this implements.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PORTFOLIO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DAY = PORTFOLIO_ROOT / "day-01-crypto-market-intelligence"

# Files copied verbatim from the Day 1 template when scaffolding.
TEMPLATE_COPY = ["LICENSE", ".gitignore", "requirements.txt", "pyproject.toml"]

# Directories every day folder must have (plan.md §5 file tree).
REQUIRED_DIRS = [
    "data/raw",
    "data/processed",
    "notebooks",
    "src",
    "outputs/charts",
    "screenshots",
    "tests",
]

# Handoff checklist: (role, receives, produces, sign-off gate).
STAGES = [
    (
        "1 · Researcher",
        "Roadmap entry for the day (problem, skills, suggested data)",
        (
            "research_brief.md — verified source, endpoints, rate limits, "
            "metric definitions, fallback parameters"
        ),
        (
            "One lean verification pass only; endpoints/params written down "
            "once and never re-searched. No live fetch."
        ),
    ),
    (
        "2 · Planner",
        "Roadmap entry + research_brief.md",
        (
            "plan.md — problem, audience, questions, exact file tree, "
            "per-file responsibilities, success checklist (§8)"
        ),
        (
            "Plan is the source of truth. If brief and plan disagree, the "
            "plan wins and the difference is noted."
        ),
    ),
    (
        "3 · Coder",
        "research_brief.md + plan.md",
        (
            "Working project: src/, notebooks/analysis.ipynb, outputs/charts/, "
            "tests/, data/ (live or labelled-synthetic), draft README.md, "
            "data/README.md, outputs/insights_summary.md"
        ),
        (
            "Handoff checklist BEFORE the tester starts: venv exists with "
            "pinned deps installed; `black --check` + `ruff check` pass; "
            "`pytest` passes; `.gitignore` matches the plan; "
            "screenshots/dashboard.png is a real capture of the running app "
            "(or explicitly flagged as a composite). No extra web searches."
        ),
    ),
    (
        "4 · Tester",
        (
            "Coder's finished tree (in the coder's venv — never install the "
            "project's own deps from scratch; if the venv is missing, report "
            "'blocked: no venv')"
        ),
        (
            "test_report.md — verified result, not edits: py_compile, pytest, "
            "pipeline run, Streamlit smoke + screenshot, manual validation of "
            "one metric, chart legibility check"
        ),
        (
            "MANDATORY smoke gate: run `streamlit run src/app.py` on a FRESH "
            "port (never 8501 — it may already be in use; use 8502 or higher), "
            "confirm HTTP 200 + /_stcore/health, capture a full-page screenshot "
            "to screenshots/dashboard.png, then kill the server and verify the "
            "port is free. Pytest alone is NOT enough — the Day 1 app.py "
            "idxmin/IndexError was caught by the screenshot, not by tests. "
            "Never edit code to make a test pass — report the defect."
        ),
    ),
    (
        "5 · Optimizer",
        "Tester's verified report + coder's tree",
        (
            "Release-ready tree: pinned requirements.txt, black/ruff clean, "
            ".gitignore per plan, missing docs filled, screenshots/dashboard.png "
            "verified present, root README/docs updated"
        ),
        (
            "Fix only clear gaps; do not refactor working code; do not re-run "
            "a live API fetch when the data is already verified. Re-run pytest "
            "after any change. Verify every published number against the "
            "committed CSVs; if a doc already exists and its numbers check out, "
            "fix only concrete gaps instead of rewriting it."
        ),
    ),
    (
        "6 · Publisher / reviewer",
        "Optimizer's release-ready tree",
        (
            "GitHub repo (vinodvicki/60-day-data-ai-portfolio): pushed day "
            "folder, live links checked"
        ),
        (
            "FROZEN-TREE CHECK immediately before pushing: re-verify every "
            "file the READMEs reference exists on disk (charts, screenshots, "
            "CSVs) — a missing asset blocks the push. Then verify the live "
            "GitHub page renders (README, charts, links). Final gate: roadmap "
            "success criteria (plan.md §8). Only this role touches GitHub."
        ),
    ),
]


def day_dir(day: int, root: Path = PORTFOLIO_ROOT) -> Path | None:
    """Return the existing day-NN* folder, or None if there isn't one."""
    prefix = f"day-{day:02d}"
    matches = sorted(p for p in root.glob(f"{prefix}*") if p.is_dir())
    return matches[0] if matches else None


def new_day_dir(day: int, slug: str, root: Path = PORTFOLIO_ROOT) -> Path:
    """Folder name for a new day: day-NN-<slug>."""
    return root / f"day-{day:02d}-{slug}"


def print_checklist(day: int) -> None:
    """Print the 6-stage handoff checklist for a day."""
    print(f"Day {day:02d} — 6-stage handoff checklist")
    print(
        "Order is fixed: researcher -> planner -> coder -> tester -> "
        "optimizer -> publisher/reviewer."
    )
    print(
        "One writer per file; a later role never re-does an earlier "
        "role's work — it checks it and either passes it on or sends it "
        "back with a specific defect.\n"
    )
    for role, receives, produces, gate in STAGES:
        print(f"{role}")
        print(f"  Receives: {receives}")
        print(f"  Produces: {produces}")
        print(f"  Sign-off gate: {gate}\n")


# --- Scaffold -----------------------------------------------------------------

_PLACEHOLDER_RESEARCH = """# Day {day:02d} — {title}: Research Brief

**Status:** PLACEHOLDER — researcher to fill in (see AGENTS.md, stage 1).
**Business question:** <!-- one question, from the roadmap entry -->

## 1. API / data source — to verify (one lean pass)

- Source, base URL, endpoint(s), parameters, date range, granularity.
- Rate limits and the polite-use rule (spacing, retry, stop condition).
- Response fields and units.

## 2. Metrics to compute

<!-- definitions, with formulas, per the roadmap entry -->

## 3. Licence / attribution

## 4. Synthetic-fallback note (if the source is unreachable)

## 5. Verification status

- [ ] Endpoints confirmed against the official docs (date + source noted)
- [ ] Any unverified conflict recorded, with the test order to resolve it
"""

_PLACEHOLDER_PLAN = """# Day {day:02d} — {title}: Build Plan

**Status:** PLACEHOLDER — planner to fill in (see AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` — the coder must reuse the brief +
this plan. **No extra web searches.**

## 1. Problem

<!-- decision-maker, problem, 2–3 questions the dashboard/analysis answers -->

## 2. Audience / decision-maker

## 3. Data

<!-- source, endpoint, window, fetch rules, fallback, attribution -->

## 4. File tree (exact — copy the Day 1 template)

```
day-{day:02d}-{slug}/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md
├── data/
│   ├── README.md
│   ├── raw/
│   └── processed/
├── notebooks/analysis.ipynb
├── src/
├── outputs/
│   ├── insights_summary.md
│   └── charts/
├── screenshots/
└── tests/
```

## 5. Per-file responsibilities

## 6. Charts (minimum 2 labelled charts)

## 7. Success criteria checklist (from the roadmap — all must pass)

- [ ] Problem statement + audience written (README)
- [ ] Data provenance documented (data/README.md)
- [ ] 2+ labelled charts produced
- [ ] 3 findings + 1 actionable recommendation (outputs/insights_summary.md)
- [ ] README with setup instructions, sample outputs, limitations
- [ ] No credentials in the repo; no huge files committed
- [ ] One metric manually validated and recorded
- [ ] Pipeline runs end-to-end from a clean checkout
- [ ] Notebook runs top-to-bottom without errors

## 8. Risks & mitigations

## 9. Build order
"""

_PLACEHOLDER_README = """# Day {day:02d} — {title}

> **60-Day Data Analytics + AI Portfolio, Day {day:02d}.**
> PLACEHOLDER — coder to fill in (see AGENTS.md, stage 3).

## Problem

<!-- one paragraph + business question -->

## Dataset

<!-- source, endpoint, date accessed, window, row counts, licence note -->

## Tools

<!-- Python version + libraries; see requirements.txt -->

## Method

## Key insights

## Visuals

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q
```

## Limitations

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Victor.
"""

_PLACEHOLDER_DATA_README = """# Data provenance — Day {day:02d} {title}

**Status:** PLACEHOLDER — fill in during the build (see AGENTS.md).

## Source

- Provider, endpoint used, window, access date, keyless vs key, row counts.
- Licence / attribution note.

## Fetch outcome

## Row counts and coverage

## Commit rule for data files

- Small raw data IS committed: files under 1 MB each (under 5 MB per day
  folder) are part of the deliverable — `.gitignore` must NOT exclude
  `data/`. Anything larger must be `.gitignore`d and regenerated by the
  pipeline; record how to re-fetch it here.

## Manual validation (one metric, by hand)

## Versions used for this build
"""

_PLACEHOLDER_INSIGHTS = """# Day {day:02d} — {title}: Insights

**Status:** PLACEHOLDER — coder to fill in (see AGENTS.md, stage 3).

## Finding 1

<!-- tied to a question in plan.md and a chart, with metric values -->

## Finding 2

## Finding 3

## Recommendation (analytical next step — never investment advice)

## Limitations
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def scaffold(day: int, slug: str, root: Path = PORTFOLIO_ROOT) -> Path:
    """Create the day-NN-<slug> folder from the Day 1 template tree."""
    target = new_day_dir(day, slug, root)
    if target.exists():
        print(f"ERROR: {target} already exists — refusing to overwrite.")
        raise SystemExit(1)
    title = slug.replace("-", " ").title()
    ctx = {"day": day, "slug": slug, "title": title}

    for name in TEMPLATE_COPY:
        src = TEMPLATE_DAY / name
        if src.exists():
            _write(target / name, src.read_text())
        else:  # Template missing (e.g. scaffold tested outside the portfolio).
            _write(target / name, f"# Placeholder {name} for Day {day:02d}\n")

    _write(target / "research_brief.md", _PLACEHOLDER_RESEARCH.format(**ctx))
    _write(target / "plan.md", _PLACEHOLDER_PLAN.format(**ctx))
    _write(target / "README.md", _PLACEHOLDER_README.format(**ctx))
    _write(target / "data" / "README.md", _PLACEHOLDER_DATA_README.format(**ctx))
    _write(
        target / "outputs" / "insights_summary.md",
        _PLACEHOLDER_INSIGHTS.format(**ctx),
    )

    # Minimal valid notebook placeholder (one markdown cell).
    _write(
        target / "notebooks" / "analysis.ipynb",
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [
                            f"# Day {day:02d} — {title}: analysis\n",
                            "\n",
                            (
                                "PLACEHOLDER — coder to fill in. Must run "
                                "top-to-bottom without errors. Resolve the "
                                "project root from the file's own location "
                                "(`Path(__file__)` / notebook dir), never from "
                                "the working directory — see AGENTS.md, "
                                "Day 1 lesson (e)."
                            ),
                        ],
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    },
                    "language_info": {"name": "python", "version": "3.12.0"},
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            },
            indent=1,
        )
        + "\n",
    )

    # Scaffold smoke test: asserts the day folder has the required docs.
    # The coder replaces it with real tests (plan.md §8).
    _write(
        target / "tests" / "test_smoke.py",
        '"""Scaffold smoke test — replaced by the coder with real tests."""\n'
        "\n"
        "from pathlib import Path\n"
        "\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "\n"
        "\n"
        "def test_readme_exists():\n"
        '    assert (ROOT / "README.md").read_text().strip() != ""\n'
        "\n"
        "\n"
        "def test_data_readme_exists():\n"
        '    assert (ROOT / "data" / "README.md").exists()\n',
    )

    for d in REQUIRED_DIRS:
        (target / d).mkdir(parents=True, exist_ok=True)
    print(f"Created {target}")
    print("Next: researcher fills in research_brief.md (AGENTS.md stage 1).")
    return target


# --- Validate -----------------------------------------------------------------

SECRET_RE = re.compile(
    r"(api[_-]?key|password|passwd|secret|bearer)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    r"|(sk-(?:live|test)-[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{24,}|AKIA[0-9A-Z]{16})",
    re.IGNORECASE,
)
# Lines that are allowed to mention credentials (env-var reads, docs).
SECRET_ALLOW = re.compile(
    r"os\.environ|getenv|COINGECKO_DEMO_API_KEY|never|"
    r"no .* key|do not|must not|placeholder",
    re.IGNORECASE,
)


def _check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def validate(day: int, root: Path = PORTFOLIO_ROOT) -> bool:
    """Validate a day folder against the roadmap success criteria."""
    folder = day_dir(day, root)
    print(
        f"Day {day:02d} — validation"
        + (f" ({folder.name})" if folder else " (folder not found)")
    )
    if folder is None:
        print("  [FAIL] Day folder does not exist — run scaffold first.")
        return False

    results = []

    readme = folder / "README.md"
    results.append(
        _check(
            "README.md exists and is filled in (not a placeholder)",
            readme.exists()
            and len(readme.read_text(errors="ignore")) > 500
            and "PLACEHOLDER" not in readme.read_text(errors="ignore"),
            f"{readme.stat().st_size} bytes" if readme.exists() else "missing",
        )
    )

    data_readme = folder / "data" / "README.md"
    results.append(
        _check(
            "data/README.md provenance exists",
            data_readme.exists() and len(data_readme.read_text(errors="ignore")) > 200,
            "missing" if not data_readme.exists() else "",
        )
    )

    charts = (
        sorted((folder / "outputs" / "charts").glob("*.png"))
        if (folder / "outputs" / "charts").exists()
        else []
    )
    results.append(
        _check(
            "2+ labelled charts in outputs/charts/",
            len(charts) >= 2,
            f"{len(charts)} chart(s) found",
        )
    )

    insights = folder / "outputs" / "insights_summary.md"
    insights_ok = insights.exists() and "PLACEHOLDER" not in insights.read_text(
        errors="ignore"
    )
    results.append(
        _check(
            "outputs/insights_summary.md filled in (3 findings + 1 recommendation)",
            insights_ok,
            "missing/placeholder" if not insights_ok else "",
        )
    )

    tests = (
        sorted((folder / "tests").glob("test_*.py"))
        if (folder / "tests").exists()
        else []
    )
    results.append(
        _check(
            "tests/ has at least one test file",
            len(tests) >= 1,
            f"{len(tests)} test file(s)",
        )
    )

    req = folder / "requirements.txt"
    pinned = False
    if req.exists():
        lines = [
            ln.strip()
            for ln in req.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        pinned = bool(lines) and all("==" in ln for ln in lines)
    results.append(
        _check(
            "requirements.txt exists with pinned (==) versions",
            pinned,
            "missing/unpinned" if not pinned else "",
        )
    )

    gitignore = folder / ".gitignore"
    gi_ok = False
    if gitignore.exists():
        lines = [ln.strip() for ln in gitignore.read_text().splitlines()]
        gi_ok = not any(
            ln in ("data/", "data", "data/raw/", "data/raw/*.json")
            or ln.startswith("data/")
            for ln in lines
            if ln and not ln.startswith("#")
        )
    results.append(
        _check(
            ".gitignore does NOT exclude data/ (small raw data is committed)",
            gi_ok,
            "missing or excludes data/" if not gi_ok else "",
        )
    )

    # No secrets: scan text files (excluding venvs/caches) for credential
    # assignments or well-known key shapes.
    hits = []
    for path in folder.rglob("*"):
        if (
            not path.is_file()
            or ".venv" in path.parts
            or "__pycache__" in path.parts
            or ".pytest_cache" in path.parts
        ):
            continue
        if path.suffix.lower() not in {
            ".py",
            ".md",
            ".txt",
            ".json",
            ".toml",
            ".yml",
            ".yaml",
            ".ipynb",
        }:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line) and not SECRET_ALLOW.search(line):
                hits.append(f"{path.relative_to(folder)}:{i}")
    results.append(
        _check(
            "No credentials in the repo (no key/token/password values)",
            not hits,
            "; ".join(hits[:5]) if hits else "",
        )
    )

    # Data-size rule: no single data file over 1 MB, no data/ over 5 MB.
    big = []
    data_dir = folder / "data"
    total = 0
    if data_dir.exists():
        for path in data_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
                if path.stat().st_size > 1_000_000:
                    big.append(str(path.relative_to(folder)))
    results.append(
        _check(
            "No huge files committed (data/ < 5 MB total, no file > 1 MB)",
            total <= 5_000_000 and not big,
            f"data/ = {total / 1_000:.0f} KB" + (f"; oversize: {big}" if big else ""),
        )
    )

    shot = folder / "screenshots" / "dashboard.png"
    results.append(
        _check(
            "screenshots/dashboard.png exists (real app capture preferred)",
            shot.exists(),
            "missing" if not shot.exists() else f"{shot.stat().st_size} bytes",
        )
    )

    # Run pytest in the day's venv if one exists, else the current python.
    venv_python = folder / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    if tests:
        proc = subprocess.run(
            [python, "-m", "pytest", str(folder / "tests"), "-q"],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        out = (proc.stdout.strip().splitlines() or [""])[-1]
        err = (proc.stderr.strip().splitlines() or [""])[-1]
        detail = out if proc.returncode == 0 else (err or out)
        if "No module named pytest" in proc.stderr:
            detail = f"pytest not installed under {python} — create the day venv first"
        results.append(
            _check(
                f"pytest passes ({'day venv' if venv_python.exists() else 'system python'})",
                proc.returncode == 0,
                detail,
            )
        )
    else:
        results.append(_check("pytest passes", False, "no tests to run"))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed.")
    return passed == len(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="60-day portfolio orchestrator: checklist, scaffold, validate."
    )
    parser.add_argument("--day", type=int, required=True, help="Day number, e.g. 2")
    parser.add_argument(
        "--slug",
        help="Slug for scaffold, e.g. " "'crypto-risk-volatility' (scaffold only)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PORTFOLIO_ROOT,
        help="Portfolio root (default: parent of agents/)",
    )
    parser.add_argument(
        "command",
        choices=["checklist", "scaffold", "validate"],
        help="What to do for this day",
    )
    args = parser.parse_args(argv)

    if args.command == "checklist":
        print_checklist(args.day)
        return 0
    if args.command == "scaffold":
        if not args.slug:
            print(
                "ERROR: scaffold needs --slug, e.g. --slug " "'crypto-risk-volatility'."
            )
            return 2
        scaffold(args.day, args.slug, args.root)
        return 0
    return 0 if validate(args.day, args.root) else 1


if __name__ == "__main__":
    raise SystemExit(main())
