# Data provenance — Day 12 Customer Segmentation Engine

## Source

- **Provider:** UCI Machine Learning Repository, dataset 352, "Online Retail".
- **Dataset page:** https://archive.ics.uci.edu/dataset/352/online+retail
- **Download (primary):** https://archive.ics.uci.edu/static/public/352/data.csv
  — HTTP 200, 45,038,760 bytes (~43.0 MB), fetched 2026-11-16, no key, no
  account, no documented rate limit. One single download.
- **Download (fallback, not needed):** legacy XLSX
  https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
  (HTTP 200, 23,715,344 bytes). The XLSX does NOT live at
  `https://archive.ics.uci.edu/static/public/352/Online%20Retail.xlsx`
  (HTTP 404) — that path was not used.
- **DOI:** https://doi.org/10.24432/C5BW33
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).
  Attribution: Chen, D. (2015). Online Retail [Dataset]. UCI Machine
  Learning Repository. https://doi.org/10.24432/C5BW33. Also cite Chen,
  Sain & Guo (2012) as the RFM-segmentation source paper for this exact
  dataset.
- **Page inconsistency (recorded, not resolved by guessing):** the dataset
  page header says "# Features 6" while the variables table lists 8
  columns — the file itself is authoritative (8 columns verified).

## Fetch outcome

Live CSV download succeeded on the first attempt (2026-11-16). Verified
after fetch: 541,909 rows, 8 columns with the exact names
`InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice,
CustomerID, Country`. First data row `536365,…,12/1/2010 8:26,2.55,17850,
United Kingdom` confirmed.

