# Day 11 — Inventory Demand Forecast: Research Brief

**Status:** RESEARCH COMPLETE — verified live 2026-11-15 (one lean probe pass).
**Business question:** For a UK online retailer, how much of each key product
will sell over the next 4 weeks, and what should be reordered now to avoid
stockouts without over-stocking slow lines?
**Audience:** A retail inventory / buying manager (non-technical reader of
the README and reorder list) and a data reviewer checking the forecast
method. The deliverable is a SKU-level forecast plus a proposed reorder
list, not a revenue dashboard — Day 10 already covered revenue.

## 1. Data source — verified live

### 1a. PRIMARY — UCI Online Retail (Chen, 2015)

- **Source:** UCI Machine Learning Repository, dataset **"Online Retail"**,
  dataset ID **352**, DOI **https://doi.org/10.24432/C5BW33**.
- **Dataset page (verified 2026-11-15, HTTP 200):**
  `https://archive.ics.uci.edu/dataset/352/online+retail`
  (page fetched in full: 174,303 bytes, ~1.0 s).
- **Download (verified 2026-11-15, HTTP 200):**
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  — a ZIP containing `Online Retail.xlsx`, listed on the page as
  **22.6 MB**. HEAD returned HTTP 200; a ranged GET returned HTTP 200
  with the full file (23,715,478 bytes ≈ 22.6 MB, confirmed ZIP archive
  data) — **the server ignores the Range header, so the coder must do
  one plain full download, not a ranged/resumable fetch.** The probe
  copy was deleted immediately; no raw file is committed by the
  researcher. No key, no account, no documented rate limit; one single
  download is the whole fetch.
