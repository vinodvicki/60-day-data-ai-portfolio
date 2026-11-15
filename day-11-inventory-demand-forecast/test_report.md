# Day 11 — Test report (Stage 4, tester verification, 2026-11-15)

**Project:** Inventory Demand Forecast — UCI Online Retail (2010–2011).
**Tester verdict: PASS with 1 minor documentation defect + 3 cosmetic observations.**
No code defect, no gate failure. The defect list (§9) is docs-only; nothing
blocks the optimizer from fixing it without touching the pipeline.

## 1. Commands run and results

All commands run in the coder's venv
(`day-11-inventory-demand-forecast/.venv`, Python 3.12.3). No dependencies
installed; no live fetch; raw ZIP/XLSX absent throughout (only
`data/raw/sample_rows.json` on disk).

| # | Command | Result |
|---|---|---|
| 1 | `.venv/bin/python -m py_compile src/*.py` | exit 0 |
| 2 | `.venv/bin/black --check src tests` | clean — "8 files would be left unchanged", exit 0 |
| 3 | `.venv/bin/ruff check src tests` | "All checks passed!", exit 0 |
| 4 | `.venv/bin/python -m pytest tests/ -q` (day folder) | **27 passed, 1 warning in 37.31 s**, exit 0 |
| 5 | `python -m pytest day-11-inventory-demand-forecast/tests/ -q` (repo root) | **27 passed, 1 warning in 29.12 s**, exit 0 |
| 6 | `python -m src.data_pipeline --offline` (raw absent) | exit 0 — "offline regeneration complete (data_source.json untouched if live)" |
| 7 | `jupyter nbconvert --to notebook --execute --inplace --allow-errors notebooks/analysis.ipynb` | exit 0, **15 cells, 0 error cells** |
| 8 | `streamlit run src/app.py --server.port 8503` + curl + Playwright screenshot | HTTP 200 on `/`, HTTP 200 on `/_stcore/health`, clean log, screenshot 1200×5955, 855,566 bytes, **byte-identical to `screenshots/dashboard.png`**; server killed, port 8503 verified free |
| 9 | `python3 agents/orchestrator.py --day 11 validate` (portfolio root) | **11/11 checks passed**, exit 0 |

Pytest warning (1, both runs): `statsmodels` `ConvergenceWarning:
Optimization failed to converge` in
`tests/test_pipeline.py::test_offline_run_does_not_clobber_data_source` —
the known Holt ETS warning (coder gap 2). Fits still return deterministic
forecasts; backtest values reproduce exactly (see §4).

## 2. Offline pipeline reproducibility

- `data_source.json` sha256 before and after the offline run:
  `3504356393cc51904390f13508b5d130313116258f11f2eb73353a2842afedca` —
  **byte-identical** (`cmp` clean).
- All 7 processed CSV sha256 values unchanged after the run
  (e.g. `weekly_demand.csv b26fe405…`, `reorder_list.csv e507baa1…`).
- Row counts after the run match the plan exactly: `weekly_demand.csv`
  1,040; `weekly_aggregate.csv` 52; `sku_summary.csv` 20;
  `cluster_summary.csv` 4; `forecast.csv` 84; `backtest.csv` 252
  (2 origins × 6 methods × 21 series); `reorder_list.csv` 20.

## 3. Notebook

- nbconvert exit 0, 15 cells, **0 error cells** (counted by parsing the
  executed notebook JSON).
- Guarded forecast section behaved as designed with the raw absent —
  cell 13 prints: "Raw XLSX not present (git-ignored, deleted at handoff) —
  forecast section skipped; committed CSVs used. Committed forecast rows:
  84 | backtest rows: 252".
- Root resolution confirmed: `notebooks/analysis.ipynb` defines
  `_find_root()` from `Path(__file__)` (line 48–51), not from cwd.
- Note: the `--inplace` re-execution refreshed the notebook's outputs, so
  the file is now 648,693 bytes (was 648,748 at handoff). Still 15 cells,
  0 errors. The README validation line quoting "648,748 bytes" is now
  stale by 55 bytes — see observation §9.5.

## 4. Streamlit smoke gate (mandatory)

