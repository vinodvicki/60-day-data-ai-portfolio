# Coder handoff — Day 14: Voter Turnout Analytics

**Status:** complete. All coder gates pass. Descriptive only — no predictive
model, per Victor's voice-call decision (2026-11-20). Outliers screened during
skewness screening and reported as found, never dropped.

## What was produced (exact paths)

All under `~/workspace/goals/60-day-data-ai-portfolio/day-14-voter-turnout-analytics/`:

- `README.md` — problem, audience, headline findings, top/bottom-10 tables,
  decider rules, setup, validation, limitations, attribution.
- `requirements.txt` — pinned `==` versions verified in the build venv
  (Python 3.12.3): Day 13 stack + `geopandas==1.2.0` + `scipy==1.18.1`; no
  scikit-learn, no openpyxl. `src/requirements.txt` forwards to it (Day 13
  pattern).
- `.gitignore` — scaffold defaults + shapefile/EAVS/synthetic exclusions;
  does NOT exclude `data/` or the two UF CSVs. (One addition vs the plan:
  `data/raw/*_synthetic.csv`, because the plan stores the synthetic fallback
  as a CSV — see §11 note below.)
- `pyproject.toml`, `LICENSE`, `.pre-commit-config.yaml` — scaffold files,
  unchanged except nothing.
- `research_brief.md`, `plan.md` — untouched.
- `src/__init__.py`, `src/turnout.py` (pure functions, all tested),
  `src/data_pipeline.py` (`--live` / `--offline` / `--use-cache` /
  `--synthetic`), `src/make_charts.py` (exactly 4 charts),
  `src/app.py` (Streamlit dashboard, `layout="wide"`, `width="stretch"`).
- `data/raw/Turnout_1980_2022_v1.2.csv` (116,830 bytes, committed),
  `data/raw/Turnout_2024G_v0.4.csv` (8,378 bytes, committed).
- `data/processed/data_source.json`, `turnout_long.csv` (1,196 rows),
  `national_series.csv` (23 rows), `state_2024.csv` (52 rows),
  `correlations.csv` (3 rows), `outliers.csv` (5 rows).
- `data/README.md` — full provenance (see below).
- `notebooks/analysis.ipynb` — 16 cells, executes via nbconvert with 0
  error cells; `_find_root()` from the notebook location; map section
  guarded by the shapefile's presence.
- `outputs/insights_summary.md` — one finding per §2.1 question + top/bottom
  tables + correlation table + outlier list + limitations.
- `outputs/charts/01_turnout_map_2024.png` (218,227 bytes),
  `02_turnout_over_time.png` (123,303 bytes),
  `03_state_ranking_2024.png` (212,520 bytes),
  `04_demographic_scatter.png` (144,820 bytes).
- `screenshots/dashboard.png` — real capture, 1200×5481, 716,699 bytes
  (< 1 MB).
- `tests/test_pipeline.py` — 31 tests. `tests/test_smoke.py` (scaffold
  placeholder) deleted, per plan §5.
- `.venv/` — build venv with pinned deps + dev tools (ruff 0.17.4,
  black 26.10.1, mypy 2.4.1, pytest-cov 7.1.0).

## Verified numbers

| Gate | Result |
|---|---|
| pytest (in day folder) | **31 passed**, coverage **65.20%** (threshold 30) |
| pytest (from portfolio root) | **31 passed**, coverage **65.20%** (chart-01 lines uncovered without the shapefile; still ≥ 30) |
| `black --check src tests` | clean |
| `ruff check src tests` | clean |
| `mypy src tests` (from inside the day folder) | clean — no issues in 6 source files |
| `python agents/orchestrator.py --day 14 validate` | **11/11 checks passed** |
| Notebook (nbconvert, `--execute --inplace`) | 16 cells, **0 error cells**; re-executed after the shapefile was deleted — the guarded map section prints "Shapefile absent — map re-render skipped" and still finishes clean |
| Streamlit smoke | Port **8502** (fresh, never 8501); HTTP **200** on `/` and on `/_stcore/health`; server log clean (0 errors); real full-page screenshot `screenshots/dashboard.png`, 1200×5481, **716,699 bytes**; server killed, port 8502 verified free |
| Hand-validated metric | 2024 US VEP turnout recomputed by hand from the committed CSV: 156,766,239 ÷ 243,803,423 × 100 = **64.30%**, diff **0.0 pp** vs the file rate |

Key data numbers (all from the committed CSVs):

