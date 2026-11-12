# Optimizer handoff — Day 08 Hospital Readmission Risk Model

**Stage:** optimizer (role 5 of 6) → publisher/reviewer. **Date:** 2026-11-12.
**Verdict: RELEASE-READY.** Both tester defects fixed, charts regenerated and
viewed, all gates pass (pytest 42/42, black + ruff clean, orchestrator
validate 11/11). No live fetch re-run; no model or CSV touched.

## What was changed (exact files)

All paths under `~/workspace/goals/60-day-data-ai-portfolio/day-08-hospital-readmission-risk-model/`:

1. **`src/make_charts.py`** — the only code file changed (2 lines):
   - **D-1, line 350:** `ax2.set_ylim(0.5, 0.85)` → `ax2.set_ylim(0, 0.9)`
     (chart 04(b) y-axis now starts at 0, per plan §7 "no truncated axes").
   - **D-2, line 282:** chart 03 footnote now reads "Brier baseline is the
     prevalence-only predictor (0.1006 at the test-set prevalence 0.1135;
     0.0991 at the raw prevalence 0.1116)." — footnote and legend now agree
     (legend renders the committed `brier_baseline` 0.1006 as "(baseline
     0.101)") and the two baselines are each labelled.
2. **`tests/test_pipeline.py`** — 2 new regression tests, nothing else touched:
   - `test_chart_04b_y_axis_starts_at_zero` (pins `set_ylim(0, 0.9)`, forbids
     the old `set_ylim(0.5, 0.85)`).
   - `test_chart_03_footnote_matches_legend_brier_baseline` (pins the
     footnote wording and asserts both models' committed `brier_baseline`
     is 0.1006). One iteration: the first version compared a pandas Series
     to `pytest.approx`, which does not work element-wise; fixed to an
     explicit per-value tolerance check.
3. **`outputs/charts/03_calibration.png`** — regenerated from the committed
   processed CSVs only (142,434 → 148,939 bytes; dimensions unchanged,
   1500×1050).
4. **`outputs/charts/04_interpretation.png`** — regenerated from the committed
   processed CSVs only (180,050 → 179,433 bytes; dimensions unchanged,
   2100×900). Charts 01 and 02 untouched (timestamps/sizes unchanged).

No other files changed. No doc needed rewriting: every published number in
`README.md`, `data/README.md`, `outputs/insights_summary.md` and
`outputs/model_card.md` was checked against `data/processed/model_metrics.csv`
and matches (see §Verified numbers).

## Defect fixes verified (viewed at full size)

- **D-1 — chart 04(b):** y-axis now runs 0.0–0.9. Logistic [90-100)
  ROC-AUC 0.5079 renders as a substantial bar (~56% of axis height), not a
  ~2% sliver; [20-30) 0.7531 is proportionally taller. All 9 plotted age
  bands (both models) legible; panel (a) still shows all 10 odds-ratio bars;
  the [0-10) omission footnote is unchanged and correct.
- **D-2 — chart 03:** legend "(baseline 0.101)" and footnote "(0.1006 at the
  test-set prevalence 0.1135; 0.0991 at the raw prevalence 0.1116)" now agree
  and each number is labelled. Brier/slope/intercept annotations unchanged
  and matching the committed values (0.097/0.096, 0.91/1.07, −0.16/+0.14).

## Verified numbers (reused verbatim from tester + coder — not recomputed)

- Logistic: ROC-AUC 0.6612, PR-AUC 0.2071, Brier 0.0971, slope 0.9131,
  intercept −0.1609, sensitivity 0.0128 / specificity 0.9977 / precision
  0.4203 / F1 0.0248 @ 0.5; CV ROC-AUC 0.6633 ± 0.0032, CV PR-AUC
  0.2177 ± 0.0070.
