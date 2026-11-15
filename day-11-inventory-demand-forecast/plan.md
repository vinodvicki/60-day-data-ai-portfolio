# Day 11 — Inventory Demand Forecast: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-15) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Inventory Demand Forecast. Sector: Retail &
Supermarkets. Problem: Predict near-term item demand and evaluate simple
baselines versus ML models to help reduce stockouts. GitHub deliverable:
SKU-level forecast and proposed reorder list. Core skills: SQL, Power BI,
clustering, demand forecasting. Suggested data: UCI Online Retail or other
public transactional retail data."
Section context (Days 10–12, Retail & E-Commerce).

| Item | Value |
|---|---|
| Fetch date | 2026-11-15 |
| Source | UCI Online Retail, dataset 352, DOI 10.24432/C5BW33, CC BY 4.0 — `https://archive.ics.uci.edu/static/public/352/online+retail.zip` (HTTP 200 verified) |
| Expected rows | **541,909 rows**, 8 columns (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country) |
| Date range | Stated 2010-12-01 → 2011-12-09 in the dataset documentation — **coder confirms from the file** and records the confirmed range |
| Deliverable | SKU-level forecast (top 20 SKUs + aggregate) plus a proposed reorder list |
| Scope | Analytical exercise on public historical retail transactions (2010–2011). **Not a current-market or forward-trading tool.** Demand is counted in **units**; revenue (GBP) is used only to rank SKUs. |

## 1. Problem statement + audience

**Problem.** A UK online retailer needs to know, for each of its key
products, how much will sell over the next 4 weeks — and what to reorder
now to avoid stockouts without over-stocking slow lines. The catalogue
has roughly 4,000 StockCodes, but demand is heavily concentrated, and
most of the long tail is intermittent (many zero weeks), so forecasting
every SKU individually would produce noise presented as precision. This
project therefore forecasts the top 20 SKUs by revenue individually plus
one aggregate series, compares simple baselines against an
intermittent-demand method, exponential smoothing and gradient boosting
on the same 4-week holdout, picks the winner **per demand-pattern
cluster** (not one global winner), and turns the winning forecasts into
a labelled, assumption-based reorder list. The dataset is the same messy
real retail data as Day 10 — cancelled orders, negative quantities,
missing customer IDs, postage and adjustment lines mixed in with real
products, no category, lead-time or inventory column — so the cleaning
rules are part of the deliverable: every exclusion is counted, and every
number traces to the cleaned weekly demand series defined in §3.2/§4.1.

**Two hard limits are stated up front and labelled on every surface
(README, notebook, insights, dashboard, charts, reorder list):**

1. **The forecast is a trend extrapolation from one retailer over one
   year — NOT a seasonal prediction.** The weekly series is 52 weeks, a
   single cycle, so no seasonal component is fitted (see §4.3) and
   nothing is claimed beyond the 4-week horizon.
2. **Reorder quantities assume zero on-hand stock and a 1-week lead
   time.** The dataset contains no inventory levels and no lead times,
   so the reorder list publishes an order-up-to level `S` and the
   implied order "if starting from zero" (see §4.5). No on-hand number
   is ever invented.

**Audience / decision-maker.** A retail inventory / buying manager
(non-technical reader of the README and the reorder list) who needs to
know what to order now, which lines to review manually, and how much to
trust each number — and a data reviewer checking the forecast method,
who wants a documented cleaning pipeline with counted exclusions, a
backtest the forecast must beat, per-cluster method choice with a stated
tie-break, and error metrics defined once and used everywhere.

## 2. Research questions (exactly 3)

1. **How much of each key product will sell over the next 4 weeks?**
   Weekly unit demand for the top 20 SKUs by revenue (§4.1) plus the
   aggregate series, forecast 4 weeks ahead from the method that wins
   each SKU's demand-pattern cluster (§4.3), with the forecast, the
   holdout actuals and the naïve baseline shown side by side.
2. **Which forecasting method actually works, and for what kind of
   demand?** Baselines (naïve, seasonal naïve, 4-week moving average)
   vs Croston-SBA, Holt ETS (trend, no seasonality) and
   HistGradientBoosting on lag features, scored on the same 4-week
   holdout with WAPE (primary), MAE, RMSE and bias (§4.4); demand
   pattern classified per SKU by Syntetos–Boylan ADI/CV² quadrants
   (§4.2) with a KMeans k = 4 cross-check; the winner is chosen per
   cluster, with the tie-break in §4.3.
3. **What should be reordered now?** A reorder list for the top 20 SKUs
   (§4.5) — forecast 4-week total, safety stock, reorder point,
   order-up-to level and implied order from zero on-hand, at the stated
   service level, with a stockout-risk / review-manually flag — plus
   **exactly three actionable recommendations** (§4.7), each tied to a
   measured number.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** UCI Machine Learning Repository, dataset **"Online Retail"**,
  dataset ID **352**, DOI `10.24432/C5BW33`, Chen (2015). Dataset page
  `https://archive.ics.uci.edu/dataset/352/online+retail`.
- **Download (verified 2026-11-15, HTTP 200):**
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  — a ZIP containing `Online Retail.xlsx` (**22.6 MB** per the dataset
  page; probe GET returned 23,715,478 bytes). No key, no account, no
  documented rate limit; one single download is the whole fetch. **The
  server ignores the Range header — the coder does one plain full
  download, not a ranged/resumable fetch.** On HTTP failure, wait 60 s,
  retry once, then stop and report.
- **Coverage verified from the dataset page:** **541,909 instances**,
  8 variables in the variables table. Stated range 2010-12-01 →
  2011-12-09 — coder confirms from the file and records the confirmed
  range in `data_source.json` and `data/README.md`. **Page
  inconsistency to record, not resolve by guessing:** the page header
  says "# Features 6" while the variables table lists 8 columns — the
  file itself is authoritative (Day 10 also found 8 columns).
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
`data_source.json` and reported in `data/README.md`. This is the same
ordered list as Day 10 §3.2, re-applied here because the raw file is the
same — the counts are re-derived from the file, not copied from Day 10:

1. **Parse:** read the XLSX with `pandas.read_excel(engine="openpyxl")`
   (one sheet, `Online Retail`). Parse `InvoiceDate` to datetime.
   Drop rows where `InvoiceDate` is unparseable (count them; expected 0).
