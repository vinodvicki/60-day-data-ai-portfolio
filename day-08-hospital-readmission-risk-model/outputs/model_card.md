# Model Card — Hospital Readmission Risk Model (Day 08)

**Version:** 1.0 (2026-11-12) · **Status:** analytical exercise — **NOT a clinical tool**

## Model details

Two binary classifiers predict whether a hospital encounter is followed by
readmission within 30 days (`y = 1` if `readmitted == "<30"`, else 0).
Both sit behind the **same** preprocessing (`ColumnTransformer`: numeric →
`StandardScaler`; categorical → `OneHotEncoder(handle_unknown="ignore",
sparse_output=False)`), so the comparison is apples-to-apples. No tuning,
no class weighting, no resampling — both train on the natural 11.16%
prevalence so predicted probabilities stay interpretable as risks.
Threshold 0.5 is the reported operating point; it was not tuned.

| Model | Class | Hyperparameters |
|---|---|---|
| Logistic regression (interpretable baseline) | `LogisticRegression` | `C=1.0`, `max_iter=1000` |
| HistGradientBoosting (comparator) | `HistGradientBoostingClassifier` | `max_iter=300`, `learning_rate=0.05`, `random_state=42` |

**Features (46):** 8 numeric (`time_in_hospital`, `num_lab_procedures`,
`num_procedures`, `num_medications`, `number_outpatient`,
`number_emergency`, `number_inpatient`, `number_diagnoses`) + 38
categorical (race, gender, age band, admission/discharge/source codes
with labels joined from `IDS_mapping.csv`, `medical_specialty`,
`payer_code`, `max_glu_serum`, `A1Cresult`, `change`, `diabetesMed`,
`diag_1/2/3_group` (ICD-9 chapters), 23 medication columns).
`encounter_id` and `patient_nbr` are not features; `patient_nbr` is only
the grouping key for the split.

**Training / evaluation data:** 101,766 raw encounters → 100,114 after
excluding 1,652 expired/hospice discharges (ids 11/19/20/21, labels
verified from `IDS_mapping.csv`). Patient-grouped 80/20 hold-out, seed 42
(`StratifiedGroupKFold`, 5 folds, fold 0 = test): train 80,090 rows
(56,417 patients, 11.34% positive), test 20,024 rows (14,022 patients,
11.35% positive), **zero patient overlap**. 5-fold grouped CV on the
train set only.

## Intended use

- **Intended:** an analytical exercise and portfolio demonstration of a
  classification done properly on messy real health data — leakage
  handled, imbalance handled without distorting probabilities,
  calibration reported instead of assumed.
- **Out of scope / must never be used for:** any clinical decision —
  triage, discharge planning, follow-up prioritisation, or patient
  communication. The model is not validated for care, not validated on
  current practice, and at threshold 0.5 it misses ~99% of readmissions.

## Data

- **Source:** Diabetes 130-US Hospitals for Years 1999–2008, UCI Machine
  Learning Repository (id 296). https://archive.ics.uci.edu/dataset/296/diabetes-130-us-hospitals-for-years-1999-2008
  DOI: https://doi.org/10.24432/C5230J. Licence: **CC BY 4.0**.
- **Citation:** Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014).
  Diabetes 130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine
  Learning Repository. https://doi.org/10.24432/C5230J
- **Intro paper:** Strack et al. (2014), BioMed Research International,
  vol. 2014, Article ID 781670.
- **De-identification:** the dataset is published as de-identified (no
  names, dates of birth or direct identifiers; `encounter_id` /
  `patient_nbr` are arbitrary keys). No re-identification attempt is
  permitted.
- **Coverage:** diabetes patients only; 1999–2008; 130 US hospitals.
  Inclusion: inpatient encounter, diabetes entered as a diagnosis, length
  of stay 1–14 days, lab tests performed, medications administered.
- **Target distribution (raw):** `<30` 11,357 (11.16%), `>30` 35,545
  (34.93%), `NO` 54,864 (53.91%). The `>30` group is folded into the
  negative class; the 3-class split is reported in the notebook, insights
  and chart 01 so that is not hidden.
- **Missing values:** the file uses `?` (the metadata API says "NaN" —
  wrong for this file). `weight` 96.86% missing → dropped. `payer_code`
  39.56%, `medical_specialty` 49.08%, `race` 2.23% missing → kept as an
  explicit "Missing" category. `max_glu_serum` / `A1Cresult` value "None"
  means "not measured" and is a real category, not missing. Full
  per-column rates: `data/README.md` and `data/processed/data_source.json`.
- **Data-size exception:** the raw CSV (~19 MB) is git-ignored and
  downloaded at build time (`python -m src.data_pipeline --live`, verified
  row count + target distribution). Committed provenance: a 500-row raw
  sample, `IDS_mapping.csv`, and compact processed CSVs.

## Metrics (held-out test set, n = 20,024)

Baselines: prevalence-only predictor — ROC-AUC 0.5, PR-AUC 0.1116,
Brier 0.1006 (at the test-set prevalence 0.1135; 0.0991 at the raw
prevalence 0.1116).

