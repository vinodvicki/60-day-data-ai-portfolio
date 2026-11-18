# Day 12 — Customer Segmentation Engine: Research Brief

**Status:** VERIFIED — one lean pass completed 2026-11-16 (researcher, stage 1).
**Business question:** Which customer groups does this UK online retailer actually have — who is worth protecting, who is slipping away, and who is already gone — and what should the retailer do differently for each group?

## 1. Data source — verified from scratch

**Source:** UCI Machine Learning Repository, dataset 352, "Online Retail", donated 2015-11-05 by Daqing Chen (London South Bank University). Same dataset Days 10–11 used; re-verified independently in this pass, not copied from their notes.

| Check | Result (2026-11-16) |
|---|---|
| Dataset page | `https://archive.ics.uci.edu/dataset/352/online+retail` — **HTTP 200**, crawled 2026-11-16 14:00 UTC |
| Metadata API | `https://archive.ics.uci.edu/api/dataset?id=352` — **HTTP 200**, JSON, 4,101 bytes; returns `num_instances: 541909`, `data_url` (see below), `repository_url` |
| Primary download (CSV) | `https://archive.ics.uci.edu/static/public/352/data.csv` — **HTTP 200**; full GET probe to `/dev/null` measured **45,038,760 bytes (~43.0 MB)**; header row confirmed: `InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country`; first data row `536365,…,12/1/2010 8:26,2.55,17850,United Kingdom` |
| Legacy download (XLSX) | `https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx` — **HTTP 200**, **23,715,344 bytes (~22.6 MB)**, matching the 22.6 MB listed on the dataset page |
| DOI | `https://doi.org/10.24432/C5BW33` — **HTTP 302** → dataset page (Cloudflare). Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33 |
| Instances | **541,909** rows (dataset page + API agree) |
| Date range | **01/12/2010 – 09/12/2011** (DD/MM/YYYY, as published) — UK-based, non-store online retail, mainly unique all-occasion gifts; many customers are wholesalers |
| Associated tasks (per UCI) | Classification, Clustering — clustering is an intended use |
| Introductory paper | Chen, Sain & Guo (2012), "Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining", *J. Database Marketing & Customer Strategy Management* 19(3), doi:10.1057/dbm.2012.17 — the RFM-segmentation paper for this exact dataset |

**Endpoints / access:** no API key, no login, no published rate limit. Polite-use rule: one single download of `data.csv` (or the `ucimlrepo` Python package, `fetch_ucirepo(id=352)`, which hits the same API + `data.csv`); do not hammer the server; if a download fails, wait and retry once, then fall back to the legacy XLSX URL, then to the synthetic fallback (§4). Stop condition: two consecutive failed attempts on both URLs.

**Schema (8 columns, as published on the dataset page):**

| Column | Type | Meaning |
|---|---|---|
| InvoiceNo | Categorical (ID) | 6-digit invoice number; prefix `C` = cancellation |
| StockCode | Categorical (ID) | 5-digit product code |
| Description | Categorical | Product name |
| Quantity | Integer | Units per transaction (can be negative — cancellations/returns) |
| InvoiceDate | Date | Day + time of transaction |
| UnitPrice | Continuous, GBP (sterling) | Price per unit |
| CustomerID | Categorical | 5-digit customer number (missing on some rows — coder to count) |
| Country | Categorical | Customer's country of residence |

**Discrepancies found in this pass (record, do not silently resolve):**
1. The dataset page header says "# Features: 6" but the variables table lists **8 columns** — the 6 are the non-ID features; the 2 ID columns (InvoiceNo, StockCode) make 8. Coder to use all 8 columns; planner to note the count as 8.
2. The XLSX does **not** live at `https://archive.ics.uci.edu/static/public/352/Online%20Retail.xlsx` — that path returns **HTTP 404**. The working XLSX URL is the legacy `.../ml/machine-learning-databases/00352/Online%20Retail.xlsx` path. Use `data.csv` as primary; XLSX is backup only.
3. HEAD on `data.csv` returns no `Content-Length`/`Content-Type`; size (45,038,760 bytes) was established only by a full GET streamed to `/dev/null`. No probe copy was retained anywhere (data/raw/ and data/processed/ verified empty after the probe) — the real download is the coder's job.
4. Date range is published in DD/MM/YYYY (01/12/2010 = 1 Dec 2010). Do not read it as MM/DD.