2. **Cancellations:** rows whose `InvoiceNo` starts with `C` are
   cancellations. Count them separately (`n_cancelled_invoices`,
   `n_cancelled_rows`) and **exclude** them from all demand analysis.
3. **Non-positive quantity:** after removing cancellations, drop rows
   with `Quantity <= 0` (count them — these are returns/adjustments
   without a `C` prefix). Demand rows must have `Quantity > 0`.
4. **Non-positive price:** drop rows with `UnitPrice <= 0` (count them).
5. **Non-product adjustment lines:** drop rows whose `StockCode` is in
   the adjustment list — `POST`, `DOT`, `M`, `D`, `BANK CHARGES`, `CRUK`,
   `C2`, `AMAZONFEE` — **plus** any row whose `Description` (uppercased,
   stripped) is in `{"POSTAGE", "DISCOUNT", "MANUAL", "BANK CHARGES",
   "AMAZON FEE", "CRUK"}`. The coder profiles the actual distinct
   `StockCode`/`Description` values first: if a code on this list does
   not occur, it is simply recorded as 0; if an *additional* adjustment
   code occurs, the coder adds it to the list **only** if it is plainly
   non-product, records the addition in `data_source.json`, and does
   not silently drop any code that looks like a real product. The final
   list is frozen in `data_source.json`.
6. **Missing description:** drop rows with missing/blank `Description`
   (count them; expected small).
7. **Revenue (ranking only):** `line_revenue = Quantity × UnitPrice`
   (GBP) on the cleaned set. No currency conversion, no tax adjustment
   (the dataset does not state whether prices include VAT — disclosed as
   a limitation). **Demand is units; price plays no role in the
   forecast itself.**
8. **CustomerID scope:** rows with missing `CustomerID` stay in the
   demand analysis (demand is summed over all customers — do not filter
   on `CustomerID`). Report the missing share; it is irrelevant to SKU
   demand and is not an exclusion.
9. **Partial weeks:** rows whose `InvoiceDate` falls in the partial first
   week (2010-12-01 → 2010-12-05) or the partial last week (2011-12-05
   → 2011-12-09) are counted separately (`n_partial_week_rows`) and
   **excluded from the weekly demand series** (§4.1). They are in the
   cleaned set for the cleaning audit, but no weekly series, ranking,
   clustering or forecast uses them, so every downstream number traces
   to the same 52 full weeks.

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
  EXCEPTION** applies to this day only (same mechanism as Days 8–10):
  - **`.gitignore` MUST exclude the raw data:** `data/raw/online_retail.zip`,
    `data/raw/Online Retail.xlsx`, `data/raw/*_synthetic.csv`
    (synthetic fallback is always git-ignored). This is the one
    deliberate deviation from the "do NOT ignore `data/`" rule (Day 1
    lesson (d)) — the exception is forced by size and is recorded here,
    in `data/README.md`, and in the insights summary.
  - **`.gitignore` must NOT exclude `data/` itself** — only the three
    raw-data lines above. All processed files in §3.5 and the sample
    below are committed.
  - **The pipeline downloads the raw at build time** (`--live`),
    verifies the counts in §3.3, and caches it under `data/raw/` for
    re-use (`--use-cache`). `--offline` runs from the committed
    processed files only (no network, no raw needed) and regenerates
    charts + summaries from them.
  - **Committed provenance artefacts (small, the reproducibility
    record):** `data/raw/sample_rows.json` (**1,000 cleaned rows**,
    clearly labelled as a sample) and the compact processed files in
    §3.5. Expected `data/` total < 5 MB, no committed file > 1 MB.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the three raw-data lines above. The
  tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Source, URL, DOI, licence, fetch date, row counts (raw / cleaned / cancelled / excluded per rule / partial-week rows), confirmed date range, adjustment-code list, full-weeks definition (52 weeks), top-20 selection (ranking, replacements), clustering parameters + quadrant counts, methods + backtest metrics (per origin, per method, per cluster), winner per cluster + tie-break outcome, reorder assumptions (lead time, service levels, zero on-hand), manual validation, versions |
| `data/processed/weekly_demand.csv` | Long format, one row per top-20 SKU per full week (20 × 52 = 1,040 rows): `week_start`, `stock_code`, `description`, `units` |
| `data/processed/weekly_aggregate.csv` | 52 rows: `week_start`, `units` (total weekly units across all cleaned SKUs in full weeks) |
| `data/processed/sku_summary.csv` | One row per top-20 SKU: `stock_code`, `description`, `revenue_gbp`, `revenue_share`, `total_units`, `weeks_with_demand`, `mean_weekly_units`, `adi`, `cv2`, `cluster` |
| `data/processed/cluster_summary.csv` | One row per SBC quadrant (all SKUs with any demand): `cluster`, `n_skus`, `share_skus`, `share_units`, `mean_adi`, `mean_cv2` |
| `data/processed/forecast.csv` | Published 4-week forecast (cluster winner per SKU): 20 SKUs × 4 weeks + aggregate × 4 weeks = 84 rows: `week_start`, `stock_code`, `description`, `cluster`, `winning_method`, `forecast_units` |
| `data/processed/backtest.csv` | One row per origin × method × series (top 20 SKUs + aggregate): `origin`, `method`, `stock_code`, `wape`, `mae`, `rmse`, `bias` |
| `data/processed/reorder_list.csv` | 20 rows, one per top-20 SKU — columns fixed in §4.5 |

- The full raw XLSX is **not** committed (size). It is rebuilt by
  `python -m src.data_pipeline --live` from the live URL, and the
  notebook re-runs the forecast from it when present (§6, notebook
  rule). The committed processed CSVs are the offline-reproducible
  record: every number in the README, insights and dashboard must match
  them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date). It regenerates only the derived tables/charts
  from the committed CSVs; **a test asserts this — the offline run
  skips writing `data_source.json` entirely when a live record already
  exists.** **CI-flake lesson (Day 9, 2026-11-13):** the
  offline-reproduction test compares regenerated floats with a
  **tolerance** (absolute ≤ 0.01 on GBP values, relative ≤ 1e-6
  elsewhere) — never byte-exact — because environment rounding flakes
  byte comparisons.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if a live download fails):** per brief §5 —
  retry once after 60 s, then stop and report to the orchestrator —
  **do not silently substitute synthetic data**. If a synthetic
  fallback were ever authorised, it must be built from documented
  parameters (52 weeks, 20 SKUs with lognormal weekly demand, a
  December uplift, intermittent tail SKUs, seed 42), stored as
  `data/raw/*_synthetic.csv` (git-ignored, NEVER overwrites real data),
  recorded in `data_source.json` as `synthetic: true, seed: 42`, and
  labelled "SYNTHETIC — NOT REAL DATA" in every chart, the notebook,
  and the README. Methods (§4) are unchanged. Not expected to be needed
  (probe HTTP 200).