- HistGB: ROC-AUC 0.6761, PR-AUC 0.2293, Brier 0.0956, slope 1.0698,
  intercept +0.1434, sensitivity 0.0088 / specificity 0.9994 / precision
  0.6667 / F1 0.0174 @ 0.5; CV ROC-AUC 0.6736 ± 0.0033, CV PR-AUC
  0.2334 ± 0.0071.
- Baselines: prevalence-only ROC-AUC 0.5, PR-AUC 0.1116, Brier **0.1006**
  (test-set prevalence 0.1135) / **0.0991** (raw prevalence 0.1116) — each
  labelled wherever it appears (README, data/README, insights, model card,
  chart 03 footnote + legend).
- Cohort: 101,766 raw; <30 11,357 / >30 35,545 / NO 54,864; 1,652 exclusions
  {11: 1,642; 19: 8; 20: 2; 21: 0}; 100,114 after exclusions; train 80,090 /
  test 20,024, 0 patient overlap.

## Gate results

- `pytest tests/ -q` (day folder): **42 passed** (40 original + 2 new
  regression tests). From portfolio root: **42 passed**. (Expectation was
  40; the +2 is the new pinning tests.)
- `black --check src tests`: clean ("7 files would be left unchanged").
- `ruff check src tests`: clean ("All checks passed!").
- `python -m src.data_pipeline --offline`: exit 0, `data_source.json`
  byte-identical (sha256 `fadf3f4a…ebc3`, matches the tester's hash).
- `requirements.txt`: all 11 pins match the build venv exactly
  (`pip freeze`: pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
  nbformat 5.11.1, scikit-learn 1.9.1, scipy 1.18.1).
- `screenshots/dashboard.png`: present, 1440×6441, 890,909 bytes — the
  tester's fresh capture (port 8503). **Not re-captured** per the optimizer
  brief (re-capture only if missing); see Known gaps.
- `.gitignore`: matches plan §3.4 (scaffold defaults + the three raw-data
  lines `data/raw/diabetic_data.csv`, `data/raw/*.zip`,
  `data/raw/*_synthetic.csv`); nothing else under `data/` excluded.
- File sizes: no file > 1 MB; `data/` total 984,666 bytes (< 5 MB).
- README-referenced files: all 27 checked paths exist on disk (charts,
  screenshot, notebook, all processed CSVs, `data_source.json`,
  `sample_rows.json`, `IDS_mapping.csv`, model card, insights, READMEs).
  The only exception is `data/raw/diabetic_data.csv`, referenced only as
  the git-ignored, never-committed download — expected per plan §3.4.
- Orchestrator validate: `python3 agents/orchestrator.py --day 8 validate`
  → **11/11 checks passed** (no FAIL; the raw-data git-ignore exception
  did not trip the validator — it checks that `data/` as a whole is not
  excluded, and it is not).

## Known gaps / notes for the publisher

1. **`screenshots/dashboard.png` predates the chart regeneration.** It is
   the tester's genuine capture of the running app, and the chart PNGs kept
   the same pixel dimensions (03: 1500×1050, 04: 2100×900), so the dashboard
   layout is unchanged — but the screenshot shows the pre-fix chart 03
   footnote and chart 04(b) axis. If the publisher re-runs the smoke gate
   before pushing (recommended), capture a fresh screenshot then; if not,
   the file as-is is still a real capture of the same app.
2. The workspace copy is not a git checkout (`git status` fails: "not a git
   repository"), so the publisher must confirm `.gitignore` behaviour with
   git before pushing, as the coder already flagged.
3. No other gaps: the PR-AUC trapezoid-vs-average-precision difference
   (+0.0019/+0.0026) is expected, not a defect (tester's §3).

## Publisher's first step

Run the frozen-tree check immediately before pushing: re-verify every file
the READMEs reference exists on disk (charts, `screenshots/dashboard.png`,
CSVs, model card), then push the day folder to
`vinodvicki/60-day-data-ai-portfolio` and verify the live GitHub page
renders. Consider a fresh Streamlit smoke capture first (see gap 1).
