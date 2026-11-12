# Coder handoff — Day 08 Hospital Readmission Risk Model

**Stage:** coder (role 3 of 6) → tester. **Date:** 2026-11-12.
**Repo:** `vinodvicki/60-day-data-ai-portfolio`, day folder
`day-08-hospital-readmission-risk-model/`. Built exactly to `plan.md`
(plan wins over the brief where they differ; differences are in plan §11).

## What was produced (exact file paths)

All paths under `~/workspace/goals/60-day-data-ai-portfolio/day-08-hospital-readmission-risk-model/`:

- `src/data_pipeline.py` — download (zip URL, 1 retry, cache), verify,
  clean (§3.3), exclusions with label-governs guard, synthetic fallback
  (seed 42), `--live` / `--use-cache` / `--offline` / `--synthetic`.
- `src/metrics.py` — pure metric functions (Brier, prevalence Brier,
  calibration slope/intercept, calibration-in-the-large, deciles,
  confusion metrics, ROC/PR-AUC wrappers).
- `src/model.py` — shared preprocessor, both pipelines, patient-grouped
  split, CV, evaluation, odds ratios, permutation importance, subgroups.
- `src/make_charts.py` — exactly 4 charts, offline from processed CSVs.
- `src/app.py` — Streamlit dashboard, processed CSVs only, never live-fetches.
- `src/__init__.py` — empty; added so `python -m src.…` and `src.*`
  imports work from any cwd (recorded choice per plan §5).
- `notebooks/analysis.ipynb` — 16 cells, executed via nbconvert, 0 error
  cells (both with raw present — guarded training re-ran — and with raw
  absent — training skipped).
- `tests/test_pipeline.py` — 40 tests (replaces scaffold `test_smoke.py`,
  deleted).
- `data/README.md`, `README.md`, `outputs/insights_summary.md`,
  `outputs/model_card.md` (named deliverable), `requirements.txt`,
  `.gitignore`, `pyproject.toml`.
- `data/raw/sample_rows.json` (500 rows), `data/raw/IDS_mapping.csv`,
  `data/processed/data_source.json`, `sample_encounters.csv` (1,000 rows),
  `model_metrics.csv`, `calibration_deciles.csv`, `subgroup_metrics.csv`,
  `feature_importance.csv`, `roc_pr_curves.csv`.
- `outputs/charts/01_readmission_overview.png`,
  `02_discrimination.png`, `03_calibration.png`,
  `04_interpretation.png` — all viewed by the coder, legible, to scale.
- `screenshots/dashboard.png` — real capture (1440×8200, full page) of
  the running app on port 8502.

## Verified numbers

- **Download:** UCI zip 3,170,254 bytes; CSV 19,159,383 bytes; HTTP 200.
- **Rows:** 101,766 raw; target `<30` 11,357 / `>30` 35,545 / `NO` 54,864
  (11.16% positive) — exactly the brief's verified counts.
- **Missing:** `weight` 96.86% (dropped); `medical_specialty` 49.08%,
  `payer_code` 39.56%, `race` 2.23% (kept as "Missing");
  `max_glu_serum` / `A1Cresult` 0.00% ("None" is a real category — see
  Known gaps for the trap this fixed).
- **Exclusions:** 1,652 rows — id 11 "Expired" 1,642; 19: 8; 20: 2; 21: 0.
  Labels verified from `IDS_mapping.csv`; no deviation (label rule did
  not trigger). Ids 13/14 ("Hospice / home", "Hospice / medical facility")
  retained per the frozen list. 100,114 encounters remain.
- **Split:** train 80,090 rows (56,417 patients, 11.34% positive), test
  20,024 rows (14,022 patients, 11.35% positive), test share 20.0%,
  **0 patient overlap**.
- **Logistic:** ROC-AUC 0.6612, PR-AUC 0.2071, Brier 0.0971, slope 0.9131,
  intercept −0.1609, sensitivity 0.0128 / specificity 0.9977 / precision
  0.4203 / F1 0.0248 @ 0.5; CV ROC-AUC 0.6633 ± 0.0032, CV PR-AUC
  0.2177 ± 0.0070.
- **HistGB:** ROC-AUC 0.6761, PR-AUC 0.2293, Brier 0.0956, slope 1.0698,
  intercept +0.1434, sensitivity 0.0088 / specificity 0.9994 / precision
  0.6667 / F1 0.0174 @ 0.5; CV ROC-AUC 0.6736 ± 0.0033, CV PR-AUC
  0.2334 ± 0.0071.
- **Baselines:** prevalence-only ROC-AUC 0.5, PR-AUC 0.1116, Brier 0.1006
  (test-set prevalence 0.1135; 0.0991 at the raw prevalence 0.1116).
- **Subgroup headline:** ROC-AUC falls with age — [20-30) 0.753/0.799 to
  [90-100) 0.508/0.561 (logistic/HistGB); [0-10) n=33, 0 positives,
  ROC-AUC undefined. Gender Female 0.668 / Male 0.654 (logistic); race
  Caucasian 0.661 / African American 0.663 (logistic).
