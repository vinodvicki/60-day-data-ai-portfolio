# Day 10 — Retail Sales Intelligence Dashboard: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-14) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Measure revenue, units, product mix, regional
variation, and seasonal performance to spot opportunities. GitHub deliverable:
Sales KPI dashboard plus three commercial recommendations. Core skills: SQL,
Power BI, clustering, demand forecasting. Suggested data: UCI Online Retail or
other public transactional retail data."
Section context (Days 10–12, Retail & E-Commerce).

| Item | Value |
|---|---|
| Fetch date | 2026-11-14 |
| Source | UCI Online Retail, dataset 352, DOI 10.24432/C5BW33, CC BY 4.0 — `https://archive.ics.uci.edu/static/public/352/online+retail.zip` (HTTP 200 verified) |
| Expected rows | **541,909 rows**, 8 columns (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country) |
| Date range | Stated 2010-12-01 → 2011-12-09 in the dataset documentation — **coder confirms from the file** and records the confirmed range |
| Deliverable | Sales KPI dashboard + **exactly three commercial recommendations**, each tied to a measured number |
| Scope | Analytical exercise on public historical retail transactions (2010–2011). **Not a current-market or forward-trading tool.** All revenue in GBP. |

## 1. Problem statement + audience

**Problem.** A UK online retailer has a year of transaction data and three
linked questions: *where does the money actually come from* (revenue,
units, product mix, countries, seasons), *who are the customers*
(recency / frequency / monetary value, and which groups behave alike),
and *what should the next quarter look like* (a near-term demand forecast
with honest uncertainty, plus three commercial actions worth taking)?
The dataset is famous and messy in exactly the ways real retail data is
messy — cancelled orders, negative quantities, missing customer IDs,
postage and adjustment lines mixed in with real products, no category
column — so the cleaning rules are part of the deliverable, not a
footnote: every exclusion is counted, and every number in the dashboard
traces to the cleaned transaction set defined in §3.2. The analysis is
honest about its limits up front: the data cover one retailer over one
year (2010–2011), so seasonality is observed, not estimated from
multiple years; the forecast is a trend extrapolation with bootstrap
intervals, not a seasonal model; and the recommendations are commercial
judgements grounded in measured numbers, not measured effects.

**Audience / decision-maker.** A data analyst or hiring reviewer who wants
to see retail analytics done properly on real transactional data: a
documented cleaning pipeline with counted exclusions, KPIs with stated
definitions and denominators, product mix and regional variation shown
with shares (not just ranks), customer clustering from RFM with a
silhouette check (not vibes), a forecast with a baseline it must beat
and a backtest, and three recommendations that each name their evidence,
their action, and their expected effect in measured terms.

## 2. Research questions (exactly 3)

1. **Where does the revenue come from?** Total revenue, units, orders,
   AOV, unique customers and repeat rate (§4.1); monthly revenue/units
   with month-over-month growth and the December peak quantified;
   product mix (top 10 SKUs by revenue and by units, keyword-derived
   product groups, concentration of the top 10); regional variation
   (revenue/orders/AOV by country, UK share, non-UK vs UK AOV).
2. **Who are the customers, and which groups behave alike?** RFM per
   identified customer (recency to the dataset end, frequency = orders,
   monetary = revenue), standardised, KMeans k = 4 (§4.3) with a
   silhouette score; cluster sizes, centroid RFM values and a
   plain-language label per cluster; the share of revenue each cluster
   contributes; the share of transactions with no CustomerID excluded
   from this question, reported, not hidden.
3. **What demand is coming next, and what should the business do about
   it?** An 8-week-ahead weekly-revenue forecast with 80% and 95%
   prediction intervals from the method that wins the backtest (§4.4),
   plus **exactly three commercial recommendations** (§4.5), each with
   evidence → action → expected effect in measured terms.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** UCI Machine Learning Repository, dataset **"Online Retail"**,
  dataset ID **352**, DOI `10.24432/C5BW33`, Chen (2015). Dataset page
  `https://archive.ics.uci.edu/dataset/352/online+retail`.
- **Download (verified 2026-11-14, HTTP 200):**
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  — a ZIP containing `Online Retail.xlsx` (**22.6 MB** per the dataset
  page). No key, no account, no documented rate limit; one single
  download is the whole fetch. On HTTP failure, wait 60 s, retry once,
  then stop and report.
