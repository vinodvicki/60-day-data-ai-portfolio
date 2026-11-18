# Day 12 — Customer Segmentation Engine: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-16) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Customer Segmentation Engine. Problem: use
recency, frequency, monetary value, and clustering to distinguish customer
groups and retention opportunities. Deliverable: RFM segments with tailored
action suggestions. Core skills: SQL, Power BI, clustering, demand
forecasting. Suggested data: UCI Online Retail."
Section context (Days 10–12, Retail & E-Commerce).

| Item | Value |
|---|---|
| Fetch date | 2026-11-16 |
| Source | UCI Online Retail, dataset 352, DOI 10.24432/C5BW33, CC BY 4.0 — primary `https://archive.ics.uci.edu/static/public/352/data.csv` (HTTP 200 verified, 45,038,760 bytes ≈ 43.0 MB); fallback legacy XLSX `https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx` (HTTP 200 verified, 23,715,344 bytes ≈ 22.6 MB) |
| Expected rows | **541,909 rows**, 8 columns (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country) |
| Date range | 2010-12-01 → 2011-12-09 (DD/MM/YYYY as published) — **coder confirms from the file** and records the confirmed range |
| Deliverable | RFM segments (one row per customer, one segment each) with a tailored action suggestion per segment, each with the £ at stake |
| Scope | Analytical exercise on public historical retail transactions (2010–2011). **Not a current-market or forward-trading tool.** Scores are relative to this customer base, not absolute. |

## 1. Problem statement + audience

**Problem.** A UK online retailer has ~4,300 identified customers but no
picture of who they are: a small core may drive most of the revenue
(Day 10 found 222 customers, 5.12%, driving 47.94% of identified-customer
revenue), a large tail may have bought once and never returned, and a
middle group may be quietly slipping away. The retailer needs to know,
for each customer group, who is worth protecting, who is slipping away,
and who is already gone — and what to do differently for each group.
This project computes Recency, Frequency and Monetary value per customer,
scores them, clusters them, and turns each resulting segment into one
tailored action with the £ at stake. The dataset is the same messy real
retail data as Days 10–11 — cancelled orders, negative quantities,
missing customer IDs, postage and adjustment lines — so the cleaning
rules are part of the deliverable: every exclusion is counted, and every
number traces to the cleaned RFM table defined in §3.2/§4.1.

**Three hard limits are stated up front and labelled on every surface
(README, notebook, insights, dashboard, charts, segment table):**

1. **RFM scores are relative to this customer base, not absolute.** A
   score of 5 means "top fifth of these customers", not "good" in any
   absolute sense. Recompute if the base changes.
2. **The data is 2010–2011 — the segments describe that year, not
   today.** No claim is made about current customers; the actions are
   the *kind* of action each segment warrants, illustrated with this
   year's £.
3. **14.80% of cleaned revenue has no CustomerID (Day 10 figure —
   coder re-derives the exact share, §3.2 rule 8) and cannot be
   attributed to any segment.** Segment revenue shares are reported
   against attributed revenue AND against total cleaned revenue, so the
   unattributed gap is visible, never hidden.

**Audience / decision-maker.** A retail / CRM manager (non-technical
reader of the README and the segment table) who needs to know which
customers to protect, which to win back, and which to stop spending on —
and a data reviewer checking the method, who wants a documented cleaning
pipeline with counted exclusions, a re-derived (not copied) choice of k,
a stated decider rule for when methods disagree (§2.0), and an
agreement rate that is reported, not hidden.

## 2. Decisions (frozen)

### 2.0 THE DECIDER RULE — first decision, non-negotiable

Day 11 measured that SBC quadrants vs KMeans (k=4) agreement was only
**64.0%** — the methods genuinely disagree about roughly a third of
customers. This plan therefore states up front which method decides
segment assignment, and it is exactly one method:

- **DECIDER: KMeans on log1p-transformed, StandardScaler-scaled R/F/M
  is the single source of segment assignment.** Every customer is
  assigned to exactly one segment by their KMeans cluster (§4.3). The
  cluster is then *named* from its median RFM quintile-score profile
  via the fixed naming rule (§4.2) — so the customer-facing output
  is named RFM segments (Champions, Loyal Customers, …), but **KMeans
  decides the boundaries and the assignment**, not the RFM-score rule.
- **RFM quintile scores are the descriptive / explanatory layer only.**
  They name the segments, populate the profile table (§4.5) and Chart
  02, and explain *why* a segment is called what it is. They never
  reassign a customer: no customer is moved between segments because
  their RFM code "looks like" another segment.
- **SBC quadrants are an interpretive cross-check only.** The agreement
  rate — the share of multi-order customers whose KMeans segment maps
  to their SBC quadrant under the best one-to-one mapping (§4.4) — is
  reported in the notebook, insights, dashboard and
  `data_source.json`, with the full segment × quadrant contingency
  table in `agreement.csv`. Disagreements are reported, never averaged
  away and never used to override a KMeans assignment.
- **Tester gate (mandatory):** the tester verifies the decider was
  actually used — the `segment` column in `rfm_table.csv` must equal
  the KMeans-label → name mapping for every customer (a test asserts
  this on fixtures and on the committed file), and a test asserts that
  no customer is assigned by the RFM-score rule alone. If the segment
  column cannot be reproduced from the KMeans labels, the build fails.
- **No surface** (README, notebook, insights, dashboard, chart) may
  present RFM-score segments and KMeans segments as if they were the
  same grouping, and no surface may report a segment without saying
  KMeans decided it.

### 2.1 Research questions (exactly 3)

1. **Which customer groups does this retailer actually have?** RFM
   quintile scores + KMeans clustering (§4.1–§4.3) produce the
   segments, each described by n, share of customers, share of
   revenue, and mean/median R/F/M (§4.5).
