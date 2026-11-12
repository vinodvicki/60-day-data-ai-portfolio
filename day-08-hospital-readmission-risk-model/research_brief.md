# Day 08 — Hospital Readmission Risk Model: Research Brief

**Status:** RESEARCH COMPLETE (AGENTS.md, stage 1) — 2026-11-12.
**Business question:** Which features of a hospital stay are associated with a
patient being readmitted within 30 days of discharge — and how well can a
model discriminate readmitted from non-readmitted patients, and how
well-calibrated are its predicted risks?
**Roadmap entry (verbatim, p. 3):** "DAY 08 | Hospital Readmission Risk Model —
Problem / analysis: Use de-identified example data to study features
associated with readmissions and assess discrimination and calibration.
GitHub deliverable: Reproducible classification notebook with model card."
Section context (Days 7–9, Healthcare & Medical Analytics). Core skills:
SQL, Python, classification, forecasting, Power BI. Suggested data (section
level, Days 7–9): CDC Open Data; de-identified or synthetic hospital
datasets. **No data source is listed for Day 8 itself** — this brief verifies
one from scratch.

## 1. Data source — verified (one lean pass, 2026-11-12)

### 1.1 Source chosen: UCI Diabetes 130-US Hospitals, 1999–2008 (UCI ML Repository, id 296)

- **Source:** Diabetes 130-US Hospitals for Years 1999–2008. Publisher: UCI
  Machine Learning Repository. Donated 2014-05-02; last updated 2024-09-24.
  De-identified inpatient records of patients diagnosed with diabetes at
  130 US hospitals and integrated delivery networks, 1999–2008.
- **Dataset page:** https://archive.ics.uci.edu/dataset/296/diabetes-130-us-hospitals-for-years-1999-2008
- **Metadata API (JSON, no key):** https://archive.ics.uci.edu/api/dataset?id=296
- **DOI:** https://doi.org/10.24432/C5230J
- **Intro paper:** Strack, DeShazo, Gennings, Olmo, Ventura, Cios & Clore,
  "Impact of HbA1c Measurement on Hospital Readmission Rates: Analysis of
  70,000 Clinical Database Patient Records", BioMed Research International,
  vol. 2014, Article ID 781670 —
  https://www.hindawi.com/journals/bmri/2014/781670/
- **Access:** no sign-in, no key, no payment. Static file download.

### 1.2 Exact download route (copy — the coder does not re-derive)

Preferred route (zip, includes the ID-mapping file):

```
GET https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip
```

Contents (verified from the probe download):

| File in zip | Uncompressed size |
|---|---|
| `diabetic_data.csv` | 19,159,383 bytes (~18.3 MB) |
| `IDS_mapping.csv` | 2,547 bytes |

