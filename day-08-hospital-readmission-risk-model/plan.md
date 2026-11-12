# Day 08 — Hospital Readmission Risk Model: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-12) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 08 | Hospital Readmission Risk Model —
Problem / analysis: Use de-identified example data to study features
associated with readmissions and assess discrimination and calibration.
GitHub deliverable: Reproducible classification notebook with model card."
Section context (Days 7–9, Healthcare & Medical Analytics). Core skills:
SQL, Python, classification, forecasting, Power BI. Suggested data (section
level): CDC Open Data; de-identified or synthetic hospital datasets.

| Item | Value |
|---|---|
| Fetch date | 2026-11-12 |
| Source | UCI Diabetes 130-US Hospitals, 1999–2008 (id 296) — de-identified inpatient encounters, 130 US hospitals |
| Expected rows | **101,766 encounters** (verified probe count; header + 101,766 rows), 50 columns / 47 features |
| Target | Binary: `y = 1` if `readmitted == "<30"`, else `0`. Positive rate **11.16%** (11,357 / 101,766) |
| Models | Exactly 2: logistic regression (interpretable baseline) + HistGradientBoosting (comparator) |
| Scope | Analytical exercise on de-identified example data. **Not a clinical tool.** No external validation set; diabetes patients only; 1999–2008 US practice |

## 1. Problem statement + audience

**Problem.** A hospital stay ends, and within 30 days some patients are back.
Day 8 asks two linked questions about that return: *which features of the
stay and the patient are associated with being readmitted within 30 days*,
and *how well can a model tell the two groups apart — and how much can its
predicted risks be trusted?* The second half matters as much as the first:
a model that ranks patients well but whose "20% risk" actually means 5% (or
40%) would mislead any decision made from it, so discrimination (ROC-AUC,
PR-AUC) and calibration (Brier score, slope/intercept, decile table) are
reported side by side, for both models, on the same held-out patients. The
analysis is honest about its limits up front: the data is 1999–2008, covers
diabetes patients only, has no external validation set, and the same patient
can appear many times — so the train/test split is grouped by patient, the
patients who died or went to hospice (and therefore *cannot* be readmitted)
are excluded before modelling, and performance is reported by age, sex and
race as a fairness check.

**Audience / decision-maker.** A data analyst or hiring reviewer who wants to
see a classification done properly on messy real health data: leakage
handled, imbalance handled without distorting the probabilities, calibration
reported instead of assumed, and the model card stating plainly what the
model must never be used for. Every finding must carry its definition and
its denominator, and must say "associated with" — never "causes".

## 2. Research questions (exactly 4)

1. **Which features are associated with readmission within 30 days?**
   Univariate <30-day rates by the main features (prior inpatient visits,
   length of stay, number of medications/diagnoses, A1C result, age band,
   discharge disposition, diagnosis group) plus the logistic regression's
   odds ratios — which factors raise or lower the odds, and by how much?
2. **How well do the models discriminate readmitted from non-readmitted
   patients?** Test-set ROC-AUC and PR-AUC (PR-AUC is mandatory: the
   positive rate is only 11.16%), confusion matrix at threshold 0.5 with
   sensitivity / specificity / precision / NPV / F1, and 5-fold grouped-CV
   mean ± std — for both models, against the prevalence-only baselines.
3. **How well calibrated are the predicted risks?** Brier score (model vs
   prevalence baseline ≈ 0.0991), calibration slope and intercept (ideal
   1 / 0), calibration-in-the-large (mean predicted vs observed rate),
   and the decile calibration table + chart — for both models, as-is, with
   no recalibration (§4.5).
4. **Is performance consistent across patient subgroups?** Test-set ROC-AUC,
   PR-AUC and Brier by age band, by gender and by race, with n and positive
   rate per subgroup — does the model work as well for older patients,
   women, and non-Caucasian patients as for the rest?

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

- **Source:** Diabetes 130-US Hospitals for Years 1999–2008, UCI Machine
  Learning Repository (id 296). Donated 2014-05-02; last updated 2024-09-24.
  Dataset page: https://archive.ics.uci.edu/dataset/296/diabetes-130-us-hospitals-for-years-1999-2008
  Metadata API (no key): https://archive.ics.uci.edu/api/dataset?id=296
  DOI: https://doi.org/10.24432/C5230J
