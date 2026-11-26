# Day 19 — Credit Card Fraud Detection: Build Plan

**Status:** FROZEN — planner, 2026-11-26. Source of truth for the build.
**Source:** roadmap entry (Phase 2, Banking, Finance & Economics) +
`research_brief.md`. No extra web searches. Describe only what the
roadmap lists: train imbalanced classifiers; compare recall, precision
and the operational cost of false alarms; deliverable is a fraud
detection metrics panel with threshold tradeoffs.

## 1. Problem

A card issuer sees 284,807 transactions in two days, of which 492
(0.17%) are fraud. A model that predicts "never fraud" is 99.83%
accurate and useless. The questions this day answers:

1. Which imbalanced classifier catches the most fraud (recall) while
   keeping false alarms (precision) manageable?
2. How do precision and recall trade off as the decision threshold moves?
3. What does each threshold cost in dollars — missed fraud vs. review
   time on false alarms — and which threshold minimises that cost?

## 2. Audience / decision-maker

A fraud-operations lead deciding (a) which model to put behind the
alert queue and (b) where to set the alert threshold, balancing fraud
losses against analyst review workload.

## 3. Data

- Source: Hugging Face mirror `RS2k03/creditcard-fraud-dataset`,
  `creditcard.csv` (same file as Kaggle's, verified fingerprint:
  284,807 rows, 492 frauds, md5 `e90efcb83d69faf99fcab8b0255024de`).
  No key. One GET. See brief §1a.
- Raw file is 144 MB: NOT committed, git-ignored in
  `data/raw/creditcard.csv`, local-only cache. Pipeline `--live`
  downloads + fingerprint-checks; `--offline` replays from the cache.
  Before validate/push the raw file moves to
  `~/workspace/day-19-data/creditcard.csv` (Day 18 precedent).
- Split: stratified 70/30 train/test, seed 42. Features V1–V28 plus
  standardised Amount and Time.
- Models (brief §3): majority baseline, logistic regression
  (`class_weight="balanced"`), random forest (200 trees,
  `class_weight="balanced_subsample"`, seed 42).- Cost model (brief §2): missed fraud costs its Amount; a false alarm
  costs $5.00 review (assumption, labelled everywhere); cost reported
  per 10,000 transactions.

## 4. File tree (exact)

```
day-19-credit-card-fraud-detection/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── .pre-commit-config.yaml
├── research_brief.md  plan.md
├── checkpoint-stage1-researcher.md  checkpoint-stage2-planner.md
├── checkpoint-stage3-coder.md  checkpoint-stage4-tester.md
├── checkpoint-stage5-optimizer.md  checkpoint-stage6-publisher.md
├── coder_handoff.md  test_report.md  optimizer_handoff.md
├── publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/creditcard.csv            (git-ignored, local-only, 144 MB)
│   └── processed/
│       ├── data_source.json
│       ├── class_summary.csv
│       ├── amount_summary.csv
│       ├── amount_hist.csv
│       ├── model_metrics.csv
│       ├── confusion_matrix.csv
│       ├── threshold_sweep.csv
│       ├── cost_curve.csv
│       └── pr_curves.csv
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── analysis.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_class_imbalance.png
│       ├── 02_pr_curves.png
│       ├── 03_threshold_tradeoff.png
│       └── 04_cost_curve.png
├── screenshots/dashboard.png
└── tests/
    ├── conftest.py
    ├── test_pipeline.py
    ├── test_analysis.py
    └── test_smoke.py
```

## 5. Per-file responsibilities

- `src/data_pipeline.py` — download (live) / load (offline) raw CSV,
  fingerprint check, stratified split, feature standardisation,
  train 3 models, write all 9 processed files + `data_source.json`.
  CLI: `--live | --offline | --use-cache`. No network in `--offline`.
- `src/analysis.py` — pure functions reused by pipeline/tests:
  `confusion_at_threshold`, `metrics_at_threshold`,
  `threshold_sweep`, `expected_cost`, `pr_auc`/`roc_auc`,
  `summarise_classes`, `summarise_amounts`. No I/O, no model training.