- **Licence: CC BY 4.0.** Attribution verbatim in README.md,
  data/README.md, the notebook and the dashboard footer (§3.1).
- **No Power BI file:** no `.pbix` is produced (same decision as
  Days 8–10 — a `.pbix` cannot be built or verified in this
  environment); the forecast is delivered as the Streamlit app + static
  charts. Recorded here so the coder does not re-litigate it. The SQL
  skill is covered by the §4.6 check.

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Weekly demand series + top-20 SKU selection (DECIDED)

- **Weekly demand (units):** summed cleaned `Quantity` per SKU per
  ISO week (Monday–Sunday, `InvoiceDate` floored to the Monday of its
  week). **Only full weeks fully inside the data range are kept:**
  week 1 starts Monday 2010-12-06, week 52 ends Sunday 2011-12-04 —
  **52 full weeks**. The partial first week (2010-12-01 → 2010-12-05)
  and the partial last week (2011-12-05 → 2011-12-09, only 5 trading
  days, ending Friday) are excluded from the series (§3.2 rule 9) and
  the kept week count (52) and the dropped weeks are recorded in
  `data_source.json`. **December 2011 is a partial month** (data end
  2011-12-09) — the series ends 2011-12-04, so no partial week is ever
  presented as a full week of demand; say so wherever December appears.
- **No-Saturday check:** the coder re-confirms from the file whether
  Saturday transactions are absent (Day 10 observed none). If true,
  record it in `data_source.json` as a structural 6-day trading week —
  a further reason weekly (not daily) aggregation is used. Daily
  aggregation is used only for profiling (weekday pattern), not for
  modelling.
- **Top-20 selection rule (frozen):** rank all SKUs by cleaned revenue
  (`Quantity × UnitPrice`, summed over the 52 full weeks) descending.
  Take the top 20 **subject to the coverage rule: each selected SKU
  must have demand (`units > 0`) in ≥ 30 of the 52 weeks**. If a
  top-20-by-revenue SKU fails that rule (e.g. a one-off bulk / seasonal
  line), drop it from the individual forecast, name it in the README
  and `data_source.json`, and replace it with the next-ranked SKU that
  passes, until exactly 20 SKUs are selected. Report the final 20 with
  their revenue share (share of total cleaned revenue over the 52 full
  weeks) in `sku_summary.csv`, the README and the insights.
- **Aggregate series:** total weekly units across **all** cleaned SKUs
  in the 52 full weeks (one series, 52 rows) — the "how busy will the
  warehouse be" number, and the series the ML method can be judged most
  reliably on, since it is smooth. Forecast with the same 6 methods and
  the same holdouts as the SKUs.

### 4.2 Demand-pattern clustering (DECIDED — roadmap "clustering" skill)

- **Primary: Syntetos–Boylan (SBC) classification** per SKU, from two
  per-SKU statistics over the 52 full weeks: **ADI** (average
  inter-demand interval = 52 / weeks-with-demand) and **CV²** (squared
  coefficient of variation of non-zero weekly demand). Quadrants with
  the standard cut-offs **ADI = 1.32, CV² = 0.49**: smooth
  (ADI < 1.32, CV² < 0.49), erratic (ADI < 1.32, CV² ≥ 0.49),
  intermittent (ADI ≥ 1.32, CV² < 0.49), lumpy (ADI ≥ 1.32,
  CV² ≥ 0.49). Classify **every SKU with any demand** in the 52 full
  weeks (not just the top 20) and report the count + unit share per
  quadrant in `cluster_summary.csv` — this is the "what kind of demand
  do we actually have" finding.
- **Method choice follows the cluster:** smooth → ETS / gradient
  boosting; erratic → gradient boosting / ETS (variance is the problem,
  not zeros); intermittent → Croston/SBA; lumpy → Croston/SBA with a
  wide safety stock (§4.5) and a "review manually" flag — a point
  forecast must not pretend lumpy demand is predictable. These are
  priors, not the winner rule: the winner is decided by measured WAPE
  (§4.3), and any case where the measured winner contradicts the prior
  is reported, not hidden.
- **Secondary (cross-check, IN):** KMeans (**k = 4**, `random_state=42`,
  `n_init=10`) on standardised per-SKU features
  [mean weekly units, CV, ADI, trend slope] for the **top 200 SKUs by
  revenue**, to check whether the SBC quadrants line up with
  data-driven groups. Report the agreement rate (share of the top 200
  whose KMeans group maps to their SBC quadrant under the best
  one-to-one mapping) in the notebook and insights. If they disagree,
  report the disagreement; do not force k to match the quadrants. The
  SBC classification is the decision-maker; KMeans is the check.

### 4.3 Forecast methods + backtest (DECIDED)

- **Target:** weekly units per top-20 SKU + the aggregate series
  (52 full weeks each).
- **Horizon:** **4 weeks ahead**. Do not claim beyond 4 weeks.
- **Methods (exactly six, no tuning grid), all forecasts clipped at
  ≥ 0 (demand cannot be negative):**

  | # | Method | Type | Definition |
  |---|--------|------|------------|
  | 1 | Naïve | Baseline | `ŷ(t) = y(t-1)` for all 4 horizon weeks. |
  | 2 | Seasonal naïve | Baseline | `ŷ(t) = y(t-52)`; **see the §11 note — with a 52-week series this is unavailable on both backtest origins, so it falls back to naïve and is excluded from winner selection** (its WAPE is reported as n/a, not as a second copy of naïve). |
  | 3 | 4-week moving average | Baseline | Mean of the last 4 observed weeks, flat for all 4 horizon weeks. |
  | 4 | Croston-SBA | Intermittent-demand | Croston with the Syntetos–Boylan bias correction (SBA = Croston × (1 − α/2)), α = 0.1, fixed. Candidate for the intermittent/lumpy clusters, not for smooth SKUs. |
  | 5 | Holt ETS | Statistical | `statsmodels` ExponentialSmoothing with additive trend, **no seasonal component** — a 52-week series cannot estimate annual seasonality (period 52) from a single cycle, so do NOT fit seasonal Holt-Winters on weekly data; that would be over-fitting one Christmas. |
  | 6 | HistGradientBoosting | ML | `sklearn` HistGradientBoostingRegressor (no new dependency) with features: lags 1, 2, 4 weeks; rolling 4-week mean; week-of-year / month; a December/Christmas indicator. Trained per SKU on its training weeks (lag 4 leaves 44 usable rows from 48 training weeks — small; expect high variance and report it) and on the aggregate series. Fixed hyperparameters, `random_state=42`; no tuning grid. |

