# Test report — Day 16 Crop Yield Prediction

**Role:** tester (stage 4 of 6). **Date:** 2026-11-23.
**Verdict: PASS with 2 minor surface defects (D-1, D-2) for the optimizer.**
All gates pass; nothing is broken in the pipeline, models or data.

## 1. Commands run + results (exact)

All in the coder's venv `day-16-crop-yield-prediction/.venv` (present; nothing
installed from scratch).

| Check | Command | Result |
|---|---|---|
| py_compile | `.venv/bin/python -m py_compile src/*.py tests/*.py` | exit 0 |
| pytest, day folder | `.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30` | **21 passed**, coverage **47.70%** (bar 30) — coder's number reproduced exactly |
| pytest, repo root | `python -m pytest day-16-crop-yield-prediction/tests/ -q --cov=day-16-crop-yield-prediction/src --cov-fail-under=30` (from `60-day-data-ai-portfolio/`) | **21 passed**, coverage **47.70%** — same |
| pipeline `--offline` | `.venv/bin/python src/data_pipeline.py --offline` | rows=26, train=20, held-out=6; `yield_weather.csv` byte-identical to the live run; `data_source.json` **not clobbered** (md5 unchanged) |
| black | `.venv/bin/python -m black --check src tests` | exit 0, 7 files unchanged |
| ruff | `.venv/bin/python -m ruff check src tests` | All checks passed |
| mypy (from inside the day folder) | `.venv/bin/python -m mypy src tests` | Success: no issues found in 7 source files |
| notebook | `jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb` | exit 0, **0 error cells** (14 cells) |
| orchestrator validate | (optimizer stage — not yet run) | — |

## 2. Hand-validation (plan §4.4 — recomputed by hand, `csv` + `math` only, no pipeline code)

- 2024 USA maize yield from the committed raw CSV: filter
  `Entity == "United States"`, year 2024 → **11.253324 t/ha**,
  **179.28 bu/acre** (× 39.368 / 2.47105). Stored value identical:
  **diff 0.0 t/ha** (bu/acre diff 2.8e-14, float rounding only). PASS.
- Recorded in `data/processed/data_source.json` under `manual_validation`
  (metric, method, both values, diff 0.0, tester, 2026-11-23).

## 3. Streamlit smoke gate (mandatory)

- Port **8506** (fresh, never 8501). `GET /` → **HTTP 200**;
  `GET /_stcore/health` → **HTTP 200 `ok`**; clean server log, no
  exceptions — the app renders end to end (no Day 1-style `idxmin` crash).
- Screenshot: real full-page capture with Playwright, viewport
  1280×4467 (height = `[data-testid="stMain"]` scrollHeight — the
  `documentElement`/`stAppViewContainer` height stays at the viewport
  height, so the first two captures were only 900 px tall; the probe
  script `/tmp/probe_heights.py` found the true 4,467 px height).
  File `screenshots/dashboard.png`: **1280×4467, 408,590 bytes**,
  md5 `4cf04b335a433e314189151101011d15`.
- Server killed after capture; port 8506 verified free afterwards.
  (Earlier ports 8502/8503/8504/8505 were used for the two short captures
  and the height probe; all were killed and verified free.)

## 4. Chart legibility check

- 01 yield history: legible, to scale (y 7–12.5, line chart, no truncated
  bars); 2012 dip + 2025 annotations clear. PASS.
- 02 actual vs predicted: legible; grouped bars, y 9.5–12.5, RMSEs in the
  title. PASS.
- 03 feature drivers: **DEFECT D-2** (see §6) — the `heat_days_gs`
  y-label collides with its `r = -0.17` annotation. Otherwise legible.
- 04 station map: legible; both stations labelled with exact coordinates;
  schematic note present. PASS.
- All 4 charts are PNGs > 10 KB, correct magic bytes (test suite asserts this).

## 5. Cross-checks (plan §3.3)

- Row counts: yields 26, weather 9,497 days/state, joined 26 (20/6). PASS.
- 2012 drought spot-check (test suite): Iowa gs rain 423.6 mm (2012) <
  1041.9 mm (2010); yield 7.73 < 9.58 t/ha. PASS.
- Numbers in README/insights/notebook match the committed CSVs (spot-checked:
  Ridge 0.540, naive_last 0.287, 2024 yield 11.253324, 2012 yield 7.73).
  PASS.
- Forbidden-claim grep passes (no causal language, no 2026 forecast, USDA
  named only as not-used-live). PASS.
- Data-size rule: raw 952,064 B total, largest file 368,479 B. PASS.

## 6. Defects found (for the optimizer — both are surface-only)

- **D-1 — Dashboard KPI truncated.** In `screenshots/dashboard.png` the
  4th KPI reads "26 (train 2…" — `src/app.py` sets the "Years modelled"
  metric value to `f"{len(df)} (train … + held-out …)"`, which overflows
  its column even at 1280 px wide. Fix: shorten the value (e.g. `"26"`)
  and move the split into the delta text.
- **D-2 — Chart 03 annotation collision.** In
  `outputs/charts/03_feature_drivers.png` the `heat_days_gs` y-tick label
  overlaps the `r = -0.17` annotation, and `jul_temp_mean`'s `r = -0.39`
  touches the left spine. Cause: negative-bar annotations are placed at
  `coef − 0.05` with `ha="right"`, and the x-axis starts at ≈ −0.55, so
  the longest negative bar's text runs into the tick labels. Fix: widen
  the x-limits (e.g. `set_xlim(-0.75, 1.05)`) so the annotations sit
  inside the axes.

## 7. What the optimizer must do (next role's first step)

1. Fix D-1 in `src/app.py` and D-2 in `src/make_charts.py` (regenerate
   chart 03 only — the CSVs are unchanged).
2. Re-capture `screenshots/dashboard.png` on a fresh port (8507+) with the
   tall-viewport method (`[data-testid="stMain"]` scrollHeight), kill the
   server, verify the port is free.
3. Re-run pytest + black/ruff/mypy; run `orchestrator validate` (11/11).
4. Do NOT re-run the pipeline `--live` — it would drop the
   `manual_validation` section just added to `data_source.json`.
