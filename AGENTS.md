# AGENTS.md — 60-Day Data Analytics + AI Portfolio

How each day's project is built, by six roles in fixed order. This file is
the short canonical version; full detail lives in
[`docs/multi-agent-workflow.md`](docs/multi-agent-workflow.md) and the
Day 1 retrospective in [`docs/day-01-retrospective.md`](docs/day-01-retrospective.md).

Repo: `vinodvicki/60-day-data-ai-portfolio` (GitHub). Victor's standard:
very professional, industry-standard code quality; every project actually
workable/runnable end-to-end — clean modular code, tests, linting, CI,
pinned dependencies, verified runs before push.

## The six roles

Order is fixed: researcher → planner → coder → tester → optimizer →
publisher/reviewer. A later role never re-does an earlier role's work; it
checks it and either passes it on or sends it back with a specific defect.
No role is added, removed or merged without Victor's say-so. **One writer
per file** — parallel work only across different days or strictly
sequential roles, never two agents writing the same file.

| # | Role | Receives | Produces | Sign-off gate |
|---|---|---|---|---|
| 1 | **Researcher** | Roadmap entry for the day (problem, skills, suggested data) | `research_brief.md` — verified source, endpoints, rate limits, metric definitions, fallback parameters | One lean verification pass; endpoints/params written down once, never re-searched. No live fetch — that is the coder's job. |
| 2 | **Planner** | Roadmap entry + `research_brief.md` | `plan.md` — problem, audience, questions, exact file tree, per-file responsibilities, success checklist (§8) | Plan is the source of truth. If brief and plan disagree, the plan wins and the difference is noted. |
| 3 | **Coder** | `research_brief.md` + `plan.md` | Working project: `src/`, `notebooks/analysis.ipynb`, `outputs/charts/`, `tests/`, `data/` (live or labelled-synthetic), draft `README.md`, `data/README.md`, `outputs/insights_summary.md` | Handoff checklist before the tester starts: venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes; `.gitignore` matches the plan; `screenshots/dashboard.png` is a real capture of the running app (or explicitly flagged as a composite). Build only what the plan lists; no extra web searches. |
| 4 | **Tester** | Coder's finished tree, in the coder's venv | `test_report.md` — verified result, not edits: `py_compile`, `pytest`, pipeline run, Streamlit smoke + screenshot, manual validation of one metric, chart legibility check | **Mandatory smoke gate** (see "Workflow refinement" below): Streamlit on a fresh port, HTTP 200 + health check, real screenshot captured, server killed and port verified free. Never install the project's own deps from scratch — if the venv is missing, report "blocked: no venv". Never edit code to make a test pass — report the defect with exact numbers. |
| 5 | **Optimizer** | Tester's verified report + coder's tree | Release-ready tree: pinned `requirements.txt`, black/ruff clean, `.gitignore` per plan, missing docs filled, `screenshots/dashboard.png` verified present, root README/docs updated | Fix only clear gaps; do not refactor working code; do not re-run a live API fetch when the data is already verified. Re-run `pytest` after any change. Verify every published number against the committed CSVs; if a doc already exists and its numbers check out, fix only concrete gaps instead of rewriting it. |
| 6 | **Publisher / reviewer** | Optimizer's release-ready tree | Pushed day folder in `vinodvicki/60-day-data-ai-portfolio`, live links checked | **Frozen-tree check immediately before pushing:** re-verify every file the READMEs reference exists on disk (charts, screenshots, CSVs) — a missing asset blocks the push. Then verify the live GitHub page renders. Final gate: roadmap success criteria (plan.md §8). Only this role touches GitHub. |

## Handoff format

Each role hands off with a short written report (a file in the day folder
or a message to the orchestrator), never just a verbal "done":

1. **What was produced** — exact file paths.
2. **Verified numbers** — exact figures, row counts, versions, commands run
   and their results (exit codes, pass/fail counts).
3. **Known gaps / defects** — anything unfinished, with the exact file and
   line where it lives.
4. **Next role's first step** — the one thing the next role should do first.

Handoffs are reports, not conversations: the next role must need no extra
context fetch to start.

## Token-optimisation rules

- **One verification, reused everywhere.** Endpoints, rate limits, metric
  definitions and fallback parameters are verified once by the researcher
  and then copied, never re-searched or re-verified by later roles.
- **Reuse the tester's numbers.** The optimizer and publisher use the
  tester's verified figures verbatim (returns, drawdowns, correlations, row
  counts). Nobody recomputes a finding from scratch — a spot-check from the
  committed CSVs is the most that is ever needed.
- **Pass only what the next role needs.** Each handoff carries its own
  output + the one upstream file the next role must read (brief/plan for the
  coder, report for the optimizer), not the whole history.
- **Minimal edits.** Fix clear gaps only; do not refactor working code, do
  not add dependencies, do not re-run a live API fetch when the data is
  already verified in the tree.
- **Small, pinned dependencies.** `requirements.txt` pins exact `==`
  versions verified in the build venv; no new runtime dependency without a
  plan change. Dev tools (ruff, black) are pinned once in the portfolio-root
  `requirements-dev.txt`, shared by all days.
- **No duplicate parallel work.** Only one agent works on a given file at a
  time; parallelism is for independent days or sequential roles.

## Tooling