- `src/make_charts.py` — draws the 4 charts from processed CSVs only,
  to scale, legible, 1280 px wide.
- `src/app.py` — Streamlit metrics panel: reads processed CSVs +
  charts only; model comparison table; threshold slider recomputing
  precision/recall/cost from `threshold_sweep.csv`; cost assumptions
  and all 5 limitations on the page.
- `notebooks/analysis.ipynb` — reads processed CSVs only; reproduces
  the headline numbers and the 4 charts inline; `_find_root()` from the
  notebook file location (Day 1 lesson).
- `tests/conftest.py` — sys.path bootstrap (Day 17 fix) + a small
  seeded synthetic fixture (test-only, clearly labelled; never written
  to `data/`).
- `tests/test_pipeline.py` — fingerprint constants, cost/sweep math on
  the fixture, processed-file existence/shape.
- `tests/test_analysis.py` — metric formulas vs. hand-computed values,
  threshold sweep monotonicity, cost model edge cases.
- `tests/test_smoke.py` — README embeds the 4 charts + dashboard
  preview, all referenced files exist, no secrets in tree.
- `requirements.txt` — pinned to the venv-verified versions (pandas
  3.1.1, numpy 2.5.4, matplotlib 3.11.2, streamlit 1.66.1, requests
  2.34.2, pytest 9.2.0, pytest-cov 7.1.0, jupyter 1.1.1, nbformat
  5.11.1, scikit-learn 1.9.1, scipy 1.18.1; dev tools black 26.10.1,
  ruff 0.17.4, mypy 2.4.1 in the portfolio-root requirements-dev.txt).

## 6. Charts (4, all embedded in the day README Visuals section)

1. `01_class_imbalance.png` — class counts (log scale) + Amount
   distribution by class (log Amount axis).
2. `02_pr_curves.png` — precision–recall curves for all 3 models on the
   test set, PR-AUC in the legend; no-legend ROC curve is NOT the point.
3. `03_threshold_tradeoff.png` — precision, recall and F1 vs. decision
   threshold for the best model (by PR-AUC).
4. `04_cost_curve.png` — expected cost per 10,000 transactions vs.
   threshold, minimum marked; stacked split of missed-fraud dollars vs.
   review dollars at the minimum.

## 7. Success criteria checklist (from the roadmap — all must pass)

- [ ] Problem statement + audience written (README)
- [ ] Data provenance documented (data/README.md)
- [ ] 2+ labelled charts produced (4 produced)
- [ ] 3 findings + 1 actionable recommendation (outputs/insights_summary.md)
- [ ] README with setup instructions, sample outputs, limitations
- [ ] No credentials in the repo; no huge files committed (raw 144 MB git-ignored)
- [ ] One metric manually validated and recorded (tester hand-checks one
      number from the processed CSVs, e.g. fraud count or a threshold row)
- [ ] Pipeline runs end-to-end from a clean checkout (`--live` re-downloads)
- [ ] Notebook runs top-to-bottom without errors (reads processed CSVs only)

## 8. Risks & mitigations

- Raw file too large to commit → git-ignored cache + processed-only
  commits; pipeline re-downloads on `--live` (verified ~8 s).
- Validate counts `data/` on disk → move raw cache to
  `~/workspace/day-19-data/` before validate/push (Day 18 precedent).
- Thresholds swept on the test set → labelled illustrative in every doc.
- Random forest on 199k training rows is slow-ish (~1–2 min) →
  acceptable; n_estimators fixed at 200, no tuning grid.
- Notebook must not read the raw CSV (CI runs it without the cache) →
  notebook reads processed CSVs only; tested by executing from a copy
  without `data/raw/`.

## 9. Build order

researcher (done) → planner (this file) → coder (venv, pipeline,
analysis, charts, app, notebook, tests, gates) → tester (independent
re-verification + smoke + hand-validation) → optimizer (gaps only,
re-run gates) → publisher (stage PNGs first, then text push).
