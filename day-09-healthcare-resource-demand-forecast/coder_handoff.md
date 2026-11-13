# Coder handoff — Day 09 Healthcare Resource Demand Forecast

**Stage:** coder (role 3 of 6) → tester. **Date:** 2026-11-13.
**Repo:** `vinodvicki/60-day-data-ai-portfolio`, day folder
`day-09-healthcare-resource-demand-forecast/`. Built exactly to `plan.md`
(plan wins over the brief where they differ; differences are in plan §11).

## What was produced (exact file paths)

All paths under `~/workspace/goals/60-day-data-ai-portfolio/day-09-healthcare-resource-demand-forecast/`:

- `src/data_pipeline.py` — live fetch (NSSP `$limit=50000`, bed 2 paged
  calls), count/range verification, Combined construction + 72-NULL audit,
  national / state / bed series (state-sum ratio), `sample_rows.json`,
  processed CSVs + `data_source.json`; modes `--live` / `--use-cache` /
  `--offline` / `--synthetic`.
- `src/forecast.py` — seasonal naïve + Holt-Winters (additive trend +
  additive seasonality, period 52), residual-bootstrap intervals (seed 42,
  1,000 paths), 3-origin rolling backtest, band classification,
  `build_forecast` writing `forecast.csv` / `backtest.csv` /
  `band_history.csv`.
- `src/metrics.py` — pure metric functions (RMSE, MAE, MAPE, interval
  coverage, seasonal-naïve predict).
- `src/make_charts.py` — exactly 4 charts, offline from processed CSVs.
- `src/app.py` — Streamlit dashboard, processed CSVs only, never
  live-fetches; forecast + intervals, backtest, bands + state comparison,
  bed panel + staffing table, volume converter (defaults 1,000/week, 15%).
- `src/__init__.py` — empty.
- `notebooks/analysis.ipynb` — 16 cells, executed via nbconvert, 0 error
  cells, both with raw present (guarded forecast re-ran; metrics matched
  committed CSVs) and with raw absent (forecast skipped with a note).
  The committed copy is the **no-raw execution** (the state at handoff).
- `tests/test_pipeline.py` — **37 tests** (replaces scaffold
  `test_smoke.py`, deleted).
- `data/README.md`, `README.md`, `outputs/insights_summary.md`,
  `requirements.txt` (Day 8 stack + statsmodels 0.15.0), `.gitignore`,
  `pyproject.toml`.
- `data/raw/sample_rows.json` (1,000 NSSP + 100 bed rows, 798,920 bytes),
  `data/processed/data_source.json`, `national_combined.csv` (161 rows),
  `state_combined.csv` (8,187 rows), `bed_utilisation.csv` (226 rows),
  `forecast.csv` (8 rows), `backtest.csv` (6 rows), `band_history.csv`
  (161 rows).
- `outputs/charts/01_forecast.png`, `02_backtest.png`,
  `03_demand_bands.png`, `04_bed_capacity.png` — all viewed by the coder,
  legible, to scale (two annotation/table defects found and fixed, see
  Known gaps).
- `screenshots/dashboard.png` — real capture (1200×5957, 974,008 bytes)
  of the running app on port 8502.

## Verified numbers

- **Live fetch:** NSSP **25,116 rows** (2023-10-07 → 2026-10-31), bed
  **81,713 rows** (2020-01-01 → 2024-04-27) — both match the brief's
  probed counts exactly.
- **National series:** 161 weeks; latest week (2026-10-31) **2.3%**
  (COVID-19 0.5% + Influenza 1.7% + RSV 0.1%). Observed max Combined
  **10.4%** (2023-12-30); 2024–25 winter peak 10.0% (2025-02-01).
- **NULL audit:** **72 rows** (0.29%): Iowa 54 (nothing since 2026-07-04),
  Delaware 9, Georgia 9 (nothing since 2026-10-17). **National weeks
  affected: 0.**
- **Backtest (3 origins × 2 methods):** Holt-Winters mean RMSE **0.4693**,
  MAE 0.4177, MAPE 42.19, mean 80% coverage 75.0%; seasonal naïve mean
  RMSE **0.8244**, MAE 0.7833, MAPE 80.63, coverage 91.67%. Per-origin HW
  RMSE: 0.4909 / 0.5942 / 0.3229 (origins 12 / 8 / 4); naïve wins origin 8
  (0.3905 vs 0.5942). **Published method: Holt-Winters.**
- **Forecast (8 weeks, 2026-11-07 → 2026-12-26):** 3.03, 3.79, 4.75, 5.68,
  6.57, 8.19, 10.91, **13.87%**; bands Moderate, Moderate, High, High,
  Surge, Surge, Surge, Surge. Final week 80% interval 12.76–14.91%,
  95% interval 12.08–15.38%.
- **Band history:** Low 89, Moderate 35, High 19, Surge **18** of 161
  weeks — Surge is a real historical level, not decorative.
- **Top-5 states (latest-4-week mean):** Hawaii 7.0% (already Surge),
  Florida 3.4%, Louisiana 2.9%, Washington 2.8%, Texas 2.6%.
- **Bed series:** 226 weeks; mean utilisation 72.5%, max 78.9%
  (2022-12-10), latest 74.95% (2024-04-27), ICU latest 71.65%. Full
  coverage share 86.36% (11,145 state-days dropped). 45 of 226 weeks have
  <50 states reporting, all in 2020.
- **Hand validation (two metrics, by independent recomputation from the
  raw JSONs — not via the pipeline):** latest-week Combined
  0.5 + 1.7 + 0.1 = 2.3, **diff 0.0**; final bed week
  3,604,488 / 4,808,901 = 0.7495, **diff 0.0** (ICU 0.7165, diff 0.0).
  Recorded in `data/README.md`.