- **Download (coder to use, exactly this URL — preferred route, zip):**
  `GET https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip`
  (3,170,254 bytes; contains `diabetic_data.csv` 19,159,383 bytes +
  `IDS_mapping.csv` 2,547 bytes).
  Alternative (raw CSV only, same data):
  `GET https://archive.ics.uci.edu/static/public/296/data.csv`
  Do NOT use the `ucimlrepo` package route and do NOT use Kaggle mirrors.
- **Access:** no sign-in, no key, no payment, no published rate limit.
  One `GET` per build; cache under `data/raw/` and re-use it
  (`--offline` / `--use-cache` per the Day 1 pattern). One retry on a
  failed download, then stop and report — never hammer the host.
- **CDC Open Data: ruled out for training data** (brief §1.8 — no
  patient-level readmission dataset exists in the catalog). CMS HRRP is
  hospital-level aggregate only with an unverified endpoint: **not a
  dependency and not a benchmark line — dropped entirely** (§11).
- **Inclusion criteria (dataset page):** inpatient encounter; diabetes
  entered as a diagnosis; length of stay 1–14 days; lab tests performed;
  medications administered.

### 3.2 Target (verified counts from the probe — reuse verbatim)

| `readmitted` value | Meaning | Rows | Share |
|---|---|---|---|
| `<30` | Readmitted within 30 days | 11,357 | 11.16% |
| `>30` | Readmitted after 30 days | 35,545 | 34.93% |
| `NO` | Not readmitted (in the record window) | 54,864 | 53.91% |
| **Total** | | **101,766** | **100%** |

- **Binary target:** `y = 1` if `readmitted == "<30"`, else `0`.
- **Report the 3-class distribution** in the notebook, insights and model
  card even though the model is binary, so the `>30` group is not silently
  folded into the negative class without the reader knowing.

### 3.3 Cleaning rules (frozen — the tester tests these)

1. **Missing symbol is `?`, not `NaN`.** The metadata API says
   `missing_values_symbol: "NaN"` — that is WRONG for this file (brief
   §5 open conflict). Load with `na_values=["?"]` (and empty strings).
   The pipeline reports the exact per-column missing rate for every
   column; the tester flags it if `weight` is not ≈97% missing.
2. **Drop `weight`** (≈97% missing — documented in Strack et al. 2014,
   coder confirms the exact rate). Do not impute it. Record the exact
   rate in `data_source.json`.
3. **Keep high-missing categoricals as explicit "Missing" categories**
   (do not drop the rows): `payer_code` (~40% missing),
   `medical_specialty` (~49% missing), `race` (`?`), `diag_2` / `diag_3`
   (`?`). Missingness here is informative, not random.
4. **`max_glu_serum` / `A1Cresult` value "None" means "not measured"** —
   it is a real category, not missing. Keep as-is.
5. **Drop IDs from features:** `encounter_id` (row key) and `patient_nbr`
   (kept ONLY as the grouping key for the split, §4.4).
6. **ID mapping:** load `IDS_mapping.csv` from the zip — do NOT hard-code
   the labels for `admission_type_id`, `discharge_disposition_id`,
   `admission_source_id`. The pipeline joins the labels and records the
   mapping version (file size 2,547 bytes) in `data_source.json`.
7. **ICD-9 grouping for `diag_1` / `diag_2` / `diag_3`** (fixed table —
   applied identically to all three columns; the original codes are then
   dropped):

   | Group | ICD-9 codes |
   |---|---|
   | Diabetes | `250.xx` (code starts with `250`) |
   | Circulatory | 390–459, 785 |
   | Respiratory | 460–519, 786 |
   | Digestive | 520–579, 787 |
   | Genitourinary | 580–629, 788 |
   | Musculoskeletal | 710–739 |
   | Neoplasms | 140–239 |
   | Injury & poisoning | 800–999 |
   | Other | Every other numeric code (incl. 001–139, 240–279 except 250, 280–289, 290–319, 320–389, 680–709, 740–779, 780–784, 789–799) and all V/E codes |
   | Missing | `?` / empty |

   Implementation: strip the code, take the integer part before any `.`
   (e.g. `250.13` → 250, `786.05` → 786); codes starting with `V` or `E`
   → Other. A test asserts the mapping on fixtures (`250.13` → Diabetes,
   `428` → Circulatory, `786.05` → Respiratory, `?` → Missing).