**Date-format note (plan §3.1 vs the file):** the plan says to read dates
with `dayfirst=True` (DD/MM/YYYY as published). The CSV file itself uses
M/D/YYYY — "12/1/2010 8:26" is 1 Dec 2010. Parsing with `dayfirst=True`
drops 308,950 rows as unparseable and shifts the range to 2010-01-12.
The file is authoritative: `dayfirst=False` gives 0 unparseable dates
and the published range 2010-12-01 → 2011-12-09, matching Days 10–11
(which read the XLSX's real datetimes). The pipeline uses
`dayfirst=False`; see `src/data_pipeline.py`.

## Row counts and coverage

- **Confirmed date range:** 2010-12-01 08:26 → 2011-12-09 12:50.
  Snapshot date 2011-12-10 = max(InvoiceDate) + 1 day.
- **Raw rows:** 541,909. **Cleaned rows:** 527,795.
  **Cleaned revenue:** £10,283,243.98. **Cleaned units:** 5,577,139.
  **Cleaned orders:** 19,776. **Identified customers:** 4,334.

### Cleaning audit (rules applied in order, plan §3.2)

| Step | Rows removed |
|---|---:|
| Unparseable InvoiceDate | 0 |
| Cancellations (InvoiceNo starting `C`) | 9,288 rows (3,836 invoices) |
| Non-positive Quantity | 1,336 |
| Non-positive UnitPrice | 1,181 |
| Non-product adjustment lines | 2,309 |
| Missing Description | 0 |
| **Cleaned rows** | **527,795** |

- **Adjustment codes used:** StockCodes POST, DOT, M, D, BANK CHARGES,
  CRUK, C2, AMAZONFEE; descriptions POSTAGE, DISCOUNT, MANUAL, BANK
  CHARGES, AMAZON FEE, CRUK. No additional adjustment code was added.
  StockCodes actually present among the dropped rows: AMAZONFEE, BANK
  CHARGES, C2, DOT, M, POST. Descriptions actually present among the
  dropped rows: AMAZON FEE, BANK CHARGES, CARRIAGE, DOTCOM POSTAGE,
  MANUAL, POSTAGE (CARRIAGE / DOTCOM POSTAGE rows were caught by their
  StockCode, not by the description list).
- **Missing CustomerID:** 131,455 cleaned rows (24.91% of cleaned rows)
  have no CustomerID. Their revenue is **£1,522,177.33 — 14.80% of
  cleaned revenue** — and is carried as its own
  `Unattributed (no CustomerID)` row in `segment_profile.csv`, so
  segment revenue shares do not silently sum to 100%. These rows are
  excluded from RFM and clustering only.

## RFM definitions + scoring

- **Recency (R)** = snapshot date − most recent InvoiceDate, in calendar
  days (range 1–374). **Frequency (F)** = distinct InvoiceNo per
  customer. **Monetary (M)** = Σ(Quantity × UnitPrice) in GBP.
- **Scoring:** percentile-rank 1–5 (ties share a score), R inverted;
  `rfm_code = R·100 + F·10 + M`; `rfm_score = R + F + M` (3–15). Scores
  are relative to this customer base, not absolute.

## Decider rule (plan §2.0)

**KMeans on log1p-transformed, StandardScaler-scaled R/F/M is the SOLE
decider of segment assignment.** RFM quintile scores name and explain
the segments; SBC quadrants are a cross-check with the agreement rate
reported. The `segment` column in `rfm_table.csv` reproduces exactly
from the KMeans labels + the §4.2 prototype naming for every customer
(tested).

## k-selection outcome

k = 2..8, `KMeans(random_state=42, n_init=10)`, silhouette primary +
elbow SSE:

| k | SSE | Silhouette |
|---:|---:|---:|
| 2 | 6,467.5 | **0.4330** |
| 3 | 4,848.8 | 0.3374 |
| 4 | 3,918.6 | 0.3339 |
| 5 | 3,261.8 | 0.3182 |
| 6 | 2,836.0 | 0.3131 |
| 7 | 2,528.8 | 0.3029 |
| 8 | 2,328.2 | 0.2885 |

**Chosen k = 2** by the §4.3 rule (argmax silhouette; 0.01 smaller-k
tie-break — not triggered, k = 3 is 0.0956 below k = 2). Day 10's k = 4
(silhouette 0.616 on its own cleaning) is not copied; the re-derived k
differs and the difference is reported here. Cluster → name mapping:
cluster 0 → Hibernating (median scores R2 F1 M2); cluster 1 →
Champions (median scores R4 F5 M5).

## SBC parameters + quadrant counts

- ADI in weeks (mean inter-order gap in days ÷ 7), cut-off 1.32; CV² from
  per-order £ totals, cut-off 0.49 (SBC-published rounded convention; the
  exact theoretical cut-offs are 4/3 and 0.5 per Kostenko & Hyndman).
- Quadrants: Smooth 59, Erratic 88, Intermittent 2,175, Lumpy 507,
  Single-order 1,505. Multi-order customers: 2,829.
- **Agreement rate (SBC ↔ KMeans): 51.5%** (1,458 of 2,829 multi-order
  customers matched under the greedy best one-to-one segment↔quadrant
  mapping; Single-order excluded). Contingency table in
  `data/processed/agreement.csv`. SBC never overrides a KMeans
  assignment.

## Commit rule for data files

- **Data-size exception (plan §3.4):** the raw CSV (~43.0 MB) is far over
  the portfolio rule (files < 1 MB each, < 5 MB per day folder), so
  `data/raw/data.csv` and `data/raw/Online Retail.xlsx` are git-ignored
  and re-downloaded at build time. `.gitignore` must NOT exclude `data/`
  itself — only those raw-data lines.
- **Committed:** `data/raw/sample_rows.json` (1,000 cleaned rows,
  provenance sample) and `data/processed/` (`data_source.json`,
  `rfm_table.csv`, `segment_profile.csv`, `sbc_summary.csv`,
  `agreement.csv`). No committed file > 1 MB; `data/` total < 5 MB.
- **Reproduce:** `python -m src.data_pipeline --live` (downloads the raw
  file) or `--offline` (regenerates from the committed CSVs; never
  overwrites a live `data_source.json`).

## Manual validation (one metric, by hand)

Independent recomputation straight from `data/raw/data.csv` with plain
pandas (not `src.rfm` / `src.clustering`): same cleaning order, snapshot
2011-12-10, calendar-date Recency.

| Customer | Hand R / F / M | Table R / F / M | Diff |
|---:|---:|---:|---:|
| 14646 | 2 / 72 / £279,138.02 | 2 / 72 / £279,138.02 | 0, 0, £0.00 |
| 14911 | 2 / 198 / £136,275.72 | 2 / 198 / £136,275.72 | 0, 0, £0.00 |
| 17850 | 373 / 34 / £5,391.21 | 373 / 34 / £5,391.21 | 0, 0, £0.00 |

Segment revenue cross-check from the committed CSVs: Champions
rfm_table sum £7,436,335.44 vs segment_profile £7,436,335.44 (diff
£0.00); Hibernating £1,324,731.21 vs £1,324,731.21 (diff £0.00).
Recency range in `rfm_table.csv` is 1–374, matching plan §4.1.

Note: an earlier build computed Recency with raw `Timedelta.days`,
which floored intraday times and gave R=1 for customer 14646 (hand: 2).
Fixed to calendar-date difference in `src/rfm.py` (`compute_rfm`),
then re-validated exact.

## Versions used for this build

Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2,
scikit-learn 1.9.1, scipy 1.18.1, openpyxl 3.1.5, streamlit 1.66.1,
pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1. Full pinned list in
`requirements.txt`. Dev tools: ruff 0.17.4, black 26.10.1 (portfolio-root
`requirements-dev.txt`).
