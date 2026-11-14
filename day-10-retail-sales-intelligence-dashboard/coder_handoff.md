# Day 10 — Coder handoff (Stage 3, DONE 2026-11-14)

**Project:** Retail Sales Intelligence Dashboard — UCI Online Retail (Dec 2010 –
Dec 2011). Sales KPI dashboard + three commercial recommendations.

## What was produced

- `src/metrics.py`, `src/clustering.py`, `src/forecast.py`,
  `src/data_pipeline.py`, `src/make_charts.py`, `src/app.py`
- `tests/test_pipeline.py` (31 tests; `tests/test_smoke.py` deleted per plan)
- `notebooks/analysis.ipynb` (16 cells, 0 error cells via nbconvert)
- `outputs/charts/01_monthly_sales.png`, `02_product_country.png`,
  `03_rfm_clusters.png`, `04_forecast.png` (exactly 4, all visually checked)
- `outputs/insights_summary.md`, `README.md`, `data/README.md`
- `data/processed/` — 10 files (data_source.json + 9 CSVs), `data/raw/sample_rows.json`
  (1,000 cleaned rows)
- `screenshots/dashboard.png` (1200×6321, 461,265 bytes — real capture, see below)
- `requirements.txt` (Day 9 stack + openpyxl==3.1.5), `.gitignore` (plan §3.4),
  `pyproject.toml`, `LICENSE`

## Verified numbers

- Raw: 541,909 rows, 8 columns, 2010-12-01 08:26 → 2011-12-09 12:50 (verified
  from the file). Cleaned: **527,795 rows, £10,283,243.98 revenue, 19,776
  orders, 4,334 customers**. Exclusions in order: cancelled 9,288 (3,836
  invoices) → qty ≤ 0: 1,336 → price ≤ 0: 1,181 → adjustment: 2,309 →
  missing description: 0. Missing-CustomerID rows: 131,455, 14.80% of revenue
  (£1,522,177.33).
- KPIs: units 5,577,139; AOV £519.99; repeat rate 65.27%; top-10 SKU share
  9.41%; UK share 85.18% (£8,759,372.58).
- Monthly: Nov 2011 peak £1,457,745.53 (2,751 orders), 2.86× Feb 2011
  (£508,952.87); Sep–Nov £3,594,965.43 (34.96%). Dec 2011 partial (9 days)
  £615,501.60, flagged, excluded from MoM.
- Top SKUs: REGENCY CAKESTAND 3 TIER £174,484.74 (1.70%); PAPER CRAFT LITTLE
  BIRDIE £168,469.60 (1.64%, 1 order, 80,995 units); WHITE HANGING HEART
  £104,340.29. Groups: SET 7.35%, JUMBO 5.70%, Other 65.46%.
- Countries: UK £8,759,372.58 (85.18%, AOV £489.24); Netherlands £283,889.34
  (AOV £3,052.57); EIRE £271,164.30; Germany £205,569.89; France £184,582.74;
  Australia £138,171.31 (AOV £2,467.34); non-UK £1,523,871.40, AOV £814.03.
- Clusters (silhouette **0.616**): Champions 13 (18.68%, mean £125,862.44);
  Big spenders 209 (29.26%); Occasional buyers 3,046 (46.27%); Lapsed 1,066
  (5.79%, recency 247.5 days). Top 222 customers (5.12%) = **47.94% =
  £4,200,055.35** of identified revenue.
- Forecast: Holt-Winters wins (mean RMSE £55,504.52 vs naïve £62,800.78;
  origin 8: £38,624.28 vs £51,795.73; origin 16: £72,384.76 vs £73,805.83).
  8-week forecast 2011-12-05 → 2012-01-23: £346,552.30 → £418,710.57, total
  **£3,061,051.48**. Weekly series 51 full weeks; last full week 2011-11-28
  £310,353.86; max weekly £374,736.15.
- Recommendations (numbers verified against committed CSVs): (1) protect the
  222 (47.94%, £4,200,055.35; losing 10% ≈ £420k); (2) build stock 6–8 weeks
  before September (Sep–Nov £3,594,965.43; 5% Nov stock-out ≈ £73k);
  (3) win back 1,066 lapsed (10% return at £475.91 ≈ £50,732; at Occasional
  mean £1,330.93 ≈ £141,877).
- Quirk recorded: **no Saturday transactions at all** in the data; peak hours
  12:00 (13.79%), 10:00 (13.65%); Thursday 20.77%, Sunday 7.83%.

## Gates run (all pass)

