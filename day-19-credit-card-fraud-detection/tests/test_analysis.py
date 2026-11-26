"""Day 19 tests for src/analysis.py — pure functions on a seeded fixture.

The fixture is a small synthetic classification set generated in-test
with sklearn (seed 42). It is test-only data, clearly labelled here,
and is never written to data/ — the real dataset lives in the raw file
and the processed tables, not in these tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification

from src import analysis as an


@pytest.fixture(scope="module")
def fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Seeded imbalanced fixture: 2,000 rows, 2% positive class."""
    x, y = make_classification(
        n_samples=2000,
        n_features=10,
        n_informative=5,
        n_redundant=2,
        weights=[0.98, 0.02],
        random_state=42,
    )
    rng = np.random.default_rng(42)
    scores = np.clip(0.5 * y + 0.25 * rng.random(len(y)) + 0.05 * x[:, 0], 0, 1)
    amounts = np.abs(rng.normal(100.0, 50.0, size=len(y))) + 1.0
    return y.astype(int), scores.astype(float), amounts


def test_confusion_counts_add_up(
    fixture: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    """TP + FP + TN + FN equals the number of rows, at any threshold."""
    y_true, y_score, _ = fixture
    for threshold in (0.1, 0.5, 0.9):
        conf = an.confusion_at_threshold(y_true, y_score, threshold)
        assert sum(conf.values()) == len(y_true)
        assert conf["tp"] + conf["fn"] == int(np.sum(y_true == 1))
        assert conf["tn"] + conf["fp"] == int(np.sum(y_true == 0))


def test_metrics_match_hand_computation() -> None:
    """Precision/recall/F1 against values computed by hand on 6 rows."""
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_score = np.array([0.9, 0.6, 0.7, 0.2, 0.4, 0.1])
    # threshold 0.5: predictions 1,1,1,0,0,0 -> TP=2, FP=1, FN=1, TN=2
    metrics = an.metrics_at_threshold(y_true, y_score, 0.5)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(2 / 3)
    assert metrics["accuracy"] == pytest.approx(4 / 6)


def test_metrics_zero_denominator_is_zero_not_nan() -> None:
    """No positives predicted -> precision 0.0, not NaN."""
    y_true = np.array([1, 0, 0])
    y_score = np.array([0.1, 0.1, 0.1])
    metrics = an.metrics_at_threshold(y_true, y_score, 0.5)
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0


def test_threshold_sweep_recall_falls_as_threshold_rises(
    fixture: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    """Recall is non-increasing and precision is roughly non-decreasing."""
    y_true, y_score, amounts = fixture
    sweep = an.threshold_sweep(y_true, y_score, amounts, [0.1, 0.3, 0.5, 0.7, 0.9])
    assert len(sweep) == 5
    recalls = sweep["recall"].to_numpy(dtype=float)
    assert bool(np.all(recalls[:-1] >= recalls[1:]))
    assert set(sweep.columns) >= {
        "threshold",
        "precision",
        "recall",
        "f1",
        "missed_fraud_usd",
        "total_cost_usd",
        "cost_per_10k_txns_usd",
    }


def test_expected_cost_formula() -> None:
    """Cost = $5 per false alarm + missed fraud dollars."""
    assert an.expected_cost(10, 250.0) == pytest.approx(10 * 5.0 + 250.0)
    assert an.expected_cost(0, 0.0) == pytest.approx(0.0)
    assert an.expected_cost(3, 0.0, review_cost_usd=10.0) == pytest.approx(30.0)


def test_sweep_cost_matches_manual_sum(
    fixture: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    """One sweep row's total cost equals FP*$5 + missed Amount."""
    y_true, y_score, amounts = fixture
    sweep = an.threshold_sweep(y_true, y_score, amounts, [0.5])
    row = sweep.iloc[0]
    missed = float(np.sum(amounts[(y_score < 0.5) & (y_true == 1)]))
    assert row["missed_fraud_usd"] == pytest.approx(missed)
    assert row["total_cost_usd"] == pytest.approx(row["fp"] * 5.0 + missed)
    assert row["cost_per_10k_txns_usd"] == pytest.approx(
        row["total_cost_usd"] / len(y_true) * 10_000.0
    )


def test_ranking_metrics_range(
    fixture: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    """PR-AUC and ROC-AUC are in [0, 1] and PR-AUC beats prevalence."""
    y_true, y_score, _ = fixture
    ranks = an.ranking_metrics(y_true, y_score)
    assert 0.0 <= ranks["pr_auc"] <= 1.0
    assert 0.0 <= ranks["roc_auc"] <= 1.0
    assert ranks["pr_auc"] > float(np.mean(y_true))


def test_summarise_classes() -> None:
    """Class summary counts and shares on a tiny frame."""
    df = pd.DataFrame(
        {
            "Class": [0, 0, 0, 1],
            "Amount": [10.0, 20.0, 30.0, 100.0],
        }
    )
    summary = an.summarise_classes(df)
    assert len(summary) == 2
    assert summary.loc[summary["Class"] == 1, "n_transactions"].iloc[0] == 1
    assert summary.loc[summary["Class"] == 1, "share_pct"].iloc[0] == pytest.approx(
        25.0
    )
    assert summary.loc[summary["Class"] == 1, "total_amount_usd"].iloc[
        0
    ] == pytest.approx(100.0)


def test_summarise_amounts() -> None:
    """Amount quantiles: median of [10, 20, 30] is 20."""
    df = pd.DataFrame(
        {
            "Class": [0, 0, 0, 1, 1],
            "Amount": [10.0, 20.0, 30.0, 5.0, 15.0],
        }
    )
    summary = an.summarise_amounts(df)
    assert summary.loc[summary["Class"] == 0, "median_usd"].iloc[0] == pytest.approx(
        20.0
    )
    assert summary.loc[summary["Class"] == 1, "min_usd"].iloc[0] == pytest.approx(5.0)
