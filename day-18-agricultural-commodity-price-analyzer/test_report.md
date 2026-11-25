# Test report — Day 18 Agricultural Commodity Price Analyzer

**Status:** VERIFIED — all gates re-run independently by the tester,
2026-11-25 ~07:45 PST. **No defects found; nothing sent back.**

## 1. Gates re-run (independent of the coder)

| Gate | Command / method | Result |
|---|---|---|
| `py_compile` | `python -m py_compile src/*.py` | **PASS** |
| pytest, repo root | `pytest day-18-.../tests/ --cov=.../src --cov-fail-under=30 -q` (from `60-day-data-ai-portfolio/`) | **31 passed**, coverage **33.33%** (threshold 30) |
| pytest, day folder | `pytest --cov=src --cov-fail-under=30 -q` (from inside the day folder) | **31 passed**, coverage **33.33%** |
| black | `black --check src tests` | **clean** |
| ruff | `ruff check src tests` | **clean** |
| mypy | `mypy src tests` (from inside the day folder) | **clean** |
| Notebook | `jupyter nbconvert --to notebook --execute --stdout notebooks/analysis.ipynb` | **exit 0, 24 cells, 0 error cells** |
| Pipeline `--offline` | replay from committed raw files | all 10 processed CSVs **byte-identical** to the live run; `data_source.json` **untouched** (source "live" preserved) |
| Streamlit smoke | port **8503** (fresh, never 8501/8502) | `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200 `ok`**; clean server log, no exceptions — the app renders end to end |

## 2. Hand-validation (plan §4.5)

- **Metric:** maize price, 2012-09 (drought peak month). Recomputed
  directly from `data/raw/fred_maize.csv` (`PMAIZMTUSDM`, 2012-09-01):
  **$320.705906/t**; `data/processed/monthly_prices.csv` gives the same
  value — **diff 0.0, exact match**. Recorded in `data_source.json`
  under `manual_validation`.
- **Spot check 2:** wheat price, 2008-10 (largest shock month):
  $202.774935/t raw vs processed — **diff 0.0**.
- **Spot check 3:** 2012 growing-season DSCI mean (IA+IL avg) =
  200.365, matching Day 17's reported 200.4 for the same year/states.
- Do NOT re-run `--live` after this point without re-adding the
  `manual_validation` section (the pipeline preserves it when present,
  but a fresh live run from a clean checkout would drop it).

## 3. Streamlit smoke gate (mandatory)

- Port **8503** (fresh). `GET /` → **HTTP 200**;
  `GET /_stcore/health` → **HTTP 200 `ok`**; clean server log.
- Screenshot: real full-page capture with Playwright, viewport
  1280×6072 (height = max of `[data-testid="stMain"]` scrollHeight,
  `body` and `documentElement` scrollHeight, after waiting for the
  "Volatility and shocks" header and the images). File
  `screenshots/dashboard.png`: **1280×6072, 754,636 bytes**, md5
  `f47a232b83c27a08b82dbe793be3f186`.
- Server killed after capture (process-group SIGTERM, 5 s grace);
  port verified free afterwards (`ss` shows nothing on 8503, no
  streamlit processes remain).
- The screenshot shows all 4 KPIs (including the fixed "3 commodities
  combined" delta, now fully legible), all 4 charts, the annual table,
  the seasonality table, the top-10 shocks table, the correlation
  table, the forecast table, the county ranking and the limitations
  section, with no truncation of the KPI values.

## 4. Chart legibility check

- 01 price levels: legible, to scale (y 0–660, 3 series, 4 shaded shock
  windows with staggered short labels, no collisions). PASS.
- 02 seasonality: legible; peaks text box ("Maize May 1.04 · Wheat May
  1.03 · Soybeans Jun 1.04") sits clear of the lines; axes labelled.
  PASS.
- 03 volatility/shocks: legible; both panels readable, top-10 bars
  labelled with month + commodity. PASS.
- 04 county map: legible; all 201 counties joined by FIPS, colourbar
  labelled, top-3 labels (Massac 73.9%, Pulaski 72.3%, Hardin 71.7%)
  with leader arrows, no overlap. PASS.

## 5. Numbers spot-checked against the committed CSVs

- Seasonality: maize peak May 1.037 / trough Sep 0.968; wheat May 1.031 /
  Aug 0.983; soybeans Jun 1.042 / Oct 0.942 — match `seasonality.csv`.
- Drawdowns: wheat −69.65%, maize −63.21%, soybeans −50.99% — recomputed
  from `monthly_prices.csv`, match.
- Shock counts: 76 total (maize 21, wheat 30, soybeans 25) — match
  `shocks.csv`. Largest: wheat −26.0% (2008-10).
- Join correlations: all |r| ≤ 0.15, all p > 0.46 — match
  `correlations.csv`. Regression R² = 0.016 — match
  `regression_maize.csv`.
- Forecast: Oct 2026 $239.56/t, May 2027 $252.31/t, Sep 2027 $240.81/t;
  backtest RMSE $23.38/t vs $41.74/t — match `forecast_maize.csv` and
  `data_source.json`.

## 6. Defects

- None. No send-back to the coder.

## 7. Notes for the optimizer

- The notebook's 4 `Image()` cell outputs are stripped in the committed
  file (56,039 B; the executed version was 1,055,124 B — over the
  1 MB/file rule). The notebook still executes cleanly (verified above);
  do not re-execute it in place or the outputs will be re-embedded.
- `/tmp/smoke18.py` was lost to a /tmp wipe mid-run; the smoke script
  now lives at `~/workspace/smoke18.py` (port 8503 version).
- `data_source.json` now carries `manual_validation` — the optimizer
  must not re-run `--live` without preserving it.