| Gate | Result |
|---|---|
| pytest `tests/test_pipeline.py` | **31/31 passed** (day folder; also passed from repo root) |
| black `--check src tests` | clean (7 files unchanged) |
| ruff `check src tests` | clean |
| Notebook via nbconvert | 16 cells, **0 error cells** (executed 2026-11-14 with raw present; guarded forecast section re-ran and asserted the backtest/forecast match) |
| Streamlit smoke | port **8502**: HTTP 200 on `/`, HTTP 200 on `/_stcore/health`; server killed, port verified free |
| Screenshot | `screenshots/dashboard.png`, 1200×6321, 461,265 bytes — visually verified, all sections render, "£10.28m" metric not truncated |
| Orchestrator validate | **10/11** — one false positive, see "Known gaps" below |
| File sizes | No committed file > 1 MB (notebook 904,309 bytes; dashboard.png 461,265 bytes); `data/` committed total 500 KB (< 5 MB) |
| Hand validation (coder) | Sum of `monthly_sales.csv` revenue_gbp = **£10,283,243.98**, exactly equal to `data_source.json` total (diff £0.00). Country sum also exact; top-10 share 9.41%; repeat rate 65.27% (from `rfm_clusters.csv`); AOV £519.99. Full arithmetic in `data/README.md`. |

## Screenshot method (read this before re-shooting)

Playwright `full_page=True` does **not** work for this Streamlit version: the
page scrolls inside `MAIN[data-testid="stMain"]` (scrollHeight 6,321 px), not
the document. Scroll-and-stitch also fails — it duplicates the fixed-position
Deploy button and leaves seams in the charts. The working method is a
**single shot with the viewport resized to the measured stMain scrollHeight**
(see `/tmp/shot_day10f.py`): load at 1200×900, poll until scrollHeight is
stable (2 consecutive equal readings), `set_viewport_size(1200, height)`,
wait 6 s, screenshot. A 1000-px-wide capture was rejected: it truncates the
KPI metrics ("£10.2…") and cuts the cluster table. The final PNG was
palette-quantised to 256 colours (PIL adaptive) from the RGB capture to meet
the < 1 MB rule (1,138,355 → 461,265 bytes); content is identical and was
visually verified after quantisation. Do **not** re-save with PIL
`optimize=True` — it made the file larger (1,036,299 bytes).

## Known gaps / defects

1. **Orchestrator validate 10/11 — false positive, no action taken.** The
   validator's credential heuristic (`AKIA[0-9A-Z]{16}`, case-insensitive)
   matches the string `aKiAEJDJ5gl4N03YwLAe` inside the base64-encoded chart
   PNG embedded in `notebooks/analysis.ipynb:328` (the chart-01 display
   output). That string is random base64 image data, not a credential — there
   is no key, token, password or secret anywhere in the tree (verified by
   inspection of the match and its context). Day 9's notebook has 4 embedded
   PNGs too and passes only because its base64 happens not to contain the
   pattern. Deliberately NOT fixed by perturbing a verified chart or stripping
   the inline charts — both would weaken the deliverable to dodge a heuristic.
   Shared-tooling note: the validator should skip `image/png` base64 blobs in
   `.ipynb` outputs.
2. **Screenshot is palette-quantised (256 colours), not raw RGB** — content
   identical, visually verified. Recorded here so the publisher knows.
3. **Notebook is 904,309 bytes, close to the 1 MB limit** — do not add heavy
   outputs.
4. Raw ZIP/XLSX were **deleted from disk at handoff** (plan §9). The tester
   must not re-download live data; `--offline` runs from the committed CSVs.

## Bugs fixed during coding

- `Series.dt.weekday` deprecation → `day_of_week`.
- Weekly full-weeks formula bug for Sunday max dates (first/last full Monday
  computation); real-data output unchanged (still 51 weeks).
- Test float-equality → approximate comparisons (Day 9 CI lesson).
- Chart 02: x-limits/title shortened, UK-share annotation moved inside the
  panel. Chart 03: right panel switched to log scale, shortened inside-bar
  labels, footnote "Percentages are shares of identified-customer revenue";
  DPI 100 (4,334-point scatter) to keep the notebook < 1 MB.
- App metric truncation: "Total revenue" showed "£10,283,…" in the 6-column
  layout — changed to "£10.28m" with the exact total in the caption; verified
  live in the final screenshot.

## Tester's first step

Use the coder's venv (never install deps). Run `py_compile`, pytest from the
repo root AND the day folder, `python -m src.data_pipeline --offline` (raw is
absent — do not re-download), Streamlit smoke on a fresh port **8503+** with a
real full-page screenshot (reuse `/tmp/shot_day10f.py`, tall-viewport method),
hand-validate one metric from the committed CSVs, check chart legibility, and
confirm the validate false positive is base64 image data, not a credential.
Write `test_report.md`. Never edit code to make a test pass — report defects.