2. **Who is worth protecting, who is slipping away, and who is already
   gone?** The per-segment profile (§4.5) ranks segments by revenue
   concentration and recency; the SBC cross-check (§4.4) shows whether
   the data-driven groups line up with demand-pattern quadrants, with
   the agreement rate reported.
3. **What should the retailer do differently for each group?** Exactly
   one tailored action per segment (§4.5), each with the £ at stake
   where computable — the roadmap deliverable.

### 2.2 Other frozen decisions

- **k is re-derived, not copied.** k is chosen from k = 2..8 by
  silhouette score (primary) + elbow SSE (reported), §4.3. Day 10's
  k = 4 is a precedent, not a prescription; if the re-derived k
  differs, the plan's k differs and the difference is reported.
- **RFM scoring is percentile-rank based, not qcut** (§4.1) — this
  sidesteps the brief's qcut duplicate-edge trap deterministically.
  Noted as a brief-vs-plan difference in §11.
- **SBC unit fixed:** ADI in **weeks** (mean inter-order gap in days
  ÷ 7); CV² from **per-order £ totals** (§4.4). Single-order
  customers get quadrant `Single-order` and are excluded from the
  agreement-rate denominator.
- **No partial-week exclusion for Day 12** (unlike Day 11): RFM is
  computed over the full cleaned window, snapshot 2011-12-10 (§4.1).
  Noted in §11.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** UCI Machine Learning Repository, dataset **"Online
  Retail"**, dataset ID **352**, DOI `10.24432/C5BW33`, Chen (2015).
  Dataset page `https://archive.ics.uci.edu/dataset/352/online+retail`.
- **Download — PRIMARY (verified 2026-11-16, HTTP 200):**
  `https://archive.ics.uci.edu/static/public/352/data.csv` — full GET
  probe measured **45,038,760 bytes (~43.0 MB)**; header row confirmed:
  `InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country`;
  first data row `536365,…,12/1/2010 8:26,2.55,17850,United Kingdom`.
  No key, no account, no documented rate limit; one single download is
  the whole fetch. **Read with `encoding="ISO-8859-1"` (latin-1) and
  `dayfirst=True` dates (DD/MM/YYYY as published).** HEAD returns no
  `Content-Length`/`Content-Type` — do not rely on headers; verify by
  the row/column counts in §3.3.
- **Download — FALLBACK (verified 2026-11-16, HTTP 200):** legacy XLSX
  `https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx`
  (**23,715,344 bytes, ~22.6 MB**). Use only if the CSV download fails
  twice (§3.3). **The XLSX does NOT live at
  `https://archive.ics.uci.edu/static/public/352/Online%20Retail.xlsx`
  (HTTP 404)** — do not use that path.
- **Coverage verified from the dataset page + metadata API:**
  **541,909 instances**, 8 variables in the variables table. Stated
  range 2010-12-01 → 2011-12-09 — coder confirms from the file and
  records the confirmed range in `data_source.json` and
  `data/README.md`. **Page inconsistency to record, not resolve by
  guessing:** the page header says "# Features 6" while the variables
  table lists 8 columns — the file itself is authoritative (Days 10–11
  also found 8 columns).
- **Fields (8):** `InvoiceNo` (string; cancellations start with `C`),
  `StockCode` (string), `Description` (string), `Quantity` (int),
  `InvoiceDate` (datetime), `UnitPrice` (float, GBP), `CustomerID`
  (float/int, missing on some rows), `Country` (string).
- **Licence / attribution:** **CC BY 4.0** (stated on the dataset page).
  Cite verbatim in `data/README.md`, the notebook and the day README:
  > Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning
  > Repository. https://doi.org/10.24432/C5BW33
  Also cite Chen, Sain & Guo (2012) as the RFM-segmentation source
  paper for this exact dataset.

### 3.2 Cleaning rules (frozen — the tester tests these)

Applied in this order; every step's excluded-row count is recorded in
`data_source.json` and reported in `data/README.md`. Same ordered list
as Days 10–11 §3.2, re-applied here because the raw file is the same —
the counts are re-derived from the file, not copied from Days 10–11:

1. **Parse:** read the CSV (`encoding="ISO-8859-1"`, `dayfirst=True`).
   Parse `InvoiceDate` to datetime. Drop rows where `InvoiceDate` is
   unparseable (count them; expected 0).
2. **Cancellations:** rows whose `InvoiceNo` starts with `C` are
   cancellations. Count them separately (`n_cancelled_invoices`,
   `n_cancelled_rows`) and **exclude** them from all RFM analysis.
3. **Non-positive quantity:** after removing cancellations, drop rows
   with `Quantity <= 0` (count them — these are returns/adjustments
   without a `C` prefix). RFM rows must have `Quantity > 0`.
4. **Non-positive price:** drop rows with `UnitPrice <= 0` (count them).
5. **Non-product adjustment lines:** drop rows whose `StockCode` is in
   the adjustment list — `POST`, `DOT`, `M`, `D`, `BANK CHARGES`,
   `CRUK`, `C2`, `AMAZONFEE` — **plus** any row whose `Description`
   (uppercased, stripped) is in `{"POSTAGE", "DISCOUNT", "MANUAL",
   "BANK CHARGES", "AMAZON FEE", "CRUK"}`. The coder profiles the
   actual distinct `StockCode`/`Description` values first: if a code on
   this list does not occur, it is simply recorded as 0; if an
   *additional* adjustment code occurs, the coder adds it to the list
   **only** if it is plainly non-product, records the addition in
   `data_source.json`, and does not silently drop any code that looks
   like a real product. The final list is frozen in
   `data_source.json`.
6. **Missing description:** drop rows with missing/blank `Description`
   (count them; expected small).