8. **Exclusions — discharge disposition (DECIDED, §1.6 item 1).**
   Exclude encounters whose `discharge_disposition_id` is in
   **{11, 19, 20, 21}** — Expired and hospice discharges under the UCI
   `IDS_mapping.csv` numbering. These patients died or entered hospice
   and therefore *cannot* be readmitted within 30 days; keeping them
   would label impossible negatives and bias the model. Guard (the
   numbering is the one place the plan does not trust from memory): the
   pipeline reads the labels from `IDS_mapping.csv` at build time, logs
   the label + count for each excluded ID, and records them in
   `data_source.json`. **If the labels do not read Expired / Hospice*,
   the label rule governs, not the IDs** — exclude every disposition
   whose label contains "Expired" or "Hospice", record the actual IDs
   used and the deviation in `data/README.md` and plan §11, and do not
   silently proceed on IDs alone. No other encounters are excluded
   (no transfer exclusion, no deduplication — see limitation in §4.6).
   The coder records rows before/after exclusion and the per-ID counts.
9. **Features (46 modelled; weight dropped from the 47 in the metadata):**
   - **Numeric (8):** `time_in_hospital`, `num_lab_procedures`,
     `num_procedures`, `num_medications`, `number_outpatient`,
     `number_emergency`, `number_inpatient`, `number_diagnoses`.
   - **Categorical (38):** `race`, `gender`, `age`,
     `admission_type_id`, `discharge_disposition_id`,
     `admission_source_id`, `medical_specialty`, `payer_code`,
     `max_glu_serum`, `A1Cresult`, `change`, `diabetesMed`,
     `diag_1_group`, `diag_2_group`, `diag_3_group`, and the medication
     columns from the verified header (`metformin` …
     `metformin-pioglitazone`; the coder derives the list from the
     header and records the count — see §11 on the brief's "24").
   - `gender` value "Unknown/Invalid" is kept as its own category.

### 3.4 Data-size exception and commit rule (READ CAREFULLY — differs from Days 1–6)

- The raw CSV is **19,159,383 bytes (~18.3 MB)** — far over the portfolio
  rule (files < 1 MB each, < 5 MB per day folder). Therefore the
  **DATA-SIZE EXCEPTION** applies to this day only:
  - **`.gitignore` MUST exclude the raw data:** `data/raw/diabetic_data.csv`,
    `data/raw/*.zip`, `data/raw/*_synthetic.csv` (synthetic fallback is
    always git-ignored). This is the one deliberate deviation from the
    "do NOT ignore `data/`" rule (Day 1 lesson (d)) — the exception is
    forced by size and is recorded here, in `data/README.md`, and in the
    model card.
  - **The pipeline downloads the raw at build time** (`--live`), verifies
    row count = 101,766 and the target distribution in §3.2, and caches
    it under `data/raw/` for re-use (`--use-cache`). `--offline` runs
    from the committed processed files only (no network, no raw needed)
    and regenerates charts + summaries from them.
  - **Committed provenance artefacts (small, the reproducibility record):**
    `data/raw/sample_rows.json` (≤ 1,000 rows of the raw CSV, ≈ 190 KB,
    clearly labelled as a sample), `data/raw/IDS_mapping.csv` (2,547
    bytes), and the compact processed files in §3.5. Expected `data/`
    total < 1 MB.
- **`.gitignore` otherwise follows the scaffold default:** `__pycache__/`,
  `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`,
  `.pytest_cache/`, `.ipynb_checkpoints/`, plus the three raw-data lines
  above. The tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Source, URLs, DOI, licence, fetch date, row counts (raw / after exclusions / train / test), target distribution, per-column missing rates, exclusion counts + labels, split scheme + seed, model hyperparameters, metric summary |
| `data/processed/sample_encounters.csv` | 1,000-row cleaned sample (seed 42): grouped features + binary target — the offline EDA / SQL-check frame |
| `data/processed/model_metrics.csv` | One row per model: ROC-AUC, PR-AUC, Brier, Brier-baseline, calibration slope/intercept, calibration-in-the-large, sensitivity, specificity, precision, NPV, F1 @ 0.5, CV ROC-AUC mean±std, CV PR-AUC mean±std |
| `data/processed/calibration_deciles.csv` | Both models × 10 decile bins: bin, n, mean predicted risk, observed rate |
| `data/processed/subgroup_metrics.csv` | Per subgroup (age band, gender, race): n, positive rate, ROC-AUC, PR-AUC, Brier |
| `data/processed/feature_importance.csv` | Logistic-regression odds ratios (top 20 by \|log-OR\|) + HistGB permutation importance (top 20) |

- The full cleaned modelling frame (~100k rows) is **not** committed
  (size). It is rebuilt by `python -m src.data_pipeline --live` from the
  cached/downloaded raw, and the notebook re-runs training from it when
  present (§6, notebook rule). The committed summary CSVs are the
  offline-reproducible record: every number in the README, insights and
  model card must match them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date). It regenerates only the derived tables/charts
  from the committed CSVs; a test asserts this.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if the UCI download fails):** per brief §4 —
  20,000 encounters, seed 42, documented logistic generator (higher odds
  with longer stay, more prior inpatient visits, more medications, more
  diagnoses, `A1Cresult` > 8; coefficients recorded in the generator),
  target rate 11.2% `<30`. File `data/raw/diabetic_data_synthetic.csv`
  (git-ignored, NEVER overwrites real data); `data_source.json` records
  `synthetic: true, seed: 42`; README, dashboard, notebook, insights and
  model card all carry a "synthetic data" banner if it is used. Metrics
  (§4) are unchanged. Not expected to be needed (all probes HTTP 200).
