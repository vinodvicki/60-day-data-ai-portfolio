# Day 10 — Retail Sales Intelligence Dashboard: Research Brief

**Status:** RESEARCH COMPLETE — verified live 2026-11-14 (one lean probe pass).
**Business question:** Which products, countries and seasons drive revenue for
a UK online retailer, and where are the three biggest commercial opportunities?

## 1. Data source — verified live

### 1a. PRIMARY — UCI Online Retail (Chen, 2015)

- **Source:** UCI Machine Learning Repository, dataset **"Online Retail"**,
  dataset ID **352**, DOI **https://doi.org/10.24432/C5BW33**.
- **Dataset page (verified 2026-11-14, HTTP 200):**
  `https://archive.ics.uci.edu/dataset/352/online+retail`
- **Download (verified 2026-11-14, HTTP 200):**
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  — a ZIP containing `Online Retail.xlsx` (**22.6 MB** per the dataset page).
  No key, no account, no documented rate limit; one single download is the
  whole fetch. On HTTP failure, wait 60 s, retry once, then stop and report.
- **Coverage verified from the dataset page:** **541,909 instances**,
  8 variables. The page states the data are "all the transactions occurring
  between 01/12/2010 and 09/12/2011 for a UK-based and registered
  non-store online retail" — the coder MUST confirm the date range from
  the downloaded file itself (it was not re-verified in the probe pass)
  and record the confirmed range in `data_source.json` and `data/README.md`.
- **Fields (8):** `InvoiceNo` (string; cancellations start with `C`),
  `StockCode` (string), `Description` (string), `Quantity` (int),
  `InvoiceDate` (datetime), `UnitPrice` (float, GBP), `CustomerID`
  (float/int, missing for some rows), `Country` (string).
- **Expected quirks (coder must verify counts from the file, not trust
  this list):**
  - Cancelled invoices (`InvoiceNo` starting with `C`) carry negative
    `Quantity` — exclude from revenue, count them separately.
  - Some rows have negative `Quantity` without a `C` prefix, zero or
    negative `UnitPrice`, and missing `Description` (adjustment/bad-debt
    codes such as `POST`, `DOT`, `BANK CHARGES`, `M`).
  - `CustomerID` is missing on a substantial share of rows (guest /
    unidentified transactions) — customer-level analysis (RFM, clustering)
    uses identified customers only; the share excluded must be reported.
  - `Description` is free text; there is **no product-category column** —
    product mix must be derived (top SKUs by revenue/units, plus a
    keyword-derived product group, documented as derived, not source data).
  - Prices are in GBP; the dataset is a single UK retailer, so the
    "regional variation" is country of the *customer*, dominated by the UK.
- **Licence / attribution:** **CC BY 4.0** (stated on the dataset page).
  Cite: "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning
  Repository. https://doi.org/10.24432/C5BW33". Attribution must appear in
  `data/README.md`, the notebook, and the day README.
