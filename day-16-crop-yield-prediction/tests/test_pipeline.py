"""Day 16 Crop Yield Prediction: pipeline / model / chart contract tests.

All tests run offline from the committed raw files. No network is used.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import data_pipeline as dp
import model as md

PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
CHARTS = ROOT / "outputs" / "charts"


def test_yield_2024_value() -> None:
    """Hand-validation anchor: 2024 USA maize yield is 11.253324 t/ha."""
    df = pd.read_csv(PROCESSED / "yield_weather.csv")
    value = float(df.loc[df["year"] == 2024, "yield_t_per_ha"].iloc[0])
    assert value == pytest.approx(11.253324, abs=1e-6)
    bu = float(df.loc[df["year"] == 2024, "yield_bu_per_acre"].iloc[0])
    assert bu == pytest.approx(11.253324 * 39.368 / 2.47105, abs=1e-3)


def test_split_counts() -> None:
    df = pd.read_csv(PROCESSED / "yield_weather.csv")
    assert len(df) == 26
    assert int((df["split"] == "train").sum()) == 20
    assert int((df["split"] == "heldout").sum()) == 6
    assert set(df.loc[df["split"] == "train", "year"]) == set(range(2000, 2020))
    assert set(df.loc[df["split"] == "heldout", "year"]) == set(range(2020, 2026))


def test_offline_reproduces_processed() -> None:
    """--offline replay reproduces yield_weather.csv exactly."""
    before = (PROCESSED / "yield_weather.csv").read_bytes()
    dp.run("offline")
    after = (PROCESSED / "yield_weather.csv").read_bytes()
    assert before == after


def test_clean_yields_rejects_bad_rows() -> None:
    raw = (RAW / "maize_yields_owid.csv").read_text(encoding="utf-8")
    blanked = raw.replace("United States,USA,2024,11.253324", "United States,USA,2024,")
    assert blanked != raw
    with pytest.raises(ValueError, match="missing yield"):
        dp.clean_yields(blanked)


def test_build_features_toy_frame() -> None:
    """Feature definitions on a fixed toy daily frame (one year, 2000)."""
    days = pd.date_range("2000-01-01", "2000-12-31", freq="D")
    n = len(days)
    daily = {
        "time": [d.strftime("%Y-%m-%d") for d in days],
        "temperature_2m_mean": [20.0] * n,
        "temperature_2m_max": [31.0 if d.month in (6, 7, 8) else 25.0 for d in days],
        "precipitation_sum": [
            2.0 if d.month in (4, 5, 6, 7, 8, 9) else 0.0 for d in days
        ],
    }
    features = dp.build_features(daily)
    assert len(features) == 1
    row = features.iloc[0]
    assert row["year"] == 2000
    assert row["gs_temp_mean"] == pytest.approx(20.0)
    # Apr–Sep = 183 days × 2 mm
    assert row["gs_precip_total"] == pytest.approx(366.0)
    assert row["jul_temp_mean"] == pytest.approx(20.0)
    assert row["jul_precip_total"] == pytest.approx(62.0)
    assert row["jun_precip_total"] == pytest.approx(60.0)
    # Jun+Jul+Aug days with max > 30 °C: 30 + 31 + 31 = 92
    assert row["heat_days_gs"] == 92


def test_build_features_rejects_negative_precip() -> None:
    days = pd.date_range("2000-01-01", "2000-12-31", freq="D")
    daily = {
        "time": [d.strftime("%Y-%m-%d") for d in days],
        "temperature_2m_mean": [20.0] * len(days),
        "temperature_2m_max": [25.0] * len(days),
        "precipitation_sum": [-1.0] * len(days),
    }
    with pytest.raises(ValueError, match="negative precipitation"):
        dp.build_features(daily)


def test_metrics_formulas() -> None:
    actual = pd.Series([10.0, 11.0, 12.0])
    predicted = np.array([10.5, 10.5, 12.5])
    out = md.compute_metrics(actual, predicted)
    assert out["rmse"] == pytest.approx(0.5)
    assert out["mae"] == pytest.approx(0.5)
    assert out["bias"] == pytest.approx((0.5 - 0.5 + 0.5) / 3)
    ss_res = float(((actual.to_numpy() - predicted) ** 2).sum())
    ss_tot = float(((actual.to_numpy() - actual.mean()) ** 2).sum())
    assert out["r2"] == pytest.approx(1 - ss_res / ss_tot)


def test_naive_last_is_previous_year_actual() -> None:
    df = pd.read_csv(PROCESSED / "yield_weather.csv")
    train = df[df["split"] == "train"]
    heldout = df[df["split"] == "heldout"]
    base = md.baseline_predictions(train, heldout)
    assert float(base["naive_last"].iloc[0]) == pytest.approx(10.512726)  # 2019 actual
    assert float(base["naive_last"].iloc[1]) == pytest.approx(10.757499)  # 2020 actual
    assert float(base["naive_mean"].iloc[0]) == pytest.approx(
        float(train["yield_t_per_ha"].mean())
    )


def test_scaler_fit_on_train_only() -> None:
    """No leakage: the StandardScaler means equal the TRAIN feature means."""
    df = pd.read_csv(PROCESSED / "yield_weather.csv")
    train = df[df["split"] == "train"]
    models = md.train_models(train)
    scaler = models["scaler"]
    assert isinstance(scaler, object)
    from sklearn.preprocessing import StandardScaler

    assert isinstance(scaler, StandardScaler)
    expected = train[md.FEATURES].to_numpy(dtype=float).mean(axis=0)
    assert np.allclose(scaler.mean_, expected)


def test_model_determinism() -> None:
    """Same seed → same held-out RMSE on a second run."""
    _, _, _, winner1 = md.run()
    results = pd.read_csv(PROCESSED / "model_results.csv")
    rmse1 = float(
        results.loc[results["model"] == "RandomForest", "heldout_rmse_t_per_ha"].iloc[0]
    )
    _, _, _, winner2 = md.run()
    results2 = pd.read_csv(PROCESSED / "model_results.csv")
    rmse2 = float(
        results2.loc[results2["model"] == "RandomForest", "heldout_rmse_t_per_ha"].iloc[
            0
        ]
    )
    assert rmse1 == rmse2
    assert winner1 == winner2 == "Ridge"


def test_winner_rule_tie_goes_to_simpler() -> None:
    frame = pd.DataFrame(
        {
            "model": ["OLS", "Ridge", "RandomForest"],
            "heldout_rmse_t_per_ha": [0.540, 0.545, 0.600],
        }
    )
    assert md.pick_winner(frame) == "OLS"
    frame2 = pd.DataFrame(
        {
            "model": ["OLS", "Ridge", "RandomForest"],
            "heldout_rmse_t_per_ha": [0.700, 0.540, 0.545],
        }
    )
    assert md.pick_winner(frame2) == "Ridge"


def test_2012_drought_spot_check() -> None:
    """2012 growing-season rain (Iowa) is far below 2010 — the drought year."""
    raw = json.loads((RAW / "weather_iowa.json").read_text(encoding="utf-8"))
    features = dp.build_features(raw["daily"])
    p2010 = float(features.loc[features["year"] == 2010, "gs_precip_total"].iloc[0])
    p2012 = float(features.loc[features["year"] == 2012, "gs_precip_total"].iloc[0])
    assert p2012 < p2010
    assert p2012 < 500.0  # 423.6 mm observed
    assert p2010 > 1000.0  # 1041.9 mm observed


def test_charts_exist_and_are_png() -> None:
    expected = [
        "01_yield_history.png",
        "02_actual_vs_predicted.png",
        "03_feature_drivers.png",
        "04_weather_stations_map.png",
    ]
    for name in expected:
        path = CHARTS / name
        assert path.exists(), f"missing chart {name}"
        assert path.stat().st_size > 10_000, f"chart {name} suspiciously small"
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_data_size_rule() -> None:
    for path in RAW.iterdir():
        assert path.stat().st_size < 1_000_000, f"raw file too big: {path.name}"
    total = sum(p.stat().st_size for p in RAW.iterdir())
    assert total < 5_000_000
    processed_total = sum(
        p.stat().st_size for p in PROCESSED.iterdir() if p.suffix == ".csv"
    )
    assert processed_total < 1_000_000


def test_data_source_json() -> None:
    record = json.loads((PROCESSED / "data_source.json").read_text(encoding="utf-8"))
    assert record["synthetic"] is False
    assert record["row_counts"]["joined_rows"] == 26
    assert "ourworldindata.org" in record["sources"]["yields"]["url"]
    assert "open-meteo.com" in record["sources"]["weather"]["url"]


def test_no_forbidden_claims_in_docs() -> None:
    """No causal language, no 2026 forecast, no USDA-as-used-source claim."""
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    insights = " ".join(
        (ROOT / "outputs" / "insights_summary.md").read_text(encoding="utf-8").split()
    )
    for text, name in ((readme, "README"), (insights, "insights")):
        lowered = text.lower()
        assert "causes yield" not in lowered, name
        assert "predicts 2026" not in lowered, name
        assert "predict the 2026" not in lowered, name
    assert "USDA Quick Stats API needs a key" in readme or "needs an API key" in readme


def test_notebook_is_valid() -> None:
    import nbformat

    nb = nbformat.read(ROOT / "notebooks" / "analysis.ipynb", as_version=4)
    nbformat.validate(nb)
    assert len(nb.cells) >= 8
    sources = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    assert "_find_root" in sources


def test_gitignore_does_not_exclude_data() -> None:
    lines = [
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "data/raw/*_synthetic.json" in lines
    assert not any(
        line == "data/" or line.startswith("data/") and "*" not in line
        for line in lines
    )


def test_no_secrets_in_tree() -> None:
    # Published surfaces only: working notes (plan/brief) may legitimately
    # mention the words "secret" or "API key" as checklist items.
    forbidden = ("api_key", "API_KEY", "password", "secret")
    paths = list((ROOT / "src").rglob("*.py")) + [
        ROOT / "README.md",
        ROOT / "data" / "README.md",
        ROOT / "outputs" / "insights_summary.md",
    ]
    for path in paths:
        if ".venv" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in forbidden:
            assert word not in text, f"{word} in {path}"