Alternative route (raw CSV only, same data — verified by range probe, header
matches the zip's CSV):

```
GET https://archive.ics.uci.edu/static/public/296/data.csv
```

Do NOT use the `ucimlrepo` Python package route (`fetch_ucirepo(id=296)`) —
it adds a dependency for no benefit; the direct download is simpler and
reproducible. Do NOT use Kaggle mirrors (sign-in required).

### 1.3 Probe results (2026-11-12 — all HTTP 200)

| Probe | Result |
|---|---|
| `HEAD` dataset page | 200 |
| `HEAD` zip URL | 200 |
| `HEAD` `data.csv` URL | 200 |
| Metadata API `?id=296` | 200, JSON: `num_instances` 101766, `num_features` 47, `target_col` `readmitted`, `index_col` `encounter_id`, `patient_nbr` |
| Range probe of zip (first 2 KB requested; server returned whole file, 3,170,254 bytes) | Valid ZIP, 2 files as above |
| CSV line count (probe copy) | 101,767 lines = header + **101,766 rows** — matches metadata exactly |
| CSV header (50 columns, verified) | `encounter_id,patient_nbr,race,gender,age,weight,admission_type_id,discharge_disposition_id,admission_source_id,time_in_hospital,payer_code,medical_specialty,num_lab_procedures,num_procedures,num_medications,number_outpatient,number_emergency,number_inpatient,diag_1,diag_2,diag_3,number_diagnoses,max_glu_serum,A1Cresult,metformin,repaglinide,nateglinide,chlorpropamide,glimepiride,acetohexamide,glipizide,glyburide,tolbutamide,pioglitazone,rosiglitazone,acarbose,miglitol,troglitazone,tolazamide,examide,citoglipton,insulin,glyburide-metformin,glipizide-metformin,glimepiride-pioglitazone,metformin-rosiglitazone,metformin-pioglitazone,change,diabetesMed,readmitted` |

**Data-size rule (planner must record in the plan):** the raw CSV is
~19 MB uncompressed / ~3.2 MB zipped — it EXCEEDS the portfolio rule
(files under 1 MB each, under 5 MB per day folder). The raw data must
therefore be `.gitignore`d for this day (exception to the usual
commit-small-raw-data rule, forced by size). The pipeline downloads it at
build time, verifies row count (101,766) and the target distribution
below, and caches it locally. Commit only `data_source.json`,
`IDS_mapping.csv` (2.5 KB), and a small documented sample if the planner
wants one (≤1,000 rows, ≈190 KB, clearly labelled as a sample).

### 1.4 Target definition — `readmitted` (verified from probe CSV)

Three-class original, binary target for the model (planner confirms):

| Value | Meaning | Rows (probe count) | Share |
|---|---|---|---|
| `<30` | Readmitted within 30 days of discharge | 11,357 | 11.16% |
| `>30` | Readmitted after 30 days | 35,545 | 34.93% |
| `NO` | Not readmitted (in the record window) | 54,864 | 53.91% |
| **Total** | | **101,766** | **100%** |

- **Primary binary target (recommended):** `y = 1` if `readmitted == "<30"`,
  else `0`. Positive rate **11.16%** — imbalanced; report PR-AUC
  alongside ROC-AUC (see §2) and use a stratified split.
- **Report the 3-class distribution** in the notebook/insights even though
  the model is binary, so the ">30" group is not silently folded into the
  negative class without the reader knowing.
- **Inclusion criteria (from the dataset page):** inpatient encounter;
  diabetes entered as a diagnosis; length of stay 1–14 days; lab tests
  performed; medications administered.

### 1.5 Fields the model will use (from the verified variable table)

- **IDs — drop from features:** `encounter_id`, `patient_nbr` (keep
  `patient_nbr` ONLY as the grouping key for the train/test split, §2).
- **Demographics:** `race` (Caucasian / Asian / African American / Hispanic /
  other), `gender`, `age` (10-year bands `[0-10)` … `[90-100)`).
- **Stay:** `admission_type_id` (9 values), `discharge_disposition_id`
  (29 values), `admission_source_id` (21 values), `time_in_hospital`
  (days), `medical_specialty`, `payer_code`.
- **Utilisation (counts in the year before hospitalisation):**
  `number_outpatient`, `number_emergency`, `number_inpatient`;
  in-stay counts: `num_lab_procedures`, `num_procedures`,
  `num_medications`, `number_diagnoses`.
- **Diagnoses:** `diag_1`, `diag_2`, `diag_3` (ICD-9 codes; group into
  broad chapters, e.g. circulatory / respiratory / diabetes / other —
  planner decides the grouping).
- **Labs / meds:** `max_glu_serum`, `A1Cresult`, 24 medication columns
  (`metformin` … `metformin-pioglitazone`), `change`, `diabetesMed`.
- **ID mapping:** `IDS_mapping.csv` maps the integer codes of
  `admission_type_id`, `discharge_disposition_id`, `admission_source_id`
  to labels — the pipeline must load it, not hard-code the labels.

### 1.6 Data-quality notes the coder must handle (verified or documented in the source)

- **Missing values: yes.** The CSV uses `?` as the missing symbol (visible
  in the probe's first data row: `weight` and `payer_code` are `?`, as are
  `diag_2`/`diag_3`). ⚠️ The metadata API says `missing_values_symbol:
  "NaN"` — that is WRONG for this file; treat `?` as missing (see §5).
- **Heavily missing columns (documented in Strack et al. 2014; coder to
  confirm counts from the file):** `weight` ~97% missing, `payer_code`
  ~40% missing, `medical_specialty` ~49% missing. Plan: drop `weight`
  or treat missingness explicitly — planner decides, coder reports the
  exact missing rates.
- **Leakage traps (standard for this dataset — planner must fix the rules
  in the plan before the coder starts):**
  1. `discharge_disposition_id` includes "expired" (died in hospital)
     and hospice discharges — those patients cannot be readmitted. The
     standard practice is to EXCLUDE encounters whose discharge
     disposition is expired / hospice / transferred to another facility
     as appropriate; the exact exclusion list is a plan decision.
  2. **Same patient, many encounters:** `patient_nbr` repeats. The
     train/test split MUST be grouped by `patient_nbr` (no patient in
     both train and test) or the metrics are optimistically biased.
     Use a stratified group split (or GroupKFold for CV).
  3. Encounters after a patient's first readmission are not independent
     observations — note as a limitation in the model card.
- **Scope limits for the model card:** diabetes patients only; 1999–2008
  US data (practice patterns have changed); 130 hospitals; no external
  validation set; demographic fields (race, gender, age) are present —
  report performance by subgroup if the planner includes it, and state
  plainly that the model is an analytical exercise, NOT a clinical tool.

### 1.7 Rate limits and polite-use rule

- None published: this is a static file on the UCI archive, not a
  rate-limited API. One `GET` per build; cache the download under
  `data/raw/` and re-use it (`--offline` / `--use-cache` per the Day 1
  pattern). No key, no header, no retry logic needed beyond a single
  retry on a failed download. Do not hammer the host with repeated
  downloads.

### 1.8 CDC Open Data route — checked, NOT usable for training (2026-11-12)

The roadmap suggests CDC Open Data for Days 7–9. Day 7 already used CDC
PLACES. For Day 8 I searched the CDC Open Data (Socrata) catalog:

- `https://data.cdc.gov/api/views.json?q=readmission` and
  `?q=hospital%20readmission` (both HTTP 200): **no patient-level
  hospital-readmission dataset exists** on data.cdc.gov. The nearest
  items are aggregate only — NHSN "Weekly Hospital Respiratory Admission
  Levels and Rates by Jurisdiction" (`vdzy-6i9v`, admission *levels*, not
  readmissions) and NHAMCS outpatient restricted data.
