# Day 12 — Optimizer handoff (Stage 5, DONE 2026-11-16)

**Project:** Customer Segmentation Engine — UCI Online Retail (Dec 2010 – Dec 2011).
**Verdict: PASS — release-ready.** Tester defects D-1 and D-2 fixed; D-3
deliberately left as-is (see below). No working code refactored, no live
API fetch re-run, no published number changed.

## What was produced / changed

- `src/make_charts.py` — D-1 fix only (`chart_02`): revenue bars now one
  neutral colour `#455a64` (was per-segment colours). Legend swatch now
  matches every revenue bar. Values, labels, footnote unchanged.
- `src/app.py` — D-2 fix only: a compact 5-column action table
  (`segment`, `n_customers`, `revenue_gbp`, `action`, `gbp_at_stake`,
  £ columns formatted `£%,.2f`) is shown above the full 18-column
  profile table, under the heading "What to do per segment — action +
  £ at stake". The full table follows unchanged below it.
- `tests/test_pipeline.py` — 2 regression tests added (26 → 28):
  `test_chart_02_revenue_bars_use_one_neutral_colour` (renders chart 02
  and asserts both revenue bars share exactly `#455a64`) and
  `test_dashboard_surfaces_action_and_gbp_without_scrolling` (asserts
  the compact action table exists in `app.py` before the full profile
  table).
- `README.md` — pytest count updated 26 → 28 in both places (run command
  and Validation section). No other number changed.
- `outputs/charts/02_segment_value.png` — regenerated (only chart that
  changed). `screenshots/dashboard.png` — re-captured on fresh port 8504
  (see smoke gate).
- `notebooks/analysis.ipynb` — re-executed via nbconvert (offline, raw
  absent); 16 cells, 0 error cells; now 422,134 bytes.

## Defects

### D-1 — FIXED (minor, cosmetic)
Chart 02 revenue bars were per-segment colours (Champions red,
Hibernating brown) while the legend swatch rendered single-colour brown.
Fix: single neutral `#455a64` for all revenue bars; legend now matches.
Verified visually in the new screenshot and by the new regression test.

### D-2 — FIXED (minor)
The dashboard's 18-column segment table was cut off after
`mean_recency_days` at 1200 px, hiding the action + £-at-stake columns
behind a horizontal scroll. Fix: compact 5-column action table above the
full table — segment, n, revenue, action and £ at stake are all visible
without scrolling (confirmed in the new 1200 px screenshot; action text
is ellipsised inside its cell, as Streamlit renders long text, but the
column and the full £ at stake are visible, and the complete action text
is in the README / insights summary / full table). Full 18-column table
kept unchanged below it.

### D-3 — LEFT AS-IS (optional, minor, pre-existing)
Chart 04 "Smooth" label still sits over the dense point cloud. No
low-risk fix exists: the Smooth quadrant is only 2.4% of the x-axis wide
(ADI 1.32 vs xlim 54.75, set by the 52.1-week max ADI) and 11% of the
y-axis tall (CV² 0.49 vs ylim 4.36), so any label inside it overlaps the
adjacent Intermittent cloud, and moving it up would cross the CV² = 0.49
line into the Erratic quadrant (wrong quadrant). The label is legible via
its white box and is in the correct quadrant — leaving it is acceptable,
as the tester allowed.

## Gates run (all pass)

| Gate | Result |
|---|---|
| `black --check src tests` | clean (8 files) |
| `ruff check src tests` | clean |
| pytest, day folder | **28/28 passed in 8.21 s** |
| pytest, repo root | **28/28 passed in 9.91 s** |
| Notebook via nbconvert (offline, raw absent) | exit 0, 16 cells, **0 error cells** |
| Pipeline `--offline` | exit 0; `data_source.json` byte-identical (sha256 `d3064fb7…`, unchanged); all 4 processed CSVs + charts 01/03/04 byte-identical |
| Orchestrator validate | **11/11** (pytest inside validate: 28 passed) |
| Streamlit smoke, fresh port **8504** | `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200** (`ok`); server log clean (0 errors); server killed, **port 8504 verified free**, no Streamlit processes remain |
| Screenshot | `screenshots/dashboard.png`, **1200×4934, 613,014 bytes** (taller than the tester's 4723 px because the compact action table was added), sha256 `f2fa04d4…`, visually verified: KPI row, compact action table, full profile, all 4 charts, k-selection, SBC tables, methods + limitations, CC BY 4.0 footer |
| File sizes | `data/` total 1,088,044 bytes (< 5 MB); no file > 1 MB anywhere in the day folder (largest: dashboard.png 613,014; `data_source.json` 588,186) |
| Frozen-tree check | All plan §5 files present (incl. this file); no extra deliverable files (only git-ignored `__pycache__`); all README-referenced files exist on disk (4 charts, screenshot, notebook, CSVs, `data_source.json`); `.gitignore` matches plan §3.4 (3 raw-data lines; `data/` itself NOT excluded; plus the tester-noted harmless `*.pyc` line); no base64 strings in any doc |

## Numbers re-verified (spot-check from the committed CSVs — tester's figures carried verbatim)

- Champions revenue share (attributed): £7,436,335.441 ÷
  (£7,436,335.441 + £1,324,731.212) = **0.848793** = 84.9% — matches
  `segment_profile.csv`.
- Attributed £8,761,066.65 + unattributed £1,522,177.33 =
  **£10,283,243.98** = cleaned revenue exactly.
- Unattributed share: £1,522,177.33 ÷ £10,283,243.98 = **0.148025** =
  14.80% — matches `data_source.json`.
- Agreement rate: Champions↔Intermittent 1,274 + Hibernating↔Lumpy 184 =
  1,458 ÷ 2,829 = **0.515376** = 51.5% — matches `data_source.json`.
- Cleaning sum: 541,909 − 9,288 − 1,336 − 1,181 − 2,309 = **527,795** =
  cleaned rows. `rfm_table.csv`: 4,334 rows.
- Champions 1,661 / £7,436,335.44; Hibernating 2,673 / £1,324,731.21;
  `gbp_at_stake` = segment revenue for both — unchanged.

## Files changed (only these)

- `src/make_charts.py` (D-1), `src/app.py` (D-2), `tests/test_pipeline.py`
  (+2 tests), `README.md` (pytest count 26 → 28, two places),
  `outputs/charts/02_segment_value.png` (regenerated),
  `screenshots/dashboard.png` (re-captured),
  `notebooks/analysis.ipynb` (re-executed, 422,134 bytes).
- Deliberately unchanged (byte-identical shas verified): all processed
  CSVs, `data_source.json`, charts 01/03/04, `data/README.md`,
  `outputs/insights_summary.md`, `plan.md`, `coder_handoff.md`,
  `test_report.md`. No `.pytest_cache/` / `.ruff_cache/` in the tree to
  push.

## Known gaps / defects

- None blocking. D-3 left as-is by design (see above). k = 2 coarseness
  disclosure (tester-verified, README + insights) still stands.

## Publisher's first step

Run the frozen-tree check immediately before pushing (re-verify every
file the READMEs reference exists on disk — charts, screenshot, CSVs),
then push the day folder to `vinodvicki/60-day-data-ai-portfolio` per
AGENTS.md stage 6. Push manifest must include the changed files above
(`02_segment_value.png`, `dashboard.png`, `src/make_charts.py`,
`src/app.py`, `tests/test_pipeline.py`, `README.md`,
`notebooks/analysis.ipynb`, `optimizer_handoff.md`) and must NOT include
`.pytest_cache/` or `.ruff_cache/`.