- **Coverage verified from the dataset page:** **541,909 instances**,
  stated date range **01/12/2010 → 09/12/2011** ("all the transactions
  occurring between 01/12/2010 and 09/12/2011 for a UK-based and
  registered non-store online retail"). The coder MUST confirm the date
  range and row count from the downloaded file itself and record the
  confirmed values in `data_source.json` and `data/README.md`.
- **Fields (8 columns in the variables table):** `InvoiceNo` (string;
  cancellations start with `C`), `StockCode` (string), `Description`
  (string), `Quantity` (int), `InvoiceDate` (datetime), `UnitPrice`
  (float, GBP), `CustomerID` (float/int, missing for some rows),
  `Country` (string). **Note a page inconsistency for the coder to
  record, not resolve by guessing:** the page header says
  "# Features 6" while the variables table lists 8 columns — the file
  itself is authoritative; Day 10 also found 8 columns. Do not "fix"
  the page's count in the brief.
- **Expected quirks (coder must verify counts from the file, not trust
  this list):**
  - Cancelled invoices (`InvoiceNo` starting with `C`) carry negative
    `Quantity` — exclude from demand, count them separately.
  - Some rows have negative `Quantity` without a `C` prefix, zero or
    negative `UnitPrice`, and missing `Description` (adjustment /
    bad-debt codes such as `POST`, `DOT`, `BANK CHARGES`, `M`) — these
    are not sellable demand; exclude and report the exclusion counts.
  - `CustomerID` is missing on a substantial share of rows — irrelevant
    for SKU demand (demand is summed over all customers), but do not
    filter on `CustomerID`.
  - `Description` is free text; there is **no product-category column**
    — SKU identity is `StockCode` (+ `Description` for labelling only).
    Do not invent categories; group only via the demand-pattern
    clustering in §2.
  - **December 2011 is a partial month** (data end 09/12/2011) and the
    Christmas peak falls in the holdout — the backtest (§2) will
    therefore test the hardest weeks of the year; say so, do not
    silently drop December.
  - **No Saturday transactions** were observed in Day 10's profiling
    (the retailer apparently did not trade Saturdays) — the coder must
    re-confirm from the file; if true, daily series have a structural
    6-day week, which is a further reason to aggregate weekly (§2).
  - Prices are in GBP; demand is counted in **units**, so price plays
    no role in the forecast itself (revenue is used only to rank SKUs).
- **Licence / attribution:** **CC BY 4.0** (stated on the dataset page:
  "licensed under a Creative Commons Attribution 4.0 International
  (CC BY 4.0) license"). Cite: "Chen, D. (2015). Online Retail
  [Dataset]. UCI Machine Learning Repository.
  https://doi.org/10.24432/C5BW33". Attribution must appear in
  `data/README.md`, the notebook, and the day README.
- **Rate limits:** none documented on the dataset page. Polite-use rule:
  one download, no scraping loop, no repeated hits; on HTTP failure,
  wait 60 s, retry once, then stop and report (§4).
- **Data-size rule:** the raw XLSX (~22.6 MB) is far over the 1 MB/file
  guideline — it is **git-ignored** and re-downloaded at build time
  (same pattern as Days 8–10). Committed data = processed aggregates
  (weekly SKU demand, forecast table, reorder list) + a small cleaned
  sample (≤ 1,000 rows), total under 5 MB/day, no single file over
  1 MB. The pipeline must run end-to-end from the downloaded file with
  no manual step.

### 1b. Ruled out

- **UCI Online Retail II (dataset 502, 2009–2011):** a superset of the
  same retailer; heavier file, no extra value for a 4-week SKU forecast
  — not needed.
- **Kaggle copies of Online Retail:** require a Kaggle account/token;
  the UCI direct download needs neither.
- **Synthetic-only build:** rejected — the roadmap names UCI Online
  Retail and the live file is reachable; synthetic is fallback only
  (§4). No silent synthetic substitution, ever.

## 2. Forecast design — recommendations for the planner

These are researcher recommendations, not planner decisions. The planner
fixes the final values in `plan.md`; where a value below is an assumption
(not in the data) it is labelled ASSUMPTION.

### 2a. Which SKUs to forecast (concrete recommendation)

- **Forecast individually: the top 20 SKUs by revenue** over the cleaned
  period (revenue = summed `Quantity × UnitPrice` after cleaning).
  Reasoning: the catalogue has ~4,000 StockCodes, but demand is heavily
  concentrated (Day 10 found the top SKUs dominate revenue); the top 20
  are the lines where a stockout actually costs money, and 20 is small
  enough to chart, table and sanity-check one by one in a one-day build.
  Each of the 20 must have sales in **≥ 30 of the 52 weeks** — if a
  top-20-by-revenue SKU fails that (e.g. a one-off bulk / seasonal
  line), drop it from the individual forecast, say so in the README,
  and replace it with the next-ranked SKU that passes. Report the final
  20 with their revenue share.
- **Do NOT forecast all SKUs individually.** The long tail is mostly
  intermittent (many zero weeks); per-SKU ML on ~4,000 sparse series
  in one day would produce noise presented as precision. Instead the
  tail is handled in aggregate (§2d) and via the clustering in §2e.
- **Also forecast the aggregate:** total weekly units across all
  cleaned SKUs (one series) — this is the "how busy will the warehouse
  be" number and the series the ML method can be judged most reliably
  on, since it is smooth.

### 2b. Aggregation level — WEEKLY (primary)

- **Weekly demand per SKU** (Monday–Sunday weeks, `InvoiceDate`
  floored to week). Reasoning: daily per-SKU demand is mostly zeros
  (sparse + no Saturdays), so daily models would learn mostly "zero";
  weekly gives 52 observations per SKU — enough for lag/rolling
  features and a 4-week holdout, while still matching a weekly
  reorder cycle. Daily aggregation is used only for profiling (weekday
  pattern, confirming the no-Saturday quirk), not for modelling.
- Weekly series length: 52 weeks (2010-12-06 week through the partial
  week ending 2011-12-09). The final week is partial — flag it in the
  series chart and exclude it from training if it has < 4 trading days
  (planner fixes the rule; document whichever is chosen).

### 2c. Forecast horizon — 4 WEEKS

- **Horizon: 4 weeks ahead** (the 4 weeks after the last full training
  week). Reasoning: it matches a weekly reorder cycle with a 1-week
  lead time (§2f) — one order cycle plus cover — and it is the longest
  horizon a 52-week series can support without the backtest becoming
  meaningless. Longer horizons (8–12 weeks) would need multi-year
  seasonality the data does not have. Do not claim beyond 4 weeks.
- **Backtest (the honest test):** train on weeks up to 4 weeks before
  the end, forecast the last 4 full weeks, score against actuals.
  That holdout covers late November / early December — the Christmas
  ramp — so errors will look worse than a mid-year holdout; report
  them as they are and explain why. A second, mid-year 4-week holdout
  (e.g. train to end-June, forecast July) is recommended as a
  supplementary check if time allows, so the headline number is not
  only the Christmas test — planner decides, and the README must say
  which holdouts were used.

### 2d. Methods to compare — baselines vs ML (concrete list)

Compare all methods on the **same** weekly series, same 4-week
holdout, per SKU and on the aggregate. Minimum set:

| # | Method | Type | Notes |
|---|--------|------|-------|
| 1 | Naïve (last week repeats) | Baseline | `ŷ(t) = y(t-1)` for all 4 weeks. |
| 2 | Seasonal naïve (same week last year) | Baseline | `ŷ(t) = y(t-52)`; only available for the last weeks of the year — where unavailable, fall back to naïve and say so. With one year of data this is a weak baseline; keep it because the roadmap asks for a seasonal comparison, not because it will win. |
| 3 | 4-week moving average | Baseline | Mean of the last 4 weeks, flat for all 4 horizon weeks. |
| 4 | Croston / SBA (Syntetos–Boylan approximation) | Intermittent-demand method | For slow/intermittent SKUs (§2e); SBA = Croston × (1 − α/2) bias correction. Use as the candidate for the intermittent/lumpy clusters, not for smooth SKUs. |
| 5 | Holt exponential smoothing (ETS, trend, no seasonality) | ML-adjacent / statistical | `statsmodels` ExponentialSmoothing with trend, no seasonal component — a 52-week series cannot estimate annual seasonality (period 52) from a single cycle, so do NOT fit seasonal Holt-Winters on weekly data; that would be over-fitting one Christmas. |
| 6 | Gradient boosting on lag features | ML | `sklearn` HistGradientBoostingRegressor (no new dependency) with features: lags 1, 2, 4 weeks; rolling 4-week mean; week-of-year / month; a December/Christmas indicator. Train per SKU on its 48 training weeks (small — expect high variance; report it) and on the aggregate series. |

- **Winner selection:** pick the winner **per cluster** (§2e), not one
  global winner — a method that wins on smooth SKUs will lose on
  intermittent ones, and a single winner would mislead the reorder
  list. The reorder list (§2f) uses each SKU's cluster winner.
- **Error metrics (all reported per SKU and volume-weighted overall):**
  - **WAPE (primary):** `Σ|actual − forecast| / Σ actual` — the
    headline metric. Scale-free across SKUs, defined even when a week
    is zero, and directly interpretable ("we were off by X% of total
    units"). Report WAPE per method, per cluster, and overall.
  - **MAE (secondary):** mean absolute error in units — the
    operationally meaningful number ("off by ~N units a week").
  - **RMSE (secondary):** penalises large misses; report alongside MAE
    so a method that is usually close but occasionally badly wrong is
    visible.
  - **Bias / mean signed error (secondary):** `mean(forecast − actual)` —
    a forecast that is unbiased on MAE can still systematically
    over-stock; bias is what the reorder list actually feels.
  - **MAPE: do NOT use as a headline metric** — it is undefined on
    zero-demand weeks and explodes on small denominators, which is
    exactly the intermittent tail. If MAPE is shown at all, restrict
    it to weeks with actual > 0 and label that restriction.
  - Also report **in-sample vs holdout** WAPE so over-fitting is visible,
    and the naïve baseline's WAPE as the "beat this" line on every chart.

### 2e. Clustering angle (roadmap "clustering" skill)

- **Primary: Syntetos–Boylan demand-pattern classification** per SKU,
  from two per-SKU statistics over the 52 weeks: **ADI** (average
  inter-demand interval = weeks / weeks-with-demand) and **CV²**
  (squared coefficient of variation of non-zero weekly demand).
  Quadrants (standard cut-offs ADI = 1.32, CV² = 0.49):
  smooth (ADI < 1.32, CV² < 0.49), erratic (ADI < 1.32, CV² ≥ 0.49),
  intermittent (ADI ≥ 1.32, CV² < 0.49), lumpy (ADI ≥ 1.32,
  CV² ≥ 0.49). Classify **every SKU with any demand** (not just the
  top 20) and report the count + unit share per quadrant — this is the
  "what kind of demand do we actually have" finding.
- **Method choice follows the cluster:** smooth → ETS / gradient
  boosting; erratic → gradient boosting / ETS (variance is the
  problem, not zeros); intermittent → Croston/SBA; lumpy → Croston/SBA
  with a wide safety stock (§2f) and a "review manually" flag — do not
  let a point forecast pretend lumpy demand is predictable.
- **Secondary (cross-check, planner confirms):** KMeans (k = 4) on
  standardised per-SKU features [mean weekly units, CV, ADI, trend
  slope] for the top ~200 SKUs by revenue, to check whether the
  SBC quadrants line up with data-driven groups. If they disagree,
  report the disagreement; do not force k to match the quadrants.
  The SBC classification is the decision-maker; KMeans is the check.

### 2f. Reorder logic inputs (ASSUMPTIONS — no lead-time or inventory data exists in this dataset)

State all of these as assumptions in the README and the reorder list;
none of them is measured:

- **Lead time (ASSUMPTION): 1 week** — order placed at the start of a
  week arrives at the start of the next. Reasoning: weekly review
  cycle, UK domestic supplier, no data to support anything longer;
  a longer assumed lead time would inflate safety stock without
  evidence. Sensitivity: also show the reorder point at a 2-week lead
  time in an appendix column so the buyer can see the cost of the
  assumption.
- **Review period: 1 week** (orders reviewed weekly, matching the
  forecast cadence).
- **Service level target (ASSUMPTION): 95%** (z = 1.65) for smooth /
  erratic SKUs; **90%** (z = 1.28) for intermittent / lumpy SKUs,
  where a 95% target would mean holding stock that mostly never moves.
  Record the two levels separately; do not average them.
- **Safety stock (ASSUMPTION formula, standard):**
  `SS = z × σ(weekly demand) × √(lead time in weeks)`, with σ from the
  SKU's cleaned weekly demand over the training window. For
  intermittent SKUs use σ of non-zero weeks only, and flag the result
  as approximate.
- **Reorder point:** `ROP = mean weekly demand × lead time + SS`.
- **Order-up-to level (per SKU):**
  `S = forecast 4-week demand (cluster winner) + SS`; proposed order
  quantity = `max(0, S − assumed on-hand)`. **On-hand inventory is
  unknown (ASSUMPTION):** the dataset has no stock levels, so the
  reorder list must be published in the form "order up to S units;
  order `S` if starting from zero" — i.e. present the order-up-to
  level as the deliverable and the implied order assuming zero
  on-hand, with the zero-stock assumption printed on the list itself.
  Never invent an on-hand number.
- **Reorder list scope:** the top 20 forecast SKUs only, one row per
  SKU: SKU, description, cluster, winning method, 4-week forecast,
  mean weekly demand, σ, safety stock, ROP, order-up-to S, implied
  order (from zero), service level used. SKUs whose forecast is flat /
  Croston-based carry a "low-confidence — review manually" flag.

### 2g. SQL (roadmap skill)

- An in-memory SQLite check in the notebook: weekly demand per SKU
  and the top-20-by-revenue ranking via SQL, asserted equal to the
  pandas result (as Days 8–10 did). No external database.

### 2h. Power BI (roadmap skill)

- No `.pbix` is produced (same decision as Days 8–10 — a `.pbix`
  cannot be built or verified in this environment); the forecast is
  delivered as the Streamlit app + static charts. Recorded here so the
  planner does not re-litigate it.

## 3. Metrics to compute (definitions, used everywhere)

- **Weekly demand (units):** summed cleaned `Quantity` per SKU per
  week. Cleaning = exclude cancelled invoices (`InvoiceNo` starting
  `C`), exclude rows with `Quantity ≤ 0` after cancellation handling,
  exclude `UnitPrice ≤ 0`, exclude non-product adjustment StockCodes /
  descriptions (planner fixes the exact list; Day 10's list is the
  starting point). Every exclusion counted and reported.
- **Revenue (ranking only):** `Quantity × UnitPrice` per line, summed
  after cleaning, GBP. Used only to rank SKUs and to report the top
  20's revenue share — the forecast itself is in units.
- **Forecast accuracy:** WAPE (primary), MAE, RMSE, bias — definitions
  in §2d, all on the 4-week holdout, per SKU and volume-weighted.
- **Demand-pattern statistics:** ADI and CV² per SKU (§2e); cluster
  counts and unit shares.
- **Reorder quantities:** ROP, safety stock, order-up-to S (§2f) —
  all labelled as assumption-based.
- **Visualisations (at least two well-labelled, roadmap minimum):**
  (1) actual vs forecast weekly units for the top SKUs (one panel per
  SKU or small multiples, holdout shaded, naïve baseline shown);
  (2) demand-pattern scatter (ADI vs CV², quadrants drawn, top 20
  highlighted); (3) recommended: WAPE by method × cluster bar chart
  and the reorder-list chart/table in the app. Every chart: title,
  axis labels with units, source note, and the holdout window labelled.

## 4. Licence / attribution

CC BY 4.0 — attribution line in §1a, required in `data/README.md`, the
notebook, and the day README. No licence-file changes (portfolio LICENSE
already covers the code).

## 5. Synthetic-fallback note

Only if the live download fails: retry once after 60 s, then stop and
report to the orchestrator — **do not silently substitute synthetic
data**. If a synthetic fallback were ever authorised, it must be built
from documented parameters (52 weeks, 20 SKUs with lognormal weekly
demand, a December uplift, intermittent tail SKUs, seed 42), stored as
`data/raw/*_synthetic.csv`, recorded in `data_source.json` as
`synthetic: true`, and labelled "SYNTHETIC — NOT REAL DATA" in every
chart, the notebook, and the README; it must never overwrite real data.
**The live download works (verified above), so the fallback is
contingency only; the coder must not use it unless the live call fails
after the one retry.**

## 6. Verification status

- [x] Source confirmed against the official UCI page (2026-11-15):
  dataset 352, 541,909 instances, 8 columns in the variables table
  (page header says "# Features 6" — discrepancy recorded in §1a),
  date range 01/12/2010 → 09/12/2011, CC BY 4.0, DOI 10.24432/C5BW33.
- [x] Download URL
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  returned HTTP 200 on HEAD and on GET; full file 23,715,478 bytes
  (≈ 22.6 MB, matches the page listing), confirmed ZIP archive data.
  Server ignores the Range header — coder does one plain full download.
  No rate limit documented; one download, retry-once-after-60-s rule.
- [x] Conflicts recorded with resolution:
  - The dataset has **no product-category, lead-time or inventory
    columns** — resolved by SKU-level (not category) forecasting, and
    by assumption-based reorder logic (§2f) labelled as such.
  - The raw file (22.6 MB) exceeds the commit-size rule — resolved by
    git-ignoring it and committing aggregates + a ≤ 1,000-row sample
    (Day 8–10 pattern).
  - The weekly series is only 52 weeks — resolved by a 4-week horizon,
    no seasonal Holt-Winters on weekly data, and a disclosed
    single-year seasonality limit.
  - The 4-week holdout falls on the Christmas ramp — resolved by
    reporting it as the hard test it is, with an optional mid-year
    holdout as a supplementary check (§2c).
  - Page header "# Features 6" vs 8 columns in the variables table —
    resolved by treating the file as authoritative; coder confirms.
- [ ] No live download performed by the researcher beyond the probe
  GET (the probe copy was deleted immediately; the full build download
  is the coder's job); date range, row count, quirk counts and the
  no-Saturday observation are to be confirmed from the file by the
  coder.

## 7. Open items for the planner

1. Fix the top-20 selection rule exactly (§2a: revenue ranking,
   ≥ 30/52 weeks with demand, replacement rule) and the cleaning /
   adjustment-code exclusion list.
2. Fix the partial-final-week rule (§2b) and the backtest windows
   (Christmas holdout mandatory; mid-year supplementary holdout yes/no).
3. Fix the per-cluster winner-selection rule (§2d/§2e) and confirm the
   KMeans cross-check (k = 4, top ~200 SKUs) is in or out.
4. Fix the reorder-list columns and the exact wording of the
   assumption labels (§2f: 1-week lead time, 95%/90% service levels,
   zero on-hand).
5. Decide the committed-data set (weekly demand, forecast table,
   reorder list, sample) so the day folder stays under the 5 MB limit
   with the raw file git-ignored.
6. Fix the recommendation structure: one actionable recommendation
   minimum (roadmap), each tied to a measured number — e.g. which
   SKUs to order now, which lumpy lines to review manually, and what
   the forecast error implies for safety stock.

## Handoff

- **Produced:** `research_brief.md` (this file).
- **Verified numbers:** UCI dataset 352, 541,909 instances, 8 columns
  (variables table), date range 01/12/2010 → 09/12/2011, CC BY 4.0,
  DOI 10.24432/C5BW33; dataset page HTTP 200; download URL HTTP 200
  (HEAD and GET), 23,715,478 bytes ≈ 22.6 MB, confirmed ZIP; no rate
  limit documented.
- **Known gaps:** date range / row count / quirk counts to be confirmed
  from the file by the coder; "# Features 6" vs 8 columns discrepancy
  recorded; no lead-time/inventory data exists — reorder logic is
  assumption-based by design.
- **Next role's first step (planner):** read §7 and write `plan.md`
  with the exact file tree, the top-20 selection and cleaning rules,
  the backtest windows, the per-cluster winner rule, and the §8
  checklist.