- **Data-size rule:** the raw XLSX (22.6 MB) is far over the 1 MB/file
  guideline — it is **git-ignored** and re-downloaded at build time (same
  pattern as Day 8's 19 MB CSV). Committed data = processed aggregate
  CSVs + a 1,000-row cleaned sample, total under 5 MB/day. The pipeline
  must run end-to-end from the downloaded file with no manual step.

### 1b. Ruled out

- **UCI Online Retail II (dataset 502, 2009–2011):** a superset of the
  same retailer; heavier file, no extra analytical value for a one-day
  dashboard — not needed.
- **Kaggle copies of Online Retail:** require a Kaggle account/token;
  the UCI direct download needs neither.
- **Synthetic-only build:** rejected — the roadmap names UCI Online
  Retail and the live file is reachable; synthetic is fallback only (§4).

## 2. Metrics to compute

- **Revenue:** `Quantity × UnitPrice` per line, summed after cleaning
  (cancellations, non-positive prices and non-product adjustment rows
  excluded; exclusions counted and reported). All revenue in GBP.
- **KPIs (defined once, used everywhere):** total revenue, total units
  sold, number of orders (distinct non-cancelled `InvoiceNo`),
  average order value (revenue / orders), unique customers, repeat-customer
  rate (customers with ≥ 2 orders / all customers), revenue per customer.
- **Product mix:** top 10 SKUs by revenue and by units; keyword-derived
  product groups (planner defines the grouping rule — e.g. leading
  keywords of `Description`); revenue share of the top 10 SKUs
  (concentration) and of the top product group.
- **Regional variation:** revenue / orders / AOV by country (top 10 +
  "Other"); UK share of revenue; non-UK AOV vs UK AOV.
- **Seasonality:** monthly revenue, units and orders; month-over-month
  growth; weekday and hour-of-day patterns (from `InvoiceDate`); the
  peak month and the December spike, quantified.
- **Customer clustering (roadmap "clustering" skill):** RFM per identified
  customer (Recency = days since last purchase to the dataset end,
  Frequency = orders, Monetary = revenue), standardised, KMeans k = 4
  (planner confirms k from the silhouette check; no tuning grid).
  Report cluster sizes, centroid RFM values and a plain-language label
  per cluster. This is descriptive segmentation, not a churn model.
- **Demand forecast (roadmap "demand forecasting" skill):** monthly
  revenue, 3 months ahead, with methods (a) seasonal naïve (same month
  last year) as the baseline and (b) Holt-Winters (additive trend +
  additive seasonality, period 12) as the candidate. Backtest on the
  last 3 months (train to 3 months before the end, forecast 3 months);
  report RMSE/MAE for both and publish the lower-RMSE method. Note the
  series is only 12 months long, so seasonality is estimated from a
  single year — disclose this as a limitation, do not over-claim.
- **SQL (roadmap skill):** an in-memory SQLite check in the notebook —
  monthly revenue + top-10-countries aggregation via SQL, asserted equal
  to the pandas result (as Days 8–9 did). No external database.
- **Power BI (roadmap skill):** no `.pbix` is produced (same decision as
  Days 8–9 — a `.pbix` cannot be built or verified in this environment);
  the KPI dashboard is delivered as the Streamlit app + the 4 static
  charts. Recorded here so the planner does not re-litigate it.
- **Recommendations:** exactly three commercial recommendations, each tied
  to a measured number (roadmap deliverable). The planner fixes which
  three after the numbers are known; each must name the evidence, the
  action, and the expected effect in measured terms.

## 3. Licence / attribution

CC BY 4.0 — attribution line in §1a, required in `data/README.md`, the
notebook, and the day README. No licence-file changes (portfolio LICENSE
already covers the code).

## 4. Synthetic-fallback note

Only if the live download fails: build a clearly-labelled synthetic
transactional dataset from documented parameters — 12 months, ~40,000
orders, 5 countries, 200 SKUs, lognormal basket sizes, December uplift
×1.8, seed 42 — stored as `data/raw/*_synthetic.csv`, `data_source.json`
`synthetic: true`, and labelled "SYNTHETIC — NOT REAL DATA" in every
chart, the notebook, and the README. **The live download works (verified
above), so the fallback is contingency only; the coder must not use it
unless the live call fails.**

## 5. Verification status

- [x] Source confirmed against the official UCI page (2026-11-14):
  dataset 352, 541,909 instances, 8 variables, CC BY 4.0, DOI
  10.24432/C5BW33. Download URL
  `https://archive.ics.uci.edu/static/public/352/online+retail.zip`
  returned HTTP 200; file listed as `Online Retail.xlsx`, 22.6 MB.
- [x] Conflicts recorded with resolution:
  - The dataset has **no product-category column** — resolved by deriving
    product groups from `Description` keywords, documented as derived.
  - The raw file (22.6 MB) exceeds the commit-size rule — resolved by
    git-ignoring it and committing aggregates + a 1,000-row sample
    (Day 8 pattern).
  - The monthly series is only 12 months — resolved by disclosing the
    single-year seasonality limit and keeping the forecast horizon at
    3 months with a backtest.
  - Stated date range (2010-12-01 → 2011-12-09) comes from the dataset
    documentation, **not** re-verified in the probe — the coder confirms
    it from the file.
- [ ] No live download performed by the researcher (that is the coder's
  job); the probe was the dataset page + a HEAD on the download URL only.

## 6. Open items for the planner

1. Fix the product-group derivation rule (keyword list) and the KMeans k
   (provisional 4, confirm from the silhouette check).
2. Fix the cleaning rules precisely (which StockCodes/descriptions count
   as non-product adjustments; how cancelled invoices are treated).
3. Decide the committed-data set (aggregates + sample) so the day folder
   stays under the 5 MB limit with the raw file git-ignored.
4. Fix the three-recommendation structure (evidence → action → expected
   effect) and which dashboard panels carry them.
5. Confirm the forecast backtest design (3-month holdout) and the
   single-year seasonality disclosure wording.

## Handoff

- **Produced:** `research_brief.md` (this file).
- **Verified numbers:** UCI dataset 352, 541,909 rows, 8 columns, CC BY 4.0,
  download HTTP 200, XLSX 22.6 MB.
- **Known gaps:** date range to be confirmed from the file by the coder;
  cleaning counts unknown until the file is profiled.
- **Next role's first step (planner):** read §6 and write `plan.md` with
  the exact file tree, cleaning rules, product-group rule, and §8 checklist.
