# Data provenance — Day 10 Retail Sales Intelligence Dashboard

## Source

- **Provider:** UCI Machine Learning Repository
- **Dataset:** "Online Retail", dataset ID **352**, Chen (2015)
- **Dataset page:** https://archive.ics.uci.edu/dataset/352/online+retail
- **Download URL:** https://archive.ics.uci.edu/static/public/352/online+retail.zip
  (ZIP containing `Online Retail.xlsx`, 22.6 MB)
- **DOI:** https://doi.org/10.24432/C5BW33
- **Licence / attribution:** **CC BY 4.0** — Chen, D. (2015). Online Retail
  [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33
- **Fetch date (UTC):** 2026-11-14T14:19:41Z — one GET, no key, no account
- **Coverage:** 541,909 instances, 8 variables, as stated on the dataset page
- **Confirmed date range (from the file):** 2010-12-01 08:26 → 2011-12-09 12:50

## Fetch outcome

- ZIP downloaded (23,715,478 bytes), XLSX opens with `openpyxl`.
- Verified after fetch: row count **541,909** (matches the dataset page),
  **8 columns** with the exact names `InvoiceNo, StockCode, Description,
  Quantity, InvoiceDate, UnitPrice, CustomerID, Country`.
- Missing values in the raw file: Description 1,454 rows; CustomerID 135,080
  rows. No unparseable `InvoiceDate` values (0).

## Row counts and coverage

Cleaning applied in this order (plan §3.2); every step's excluded-row count is
recorded in `data/processed/data_source.json`:

| Step | Rows excluded | Running total |
|---|---|---|
| Raw rows | — | 541,909 |
| Unparseable `InvoiceDate` | 0 | 541,909 |
| Cancellations (`InvoiceNo` starts `C`) | 9,288 (3,836 invoices) | 532,621 |
| Non-positive `Quantity` (≤ 0) | 1,336 | 531,285 |
| Non-positive `UnitPrice` (≤ 0) | 1,181 | 530,104 |
| Postage / adjustment lines | 2,309 | 527,795 |
| Missing `Description` | 0 | 527,795 |
| **Cleaned rows** | | **527,795** |

Cleaned set: **527,795** transaction lines, **19,776 orders**, **4,334 identified
customers**, **5,577,139 units**, total revenue **£10,283,243.98** (GBP,
Revenue = Quantity × UnitPrice).

Adjustment lines removed (StockCodes): `POST, DOT, M, D, BANK CHARGES, CRUK,
C2, AMAZONFEE`, plus gift-voucher codes with prefix `gift_0001_` (34 rows,
payment instruments, not merchandise — added after profiling, recorded in
`data_source.json`); and Descriptions `POSTAGE, DISCOUNT, MANUAL, BANK
CHARGES, AMAZON FEE, CRUK`.

**Missing CustomerID:** 131,455 cleaned rows (14.80% of revenue,
£1,522,177.33) have no CustomerID. They stay in the revenue / product /
country analysis and are excluded from RFM and clustering only.

## Series definitions

- **Monthly:** calendar months Dec 2010 → Nov 2011 are full months.
  **Dec 2011 is partial** (data end 2011-12-09, 9 days) — shown in
  `monthly_sales.csv` with `is_partial = True`, hatched in chart 01, and
  **excluded** from month-over-month growth. November 2011 is the peak month
  (£1,457,745.53); February 2011 is the low month (£508,952.87).
- **Weekly:** ISO weeks (Monday–Sunday); only weeks fully inside the data range
  are kept — **51 weeks**, 2010-12-06 → 2011-11-28. The partial first week
  (starts 2010-12-01, a Wednesday) and partial last week (ends 2011-12-09, a
  Friday) are dropped. Last full week (2011-11-28): £310,353.86. Maximum weekly
  revenue: £374,736.15.

## Product groups

Derived, not source categories: `product_group` = the first alphabetic word of
`Description`, uppercased. Top 10 groups reported individually, the rest as
`Other` (65.46% of revenue). Top groups: SET 7.35%, JUMBO 5.70%, RED 3.87%,
PAPER 3.44%, DOORMAT 3.16%, LUNCH 2.63%, REGENCY 2.59%, VINTAGE 2.33%,
WHITE 1.88%, PINK 1.59%. Full table in `data/processed/product_groups.csv`.

## RFM + clustering

- RFM per identified customer only (4,334 customers): Recency = days from the
  customer's last purchase to the dataset end (2011-12-09); Frequency = distinct
  orders; Monetary = total revenue.
- KMeans: features standardised (`StandardScaler`), **k = 4**, `random_state=42`,
  `n_init=10`. **Silhouette score: 0.6163** — well separated (no "weak
  separation" disclosure needed; the threshold was 0.15).
- Labels assigned from the fitted centroids after fitting: Champions (13
  customers, mean monetary £125,862.44), Big spenders (209, £12,265.65),
  Occasional buyers (3,046, £1,330.93), Lapsed (1,066, £475.91). Full table in
  `data/processed/cluster_summary.csv`; one row per customer in
  `data/processed/rfm_clusters.csv`.
- Descriptive segmentation, not a churn or lifetime-value model.

## Forecast

- Target: weekly revenue (51 full weeks). Horizon: **8 weeks ahead**
  (2011-12-05 → 2012-01-23).
- Exactly two methods: **naïve** (last observed weekly revenue) and
  **Holt-Winters, additive trend, no seasonality** (`statsmodels`
  `ExponentialSmoothing`, `trend="add"`, `seasonal=None`). No seasonality: one
  year of data cannot support a seasonal fit (statsmodels needs ≥ 2 cycles).
- Prediction intervals: residual bootstrap, seed 42, 1,000 paths — 80% and 95%.
- Backtest: two rolling origins (train ends 8 and 16 weeks before the end),
  8-week horizons, RMSE and MAE for both methods.

| Origin | Method | RMSE (£) | MAE (£) |
|---|---|---|---|
| 8 | Holt-Winters | 38,624.28 | 35,353.66 |
| 8 | Naïve | 51,795.73 | 42,772.54 |
| 16 | Holt-Winters | 72,384.76 | 49,943.63 |
| 16 | Naïve | 73,805.83 | 52,168.48 |

Mean RMSE: Holt-Winters **£55,504.52** vs naïve £62,800.78 — Holt-Winters is the
published forecast. The 8 published weeks total **£3,061,051.48**, rising from
£346,552.30 to £418,710.57 per week. Full forecast in
`data/processed/forecast.csv`; backtest in `data/processed/backtest.csv`.
- The forecast is a **trend extrapolation**, not a seasonal prediction: the
  December spike is visible in the history but is not modelled.

## Committed files

| File | Contents |
|---|---|
| `raw/sample_rows.json` | 1,000 cleaned rows (sample, with a provenance note) — the only raw-data artefact committed |
| `processed/data_source.json` | Source, URL, DOI, licence, fetch date, all counts above, cluster parameters + silhouette, forecast method + backtest metrics |
| `processed/monthly_sales.csv` | 13 rows (Dec 2010 → Dec 2011): month, revenue_gbp, units, orders, aov_gbp, customers, is_partial |
| `processed/weekly_revenue.csv` | 51 rows (full weeks): week_start, revenue_gbp, units, orders |
| `processed/country_sales.csv` | 38 rows (one per country): country, revenue_gbp, revenue_share, orders, aov_gbp, units |
| `processed/top_products.csv` | Top 20 SKUs: stock_code, description, revenue_gbp, revenue_share, units, orders |
| `processed/product_groups.csv` | 11 rows (top 10 groups + Other): product_group, revenue_gbp, revenue_share, units, skus |
| `processed/rfm_clusters.csv` | 4,334 rows (one per identified customer): customer_id, recency_days, frequency, monetary_gbp, cluster, cluster_label |
| `processed/cluster_summary.csv` | 4 rows (one per cluster): cluster, label, n_customers, share_customers, share_revenue, mean_recency, mean_frequency, mean_monetary |
| `processed/forecast.csv` | 8 rows: week_start, forecast_gbp, lo_80, hi_80, lo_95, hi_95 |
| `processed/backtest.csv` | 4 rows (2 origins × 2 methods): origin, method, rmse, mae |

## Commit rule for data files

- **Data-size exception (plan §3.4, Day 8 precedent):** the raw XLSX (22.6 MB)
  is over the portfolio rule (files < 1 MB each, < 5 MB per day folder), so
  `data/raw/online_retail.zip` and `data/raw/Online Retail.xlsx` are
  git-ignored and re-downloaded at build time by
  `python -m src.data_pipeline --live`. They must not be on disk at handoff.
  Synthetic fallback output (`data/raw/*_synthetic.csv`) is also git-ignored
  and must never overwrite real data.
- Committed `data/` total: **467 KB** (< 5 MB); no committed file > 1 MB
  (largest: `raw/sample_rows.json`, 302,406 bytes).
- The pipeline regenerates everything from the live URL (`--live`) or from the
  committed processed CSVs (`--offline`, no network, no raw file needed).
  `--offline` does **not** clobber the live-run fields in `data_source.json`
  (source, counts, fetch date) — a test asserts this, using tolerance-based
  float comparison (Day 9 CI lesson: absolute ≤ 0.01 on GBP values, never
  byte-exact).

## Manual validation (one metric, by hand)

**Coder's hand validation, 2026-11-14.** Total revenue was recomputed
independently from the committed `data/processed/monthly_sales.csv` (summing
its 13 `revenue_gbp` values by hand from the CSV, not from the pipeline's own
output):

778,008.36 + 671,992.41 + 508,952.87 + 691,265.94 + 516,339.79 + 741,275.74 +
738,876.88 + 689,397.74 + 736,667.22 + 1,030,500.36 + 1,106,719.54 +
1,457,745.53 + 615,501.60 = **£10,283,243.98** — exactly equal to the total
recorded in `data_source.json` (difference **£0.00**).

Cross-checks from the committed CSVs: sum of `country_sales.csv`
`revenue_gbp` = £10,283,243.98 (exact); top-10 SKU revenue
(£967,969.90) / total = 9.41% (matches `data_source.json`); repeat rate
recomputed from `rfm_clusters.csv` (2,829 of 4,334 customers with frequency
≥ 2) = 65.27%; AOV = £10,283,243.98 / 19,776 = £519.99. The tester re-validates
one metric independently in `test_report.md`.

## Versions used for this build

- Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
  nbformat 5.11.1, scikit-learn 1.9.1, scipy 1.18.1, statsmodels 0.15.0,
  openpyxl 3.1.5 (see `requirements.txt` for the pinned list).
- Playwright 1.55.0 (screenshot capture only — not in `requirements.txt`).
- black 26.10.1, ruff 0.17.4 (lint/format only — pinned in the portfolio-root
  `requirements-dev.txt`).
