# Coder handoff — Day 20 Inflation & Cost of Living Dashboard

## What was produced

- `src/analysis.py` — pure functions: yoy, mom, cumulative_since,
  real_earnings, indexed, basket_cost, purchasing_power, cagr,
  annualised_vol, log_returns, summarise_series.
- `src/data_pipeline.py` — FRED fredgraph.csv fetch (10 series, no key),
  `--live | --offline | --use-cache | --synthetic`; builds the frozen 8
  processed files + `data_source.json`.
- `src/make_charts.py` — 4 charts from processed CSVs only, 1280 px wide.
- `src/app.py` — Streamlit purchasing-power dashboard (processed CSVs +
  charts only; 6 labelled assumptions on the page; basket slider).
- `notebooks/analysis.ipynb` — 15 cells, reads processed CSVs only,
  `_find_root()` from the notebook location.
- `tests/` — conftest.py (sys.path bootstrap), test_analysis.py (15
  tests), test_pipeline.py (13), test_make_charts.py (6),
  test_smoke.py (8).
- `data/raw/` — 10 verbatim FRED CSVs (~150 KB total, committed).
  `data/processed/` — the frozen 8 files. `data/README.md`,
  `outputs/insights_summary.md`, `README.md` (4 charts embedded +
  dashboard preview), `requirements.txt` (pinned, no plotly/scikit-learn).

## Verified numbers (coder's gates, all in the day venv)

- `black --check src tests` PASS; `ruff check src tests` PASS;
  `mypy src tests` PASS (10 source files, no issues).
- `pytest tests/ -q --cov=src --cov-fail-under=30`: **41 passed**,
  coverage **64.88%** (threshold 30).
- Notebook: nbconvert execute, 15 cells, **0 errors**.
- Pipeline: `--offline` build, 248 months (Mar 2006 → Oct 2026),
  window_end 2026-10-01, synthetic False.
- Streamlit smoke (port 8502): HTTP 200 on `/` and `/_stcore/health`;
  real screenshot `screenshots/dashboard.png` 1280×4219, 472,856 bytes,
  md5 a90434fa75c1d7cbfcac02dd49b71e0e; port verified free after kill.
- Headline findings: CPI +69.0% since Mar 2006 (199.65 → 337.48); $100
  basket → $168.99; $1 worth $0.30; peak YoY 8.98% (Jun 2022); latest
  YoY 3.72% (Sep 2026); housing +80.0%, food +79.4%, medical +79.1%,
  apparel +15.0%; energy +20.35% YoY (Sep 2026); real pay +12.2%
  ($10.04 → $11.26), real YoY −0.54% (Sep 2026).

## Known gaps / defects fixed in-stage

- **D-1 (data):** the first two `--live` runs were killed by service
  restarts after 1–2 series; finished from the verbatim FRED downloads
  (researcher probe, same day) via `--offline`. Documented in
  data/README.md. The `--live` path was exercised for 2 series.
- **D-2 (data, real bug):** Oct 2025 has no CPI value (BLS never
  published it — 2025 lapse in appropriations). The first build dropped
  that row, which silently shifted every later YoY by one month (Oct 2026
  YoY read 4.08% — actually a 13-month change). Fixed: raw rows with
  missing values are kept, panel reindexed to a complete monthly grid;
  Oct 2026 YoY is now correctly NaN and the latest reported YoY is
  Sep 2026, 3.72% (matches BLS's published 3.7%). Verified against the
  BLS Real Earnings release.
- **D-3 (charts):** chart 01 y-axis clipped at 0, hiding the 2009/2015
  deflation dips → ylim now extends below zero. Chart 04 title mangled
  by matplotlib mathtext (`$...$` pairs) → titles/labels rewritten
  without dollar-sign pairs. Chart 02 "+66%" label struck through by the
  dashed headline line → white backing added. App `$...$` LaTeX
  rendering in the basket line → dollars escaped (`\$`).
- All 4 charts + the new screenshot were viewed after the fixes.

## Next role's first step (Tester)

Re-run every gate in this venv (never provision deps yourself): pytest
with coverage (record the number), mypy, black/ruff, notebook execute
from a copy without `data/raw/`, Streamlit smoke on a different fresh
port (8503+) with your own screenshot, hand-validate one metric from the
processed CSVs, and view the PNGs for legibility. Report defects with
exact numbers; do not edit code to make a test pass.