- **Coverage verified from the dataset page:** **541,909 instances**,
  8 variables. Stated range 2010-12-01 → 2011-12-09 — coder confirms
  from the file and records the confirmed range in `data_source.json`
  and `data/README.md`.
- **Fields (8):** `InvoiceNo` (string; cancellations start with `C`),
  `StockCode` (string), `Description` (string), `Quantity` (int),
  `InvoiceDate` (datetime), `UnitPrice` (float, GBP), `CustomerID`
  (float/int, missing on some rows), `Country` (string).
- **Licence / attribution:** **CC BY 4.0** (stated on the dataset page).
  Cite verbatim in `data/README.md`, the notebook and the day README:
  > Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning
  > Repository. https://doi.org/10.24432/C5BW33

### 3.2 Cleaning rules (frozen — the tester tests these)

Applied in this order; every step's excluded-row count is recorded in
`data_source.json` and reported in `data/README.md`:

1. **Parse:** read the XLSX with `pandas.read_excel(engine="openpyxl")`
   (one sheet, `Online Retail`). Parse `InvoiceDate` to datetime.
   Drop rows where `InvoiceDate` is unparseable (count them; expected 0).
2. **Cancellations:** rows whose `InvoiceNo` starts with `C` are
   cancellations. Count them separately (`n_cancelled_invoices`,
   `n_cancelled_rows`) and **exclude** them from all revenue analysis.
3. **Non-positive quantity:** after removing cancellations, drop rows
   with `Quantity <= 0` (count them — these are returns/adjustments
   without a `C` prefix). Revenue rows must have `Quantity > 0`.
4. **Non-positive price:** drop rows with `UnitPrice <= 0` (count them).
5. **Non-product adjustment lines:** drop rows whose `StockCode` is in
   the adjustment list — `POST`, `DOT`, `M`, `D`, `BANK CHARGES`, `CRUK`,
   `C2`, `AMAZONFEE` — **plus** any row whose `Description` (uppercased,
   stripped) is in `{"POSTAGE", "DISCOUNT", "MANUAL", "BANK CHARGES",
   "AMAZON FEE", "CRUK"}`. The coder profiles the actual distinct
   `StockCode`/`Description` values first: if a code on this list does
   not occur, it is simply recorded as 0; if an *additional* adjustment
   code occurs (e.g. a `gift_0001_*` code or an all-caps non-product
   description), the coder adds it to the list **only** if it is plainly
   non-product, records the addition in `data_source.json`, and does
   not silently drop any code that looks like a real product. The final
   list is frozen in `data_source.json`.
6. **Missing description:** drop rows with missing/blank `Description`
   (count them; expected small).
7. **Revenue:** `line_revenue = Quantity × UnitPrice` (GBP) on the
   cleaned set. No currency conversion, no tax adjustment (the dataset
   does not state whether prices include VAT — disclosed as a limitation).
8. **Customer-level scope:** rows with missing `CustomerID` stay in the
   revenue/product/country analysis but are **excluded** from RFM and
   clustering. Report the excluded share of revenue and of orders.
9. **Monthly series:** calendar months Dec 2010 → Nov 2011 are full
   months; **Dec 2011 is partial** (data end 2011-12-09, 9 days) —
   shown in charts/tables flagged "PARTIAL (9 days)" and **excluded**
   from month-over-month growth. Monthly revenue/units/orders are
   computed from the cleaned set.
10. **Weekly series (forecast target):** ISO weeks (Monday–Sunday).
    Keep only **full weeks** fully inside the data range; drop the
    partial first week (starts 2010-12-01, a Wednesday) and the partial
    last week (ends 2011-12-09, a Friday). Record the kept week count
    (expected 51) and the dropped weeks in `data_source.json`.

### 3.3 Fetch rules

- One `GET` per build; unzip under `data/raw/` and re-use it
  (`--offline` / `--use-cache` per the Day 1 pattern). One retry after
  60 s on HTTP 429/5xx, then stop and report — never hammer the host.
- Verify after fetch: ZIP downloads, XLSX opens, row count = 541,909,
  8 columns with the exact names in §3.1. Record the verified counts in
  `data_source.json`. If a count differs, report it — do not silently
  proceed.

