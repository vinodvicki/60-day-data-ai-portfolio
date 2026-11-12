"""Day 8 — Hospital Readmission Risk Model: pure metric functions.

No I/O, no network. Every function here is unit-tested in
tests/test_pipeline.py. Definitions follow plan.md §4.1–4.2 (from
research_brief.md §2).

Conventions
-----------
- ``y_true``: binary 0/1 outcomes (1 = readmitted within 30 days).
- ``y_prob``: predicted probabilities in [0, 1].
- ``calibration_slope_intercept`` returns ``(slope, intercept)``; ideal
  is (1, 0).
- ``calibration_in_the_large`` returns ``(mean_predicted, observed_rate)``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import average_precision_score, roc_auc_score

_EPS = 1e-6


def _as_arrays(y_true, y_prob) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(y_prob, dtype=float).ravel()
    if y.shape != p.shape:
        raise ValueError("y_true and y_prob must have the same length")
    if len(y) == 0:
        raise ValueError("empty input")
    return y, np.clip(p, _EPS, 1.0 - _EPS)


def roc_auc(y_true, y_prob) -> float:
    """Area under the ROC curve (0.5 = chance, 1.0 = perfect)."""
    y, p = _as_arrays(y_true, y_prob)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, p))


def pr_auc(y_true, y_prob) -> float:
    """Average precision (area under the precision-recall curve).

    Baseline for a constant predictor is the positive rate.
    """
    y, p = _as_arrays(y_true, y_prob)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(average_precision_score(y, p))


def brier_score(y_true, y_prob) -> float:
    """Mean squared error between predicted probability and 0/1 outcome."""
    y, p = _as_arrays(y_true, y_prob)
    return float(np.mean((p - y) ** 2))


def prevalence_brier(rate: float) -> float:
    """Brier score of a constant predictor at the prevalence ``rate``.

    A constant ``p`` scores ``p * (1 - p)``; at the Day 8 prevalence
    0.1116 that is ~0.0991.
    """
    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate must be in [0, 1]")
    return float(rate * (1.0 - rate))


def calibration_slope_intercept(y_true, y_prob) -> tuple[float, float]:
    """Calibration slope and intercept.

    Fits ``logit(P(y=1)) = a + b * logit(p)`` by maximum likelihood
    (2-parameter logistic regression on the logit of the predictions).
    Ideal: slope ``b = 1``, intercept ``a = 0``. Slope < 1 means the
    predictions are over-confident (too extreme); slope > 1 means
    under-confident.
    """
    y, p = _as_arrays(y_true, y_prob)
    logit_p = np.log(p / (1.0 - p))

    def neg_log_lik(params: np.ndarray) -> float:
        a, b = params
        z = a + b * logit_p
        # log(sigmoid(z)) computed stably: -softplus(-z).
        log_sigmoid = -np.logaddexp(0.0, -z)
        log_one_minus = -np.logaddexp(0.0, z)
        return float(-np.sum(y * log_sigmoid + (1.0 - y) * log_one_minus))

    result = minimize(neg_log_lik, x0=np.array([0.0, 1.0]), method="L-BFGS-B")
    if not result.success:
        raise RuntimeError(f"calibration fit failed: {result.message}")
    intercept, slope = float(result.x[0]), float(result.x[1])
    return slope, intercept


def calibration_in_the_large(y_true, y_prob) -> tuple[float, float]:
    """(mean predicted probability, observed event rate). Ideal: equal."""
    y, p = _as_arrays(y_true, y_prob)
    return float(np.mean(p)), float(np.mean(y))


def decile_table(y_true, y_prob) -> pd.DataFrame:
    """Calibration deciles: 10 equal-size bins by predicted risk.

    Returns a DataFrame with columns ``decile`` (1–10, lowest risk first),
    ``n``, ``mean_predicted`` and ``observed_rate``.
    """
    y, p = _as_arrays(y_true, y_prob)
    order = np.argsort(p, kind="stable")
    chunks = np.array_split(order, 10)
    rows = []
    for i, idx in enumerate(chunks, start=1):
        rows.append(
            {
                "decile": i,
                "n": len(idx),
                "mean_predicted": float(np.mean(p[idx])),
                "observed_rate": float(np.mean(y[idx])),
            }
        )
    return pd.DataFrame.from_records(rows)


def confusion_metrics(y_true, y_prob, threshold: float = 0.5) -> dict:
    """Confusion matrix at ``threshold`` plus the standard rates.

    Keys: tp, tn, fp, fn, sensitivity (recall), specificity, precision
    (PPV), npv, f1. Rates are NaN when their denominator is 0.
    """
    y, p = _as_arrays(y_true, y_prob)
    pred = (p >= threshold).astype(int)
    tp = np.sum((pred == 1) & (y == 1)).item()
    tn = np.sum((pred == 0) & (y == 0)).item()
    fp = np.sum((pred == 1) & (y == 0)).item()
    fn = np.sum((pred == 0) & (y == 1)).item()

    def _rate(num: int, den: int) -> float:
        return float(num / den) if den else float("nan")

    sensitivity = _rate(tp, tp + fn)
    specificity = _rate(tn, tn + fp)
    precision = _rate(tp, tp + fp)
    npv = _rate(tn, tn + fn)
    f1 = (
        float(2 * precision * sensitivity / (precision + sensitivity))
        if precision + sensitivity > 0
        else float("nan")
    )
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "npv": npv,
        "f1": f1,
    }
