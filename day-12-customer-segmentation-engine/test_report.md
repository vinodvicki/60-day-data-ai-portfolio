# Day 12 — Tester report (Stage 4, DONE 2026-11-16)

**Project:** Customer Segmentation Engine — UCI Online Retail (Dec 2010 – Dec 2011).
**Verdict: PASS — no blocking defects.** All gates green; 3 minor/cosmetic items
below for the optimizer. Send to optimizer.

## Gates run (all pass)

| Gate | Result |
|---|---|
| `py_compile` all `src/*.py` | OK |
| `black --check src tests` | clean (8 files unchanged) |
| `ruff check src tests` | clean |
| pytest, day folder (`.venv/bin/python -m pytest tests/ -q`) | **26/26 passed in 13.65 s** |
| pytest, repo root (same venv python; system `python3` has no pytest) | **26/26 passed in 9.70 s** |
| Decider tests alone | `test_decider_segment_equals_kmeans_label_mapping` + `test_decider_no_customer_assigned_by_rfm_score_rule_alone` — both PASSED (2.49 s) |
| Pipeline `--offline` (raw absent) | exit 0; all 4 processed CSVs + `data_source.json` + `sample_rows.json` **byte-identical** (sha256 checked before/after). `data_source.json` sha256 `d3064fb7…` — matches coder's claim |
| Notebook via nbconvert (offline, raw absent) | 16 cells, **0 error cells**, exit 0. Guarded section printed: "Raw file not present — guarded re-run skipped; committed CSVs used as-is." Notebook re-executed in place; now 422,118 bytes |
| Orchestrator validate | **11/11** |
| File sizes | `data/` total 1,088,044 bytes (< 5 MB); no file > 1 MB anywhere in the day folder (largest: `data_source.json` 588,186; `screenshots/dashboard.png` 592,338) |
| `.gitignore` vs plan §3.4 | Matches: scaffold defaults + the 3 raw-data lines (`data/raw/data.csv`, `data/raw/Online Retail.xlsx`, `data/raw/*_synthetic.csv`); `data/` itself NOT excluded. One extra harmless line: `*.pyc` |
| Credential grep | Clean — only hits are the literal string `.streamlit/secrets.toml` in `plan.md` (§3.4 list) and the product description "RED METAL BOX TOP SECRET" in `sample_rows.json` (real dataset product name, not a secret) |
| No base64 in docs | 0 long-string lines in `README.md`, `outputs/insights_summary.md`, `data/README.md`, `coder_handoff.md` |
| Plan-tree files | All §5 files exist except `test_report.md` (this file), `optimizer_handoff.md`, `publisher_handoff.md` (later roles) |
| README-referenced files | All exist on disk (4 charts, screenshot, notebook, CSVs, `data_source.json`) |

## Mandatory smoke gate (fresh port 8503 — coder used 8502)

- Server: `.venv/bin/streamlit run src/app.py --server.port 8503 --server.headless true`
- `GET /` → **HTTP 200** (6,467 bytes); `GET /_stcore/health` → **HTTP 200** (`ok`)
- Server log: clean — 0 errors / exceptions / tracebacks
- Screenshot: tall-viewport single-shot (`.stMain` scrollHeight method, per
  Day 10/11 — Playwright `full_page` and scroll-and-stitch fail on Streamlit).
  Playwright is **not** in the Day 12 venv, so the screenshot driver only was
  run from the Day 10 venv (nothing installed). ScrollHeight measured **4723**.
- Tester screenshot: `1200×4723`, **592,338 bytes** — **byte-identical to the
  coder's `screenshots/dashboard.png`** (sha256 `d3de008b…` both files,
  `cmp` clean). This confirms the coder's shot is a genuine capture of this app.
- Dashboard render verified visually from the tester shot: KPI row (4,334
  customers, £10.28m / £8.76m with full values as deltas, Champions 51.5%
  agreement), segment profile table, all 4 charts, k-selection table
  (k=2, silhouette 0.433), SBC cross-check, segment × SBC contingency table,
  methods + limitations, CC BY 4.0 footer. No render errors.
- Server killed; **port 8503 verified free** afterwards (no Streamlit processes).

## Hand validation (tester, independent of the coder's — recomputed from the committed CSVs)