- **Backtest (fixed, two origins, all 6 methods at each origin, per
  SKU and on the aggregate):**
  - **Primary origin (the headline test):** train on weeks 1–48
    (2010-12-06 → 2011-11-06), forecast weeks 49–52 (2011-11-07 →
    2011-12-04). This holdout covers late November / early December —
    the Christmas ramp — so errors will look worse than a mid-year
    holdout; report them as they are and explain why.
  - **Supplementary origin (the mid-year check, IN):** train on weeks
    1–29 (2010-12-06 → 2011-06-26), forecast weeks 30–33 (2011-06-27
    → 2011-07-24). The README must say both holdouts were used and
    which one is headline.
  - Metrics per origin × method × series: WAPE, MAE, RMSE, bias (§4.4),
    written to `backtest.csv`.
- **Per-cluster winner rule (frozen):** for each SBC cluster, compute
  the **volume-weighted WAPE on the primary holdout** across the top-20
  SKUs in that cluster (weights = actual holdout units; a cluster with
  a single top-20 SKU uses that SKU's WAPE and is flagged "n = 1").
  The method with the **lowest volume-weighted primary-holdout WAPE**
  is that cluster's winner. **Tie-break:** if two methods are within
  **0.5 percentage points** of WAPE, pick the simpler method, in this
  fixed simplicity order — naïve, 4-week moving average, Croston-SBA,
  Holt ETS, HistGradientBoosting (seasonal naïve never contends, §11).
  The supplementary holdout is a check only: if its winner differs from
  the primary winner, report both and disclose the disagreement — the
  **primary winner governs the reorder list**. The aggregate series
  gets its own winner by the same rule (lowest primary-holdout WAPE,
  same tie-break); it is not assigned to a cluster. The reorder list
  (§4.5) uses each SKU's cluster winner. A cluster with no top-20 SKU
  has no winner (reported as n/a, not invented).
- **Published forecast:** `forecast.csv` — the 4 weeks after the last
  full week (weeks starting 2011-12-05, 2011-12-12, 2011-12-19,
  2011-12-26), per top-20 SKU from its cluster winner and for the
  aggregate from its winner. Labelled as a 4-week trend extrapolation
  (§1), not a seasonal prediction.

### 4.4 Error metrics (defined once, used everywhere)

All on the 4-week holdout, per SKU and volume-weighted overall:

| Metric | Definition | Role |
|---|---|---|
| **WAPE (primary)** | `Σ\|actual − forecast\| / Σ actual` over the holdout | Headline metric. Scale-free across SKUs, defined even when a week is zero, directly interpretable ("we were off by X% of total units"). Reported per method, per cluster, and overall. |
| **MAE (secondary)** | Mean absolute error, in units | Operationally meaningful ("off by ~N units a week"). |
| **RMSE (secondary)** | Root mean squared error, in units | Penalises large misses; shown alongside MAE so a method that is usually close but occasionally badly wrong is visible. |
| **Bias (secondary)** | `mean(forecast − actual)` | A forecast unbiased on MAE can still systematically over-stock; bias is what the reorder list actually feels. |
| **MAPE** | **NOT a headline metric** — undefined on zero-demand weeks and explodes on small denominators, exactly the intermittent tail. If shown at all, restrict it to weeks with actual > 0 and label that restriction. | — |

Also report **in-sample vs holdout** WAPE so over-fitting is visible,
and the naïve baseline's WAPE as the "beat this" line on every chart.

### 4.5 Reorder logic (DECIDED — all inputs are ASSUMPTIONS, labelled as such)

No lead-time or inventory data exists in this dataset. Every input below
is an assumption, stated as such in the README, the notebook, the
insights, the dashboard and on the reorder list itself:

- **Lead time (ASSUMPTION): 1 week** — order placed at the start of a
  week arrives at the start of the next. Reasoning: weekly review cycle,
  UK domestic supplier, no data to support anything longer. Sensitivity:
  the reorder point at a **2-week lead time** is shown as an appendix
  column (`reorder_point_2wk_units`) so the buyer can see the cost of
  the assumption.
- **Review period: 1 week** (orders reviewed weekly, matching the
  forecast cadence).
- **Service level target (ASSUMPTION): 95% (z = 1.65)** for smooth /
  erratic SKUs; **90% (z = 1.28)** for intermittent / lumpy SKUs, where
  a 95% target would mean holding stock that mostly never moves. Record
  the two levels separately per SKU; do not average them.
- **Safety stock (ASSUMPTION formula, standard):**
  `SS = z × σ(weekly demand) × √(lead time in weeks)`, with σ from the
  SKU's cleaned weekly demand over the training window (weeks 1–48,
  `ddof=1`). For intermittent / lumpy SKUs use σ of **non-zero weeks
  only**, and flag the result as approximate.
- **Reorder point:** `ROP = mean weekly demand × lead time + SS`
  (mean weekly demand over the training window).
- **Order-up-to level (per SKU):**
  `S = forecast 4-week demand (cluster winner) + SS`; proposed order
  quantity = `max(0, S − assumed on-hand)`. **On-hand inventory is
  unknown (ASSUMPTION):** the reorder list is published as "order up to
  S units; order `S` if starting from zero" — i.e. the order-up-to level
  is the deliverable and the implied order assumes zero on-hand, with
  the zero-stock assumption printed on the list itself. **Never invent
  an on-hand number.**