- Fresh port **8503** (never 8501; coder's 8502 not reused).
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200**.
- Server log (`/tmp/streamlit_day11_test.log`): **zero** lines matching
  error/exception/traceback/warning.
- Screenshot: single-shot tall-viewport method (viewport resized to the
  measured `stMain` scrollHeight, 5,955 px — Playwright `full_page` does
  not work on this Streamlit version). Tester capture
  `/tmp/day11_tester_shot.png`: **1200×5955, 855,566 bytes**,
  sha256 `0150acec52f7f31374faeb40f32fb6f7cf995040ddf239be660c4b4fd25eebaa`
  — **byte-identical to the coder's `screenshots/dashboard.png`**.
  The dashboard renders fully: title + two assumption labels, KPI row
  (5,241,272 units; 12.4% top-20 revenue share; 44.2% headline WAPE;
  2 review-manually), forecast table, reorder-list table (with the
  "Total order-up-to across the top 20: 97,314 units" line), all 4 charts,
  method-comparison table (seasonal-naïve row shown as None/n/a),
  cluster tables, 3 recommendations, methods + limitations, CC BY 4.0
  footer. No error banner. (The reorder and method tables scroll
  horizontally — Streamlit's default dataframe behaviour, not a defect.)
- Server killed with `fuser -k 8503/tcp`; `ss` confirms **port 8503 free**.

## 5. Manual validation (different metric from the coder's)

Recomputed independently from the committed CSVs (no pipeline code):

- **Reorder total S = 97,314 units (primary check).**
  `reorder_list.csv`: Σ `order_up_to_units` = **97,313.71514638793**
  → 97,314 ✓. Σ `forecast_4w_units` = 69,194.25609214183,
  Σ `safety_stock_units` = 28,119.459054246086;
  S − (forecast + SS) = **0.0 exactly** ✓. `implied_order_zero_on_hand_units`
  == `order_up_to_units` on all 20 rows ✓.
- **Top-20 forecast total:** `forecast.csv` (excl. AGGREGATE) sums to
  **69,194.25609214183** → 69,194 ✓. Aggregate forecast = **627,508.0** ✓.
- **Moving-average WAPE 44.16% (second check).** Per-SKU WAPEs recomputed
  per-week from `weekly_demand.csv` (mean of training weeks 45–48, flat
  over holdout weeks 49–52) match `backtest.csv` exactly for all 19
  defined SKUs (22502 is NaN — zero holdout actuals, correctly excluded
  as weight 0). Volume-weighted over the top 20:
  Σ(WAPE × actual) / Σ(actual) = **0.44160365638563825 = 44.16%** ✓
  (matches `data_source.json` `overall_volume_weighted_wape_primary`
  to all digits). My first attempt used the error of the 4-week totals
  (41.03%) — wrong definition; WAPE sums per-week absolute errors, per
  plan §4.4. The 44.16% figure is correct.
- **Per-cluster winners verified from `backtest.csv` + `sku_summary.csv`:**
  smooth MA 34.03%, erratic MA 47.26%, intermittent Holt 52.35%,
  lumpy naïve 29.74%, aggregate naïve 8.25% — all match the docs.
  Tie-breaks hold: Croston-SBA smooth 33.64% is 0.39 pp below MA 34.03%
  (< 0.5 pp, simpler wins → MA); Holt erratic 46.94% is 0.32 pp below MA
  47.26% (< 0.5 pp → MA). Overall: MA 44.16%, naïve 44.33%, Holt 45.52%,
  gradient boosting 65.51%, Croston-SBA 80.30% — all match.
- **Supplementary holdout:** lumpy MA 169.3% wins (disagrees with primary,
  disclosed); Croston-SBA lumpy 3,805.98% ✓ (insights "3,805.9%").
- **Spot checks:** 23084 order-up-to 19,343.01, 23166 18,729.99,
  22197 14,550.40 ✓; lumpy S sum 38,073.01 ✓; 23084 forecast 17,840 =
  4 × week-52 units (4,460) ✓; 22423 published forecast 901.0 =
  4 × mean([169, 235, 261, 236]) ✓; 23166 max training week 74,215 ✓.

## 6. Chart legibility (all 4 viewed at full size)

| Chart | Verdict |
|---|---|
| 01_forecast_vs_actual.png (160,533 B) | PASS — legible, to scale, holdout shaded (weeks 49–52), footnoted. Cosmetic only: top-right panel title truncated ("WHITE HANGING HEART T-LIGHT HOLD", missing "ER") — §9.3. |
| 02_method_wape.png (56,034 B) | PASS — grouped bars legible, naïve 44.3% reference line, winners named in subtitle, footnoted. Lumpy Croston bar 169.3% matches the CSV. |
| 03_demand_pattern_clusters.png (90,865 B) | PASS WITH NOTE (cosmetic) — quadrant lines/labels in correct quadrants, axes labelled (log scale noted), footnote present, scatter to scale. The known top-20 label overlap is confirmed: in the ADI ≈ 1.0–1.3 cluster the labels pile into an illegible smudge; only 23166 and 23203 are readable, and the "Smooth" quadrant label is partly obscured by points. Exact per-SKU ADI/CV² are in `sku_summary.csv` and `data_source.json`, and the chart's clustering story still reads — cosmetic, not a send-back. |
| 04_reorder_list.png (143,374 B) | PASS — legible, to scale, ranked by order-up-to, review-manually flags + service levels annotated, footnote present. Cosmetic only: y-labels truncated at ~25 chars ("MEDIUM CERAMIC TOP STO", "PAPER CHAIN KIT 50'S C", …) — §9.3. 23166's bar correctly shows a tiny forecast sliver + huge hatched safety stock. |

## 7. Cross-checks

- **`.gitignore`** matches plan §3.4 exactly: scaffold defaults plus
  the three raw-data lines (`data/raw/online_retail.zip`,
  `data/raw/Online Retail.xlsx`, `data/raw/*_synthetic.csv`); `data/`
  itself is NOT excluded.
- **Sizes:** `data/` total 933,475 bytes (< 5 MB); no file anywhere in
  the day folder (excluding `.venv`) exceeds 1 MB (largest:
  `screenshots/dashboard.png` 855,566; notebook 648,693 after
  re-execution; `data_source.json` 607,391). No raw ZIP/XLSX on disk.
- **Plan §5 tree:** every listed file exists on disk (checked all 35
  paths); `tests/test_smoke.py` is deleted, only `tests/test_pipeline.py`
  exists (27 tests, ≥ 15 required).
- **README references:** every file referenced by `README.md`,
  `data/README.md` and `outputs/insights_summary.md` exists
  (4 charts, `screenshots/dashboard.png`, `data/README.md`,
  `requirements.txt`, `outputs/insights_summary.md`, `LICENSE`).
  `src/app.py` embeds all 4 charts (`CHARTS = ROOT / "outputs" / "charts"`,
  lines 17, 99–115) and loads the processed CSVs only.
- **Headline numbers agree with the committed CSVs** (all spot-checked):
  cleaned 527,795 rows / £10,283,243.98 / 5,577,139 units / 19,776 orders;
  exclusions 9,288 (3,836 invoices) / 1,336 / 1,181 / 2,309 / 0;
  missing-CustomerID 131,455 (24.91%); partial-week rows 27,349,
  full-week rows 500,446 (527,795 − 27,349 ✓); aggregate 5,241,272 units,
  week-52 156,877, holdout actual 681,023; top 20 = 451,918 units,
  £1,188,693.92, 12.36% of £9,617,473.66; clusters 137 / 935 / 893 / 1,932
  with unit shares 17.28% / 48.55% / 8.50% / 25.66%; KMeans agreement
  64.0%; 23284 replacement (£37,111.60, 27 weeks) recorded in
  `data_source.json` and both READMEs; no-Saturday confirmed
  (`n_saturday_rows: 0`); 52 full weeks 2010-12-06 → 2011-12-04.
- **Insights arithmetic:** 19,343 + 18,730 + 14,550 = 52,623 = 54.1% of
  97,314 ✓; 38,073 = 39.1% ✓; 28,120 = 28.9% ✓. Exactly 3
  recommendations, each evidence → action → expected effect.
- **Credential grep** over `src`, `tests`, `*.md`, `*.txt`, `*.toml`,
  `*.json`, `*.ipynb`, `*.csv`: **no hits** for api-key/password/secret/
  token patterns (the only "key" mentions are "no key, no account").
- **Requirements:** 13 packages, all pinned `==`, versions match
  `data/README.md` (pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2,
  streamlit 1.66.1, openpyxl 3.1.5, …).

## 8. Orchestrator validate

`python3 agents/orchestrator.py --day 11 validate` from the portfolio
root: **11/11 checks passed** (README, provenance, 4 charts, insights,
tests, pinned deps, `.gitignore`, no credentials, data-size rule,
screenshot, pytest 27 passed in 26.62 s).

## 9. Defect list

### Defect 1 (minor, documentation — the only defect requiring a fix)

- **File:** `data/README.md`, line 145 (Manual validation section,
  "Aggregate naïve WAPE, primary holdout" spot-check).
- **What is wrong:** it states the naïve backtest forecast as
  "forecast 156,877 each week (week 48)". 156,877 is **week 52's**
  actual (row 52 of `weekly_aggregate.csv`, week starting 2011-11-28).
  The primary-holdout naïve forecast repeats the last training value,
  **week 48 = 158,805 units** (week starting 2011-10-31). The correct
  sentence is: "actual weeks 49–52 [182855, 185756, 155535, 156877],
  forecast 158,805 each week (week 48)".
- **Impact:** docs-only. The quoted WAPE (0.08252144200709814) is still
  correct — it coincidentally equals the value for either forecast
  (verified: Σ|actual − 158,805| = Σ|actual − 156,877| = 56,199 over
  Σactual = 681,023) — and `backtest.csv` (0.08252144) is correct.
  `insights_summary.md:15` is NOT affected: it correctly says the
  *published* aggregate forecast "repeats week 52's 156,877 units".
- **Fix:** one-line edit in `data/README.md:145` (156,877 → 158,805).

### Observations (cosmetic — pass with note, no fix required)

2. **Chart 03 label overlap** (`outputs/charts/03_demand_pattern_clusters.png`):
   confirmed at full size; top-20 StockCode labels in the ADI ≈ 1.0–1.3
   cluster overlap into an illegible smudge (only 23166 and 23203 readable);
   the "Smooth" quadrant label is partly obscured by points. Cosmetic:
   quadrant story still reads, exact values are in `sku_summary.csv` /
   `data_source.json`. Known gap, disclosed by the coder.
3. **Truncated chart titles/labels:** chart 01 panel title
   "85123A — WHITE HANGING HEART T-LIGHT HOLD" (missing "ER");
   chart 04 y-labels cut at ~25 characters. Cosmetic; full descriptions
   are in the CSVs and dashboard tables.
4. **`data_source.json` contains 2 bare `NaN` literals**
   (`backtest.in_sample_wape_aggregate`: `holt`, `gradient_boosting`) —
   invalid strict JSON (Python `json.load` accepts it). Suggest `null`
   instead. Cosmetic/robustness; no gate depends on it.
5. **README notebook byte count stale:** `README.md` validation section
   quotes the notebook as "648,748 bytes"; the required tester
   re-execution (`nbconvert --inplace`) refreshed its outputs and it is
   now 648,693 bytes (15 cells, 0 errors — unchanged). Update the number
   (or re-run nbconvert and record the final size).
6. **Known gaps confirmed, not defects:** Holt ETS `ConvergenceWarning`
   (1 pytest warning; fits deterministic, backtest reproduces exactly);
   23166 safety stock 18,254 vs 476-unit forecast is the plan formula
   working as specified (one 74,215-unit bulk week inflates σ), flagged
   `review-manually` and called out in the insights and README.

## 10. Tester sign-off

- py_compile ✓ · black ✓ · ruff ✓ · pytest 27/27 (day folder + repo root) ✓
- Offline pipeline reproduces processed files; `data_source.json`
  byte-identical ✓ · notebook 15 cells / 0 errors ✓
- Streamlit smoke gate (port 8503): HTTP 200 / 200, clean log, real
  screenshot byte-identical to the coder's, server killed, port free ✓
- Manual validation (reorder total S = 97,314, diff 0.0; MA WAPE 44.16%
  from per-week errors) ✓ · charts legible (03 cosmetic note) ✓
- Cross-checks, credential grep, orchestrator validate 11/11 ✓
- **Defects: 1 minor (docs-only, `data/README.md:145`).**
