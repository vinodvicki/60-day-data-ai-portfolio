"""Day 19 Credit Card Fraud Detection: pure analysis functions.

No I/O and no model training here — every function takes arrays (or a
small DataFrame) and returns numbers, so the tests can exercise them on
a seeded fixture without touching the 144 MB raw file.

Metric definitions (research_brief.md §2, frozen):
- precision = TP / (TP + FP); recall = TP / (TP + FN); F1 harmonic mean.
- PR-AUC (average precision) is the headline ranking metric for this
  0.17%-fraud problem; ROC-AUC is reported but never the headline.
- Cost model: a missed fraud costs its transaction Amount; a false
  alarm costs REVIEW_COST_USD ($5.00, an assumption, not a measured
  figure); true positives / true negatives cost $0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

REVIEW_COST_USD = 5.0


def confusion_at_threshold(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float
) -> dict[str, int]:
    """Confusion counts at one decision threshold on predicted scores."""
    pred = (y_score >= threshold).astype(int)
    true = y_true.astype(int)
    tp = int(np.sum((pred == 1) & (true == 1)))
    fp = int(np.sum((pred == 1) & (true == 0)))
    tn = int(np.sum((pred == 0) & (true == 0)))
    fn = int(np.sum((pred == 0) & (true == 1)))
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def metrics_at_threshold(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float
) -> dict[str, float]:
    """Precision, recall, F1 and accuracy at one threshold.

    Precision/recall are 0.0 (not NaN) when their denominator is 0.
    """
    conf = confusion_at_threshold(y_true, y_score, threshold)
    tp = conf["tp"]
    fp = conf["fp"]
    fn = conf["fn"]
    tn = conf["tn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "accuracy": float(accuracy),
    }


def expected_cost(
    false_positives: int,
    missed_fraud_amount_usd: float,
    review_cost_usd: float = REVIEW_COST_USD,
) -> float:
    """Total operational cost in dollars: review cost + lost fraud money."""
    return float(false_positives) * float(review_cost_usd) + float(
        missed_fraud_amount_usd
    )


def threshold_sweep(
    y_true: np.ndarray,
    y_score: np.ndarray,
    amounts: np.ndarray,
    thresholds: list[float],
    review_cost_usd: float = REVIEW_COST_USD,
) -> pd.DataFrame:
    """One row per threshold: confusion, precision/recall/F1, cost.

    Cost is also normalised per 10,000 transactions so thresholds can be
    compared independent of test-set size.
    """
    n = len(y_true)
    rows: list[dict[str, float]] = []
    for threshold in thresholds:
        conf = confusion_at_threshold(y_true, y_score, threshold)
        metrics = metrics_at_threshold(y_true, y_score, threshold)
        pred = (y_score >= threshold).astype(int)
        missed = float(np.sum(amounts[(pred == 0) & (y_true.astype(int) == 1)]))
        total_cost = expected_cost(conf["fp"], missed, review_cost_usd)
        rows.append(
            {
                "threshold": float(threshold),
                "tp": float(conf["tp"]),
                "fp": float(conf["fp"]),
                "tn": float(conf["tn"]),
                "fn": float(conf["fn"]),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "missed_fraud_usd": missed,
                "review_cost_usd": float(conf["fp"]) * float(review_cost_usd),
                "total_cost_usd": total_cost,
                "cost_per_10k_txns_usd": total_cost / n * 10_000.0 if n > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def ranking_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
    """PR-AUC (headline) and ROC-AUC for one model's test scores."""
    pr_auc = float(average_precision_score(y_true, y_score))
    roc_auc = float(roc_auc_score(y_true, y_score))
    return {"pr_auc": pr_auc, "roc_auc": roc_auc}


def summarise_classes(df: pd.DataFrame) -> pd.DataFrame:
    """One row per class: count, share, total and mean Amount."""
    summary = (
        df.groupby("Class")
        .agg(
            n_transactions=("Class", "size"),
            total_amount_usd=("Amount", "sum"),
            mean_amount_usd=("Amount", "mean"),
            median_amount_usd=("Amount", "median"),
        )
        .reset_index()
    )
    summary["share_pct"] = summary["n_transactions"] / len(df) * 100.0
    return summary[
        [
            "Class",
            "n_transactions",
            "share_pct",
            "total_amount_usd",
            "mean_amount_usd",
            "median_amount_usd",
        ]
    ]


def summarise_amounts(df: pd.DataFrame) -> pd.DataFrame:
    """Amount distribution by class: quantiles plus min/max."""
    rows: list[dict[str, float]] = []
    for cls in (0, 1):
        amounts = df.loc[df["Class"] == cls, "Amount"].to_numpy(dtype=float)
        rows.append(
            {
                "Class": float(cls),
                "min_usd": float(np.min(amounts)),
                "p25_usd": float(np.percentile(amounts, 25)),
                "median_usd": float(np.median(amounts)),
                "p75_usd": float(np.percentile(amounts, 75)),
                "p99_usd": float(np.percentile(amounts, 99)),
                "max_usd": float(np.max(amounts)),
            }
        )
    return pd.DataFrame(rows)