- **Reorder list scope:** the top 20 forecast SKUs only, one row per
  SKU, in `data/processed/reorder_list.csv` and in the dashboard.
  **Reorder-list columns (exact, in this order):**

  | Column | Meaning |
  |---|---|
  | `stock_code` | SKU |
  | `description` | Product description (labelling only) |
  | `cluster` | SBC demand-pattern cluster (smooth / erratic / intermittent / lumpy) |
  | `winning_method` | Cluster winner used for this SKU's forecast (§4.3) |
  | `forecast_4w_units` | Forecast 4-week total, cluster winner (units) |
  | `mean_weekly_units` | Mean weekly demand, training window (units/week) |
  | `sigma_weekly_units` | σ of weekly demand, training window (non-zero weeks only for intermittent/lumpy — flagged approximate) |
  | `safety_stock_units` | Safety stock SS (units) |
  | `reorder_point_units` | ROP at 1-week lead time (units) |
  | `order_up_to_units` | Order-up-to level S (units) |
  | `implied_order_zero_on_hand_units` | Proposed order assuming zero on-hand (= S; units) |
  | `service_level` | 0.95 or 0.90, per cluster |
  | `stockout_risk_flag` | `ok`, or `review-manually` for lumpy SKUs and any SKU whose cluster winner is Croston-SBA (flat / low-confidence forecast — review manually, do not let a point forecast pretend lumpy demand is predictable) |
  | `reorder_point_2wk_units` | Appendix: ROP at a 2-week lead time (sensitivity column) |

### 4.6 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `weekly_demand.csv` + `sku_summary.csv` loaded into an
in-memory SQLite database (`sqlite3`, stdlib): weekly demand per SKU
(aggregate units by week, top 5 weeks) and the top-20-by-revenue ranking,
asserted equal to the pandas result. A test asserts the SQL and pandas
numbers agree. This is the day's SQL element; no `.pbix` is built (§3.6)
and the pipeline itself stays pandas.

### 4.7 Recommendations (DECIDED — structure; content follows the numbers)

Exactly **three** actionable recommendations, in
`outputs/insights_summary.md`, the dashboard and the README. Each has the
fixed structure **evidence → action → expected effect**, where the
evidence is a measured number from the committed CSVs and the expected
effect is stated in measured terms. The three cover, in order: (1) which
SKUs to order now (from the reorder list, naming the largest
order-up-to quantities); (2) which lumpy / low-confidence lines to review
manually rather than auto-ordering; (3) what the forecast error (headline
WAPE) implies for safety stock — i.e. how much cover the error itself
demands. The coder drafts them from the computed numbers; the optimizer
verifies each evidence number against the committed CSVs. No fourth
recommendation, no recommendation without a number.

## 5. File tree (exact — build only this)