- **Conclusion:** the CDC route cannot supply training data for a
  patient-level readmission model. The UCI de-identified dataset (§1.1)
  is the roadmap's other suggested source ("de-identified … hospital
  datasets") and is the primary source. No further CDC searching by later
  roles.
- **Optional context only:** CMS Hospital Readmissions Reduction Program
  (HRRP) publishes hospital-level 30-day readmission *rates* — aggregate,
  not patient-level, so it cannot train the model. The CMS metastore API
  probed (`https://data.cms.gov/api/1/metastore/schemas/dataset/items?...`)
  returned the site's HTML shell, not JSON — endpoint NOT verified. Do not
  depend on it; if the planner wants a national benchmark line, the coder
  may cite the published CMS HRRP national rate from the CMS website with
  a URL, or drop it. Not a blocker.

## 2. Metrics to compute (definitions — frozen before the coder starts)

All metrics are computed on the held-out test set (grouped split, §1.6),
from predicted probabilities unless stated otherwise. Report each with its
definition; the tester hand-verifies one of them.

### 2.1 Discrimination

- **ROC-AUC** — area under the receiver-operating-characteristic curve
  (true-positive rate vs false-positive rate over all thresholds).
  0.5 = chance, 1.0 = perfect. Primary discrimination metric.
- **PR-AUC (average precision)** — area under the precision–recall curve.
  Mandatory here because the positive rate is only 11.16%: ROC-AUC can
  look good while precision at usable recall is poor. Baseline = positive
  rate 0.1116.
- **Confusion matrix at threshold 0.5** — plus sensitivity (recall),
  specificity, precision (PPV), NPV and F1 at that threshold. If the
  planner picks a different operating threshold, it must be stated with
  its rationale (e.g. tuned for a target sensitivity) and the 0.5 table
  still reported.