- **Top signals:** `number_inpatient` permutation importance 0.0753,
  discharge disposition 0.0532; top ORs — swing bed 5.32, Hematology 3.38,
  psychiatric hospital 3.00, hospice/home 0.25.
- **Hand validation (one metric, by hand):** test-set prevalence-only
  Brier = 0.1135 × (1 − 0.1135) = 0.1006, matching `brier_baseline`
  0.1006 in `model_metrics.csv`; at the raw prevalence 0.1116 × 0.8884
  = 0.0991. Recorded in `data/README.md`.

## Gates (all pass)

- venv `.venv` exists; pinned deps installed (pandas 3.1.1, numpy 2.5.4,
  matplotlib 3.11.2, plotly 7.1.0, streamlit 1.66.1, requests 2.34.2,
  pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1,
  scipy 1.18.1; ruff 0.17.4, black 26.10.1).
- `black --check src tests` clean; `ruff check src tests` clean.
- `pytest tests/ -q`: **40 passed**, from the day folder and from the
  portfolio root.
- `python -m src.data_pipeline --offline`: passes, `data_source.json`
  byte-identical.
- Notebook: nbconvert top-to-bottom, 16 cells, **0 error cells**, both
  with raw present (guarded training re-ran; metrics matched committed
  exactly) and with raw absent (training skipped with a note).
- Streamlit smoke: port **8502**, HTTP **200** on `/` and on
  `/_stcore/health`, real `screenshots/dashboard.png` (1440×8200, whole
  page), server killed, port verified free.
- `.gitignore` matches plan §3.4 (raw CSV + `*.zip` + `*_synthetic.csv`
  excluded; nothing else in `data/` excluded). Note: the workspace copy
  is not a git checkout, so `git check-ignore` could not be run here —
  the publisher should confirm with git before pushing.
- Data size: no file > 1 MB; committed `data/` total 984,666 bytes
  (< 1 MB). Raw CSV + zip deleted from disk at handoff (git-ignored).

## Known gaps / defects (and deliberate deviations from the plan)

1. **`roc_pr_curves.csv` is an extra processed file** (not in plan §3.5).
   Chart 02 needs ROC/PR curve points to be drawn offline from committed
   data, and no listed processed file holds them. It is compact (40 KB,
   400 points per curve, endpoints kept) and regenerable. Documented in
   `data/README.md` and here.
2. **`sample_rows.json` is 500 rows, not 1,000.** The plan's ~190 KB
   estimate for 1,000 rows was wrong — a 1,000-row raw sample is 1.33 MB,
   over the 1 MB file rule. 500 rows = 668 KB. Documented in
   `data/README.md` and in a code comment.
3. **"None"-is-a-category trap (fixed).** The first live run loaded with
   pandas' default NA strings, which include "None" — so `max_glu_serum`
   (94.75% "None") and `A1Cresult` (83.28% "None") were read as missing.
   Fixed with `keep_default_na=False, na_values=["?", ""]` in `load_raw`;
   both columns now correctly report 0.00% missing and "None" is a real
   category. Metrics were unchanged at 4 decimals (same partition, new
   label). A test pins this behaviour.
4. **HistGB needs dense input.** The shared `ColumnTransformer` uses
   `OneHotEncoder(sparse_output=False)` because HistGradientBoosting
   rejects sparse matrices (first live run failed on this; fixed and
   re-run). Noted here; plan §4.5 does not specify sparse/dense.
5. **Chart 04(a) label collision (fixed).** Three discharge dispositions
   all start "Discharged/transferred ..." and truncated to identical
   42-char labels, so matplotlib's categorical axis overplotted their
   bars (8 visible rows instead of 10). Fixed with distinct short labels
   (`_or_label` in `make_charts.py`); all 10 bars now show.
6. **Chart 04(b) omits age [0-10).** 33 test patients, 0 readmissions —
   ROC-AUC undefined (NaN). Omitted from the bars and explained in the
   chart footnote; the row is still in `subgroup_metrics.csv`.
7. No `.pbix` (plan §11), no recalibration (out of scope), CMS HRRP
   dropped (plan §11). Synthetic fallback implemented but **not used**
   (live data verified); `data_source.json` records `synthetic: false`.

## Tester's first step

Run, in the day folder's venv (do not reinstall — the venv is handed off
working): `.venv/bin/python -m pytest tests/ -q` (expect 40 passed),
then `.venv/bin/python -m src.data_pipeline --offline` (expect
"data_source.json untouched"), then re-run the Streamlit smoke gate on a
fresh port 8502+ and confirm `screenshots/dashboard.png` matches the
running app. If a live re-run is wanted, `.venv/bin/python -m
src.data_pipeline --live` re-downloads from UCI and should reproduce the
metrics exactly (same seed, same data).