7. **Line revenue:** `line_revenue = Quantity × UnitPrice` (GBP) on the
   cleaned set. No currency conversion, no tax adjustment (the dataset
   does not state whether prices include VAT — disclosed as a
   limitation).
8. **Missing CustomerID — RFM scope (differs from Day 11, frozen
   here):** rows with missing `CustomerID` are **excluded from RFM and
   clustering only** (they cannot be attributed to a customer). Count
   them (`n_missing_customer_rows`, `revenue_missing_customer_gbp`,
   `revenue_missing_customer_share`) and report the unattributed
   revenue as its own line in the segment profile (§4.5) so segment
   revenue shares do not silently sum to 100%. Day 10 reported the
   unattributed share as **14.80% of cleaned revenue** — the coder
   re-derives the exact figure from the file and records it; if it
   differs materially, the recorded figure governs. (Day 11 kept
   missing-CustomerID rows in demand because demand is summed over all
   customers; Day 12 cannot do that because RFM is per customer.)
9. **No partial-week exclusion:** unlike Day 11, no date-window trimming
   is applied — RFM uses the full cleaned window (§4.1).

### 3.3 Fetch rules

- One `GET` per build; cache under `data/raw/` and re-use it
  (`--offline` / `--use-cache` per the Day 1 pattern). One retry after
  60 s on HTTP 429/5xx, then fall back to the legacy XLSX URL (one
  attempt + one retry), then stop and report — never hammer the host.
- Verify after fetch: file downloads, row count = 541,909, 8 columns
  with the exact names in §3.1. Record the verified counts in
  `data_source.json`. If a count differs, report it — do not silently
  proceed.

### 3.4 Data-size exception and commit rule (READ CAREFULLY — Day 8 precedent)

- The raw CSV is **~43.0 MB** (fallback XLSX 22.6 MB) — far over the
  portfolio rule (files < 1 MB each, < 5 MB per day folder). Therefore
  the **DATA-SIZE EXCEPTION** applies to this day only (same mechanism
  as Days 8–11):
  - **`.gitignore` MUST exclude the raw data:** `data/raw/data.csv`,
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
| `data/processed/data_source.json` | Source, URL, DOI, licence, fetch date, row counts (raw / cleaned / cancelled / excluded per rule / missing-CustomerID rows + revenue share), confirmed date range, snapshot date, adjustment-code list, RFM definitions, scoring method, k-selection (elbow SSE + silhouette per k, chosen k + rule outcome), KMeans parameters, segment-naming mapping (cluster → name + median scores), SBC parameters + quadrant counts, agreement rate + mapping method, manual validation, versions |
| `data/processed/rfm_table.csv` | One row per identified customer (~4,334 expected — coder confirms): `customer_id`, `recency_days`, `frequency`, `monetary_gbp`, `r_score`, `f_score`, `m_score`, `rfm_code`, `rfm_score`, `kmeans_cluster`, `segment`, `sbc_quadrant` |
| `data/processed/segment_profile.csv` | One row per segment (§4.5 columns, in order): `segment`, `n_customers`, `share_customers`, `revenue_gbp`, `revenue_share_attributed`, `revenue_share_total`, `mean_recency_days`, `median_recency_days`, `mean_frequency`, `median_frequency`, `mean_monetary_gbp`, `median_monetary_gbp`, `mean_rfm_score`, `median_r_score`, `median_f_score`, `median_m_score`, `action`, `gbp_at_stake` — plus one `Unattributed (no CustomerID)` row carrying the unattributed revenue (n_customers blank/0, action `—`) |
| `data/processed/sbc_summary.csv` | One row per SBC quadrant + `Single-order`: `quadrant`, `n_customers`, `share_customers`, `revenue_gbp`, `revenue_share_attributed` |
| `data/processed/agreement.csv` | Segment × SBC-quadrant contingency table (rows = segments, columns = Smooth / Erratic / Intermittent / Lumpy / Single-order, cells = customer counts); agreement rate recorded in `data_source.json`, not in this file |
| `data/raw/sample_rows.json` | 1,000 cleaned rows, provenance sample, clearly labelled as a sample |

- The full raw CSV/XLSX is **not** committed (size). It is rebuilt by
  `python -m src.data_pipeline --live` from the live URL, and the
  notebook re-runs the segmentation from it when present (§6, notebook
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

- **Synthetic fallback (only if both download URLs fail):** per brief §4
  — retry once after 60 s per URL, then stop and report to the
  orchestrator — **do not silently substitute synthetic data**. If a
  synthetic fallback were ever authorised, it must be built from the
  brief's documented parameters (~4,300 customers / ~540k line rows,
  seed 42), stored as `data/raw/*_synthetic.csv` (git-ignored, NEVER
  overwrites real data), recorded in `data_source.json` as
  `synthetic: true, seed: 42`, and labelled "SYNTHETIC — NOT REAL DATA"
  in every chart, the notebook, and the README. Methods (§4) are
  unchanged. Not expected to be needed (both URLs probed HTTP 200).
- **Licence: CC BY 4.0.** Attribution verbatim in README.md,
  data/README.md, the notebook and the dashboard footer (§3.1).
- **No Power BI file:** no `.pbix` is produced (same decision as
  Days 8–11 — a `.pbix` cannot be built or verified in this
  environment); the segmentation is delivered as the Streamlit app +
  static charts. Recorded here so the coder does not re-litigate it.
  The SQL skill is covered by the §4.6 check.

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 RFM definitions (DECIDED — exact)

- **Snapshot ("reference") date: 2011-12-10** = max(InvoiceDate) + 1
  day. The coder confirms max(InvoiceDate) = 2011-12-09 from the file;
  if it differs, the snapshot moves with it and the confirmed value is
  recorded.
- **Recency (R)** = snapshot date − customer's most recent InvoiceDate,
  in **days**. Lower = better (more recent). Range 1–374 days on this
  window.
