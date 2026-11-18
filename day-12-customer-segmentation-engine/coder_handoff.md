# Day 12 — Coder handoff (Stage 3, DONE 2026-11-16)

**Project:** Customer Segmentation Engine — UCI Online Retail (Dec 2010 – Dec 2011).
RFM + KMeans segmentation with one tailored action per segment, £ at stake.

## What was produced

- `src/__init__.py`, `src/data_pipeline.py`, `src/rfm.py`,
  `src/clustering.py`, `src/actions.py`, `src/make_charts.py`, `src/app.py`
- `tests/test_pipeline.py` (26 tests; `tests/test_smoke.py` deleted per plan)
- `notebooks/analysis.ipynb` (16 cells, 0 error cells via nbconvert)
- `outputs/charts/01_rfm_scores.png`, `02_segment_value.png`,
  `03_kmeans_clusters.png`, `04_sbc_quadrants.png` (exactly 4)
- `outputs/insights_summary.md`, `README.md`, `data/README.md`
- `data/processed/` — `data_source.json`, `rfm_table.csv`,
  `segment_profile.csv`, `sbc_summary.csv`, `agreement.csv`;
  `data/raw/sample_rows.json` (1,000 cleaned rows)
- `screenshots/dashboard.png` (1200×4723, 592,338 bytes — real capture, see below)
- `requirements.txt` (Day 11 stack minus statsmodels, plus openpyxl==3.1.5),
  `.gitignore` (plan §3.4), `pyproject.toml`, `LICENSE`

## Verified numbers

- **Live fetch:** `https://archive.ics.uci.edu/static/public/352/data.csv`,
  first attempt, 45,038,760 bytes. **541,909 rows, 8 columns**,
  2010-12-01 08:26 → 2011-12-09 12:50 (confirmed from the file).
  Snapshot 2011-12-10. XLSX fallback not needed.
- **Cleaning (in order):** unparseable dates 0 → cancelled 9,288 rows
  (3,836 invoices) → qty ≤ 0: 1,336 → price ≤ 0: 1,181 → adjustment:
  2,309 → missing description: 0. **Cleaned: 527,795 rows,
  £10,283,243.98 revenue, 5,577,139 units, 19,776 orders.**
  Missing-CustomerID rows: 131,455 (24.91%); their revenue
  **£1,522,177.33 = 14.80% of cleaned revenue** — carried as its own
  `Unattributed (no CustomerID)` profile row.
- **Customers:** 4,334 identified. Median R 51 days, F 2, M £668.13.
  Recency range 1–374 (plan §4.1). Single-order customers: 1,505 (34.7%).
  Top customer 14646: £279,138.02, 72 orders.
- **k re-derived: k = 2, silhouette 0.4330** (k=3: 0.3374, k=4: 0.3339,
  k=5: 0.3182, k=6: 0.3131, k=7: 0.3029, k=8: 0.2885; SSE 6,467.5 →
  2,328.2). Differs from Day 10's k = 4 — reported, not copied.
  0.01 tie-break not triggered.
- **Segments (KMeans decides, plan §2.0):** Champions 1,661 (38.3%),
  **£7,436,335.44, 84.9% of attributed revenue** (median R 17d / F 6 /
  M £2,044.87); Hibernating 2,673 (61.7%), £1,324,731.21, 15.1% of
  attributed (median R 97d / F 1 / M £358.38). Cluster → name:
  cluster 0 → Hibernating (median scores R2 F1 M2); cluster 1 →
  Champions (R4 F5 M5). The RFM-score rule would disagree with KMeans
  for **2,830 of 4,334 customers** — the decider test asserts the
  segment column reproduces from the KMeans labels for every row.
- **SBC cross-check:** Smooth 59, Erratic 88, Intermittent 2,175, Lumpy
  507, Single-order 1,505. **Agreement rate 51.5%** (1,458 of 2,829
  multi-order customers, greedy best one-to-one mapping). Contingency
  table in `agreement.csv`.
- **Actions (exactly one per segment, £ at stake):** Champions — VIP
  retention, £7,436,335.44 to protect; Hibernating — one low-cost
  reactivation email, £1,324,731.21 already lapsed.

