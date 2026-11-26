"""Day 19 extra pipeline tests — feature building, model training, CLI.

Trains on a small seeded fixture (test-only synthetic data, never
written to data/) so the suite stays fast; the full-data run is the
coder's pipeline run, verified by test_pipeline.py's table checks.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import data_pipeline as dp


@pytest.fixture(scope="module")
def small_frame() -> pd.DataFrame:
    """Seeded 1,000-row frame with the real schema (V1–V28, Time, Amount, Class)."""
    rng = np.random.default_rng(42)
    n = 1000
    data = {f"V{i}": rng.normal(size=n) for i in range(1, 29)}
    data["Time"] = rng.uniform(0, 172_792, size=n)
    data["Amount"] = np.abs(rng.normal(90.0, 60.0, size=n)) + 0.01
    data["Class"] = (rng.random(n) < 0.05).astype(int)
    return pd.DataFrame(data)


def test_build_features_scales_nothing_yet(small_frame: pd.DataFrame) -> None:
    """build_features returns the 30 feature columns + the target."""
    features, target = dp.build_features(small_frame)
    assert list(features.columns) == dp.FEATURES
    assert len(features) == len(small_frame)
    assert int(target.sum()) == int(small_frame["Class"].sum())


def test_train_models_returns_three_fitted_models(
    small_frame: pd.DataFrame,
) -> None:
    """All three frozen models train and predict on the fixture."""
    features, target = dp.build_features(small_frame)
    models = dp.train_models(features, target)
    assert set(models) == {
        "baseline_majority",
        "logistic_regression",
        "random_forest",
    }
    for model in models.values():
        preds = model.predict(features)
        assert len(preds) == len(small_frame)
        assert set(np.unique(preds)) <= {0, 1}


def test_md5_of_known_content(tmp_path: Path) -> None:
    """md5_of matches hashlib on a known file."""
    path = tmp_path / "x.txt"
    path.write_bytes(b"hello")
    assert dp.md5_of(path) == hashlib.md5(b"hello").hexdigest()


def test_main_offline_without_cache_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--offline with no cached raw file fails cleanly (exit 1, no crash)."""
    monkeypatch.setattr(dp, "RAW_PATH", tmp_path / "missing.csv")
    assert dp.main(["--offline"]) == 1


def test_verify_fingerprint_rejects_wrong_md5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file of the expected size but wrong content is refused on md5."""
    monkeypatch.setattr(dp, "EXPECTED_BYTES", 5)
    bad = tmp_path / "creditcard.csv"
    bad.write_bytes(b"xxxxx")
    with pytest.raises(ValueError, match="md5"):
        dp.verify_fingerprint(bad)