### 3.4 Data-size exception and commit rule (READ CAREFULLY — Day 8 precedent)

- The raw XLSX is **22.6 MB** — far over the portfolio rule (files
  < 1 MB each, < 5 MB per day folder). Therefore the **DATA-SIZE
  EXCEPTION** applies to this day only (same mechanism as Day 8's
  19 MB CSV):
  - **`.gitignore` MUST exclude the raw data:** `data/raw/online_retail.zip`,
    `data/raw/Online Retail.xlsx`, `data/raw/*_synthetic.csv`
    (synthetic fallback is always git-ignored). This is the one
    deliberate deviation from the "do NOT ignore `data/`" rule (Day 1
    lesson (d)) — the exception is forced by size and is recorded here,
    in `data/README.md`, and in the insights summary.
  - **The pipeline downloads the raw at build time** (`--live`),
    verifies the counts in §3.3, and caches it under `data/raw/` for
    re-use (`--use-cache`). `--offline` runs from the committed
    processed files only (no network, no raw needed) and regenerates
    charts + summaries from them.
  - **Committed provenance artefacts (small, the reproducibility
    record):** `data/raw/sample_rows.json` (1,000 cleaned rows, clearly
    labelled as a sample) and the compact processed files in §3.5.
    Expected `data/` total < 5 MB, no committed file > 1 MB.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the three raw-data lines above. The
  tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Source, URL, DOI, licence, fetch date, row counts (raw / cleaned / cancelled / excluded per rule), confirmed date range, adjustment-code list, monthly + weekly series definitions, RFM/cluster parameters (k, seed, silhouette), forecast method + backtest metrics, recommendation list |
| `data/processed/monthly_sales.csv` | 13 rows (Dec 2010 → Dec 2011): `month`, `revenue_gbp`, `units`, `orders`, `aov_gbp`, `customers`, `is_partial` |
| `data/processed/weekly_revenue.csv` | ~51 rows: `week_start`, `revenue_gbp`, `units`, `orders` (full weeks only) |
| `data/processed/country_sales.csv` | One row per country: `country`, `revenue_gbp`, `revenue_share`, `orders`, `aov_gbp`, `units` |
| `data/processed/top_products.csv` | Top 20 SKUs: `stock_code`, `description`, `revenue_gbp`, `revenue_share`, `units`, `orders` |
| `data/processed/product_groups.csv` | One row per derived product group (§4.2): `product_group`, `revenue_gbp`, `revenue_share`, `units`, `skus` |
| `data/processed/rfm_clusters.csv` | One row per identified customer: `customer_id`, `recency_days`, `frequency`, `monetary_gbp`, `cluster`, `cluster_label` |
| `data/processed/cluster_summary.csv` | One row per cluster: `cluster`, `label`, `n_customers`, `share_customers`, `share_revenue`, `mean_recency`, `mean_frequency`, `mean_monetary` |
| `data/processed/forecast.csv` | 8 rows: `week_start`, `forecast_gbp`, `lo_80`, `hi_80`, `lo_95`, `hi_95` (published forecast; method named in `data_source.json`) |
| `data/processed/backtest.csv` | One row per origin × method: `origin`, `method`, `rmse`, `mae` |

- The full raw XLSX is **not** committed (size). It is rebuilt by
  `python -m src.data_pipeline --live` from the live URL, and the
  notebook re-runs the forecast from it when present (§6, notebook
  rule). The committed processed CSVs are the offline-reproducible
  record: every number in the README, insights and dashboard must match
  them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date). It regenerates only the derived tables/charts
  from the committed CSVs; a test asserts this. **CI-flake lesson
  (Day 9, 2026-11-13):** the offline-reproduction test compares
  regenerated floats with a **tolerance** (absolute ≤ 0.01 on GBP
  values, relative ≤ 1e-6 elsewhere) — never byte-exact — because
  environment rounding flakes byte comparisons.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if a live download fails):** per brief §4 —
  12 months, ~40,000 orders, 5 countries, 200 SKUs, lognormal basket
  sizes, December uplift ×1.8, seed 42. File
  `data/raw/online_retail_synthetic.csv` (git-ignored, NEVER overwrites
  real data); `data_source.json` records `synthetic: true, seed: 42`;
  README, dashboard, notebook, insights and every chart all carry a
  "SYNTHETIC — NOT REAL DATA" banner if it is used. Methods (§4) are
  unchanged. Not expected to be needed (probe HTTP 200).
