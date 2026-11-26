"""Day 19 tests for src/data_pipeline.py — constants, fingerprint rule,
and the committed processed tables.

No test here downloads the 144 MB raw file or trains a model: the
fingerprint constants are checked against the documented values, and
the processed tables (built by the coder's pipeline run) are checked
for existence, shape and internal consistency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import data_pipeline as dp

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


def test_fingerprint_constants_match_brief() -> None:
    """The frozen fingerprint is the published Kaggle fingerprint."""
    assert dp.EXPECTED_ROWS == 284_807
    assert dp.EXPECTED_FRAUD == 492
    assert dp.EXPECTED_BYTES == 150_828_752
    assert dp.EXPECTED_MD5 == "e90efcb83d69faf99fcab8b0255024de"
    assert dp.SEED == 42
    assert dp.TEST_SIZE == 0.30
    assert dp.THRESHOLDS == [round(0.05 * i, 2) for i in range(1, 20)]


def test_verify_fingerprint_rejects_wrong_file(tmp_path: Path) -> None:
    """A file with the wrong size is refused before any build."""
    bad = tmp_path / "creditcard.csv"
    bad.write_text("Time,V1,Class\n0,0.0,0\n")
    with pytest.raises(ValueError, match="raw size"):
        dp.verify_fingerprint(bad)


def test_all_processed_files_exist() -> None:
    """All 9 processed files the plan lists are present."""
    expected = {
        "data_source.json",
        "class_summary.csv",
        "amount_summary.csv",
        "amount_hist.csv",
        "model_metrics.csv",
        "confusion_matrix.csv",
        "threshold_sweep.csv",
        "cost_curve.csv",
        "pr_curves.csv",
    }
    present = {path.name for path in PROCESSED_DIR.iterdir()}
    assert expected <= present, f"missing: {expected - present}"


def test_data_source_is_real_not_synthetic() -> None:
    """data_source.json records real (not synthetic) data + the seed."""
    source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    assert source["synthetic"] is False
    assert source["seed"] == 42
    assert source["rows"] == 284_807
    assert source["fraud"] == 492
    assert source["fraud_rate_pct"] == pytest.approx(0.1727, abs=0.0001)
    assert source["md5"] == dp.EXPECTED_MD5
    assert source["test_rows"] == 85_443  # 30% of 284,807, stratified
    assert source["test_fraud"] == 148  # 30% of 492, stratified (147.6 -> 148)


def test_class_summary_matches_fingerprint() -> None:
    """Class summary: 284,315 legit + 492 fraud = 284,807 rows."""
    summary = pd.read_csv(PROCESSED_DIR / "class_summary.csv")
    assert int(summary["n_transactions"].sum()) == 284_807
    fraud_row = summary[summary["Class"] == 1].iloc[0]
    assert int(fraud_row["n_transactions"]) == 492
    assert float(fraud_row["share_pct"]) == pytest.approx(0.1727, abs=0.001)


def test_model_metrics_shape_and_ranges() -> None:
    """Three models, one row each; metrics in [0, 1]; RF beats LR on PR-AUC."""
    metrics = pd.read_csv(PROCESSED_DIR / "model_metrics.csv")
    assert list(metrics["model"]) == [
        "baseline_majority",
        "logistic_regression",
        "random_forest",
    ]
    for col in ("precision", "recall", "f1", "accuracy", "pr_auc", "roc_auc"):
        assert bool(((metrics[col] >= 0.0) & (metrics[col] <= 1.0)).all())
    baseline = metrics[metrics["model"] == "baseline_majority"].iloc[0]
    assert baseline["recall"] == 0.0  # predicts never-fraud
    assert baseline["accuracy"] == pytest.approx(0.9983, abs=0.001)
    rf = metrics[metrics["model"] == "random_forest"].iloc[0]
    lr = metrics[metrics["model"] == "logistic_regression"].iloc[0]
    assert rf["pr_auc"] > lr["pr_auc"]
    # The accuracy paradox, stated as a check: the baseline looks
    # excellent on accuracy (over 99.8%) while catching zero fraud.
    assert baseline["accuracy"] > 0.99


def test_threshold_sweep_consistent() -> None:
    """Sweep rows sum to the test size; cost columns are consistent."""
    sweep = pd.read_csv(PROCESSED_DIR / "threshold_sweep.csv")
    assert set(sweep["model"]) == {"random_forest", "logistic_regression"}
    assert len(sweep) == 2 * 19  # 19 thresholds x 2 models
    for _, row in sweep.iterrows():
        total = row["tp"] + row["fp"] + row["tn"] + row["fn"]
        assert total == 85_443
        assert row["total_cost_usd"] == pytest.approx(
            row["fp"] * 5.0 + row["missed_fraud_usd"]
        )
        assert row["cost_per_10k_txns_usd"] == pytest.approx(
            row["total_cost_usd"] / 85_443 * 10_000.0
        )


def test_cost_curve_is_best_model_minimum() -> None:
    """cost_curve.csv holds the best model's sweep; its minimum is recorded."""
    source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    cost = pd.read_csv(PROCESSED_DIR / "cost_curve.csv")
    assert set(cost["model"]) == {source["best_model"]}
    min_row = cost.loc[cost["cost_per_10k_txns_usd"].idxmin()]
    assert float(min_row["threshold"]) == pytest.approx(source["best_threshold"])
    assert float(min_row["cost_per_10k_txns_usd"]) == pytest.approx(
        source["best_threshold_cost_per_10k_usd"]
    )


def test_pr_curves_shape() -> None:
    """PR curve points exist for both scoring models, recall in [0, 1]."""
    curves = pd.read_csv(PROCESSED_DIR / "pr_curves.csv")
    assert set(curves["model"]) == {"logistic_regression", "random_forest"}
    assert bool(((curves["recall"] >= 0.0) & (curves["recall"] <= 1.0)).all())
    assert bool(((curves["precision"] >= 0.0) & (curves["precision"] <= 1.0)).all())
    for model in ("logistic_regression", "random_forest"):
        assert len(curves[curves["model"] == model]) > 50