### 2.2 Calibration (the roadmap explicitly requires this)

- **Brier score** — mean squared error between predicted probability and
  the 0/1 outcome: `(1/n) Σ (pᵢ − yᵢ)²`. Lower is better.
  Reference baselines: a constant predictor at the prevalence (0.1116)
  scores Brier = p(1−p) ≈ **0.0991**; a perfect predictor scores 0.
  Report both the model Brier and the prevalence-baseline Brier.
- **Calibration slope and intercept** — fit a logistic regression of the
  observed outcome on the logit of the predicted probability
  (`logit(y) ~ a + b·logit(p)`). Ideal: slope **b = 1**, intercept
  **a = 0**. Slope < 1 means over-confident (predictions too extreme);
  slope > 1 means under-confident.
- **Calibration-in-the-large** — mean predicted probability vs observed
  event rate on the test set (ideal: equal).
- **Decile calibration table + chart** — split test predictions into 10
  equal-size bins by predicted risk; per bin report mean predicted risk,
  observed readmission rate, and n. Chart: observed vs predicted with the
  diagonal (perfect calibration) shown. This is the chart the model card
  links to.
- **Calibration must be reported BEFORE and AFTER any recalibration**
  (e.g. Platt scaling / isotonic) if the coder applies one; the planner
  decides whether recalibration is in scope.

### 2.3 Baselines the model must beat (or be compared against)

- **Prevalence-only (constant 0.1116):** ROC-AUC 0.5, PR-AUC 0.1116,
  Brier ≈ 0.0991.
- **Logistic regression** (interpretable reference, with one-hot / grouped
  features and standard scaling where needed).
- **One tree model** (e.g. HistGradientBoosting or RandomForest — planner
  picks one): the discrimination/calibration comparison is the point of
  the notebook, not chasing the highest AUC.

### 2.4 Splits and validation (planner confirms exact numbers)

- **Hold-out:** stratified split grouped by `patient_nbr`, seed **42**,
  recommended 80/20 train/test (planner confirms).
- **Cross-validation for model selection:** 5-fold stratified group CV
  (GroupKFold with stratification by the binary target where feasible,
  else StratifiedKFold on a patient-level frame — planner decides the
  exact scheme; the rule is only that no patient crosses the fold
  boundary).
- **Report:** test-set metrics for the selected model + CV mean ± std for
  ROC-AUC and PR-AUC. No metric is ever reported from the training set
  as if it were test performance.

## 3. Licence / attribution

- **Licence: CC BY 4.0** — verified on the UCI dataset page (2026-11-12):
  "This dataset is licensed under a Creative Commons Attribution 4.0
  International (CC BY 4.0) license. This allows for the sharing and
  adaptation of the datasets for any purpose, provided that the
  appropriate credit is given."
- **Attribution wording (copy verbatim into README.md, data/README.md and
  the notebook):**
  > Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). Diabetes
  > 130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine Learning
  > Repository. https://doi.org/10.24432/C5230J
- **Also cite** the intro paper (Strack et al. 2014, BioMed Research
  International) in the model card's data section.
- **De-identification note:** the dataset is published as de-identified
  (no names, dates of birth, or direct identifiers; `encounter_id` /
  `patient_nbr` are arbitrary keys). No re-identification attempt is
  permitted; the model card must state the data is de-identified example
  data and the model is not for clinical use.

## 4. Synthetic-fallback note (only if UCI is unreachable at build time)

UCI was verified live on 2026-11-12 (HTTP 200 on page, API, zip and CSV),
so the fallback should not be needed. If the coder's download fails,
DO NOT silently substitute a different real dataset — use this spec, and
label everything synthetic:

- **Rows:** 20,000 encounters, **seed 42**.
- **Columns (subset mirroring the real schema):** `age` (10-year band),
  `gender`, `race`, `time_in_hospital` (1–14), `num_lab_procedures`,
  `num_procedures`, `num_medications`, `number_outpatient`,
  `number_emergency`, `number_inpatient`, `number_diagnoses`,
  `A1Cresult` (None / Norm / >7 / >8), `diabetesMed` (Yes/No),
  `change` (Ch/No), `insulin` (No / Steady / Up / Down), `readmitted`.