```
day-11-inventory-demand-forecast/
├── README.md  requirements.txt  .gitignore  pyproject.toml  LICENSE
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   └── sample_rows.json        (1,000 cleaned rows, provenance sample)
│   └── processed/
│       ├── data_source.json
│       ├── weekly_demand.csv       (20 SKUs × 52 weeks = 1,040 rows)
│       ├── weekly_aggregate.csv    (52 rows)
│       ├── sku_summary.csv         (20 rows)
│       ├── cluster_summary.csv     (4 rows)
│       ├── forecast.csv            (84 rows: 20 SKUs × 4 weeks + aggregate × 4)
│       ├── backtest.csv            (origins × methods × series)
│       └── reorder_list.csv        (20 rows)
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── forecast.py
│   ├── clustering.py
│   ├── reorder.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_forecast_vs_actual.png
│       ├── 02_method_wape.png
│       ├── 03_demand_pattern_clusters.png
│       └── 04_reorder_list.png
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
extra charts, no `.pbix`, no model card, no `metrics.py` (metric
functions live in `src/forecast.py`, §6).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download ZIP (1 retry after 60 s on 429/5xx then stop; one plain full download — server ignores Range), unzip, read XLSX (`openpyxl`); verify counts 541,909 / 8 columns; apply cleaning rules §3.2 in order, counting every exclusion; build the 52-full-week series (§4.1), top-20 selection with the ≥ 30/52 coverage rule + replacements, aggregate series, SKU summary; write `sample_rows.json`, the processed CSVs and `data_source.json`; modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §5 generator, seed 42). `--offline` skips writing `data_source.json` when a live record exists (§3.5). |
| `src/forecast.py` | Pure metric + forecast functions, no I/O except the builders, no network — all tested: `wape(y_true, y_pred)`, `mae(y_true, y_pred)`, `rmse(y_true, y_pred)`, `bias(y_true, y_pred)`; `naive_forecast(series, horizon=4)`, `seasonal_naive_forecast(series, horizon=4)` (falls back to naïve where `y(t-52)` is unavailable, and flags the fallback), `moving_average_forecast(series, horizon=4, window=4)`, `croston_sba_forecast(series, horizon=4, alpha=0.1)`, `holt_forecast(series, horizon=4)` (additive trend, no seasonality, fixed), `gradient_boosting_forecast(series, horizon=4)` (lag 1/2/4 + rolling-4 mean + week-of-year/month + December indicator, `random_state=42`, forecasts clipped ≥ 0); `backtest(series, origins=((48, 4), (29, 4)))` returning per-origin × method metrics; `select_cluster_winner(backtest, cluster)` implementing §4.3 (volume-weighted primary-holdout WAPE + 0.5 pp tie-break in the fixed simplicity order); `build_forecast(...)` writing `forecast.csv`, `backtest.csv` |
| `src/clustering.py` | `demand_pattern_stats(weekly)` → per-SKU ADI + CV²; `classify_sbc(adi, cv2)` → smooth / erratic / intermittent / lumpy (cut-offs 1.32 / 0.49); `summarise_clusters(stats)` → `cluster_summary.csv` rows (counts + unit shares over every SKU with any demand); `kmeans_crosscheck(features, k=4, seed=42)` (StandardScaler + KMeans on the top 200 SKUs, features [mean weekly units, CV, ADI, trend slope], returns labels + agreement rate vs SBC) |
| `src/reorder.py` | Pure functions, no I/O, no network — all tested: `safety_stock(sigma, z, lead_time_weeks=1)`, `reorder_point(mean_weekly, lead_time_weeks, safety_stock)`, `order_up_to(forecast_4w, safety_stock)`, `service_level_for(cluster)` (0.95 smooth/erratic, 0.90 intermittent/lumpy; z 1.65 / 1.28); `build_reorder_list(sku_summary, forecasts, winners)` → the 14 columns of §4.5 in order, with the `review-manually` flag rule and the 2-week ROP appendix column |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source + CC BY 4.0 attribution + "historical 2010–2011 data — trend extrapolation, not a seasonal prediction" + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (total units, top-20 revenue share, headline WAPE, SKUs flagged review-manually); weekly demand + forecast panel; method-comparison panel; clustering panel; the reorder-list table (all 14 columns, with the zero-on-hand + 1-week-lead-time assumption printed above it); the three recommendations (§4.7) as a panel; methods + limitations panel (single-year, no seasonality, no inventory data); `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with CC BY 4.0 attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): EDA on the committed tables (cleaning audit, weekday pattern / no-Saturday check, demand-pattern quadrants, KMeans cross-check); the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.6); **forecast section guarded by `RAW.exists()`** — if the raw XLSX is present it re-runs the forecast via `src.forecast` and asserts the metrics match the committed `backtest.csv` / `forecast.csv` within tolerance; if absent it loads the committed CSVs and prints a note that the forecast was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: revenue = Quantity × UnitPrice on fixtures; cancellation rows excluded (InvoiceNo `C…`); Quantity ≤ 0 and UnitPrice ≤ 0 excluded; adjustment StockCodes excluded; missing CustomerID kept in demand (not filtered); partial first/last weeks excluded from the weekly series (52 full weeks kept); top-20 selection enforces the ≥ 30/52 coverage rule with replacement; ADI/CV² on fixtures + SBC quadrant boundaries (1.32 / 0.49); KMeans deterministic (same labels, seed 42); naïve forecast = last value; moving-average forecast = mean of last 4; seasonal naïve falls back to naïve when `y(t-52)` is unavailable; Croston-SBA is non-negative and flat-ish on intermittent fixtures; Holt forecast length = horizon, no seasonal component; gradient-boosting forecast length = horizon and ≥ 0; WAPE/MAE/RMSE/bias on fixtures (WAPE defined on zero weeks, MAPE not used as headline); per-cluster winner rule + 0.5 pp tie-break picks the simpler method; reorder maths on fixtures (SS = z·σ·√LT, ROP, S, implied order = S from zero; 95% vs 90% service levels; review-manually flag on lumpy/Croston SKUs); offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.6) |
| `data/README.md` | Provenance: URL, DOI, CC BY 4.0 licence, fetch date, row counts (raw 541,909 / cleaned / excluded per rule / partial-week rows), confirmed date range, adjustment-code list, weekly-series definition (52 full weeks, partial weeks excluded), top-20 rule + replacements, clustering parameters + quadrant counts, methods + backtest metrics + per-cluster winners, reorder assumptions (1-week lead time, 95%/90% service levels, zero on-hand), manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2 question with exact numbers + **exactly three actionable recommendations** (§4.7) + limitations (single-year seasonality, 2010–2011 data, prices VAT status unknown, no inventory/lead-time data, reorder list assumes zero on-hand) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, the three recommendations, validation, limitations, attribution — with the two §1 assumption labels prominent |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 10 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat, scikit-learn, scipy, statsmodels) **plus openpyxl** (XLSX reading). No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88); `.gitignore` per §3.4 (raw-data lines are the only data exclusions; `data/` itself is NOT excluded) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_retail_zip(url: str, dest: Path) -> Path
def load_raw_xlsx(path: Path) -> pd.DataFrame
def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def build_weekly_demand(df: pd.DataFrame) -> pd.DataFrame  # 52 full weeks only
def select_top_skus(df: pd.DataFrame, n: int = 20, min_weeks: int = 30) -> pd.DataFrame
def build_aggregate_demand(df: pd.DataFrame) -> pd.DataFrame
def write_data_source(path: Path, record: dict) -> None

# src/forecast.py
def wape(y_true, y_pred) -> float
def mae(y_true, y_pred) -> float
def rmse(y_true, y_pred) -> float
def bias(y_true, y_pred) -> float
def naive_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray
def seasonal_naive_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray
def moving_average_forecast(series: pd.Series, horizon: int = 4, window: int = 4) -> np.ndarray
def croston_sba_forecast(series: pd.Series, horizon: int = 4, alpha: float = 0.1) -> np.ndarray
def holt_forecast(series: pd.Series, horizon: int = 4) -> tuple[np.ndarray, object]
def gradient_boosting_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray
def backtest(series: pd.Series, origins: tuple = ((48, 4), (29, 4))) -> pd.DataFrame
def select_cluster_winner(backtest: pd.DataFrame, cluster: str) -> str

# src/clustering.py
def demand_pattern_stats(weekly: pd.DataFrame) -> pd.DataFrame
def classify_sbc(adi: float, cv2: float) -> str
def summarise_clusters(stats: pd.DataFrame) -> pd.DataFrame
def kmeans_crosscheck(features: pd.DataFrame, k: int = 4, seed: int = 42) -> tuple[np.ndarray, float]

