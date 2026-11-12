"""Day 8 — Hospital Readmission Risk Model: models and evaluation.

Exactly two models behind the SAME preprocessing (plan.md §4.5), so the
comparison is apples-to-apples. No tuning, no class weighting, no
resampling — both models train on the natural 11.16% prevalence so the
predicted probabilities stay interpretable as risks.

Models
------
- Logistic regression (``C=1.0``, ``max_iter=1000``): interpretable
  baseline; coefficients are reported as odds ratios.
- HistGradientBoosting (``max_iter=300``, ``learning_rate=0.05``):
  comparator; permutation importance is reported.

Split
-----
Patient-grouped 80/20 hold-out via ``StratifiedGroupKFold(n_splits=5,
shuffle=True, random_state=42)`` — fold 0 is the test set, folds 1–4 are
the train set (plan.md §4.4). No patient appears in both train and test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.metrics import (
    brier_score,
    calibration_in_the_large,
    calibration_slope_intercept,
    confusion_metrics,
    decile_table,
    pr_auc,
    prevalence_brier,
    roc_auc,
)

SEED = 42
N_SPLITS = 5

# 23 medication columns, derived from the verified 50-column header
# (brief §1.5 said "24" — the header count is 23; plan §11 wins).
MEDICATION_COLUMNS = [
    "metformin",
    "repaglinide",
    "nateglinide",
    "chlorpropamide",
    "glimepiride",
    "acetohexamide",
    "glipizide",
    "glyburide",
    "tolbutamide",
    "pioglitazone",
    "rosiglitazone",
    "acarbose",
    "miglitol",
    "troglitazone",
    "tolazamide",
    "examide",
    "citoglipton",
    "insulin",
    "glyburide-metformin",
    "glipizide-metformin",
    "glimepiride-pioglitazone",
    "metformin-rosiglitazone",
    "metformin-pioglitazone",
]

NUMERIC_FEATURES = [
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
]

CATEGORICAL_FEATURES = [
    "race",
    "gender",
    "age",
    "admission_type_id",
    "discharge_disposition_id",
    "admission_source_id",
    "medical_specialty",
    "payer_code",
    "max_glu_serum",
    "A1Cresult",
    "change",
    "diabetesMed",
    "diag_1_group",
    "diag_2_group",
    "diag_3_group",
    *MEDICATION_COLUMNS,
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """Shared preprocessing: scale numerics, one-hot categoricals."""
    return ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                # Dense output: HistGradientBoosting rejects sparse input,
                # and the shared preprocessor must serve both models.
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def make_logistic_pipeline() -> Pipeline:
    """Interpretable baseline (plan §4.5)."""
    return Pipeline(
        [
            ("preprocess", build_preprocessor()),
            (
                "model",
                LogisticRegression(max_iter=1000, C=1.0, random_state=SEED),
            ),
        ]
    )


def make_histgb_pipeline() -> Pipeline:
    """Tree comparator (plan §4.5)."""
    return Pipeline(
        [
            ("preprocess", build_preprocessor()),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_iter=300, learning_rate=0.05, random_state=SEED
                ),
            ),
        ]
    )


def patient_group_split(
    df: pd.DataFrame, seed: int = SEED
) -> tuple[pd.Index, pd.Index]:
    """Patient-grouped 80/20 split; fold 0 of StratifiedGroupKFold is test.

    Returns ``(train_index, test_index)`` as the frame's own index values.
    """
    splitter = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
    folds = list(splitter.split(df, df["target"], groups=df["patient_nbr"]))
    train_pos, test_pos = folds[0]
    return df.index[train_pos], df.index[test_pos]


def train_models(X_train, y_train) -> dict[str, Pipeline]:
    """Fit both models on the training set; returns ``{name: pipeline}``."""
    models = {
        "logistic": make_logistic_pipeline(),
        "histgb": make_histgb_pipeline(),
    }
    for name, model in models.items():
        model.fit(X_train, y_train)
        print(f"trained {name}")
    return models


def cross_validate(model, X, y, groups, seed: int = SEED) -> dict[str, float]:
    """5-fold StratifiedGroupKFold CV on the given (train) set.

    Returns mean/std of ROC-AUC and PR-AUC. The model is cloned per fold
    by rebuilding it from its own class is not possible for a fitted
    pipeline, so a fresh pipeline of the same kind is built via
    ``sklearn.base.clone``.
    """
    from sklearn.base import clone

    splitter = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
    roc_scores, pr_scores = [], []
    for train_pos, val_pos in splitter.split(X, y, groups=groups):
        fold_model = clone(model)
        fold_model.fit(X.iloc[train_pos], y.iloc[train_pos])
        proba = fold_model.predict_proba(X.iloc[val_pos])[:, 1]
        roc_scores.append(roc_auc(y.iloc[val_pos], proba))
        pr_scores.append(pr_auc(y.iloc[val_pos], proba))
    return {
        "cv_roc_auc_mean": float(np.mean(roc_scores)),
        "cv_roc_auc_std": float(np.std(roc_scores, ddof=1)),
        "cv_pr_auc_mean": float(np.mean(pr_scores)),
        "cv_pr_auc_std": float(np.std(pr_scores, ddof=1)),
    }


def evaluate(model, X_test, y_test) -> dict:
    """All §4.1–4.2 metrics for one fitted model on the held-out test set.

    Returns a dict with the scalar metrics, the decile calibration table
    (DataFrame), the confusion dict, the predicted probabilities and the
    ROC/PR curve points (for chart 02, stored in roc_pr_curves.csv).
    """
    from sklearn.metrics import (
        precision_recall_curve,
        roc_curve,
    )

    proba = model.predict_proba(X_test)[:, 1]
    y = np.asarray(y_test, dtype=float)
    slope, intercept = calibration_slope_intercept(y, proba)
    mean_pred, observed = calibration_in_the_large(y, proba)
    conf = confusion_metrics(y, proba, threshold=0.5)
    fpr, tpr, _ = roc_curve(y, proba)
    precision, recall, _ = precision_recall_curve(y, proba)
    return {
        "roc_auc": roc_auc(y, proba),
        "pr_auc": pr_auc(y, proba),
        "brier": brier_score(y, proba),
        "brier_baseline": prevalence_brier(float(np.mean(y))),
        "calibration_slope": slope,
        "calibration_intercept": intercept,
        "mean_predicted": mean_pred,
        "observed_rate": observed,
        "confusion": conf,
        "deciles": decile_table(y, proba),
        "y_prob": proba,
        "roc_curve": (fpr, tpr),
        "pr_curve": (recall, precision),
    }


def logistic_odds_ratios(pipeline: Pipeline, top_n: int = 20) -> pd.DataFrame:
    """Top ``top_n`` logistic-regression coefficients by |log-odds-ratio|.

    Returns a DataFrame with ``feature``, ``odds_ratio`` and ``log_odds``.
    """
    preprocessor = pipeline.named_steps["preprocess"]
    names = preprocessor.get_feature_names_out()
    coef = pipeline.named_steps["model"].coef_[0]
    frame = pd.DataFrame(
        {"feature": names, "log_odds": coef, "odds_ratio": np.exp(coef)}
    )
    frame["abs_log_odds"] = frame["log_odds"].abs()
    return (
        frame.sort_values("abs_log_odds", ascending=False)
        .head(top_n)
        .drop(columns="abs_log_odds")
        .reset_index(drop=True)
    )


def permutation_importance_top(
    pipeline: Pipeline, X_test, y_test, top_n: int = 20, seed: int = SEED
) -> pd.DataFrame:
    """Top ``top_n`` features by permutation importance (test set, ROC-AUC).

    Permutes the original input columns, so importance is reported per
    modelled feature (not per one-hot dummy).
    """
    result = permutation_importance(
        pipeline,
        X_test,
        y_test,
        n_repeats=5,
        random_state=seed,
        scoring="roc_auc",
        n_jobs=-1,
    )
    frame = pd.DataFrame(
        {
            "feature": list(X_test.columns),
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    )
    return (
        frame.sort_values("importance_mean", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def subgroup_metrics(model, X_test, y_test, df_test: pd.DataFrame) -> pd.DataFrame:
    """Test-set ROC-AUC / PR-AUC / Brier by age band, gender and race.

    ``df_test`` is the cleaned test frame (same row order as ``X_test``)
    carrying the ``age``, ``gender`` and ``race`` columns. Subgroups with
    n < 500 or positives < 50 are flagged ``small_n``.
    """
    proba = model.predict_proba(X_test)[:, 1]
    y = np.asarray(y_test, dtype=float)
    rows = []
    for column, label in (
        ("age", "age_band"),
        ("gender", "gender"),
        ("race", "race"),
    ):
        values = df_test[column].astype(str).to_numpy()
        for group in sorted(set(values)):
            mask = values == group
            n = int(mask.sum())
            positives = int(y[mask].sum())
            sub_y, sub_p = y[mask], proba[mask]
            rows.append(
                {
                    "subgroup_type": label,
                    "subgroup": group,
                    "n": n,
                    "positive_rate": (float(positives / n) if n else float("nan")),
                    "positives": positives,
                    "roc_auc": (
                        roc_auc(sub_y, sub_p)
                        if len(np.unique(sub_y)) == 2
                        else float("nan")
                    ),
                    "pr_auc": (
                        pr_auc(sub_y, sub_p)
                        if len(np.unique(sub_y)) == 2
                        else float("nan")
                    ),
                    "brier": brier_score(sub_y, sub_p),
                    "small_n": bool(n < 500 or positives < 50),
                }
            )
    return pd.DataFrame.from_records(rows)