- **Target rate:** 11.2% `readmitted = "<30"` (matching the real 11.16%),
  generated by a documented logistic generator: higher odds with longer
  stay, more prior inpatient visits, more medications, more diagnoses,
  `A1Cresult` > 8 — with the generator's coefficients recorded in the
  generator script so the relationship is auditable, not hidden.
- **Labelling:** file `data/raw/diabetic_data_synthetic.csv`, and
  `data_source.json` records `synthetic: true` + `seed: 42`. The synthetic
  file must NEVER overwrite real data, and every output (README, notebook,
  insights, model card) must carry a "synthetic data" banner if it is used.
- **Fallback does not change the metrics in §2** — same definitions,
  same baselines, same split seed.

## 5. Verification status

- [x] Endpoints confirmed against the official source (2026-11-12):
  dataset page, metadata API, zip download, direct CSV — all HTTP 200;
  row count (101,766) and target distribution (11,357 / 35,545 / 54,864)
  verified from the probe copy; licence CC BY 4.0 and citation wording
  read off the dataset page.
- [x] CDC Open Data checked and ruled out for training data (catalog
  search, §1.8); CMS HRRP noted as aggregate-only with an unverified
  endpoint — not a dependency.
- [ ] **Open conflict (recorded, not blocking):** the metadata API says
  `missing_values_symbol: "NaN"`, but the CSV actually uses `?` for
  missing values (confirmed in the probe's first data row). **Test order
  to resolve:** the coder's pipeline treats `?` as missing and reports
  the exact per-column missing rates; if any column's missing rate looks
  wrong (e.g. `weight` not ≈97%), the tester flags it. The planner must
  not assume `NaN`.
- [ ] **Open decision for the planner:** exact discharge-disposition
  exclusion list (§1.6 trap 1), ICD-9 grouping for `diag_1/2/3`, whether
  recalibration is in scope, and whether subgroup (race/gender/age)
  performance is reported. The brief recommends; the plan decides.
- [ ] **Note for the publisher (Day 7 lesson):** keep the push manifest
  under `~/workspace/` instead of `/tmp` — a service restart wiped `/tmp`
  on Day 7. The probe download used here (`/tmp/uci_probe.zip`, 3.2 MB)
  is a throwaway probe only; the coder re-downloads from §1.2.

## 6. Handoff

1. **Produced:** this file
   (`day-08-hospital-readmission-risk-model/research_brief.md`); day
   folder scaffolded by the orchestrator and renamed to the correct slug
   (the orchestrator double-prefixed it as
   `day-08-day-08-hospital-readmission-risk-model`; renamed with `mv`).
2. **Verified numbers:** UCI 130-US Hospitals dataset — 101,766 encounters,
   47 features / 50 columns, 1999–2008, 130 hospitals; target
   `readmitted`: `<30` 11,357 (11.16%), `>30` 35,545 (34.93%), `NO`
   54,864 (53.91%); zip 3,170,254 bytes; CSV 19,159,383 bytes;
   `IDS_mapping.csv` 2,547 bytes; DOI 10.24432/C5230J; licence CC BY 4.0;
   prevalence-baseline Brier ≈ 0.0991; all four probed URLs HTTP 200.
3. **Known gaps:** CDC has no patient-level readmission dataset (ruled
   out, §1.8); CMS HRRP endpoint unverified (aggregate-only, optional);
   `?`-vs-`NaN` missing-symbol conflict (§5); discharge-exclusion list,
   ICD-9 grouping, recalibration scope and subgroup reporting are
   planner decisions, not researcher decisions.
4. **Next role's first step (planner):** fix the plan's §1.6 decisions
   (discharge-disposition exclusions, patient-grouped split, ICD-9
   grouping), the data-size exception (§1.3: raw data gitignored, pipeline
   downloads at build time), and the model set (logistic regression +
   one tree model), then write `plan.md` with the exact file tree and
   the §8 success checklist — including the model card as a named
   deliverable.