Coder hand-validated 3 customers' R/F/M. The tester recomputed three
*different* metrics from `agreement.csv`, `segment_profile.csv` and
`data_source.json`:

1. **Agreement rate 51.5%** — from `agreement.csv`, multi-order customers
   only (2,829 = 4,334 − 1,505 single-order). Greedy largest-cell-first
   one-to-one mapping: Champions↔Intermittent 1,274, then
   Hibernating↔Lumpy 184 → matched 1,458. 1,458 ÷ 2,829 = **0.515376** =
   51.5%. Recorded `data_source.json` agreement_rate 0.5153764581124072 —
   **diff 0.000000**.
2. **Champions revenue share 84.9% (attributed)** — £7,436,335.441 ÷
   (£7,436,335.441 + £1,324,731.212 = £8,761,066.653) = **0.848793** =
   84.9%, matching `segment_profile.csv` `revenue_share_attributed`
   0.848793. Share of total cleaned revenue 0.723151 also matches the profile.
3. **Unattributed revenue 14.80%** — £1,522,177.33 ÷ £10,283,243.98 =
   **0.148025** = 14.80%, matching `data_source.json`
   `revenue_missing_customer_share` 0.148025. Cross-check: attributed
   £8,761,066.65 + unattributed £1,522,177.33 = £10,283,243.98 = cleaned
   revenue exactly.

## Decider verification (mandatory, plan §2.0)

- **Segment column reproduces exactly from KMeans labels:** mapping from
  `data_source.json` `segment_naming` — cluster 0 → Hibernating (median
  scores R2 F1 M2), cluster 1 → Champions (R4 F5 M5). Independent check over
  all 4,334 rows of `rfm_table.csv`: **0 mismatches**. Segment counts:
  Champions 1,661, Hibernating 2,673 — match coder's claim and the profile.
- **Spot-check by hand (3 customers):** 12346 cluster 1 → Champions
  (segment col Champions, rfm_code 115) ✓; 12347 cluster 1 → Champions
  (rfm_code 555) ✓; 12349 cluster 0 → Hibernating (rfm_code 414) ✓.