## Gates run (all pass)

| Gate | Result |
|---|---|
| pytest `tests/test_pipeline.py` | **26/26 passed** (day folder and from repo root) |
| black `--check src tests` | clean |
| ruff `check src tests` | clean |
| Notebook via nbconvert | 16 cells, **0 error cells**, exit 0 — executed twice: once with raw present (guarded re-run passed) and once after raw deletion (guarded section prints the skip note) |
| Streamlit smoke | port **8502**: HTTP 200 on `/`, HTTP 200 on `/_stcore/health`; clean server log (0 errors); server killed, port verified free |
| Screenshot | `screenshots/dashboard.png`, 1200×4723, 592,338 bytes — real single-shot tall-viewport capture (stMain scrollHeight method), visually verified; KPI truncation fixed (£10.28m / £8.76m with full values as deltas) |
| Offline pipeline run | regenerates derived tables; `data_source.json` byte-identical (sha256 d3064fb7… verified) |
| Orchestrator validate | **11/11** |
| File sizes | No committed file > 1 MB (largest: dashboard.png 592,338; data_source.json 588,186); `data/` total 1,088 KB (< 5 MB) |
| Hand validation (coder) | Customers 14646 (R=2, F=72, M=£279,138.02), 14911 (R=2, F=198, M=£136,275.72), 17850 (R=373, F=34, M=£5,391.21) recomputed independently from the raw CSV — **diffs 0, 0, £0.00**. Champions revenue £7,436,335.44 and Hibernating £1,324,731.21 both match the profile to £0.00. Full arithmetic in `data/README.md` |

## Bugs / deviations found during coding

1. **Date format (plan §3.1 vs the file):** the plan says `dayfirst=True`
   (DD/MM/YYYY as published), but the CSV uses M/D/YYYY — parsing with
   `dayfirst=True` drops 308,950 rows as unparseable and shifts the range
   to 2010-01-12. The file is authoritative: `dayfirst=False` gives 0
   unparseable dates and the published range, matching Days 10–11.
   Recorded in `data/README.md` and in a code comment in
   `src/data_pipeline.py` (`clean_transactions`).
2. **Recency definition:** raw `Timedelta.days` floored intraday times
   and gave R=1 for customer 14646 (hand: 2) and a 0–373 range. Plan §4.1
   says range 1–374, so Recency is now the calendar-date difference
   (`src/rfm.py` `compute_rfm`); re-validated exact, range 1–374.
3. **KPI truncation in the first screenshot:** Streamlit metrics truncated
   long £ values; fixed by showing £10.28m / £8.76m with the full values
   as deltas, and re-shot.
4. **Chart 03 centroid labels** overlapped their markers; fixed with a
   white bounding box behind the annotation text.

## Known gaps / defects

1. **k = 2 is a coarse split:** "Hibernating" mixes one-time buyers with
   lapsed repeat buyers. The silhouette rule (plan §4.3) selects k = 2
   on this data (0.4330 vs 0.3374 for k = 3); a finer k would separate
   them, but the rule, not preference, chose k = 2. Disclosed in the
   README and insights.
2. **Chart 04 "Smooth" label** sits over the dense point cloud at the
   bottom-left (same pattern as Day 11's chart 03); the label has a white
   box and is in the correct quadrant, and exact per-customer ADI/CV² are
   in `data_source.json` (`sbc_per_customer`).
3. Raw CSV/XLSX were **deleted from disk at handoff** (plan §9). The
   tester must not re-download live data; `--offline` runs from the
   committed CSVs. The notebook's guarded section will print the
   "raw not present" note instead of re-running when the tester executes it.

## Tester's first step

Run `pytest tests/ -q` in the day folder venv (26 tests, ~10 s), then
re-run the offline pipeline check: confirm `python -m src.data_pipeline
--offline` leaves `data_source.json` byte-identical — or simply re-run
the existing offline-clobber test, which already asserts this. Then run
the Streamlit smoke on a fresh port (8502+) and verify the decider test
(`test_decider_segment_equals_kmeans_label_mapping`) passes.