## 2. Metrics to compute — exact definitions

Reference ("snapshot") date: **max(InvoiceDate) + 1 day** = 2011-12-10. All RFM values are per CustomerID, computed over the full window unless the planner narrows it.

- **Recency (R)** = snapshot date − customer's most recent InvoiceDate, in **days**. Lower = better (more recent).
- **Frequency (F)** = count of **distinct InvoiceNo** per customer (not line-item rows). Higher = better. Cancellations (InvoiceNo starting `C`) and negative-Quantity rows are excluded before counting — coder to record how many rows/customers this removes.
- **Monetary (M)** = Σ (Quantity × UnitPrice) per customer, in **GBP**, over the same cleaned rows. Higher = better. Rows with missing CustomerID are excluded (they cannot be attributed); coder to record the count.
- **Line value** = Quantity × UnitPrice per row; used only inside the M sum.

### RFM scoring conventions (standard practice — planner chooses one, records it)

- **Quintile 1–5 scoring (the default):** each of R, F, M is split into five equal-sized bins across the customer base (`pandas.qcut` / SQL `NTILE(5)`). R is inverted (most-recent quintile = 5); F and M are direct (top quintile = 5). Concatenated code `RFM = R·100 + F·10 + M` (e.g. 555 = best, 111 = worst); `RFM_score = R + F + M` ranges 3–15. Scores are **relative** to this customer base, not absolute — recompute if the base changes.
- **Known trap:** F and M are heavily tied at the low end (many one-time, low-spend customers), so `qcut` can fail on duplicate bin edges — coder must handle with `duplicates='drop'` or rank-based scoring and record what was done.
- **Common named segments from RFM codes** (planner to fix the exact mapping in plan.md): Champions (R,F,M all ≥ 4, e.g. 555/554/544/545), Loyal, Potential Loyalists, New Customers (high R, low F), At Risk (high F/M, low R), Hibernating / About to Sleep, Lost (low R, F, M). Each segment gets a tailored action in the deliverable (roadmap: "RFM segments with tailored action suggestions").

### KMeans-on-scaled-RFM practice (standard — planner chooses k, records how)

- Inputs: R, F, M (usually `log1p`-transformed first — all three are right-skewed — then `StandardScaler`). Never cluster raw R/F/M: Monetary's scale would dominate.
- Choose k by elbow (within-cluster SSE) **and** silhouette score together; report both. k = 4 is the Day 10 precedent on this same data (silhouette 0.616), not a prescription — planner/coder re-derive k from the cleaned Day 12 table.
- Report per-cluster centroids in original units (median R days, median F, median M £) so segments are interpretable, plus cluster sizes and share of revenue.

### SBC quadrant thresholds (background — from Day 11, re-verified)

Syntetos–Boylan–Croston (Syntetos et al. 2005) classifies each customer's (or product's) demand pattern on two axes, split at **ADI = 1.32** and **CV² = 0.49**:

