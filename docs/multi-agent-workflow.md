# Multi-agent workflow — 60-Day Data + AI Portfolio

How each day's project is built: six roles, in order, each with one clear
input and one clear output. No role is added, removed or merged without
Victor's say-so. The publisher/reviewer is the only role that touches GitHub.

## The six roles

| # | Role | Input | Output | Rule |
|---|---|---|---|---|
| 1 | **Researcher** | Roadmap entry for the day (problem, skills, suggested data) | `research_brief.md` — verified source, endpoints, rate limits, metric definitions, fallback parameters | Verify once, write it down, never re-verify. No live fetch — that is the coder's job. |
| 2 | **Planner** | Roadmap entry + `research_brief.md` | `plan.md` — problem, audience, questions, file tree, per-file responsibilities, success checklist | The plan is the source of truth for the build. If the brief and plan disagree, the plan wins and the difference is noted. |
| 3 | **Coder** | `research_brief.md` + `plan.md` | Working project: `src/`, `notebooks/analysis.ipynb`, `outputs/charts/`, `tests/`, `data/` (live or labelled-synthetic), draft `README.md` / `data/README.md` / `outputs/insights_summary.md` | Build only what the plan lists. No extra web searches — all endpoints and parameters are already verified in the brief. |
| 4 | **Tester** | Coder's finished tree | Verified result (report, not edits): `py_compile`, `pytest`, pipeline run, Streamlit smoke check, manual validation of one metric, chart legibility check | Reuse, don't redo: verify the coder's run, don't rebuild. Report exact numbers and exact failures. Never edit code to make a test pass — report it. |
| 5 | **Optimizer** | Tester's verified report + coder's tree | Release-ready tree: pinned `requirements.txt`, `black`/`ruff` clean, `.gitignore` per plan, missing docs filled, `screenshots/dashboard.png`, root `README.md`, CI workflow, this workflow doc updated | Fix only clear gaps, keep changes minimal. Re-run tests after edits; re-run the live pipeline only if pipeline code changed. |
| 6 | **Publisher / reviewer** | Optimizer's release-ready tree | GitHub repo (`60-day-data-ai-portfolio`), pushed day folder, live links checked | Creates the repo, pushes, verifies the live GitHub page renders (README, charts, links). Final quality gate: roadmap success criteria (§8 of each `plan.md`). |

**Order is fixed:** researcher → planner → coder → tester → optimizer →
publisher/reviewer. A later role never re-does an earlier role's work; it
checks it and either passes it on or sends it back with a specific defect.

## Token-lean rules

- **One verification, reused everywhere.** Endpoints, rate limits, metric
  definitions and fallback parameters are verified once by the researcher and
  then copied, never re-searched or re-verified by later roles.
- **Reuse the tester's numbers.** The optimizer and publisher use the tester's
  verified figures verbatim (returns, drawdowns, correlations, row counts).
  Nobody recomputes a finding from scratch — a spot-check from the committed
  CSVs is the most that is ever needed.
- **No duplicate parallel work.** Only one agent works on a given file at a
  time (see retrospective). Parallelism is for independent days or
  independent roles in sequence, never for two agents writing the same
  notebook, chart set or README.
- **Minimal edits.** Fix clear gaps only; do not refactor working code, do not
  add dependencies, do not re-run a live API fetch when the data is already
  verified in the tree.
- **Small, pinned dependencies.** `requirements.txt` pins exact `==` versions
  verified in the build venv; no new runtime dependency without a plan change.
- **Handoffs are reports, not conversations.** Each role's output is a file
  (or a short verified report with exact numbers, commands and file paths) so
  the next role needs no extra context fetch.

## Day 1 evidence (2026-11-05)

- **Researcher:** verified CoinGecko public API — `/market_chart/range`
  (preferred) with `days=365` fallback, 5–15 calls/min, ≥5 s spacing, one
  429 retry after 60 s, keyless vs Demo-key test order, synthetic GBM
  fallback parameters. One open conflict recorded (third-party claim that a
  Demo key is now required) with the mandatory test order to resolve it.
- **Planner:** `plan.md` — 3 questions, exact file tree, per-file function
  signatures, 8-point success checklist, build order, token note.
- **Coder:** `src/data_pipeline.py` (fetch → clean → metrics → save),
  `src/app.py` (Streamlit, processed CSVs only), `src/make_charts.py`,
  `notebooks/analysis.ipynb` (14 cells), `tests/test_pipeline.py` (7 tests),
  draft README / `data/README.md` / `insights_summary.md`.
- **Tester (verified):** `py_compile` PASS; `pytest` 7/7 PASS in 1.01 s;
  Streamlit smoke PASS (HTTP 200, `/_stcore/health` ok); pipeline run PASS
  in LIVE mode — 366 rows/coin, 2025-11-05 → 2026-11-05, 1,098 rows total;
  BTC max drawdown hand-verified (peak $105,951.50 on 2025-11-11 → trough
  $58,566.09 on 2026-07-01 = −44.72%, 232 days, match ≤1e-9); charts 01–04
  to scale, PASS. Findings: BTC −20.7% / ETH −26.2% / SOL −38.5% total
  return; max drawdowns −44.7% / −56.2% / −62.9%; BTC–ETH correlation 0.906
  full window, 0.890 latest 90 days.
