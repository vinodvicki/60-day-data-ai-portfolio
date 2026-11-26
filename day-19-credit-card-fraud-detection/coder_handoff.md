# Coder handoff — Day 19 Credit Card Fraud Detection

**Status:** COMPLETE — all coder gates green, 2026-11-26.
**Venv:** `.venv/` built with pinned deps (pandas 3.1.1, numpy 2.5.4,
matplotlib 3.11.2, streamlit 1.66.1, requests 2.34.2, pytest 9.2.0,
pytest-cov 7.1.0, jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1,
scipy 1.18.1; dev tools black 26.10.1, ruff 0.17.4, mypy 2.4.1;
playwright 1.55.0 installed in the venv for the smoke screenshot only
— NOT in requirements.txt).

## What was produced (exact paths)

- `src/analysis.py` (pure metric/cost/sweep functions), `src/data_pipeline.py`
  (download + fingerprint + 3 models + 9 processed files), `src/make_charts.py`
  (4 charts from processed CSVs only), `src/app.py` (Streamlit metrics panel).
- `data/processed/` — 9 files, 31 KB total: `data_source.json`,
  `class_summary.csv`, `amount_summary.csv`, `amount_hist.csv`,
  `model_metrics.csv`, `confusion_matrix.csv`, `threshold_sweep.csv`,
  `cost_curve.csv`, `pr_curves.csv`.
- `data/raw/creditcard.csv` — 144 MB, git-ignored local cache, verified
  fingerprint (284,807 rows, 492 frauds, md5 e90efcb8…). NOT committed.
- `outputs/charts/01–04.png`, `outputs/insights_summary.md`,
  `notebooks/analysis.ipynb` (15 cells), `README.md`, `data/README.md`.
- `tests/` — conftest.py (sys.path bootstrap), test_analysis.py (9),
  test_pipeline.py (9), test_pipeline_extra.py (5),
  test_make_charts.py (3), test_smoke.py (7). Total 33 tests.
- `screenshots/dashboard.png` — real capture, 1280×3850, 421,702 B,
  md5 7ffbe4e25f912afe898c14d8c7a1e09b (port 8502).

## Verified numbers (coder gates, all run from inside the day folder)

- `black --check src tests` clean; `ruff check src tests` clean;
  `mypy src tests` clean (9→11 files after new tests added).
- `pytest --cov=src --cov-fail-under=30`: **33 passed, coverage 64.50%**
  (analysis 100%, make_charts 99%, pipeline 46%, app 0% — app is
  exercised by the smoke test, not pytest).
- Pipeline `--offline`: fingerprint OK; baseline PR-AUC 0.0017 /
  ROC 0.5000; logistic regression PR-AUC 0.7004 / ROC 0.9679, P 0.0671,
  R 0.8784; random forest PR-AUC 0.8239 / ROC 0.9435, P 0.9720,
  R 0.7027. Best model random forest; cost-optimal threshold 0.10
  ($785.58/10k txns, P 0.7654, R 0.8378). Deterministic across 3 runs.
- Notebook nbconvert exit 0, 15 cells, 0 errors — also from a copy
  without `data/raw/` (CI-safe, reads processed CSVs only).
- Streamlit smoke (port 8502): HTTP 200 on / and /_stcore/health,
  screenshot captured, server killed, port verified free.
- Offline reproduce: pipeline re-ran `--offline` twice; processed
  files byte-identical (same metrics both runs).

## Bugs/defects fixed in-stage (coder)

- C-1: `pr_curves.csv` was 5.0 MB (85k points) — downsampled to ≤200
  points/model (now 17 KB); the 1 MB/file rule holds.
- C-2: chart 01 read the raw file (CI would fail without the cache) —
  added committed `amount_hist.csv`; all charts now read processed
  CSVs only.
- C-3: chart 01 label collisions (count vs title; `$…$` mathtext in
  the median label) and chart 04's annotation arrow crossing the panel
  — fixed and re-viewed; all 4 charts legible.
- C-4: app.py markdown `$…$` pair rendered as LaTeX math (collapsed
  spaces in the threshold line) — switched to "USD …"; model table
  trimmed to 10 columns so it fits the viewport.
- C-5: coverage was 23.92% (below the 30 floor) — added chart + pipeline
  unit tests; now 64.50%.

## Known gaps / defects

- None known. One note: the dashboard table shows only the 10 key
  columns (full table is in `model_metrics.csv`).
- `data/README.md` "Manual validation" section points at the tester:
  the tester must hand-validate one number and record the diff.

## Next role's first step (tester)

Re-run every gate independently in the coder's venv (never install
from scratch): `py_compile`, `pytest --cov=src` (record coverage),
pipeline `--offline` reproduce + diff, Streamlit smoke on a FRESH port
(8503+, not 8502), notebook execute from a copy without `data/raw/`,
hand-validate ONE metric from the processed CSVs with an exact diff,
and view all 4 charts + the screenshot for legibility. Report defects
with exact numbers; do not edit code to make a test pass.