| Metric | Logistic regression | HistGradientBoosting |
|---|---|---|
| ROC-AUC | 0.6612 | 0.6761 |
| PR-AUC (average precision) | 0.2071 | 0.2293 |
| Brier score | 0.0971 | 0.0956 |
| Calibration slope (ideal 1) | 0.9131 | 1.0698 |
| Calibration intercept (ideal 0) | −0.1609 | +0.1434 |
| Mean predicted vs observed rate | 0.1125 vs 0.1135 | 0.1126 vs 0.1135 |
| Sensitivity / specificity @ 0.5 | 0.0128 / 0.9977 | 0.0088 / 0.9994 |
| Precision / NPV / F1 @ 0.5 | 0.4203 / 0.8876 / 0.0248 | 0.6667 / 0.8874 / 0.0174 |
| Confusion @ 0.5 (TP / TN / FP / FN) | 29 / 17,712 / 40 / 2,243 | 20 / 17,742 / 10 / 2,252 |
| CV ROC-AUC (5-fold, train) | 0.6633 ± 0.0032 | 0.6736 ± 0.0033 |
| CV PR-AUC (5-fold, train) | 0.2177 ± 0.0070 | 0.2334 ± 0.0071 |

**Calibration deciles:** lowest-risk decile observed 4.0% / 3.8% vs
predicted 4.6% / 4.5%; highest-risk decile observed 26.2% / 28.3% vs
predicted 27.0% / 26.3% (logistic / HistGB). Full table:
`data/processed/calibration_deciles.csv`; chart:
`outputs/charts/03_calibration.png`.

**Interpretation:** discrimination is modest (ROC-AUC 0.66–0.68) and
calibration is reasonable as-is. The strongest signals are prior
inpatient visits (permutation importance Δ ROC-AUC 0.0753) and discharge
disposition (0.0532). Top logistic odds ratios: discharge to a Medicare
swing bed OR 5.32, Hematology OR 3.38, psychiatric hospital OR 3.00,
rehab facility OR 2.30; discharge to hospice at home OR 0.25. All are
associations, not causes, and rare-category odds ratios are noisy.

## Subgroup / fairness

Test-set ROC-AUC / PR-AUC / Brier by age band, gender and race
(`data/processed/subgroup_metrics.csv`; subgroups with n < 500 or
positives < 50 flagged small-n):

- **Age:** ROC-AUC falls with age — [20-30) 0.753 / 0.799 down to
  [90-100) 0.508 / 0.561 (logistic / HistGB). [0-10) has 33 patients and
  0 readmissions: ROC-AUC undefined.
- **Gender:** Female 0.668 / 0.683, Male 0.654 / 0.669 — broadly consistent.
- **Race:** Caucasian 0.661 / 0.676, African American 0.663 / 0.674 —
  near-identical. Hispanic (0.744 / 0.767, n=402), Asian (0.702 / 0.657,
  n=141), Other (0.596 / 0.608, n=319) and Missing-race (0.591 / 0.672,
  n=433) are small-n and should not be over-read.

This is a fairness check on an analytical exercise, not a clinical
validation. Demographic fields are used as features; the subgroup table
exists so a performance gap is visible rather than hidden.

## Limitations

- Diabetes patients only; 1999–2008 US practice (patterns have changed);
  130 hospitals; no external validation set.
- Encounters after a patient's first readmission are not independent
  observations (no encounter ordering to filter on).
- Discharge dispositions 13/14 ("Hospice / home", "Hospice / medical
  facility") are retained per the frozen exclusion list {11, 19, 20, 21};
  only expired/hospice-labelled ids in that list are excluded.
- `weight` (≈97% missing) was dropped; no imputation was attempted for it.
- Discrimination is modest and threshold-0.5 sensitivity is ~1%: the
  model ranks patients; it does not make a yes/no rule.
- Sample-based descriptive rates (chart 01(b), notebook Q1) use the
  committed 1,000-row sample, not the full cohort.

## Future work

- **Recalibration:** Platt scaling / isotonic recalibration, reported
  before and after — explicitly out of scope for Day 8.
- **Threshold selection** against an explicit cost of a missed readmission
  vs a false alarm, instead of the default 0.5.
- **External validation** on a newer, non-diabetes cohort (requires a
  different dataset and governance).
- **Feature work** starting from prior-admission history and discharge
  destination, where the signal is concentrated.

## Ethical considerations

- The data is de-identified example data; no re-identification was
  attempted or is permitted.
- The model must never be used to make care decisions, to prioritise or
  deprioritise patients, or to communicate risk to a patient — it is not
  validated for any of those uses, and its threshold-0.5 sensitivity
  (~1%) would make it dangerous as a rule.
- Subgroup performance is reported so that weaker performance for the
  oldest patients (ROC-AUC ~0.51–0.56 at [90-100)) is visible, not hidden.
- The `>30`-day readmissions are folded into the negative class; the
  3-class distribution is reported alongside so that choice is explicit.