- **Licence: CC BY 4.0.** Attribution verbatim in README.md,
  data/README.md, the notebook and the dashboard footer (§3.1).

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 KPIs (defined once, used everywhere)

Computed on the cleaned set (§3.2), all revenue in GBP:

| KPI | Definition |
|---|---|
| Total revenue | Σ `line_revenue` over cleaned rows |
| Total units | Σ `Quantity` over cleaned rows |
| Orders | Distinct non-cancelled `InvoiceNo` in the cleaned set |
| Average order value (AOV) | Total revenue / orders |
| Unique customers | Distinct non-missing `CustomerID` |
| Repeat-customer rate | Customers with ≥ 2 orders / all customers (identified only) |
| Revenue per customer | Total revenue from identified customers / unique customers |
| Top-10 SKU concentration | Revenue share of the top 10 SKUs by revenue |
| UK share | UK revenue / total revenue |

### 4.2 Product mix (DECIDED — brief open item: grouping rule)

- **Top SKUs:** top 20 by revenue (and top 10 by units, reported in the
  notebook) from the cleaned set; `top_products.csv` carries the top 20.
- **Product group (derived, not source data):** `product_group` = the
  **first alphabetic word of `Description`**, uppercased (e.g. `JUMBO`,
  `MUG`, `LUNCH`, `HEART`). Groups are ranked by revenue; the top 10
  groups are reported individually and the rest are aggregated as
  `Other` in `product_groups.csv`. The rule is data-driven (no invented
  taxonomy) and is stated as derived in every surface that uses it.
  The coder records the top-10 group list in `data_source.json`.
- **Concentration:** report the revenue share of the top 10 SKUs and of
  the top product group; the dashboard shows both as "concentration"
  callouts.

### 4.3 Customer clustering (DECIDED — roadmap "clustering" skill)

- **RFM per identified customer** (missing `CustomerID` excluded, §3.2
  rule 8): Recency = days from the customer's last purchase to the
  dataset end date (max `InvoiceDate`); Frequency = distinct orders;
  Monetary = total revenue. Computed on the cleaned set.
- **KMeans:** features standardised (`StandardScaler`), **k = 4**,
  `random_state=42`, `n_init=10`. No tuning grid. Report the
  **silhouette score**; if it is below 0.15, disclose "weak separation"
  in the notebook, insights and dashboard — do not re-cut k to chase a
  prettier score.
- **Labels:** plain-language labels assigned from the cluster centroids
  after fitting (e.g. "Champions", "Loyal regulars", "At-risk
  lapsed", "One-off browsers" — the coder picks the labels from the
  actual centroids and records them; the labels describe the centroids,
  they are not pre-assigned). Each cluster reports size, share of
  customers, share of revenue, and mean R/F/M (`cluster_summary.csv`).
- **Scope note:** this is descriptive segmentation, not a churn or
  lifetime-value model. Say so in the notebook and insights.

### 4.4 Demand forecast (DECIDED — roadmap "demand forecasting" skill)

- **Target:** weekly revenue (`weekly_revenue.csv`, ~51 full weeks).
- **Horizon:** **8 weeks ahead** from the last full week.
- **Methods (exactly two, no tuning grid):**
  1. **Naïve (baseline):** forecast for every future week = the last
     observed weekly revenue. No parameters, no fitting.
  2. **Holt-Winters, additive trend, NO seasonality:**
     `statsmodels.tsa.holtwinters.ExponentialSmoothing` with
     `trend="add"`, `seasonal=None`, fixed — no grid search. **Why no
     seasonality: the series covers a single year, so a seasonal
     component with period 52 cannot be estimated from one cycle**
     (statsmodels requires ≥ 2 cycles for a seasonal fit); the December
     spike is visible in the history and is discussed, but the forecast
     does not model it. This limitation is disclosed in the notebook,
     insights, README and dashboard — the forecast is a trend
     extrapolation, not a seasonal prediction.
- **Prediction intervals:** residual bootstrap for the published method
  (seed 42, 1,000 bootstrap paths), 80% and 95% intervals, same
  procedure as Day 9 (§4.3 of the Day 9 plan).
