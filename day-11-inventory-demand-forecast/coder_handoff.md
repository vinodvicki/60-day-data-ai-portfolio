# Day 11 — Coder handoff (Stage 3, DONE 2026-11-15)

**Project:** Inventory Demand Forecast — UCI Online Retail (Dec 2010 – Dec 2011).
SKU-level forecast (top 20 + aggregate) plus a proposed reorder list.

## What was produced

- `src/__init__.py`, `src/data_pipeline.py`, `src/forecast.py`,
  `src/clustering.py`, `src/reorder.py`, `src/make_charts.py`, `src/app.py`
- `tests/test_pipeline.py` (27 tests; `tests/test_smoke.py` deleted per plan)
- `notebooks/analysis.ipynb` (15 cells, 0 error cells via nbconvert)
- `outputs/charts/01_forecast_vs_actual.png`, `02_method_wape.png`,
  `03_demand_pattern_clusters.png`, `04_reorder_list.png` (exactly 4)
- `outputs/insights_summary.md`, `README.md`, `data/README.md`
- `data/processed/` — 7 CSVs + `data_source.json`;
  `data/raw/sample_rows.json` (1,000 cleaned rows)
- `screenshots/dashboard.png` (1200×5955, 855,566 bytes — real capture, see below)
- `requirements.txt` (Day 10 stack + openpyxl==3.1.5), `.gitignore` (plan §3.4),
  `pyproject.toml`, `LICENSE`

## Verified numbers

- Raw: 541,909 rows, 8 columns, 2010-12-01 08:26 → 2011-12-09 12:50 (verified
  from the file). Cleaned: **527,795 rows, £10,283,243.98 revenue, 5,577,139
  units, 19,776 orders**. Exclusions in order: cancelled 9,288 (3,836
  invoices) → qty ≤ 0: 1,336 → price ≤ 0: 1,181 → adjustment: 2,309 →
  missing description: 0. Missing-CustomerID rows: 131,455 (24.91%, kept in
  demand). Partial-week rows: 27,349; full-week rows: 500,446.
- **No Saturday transactions at all**; week 2010-12-27 has zero transactions
  (retailer closed over Christmas); December 2011 is a partial month.
- 52 full weeks (2010-12-06 → 2011-12-04); aggregate 5,241,272 units
  (mean 100,794/week; max 185,756 in week starting 2011-11-14).
- Top 20: **12.36% of full-week revenue** (£1,188,693.92 of £9,617,473.66),
  451,918 units (8.62%). One replacement: **23284 DOORMAT KEEP CALM AND COME
  IN (£37,111.60, only 27 weeks with demand)** — replaced by the next-ranked
  passer. Quirk found: the same StockCode can carry more than one Description
  spelling, so ranking/weekly demand group by StockCode only (modal
  description); grouping by Description would have split one SKU's revenue.
- Clusters (3,897 SKUs with any demand): smooth 137 (17.28% of units),
  erratic 935 (48.55%), intermittent 893 (8.50%), lumpy 1,932 (25.66%).
  KMeans k = 4 cross-check on top 200: agreement **64.0%** (partial, SBC decides).
- Backtest, primary holdout (train 1–48 / forecast 49–52, Christmas ramp),
  volume-weighted WAPE, top 20: moving average **44.16%**, naïve 44.33%, Holt
  45.52%, gradient boosting 65.51%, Croston-SBA 80.30%; seasonal naïve n/a on
  both origins. Winners: smooth → moving average (34.0%; Croston-SBA 33.6%
  within the 0.5 pp tie-break, simpler wins), erratic → moving average (47.3%;
  Holt 46.9% within 0.5 pp, simpler wins), intermittent → Holt (52.4%),
  lumpy → naïve (29.7%). Aggregate winner: naïve (8.25% WAPE). Supplementary
  mid-year holdout disagrees for lumpy (moving average wins, 169.3% WAPE) —
  disclosed; primary governs the reorder list.
- Published forecast: top 20 **69,194 units** over 4 weeks from 2011-12-05;
  aggregate **627,508 units** (naïve). Reorder total order-up-to **97,314
  units** (69,194 forecast + 28,120 safety stock); 2 SKUs flagged
  review-manually (23084, 23166). Largest order-up-to: 23084 (19,343), 23166
  (18,730), 22197 (14,550).
- Recommendations (exactly 3, evidence → action → expected effect) in
  `outputs/insights_summary.md`, verified against the committed CSVs.

## Gates run (all pass)