- **Optimizer:** pinned `requirements.txt` to the exact venv versions
  (pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
  nbformat 5.11.1, Python 3.12.3); `black` + `ruff` clean (fixed 1 unused
  import, 3 unused `noqa`s, import order, `datetime.UTC`, implicit string
  concatenation); fixed `.gitignore` (removed `data/raw/*.json` exclusion);
  completed `README.md`, `data/README.md`, `outputs/insights_summary.md`
  (verified every number against the CSVs); built
  `screenshots/dashboard.png` as a labelled composite of charts 01–04;
  created portfolio-root `README.md`, `.github/workflows/ci.yml`
  (Python 3.12, install → lint → pytest) and this document; re-ran
  `py_compile`, `pytest` 7/7, Streamlit smoke; secret grep clean.
- **Publisher / reviewer:** pending — repo `vinodvicki/60-day-data-ai-portfolio`
  does not exist yet; creation + push + live-page check are that role's job,
  not any earlier role's.

## Retrospective — Day 1: what worked, what was wasteful

### What worked

- **Research once, build from paper.** The brief + plan contained every
  endpoint, parameter and metric definition; the coder needed no extra web
  searches and the build matched the plan's file tree and function
  signatures.
- **Independent manual validation.** The tester hand-checking BTC max
  drawdown (and the optimizer re-checking every published number against
  the CSVs) caught nothing — which is the point: the check is cheap and
  the confidence it buys is what makes the numbers publishable.
- **Live-first fetch with a labelled fallback.** Keyless CoinGecko access
  worked (HTTP 200, no key), so the synthetic path stayed unused — but it
  existed, documented, and would have been labelled everywhere.
- **Small dependency set, pinned late.** Pinning exact versions at
  optimizer time (from the venv that actually ran) was simpler and more
  accurate than guessing pins up front.

### What was wasteful / what went wrong

- **Parallel agents duplicated work.** Two agents wrote the notebook/charts
  area and the README/docs area concurrently; the optimizer arrived to find
  `README.md`, `data/README.md` and `outputs/insights_summary.md` already
  written (well, and accurately) while the task brief still listed them as
  missing. Rework was avoided only because the files happened to be good —
  the optimizer still had to re-verify every number instead of writing
  once. *Fix: one writer per file, enforced by the orchestrator; parallel
  work only across different days or strictly sequential roles.*
- **`.venv` was empty when the tester started.** The tester had to install
  dependencies before it could verify anything, which cost a full install
  cycle inside the verification step. *Fix: the coder finishes with a
  working venv in place (or the orchestrator provisions it once per day
  before the tester starts); the tester never installs the project's own
  dependencies from scratch.*
- **`.gitignore` deviated from the plan.** The coder ignored `data/raw/*.json`
  although the plan says explicitly "do NOT ignore `data/`". The raw JSONs
  are small (~40 KB each) and are part of the deliverable, so the exclusion
  would have silently dropped the provenance artefacts from the repo.
  *Fix: the optimizer (or a checklist step) diffs `.gitignore` against the
  plan's §5/§6 list before sign-off; the plan's ignore-list is explicit and
  short — `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`, `.ipynb_checkpoints/`.*
- **Lint was left to the end.** Four files needed `black` reformatting and
  `ruff` flagged 8 issues (unused import, unused `noqa`s, import order).
  None was a bug, but all of it was avoidable. *Fix: the coder runs
  `black` + `ruff` before handing off; the tester re-runs them as part of
  verification (they are fast, offline checks).*
- **The dashboard screenshot arrived last and had to be composed.**
  A real Streamlit screenshot was not captured during the coder's smoke
  test, so the optimizer composed `screenshots/dashboard.png` from the four
  static charts instead. It is honest (labelled as a composite) and to
  scale, but it is not a screenshot of the running app. *Fix: the coder or
  tester captures the real running-app screenshot during the smoke test
  (headless browser or OS screenshot) and saves it to `screenshots/`; the
  composite approach is the fallback, not the default.*
  *(Publisher update, 2026-11-05: the file went missing before the push,
  was regenerated as a labelled composite, and was then replaced by a real
  full-page capture of the running Streamlit app — 1400×3600, BTC + ETH
  selected in the sidebar, summary table covering all three coins. The
  Day 1 README caption was corrected to describe it as a real screenshot.
  Full story: `docs/day-01-retrospective.md`.)*

## Changes for Days 2–60 (concrete)

1. **Orchestrator assigns one writer per file.** No two agents write the
   same file in the same day; overlapping scopes are sequenced, not
   parallelised.
2. **Coder's handoff checklist** (before the tester starts): venv exists
   with pinned deps installed; `black --check` + `ruff check` pass;
   `pytest` passes; `.gitignore` matches the plan; `screenshots/dashboard.png`
   is a real capture of the running app (or explicitly flagged as a
   composite).
3. **Tester provisions nothing.** The tester runs verification only, in the
   coder's venv; if the venv is missing, the tester reports "blocked: no
   venv" instead of installing.
4. **Optimizer verifies numbers, doesn't rewrite good docs.** If a doc
   already exists and its numbers check out against the data, the optimizer
   fixes only concrete gaps (stale statements, missing sections) instead of
   rewriting it.
5. **CI from Day 1 onward.** `.github/workflows/ci.yml` at the portfolio
   root already covers Day 1 (install → lint → pytest); each new day adds
   its own job (or extends the matrix) rather than inventing a new
   workflow file.
6. **Keep the 6 roles.** No new agent roles are added; when a day needs a
   new capability (e.g. an ML evaluator), it is a step inside the existing
   coder/tester/optimizer roles, documented in that day's `plan.md`.