# src/reorder.py
def safety_stock(sigma: float, z: float, lead_time_weeks: float = 1.0) -> float
def reorder_point(mean_weekly: float, lead_time_weeks: float, ss: float) -> float
def order_up_to(forecast_4w: float, ss: float) -> float
def service_level_for(cluster: str) -> tuple[float, float]  # (service_level, z)
def build_reorder_list(sku_summary: pd.DataFrame, forecasts: pd.DataFrame,
                       winners: dict) -> pd.DataFrame
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units (units, not GBP, unless a
panel is explicitly revenue), source footnote ("Source: UCI Online
Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 — historical
2010–2011 data, trend extrapolation, not a seasonal prediction"), no
truncated axes, legible at 100% zoom, holdout window labelled where it
appears.

1. **01_forecast_vs_actual.png** — Forecast vs actual on the holdout.
   Two panels: (a) aggregate weekly units — full 52-week history +
   primary-holdout actuals vs the cluster-winner forecast vs naïve,
   holdout shaded (weeks 49–52, 2011-11-07 → 2011-12-04); (b) top 4
   SKUs by revenue, small multiples, same holdout shading, actual vs
   winner forecast vs naïve. Answers Q1.
2. **02_method_wape.png** — Method comparison by WAPE. Grouped bars:
   WAPE on the primary holdout per method, grouped by SBC cluster
   (plus an overall volume-weighted group), baselines vs Croston-SBA /
   Holt / HistGradientBoosting, with the naïve WAPE as the "beat this"
   reference line and the per-cluster winner named in the title.
   Answers Q2's method half.
3. **03_demand_pattern_clusters.png** — Demand-pattern clustering.
   ADI (x) vs CV² (y) scatter, one point per SKU with any demand,
   quadrant lines drawn at ADI = 1.32 and CV² = 0.49 with the four
   quadrant labels, top-20 SKUs highlighted (larger markers, labelled
   with StockCode), log scales only if labelled as such. Answers Q2's
   clustering half.
4. **04_reorder_list.png** — Reorder-list visualisation. Horizontal
   stacked bars per top-20 SKU (ranked by order-up-to quantity):
   forecast 4-week units + safety stock = order-up-to level, coloured
   by cluster, with the `review-manually` SKUs flagged and the service
   level annotated; the zero-on-hand + 1-week-lead-time assumption in
   the footnote. Answers Q3.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–10 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URL, DOI, licence (CC BY 4.0,
      verbatim attribution), fetch date (2026-11-15), row counts (raw
      541,909 / cleaned / excluded per rule / partial-week rows),
      confirmed date range — in `data/README.md` and
      `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → clean → weekly
      series → cluster → backtest → forecast → reorder → charts, with
      `--offline` mode) + KPI/metric definitions (§4.4) written down
- [ ] **SKU-level forecast + proposed reorder list delivered** (roadmap
      deliverable): top-20 SKU forecasts + aggregate forecast, and the
      20-row reorder list with all §4.5 columns, in the dashboard,
      charts and insights
- [ ] **Simple baselines vs ML evaluated**: all 6 methods on the same
      4-week holdout (primary + supplementary origins), WAPE primary,
      MAE/RMSE/bias secondary, per SKU and volume-weighted overall;
      naïve baseline shown as the "beat this" line
- [ ] **Clustering done**: SBC ADI/CV² quadrants for every SKU with any
      demand (counts + unit shares in `cluster_summary.csv`); KMeans
      k = 4 cross-check on the top 200 SKUs with the agreement rate
      reported; method choice follows the cluster via the §4.3 winner
      rule
- [ ] **Forecast delivered honestly**: 4-week horizon only; Holt ETS
      trend-only (no seasonality — one year cannot support a seasonal
      fit); seasonal naïve reported as unavailable/n/a on this series
      (§11); the Christmas-ramp holdout reported as the hard test it is;
      **the forecast is labelled a trend extrapolation from one
      retailer, one year — NOT a seasonal prediction — on every surface**
- [ ] **Reorder list delivered with labelled assumptions**: 1-week lead
      time, 95%/90% service levels, safety stock = z·σ·√lead time,
      order-up-to from zero on-hand — **labelled on every surface**;
      2-week-lead-time ROP sensitivity column present
- [ ] **SQL check done** (§4.6): weekly demand per SKU + top-20 ranking
      via in-memory SQLite asserted equal to pandas, in the notebook
      and a test
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate below)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2 question with exact numbers) + **exactly three** actionable
      recommendations (§4.7)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; **no copying others'
      code** — all code is Victor's own original work; **data-size
      exception honoured** (no file > 1 MB, `data/` < 5 MB; raw ZIP/XLSX
      git-ignored per §3.4 and absent at handoff; `.gitignore` matches
      §5/§6 and does NOT exclude `data/`)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. the top
      SKU's 4-week forecast total or its safety stock — from the
      committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert — **exit 0 with 0 error cells** — with `_find_root()`
      and the guarded forecast section, §6)
- [ ] Pinned dependencies in `requirements.txt` (incl. openpyxl);
      **`black --check` + `ruff check` clean**
- [ ] Streamlit smoke gate passed: **fresh port 8502+**, HTTP 200 on `/`
      and on `/_stcore/health`, **real `screenshots/dashboard.png`**
      captured (**< 1 MB**), server killed and port verified free
- [ ] **Offline pipeline run must NOT clobber `data_source.json`**
      (skip writing it when a live record exists — §3.5, tested)
- [ ] **No base64 strings quoted in docs** (validator false-positive
      rule — never paste base64 content into any `.md` file)
- [ ] **Orchestrator validate clean** for the day folder
      (`python agents/orchestrator.py --day 11 validate`)
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes (≥ 15 tests, from repo root and from the day folder)
- [ ] `.gitignore` matches §3.4/§5 (raw ZIP/XLSX + synthetic excluded; `data/` itself NOT excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+), < 1 MB
- [ ] `data/` total < 5 MB, no file > 1 MB; **no raw ZIP/XLSX on disk at handoff** (git-ignored, deleted after the build); `data_source.json` records live counts, cleaning exclusions, partial-week rows, top-20 replacements, cluster parameters, backtest results, per-cluster winners and reorder assumptions
- [ ] Counts verified against §3.3 (541,909 rows, 8 columns); confirmed date range recorded; 52 full weeks recorded; Dec 2011 partial handling recorded
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Notebook runs via nbconvert with exit 0 and 0 error cells; SQL check asserts in the notebook
- [ ] Build only what §5 lists; no extra web searches; no base64 strings in any doc

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| ZIP/XLSX download fails or is truncated | 1 retry after 60 s, then stop and report; synthetic fallback (§3.6) only if live fails |
| Row count ≠ 541,909 or columns differ | Verify after fetch (§3.3); report, do not silently proceed |
| Server ignores Range header | One plain full download, never ranged/resumable (§3.1) |
| Adjustment codes list misses a real non-product code (or drops a real product) | Coder profiles distinct codes first; additions only for plainly non-product codes, recorded in `data_source.json` (§3.2 rule 5) |
| A top-20-by-revenue SKU has < 30 weeks of demand | Coverage rule + replacement with the next-ranked passing SKU, named in the README (§4.1) |
| Partial Dec 2011 weeks understate demand | Only 52 full weeks used; partial weeks counted and excluded (§3.2 rule 9, §4.1) |
| Christmas-ramp holdout makes errors look bad | Report as the hard test it is + supplementary mid-year holdout (§4.3); do not cherry-pick the easier origin |
| Seasonal Holt-Winters impossible on 1 year of data | Trend-only Holt, disclosed (§4.3) — no silent seasonal substitute |
| Seasonal naïve uncomputable on a 52-week series | Falls back to naïve, reported n/a, excluded from winner selection (§11) |
| HistGradientBoosting high variance on 44 usable training rows per SKU | Fixed hyperparameters, no tuning grid; variance reported; aggregate series is the reliable ML read (§4.3) |
| Lumpy demand presented as predictable | Croston-SBA + wide safety stock + `review-manually` flag; point forecast never presented as certain (§4.5) |
| No inventory / lead-time data tempts invented numbers | Reorder list is order-up-to from zero on-hand, assumptions printed on the list (§4.5) |
| KMeans disagrees with SBC quadrants | Report the disagreement + agreement rate; SBC decides (§4.2) |
| Prices may or may not include VAT | Disclosed as a limitation (dataset does not state it) |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text. Never quote base64 strings in docs (§8). |

## 11. Differences from the brief (plan wins)

- **Seasonal naïve (§4.3):** the brief (§2d) said seasonal naïve is
  "only available for the last weeks of the year — where unavailable,
  fall back to naïve". With a 52-week series that is wrong in a stronger
  sense: forecasting weeks 49–52 (or 30–33) needs `y(t-52)` = weeks
  −3–0 (or −22–−19), which do not exist, so seasonal naïve is
  **unavailable on both backtest origins**. The plan **fixes** this:
  the method is implemented with the naïve fallback, its WAPE is
  reported as n/a, and it is **excluded from winner selection** (it
  would otherwise be a duplicate of naïve). This is a correction of the
  brief, not a coder choice.
- **Partial-final-week rule (§4.1):** the brief (§2b) left the rule open
  ("exclude it from training if it has < 4 trading days"). The plan
  **fixes** it: only the 52 full ISO weeks (2010-12-06 → 2011-12-04)
  are used; both partial weeks are excluded and counted, regardless of
  trading-day count.
- **Backtest origins (§4.3):** the brief (§2c) made the mid-year holdout
  optional ("if time allows"). The plan **fixes** it IN: primary origin
  (train weeks 1–48, forecast 49–52) is headline; supplementary origin
  (train weeks 1–29, forecast 30–33) is mandatory as a check.
- **Per-cluster winner rule (§4.3):** the brief (§2d/§2e) said "pick the
  winner per cluster" without a rule. The plan **fixes** it:
  volume-weighted primary-holdout WAPE per cluster, tie-break within
  0.5 pp by the fixed simplicity order (naïve, moving average,
  Croston-SBA, Holt ETS, HistGradientBoosting); supplementary holdout is
  a check only and the primary winner governs the reorder list.
- **KMeans cross-check (§4.2):** the brief left it for the planner to
  confirm. The plan **fixes** it IN: k = 4, top 200 SKUs by revenue,
  features [mean weekly units, CV, ADI, trend slope], agreement rate
  reported, SBC decides.
- **Cleaning rules (§3.2):** the brief listed expected quirks; the plan
  **fixes** the ordered rules, the adjustment-code list, the
  missing-CustomerID scope (kept in demand), and the partial-week rule,
  with every exclusion counted.
- **Reorder-list columns (§4.5):** the brief (§2f) listed the fields in
  prose; the plan **fixes** the exact 14 columns in order, including
  the `stockout_risk_flag` values (`ok` / `review-manually`) and the
  2-week-lead-time ROP appendix column.
- **Data-size exception (§3.4):** the brief (§7 item 5) asked the
  planner to decide; the plan **fixes** the exception — raw ZIP/XLSX
  git-ignored and re-downloaded at build (Day 8 precedent), committed
  provenance = `sample_rows.json` (1,000 cleaned rows) + processed
  CSVs + `data_source.json`, `data/` < 5 MB, no file > 1 MB,
  `.gitignore` must NOT exclude `data/`.
- **Recommendations (§4.7):** the brief (§7 item 6) asked for one
  actionable recommendation minimum; the plan **fixes** exactly three,
  each evidence → action → expected effect, each evidence number
  verified against the committed CSVs.
- **Power BI:** the roadmap's section-level core skills list Power BI,
  but no `.pbix` is built (same decision as Days 8–10 — a `.pbix`
  cannot be built or verified in this environment); the Streamlit
  dashboard + 4 static charts are the deliverables. The SQL skill is
  covered by the §4.6 check.
- **Notebook forecast (§6):** the brief did not specify notebook
  mechanics; the plan adds the guarded forecast section (re-runs the
  forecast when the raw XLSX is present, otherwise loads committed
  CSVs — 0 errors either way).
- **CI flake (§3.5):** the Day 9 CI flake (byte-exact CSV comparison)
  is addressed here by mandating tolerance-based comparison in the
  offline-reproduction test, and the offline run skips writing
  `data_source.json` when a live record exists.

## 12. Build order

1. `src/data_pipeline.py` — download ZIP → unzip → read XLSX →
   verify counts → clean (§3.2, exclusions counted) → 52-full-week
   series → top-20 selection (≥ 30/52 rule + replacements) → aggregate
   series → `sample_rows.json` + processed CSVs + `data_source.json`
   (live run; cache raw).
2. `src/clustering.py` + `src/forecast.py` + `src/reorder.py` — ADI/CV²
   + SBC quadrants → `cluster_summary.csv`; KMeans k = 4 cross-check;
   6 methods + 2-origin backtest → `backtest.csv`; per-cluster winner
   rule (§4.3) → `forecast.csv`; reorder maths → `reorder_list.csv`.
3. `src/make_charts.py` — 4 charts from the processed CSVs.
4. `notebooks/analysis.ipynb` — EDA + Q1–Q3 + SQL check + guarded
   forecast section; run via nbconvert, exit 0, 0 errors.
5. `src/app.py` — Streamlit dashboard from processed CSVs only; smoke
   test on a fresh port (8502+) + real `screenshots/dashboard.png`
   (< 1 MB).
6. `tests/test_pipeline.py` — ≥ 15 tests (§6); delete
   `tests/test_smoke.py`; `pytest`, `black`, `ruff`; coder handoff
   checklist (§9); delete the raw ZIP/XLSX from disk at handoff.
7. Docs — `README.md`, `data/README.md`, `outputs/insights_summary.md`;
   every number checked against the committed processed CSVs; the two
   §1 assumption labels on every surface.