- **Licence: CC BY 4.0.** Attribution verbatim in README.md,
  data/README.md, the notebook and the model card:
  > Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). Diabetes
  > 130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine Learning
  > Repository. https://doi.org/10.24432/C5230J
  Also cite Strack et al. 2014 (BioMed Research International, vol. 2014,
  Article ID 781670) in the model card's data section.
- **De-identification note:** no names, dates of birth or direct
  identifiers; `encounter_id` / `patient_nbr` are arbitrary keys. No
  re-identification attempt is permitted; the model card states the data
  is de-identified example data and the model is not for clinical use.

## 4. Analysis — definitions (from the brief, frozen)

### 4.1 Discrimination (test set, from predicted probabilities)

- **ROC-AUC** — primary discrimination metric (0.5 = chance, 1.0 = perfect).
- **PR-AUC (average precision)** — mandatory: positive rate is only
  11.16%; baseline = **0.1116**.
- **Confusion matrix at threshold 0.5** — sensitivity (recall),
  specificity, precision (PPV), NPV, F1. Threshold stays 0.5; no
  threshold tuning (the 0.5 table is the reported operating point).

### 4.2 Calibration (test set, as-is — §4.5)

- **Brier score** — `(1/n) Σ (pᵢ − yᵢ)²`. Prevalence-only baseline:
  p(1−p) ≈ **0.0991** at p = 0.1116. Report model Brier and baseline.
- **Calibration slope and intercept** — logistic regression of the outcome
  on the logit of the predicted probability; ideal slope **1**, intercept
  **0**. Slope < 1 = over-confident; > 1 = under-confident.
- **Calibration-in-the-large** — mean predicted probability vs observed
  event rate on the test set (ideal: equal).
- **Decile calibration table + chart** — 10 equal-size bins by predicted
  risk; per bin mean predicted risk, observed rate, n; chart shows
  observed vs predicted with the perfect-calibration diagonal.

### 4.3 Baselines the models must be compared against

- **Prevalence-only (constant 0.1116):** ROC-AUC 0.5, PR-AUC 0.1116,
  Brier ≈ 0.0991.
- **Logistic regression** (interpretable reference) and **one tree model**
  — the comparison is the point, not chasing the highest AUC.

### 4.4 Split and validation (DECIDED)

- **Hold-out: 80/20, grouped by `patient_nbr`, seed 42.** Mechanism
  (fixed): `StratifiedGroupKFold(n_splits=5, shuffle=True,
  random_state=42)` on the cleaned frame — fold 0 is the test set, folds
  1–4 are the train set. This gives an approximately 80/20 split that is
  both patient-grouped (no patient in both train and test — a test
  asserts zero overlap) and approximately stratified on the binary target.
  The coder records train/test rows, unique patients, and positive rates
  in `data_source.json`; if the test share falls outside 18–22%, report
  it rather than forcing an exact 20%.
- **Cross-validation for model selection:** 5-fold `StratifiedGroupKFold`
  (same scheme, seed 42) on the TRAIN set only. Report CV mean ± std for
  ROC-AUC and PR-AUC per model. No metric is ever reported from the
  training set as if it were test performance.