- **ADI** (average demand interval) = total periods ÷ periods with non-zero demand (equivalently, mean gap between successive orders, in the chosen period unit — planner must fix the unit, e.g. weeks).
- **CV²** = (std ÷ mean)² of the non-zero demand sizes (here: order values or quantities per order — planner must fix which).
- Quadrants: Smooth (ADI ≤ 1.32, CV² ≤ 0.49) · Erratic (ADI ≤ 1.32, CV² > 0.49) · Intermittent (ADI > 1.32, CV² ≤ 0.49) · Lumpy (ADI > 1.32, CV² > 0.49). Sources checked 2026-11-16: Syntetos et al. 2005 via Kostenko & Hyndman (2006), *J. Operational Research Society* 57, 1256–1257 (thresholds p = 1.32, v = 0.49 as given by SBC); MDPI review (2022) restates the same four-way split.
- **Caveat to record:** Kostenko & Hyndman note the exact theoretical cut-offs are 4/3 (≈1.333) and 0.5, not 1.32/0.49 — the 1.32/0.49 values are the SBC-published rounded convention. Use 1.32/0.49 (the convention Day 11 used) and note the rounding.
- **Why this matters for Day 12:** Day 11 found SBC quadrants vs KMeans (k=4) agreement was only **64.0%** — the two methods genuinely disagree about a third of customers. The planner must write a **decider rule** (which method is primary, what the other is used for, and how disagreements are reported) instead of presenting both as if they agreed. Do not average them away.

### Prior-run context (NOT re-verified here — planner/coder re-derive)

- Day 10 (same dataset): RFM + KMeans k=4, silhouette 0.616; segments Champions 13 / Big spenders 209 / Occasional 3,046 / Lapsed 1,066; revenue £10.28m; 222 customers (5.12%) drive 47.94% of identified-customer revenue.
- Day 11: SBC-vs-KMeans agreement 64.0%.
- These are orientation only. Day 12 must compute its own numbers from its own cleaned table and say plainly where they differ.

## 3. Licence / attribution

- **Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)** — sharing and adaptation allowed for any purpose with appropriate credit (dataset page, verified 2026-11-16).
- Attribution to include in README + data/README.md: "Online Retail dataset, Chen, D. (2015), UCI Machine Learning Repository, https://doi.org/10.24432/C5BW33, licensed CC BY 4.0." Also cite Chen, Sain & Guo (2012) as the RFM-segmentation source paper.
- No personal data: CustomerID is a pseudonymous generated number; no names, emails or addresses in the file.

## 4. Synthetic-fallback note (only if both download URLs fail)

- Labelled synthetic, seed 42, `synthetic: true` in `data_source.json` (per AGENTS.md data rule); never overwrite a real download.
- Generate ~4,300 customers / ~540k line rows mimicking the real schema and marginals: InvoiceDate uniform over 2010-12-01–2011-12-09, Quantity mostly 1–12 with a long tail, UnitPrice log-normal-ish in £0.5–£20 with a few high-value items, ~90% of rows with a CustomerID, ~90% of rows United Kingdom, a small share of `C`-prefixed cancellations with negative Quantity. Then run the identical RFM pipeline so the fallback exercises the same code path.
- Fallback is a last resort: the live source verified healthy in this pass (both URLs HTTP 200), so the coder should expect the real download to work.

## 5. Verification status

- [x] Endpoints confirmed against the official source (dataset page + metadata API + both download URLs probed 2026-11-16; HTTP statuses and sizes in §1)
- [x] Row count / date range / licence / DOI as published (541,909; 01/12/2010–09/12/2011; CC BY 4.0; 10.24432/C5BW33)
- [x] Metric definitions recorded exactly (R/F/M, snapshot date, cleaning rules)
- [x] RFM quintile conventions, KMeans-on-scaled-RFM practice, and SBC thresholds (ADI 1.32, CV² 0.49) recorded with sources
- [x] Discrepancies recorded (§1, items 1–4) with the resolution the coder/planner must apply
- [x] No probe copy retained — full-GET size probes streamed to `/dev/null`; `/tmp` probe file deleted; data/raw/ and data/processed/ verified empty
- [ ] Unverified — for the coder to measure, not assumed here: exact count of rows with missing CustomerID; exact count of cancellation/negative-Quantity rows removed; final clean customer count; final k and silhouette (re-derived)