- **Backtest (fixed):** two rolling origins — train ends 8 weeks and
  16 weeks before the end of the weekly series, forecast **8 weeks**
  each; both methods at each origin; metrics RMSE and MAE. The method
  with the **lowest mean backtest RMSE** is the published 8-week
  forecast; if naïve wins, publish naïve and say so.
- **Forecast CSV:** `forecast.csv`, 8 rows, with `lo_80` / `hi_80` /
  `lo_95` / `hi_95` per week.

### 4.5 Recommendations (DECIDED — structure; content follows the numbers)

Exactly **three** commercial recommendations, in `outputs/insights_summary.md`,
the dashboard and the README. Each has the fixed structure
**evidence → action → expected effect**, where the evidence is a measured
number from the committed CSVs and the expected effect is stated in
measured terms (e.g. "the top 10 SKUs are X% of revenue — protect
availability of those SKUs" with the X filled in from the data). The
coder drafts them from the computed numbers; the optimizer verifies each
evidence number against the committed CSVs. No fourth recommendation,
no recommendation without a number.

### 4.6 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `monthly_sales.csv` + `country_sales.csv` loaded into an
in-memory SQLite database (`sqlite3`, stdlib): monthly revenue by month
and the top-5 countries by revenue, asserted equal to the pandas result.
A test asserts the SQL and pandas numbers agree. This is the day's SQL
element; no `.pbix` is built (see §11) and the pipeline itself stays
pandas.

## 5. File tree (exact — build only this)

```
day-10-retail-sales-intelligence-dashboard/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   └── sample_rows.json        (1,000 cleaned rows, provenance sample)
│   └── processed/
│       ├── data_source.json
│       ├── monthly_sales.csv       (13 rows)
│       ├── weekly_revenue.csv      (~51 rows)
│       ├── country_sales.csv
│       ├── top_products.csv        (top 20 SKUs)
│       ├── product_groups.csv
│       ├── rfm_clusters.csv
│       ├── cluster_summary.csv
│       ├── forecast.csv            (8 rows)
│       └── backtest.csv
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── clustering.py
│   ├── forecast.py
│   ├── metrics.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_monthly_sales.png
│       ├── 02_product_country.png
│       ├── 03_rfm_clusters.png
│       └── 04_forecast.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No `data/raw/*.xlsx` or
`*.zip` on disk at handoff (git-ignored, §3.4). No extra modules, no
extra charts, no `.pbix`, no model card.

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download ZIP (1 retry after 60 s on 429/5xx then stop), unzip, read XLSX (`openpyxl`); verify counts 541,909 / 8 columns; apply cleaning rules §3.2 in order, counting every exclusion; build monthly (13 rows, Dec 2011 flagged partial), weekly (~51 full weeks), country, top-products, product-group tables; write `sample_rows.json`, the processed CSVs and `data_source.json`; modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42) |
| `src/metrics.py` | Pure functions, no I/O, no network — all tested: `line_revenue(qty, price)`, `aov(revenue, orders)`, `repeat_rate(frequencies)`, `revenue_share(part, total)`, `rmse(y, p)`, `mae(y, p)`, `month_over_month(values)` (skips partial months) |
| `src/clustering.py` | `build_rfm(df)` (identified customers only); `cluster_customers(rfm, k=4, seed=42)` (StandardScaler + KMeans, returns labels + silhouette); `summarise_clusters(rfm, labels)` → `cluster_summary.csv` rows; `assign_labels(summary)` from centroids (recorded, not pre-assigned) |
| `src/forecast.py` | `naive_forecast(series, horizon)`; `holt_winters_forecast(series, horizon)` (additive trend, no seasonality, fixed); `bootstrap_intervals(residuals, point, n_paths=1000, seed=42)` returning 80%/95% bands; `rolling_backtest(series, origins=(8, 16), horizon=8)` returning per-origin × method metrics; `build_forecast(...)` writing `forecast.csv`, `backtest.csv` |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source + CC BY 4.0 attribution + "historical 2010–2011 data — not a current-market tool" + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (revenue, units, orders, AOV, customers, repeat rate); monthly trend; product mix + concentration callouts; country table; RFM cluster panel; 8-week forecast with intervals; the three recommendations (§4.5) as a panel; methods + limitations panel; `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with CC BY 4.0 attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): EDA on the committed tables (cleaning audit, seasonality, product/country mix, RFM + silhouette); the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.6); **forecast section guarded by `RAW.exists()`** — if the raw XLSX is present it re-runs the forecast via `src.forecast` and asserts the metrics match the committed `backtest.csv` / `forecast.csv` within tolerance; if absent it loads the committed CSVs and prints a note that the forecast was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: revenue = Quantity × UnitPrice on fixtures; cancellation rows excluded (InvoiceNo `C…`); Quantity ≤ 0 and UnitPrice ≤ 0 excluded; adjustment StockCodes excluded; missing CustomerID excluded from RFM only (kept in revenue); monthly Dec 2011 flagged partial and excluded from MoM; weekly series keeps full weeks only; top-10 concentration sums correctly; RFM recency/frequency/monetary on fixtures; KMeans deterministic (same labels, seed 42) + silhouette in [−1, 1]; naïve forecast = last value; HW forecast length = horizon; bootstrap intervals contain the point forecast and widen with horizon; backtest origins are (8, 16) with horizon 8; offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.6) |
| `data/README.md` | Provenance: URL, DOI, CC BY 4.0 licence, fetch date, row counts (raw 541,909 / cleaned / excluded per rule), confirmed date range, adjustment-code list, monthly/weekly definitions (partial Dec 2011, full-weeks rule), RFM/cluster parameters + silhouette, forecast method + backtest metrics, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2 question with exact numbers + **exactly three commercial recommendations** (§4.5) + limitations (single-year seasonality, 2010–2011 data, prices VAT status unknown, product groups derived) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, the three recommendations, validation, limitations, attribution |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 9 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat, scikit-learn, scipy, statsmodels) **plus openpyxl** (new runtime dep for this day — XLSX reading). No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88); `.gitignore` per §3.4 (raw-data lines are the only data exclusions) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_retail_zip(url: str, dest: Path) -> Path
def load_raw_xlsx(path: Path) -> pd.DataFrame
def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def build_monthly_sales(df: pd.DataFrame) -> pd.DataFrame
def build_weekly_revenue(df: pd.DataFrame) -> pd.DataFrame
def build_country_sales(df: pd.DataFrame) -> pd.DataFrame
def build_top_products(df: pd.DataFrame, n: int = 20) -> pd.DataFrame
def build_product_groups(df: pd.DataFrame) -> pd.DataFrame
def write_data_source(path: Path, record: dict) -> None

# src/clustering.py
def build_rfm(df: pd.DataFrame) -> pd.DataFrame
def cluster_customers(rfm: pd.DataFrame, k: int = 4, seed: int = 42) -> tuple[np.ndarray, float]
def summarise_clusters(rfm: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame

# src/forecast.py
def naive_forecast(series: pd.Series, horizon: int = 8) -> np.ndarray
def holt_winters_forecast(series: pd.Series, horizon: int = 8) -> tuple[np.ndarray, object]
def bootstrap_intervals(residuals: np.ndarray, point: np.ndarray,
                        n_paths: int = 1000, seed: int = 42) -> dict
def rolling_backtest(series: pd.Series, origins: tuple = (8, 16),
                     horizon: int = 8) -> pd.DataFrame

# src/metrics.py
def line_revenue(quantity, unit_price) -> float
def aov(revenue: float, orders: int) -> float
def repeat_rate(frequencies) -> float
def revenue_share(part: float, total: float) -> float
def rmse(y_true, y_pred) -> float
def mae(y_true, y_pred) -> float
def month_over_month(values: list[float]) -> list[float | None]
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units (GBP), source footnote
("Source: UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 —
historical 2010–2011 data, not a current-market tool"), no truncated
axes, legible at 100% zoom.

1. **01_monthly_sales.png** — Two panels: (a) monthly revenue bars with
   the December 2010 peak and the partial Dec 2011 bar hatched/flagged;
   (b) monthly orders line + AOV line (twin axis, labelled). Answers Q1's
   seasonality half.
2. **02_product_country.png** — Two panels: (a) top 10 SKUs by revenue,
   horizontal bars with values and revenue-share labels; (b) top 10
   countries by revenue, horizontal bars with values + UK share callout.
   Answers Q1's product-mix and regional halves.
3. **03_rfm_clusters.png** — Two panels: (a) RFM scatter — Recency (days)
   vs Monetary (GBP, log scale, labelled) coloured by cluster with the
   cluster labels in the legend; (b) cluster profile bars — mean monetary
   per cluster with customer counts annotated. Answers Q2.
4. **04_forecast.png** — Two panels: (a) weekly revenue history (~51
   weeks) + 8-week published forecast with shaded 80% and 95% prediction
   intervals; (b) backtest RMSE by origin for Holt-Winters vs naïve
   (grouped bars, lower is better) with the winning method named in the
   title. Answers Q3's forecast half.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–9 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URL, DOI, licence (CC BY 4.0,
      verbatim attribution), fetch date (2026-11-14), row counts (raw
      541,909 / cleaned / excluded per rule), confirmed date range — in
      `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → clean → aggregate →
      cluster → backtest → forecast → charts, with `--offline` mode) +
      KPI definitions (§4.1) written down
- [ ] **Sales KPI dashboard + three commercial recommendations delivered**
      (roadmap deliverable): KPIs, monthly/product/country/cluster panels
      and the three recommendations in the dashboard, charts and insights
- [ ] **Product mix, regional variation and seasonality measured**: top
      SKUs + derived product groups + concentration; country revenue /
      orders / AOV with UK share; monthly revenue/units/orders with MoM
      growth and the December peak quantified
- [ ] **Clustering done**: RFM per identified customer, KMeans k = 4,
      silhouette reported, cluster sizes/centroids/revenue shares in
      `cluster_summary.csv`; labels derived from centroids
- [ ] **Demand forecast delivered**: 8-week weekly-revenue forecast with
      80% and 95% prediction intervals (residual bootstrap, seed 42,
      1,000 paths) from the lower-backtest-RMSE method; backtest at 2
      rolling origins (8 / 16 weeks, 8-week horizons) with RMSE/MAE for
      both methods; single-year seasonality limitation disclosed
- [ ] **SQL check done** (§4.6): monthly revenue + top-5 countries via
      SQLite asserted equal to pandas, in the notebook and a test
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2 question with exact numbers) + **exactly three** commercial
      recommendations (§4.5)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; **data-size exception
      honoured** (no file > 1 MB, `data/` < 5 MB; raw ZIP/XLSX
      git-ignored per §3.4 and absent at handoff; `.gitignore` matches
      §5/§6)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. total
      revenue or the top SKU's revenue — from the committed CSVs,
      matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert, with `_find_root()` and the guarded forecast section, §6)
- [ ] Pinned dependencies in `requirements.txt` (incl. openpyxl);
      `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and
      on `/_stcore/health`, **real `screenshots/dashboard.png`** captured,
      server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes (≥ 15 tests)
- [ ] `.gitignore` matches §3.4/§5 (raw ZIP/XLSX + synthetic excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+)
- [ ] `data/` total < 5 MB, no file > 1 MB; no raw ZIP/XLSX on disk at handoff (git-ignored); `data_source.json` records live counts, cleaning exclusions, cluster parameters + silhouette, backtest results
- [ ] Counts verified against §3.3 (541,909 rows, 8 columns); confirmed date range recorded; Dec 2011 partial flagged; full-weeks count recorded
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Build only what §5 lists; no extra web searches

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| ZIP/XLSX download fails or is truncated | 1 retry after 60 s, then stop and report; synthetic fallback (§3.6) only if live fails |
| Row count ≠ 541,909 or columns differ | Verify after fetch (§3.3); report, do not silently proceed |
| Adjustment codes list misses a real non-product code (or drops a real product) | Coder profiles distinct codes first; additions only for plainly non-product codes, recorded in `data_source.json` (§3.2 rule 5) |
| Missing CustomerID biases the customer analysis | Identified-only RFM/clustering with the excluded share reported (§3.2 rule 8, §4.3) |
| December 2011 partial month distorts MoM/seasonality | Flagged partial, excluded from MoM growth (§3.2 rule 9) |
| Holt-Winters seasonal fit impossible on 1 year of data | Trend-only Holt-Winters, disclosed (§4.4) — no silent seasonal substitute |
| KMeans clusters weakly separated | Silhouette reported; < 0.15 disclosed as weak separation (§4.3) |
| Product groups derived from free text look like source categories | Rule is first-word, stated as derived on every surface (§4.2) |
| Prices may or may not include VAT | Disclosed as a limitation (dataset does not state it) |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text |

## 11. Differences from the brief (plan wins)

- **Product-group rule (§4.2):** the brief (§2, §6 item 1) left the
  grouping rule open ("keyword-derived product groups"); the plan
  **fixes** first-alphabetic-word of `Description`, top 10 reported,
  rest as `Other`, stated as derived.
- **KMeans k (§4.3):** the brief left k provisional at 4 pending the
  silhouette check; the plan **fixes** k = 4 with the silhouette
  reported and a < 0.15 "weak separation" disclosure — no re-cutting k.
- **Cleaning rules (§3.2):** the brief listed expected quirks; the plan
  **fixes** the ordered rules, the adjustment-code list, the
  missing-CustomerID scope, the partial-month rule and the full-weeks
  rule, with every exclusion counted.
- **Forecast design (§4.4):** the brief sketched monthly Holt-Winters
  with period 12; the plan **fixes** the weekly-revenue target
  (~51 full weeks), 8-week horizon, trend-only Holt-Winters (no
  seasonality — one year cannot support a seasonal fit), naïve baseline,
  and a 2-origin × 8-week backtest. The monthly series stays as the
  seasonality *display* (chart 01), not the forecast target.
- **Data-size exception (§3.4):** the brief (§6 item 3) asked the
  planner to decide; the plan **fixes** the exception — raw ZIP/XLSX
  git-ignored and re-downloaded at build (Day 8 precedent), committed
  provenance = `sample_rows.json` (1,000 cleaned rows) + processed
  CSVs + `data_source.json`, `data/` < 5 MB, no file > 1 MB.
- **Recommendations (§4.5):** the brief (§6 item 4) left the structure
  open; the plan **fixes** exactly three, each evidence → action →
  expected effect, each evidence number verified against the committed
  CSVs.
- **Power BI:** the roadmap's section-level core skills list Power BI,
  but the Day 10 deliverable is the "sales KPI dashboard plus three
  commercial recommendations". No `.pbix` is built (same decision as
  Days 8–9 — a `.pbix` cannot be built or verified in this environment);
  the Streamlit dashboard + 4 static charts are the deliverables. The
  SQL skill is covered by the §4.6 check.
- **Notebook forecast (§6):** the brief did not specify notebook
  mechanics; the plan adds the guarded forecast section (re-runs the
  forecast when the raw XLSX is present, otherwise loads committed
  CSVs — 0 errors either way).
- **CI flake (§3.5):** the Day 9 CI flake (byte-exact CSV comparison)
  is addressed here by mandating tolerance-based comparison in the
  offline-reproduction test.

## 12. Build order

1. `src/data_pipeline.py` — download ZIP → unzip → read XLSX →
   verify counts → clean (§3.2, exclusions counted) → monthly /
   weekly / country / top-products / product-group tables →
   `sample_rows.json` + processed CSVs + `data_source.json` (live run;
   cache raw).
2. `src/metrics.py` + `src/clustering.py` + `src/forecast.py` — pure
   metrics; RFM + KMeans k = 4 + silhouette → `rfm_clusters.csv`,
   `cluster_summary.csv`; naïve + trend-only Holt-Winters + bootstrap
   intervals + 2-origin backtest → `forecast.csv`, `backtest.csv`.
3. `src/make_charts.py` — 4 charts from the processed CSVs.
4. `notebooks/analysis.ipynb` — EDA + Q1–Q3 + SQL check + guarded
   forecast section; run via nbconvert, 0 errors.
5. `src/app.py` — Streamlit dashboard from processed CSVs only; smoke
   test on a fresh port (8502+) + real `screenshots/dashboard.png`.
6. `tests/test_pipeline.py` — ≥ 15 tests (§6); delete
   `tests/test_smoke.py`; `pytest`, `black`, `ruff`; coder handoff
   checklist (§9).
7. Docs — `README.md`, `data/README.md`, `outputs/insights_summary.md`;
   every number checked against the committed processed CSVs.
