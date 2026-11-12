# Data provenance — Day 08 Hospital Readmission Risk Model

## Source

- **Provider:** UCI Machine Learning Repository (id 296).
- **Dataset:** Diabetes 130-US Hospitals for Years 1999–2008. Donated
  2014-05-02; last updated 2024-09-24. De-identified inpatient records of
  patients diagnosed with diabetes at 130 US hospitals and integrated
  delivery networks, 1999–2008.
- **Dataset page:** https://archive.ics.uci.edu/dataset/296/diabetes-130-us-hospitals-for-years-1999-2008
- **Download used (preferred route, zip):**
  `GET https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip`
  (3,170,254 bytes; `diabetic_data.csv` 19,159,383 bytes + `IDS_mapping.csv`
  2,547 bytes). Alternative (raw CSV only):
  `GET https://archive.ics.uci.edu/static/public/296/data.csv`.
  No sign-in, no key, no payment, no published rate limit. One GET per
  build; cached under `data/raw/` and re-used (`--use-cache`).
- **DOI:** https://doi.org/10.24432/C5230J
- **Licence:** CC BY 4.0. Attribution (verbatim, also in README.md, the
  notebook and the model card):
  > Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). Diabetes
  > 130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine Learning
  > Repository. https://doi.org/10.24432/C5230J
- **Intro paper:** Strack, DeShazo, Gennings, Olmo, Ventura, Cios & Clore,
  "Impact of HbA1c Measurement on Hospital Readmission Rates: Analysis of
  70,000 Clinical Database Patient Records", BioMed Research International,
  vol. 2014, Article ID 781670.
- **De-identification:** no names, dates of birth or direct identifiers;
  `encounter_id` / `patient_nbr` are arbitrary keys. No re-identification
  attempt is permitted.
- **Inclusion criteria (dataset page):** inpatient encounter; diabetes
  entered as a diagnosis; length of stay 1–14 days; lab tests performed;
  medications administered.

## Fetch outcome

- **Fetched:** 2026-11-12 (live run, `python -m src.data_pipeline --live`).
  HTTP 200; zip 3,170,254 bytes, CSV 19,159,383 bytes — both match the
  research brief's probe exactly.
- **Verification passed:** 101,766 rows (header + 101,766) and target
  distribution `<30` 11,357 / `>30` 35,545 / `NO` 54,864 — exactly the
  brief's verified counts. The pipeline asserts both and refuses to
  proceed on a mismatch.
- **CDC Open Data: ruled out for training data** (brief §1.8 — no
  patient-level readmission dataset exists in the catalog). CMS HRRP is
  hospital-level aggregate only: dropped entirely, no benchmark line.

## Row counts and coverage

| Stage | Rows | Notes |
|---|---|---|
| Raw download | 101,766 | 50 columns / 47 features |
| After discharge exclusions | 100,114 | 1,652 removed (below) |
| Train | 80,090 | 56,417 patients, 11.34% positive |
| Test | 20,024 | 14,022 patients, 11.35% positive |
| Test share | 20.0% | within the 18–22% tolerance |
| Patient overlap train/test | 0 | asserted by the pipeline and a test |

**Target (raw):** `<30` 11,357 (11.16%), `>30` 35,545 (34.93%), `NO`
54,864 (53.91%). Binary target `y = 1` if `readmitted == "<30"`, else 0.
After exclusions the positive count is unchanged (11,357 — no excluded
encounter was a `<30` readmission by construction: the excluded patients
died or entered hospice).

**Exclusions** (discharge disposition, labels read from `IDS_mapping.csv`
at build time; no deviation — the labels read Expired/Hospice as expected):

| ID | Label | Rows |
|---|---|---|
| 11 | Expired | 1,642 |
| 19 | Expired at home. Medicaid only, hospice. | 8 |
| 20 | Expired in a medical facility. Medicaid only, hospice. | 2 |
| 21 | Expired, place unknown. Medicaid only, hospice. | 0 |
| **Total** | | **1,652** |

Note: ids 13 ("Hospice / home") and 14 ("Hospice / medical facility")
also contain the word Hospice, but they are **retained** — the frozen
exclusion list is {11, 19, 20, 21} and the label guard passed, so the
label rule did not trigger. The logistic model finds discharge to hospice
at home protective (OR 0.25); see the model card.

## Per-column missing rates (`?` as the missing symbol)

