"""Day 8 — Hospital Readmission Risk Model (Streamlit).

Which features of a hospital stay are associated with readmission within
30 days, and how well do two models discriminate and calibrate? All
numbers come from the committed processed CSVs — the app never fetches
live data and never trains a model.

Run: streamlit run src/app.py  (from the project root)
Data: data/processed/*.csv — offline, no network, no API.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Streamlit runs app.py as a script (script dir on sys.path, not the
# project root), so make the project root importable for `src.*`.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
ATTRIBUTION = (
    "Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). Diabetes "
    "130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5230J — CC BY 4.0."
)
MODEL_NAMES = {
    "logistic": "Logistic regression",
    "histgb": "HistGradientBoosting",
}


@st.cache_data
def load_all() -> (
    tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]
):
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    metrics = pd.read_csv(PROCESSED_DIR / "model_metrics.csv")
    deciles = pd.read_csv(PROCESSED_DIR / "calibration_deciles.csv")
    subgroups = pd.read_csv(PROCESSED_DIR / "subgroup_metrics.csv")
    importance = pd.read_csv(PROCESSED_DIR / "feature_importance.csv")
    sample = pd.read_csv(PROCESSED_DIR / "sample_encounters.csv")
    return record, metrics, deciles, subgroups, importance, sample


RECORD, METRICS, DECILES, SUBGROUPS, IMPORTANCE, SAMPLE = load_all()

st.set_page_config(page_title="Hospital Readmission Risk Model", layout="wide")
st.title("Hospital Readmission Risk Model")
st.markdown(
    "Which features of a hospital stay are associated with being readmitted "
    "within 30 days — and how well can a model tell the two groups apart, "
    "and how much can its predicted risks be trusted? Two models, one "
    "patient-grouped hold-out, discrimination **and** calibration reported "
    "side by side."
)
st.warning(
    "Analytical exercise on de-identified example data (diabetes patients, "
    "1999–2008). **NOT a clinical tool** — never use it to make care decisions."
)
if RECORD.get("synthetic"):
    st.warning("SYNTHETIC DATA — labelled fallback, not UCI values.")

dist = RECORD["target_distribution_raw"]
total = sum(dist.values())
col1, col2, col3, col4 = st.columns(4)
col1.metric("Encounters (raw)", f"{total:,}")
col2.metric(
    "Readmitted <30 days", f"{dist['<30']:,} ({dist['<30'] / total * 100:.2f}%)"
)
col3.metric("After exclusions", f"{RECORD['n_after_exclusions']:,}")
col4.metric(
    "Test set",
    "20,024 rows",
    "14,022 patients",
)
st.caption(
    f"Discharge exclusions (expired / hospice): "
    f"{RECORD['exclusions']['n_excluded']:,} encounters removed — "
    f"ids {RECORD['exclusions']['excluded_ids']}. Train/test split is "
    f"grouped by patient (seed 42); no patient appears in both sets."
)

st.header("Model comparison — discrimination and calibration")
model = st.selectbox(
    "Model",
    options=["logistic", "histgb"],
    format_func=lambda m: MODEL_NAMES[m],
)
row = METRICS.set_index("model").loc[model]
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "ROC-AUC (test)",
    f"{row['roc_auc']:.3f}",
    f"CV {row['cv_roc_auc_mean']:.3f} ± {row['cv_roc_auc_std']:.3f}",
)
m2.metric(
    "PR-AUC (test)",
    f"{row['pr_auc']:.3f}",
    f"baseline {RECORD['prevalence_baseline']['pr_auc']:.3f}",
)
m3.metric("Brier score", f"{row['brier']:.3f}", f"baseline {row['brier_baseline']:.3f}")
m4.metric(
    "Calibration slope / intercept",
    f"{row['calibration_slope']:.2f} / {row['calibration_intercept']:+.2f}",
    "ideal 1 / 0",
)
st.markdown(
    f"At threshold 0.5: sensitivity (recall) **{row['sensitivity']:.3f}**, "
    f"specificity **{row['specificity']:.3f}**, precision (PPV) "
    f"**{row['precision']:.3f}**, NPV **{row['npv']:.3f}**, F1 "
    f"**{row['f1']:.3f}** — TP {int(row['tp']):,}, TN {int(row['tn']):,}, "
    f"FP {int(row['fp']):,}, FN {int(row['fn']):,}. Mean predicted risk "
    f"**{row['mean_predicted']:.3f}** vs observed rate "
    f"**{row['observed_rate']:.3f}** (calibration-in-the-large)."
)
st.dataframe(
    METRICS[
        [
            "model",
            "roc_auc",
            "pr_auc",
            "brier",
            "calibration_slope",
            "calibration_intercept",
            "sensitivity",
            "specificity",
            "precision",
            "f1",
            "cv_roc_auc_mean",
            "cv_pr_auc_mean",
        ]
    ].rename(
        columns={
            "model": "Model",
            "roc_auc": "ROC-AUC",
            "pr_auc": "PR-AUC",
            "brier": "Brier",
            "calibration_slope": "Cal. slope",
            "calibration_intercept": "Cal. intercept",
            "sensitivity": "Sensitivity",
            "specificity": "Specificity",
            "precision": "Precision",
            "f1": "F1",
            "cv_roc_auc_mean": "CV ROC-AUC",
            "cv_pr_auc_mean": "CV PR-AUC",
        }
    ),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Both models train on the natural 11.16% prevalence — no class "
    "weighting, no resampling — so predicted probabilities stay "
    "interpretable as risks. No recalibration was applied (future work)."
)

st.header("Calibration deciles")
st.dataframe(
    DECILES[DECILES["model"] == model][
        ["decile", "n", "mean_predicted", "observed_rate"]
    ].rename(
        columns={
            "decile": "Decile",
            "n": "n",
            "mean_predicted": "Mean predicted risk",
            "observed_rate": "Observed rate",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.header("Is performance consistent across subgroups?")
sub_type = st.selectbox(
    "Subgroup",
    options=["age_band", "gender", "race"],
    format_func=lambda s: {"age_band": "Age band", "gender": "Gender", "race": "Race"}[
        s
    ],
)
sub = SUBGROUPS[
    (SUBGROUPS["model"] == model) & (SUBGROUPS["subgroup_type"] == sub_type)
]
st.dataframe(
    sub[
        [
            "subgroup",
            "n",
            "positives",
            "positive_rate",
            "roc_auc",
            "pr_auc",
            "brier",
            "small_n",
        ]
    ].rename(
        columns={
            "subgroup": "Subgroup",
            "n": "n",
            "positives": "Positives",
            "positive_rate": "Positive rate",
            "roc_auc": "ROC-AUC",
            "pr_auc": "PR-AUC",
            "brier": "Brier",
            "small_n": "Small-n flag",
        }
    ),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Subgroups with n < 500 or positives < 50 are flagged small-n — "
    "interpret with care. This is a fairness check on an analytical "
    "exercise, not a clinical validation."
)

st.header("What is associated with readmission?")
odds = IMPORTANCE[
    (IMPORTANCE["model"] == "logistic") & (IMPORTANCE["metric"] == "odds_ratio")
].copy()
odds["abs_log"] = odds["extra"].abs()
odds = odds.sort_values("abs_log", ascending=False).head(20)
st.markdown(
    "**Logistic-regression odds ratios** (top 20 by |log-OR|). An odds "
    "ratio above 1 means higher odds of <30-day readmission for that "
    "category, relative to the model's reference level — an association, "
    "not a cause."
)
st.dataframe(
    odds[["effect_feature", "value", "extra"]].rename(
        columns={
            "effect_feature": "Feature (one-hot level)",
            "value": "Odds ratio",
            "extra": "Log-odds",
        }
    ),
    width="stretch",
    hide_index=True,
)
perm = IMPORTANCE[
    (IMPORTANCE["model"] == "histgb")
    & (IMPORTANCE["metric"] == "permutation_importance")
]
st.markdown("**HistGradientBoosting permutation importance** (top 20, test set).")
st.dataframe(
    perm[["effect_feature", "value", "extra"]].rename(
        columns={
            "effect_feature": "Feature",
            "value": "Importance (Δ ROC-AUC)",
            "extra": "Std",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.header("Charts")
for chart in (
    "01_readmission_overview.png",
    "02_discrimination.png",
    "03_calibration.png",
    "04_interpretation.png",
):
    st.image(str(CHARTS_DIR / chart), width="stretch")

st.header("Methods, definitions & limitations — read this first")
st.markdown("""
- **Target:** binary — 1 if `readmitted == "<30"` (11,357 of 101,766
  encounters, 11.16%), else 0. The `>30` group (35,545) is folded into the
  negative class; the 3-class split is shown in chart 01 so that is not hidden.