- **No class weighting, no resampling.** Both models train on the natural
  11.16% prevalence, so predicted probabilities remain interpretable as
  risks and the calibration assessment is meaningful. PR-AUC (not
  accuracy) is the imbalance-aware discrimination metric; accuracy is
  not reported as a headline metric.

### 4.5 Model set (DECIDED — exactly two models, same preprocessing)

Both models sit behind the SAME `ColumnTransformer` (numeric →
`StandardScaler`; categorical → `OneHotEncoder(handle_unknown="ignore")`)
so the comparison is apples-to-apples. Fixed hyperparameters, no grid
search — the comparison, not tuning, is the deliverable.

1. **Logistic regression (baseline, interpretable):**
   `LogisticRegression(max_iter=1000, C=1.0)`. Coefficients are reported
   as odds ratios (top 20 by |log-OR|) — this is the interpretability
   half of Q1.
2. **HistGradientBoostingClassifier (comparator — chosen over
   RandomForest):** `HistGradientBoostingClassifier(max_iter=300,
   learning_rate=0.05, random_state=42)`. Justification: stronger tabular
   performance than RandomForest on 100k rows, materially faster to fit,
   and its probabilities are typically better calibrated than a forest's
   (forests push probabilities toward the middle). RandomForest was
   considered and rejected on those two grounds — speed and calibration.
   Permutation importance (top 20, on the test set, seed 42) is reported.

### 4.6 Recalibration and subgroup scope (DECIDED)

- **Recalibration: OUT of scope for Day 8.** Calibration is reported
  as-is for both models (§4.2). If a model is badly miscalibrated, the
  notebook, insights and model card say so — they do not fix it.
  Platt scaling / isotonic recalibration is recorded as future work in
  the model card. (If the coder applies any recalibration, the plan is
  violated — send it back.)
- **Subgroup performance: IN scope.** Test-set ROC-AUC, PR-AUC and Brier
  by **age band** (the 10-year bands as stored), **gender** (Male /
  Female / Unknown) and **race** (Caucasian / African American / Hispanic
  / Asian / Other / Missing), with n and positive rate per subgroup, in
  `subgroup_metrics.csv`, chart 04(b) for age, and the model card's
  fairness section. Subgroups with n < 500 or positives < 50 are flagged
  "small-n, interpret with care". This is a fairness check on an
  analytical exercise, not a clinical validation.
- **Limitations to state in the model card:** encounters after a patient's
  first readmission are not independent observations (no extra filtering
  — the data has no encounter ordering to filter on); diabetes patients
  only; 1999–2008 US practice (patterns have changed); 130 hospitals;
  no external validation set.

### 4.7 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `sample_encounters.csv` loaded into an in-memory
SQLite database (`sqlite3`, stdlib): the <30-day readmission rate by age
band (and by `number_inpatient` group). A test asserts the SQL and pandas
numbers agree. This is the day's SQL element; no `.pbix` is built (see
§11) and the pipeline itself stays pandas.

## 5. File tree (exact — build only this)