The metadata API says `missing_values_symbol: "NaN"` — that is **wrong**
for this file; the CSV uses `?`. The pipeline loads with
`na_values=["?", ""]` and `keep_default_na=False` (the last part matters:
pandas' default NA strings include "None", but "None" is a real category
for `max_glu_serum` / `A1Cresult` — "not measured" — and must be kept).

| Column(s) | Missing rate |
|---|---|
| `weight` | 96.86% — dropped, not imputed |
| `medical_specialty` | 49.08% — kept as "Missing" category |
| `payer_code` | 39.56% — kept as "Missing" category |
| `race` | 2.23% — kept as "Missing" category |
| `diag_3` | 1.40% — grouped to "Missing" |
| `diag_2` | 0.35% — grouped to "Missing" |
| `diag_1` | 0.02% — grouped to "Missing" |
| `max_glu_serum`, `A1Cresult` | 0.00% — "None" is a real category, not missing |
| Every other column | 0.00% |

**Features modelled (46):** 8 numeric (`time_in_hospital`,
`num_lab_procedures`, `num_procedures`, `num_medications`,
`number_outpatient`, `number_emergency`, `number_inpatient`,
`number_diagnoses`) + 38 categorical (demographics, stay codes with labels
joined from `IDS_mapping.csv`, `max_glu_serum`, `A1Cresult`, `change`,
`diabetesMed`, `diag_1/2/3_group`, and 23 medication columns —
`metformin` … `metformin-pioglitazone`, derived from the verified header;
the brief's "24" was a miscount). `encounter_id` and `patient_nbr` are
not features; `patient_nbr` is only the grouping key for the split.

**ICD-9 grouping** (`diag_1/2/3`, identical for all three): Diabetes
(250.xx), Circulatory 390–459/785, Respiratory 460–519/786, Digestive
520–579/787, Genitourinary 580–629/788, Musculoskeletal 710–739,
Neoplasms 140–239, Injury & poisoning 800–999, Other (incl. V/E codes),
Missing (`?`).

## Commit rule for data files

**Data-size exception (plan §3.4, this day only).** The raw CSV is
19,159,383 bytes — far over the portfolio rule (files < 1 MB each, < 5 MB
per day folder). Therefore:

- **Git-ignored (never committed):** `data/raw/diabetic_data.csv`,
  `data/raw/*.zip`, `data/raw/*_synthetic.csv`. The pipeline downloads the
  raw at build time and verifies it; the files are absent from the repo at
  handoff.
- **Committed provenance artefacts:** `data/raw/sample_rows.json` (500 raw
  rows, 668 KB — the plan's ~190 KB estimate for 1,000 rows was wrong: a
  1,000-row raw sample is 1.33 MB, over the 1 MB file rule, so the sample
  is 500 rows), `data/raw/IDS_mapping.csv` (2,547 bytes), and the compact
  processed CSVs below. Committed `data/` total is ≈ 0.97 MB.
- **Committed processed files:** `data_source.json`,
  `sample_encounters.csv` (1,000-row cleaned sample, seed 42),
  `model_metrics.csv`, `calibration_deciles.csv`,
  `subgroup_metrics.csv`, `feature_importance.csv`, and `roc_pr_curves.csv`
  (ROC/PR curve points, 400 per curve — a documented addition to plan
  §3.5, needed to draw chart 02 offline from committed data; without it
  the curves would have to be invented or the chart dropped).
- **`--offline` never clobbers `data_source.json`** (Day 5/6 lesson): it
  verifies the committed files exist and leaves the live record
  byte-identical. A test asserts this.

## Manual validation (one metric, by hand)

**Prevalence-only Brier score, recomputed by hand from the committed
`model_metrics.csv`:**

- Test-set observed rate = 0.1135 (2,272 / 20,024). A constant predictor
  at the prevalence scores Brier = p(1 − p) = 0.1135 × 0.8865 = **0.1006**,
  matching `brier_baseline` = 0.1006 for both models in
  `model_metrics.csv`.
- At the raw prevalence 0.1116: 0.1116 × 0.8884 = **0.0991**, matching the
  plan's reference value (§4.2).
- Both models beat the baseline (logistic 0.0971, HistGB 0.0956), and the
  notebook's guarded training section re-trained both models and matched
  the committed ROC-AUC / PR-AUC / Brier exactly.

## Versions used for this build

Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
nbformat 5.11.1, scikit-learn 1.9.1, scipy 1.18.1; ruff 0.17.4, black
26.10.1. See [requirements.txt](../requirements.txt).