- **No customer assigned by the RFM-score rule alone:** nearest-prototype
  rule (§4.2 pool) applied to each customer's own (R, F, M) scores disagrees
  with the KMeans segment for **2,830 of 4,334** customers — exactly the
  coder's claim, and exactly what the decider test asserts (`n_disagree ==
  2830`). Concrete example: customer 12346 (rfm_code 115) is Champions by
  KMeans but the RFM-score rule would call them Big Spenders — the decider
  matters and KMeans won.
- **No surface conflates the groupings:** README:70-71, `insights_summary.md:7`,
  `src/app.py:101,110`, `data/README.md:86-89` all state KMeans is the sole
  decider and RFM scores only name/explain; chart 01 panel (b) and chart 03
  titles carry "KMeans decides". The dedicated tests
  (`test_decider_segment_equals_kmeans_label_mapping`,
  `test_decider_no_customer_assigned_by_rfm_score_rule_alone`) pass.

## Deviation fixes — verified documented

1. **Date parsing `dayfirst=False`** (plan §3.1 said `dayfirst=True`): code
   comment `src/data_pipeline.py:148-155` explains the file uses M/D/YYYY
   (`dayfirst=True` drops 308,950 rows, shifts range to 2010-01-12);
   `data/README.md:34-40` documents the same. Published date range
   2010-12-01 08:26 → 2011-12-09 12:50 matches the raw data and the plan's
   published range.
2. **Calendar-date recency** (plan §4.1 range 1–374): `src/rfm.py:36-37`
   uses `(snapshot.normalize() - last.dt.normalize()).dt.days`;
   `data/README.md:162-164` and `data_source.json` `manual_validation.note`
   document the earlier `Timedelta.days` bug (R=1 for customer 14646, hand: 2)
   and the fix. Recency range in `rfm_table.csv` is 1–374 ✓. Snapshot
   2011-12-10 = max(InvoiceDate) + 1 day ✓.

## Chart legibility (all 4 viewed at 100%)

- **01_rfm_scores.png** — legible, to scale, footnoted. Histogram 3–15 +
  segment counts 2,673 / 1,661 labelled. ✓
- **02_segment_value.png** — legible, to scale, footnoted; Unattributed
  14.8% shown as its own line. Mean £4,477 / £496 per customer match the
  profile. See minor defect D1 (legend swatch).
- **03_kmeans_clusters.png** — legible; centroids marked with white X,
  labels in white boxes (coder's fix verified — no overlap). Title states
  KMeans decides. ✓
- **04_sbc_quadrants.png** — legible, threshold lines at ADI 1.32 / CV² 0.49,
  agreement 51.5% in title, single-order n=1,505 in footnote, quadrant counts
  in legend (Smooth 59, Erratic 88, Intermittent 2,175, Lumpy 507). See
  minor defect D3 (coder-disclosed "Smooth" label position).
- **k = 2 coarseness disclosure** — present in README:181-183 and
  `insights_summary.md:66-69`: "Hibernating" mixes one-time buyers with
  lapsed repeat buyers; the silhouette rule, not preference, chose k = 2.
  Not a defect — recorded for the record.

## Headline numbers — cross-checked against committed CSVs

541,909 raw / 527,795 cleaned rows; £10,283,243.98 cleaned revenue;
4,334 customers; k = 2, silhouette 0.4330 (k=3: 0.3374, k=4: 0.3339,
k=5: 0.3182, k=6: 0.3131, k=7: 0.3029, k=8: 0.2885; SSE 6,467.5 → 2,328.2);
Champions 1,661 / £7,436,335.44; Hibernating 2,673 / £1,324,731.21;
SBC Smooth 59 / Erratic 88 / Intermittent 2,175 / Lumpy 507 / Single-order
1,505; cleaning counts (cancelled 9,288 rows / 3,836 invoices, qty ≤ 0:
1,336, price ≤ 0: 1,181, adjustment: 2,309, unparseable dates 0, missing
description 0) — all agree across `data_source.json`, `segment_profile.csv`,
`sbc_summary.csv`, `agreement.csv`, README, `data/README.md`, insights and
the dashboard. Cleaning counts sum: 541,909 − 9,288 − 1,336 − 1,181 − 2,309
− 0 = 527,795 ✓.

## Defects

### D1 — MINOR — Chart 02 legend swatch does not match the revenue bars
`src/make_charts.py:115-140` (`chart_02`). The "Share of attributed revenue
(%)" bars are coloured per segment (`_colour(segment)` — Champions red,
Hibernating brown), but the legend swatch for that series renders in a
single colour (brown, the first segment after the revenue-ascending sort).
A reader can misread the red Champions bar (84.9%) as belonging to neither
legend entry. Values and labels are correct; fix is cosmetic: use one
neutral colour for all revenue bars, or drop the legend in favour of
per-bar labels.

### D2 — MINOR — Dashboard segment table hides the action column behind a horizontal scroll
`src/app.py:80` (`st.dataframe(profile, width="stretch")`). The profile has
18 columns; in the 1200 px capture the table is cut off after
`mean_recency_days` — the `action` and `gbp_at_stake` columns (the roadmap
deliverable) are only reachable by horizontal scrolling. Consider a compact
action-focused table (segment / n / revenue / action / £ at stake) above the
full table, or a `column_config` that keeps the action visible.

### D3 — MINOR (pre-existing, coder-disclosed) — Chart 04 "Smooth" label sits over the dense cloud
`src/make_charts.py:233-237` (`chart_04`). The "Smooth" label is in the
correct quadrant (ADI ≤ 1.32, CV² ≤ 0.49) and stays legible via its white
box, but it overlaps the dense orange Intermittent point cloud at the
bottom-left — the same pattern as Day 11's chart 03. No data error; a small
nudge (e.g. upper area of the Smooth quadrant) would clear it. Not
demanded for this release.

**No blocking defects. No code was edited by the tester.**

## Optimizer's first step

Fix D1 (one neutral colour for chart 02 revenue bars, or per-bar labels)
and D2 (surface the per-segment action + £ at stake without horizontal
scrolling) — both are small, then re-run `pytest` and re-shoot the
screenshot on a fresh port to confirm nothing moved. D3 is optional.
Everything else is verified and should be carried forward verbatim.