| Gate | Result |
|---|---|
| pytest `tests/test_pipeline.py` | **27/27 passed** (day folder; also passed from repo root after adding the `sys.path` insert Day 10 uses) |
| black `--check src tests` | clean (8 files unchanged) |
| ruff `check src tests` | clean |
| py_compile | OK |
| Notebook via nbconvert | 15 cells, **0 error cells**, exit 0 (executed 2026-11-15 with raw present; guarded forecast section re-ran and asserted the backtest match; re-executed after lint fixes) |
| Streamlit smoke | port **8502**: HTTP 200 on `/`, HTTP 200 on `/_stcore/health`; clean server log (0 errors); server killed, port verified free |
| Screenshot | `screenshots/dashboard.png`, 1200×5955, 855,566 bytes — real single-shot tall-viewport capture (stMain scrollHeight method), visually verified, KPIs not truncated, no seams; seasonal-naïve row now shown as n/a in the method table |
| Offline pipeline run | regenerates processed files; `data_source.json` byte-identical (sha256 verified) |
| Orchestrator validate | **11/11** |
| File sizes | No committed file > 1 MB (largest: dashboard.png 855,566; notebook 648,748; data_source.json 607,391); `data/` committed total 936 KB (< 5 MB) |
| Hand validation (coder) | 23166 safety stock recomputed by hand from the committed CSVs: 1.28 × σ(non-zero training weeks, 14,260.930926247098) = **18,253.991585596286**, matching `reorder_list.csv` exactly (**diff 0.0**). Also exact: 22423 forecast total 901.0 (4-wk moving average of [169, 235, 261, 236]) and aggregate naïve WAPE 0.08252144200709814. Full arithmetic in `data/README.md`. |

## Screenshot method (read this before re-shooting)

Playwright `full_page=True` does **not** work for this Streamlit version: the
page scrolls inside `MAIN[data-testid="stMain"]` (scrollHeight 5,955 px), not
the document. The working method is a **single shot with the viewport resized
to the measured stMain scrollHeight** (see `/tmp/shot_day11.py`): load at
1200×900, poll until scrollHeight is stable (2 consecutive equal readings),
`set_viewport_size(1200, height)`, wait 6 s, screenshot. The capture is
855,566 bytes, so no palette quantisation was needed this time. Kill the
server with `fuser -k 8502/tcp` — do **not** use `pkill -f` with the port in
the pattern, it matches the shell's own command line and kills it (SIGTERM).

## Known gaps / defects

1. **Chart 03 top-20 labels overlap** where 17 of the top 20 share ADI ≈ 1.0–1.7
   and CV² 0.2–2.7 — the codes are circled and most are readable at full zoom,
   and the exact per-SKU ADI/CV² are in `sku_summary.csv` and
   `data_source.json`. Quadrant labels are in their correct quadrants; the
   x-axis is log-scaled and labelled as such.
2. **Holt ETS convergence warnings** on some series
   (`statsmodels` ConvergenceWarning, "Optimization failed to converge") —
   the fits still return forecasts and the backtest values are deterministic;
   recorded, not suppressed.
3. **23166's safety stock (18,254 units) dwarfs its 476-unit forecast** — this
   is the formula working as specified (one 74,215-unit bulk week in training
   inflates the non-zero-week σ to 14,261), not a bug; the SKU is flagged
   `review-manually` and the case is called out in the insights and README.
4. Raw ZIP/XLSX were **deleted from disk at handoff** (plan §9). The tester
   must not re-download live data; `--offline` runs from the committed CSVs.
   The notebook's guarded forecast section will print the "raw not present"
   note instead of re-running when the tester executes it.

## Bugs fixed during coding

- Column-name mismatch: the raw file uses `StockCode`/`InvoiceNo` etc.; the
  pipeline now renames to snake_case once in `clean_transactions`.
- Description-splitting bug: grouping weekly demand / revenue by Description
  split single SKUs across rows (weekly_demand came out at 1,047 rows, and
  two SKUs showed near-zero revenue with thousands of units). Fixed by
  grouping on StockCode only with the modal description; weekly_demand is now
  exactly 1,040 rows.
- `data_source.json` recorded `last_week_start` as 2011-12-04 (the week *end*);
  fixed to the Monday 2011-11-28.
- Notebook SQL check failed on a datetime-vs-string comparison; fixed by
  normalising both sides to datetimes. Notebook guarded-forecast cell failed
  with `ModuleNotFoundError: src` because the kernel runs with cwd =
  `notebooks/`; fixed with a `sys.path.insert(0, str(ROOT))`.
- Dashboard method-comparison table dropped the seasonal-naïve row
  (`pivot_table` drops all-NaN rows by default); fixed with `dropna=False`.
- Test fixture bugs of mine (price-count ordering, ADI fixture, seasonal-naïve
  expected values, weekly max date) — fixed in the tests, not the code.

## Tester's first step

Run `pytest tests/ -q` in the day folder venv (27 tests, ~25 s), then
re-run the offline pipeline check: copy `data/processed/` to a temp dir and
confirm `python -m src.data_pipeline --offline --day-dir <tmp>` leaves
`data_source.json` byte-identical — or simply re-run the existing
offline-clobber test, which already asserts this.