- **Frequency (F)** = count of **distinct InvoiceNo** per customer (not
  line-item rows). Higher = better. Computed on the cleaned rows (§3.2).
- **Monetary (M)** = Σ (Quantity × UnitPrice) per customer, in **GBP**,
  over the same cleaned rows. Higher = better.
- **RFM scoring — percentile-rank method (frozen, §2.2):** each of R, F,
  M is scored 1–5 from its percentile rank across the customer base,
  ties sharing the same score (`rank(pct=True, method="average")`):
  F and M: `score = clip(ceil(pct × 5), 1, 5)` (top fifth = 5). R:
  inverted — `score = clip(6 − ceil(pct × 5), 1, 5)` where pct is the
  rank of Recency ascending (most recent = 5). Concatenated code
  `RFM = R·100 + F·10 + M` (e.g. 555 = best, 111 = worst);
  `RFM_score = R + F + M`, range 3–15. Scores are **relative** to this
  customer base — recompute if the base changes. This method is
  deterministic, gives ties equal scores, and cannot fail on duplicate
  bin edges (the brief's qcut trap, §11).
- **Customer base:** every CustomerID with ≥ 1 cleaned row. Expected
  ~4,334 customers (Day 10's segment counts sum to 4,334) — coder
  confirms; the confirmed count governs.

### 4.2 Segment naming rule (DECIDED — fixed prototype mapping)

KMeans clusters are named by their median RFM quintile-score profile
(median R/F/M scores across the cluster's customers). Name pool with
fixed prototypes (median-score triples), in tie-break order:

| Name | Prototype (R, F, M) | Plain meaning |
|---|---|---|
| Champions | (5, 5, 5) | Bought recently, often, spend most |
| Loyal Customers | (4, 4, 4) | Buy often and spend well |
| Big Spenders | (3, 3, 5) | Spend most per customer, less frequent |
| Potential Loyalists | (5, 2, 3) | Recent, low frequency so far — growing |
| New Customers | (5, 1, 1) | Recent, single/first purchase |
| At Risk | (2, 4, 4) | Used to buy often/spend, now quiet |
| Hibernating | (2, 2, 2) | Last purchase long ago, low everything |
| Lost | (1, 1, 1) | Lowest on all three — gone |

**Assignment rule (frozen):** for each KMeans cluster, compute its
median (R_score, F_score, M_score); assign the unused name whose
prototype is closest in Euclidean distance to that median triple;
each name is used at most once (greedy by smallest distance first,
ties broken by the pool order above). The mapping cluster → name +
median triple is recorded in `data_source.json` and
`segment_profile.csv`. With k ∈ 2..8 (§4.3) and 8 names, the pool never
runs out. If two clusters' median triples are identical, the
smaller-distance tie-break above still assigns distinct names — record
it if it happens. The names are labels for KMeans clusters, not
RFM-code thresholds: a customer with code 555 is NOT automatically a
Champion — they are a Champion only if their KMeans cluster is named
Champions (§2.0).

### 4.3 KMeans clustering — the decider (DECIDED)

- **Inputs:** R, F, M per customer, `log1p`-transformed first (all three
  are right-skewed), then `StandardScaler`. **Never cluster raw R/F/M:**
  Monetary's scale would dominate.
- **Choose k by elbow + silhouette together (re-derived):** k = 2..8,
  `KMeans(random_state=42, n_init=10)` per k; record within-cluster SSE
  (elbow) and silhouette score per k in `data_source.json`.
  **Selection rule (frozen): k = argmax silhouette; if two k values
  are within 0.01 of silhouette, pick the smaller k.** Day 10's k = 4
  (silhouette 0.616) is orientation only — do not copy it; report the
  re-derived k and silhouette, and say plainly if they differ.
- **Output:** `kmeans_cluster` (0..k−1) per customer in `rfm_table.csv`;
  per-cluster centroids in original units (median R days, median F,
  median M £) in `segment_profile.csv` and the notebook, so segments
  are interpretable; cluster sizes and revenue shares in
  `segment_profile.csv`.
- **Determinism:** fixed `random_state=42`, `n_init=10`; a test asserts
  identical labels across runs.

### 4.4 SBC quadrants + agreement rate (DECIDED — cross-check only)

- **Per-customer SBC statistics** over the full cleaned window, per
  customer (not per SKU — Day 11's unit was the SKU; Day 12's unit is
  the customer):
  - **ADI (weeks)** = mean gap between successive distinct order dates,
    in days ÷ 7. Threshold **1.32**.
  - **CV²** = (std ÷ mean)² of the customer's **per-order £ totals**
    (order value = Σ line values per InvoiceNo), non-zero orders only.
    Threshold **0.49**.
  - Quadrants: Smooth (ADI ≤ 1.32, CV² ≤ 0.49) · Erratic (ADI ≤ 1.32,
    CV² > 0.49) · Intermittent (ADI > 1.32, CV² ≤ 0.49) · Lumpy
    (ADI > 1.32, CV² > 0.49). Use 1.32/0.49 (the SBC-published rounded
    convention Day 11 used); note the Kostenko & Hyndman caveat that
    the exact theoretical cut-offs are 4/3 (≈1.333) and 0.5.
- **Single-order customers:** ADI is undefined for F = 1. They get
  `sbc_quadrant = "Single-order"`, are counted in `sbc_summary.csv`,
  and are **excluded from the agreement-rate denominator** (they have
  no demand pattern to compare).
- **Agreement rate (frozen definition):** over multi-order customers
  only, build the segment × quadrant contingency table
  (`agreement.csv`); choose the one-to-one segment↔quadrant mapping
  that maximises matched customers (greedy by largest cell first);
  **agreement rate = matched customers ÷ multi-order customers**.
  Report the rate (Day 11: 64.0% — Day 12 re-derives its own) in the
  notebook, insights, dashboard and `data_source.json`, alongside the
  contingency table. **SBC never overrides a KMeans assignment (§2.0).**

### 4.5 Segment profile + tailored actions (DECIDED — roadmap deliverable)

- **Profile table** (`segment_profile.csv`, columns in §3.5 order): one
  row per segment — n, share of customers, revenue £, revenue share of
  attributed revenue, revenue share of total cleaned revenue, mean and
  median R (days), F, M (£), mean RFM score, median R/F/M scores —
  plus the `Unattributed (no CustomerID)` row (§3.2 rule 8).
- **Exactly one tailored action per segment** (the roadmap deliverable),
  in `segment_profile.csv` (`action`), the insights summary, the
  dashboard and the README. Each action names the segment, the
  behaviour it targets, and the **£ at stake** (`gbp_at_stake` =
  the segment's `revenue_gbp`): for Champions / Loyal / Big Spenders
  the £ is "revenue to protect"; for At Risk / Hibernating / Lost it is
  "revenue at risk / already lapsed" (their M total — money that will
  not repeat unless acted on); for Potential Loyalists / New Customers
  it is "revenue to grow" (their M total as the base to build on). The
  coder drafts the actions from the computed numbers (e.g. win-back
  offer for At Risk, reactivation or stop-spending for Lost, VIP
  retention for Champions); the optimizer verifies each £ figure
  against the committed CSVs. One action per segment, no second action,
  no action without a £ figure. Segments that do not occur at the
  chosen k get no row and no action (never invent one).

### 4.6 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `rfm_table.csv` + `segment_profile.csv` loaded into an
in-memory SQLite database (`sqlite3`, stdlib): customer count and total
revenue per segment, and the top segment by revenue, asserted equal to
the pandas result. A test asserts the SQL and pandas numbers agree. This
is the day's SQL element; no `.pbix` is built (§3.6) and the pipeline
itself stays pandas.

### 4.7 Insights structure (DECIDED)

`outputs/insights_summary.md` carries one finding per §2.1 question with
exact numbers, the per-segment action table (segment, n, revenue £,
action), and limitations (2010–2011 data, relative scores, VAT status
unknown, unattributed revenue, SBC/KMeans disagreement reported with
the agreement rate). No finding without a number; no extra
recommendations beyond the one-action-per-segment table.

## 5. File tree (exact — build only this)

```
day-12-customer-segmentation-engine/
├── README.md  requirements.txt  .gitignore  pyproject.toml  LICENSE
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   └── sample_rows.json        (1,000 cleaned rows, provenance sample)
│   └── processed/
│       ├── data_source.json
│       ├── rfm_table.csv           (~4,334 rows, one per customer)
│       ├── segment_profile.csv     (k rows + 1 unattributed row)
│       ├── sbc_summary.csv         (5 rows: 4 quadrants + Single-order)
│       └── agreement.csv           (segment × quadrant contingency)
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── rfm.py
│   ├── clustering.py
│   ├── actions.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_rfm_scores.png
│       ├── 02_segment_value.png
│       ├── 03_kmeans_clusters.png
│       └── 04_sbc_quadrants.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No `data/raw/*.csv` or
`*.xlsx` on disk at handoff (git-ignored, §3.4). No extra modules, no
extra charts, no `.pbix`, no model card. The scaffold's `requirements.txt`
is Day 1's list — the coder replaces it with the §6 pinned stack.

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download CSV (primary; 1 retry after 60 s on 429/5xx, then fallback XLSX, then stop and report; one plain full download — server ignores Range), read CSV (`encoding="ISO-8859-1"`, `dayfirst=True`) or XLSX (`openpyxl`) for the fallback; verify counts 541,909 / 8 columns; apply cleaning rules §3.2 in order, counting every exclusion; compute R/F/M per customer (§4.1); write `sample_rows.json`, `rfm_table.csv` (without cluster/segment columns at this stage — those are added by `clustering.py`), and `data_source.json` (live fields); modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42). `--offline` skips writing `data_source.json` when a live record exists (§3.5). |
| `src/rfm.py` | Pure RFM functions, no I/O, no network — all tested: `compute_rfm(df, snapshot)` → per-customer R/F/M; `score_rfm(rfm)` → R/F/M quintile scores by the percentile-rank method (§4.1), `rfm_code`, `rfm_score`; `line_revenue(qty, price)` |
| `src/clustering.py` | Pure + thin I/O functions — all tested: `cluster_customers(rfm, k, seed=42)` (log1p + StandardScaler + KMeans, returns labels + per-k SSE/silhouette via `select_k(rfm, k_range=range(2, 9))`); `name_segments(profile_medians)` implementing the §4.2 prototype rule; `sbc_stats(orders)` → per-customer ADI (weeks) + CV²; `classify_sbc(adi, cv2)` → Smooth / Erratic / Intermittent / Lumpy / Single-order; `agreement_rate(contingency)` (greedy best one-to-one mapping, §4.4); `build_segment_profile(rfm_table)` → `segment_profile.csv` rows |
| `src/actions.py` | Pure functions, no I/O, no network — all tested: `action_for(segment, profile_row)` → the exactly-one action string for that segment, embedding its £ at stake; `gbp_at_stake(profile_row)`; `build_actions(segment_profile)` → fills `action` + `gbp_at_stake` columns |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source + CC BY 4.0 attribution + "historical 2010–2011 data — scores relative to this customer base" + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (identified customers, total cleaned revenue £, attributed revenue £, top segment + its revenue share, agreement rate %); segment table (all §4.5 columns incl. action + £ at stake, with the Unattributed row shown separately); the 4 charts embedded; methods + limitations panel (2010–2011 data, relative scores, KMeans decides per §2.0, SBC cross-check with agreement rate, unattributed revenue); `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with CC BY 4.0 attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): EDA on the committed tables (cleaning audit, unattributed-revenue share, country mix); RFM distributions; k-selection (elbow + silhouette table); KMeans segments + naming; SBC quadrants + agreement rate with contingency table; the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.6); **segmentation section guarded by `RAW.exists()`** — if the raw CSV/XLSX is present it re-runs RFM + KMeans via `src.rfm` / `src.clustering` and asserts the results match the committed CSVs within tolerance; if absent it loads the committed CSVs and prints a note that the re-run was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: revenue = Quantity × UnitPrice on fixtures; cancellation rows excluded (InvoiceNo `C…`); Quantity ≤ 0 and UnitPrice ≤ 0 excluded; adjustment StockCodes excluded; missing CustomerID excluded from RFM but counted with its revenue share; snapshot date = max date + 1 day; Recency/Frequency (distinct InvoiceNo)/Monetary on fixtures; percentile-rank scores in 1–5, monotonic in R/F/M, ties share a score, R inverted; RFM code/score arithmetic (555 → 15); log1p+scaling used before KMeans (monetary scale does not dominate — assert on fixtures); KMeans deterministic (same labels, seed 42); k-selection picks argmax silhouette with the 0.01 smaller-k tie-break on fixtures; segment naming follows the §4.2 prototype rule (Champions prototype → Champions; distinct names per cluster); **decider test — segment column equals the KMeans-label → name mapping for every row, and no row is assigned by the RFM-score rule alone**; SBC quadrant boundaries (1.32 / 0.49) + Single-order for F = 1; agreement rate on fixtures (perfect match → 1.0; known mismatch → exact value); one action per segment, each embedding its £ at stake; offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.6) |
| `data/README.md` | Provenance: URL, DOI, CC BY 4.0 licence, fetch date, row counts (raw 541,909 / cleaned / excluded per rule / missing-CustomerID rows + revenue share), confirmed date range, snapshot date, adjustment-code list, RFM definitions + scoring method, k-selection outcome, decider rule (§2.0), SBC parameters + quadrant counts, agreement rate, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2.1 question with exact numbers + the per-segment action table (§4.7) + limitations (2010–2011 data, relative scores, prices VAT status unknown, unattributed revenue, SBC/KMeans disagreement with agreement rate) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, the per-segment action table, the decider rule (§2.0) stated plainly, validation, limitations, attribution |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 11 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat, scikit-learn, scipy, statsmodels — **drop statsmodels**: no ETS/forecasting this day) **plus openpyxl** (fallback XLSX reading). No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88); `.gitignore` per §3.4 (raw-data lines are the only data exclusions; `data/` itself is NOT excluded) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_retail_csv(url: str, dest: Path) -> Path
def load_raw_csv(path: Path) -> pd.DataFrame
def load_raw_xlsx(path: Path) -> pd.DataFrame  # fallback only
def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def write_data_source(path: Path, record: dict) -> None

# src/rfm.py
def compute_rfm(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame
def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame  # adds r_score, f_score, m_score, rfm_code, rfm_score
def line_revenue(quantity, unit_price) -> float

# src/clustering.py
def select_k(rfm: pd.DataFrame, k_range: range = range(2, 9), seed: int = 42) -> pd.DataFrame  # k, sse, silhouette
def cluster_customers(rfm: pd.DataFrame, k: int, seed: int = 42) -> np.ndarray
def name_segments(median_scores: pd.DataFrame) -> dict  # cluster label -> segment name
def sbc_stats(orders: pd.DataFrame) -> pd.DataFrame  # per-customer ADI (weeks) + CV2
def classify_sbc(adi: float, cv2: float) -> str
def agreement_rate(contingency: pd.DataFrame) -> float
def build_segment_profile(rfm_table: pd.DataFrame) -> pd.DataFrame

# src/actions.py
def action_for(segment: str, profile_row: pd.Series) -> str
def gbp_at_stake(profile_row: pd.Series) -> float
def build_actions(segment_profile: pd.DataFrame) -> pd.DataFrame
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units (£ or days or counts as
stated), source footnote ("Source: UCI Online Retail (Chen 2015), DOI
10.24432/C5BW33, CC BY 4.0 — historical 2010–2011 data, scores relative
to this customer base"), no truncated axes, legible at 100% zoom.

1. **01_rfm_scores.png** — What the RFM scores look like. Two panels:
   (a) histogram of `RFM_score` (3–15) across identified customers;
   (b) customers per segment (bar, counts labelled). Answers Q1's
   "what groups exist" half.
2. **02_segment_value.png** — Who is worth what. Grouped horizontal
   bars per segment: share of customers vs share of attributed revenue,
   annotated with mean monetary £ per segment; the Unattributed revenue
   share shown as a separate labelled bar. Answers Q2.
3. **03_kmeans_clusters.png** — The clustering itself. Scatter of
   log10(Frequency) vs log10(Monetary £), one point per customer,
   coloured by segment (KMeans decides — say so in the title), cluster
   centroids (median R days / F / M £) marked with a distinct marker.
   Answers Q1's clustering half.
4. **04_sbc_quadrants.png** — The cross-check. ADI (weeks, x) vs CV²
   (y) scatter for multi-order customers only, one point per customer,
   coloured by SBC quadrant, threshold lines drawn at ADI = 1.32 and
   CV² = 0.49 with the four quadrant labels; agreement rate with
   KMeans in the title/footnote; single-order customer count in the
   footnote. Answers Q2's cross-check half.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–11 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URL, DOI, licence (CC BY 4.0,
      verbatim attribution), fetch date (2026-11-16), row counts (raw
      541,909 / cleaned / excluded per rule / missing-CustomerID rows +
      revenue share), confirmed date range, snapshot date — in
      `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → clean → RFM → score
      → cluster → name → SBC cross-check → actions → charts, with
      `--offline` mode) + RFM/metric definitions (§4.1) written down
- [ ] **Decider rule (§2.0) stated in the plan and honoured in the
      build**: KMeans decides segment assignment; RFM scores name and
      explain; SBC is a cross-check with the agreement rate reported;
      **tester verified the decider was actually used** (segment column
      reproduces from KMeans labels — test + test_report evidence)
- [ ] **RFM segments with tailored action suggestions delivered**
      (roadmap deliverable): one row per customer with exactly one
      segment, per-segment profile table, and **exactly one action per
      segment with the £ at stake** — in `rfm_table.csv`,
      `segment_profile.csv`, the dashboard, charts and insights
- [ ] **Clustering done**: KMeans on log1p+scaled RFM with k re-derived
      by elbow + silhouette (k = 2..8, rule in §4.3 — Day 10's k = 4
      NOT copied); per-cluster centroids in original units reported
- [ ] **SBC cross-check done**: ADI (weeks) / CV² (per-order £) quadrants
      for every multi-order customer, Single-order handled separately,
      agreement rate reported with the contingency table in
      `agreement.csv`; disagreement reported, not hidden or averaged away
- [ ] **Segments delivered honestly**: scores labelled relative to this
      customer base; 2010–2011 data labelled historical on every
      surface; unattributed (no-CustomerID) revenue shown as its own
      line with both revenue-share bases; no segment presented without
      saying KMeans decided it
- [ ] **SQL check done** (§4.6): count + revenue per segment and top
      segment by revenue via in-memory SQLite asserted equal to pandas,
      in the notebook and a test
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate below)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2.1 question with exact numbers) + the per-segment action
      table (§4.7)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, the decider rule, and limitations
- [ ] No credentials / private records in the repo; **no copying others'
      code** — all code is Victor's own original work; **data-size
      exception honoured** (no file > 1 MB, `data/` < 5 MB; raw CSV/XLSX
      git-ignored per §3.4 and absent at handoff; `.gitignore` matches
      §5/§6 and does NOT exclude `data/`)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. one
      customer's R/F/M from the sample rows, or the Champions segment's
      revenue — from the committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert — **exit 0 with 0 error cells** — with `_find_root()`
      and the guarded segmentation section, §6)
- [ ] Pinned dependencies in `requirements.txt` (incl. scikit-learn,
      scipy, openpyxl; no statsmodels); **`black --check` + `ruff check`
      clean**
- [ ] Streamlit smoke gate passed: **fresh port 8502+**, HTTP 200 on `/`
      and on `/_stcore/health`, **real `screenshots/dashboard.png`**
      captured (**< 1 MB**), server killed and port verified free
- [ ] **Offline pipeline run must NOT clobber `data_source.json`**
      (skip writing it when a live record exists — §3.5, tested)
- [ ] **No base64 strings quoted in docs** (validator false-positive
      rule — never paste base64 content into any `.md` file)
- [ ] **Orchestrator validate clean** for the day folder
      (`python agents/orchestrator.py --day 12 validate`) — **target
      11/11 checks pass**
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes (≥ 15 tests, from repo root and from the day folder)
- [ ] `.gitignore` matches §3.4/§5 (raw CSV/XLSX + synthetic excluded; `data/` itself NOT excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+), < 1 MB
- [ ] `data/` total < 5 MB, no file > 1 MB; **no raw CSV/XLSX on disk at handoff** (git-ignored, deleted after the build); `data_source.json` records live counts, cleaning exclusions, missing-CustomerID revenue share, snapshot date, k-selection outcome, segment-naming mapping, SBC counts and agreement rate
- [ ] Counts verified against §3.3 (541,909 rows, 8 columns); confirmed date range + snapshot date recorded; decider rule (§2.0) implemented — segment column reproduces from KMeans labels
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Notebook runs via nbconvert with exit 0 and 0 error cells; SQL check asserts in the notebook
- [ ] Build only what §5 lists; no extra web searches; no base64 strings in any doc

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| CSV download fails or is truncated | 1 retry after 60 s, then legacy XLSX fallback, then stop and report; synthetic fallback (§3.6) only if both fail |
| Row count ≠ 541,909 or columns differ | Verify after fetch (§3.3); report, do not silently proceed |
| CSV encoding / date parsing breaks (DD/MM/YYYY) | `encoding="ISO-8859-1"`, `dayfirst=True` (§3.1); verify header row + first data row after load |
| XLSX fallback path confusion (404 on the static path) | Use only the legacy XLSX URL in §3.1; never the static-path XLSX URL |
| Server ignores Range header | One plain full download, never ranged/resumable (§3.1) |
| qcut fails on duplicate bin edges (tied F/M) | Percentile-rank scoring (§4.1) — no qcut anywhere; tested |
| KMeans k is copied from Day 10 instead of re-derived | k-selection rule (§4.3) + test; chosen k + silhouette per k recorded |
| RFM-score rule and KMeans disagree about a customer | Decider rule (§2.0): KMeans decides, RFM names, SBC cross-checks; agreement rate reported |
| Single-order customers have no ADI | `Single-order` quadrant, excluded from agreement denominator (§4.4) |
| Adjustment codes list misses a real non-product code (or drops a real product) | Coder profiles distinct codes first; additions only for plainly non-product codes, recorded in `data_source.json` (§3.2 rule 5) |
| Unattributed (no-CustomerID) revenue silently dropped | Counted, reported as its own profile row with both revenue-share bases (§3.2 rule 8, §4.5) |
| A segment name is claimed from an RFM code, not from KMeans | Naming rule (§4.2) + decider test; no surface presents RFM-code segments as the segments |
| No inventory / lead-time data tempts invented numbers | No reorder list this day; actions carry £ at stake from measured segment revenue only (§4.5) |
| Prices may or may not include VAT | Disclosed as a limitation (dataset does not state it) |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text. Never quote base64 strings in docs (§8). |

## 11. Differences from the brief (plan wins)

- **Decider rule (§2.0):** the brief (§2) required the planner to write
  a decider rule and forbade presenting both methods as if they agreed.
  The plan **fixes** it: **KMeans on log1p+scaled RFM decides segment
  assignment**; RFM quintile scores name and explain the segments; SBC
  quadrants are a cross-check with the agreement rate reported. The
  tester must verify the decider was actually used.
- **RFM scoring (§4.1):** the brief's default was quintile bins via
  `pandas.qcut` / SQL `NTILE(5)` with a `duplicates='drop'` workaround
  for the tied-F/M trap. The plan **fixes** percentile-rank scoring
  instead (ties share a score, deterministic, no bin-edge failure) —
  same 1–5 scale, same inversion for R, same 3–15 total. The qcut trap
  is avoided by construction, not patched.
- **SBC unit (§4.4):** the brief left the planner to fix the ADI unit
  and the CV² base. The plan **fixes** ADI in weeks (mean inter-order
  gap in days ÷ 7) and CV² from per-order £ totals, and adds the
  `Single-order` quadrant for F = 1 customers (ADI undefined), who are
  excluded from the agreement-rate denominator.
- **Agreement rate (§4.4):** the brief required an agreement rate to be
  reported but did not define it. The plan **fixes** the definition:
  greedy best one-to-one segment↔quadrant mapping over multi-order
  customers only, rate = matched ÷ multi-order customers.
- **Missing CustomerID (§3.2 rule 8):** the brief said only to exclude
  such rows and record the count. The plan **fixes** the handling: the
  unattributed revenue is carried as its own row in
  `segment_profile.csv`, and segment revenue shares are reported on
  both bases (attributed and total cleaned revenue).
- **Partial weeks (§2.2):** Day 11 excluded partial first/last weeks
  from its weekly series. The plan **fixes** no partial-week exclusion
  for Day 12 — RFM uses the full cleaned window, snapshot 2011-12-10.
- **Primary download (§3.1):** the brief verified both the CSV and the
  XLSX. The plan **fixes** `data.csv` (~43 MB) as primary and the
  legacy XLSX (~22.6 MB) as fallback only (Day 11 used a ZIP URL; no
  ZIP is used this day).
- **k-selection (§4.3):** the brief left k to the planner. The plan
  **fixes** k ∈ 2..8, silhouette argmax with the 0.01 smaller-k
  tie-break, elbow SSE reported — Day 10's k = 4 is not copied.
- **Segment naming (§4.2):** the brief listed common named segments
  from RFM codes. The plan **fixes** the prototype-distance naming rule
  (8-name pool, each used at most once) applied to KMeans clusters'
  median RFM scores — names label clusters, they are not RFM-code
  thresholds.
- **Actions (§4.5):** the brief required a tailored action per segment.
  The plan **fixes** exactly one action per segment, each embedding its
  £ at stake, with the £ defined as the segment's revenue and labelled
  protect / at-risk / grow by segment type.
- **Data-size exception (§3.4):** same mechanism as Days 8–11 — raw
  CSV/XLSX git-ignored and re-downloaded at build, committed
  provenance = `sample_rows.json` (1,000 cleaned rows) + processed
  CSVs + `data_source.json`, `data/` < 5 MB, no file > 1 MB,
  `.gitignore` must NOT exclude `data/`.
- **Power BI:** the roadmap's section-level core skills list Power BI,
  but no `.pbix` is built (same decision as Days 8–11 — a `.pbix`
  cannot be built or verified in this environment); the Streamlit
  dashboard + 4 static charts are the deliverables. The SQL skill is
  covered by the §4.6 check.
- **Notebook (§6):** the brief did not specify notebook mechanics; the
  plan adds the guarded segmentation section (re-runs RFM + KMeans
  when the raw file is present, otherwise loads committed CSVs — 0
  errors either way).
- **CI flake (§3.5):** the Day 9 CI flake (byte-exact CSV comparison)
  is addressed here by mandating tolerance-based comparison in the
  offline-reproduction test, and the offline run skips writing
  `data_source.json` when a live record exists.

## 12. Build order

1. `src/data_pipeline.py` — download CSV (fallback XLSX) → verify
   counts → clean (§3.2, exclusions counted) → R/F/M per customer
   (§4.1) → `sample_rows.json` + `rfm_table.csv` (pre-cluster columns)
   + `data_source.json` (live run; cache raw).
2. `src/rfm.py` + `src/clustering.py` — score RFM (§4.1) → select k
   (§4.3) → KMeans clusters → name segments (§4.2) → SBC quadrants +
   agreement rate (§4.4) → `segment_profile.csv`, `sbc_summary.csv`,
   `agreement.csv`.
3. `src/actions.py` — exactly one action + £ at stake per segment (§4.5).
4. `src/make_charts.py` — 4 charts from the processed CSVs.
5. `notebooks/analysis.ipynb` — EDA + Q1–Q3 + SQL check + guarded
   segmentation section; run via nbconvert, exit 0, 0 errors.
6. `src/app.py` — Streamlit dashboard from processed CSVs only; smoke
   test on a fresh port (8502+) + real `screenshots/dashboard.png`
   (< 1 MB).
7. `tests/test_pipeline.py` — ≥ 15 tests (§6), **including the decider
   test**; delete `tests/test_smoke.py`; `pytest`, `black`, `ruff`;
   coder handoff checklist (§9); delete the raw CSV/XLSX from disk at
   handoff.
8. Docs — `README.md`, `data/README.md`, `outputs/insights_summary.md`;
   every number checked against the committed processed CSVs; the
   decider rule (§2.0) stated in the README; the §1 limits labelled on
   every surface.