- **Orchestrator** (`agents/orchestrator.py`, stdlib only, no LLM calls):
  `python agents/orchestrator.py --day N checklist` prints the 6-stage
  handoff checklist; `--day N --slug <slug> scaffold` creates the day
  folder from the Day 1 template tree; `--day N validate` checks a day
  folder against the roadmap success criteria (README, provenance, 2+
  charts, tests, no secrets, pinned deps, `.gitignore` rule, data-size
  rule) and runs pytest.
- **Runner** (`scripts/run_day.py`): thin wrapper — scaffolds (with
  `--scaffold --slug ...`) and runs the day's pytest suite.
- **CI**: a single consolidated `.github/workflows/ci.yml` (Stage 2,
  2026-11-05) covers every changed day folder (install → ruff → black →
  pytest → chart + notebook smoke, offline, no CoinGecko API calls). The
  former `daily-project.yml` was deleted.
- **Lint/format**: `ruff` + `black`, pinned in `requirements-dev.txt`
  (ruff 0.17.4, black 26.10.1); settings in each day's `pyproject.toml`.
  Coder runs them before handoff; tester re-runs them; CI enforces them.
- **Data-commit rule** (see Day 1 `data/README.md`): small raw data IS
  committed — files under 1 MB each, under 5 MB per day folder — because
  the raw files are the provenance record. `.gitignore` must NOT exclude
  `data/`. Anything larger must be `.gitignore`d and regenerated by the
  pipeline. Synthetic fallback output goes to
  `data/raw/*_synthetic.json` and is git-ignored; it must never overwrite
  `data/raw/*_market_chart.json`. `data_source.json` records
  `synthetic: true` + `seed: 42` when synthetic is used.
  `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
  committed cache with no network.

## Day 1 lessons learned (evidence, 2026-11-05)

(a) **CoinGecko no-key worked; the Demo-key fallback was unnecessary but
kept.** The third-party claim that `/market_chart` "now requires a demo
key" did not hold — the no-key call returned HTTP 200 for all three coins.
The key path stays in the code (env var `COINGECKO_DEMO_API_KEY` only,
never hard-coded) because a future day may hit a 401/403; an unused
fallback costs nothing, a missing one costs a day.

(b) **The app.py `idxmin` / `IndexError` bug was caught by the screenshot,
not by pytest.** `dd.idxmin()` returned labels from the full frame that
were out of bounds as positional indexes on a 366-row group; the fix
(`sort_values("date").reset_index(drop=True)` before `idxmin`, app.py
lines 181–188) came from seeing the app fail to render. Pytest only
covers the pipeline — it cannot see a dashboard crash. Hence the
mandatory smoke gate (below).

(c) **Screenshot port conflict — always use a fresh port for smoke tests.**
Port 8501 (Streamlit's default) may already be in use; the tester used
8502 and verified afterwards that the server was killed and the port free.
Rule: smoke tests use 8502 or higher, never assume 8501 is free, and
always kill the server and check the port afterwards.

(d) **`.gitignore` / raw-data decision.** The coder ignored
`data/raw/*.json` although the plan says explicitly "do NOT ignore
`data/`". The raw JSONs are small (~40 KB each, ~120 KB total) and are
part of the deliverable, so the exclusion would have silently dropped the
provenance artefacts from the repo. Resolved: commit small raw data,
document the size rule (see "Tooling" above), and diff `.gitignore`
against the plan's list before sign-off.

(e) **Notebook relative-path trap.** The notebook resolves the project
root from the working directory, so executing a copy from `/tmp` failed
with `FileNotFoundError: /tmp/data/processed/crypto_daily.csv` — a
harness artefact, not a notebook bug, but it cost a cycle. Rule: resolve
the notebook root from the notebook file's own location (`_find_root()`
in the first code cell, checking for `data/processed/crypto_daily.csv`);
never from `Path.cwd()` alone. A copy executed outside the project must
fail with a clear `FileNotFoundError`, not silently resolve to
`<cwd>/data/`.

Also from the Day 1 retrospective: parallel agents duplicated work on the
same files (fix: one writer per file, enforced by the orchestrator); the
tester started with an empty `.venv` and had to install deps before
verifying anything (fix: coder hands off with a working venv; tester
provisions nothing); lint was left to the end (fix: coder runs
black + ruff before handoff); `screenshots/dashboard.png` went missing
before the push with no agent having deleted it (fix: publisher's
frozen-tree check immediately before pushing).

## Workflow refinement (one, evidence-based)

**Make the Streamlit smoke test + real screenshot a mandatory Tester
gate — pytest alone does not close a day.** Evidence: lesson (b) — the
only bug that would have shipped broken (the `idxmin` IndexError) was
invisible to all 7 pytest tests and was caught only by rendering the app;
lesson (c) — the smoke test needs a fresh port (8502+) or it collides;
and the retrospective's missing-screenshot incident — the dashboard image
disappeared between handoff and push because no gate verified it existed.

Concretely, from Day 2 onward the Tester must, before writing
`test_report.md`: (1) start `streamlit run src/app.py` on a fresh port
(8502 or higher, never 8501); (2) confirm HTTP 200 on `/` and on
`/_stcore/health` with a clean server log; (3) capture a full-page
screenshot to `screenshots/dashboard.png`; (4) kill the server and verify
the port is free; (5) record the port, HTTP statuses and screenshot size
in the report. The Optimizer and Publisher then re-verify that exact file
exists at their handoffs (the Publisher's frozen-tree check). No new agent
role is created — this is one added step inside the existing Tester role,
and it replaces nothing: pytest, manual metric validation and the chart
legibility check all stay.