- **SQL check:** seasonal means + 4-week lag agree between pandas and
  in-memory SQLite (asserted in the notebook and in the tests).

## Gates (all pass)

- venv `.venv` exists; pinned deps installed (pandas 3.1.1, numpy 2.5.4,
  matplotlib 3.11.2, plotly 7.1.0, streamlit 1.66.1, requests 2.34.2,
  pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1,
  scipy 1.18.1, **statsmodels 0.15.0**; ruff 0.17.4, black 26.10.1).
- `black --check src tests` clean; `ruff check src tests` clean.
- `pytest tests/ -q`: **37 passed**, from the day folder and from the
  portfolio root.
- `python -m src.data_pipeline --live` verified live counts; `--offline`
  reproduces all processed CSVs **byte-identically** (md5-verified) and
  leaves `data_source.json` untouched.
- Notebook: nbconvert top-to-bottom, 16 cells, **0 error cells**, both
  with raw present (guarded forecast re-ran, byte-identical) and with raw
  absent (forecast skipped with a note).
- Streamlit smoke: port **8502**, HTTP **200** on `/` and on
  `/_stcore/health`, clean server log, real `screenshots/dashboard.png`
  (1200×5957, 974,008 bytes), server killed, port verified free.
- `.gitignore` matches plan §3.4 (raw NSSP + bed JSONs + `*_synthetic.json`
  excluded; nothing else in `data/` excluded). Note: the workspace copy
  is not a git checkout, so `git check-ignore` could not be run here —
  the publisher should confirm with git before pushing.
- Data size: no file > 1 MB (largest is the screenshot, 974,008 bytes);
  committed `data/` total 1,132,954 bytes (< 5 MB). Raw full JSONs deleted
  from disk at handoff (git-ignored; NSSP ~2.9 MB, bed ~585 MB).

## Known gaps / defects (and deliberate deviations from the plan)

1. **Forecast outer weeks exceed the observed maximum.** The 8-week
   forecast reaches 13.87%, above the observed max of 10.4%. This is the
   plan-fixed method working as specified (additive trend extrapolates
   the steep autumn rise; no tuning allowed), and it is disclosed
   prominently in the README, notebook, insights summary and dashboard —
   not hidden. The flu comparison supports a severe season (1.7% now vs
   0.3% a year ago), but weeks 7–8 are labelled a severe-season scenario.
2. **Bed `*_coverage` columns are hospital counts, not 0/1 flags** (the
   brief assumed 0/1). Full coverage is defined as
   `inpatient_beds_coverage == inpatient_beds_used_coverage` (both > 0);
   86.36% of state-days qualify. Documented in `data/README.md` and the
   pipeline docstring.
3. **Bed sample is 100 rows, not 1,000.** Bed rows are wide (~129 fields,
   ~7 KB each as JSON); 1,000 rows would be ~7 MB, over the 1 MB file
   rule. 100 rows = ~0.65 MB of the 799 KB sample file. Within the plan's
   "≤ 1,000 rows per dataset". Documented in `data/README.md` and a code
   comment.
4. **Holt-Winters ConvergenceWarning (suppressed, recorded).**
   statsmodels' optimiser emits a ConvergenceWarning on some windows (it
   stops on tolerance, not a failed fit). Parameters are finite and the
   forecasts are sane, so the warning is suppressed in
   `src/forecast.py` (`holt_winters_forecast`) and recorded in
   `data/README.md` and the notebook.
5. **Chart defects found by viewing and fixed:** (a) chart 01's "Latest:
   2.3%" annotation ran off the right edge — moved left of the point;
   (b) chart 04(b)'s staffing table text overlapped its cells — shortened
   labels + explicit column widths + wider panel; (c) chart 04's x-label
   collided with the 5-line footnote — bottom margin raised; (d) chart
   03's footnote wrongly implied Surge never occurred — corrected to the
   observed 18 weeks.
6. **Screenshot is 1200 px wide, not 1440.** The full-page capture at
   1440×6400 was 1,091,715 bytes — over the 1 MB file rule. Re-captured
   at 1200×5957 (974,008 bytes, trailing whitespace trimmed); it is a
   real capture of the running app, all sections incl. the footer.
7. **Bed early-2020 thin reporting (disclosed, not fixed).** 45 of 226
   bed weeks have <50 states reporting; the 48.9–59.8% readings in early
   2020 reflect 3–38 states. Kept per the plan (all weeks retained);
   disclosed in chart 04's footnote, the README, the notebook and the
   dashboard.
8. No `.pbix` (plan §11), no SARIMA (plan §11). Synthetic fallback
   implemented but **not used** (live data verified);
   `data_source.json` records `synthetic: false`.

## Tester's first step

Run, in the day folder's venv (do not reinstall — the venv is handed off
working): `.venv/bin/python -m pytest tests/ -q` (expect 37 passed),
then `.venv/bin/python -m src.data_pipeline --offline` (expect
"data_source.json untouched" and byte-identical CSVs), then re-run the
Streamlit smoke gate on a fresh port 8502+ and confirm
`screenshots/dashboard.png` matches the running app. If a live re-run is
wanted, `.venv/bin/python -m src.data_pipeline --live` re-downloads from
CDC/HHS and should reproduce the metrics exactly (same data, seed 42);
note the raw bed JSON is ~585 MB on disk, so delete it again afterwards
(`rm data/raw/nssp_ed_visits.json data/raw/bed_capacity.json`).