- Rows: 1,144 (1980–2022 file) + 52 (2024 file) = **1,196**; duplicates 0.
- Column-5 parse counts — 1980–2022 file: 51 URLs / 1,039 vote counts /
  54 blank; 2024 file: 51 URLs / 0 vote counts / 1 blank.
- Null ballots: **209** total (200 state-year rows + 9 national rows,
  1980–1996). All years 2010–2024 complete.
- Recompute check: 987 rows, max diff **0.0226 pp**, 0 rows over 0.05 pp.
  Spot-checks: 2024 US 64.30%, 2022 US 46.12%, CO 73.40%, CA 62.26%,
  AR 54.06%.
- VEP reconciliation: 0 rows flagged (tolerance 0.5%); max relative
  difference 0.058%.
- EAVS cross-check (F1a ballots cast, V1): sampled CO −0.011%, CA +0.15%
  (both within 0.5%); additional AR −5.71%, TX +0.78% (over 0.5%,
  disclosed in the memo; UF stands). EAVS V2 was not linked on the EAC
  index page as fetched 2026-11-21, so V1 was used (plan §3.1 fallback).
- Shapefile join: **51/51** jurisdictions joined; 0 unmatched.
- 2024 ranking: WI 76.66% (#1) … HI 50.26% (#51); DC 64.94% (rank 25);
  7 states up vs 2020, 44 down, median −1.68 pp.
- Correlations (2024, n = 51): noncitizen r = −0.07, p = 0.639 (no clear
  association); felon share r = −0.40, p = 0.003 (moves with turnout,
  association only); overseas n = 0 (not computable).
- Skewness: presidential pooled −0.27, midterm pooled +0.06.
- Outliers: **5 rows, all from the pooled presidential pass** (1980 DC
  37.90%, 1980 SC 42.35%, 1988 SC 42.46%, 1996 NV 41.23%, 2016 HI 43.19%);
  **the 2024 pass flagged zero states**. All 5 rows remain in
  `turnout_long.csv` (asserted by a test).
- Data size: `data/` = **304 KB** total; no file over 1 MB. Shapefile zip,
  EAVS zip and their unpacked contents were downloaded at build time,
  used, and **deleted at handoff** (git-ignored, per plan §9).

## Plan vs brief differences (plan wins — §11, all honoured)

- Single correlation scope `2024_states` (no pooled presidential scope).
- VEP reconciliation tolerance fixed at > 0.5% of file VEP.
- Choropleth via geopandas + matplotlib (not Plotly geo).
- Doc `.txt` files read at build time, not committed (v1.2 dated 10/8/2024;
  v0.4 dated 3/2/2026).
- Offline chart-01 behaviour: "shapefile absent, chart 01 not regenerated",
  committed PNG stands.
- Alaska/Hawaii as geometry-transform insets on the main axes (separate
  inset axes shift under `bbox_inches="tight"` — found during the build).
- Notebook map section guarded by the shapefile's presence.
- Day 13 stack + geopandas + scipy; no scikit-learn, no openpyxl.

## Known gaps / defects

- **National VEP turnout 1980–1996 is not reported in the file at all**
  (blank ballots and blank rate on the US rows). The brief expected the
  national total to be estimated; in the file as delivered, the estimate
  covers 1998–2008 only. Recorded as missing in `national_series.csv`
  and labelled on every surface that uses it — this is a property of the
  source file, not a pipeline defect.
- **EAVS disagreements over 0.5% for Arkansas (−5.71%) and Texas (+0.78%)**
  are disclosed in the memo and `data_source.json`; UF figures stand per
  Rule 1. Not a defect — a recorded cross-check result.
- The dashboard's national-series table has 9 columns and scrolls
  horizontally in the app (last column partly visible until scrolled) —
  standard Streamlit dataframe behaviour, not a defect.
- The Streamlit smoke run used `--server.fileWatcherType none`: the
  default file watcher raises an inotify-limit error in this sandbox
  (environment limit, not an app defect). With that flag the server log is
  clean.
- The screenshot was taken with Playwright from the Day 10 venv (which has
  it installed); Day 14's venv does not include Playwright and
  `requirements.txt` does not list it — it is screenshot tooling only, not
  a runtime dependency.

## Tester's first step

From inside the day folder, in the coder's venv (`.venv/` exists with pinned
deps installed — provision nothing): run
`.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30` and
confirm 30 passed, then re-run the Streamlit smoke on a fresh port (8502+,
`--server.fileWatcherType none` — see the inotify note above) and check the
screenshot against the app. Then verify one metric by hand from the committed
CSVs (suggested: 2024 US VEP turnout, 156,766,239 ÷ 243,803,423 = 64.30%).