- **Leakage handled:** the split is grouped by `patient_nbr` (no patient in
  both train and test), and encounters discharged expired or to hospice
  (1,652) are excluded before modelling — those patients cannot be readmitted.
- **Missing values:** the file uses `?` as the missing symbol. `weight`
  (~97% missing) was dropped; `payer_code`, `medical_specialty`, `race` and
  `diag_2`/`diag_3` keep "Missing" as an explicit category.
- **Diagnoses:** `diag_1/2/3` (ICD-9) are grouped into 10 chapters
  (Diabetes, Circulatory, Respiratory, Digestive, Genitourinary,
  Musculoskeletal, Neoplasms, Injury & poisoning, Other, Missing).
- **Imbalance:** accuracy is not a headline metric — PR-AUC and the
  confusion matrix at threshold 0.5 are, because the positive rate is only
  11.16%.
- **Calibration:** reported as-is (Brier, slope/intercept, deciles). No
  recalibration was applied; Platt/isotonic scaling is future work.
- **Limits:** diabetes patients only; 1999–2008 US practice (patterns have
  changed); 130 hospitals; no external validation set; encounters after a
  patient's first readmission are not independent observations.
""")
st.caption(ATTRIBUTION)
st.caption(
    "Intro paper: Strack et al. (2014), BioMed Research International, "
    "vol. 2014, Article ID 781670."
)