```
day-08-hospital-readmission-risk-model/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── sample_rows.json        (≤1,000 rows, provenance sample)
│   │   └── IDS_mapping.csv         (2,547 bytes, from the zip)
│   └── processed/
│       ├── data_source.json
│       ├── sample_encounters.csv   (1,000-row cleaned sample, seed 42)
│       ├── model_metrics.csv
│       ├── calibration_deciles.csv
│       ├── subgroup_metrics.csv
│       └── feature_importance.csv
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py                 (only if `python -m src.…` needs it —
│   │                                Day 7 pattern; coder decides, records
│   │                                the choice in the coder handoff)
│   ├── data_pipeline.py
│   ├── model.py
│   ├── metrics.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   ├── model_card.md
│   └── charts/
│       ├── 01_readmission_overview.png
│       ├── 02_discrimination.png
│       ├── 03_calibration.png
│       └── 04_interpretation.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is REPLACED by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No `data/raw/diabetic_data.csv`
and no `data/raw/*.zip` on disk at handoff (git-ignored, §3.4); the
validator's data-size check therefore passes on the real files. No extra
modules, no extra charts, no `.pbix`, no `weekly_briefing.md`.

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download (zip URL §3.1, 1 retry, cache to `data/raw/`), verify row count 101,766 + target distribution §3.2; load with `na_values=["?"]`; load `IDS_mapping.csv` and join labels; `clean` (§3.3 rules 1–9 incl. ICD-9 grouping + exclusions with per-ID counts); write `sample_rows.json`, `sample_encounters.csv`, `data_source.json`; modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42); `--keep-raw` debug flag (default off — raw is cached, not deleted, because re-downloading is the expensive part; the file is git-ignored either way) |
| `src/model.py` | `NUMERIC_FEATURES` / `CATEGORICAL_FEATURES` lists (§3.3 rule 9); `build_preprocessor()`; `make_logistic_pipeline()` / `make_histgb_pipeline()` (hyperparameters §4.5); `patient_group_split(df)` (StratifiedGroupKFold, fold 0 = test, seed 42); `train_models(X_train, y_train)`; `cross_validate(model, X, y, groups)` (5-fold, mean ± std ROC-AUC / PR-AUC); `evaluate(model, X_test, y_test)` (all §4.1–4.2 metrics + deciles); permutation importance for HistGB |
| `src/metrics.py` | Pure functions, no I/O, no network — all tested: `brier_score(y, p)`, `prevalence_brier(rate)`, `calibration_slope_intercept(y, p)`, `calibration_in_the_large(y, p)`, `decile_table(y, p)`, `confusion_metrics(y, p, threshold=0.5)`; thin wrappers around `sklearn.metrics` for ROC-AUC / PR-AUC |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the UCI source + DOI + "de-identified example data, not a clinical tool" + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): cohort + target overview; model comparison (ROC/PR/calibration from committed CSVs, model selector); subgroup table; feature-effects table; model-card link; methods + limitations panel; `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with CC BY 4.0 attribution; "NOT a clinical tool" banner |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): EDA on the committed sample + processed tables answering Q1–Q4; the 4 charts inline; the SQL check (§4.7); **training section guarded by `RAW.exists()`** — if `data/raw/diabetic_data.csv` is present it re-runs training via `src.model` and asserts the metrics match the committed `model_metrics.csv` within tolerance; if absent it loads the committed metrics and prints a note that training was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: `?`-as-missing + `weight` ≈97% missing; exclusion counts + zero overlap of patients across the split; ICD-9 grouping fixtures; target rate 11.16% on the sample; Brier / decile / calibration-slope hand-checks on fixtures; confusion metrics at 0.5; offline run does not clobber `data_source.json` live fields; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.7) |
| `outputs/model_card.md` | **Named deliverable (roadmap).** Model details (both models, hyperparameters, preprocessing), intended use + out-of-scope uses (NOT clinical), data section (source, DOI, CC BY 4.0, Strack et al. citation, de-identification note, 1999–2008 + diabetes-only limits), training/evaluation data (split scheme, exclusions, n), metrics (discrimination AND calibration, both models, with baselines), subgroup / fairness section, limitations, future work (recalibration), ethical considerations |
| `data/README.md` | Provenance: URLs, DOI, licence, fetch date, row counts (raw / after exclusions / train / test), target distribution, per-column missing rates, exclusion labels + counts, split scheme, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2 question with exact numbers + one actionable recommendation + limitations |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (metric table + chart thumbnails), headline findings with numbers, validation, limitations, attribution |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 7 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat) **plus scikit-learn + scipy** (new runtime deps for this day — HistGradientBoosting, calibration, permutation importance). No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88); `.gitignore` per §3.4 (raw-data lines are the only data exclusions) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_data(url: str, dest: Path) -> Path
def load_raw(csv_path: Path) -> pd.DataFrame          # na_values=["?"]
def load_id_mapping(csv_path: Path) -> dict[str, dict[int, str]]
def group_icd9(code: str) -> str
def clean_encounters(df: pd.DataFrame, mapping: dict) -> pd.DataFrame
def apply_exclusions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def make_binary_target(s: pd.Series) -> pd.Series     # 1 if "<30" else 0
def write_data_source(path: Path, record: dict) -> None

# src/model.py
def build_preprocessor() -> ColumnTransformer
def make_logistic_pipeline() -> Pipeline
def make_histgb_pipeline() -> Pipeline
def patient_group_split(df: pd.DataFrame, seed: int = 42) -> tuple[pd.Index, pd.Index]
def train_models(X_train, y_train) -> dict[str, Pipeline]
def cross_validate(model, X, y, groups, seed: int = 42) -> dict[str, float]
def evaluate(model, X_test, y_test) -> dict  # metrics + decile table + confusion

# src/metrics.py
def brier_score(y_true, y_prob) -> float
def prevalence_brier(rate: float) -> float
def calibration_slope_intercept(y_true, y_prob) -> tuple[float, float]
def calibration_in_the_large(y_true, y_prob) -> tuple[float, float]
def decile_table(y_true, y_prob) -> pd.DataFrame
def confusion_metrics(y_true, y_prob, threshold: float = 0.5) -> dict
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units, source footnote ("Source: UCI
Diabetes 130-US Hospitals 1999–2008, DOI 10.24432/C5230J, CC BY 4.0 —
de-identified example data, not a clinical tool"), no truncated axes,
legible at 100% zoom.

1. **01_readmission_overview.png** — Two panels: (a) horizontal bar of the
   3-class `readmitted` distribution with counts + %; (b) <30-day rate by
   prior inpatient visits (`number_inpatient` 0 / 1 / 2 / 3+), with n
   labelled per bar. Answers Q1's descriptive half.
2. **02_discrimination.png** — Two panels: (a) ROC curves, both models +
   chance diagonal, AUCs in the legend; (b) PR curves, both models +
   prevalence baseline 0.1116, APs in the legend. Answers Q2.
3. **03_calibration.png** — Calibration plot: observed vs mean predicted
   rate per decile for both models + perfect-calibration diagonal; Brier,
   slope and intercept annotated per model. Answers Q3.
4. **04_interpretation.png** — Two panels: (a) logistic-regression odds
   ratios, top 10 by |log-OR| on a log scale with the 1.0 line; (b)
   test-set ROC-AUC by age band, grouped bars for both models.
   Answers Q1's model half and Q4 (age).

The Streamlit dashboard embeds the 4 PNGs (as Day 6/7 do) so the README
thumbnails and the app agree. Subgroup results by gender and race live in
the committed table + model card (chart 04 covers age only).

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URLs, DOI, licence/attribution
      (CC BY 4.0, verbatim citation), fetch date (2026-11-12), row counts
      (raw 101,766 / after exclusions / train / test), target distribution,
      per-column missing rates, exclusion labels + counts — in
      `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → clean → split → train →
      evaluate → charts, with `--offline` mode) + metric definitions
      (§4.1–4.2) written down
- [ ] **Model card delivered** (`outputs/model_card.md`) — roadmap
      deliverable, with intended use, out-of-scope uses, data, metrics,
      subgroup/fairness, limitations, future work
- [ ] **Discrimination AND calibration reported** for both models on the
      held-out test set (ROC-AUC, PR-AUC, Brier vs 0.0991 baseline,
      slope/intercept, calibration-in-the-large, decile table + chart)
- [ ] **Patient-grouped split** enforced (no patient in both train and
      test — asserted by a test) and **discharge exclusions {11, 19, 20,
      21} applied with labels verified from `IDS_mapping.csv`**
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2 question with exact numbers) + one actionable recommendation
- [ ] README with setup instructions, sample outputs (metric table +
      chart thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; **data-size exception
      honoured** (no file > 1 MB, `data/` < 5 MB; raw CSV + zip
      git-ignored per §3.4 and absent at handoff; `.gitignore` matches §5/§6)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. the
      prevalence Brier or one decile bin — from the committed CSVs,
      matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert, with `_find_root()` and the guarded training section, §6)
- [ ] Pinned dependencies in `requirements.txt` (incl. scikit-learn +
      scipy); `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and
      on `/_stcore/health`, **real `screenshots/dashboard.png`** captured,
      server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs, model card)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes (≥ 15 tests)
- [ ] `.gitignore` matches §3.4/§5 (raw CSV + zip + synthetic excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+)
- [ ] `data/` total < 5 MB, no file > 1 MB; no raw CSV/zip on disk at handoff (git-ignored); `data_source.json` records live counts, exclusions, missing rates, split sizes
- [ ] Target distribution verified against §3.2 (11,357 / 35,545 / 54,864); `weight` missing rate ≈97% confirmed and recorded
- [ ] Build only what §5 lists; no extra web searches

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| UCI download fails at build time | Synthetic fallback (§3.6, seed 42, labelled everywhere); one retry, then stop and report |
| `?`-vs-`NaN` missing-symbol conflict (§3.3 rule 1) | Load with `na_values=["?"]`; per-column missing rates reported; tester flags if `weight` not ≈97% |
| Exclusion IDs don't match Expired/Hospice labels in `IDS_mapping.csv` | Label rule governs (§3.3 rule 8); actual labels + counts recorded, deviation noted |
| Same patient in train and test (leakage) | `StratifiedGroupKFold` by `patient_nbr`; test asserts zero patient overlap |
| Imbalance (11.16% positive) misread via accuracy | Accuracy is not a headline metric; PR-AUC + confusion matrix at 0.5 reported |
| Calibration misread as "the model is wrong" | Report as-is with slope/intercept/Brier; recalibration explicitly future work (§4.6) |
| Raw CSV too big to commit | §3.4 exception: git-ignored, downloaded at build, small committed provenance artefacts |
| Notebook can't train offline (no raw data) | Guarded training section (§6); notebook fully executable from committed processed CSVs |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |

## 11. Differences from the brief (plan wins)

- **Exclusion list (§3.3 rule 8):** the brief (§1.6) left the exact list
  open; the plan fixes **{11, 19, 20, 21}** with the label-verification
  guard (label rule governs if IDs and labels disagree).
- **Split mechanism (§4.4):** the brief recommended an 80/20 stratified
  grouped split; the plan fixes the mechanism
  (`StratifiedGroupKFold`, 5 folds, fold 0 = test, seed 42) and the
  18–22% test-share tolerance.
- **ICD-9 grouping (§3.3 rule 7):** the brief left the grouping open; the
  plan fixes the 10-group chapter table, applied identically to
  `diag_1/2/3`.
- **Model set (§4.5):** the brief offered HistGradientBoosting *or*
  RandomForest; the plan picks **HistGradientBoosting** (speed +
  calibration) and fixes both models' hyperparameters with no tuning.
- **Recalibration (§4.6):** the brief left it open; the plan puts it
  **out of scope** — calibration reported as-is, recalibration is future
  work.
- **Subgroup reporting (§4.6):** the brief left it open; the plan puts it
  **in scope** (age band, gender, race; ROC-AUC / PR-AUC / Brier + n).
- **Class weighting (§4.4):** the brief did not specify; the plan fixes
  **no class weighting and no resampling**, so predicted probabilities
  stay interpretable as risks.
- **Medication-column count (§3.3 rule 9):** the brief (§1.5) says "24
  medication columns"; counted from the verified 50-column header there
  are **23** (`metformin` … `metformin-pioglitazone`) plus `change` and
  `diabetesMed`. The plan wins — the coder derives the list from the
  header and records the count.
- **CMS HRRP benchmark (§3.1):** the brief (§1.8) left open citing the
  published CMS national rate; the plan **drops it entirely** (endpoint
  unverified, aggregate-only) — no benchmark line.
- **Power BI:** the roadmap's section-level core skills list Power BI, but
  the Day 8 deliverable is the "reproducible classification notebook with
  model card". No `.pbix` is built; the notebook + Streamlit dashboard
  are the deliverables. The SQL skill is covered by the §4.7 check.
- **Notebook training (§6):** the brief did not specify notebook
  mechanics; the plan adds the guarded training section (trains when the
  raw CSV is present, otherwise loads committed metrics — 0 errors
  either way).
- **Data-size exception (§3.4):** the brief (§1.3) anticipated it; the
  plan fixes the exact `.gitignore` lines and the committed artefacts
  (≤1,000-row sample, `IDS_mapping.csv`, compact processed CSVs).

## 12. Build order

1. `src/data_pipeline.py` — download → verify counts → clean (§3.3) →
   exclusions → sample + `data_source.json` (live run; cache raw).
2. `src/metrics.py` + `src/model.py` — pure metrics, preprocessing,
   both models, grouped split, CV, evaluation → processed CSVs.
3. `src/make_charts.py` — 4 charts from the processed CSVs.
4. `notebooks/analysis.ipynb` — EDA + Q1–Q4 + SQL check + guarded
   training section; run via nbconvert, 0 errors.
5. `src/app.py` — Streamlit dashboard from processed CSVs only; smoke
   test on a fresh port (8502+) + real `screenshots/dashboard.png`.
6. `tests/test_pipeline.py` — ≥ 15 tests (§6); `pytest`, `black`,
   `ruff`; coder handoff checklist (§9).
7. Docs — `README.md`, `data/README.md`, `outputs/insights_summary.md`,
   `outputs/model_card.md`; every number checked against the committed
   processed CSVs.
