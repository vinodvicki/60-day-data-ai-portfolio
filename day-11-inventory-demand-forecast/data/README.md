# Data provenance — Day 11 Inventory Demand Forecast

## Source

- **Provider:** UCI Machine Learning Repository, dataset "Online Retail",
  dataset ID 352.
- **Dataset page:** https://archive.ics.uci.edu/dataset/352/online+retail
- **Download URL:** https://archive.ics.uci.edu/static/public/352/online+retail.zip
  (one plain full download — the server ignores the Range header, so no
  ranged/resumable fetch was attempted). No key, no account, no documented
  rate limit. One retry after 60 s on HTTP 429/5xx, then stop (not needed).
- **Fetch date:** 2026-11-15 (live, `source: "live"` in `data_source.json`).
- **Licence / attribution:** CC BY 4.0. Chen, D. (2015). Online Retail
  [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33
- **Page inconsistency (recorded, not resolved by guessing):** the dataset
  page header says "# Features 6" while the variables table lists 8 columns.
  The file itself is authoritative: **8 columns verified**
  (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice,
  CustomerID, Country).

## Fetch outcome

- ZIP downloaded: 23,715,478 bytes; XLSX inside: `Online Retail.xlsx`.
- **Verified from the file: 541,909 rows, 8 columns** (matches the dataset page).
- Confirmed date range: **2010-12-01 08:26 → 2011-12-09 12:50**.
- **No Saturday transactions at all** (0 rows) — the retailer did not trade
  Saturdays, a structural 6-day trading week and a further reason for weekly
  (not daily) aggregation.
- Week of 2010-12-27 has **zero transactions** — the retailer was closed over
  Christmas. December 2011 is a partial month (data end 2011-12-09).

## Row counts and coverage

Cleaning rules (plan §3.2) applied in this order; every exclusion counted:

| Step | Rows excluded / remaining |
|---|---|
| Raw rows | 541,909 |
| Unparseable InvoiceDate | 0 |
| Cancelled rows (InvoiceNo starting with `C`) | 9,288 (3,836 invoices) |
| Non-positive quantity (after cancellations) | 1,336 |
| Non-positive price | 1,181 |
| Non-product adjustment lines (StockCode in POST, DOT, M, D, BANK CHARGES, CRUK, C2, AMAZONFEE; Description in POSTAGE, DISCOUNT, MANUAL, BANK CHARGES, AMAZON FEE, CRUK) | 2,309 |
| Missing / blank description | 0 |
| **Cleaned rows** | **527,795** |
| Cleaned revenue (GBP, Quantity × UnitPrice) | £10,283,243.98 |
| Cleaned units / orders | 5,577,139 units / 19,776 orders |
| Rows with missing CustomerID (kept in demand — demand is summed over all customers) | 131,455 (24.91% of cleaned rows) |
| Partial-week rows (2010-12-01 → 2010-12-05 and 2011-12-05 → 2011-12-09) — excluded from the weekly series | 27,349 |
| Full-week rows (52 weeks) | 500,446 |

**Weekly series:** 52 full ISO weeks, week 1 starting Monday 2010-12-06, week 52
starting Monday 2011-11-28 and ending Sunday 2011-12-04. Aggregate weekly
units across all cleaned SKUs in the 52 full weeks: 5,241,272 units
(mean 100,794/week; max 185,756 in week starting 2011-11-14).

**Top-20 selection:** revenue-ranked over the 52 full weeks, each SKU with
demand in ≥ 30 of the 52 weeks. One top-20-by-revenue SKU failed the coverage
rule and was replaced: **23284 DOORMAT KEEP CALM AND COME IN (£37,111.60,
only 27 weeks with demand)**. The final top 20 are 12.36% of cleaned full-week
revenue (£9,617,473.66) and 451,918 units (8.62% of all weekly units).
One data quirk found during the build: the same StockCode can carry more than
one Description spelling in the raw file, so revenue ranking and weekly demand
are grouped by StockCode only (description = the modal spelling per SKU);
grouping by Description would have split one SKU's revenue across rows.

**Clustering:** Syntetos–Boylan ADI/CV², cut-offs ADI 1.32, CV² 0.49, over all
3,897 SKUs with any demand — smooth 137 (17.28% of units), erratic 935
(48.55%), intermittent 893 (8.50%), lumpy 1,932 (25.66%). KMeans k = 4
cross-check on the top 200 SKUs by revenue: agreement rate 64.0% (partial
agreement; SBC decides).

**Methods + backtest:** six methods (naïve, seasonal naïve, 4-week moving
average, Croston-SBA α = 0.1, Holt ETS trend-only, HistGradientBoosting) on two
4-week holdouts — primary train weeks 1–48 / forecast weeks 49–52
(2011-11-07 → 2011-12-04, the Christmas ramp, headline); supplementary train
weeks 1–29 / forecast weeks 30–33 (2011-06-27 → 2011-07-24). Seasonal naïve is
unavailable on both origins (y(t−52) does not exist for a 52-week series): its
WAPE is n/a and it never contends for winner selection. Overall
volume-weighted primary-holdout WAPE (top 20): moving average 44.16%, naïve
44.33%, Holt 45.52%, gradient boosting 65.51%, Croston-SBA 80.30%. Per-cluster
winners: smooth → 4-week moving average (34.0%; Croston-SBA 33.6% was within
the 0.5 pp tie-break, simpler method wins), erratic → 4-week moving average
(47.3%; Holt 46.9% within 0.5 pp, simpler wins), intermittent → Holt ETS
(52.4%), lumpy → naïve (29.7%). Aggregate winner: naïve (8.25% WAPE).
In-sample vs holdout WAPE on the aggregate (one-step): naïve 25.6%,
moving average 18.3%, Croston-SBA 21.9% — holdout errors are much larger
because the holdout is the Christmas ramp.

**Reorder assumptions:** 1-week lead time; 95% service level (z = 1.65) for
smooth/erratic, 90% (z = 1.28) for intermittent/lumpy; safety stock
SS = z·σ·√LT with σ over training weeks 1–48 (non-zero weeks only for
intermittent/lumpy); order-up-to S = forecast 4-week demand + SS; implied
order assumes zero on-hand. Total order-up-to 97,313.7 units (69,194.3
forecast + 28,119.5 safety stock). 2 SKUs flagged `review-manually` (both
lumpy: 23084, 23166).

## Commit rule for data files

- The raw XLSX (22.6 MB) exceeds the 1 MB/file rule, so the **data-size
  exception** applies: `data/raw/online_retail.zip` and
  `data/raw/Online Retail.xlsx` are git-ignored (see `.gitignore`) and
  re-downloaded by `python -m src.data_pipeline --live`. They are deleted
  from disk at handoff.
- `.gitignore` does **not** exclude `data/` itself — only the three raw-data
  lines. Committed: `data/processed/` (7 CSVs + `data_source.json`) and
  `data/raw/sample_rows.json` (1,000 cleaned rows, deterministic sample,
  seed 42). Committed `data/` total is under 5 MB; no committed file is
  over 1 MB.
- `--offline` regenerates the derived tables/charts from the committed CSVs
  and **never writes `data_source.json` when a live record exists** (tested —
  the file stays byte-identical).

## Committed processed files

| File | Rows | Contents |
|---|---|---|
| `data/processed/data_source.json` | — | Source, counts, cleaning exclusions, top-20 selection, clustering, backtest metrics, winners, reorder assumptions, versions; plus per-SKU ADI/CV² for all 3,897 SKUs (used by chart 03) |
| `data/processed/weekly_demand.csv` | 1,040 | Top-20 SKU × 52 weeks: week_start, stock_code, description, units |
| `data/processed/weekly_aggregate.csv` | 52 | week_start, units (all cleaned SKUs) |
| `data/processed/sku_summary.csv` | 20 | stock_code, description, revenue_gbp, revenue_share, total_units, weeks_with_demand, mean_weekly_units, adi, cv2, cluster |
| `data/processed/cluster_summary.csv` | 4 | cluster, n_skus, share_skus, share_units, mean_adi, mean_cv2 |
| `data/processed/forecast.csv` | 84 | 20 SKUs × 4 weeks + aggregate × 4: week_start, stock_code, description, cluster, winning_method, forecast_units |
| `data/processed/backtest.csv` | 252 | 2 origins × 6 methods × 21 series: origin, method, stock_code, wape, mae, rmse, bias |
| `data/processed/reorder_list.csv` | 20 | The 14 reorder columns (plan §4.5) |

## Manual validation (one metric, by hand)

Recomputed independently from the committed CSVs (2026-11-15), no pipeline code:

**23166 (MEDIUM CERAMIC TOP STORAGE JAR) safety stock.** Training weeks 1–48
(weeks starting 2010-12-06 → 2011-11-07), non-zero weeks only (lumpy SKU):
27 non-zero weeks, values
[74215, 192, 393, 215, 67, 145, 125, 54, 7, 82, 94, 193, 362, 128, 59, 141,
82, 24, 129, 39, 92, 79, 42, 82, 57, 63, 33].
σ (sample, ddof = 1) = 14,260.930926247098 units.
SS = z·σ·√LT = 1.28 × 14,260.930926247098 × √1 = **18,253.991585596286 units**.
Committed `reorder_list.csv` value: 18,253.991585596286. **Diff: 0.0 (exact).**

Two further spot-checks, also exact (diff 0.0):
- **22423 forecast total:** smooth-cluster winner is the 4-week moving
  average; last 4 weeks [169, 235, 261, 236], mean 225.25, × 4 = **901.0**;
  committed `forecast.csv` total for 22423 = 901.0.
- **Aggregate naïve WAPE, primary holdout:** actual weeks 49–52
  [182855, 185756, 155535, 156877], forecast 158,805 each week (week 48);
  Σ|actual − forecast| / Σactual = **0.08252144200709814**; committed
  `backtest.csv` value identical.

## Versions used for this build

Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
nbformat 5.11.1, scikit-learn 1.9.1, scipy 1.18.1, statsmodels 0.15.0,
openpyxl 3.1.5; ruff 0.17.4, black 26.10.1 (dev tools).
