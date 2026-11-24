# Test report — Day 17 Drought Impact Analyzer

**Role:** tester (stage 4 of 6). **Date:** 2026-11-24.
**Verdict: PASS with 1 cosmetic defect (D-1) for the optimizer.**
All gates pass; nothing is broken in the pipeline, analysis or data.

## 1. Commands run + results (exact)

| Check | Command (day venv, from inside the day folder) | Result |
|---|---|---|
| pytest + coverage | `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=30 -q` | **34 passed**, coverage **51.84%** (threshold 30) |
| pytest, repo root | `python -m pytest day-17-drought-impact-analyzer/tests/ -q` (from `60-day-data-ai-portfolio/`) | **34 passed** |
| black | `python -m black --check src tests` | exit 0, 9 files unchanged |
| ruff | `python -m ruff check src tests` | All checks passed |
| mypy (from inside the day folder) | `python -m mypy src tests` | Success: no issues found in 9 source files |
| pipeline `--offline` | `python -m src.data_pipeline --offline` | rows=26, county_year_rows=5226, worst_year=2012, gs_dsci_mean=200.4; `annual_drought_yield.csv`, `county_year.csv` and `data_source.json` **byte-identical** to the live run (cmp, no diff) |
| notebook | `jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb` | exit 0, **0 error cells** (17 cells) |
| orchestrator validate | `python agents/orchestrator.py --day 17 validate` | **11/11 checks passed** |
| Streamlit smoke | port 8502 (fresh, never 8501) | `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200 `ok`**; clean server log, no exceptions — the app renders end to end |

## 2. Defect found during testing (fixed in this stage, not passed on)

- **T-1 — Offline run clobbered the analysis columns (real).** The pipeline's
  `--offline` run rewrote `annual_drought_yield.csv` without the
  `yield_trend_fit_t_per_ha` / `yield_resid_t_per_ha` columns that
  `analysis.py` adds in place, so the offline file differed from the live
  file at line 1. Fix (tester, with the coder's plan §5 already allowing
  it): `data_pipeline.run()` now calls the analysis module's pure
  functions (`detrend_yield`, `compute_correlations`, `ar1_forecast_table`)
  and writes the enriched annual table plus `correlation_results.csv` and
  `ar1_forecast.csv` in the same run. Re-verified: `--offline` now
  reproduces all three files byte-identically, `data_source.json`
  untouched, pytest still 34/34. The standalone `python -m src.analysis`
  entry point is unchanged and idempotent.

## 3. Streamlit smoke gate (mandatory)

- Port **8502** (fresh, never 8501). `GET /` → **HTTP 200**;
  `GET /_stcore/health` → **HTTP 200 `ok`**; clean server log, no
  exceptions — the app renders end to end (no Day 1-style crash).
- Screenshot: real full-page capture with Playwright, viewport
  1280×4542 (height = max of `[data-testid="stMain"]` scrollHeight,
  `body` and `documentElement` scrollHeight — the first attempt caught a
  blank loading page at 900 px because the app had not rendered yet; the
  re-run waits for the "Drought severity trend" header and the images
  before measuring). File `screenshots/dashboard.png`: **1280×4542,
  554,467 bytes**, md5 `f81686d41520f65bd78bd5f4d09f975c`.
- Server killed after capture (process-group SIGTERM); the port was still
  bound at the immediate 2 s re-check and was **verified free 3 s later**
  (`ss` shows nothing on 8502, no streamlit processes remain) — the
  shutdown just needed a few seconds, not a leak.
- The screenshot shows all 4 KPIs, all 4 charts, the annual table, the
  correlation table, the county ranking, the AR(1) forecast table and the
  limitations section, with no truncation of the KPI values.

## 4. Chart legibility check

- 01 DSCI trend: legible, to scale (y 0–230, DSCI = 100 dashed line, 2012
  annotation clear). PASS.
- 02 drought vs yield scatter: legible; year labels readable, OLS line
  clear, 2012 outlier at bottom right. PASS.
- 03 precipitation anomaly: legible; blue/brown bars + black yield-residual
  line on the secondary axis, both axes labelled. PASS.
- 04 county map: legible; Iowa dark red, Illinois lighter, top-3 counties
  labelled, colourbar 0–12.7%. PASS. (The coder's first build of this chart
  was empty — a FIPS int/str join bug — and was fixed before handoff; the
  current PNG is the fixed version, 157,730 bytes.)

## 5. Manual validation of one metric (plan §4.5)

- **Metric:** Iowa 2012 growing-season mean DSCI.
- **Method:** independent recomputation from `data/raw/dsci_iowa.csv`
  (filter MapDate weeks in Apr–Sep 2012, mean of DSCI) vs the committed
  `gs_dsci_mean_iowa` in `data/processed/annual_drought_yield.csv`.
- **Result:** hand-computed **204.15384615384616** vs committed
  **204.15384615384616** — **difference 0.0, exact match** (26
  growing-season weeks). Recorded in `data/processed/data_source.json`
  under `manual_validation` and in `data/README.md`.
- **Spot cross-check (not the hand metric):** county-mean DSCI proxy vs
  official state DSCI agrees within 7.0 points for every checked
  year/state (2012 IA −0.7, IL +7.0; 2023 IA −1.7, IL −3.3; 2000 IA −0.4,
  IL −3.7) — the gap is the simple county mean vs the area-weighted state
  value, as expected.

## 6. Verified findings (tester's numbers, from the committed CSVs)

- DSCI vs detrended yield: r = **−0.6137**, p = **0.00085**, R² = 0.3767,
  slope −0.0076 t/ha per DSCI point (n = 26). Raw-yield r = −0.298,
  p = 0.139.
- Precipitation anomaly vs detrended yield: r = +0.2721, p = 0.1786 (not
  significant). July precipitation anomaly: r = +0.2440, p = 0.2297.
- 2012: gs DSCI mean 200.37 (IA 204.15, IL 196.58), yield 7.726 t/ha,
  residual −2.239 t/ha, rain anomaly −182.7 mm (−30.7%).
- AR(1): 2025 backtest forecast 49.03 vs actual 57.87 (error 8.84) vs
  naive error 9.25; 2026 forecast 50.16, interval [1.83, 98.48].
- Top county: Davis County, IA (12.67% mean D2+); worst county-year:
  Woodbury County, IA 2023 (97.72% D2+).

## 7. Defects for the optimizer

- **D-1 (cosmetic) — "None" in the AR(1) forecast table.** In
  `screenshots/dashboard.png` the forecast table shows `None` where the
  2026 actual and the 2025 interval are missing (NaN). Fix: display
  "—" for missing values (e.g. `forecast.fillna("—")` for display, or
  format the table before `st.dataframe`). Cosmetic only; the committed
  `ar1_forecast.csv` correctly holds empty fields.

## 8. Next role's first step

Optimizer: fix D-1, re-capture `screenshots/dashboard.png` on a fresh port
(8503+) with the render-wait method (wait for the section header + images,
then measure height), kill the server, verify the port is free, re-run
pytest + black/ruff/mypy, run `orchestrator validate` (11/11). Do NOT
re-run the pipeline `--live` — it would drop the `manual_validation`
section just added to `data_source.json`.
