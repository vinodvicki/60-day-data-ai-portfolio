"""Smoke tests for src/data_pipeline.py — fast, offline, no network."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_pipeline import clean_chart, compute_metrics, generate_synthetic


def _raw(prices, caps=None, vols=None):
    n = len(prices)
    caps = caps if caps is not None else [1_000_000.0] * n
    vols = vols if vols is not None else [10_000.0] * n
    # Daily timestamps from 2025-11-05, milliseconds.
    base = pd.Timestamp("2025-11-05", tz="UTC").value // 10**6
    ts = [base + i * 86_400_000 for i in range(n)]
    return {
        "prices": [[t, p] for t, p in zip(ts, prices)],
        "market_caps": [[t, c] for t, c in zip(ts, caps)],
        "total_volumes": [[t, v] for t, v in zip(ts, vols)],
    }


def test_clean_chart_merges_and_dedupes():
    raw = _raw([100.0, 110.0, 105.0])
    raw["prices"].append(raw["prices"][1])  # duplicate timestamp
    df = clean_chart(raw, "bitcoin")
    assert list(df.columns) == ["date", "coin", "price", "market_cap", "volume"]
    assert len(df) == 3
    assert df["date"].tolist() == ["2025-11-05", "2025-11-06", "2025-11-07"]
    assert df["coin"].unique().tolist() == ["bitcoin"]
    assert df["price"].notna().all()


def test_clean_chart_rejects_nan_price():
    raw = _raw([100.0, None, 105.0])
    with pytest.raises(AssertionError):
        clean_chart(raw, "bitcoin")


def _metrics_frame():
    # 40 days: price rises 1% a day for 20 days, then falls 2% a day.
    prices = [100.0 * 1.01**i for i in range(20)]
    prices += [prices[-1] * 0.98**i for i in range(1, 21)]
    dates = pd.date_range("2025-11-05", periods=40, freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": list(dates) * 2,
            "coin": ["bitcoin"] * 40 + ["ethereum"] * 40,
            "price": prices + [p * 2 for p in prices],
            "market_cap": [1e9] * 80,
            "volume": [1e7] * 80,
        }
    )


def test_compute_metrics_daily_and_7d_return():
    out = compute_metrics(_metrics_frame())
    btc = out[out["coin"] == "bitcoin"].reset_index(drop=True)
    assert btc["daily_return"].iloc[1] == pytest.approx(0.01, abs=1e-9)
    # 7d return on day 8 (index 7): price_7 / price_0 - 1 = 1.01^7 - 1
    assert btc["return_7d"].iloc[7] == pytest.approx(1.01**7 - 1, abs=1e-9)
    assert btc["daily_return"].iloc[0] != btc["daily_return"].iloc[0]  # NaN first row


def test_compute_metrics_volatility_positive_and_annualised():
    out = compute_metrics(_metrics_frame())
    btc = out[out["coin"] == "bitcoin"]
    vol = btc["vol_30d_annualised"].dropna()
    assert (vol > 0).all()
    # Annualised vol = 30d std of daily returns * sqrt(365)
    raw_std = btc["daily_return"].iloc[1:31].std(ddof=1)
    assert btc["vol_30d_annualised"].iloc[30] == pytest.approx(
        raw_std * np.sqrt(365), rel=1e-6
    )


def test_compute_metrics_drawdown_sign_and_value():
    out = compute_metrics(_metrics_frame())
    btc = out[out["coin"] == "bitcoin"].reset_index(drop=True)
    assert (btc["drawdown"] <= 0).all()
    assert btc["drawdown"].iloc[19] == pytest.approx(0.0)  # at the peak
    peak = 100.0 * 1.01**19
    trough = peak * 0.98**20
    assert btc["drawdown"].min() == pytest.approx(trough / peak - 1, rel=1e-9)
    # Relative volume / turnover on flat volume & cap
    assert btc["relative_volume"].iloc[30] == pytest.approx(1.0)
    assert btc["turnover"].iloc[0] == pytest.approx(1e7 / 1e9)


def test_generate_synthetic_deterministic_and_365_rows():
    a = generate_synthetic(seed=42)
    b = generate_synthetic(seed=42)
    assert a == b
    for coin in ("bitcoin", "ethereum", "solana"):
        assert len(a[coin]["prices"]) == 365
        assert len(a[coin]["market_caps"]) == 365
        assert len(a[coin]["total_volumes"]) == 365
    # clean_chart works unchanged on synthetic data
    df = clean_chart(a["bitcoin"], "bitcoin")
    assert len(df) == 365
    assert df["date"].iloc[0] == "2025-11-05"
    assert df["price"].iloc[0] == pytest.approx(100_000.0)


def test_generate_synthetic_different_seed_differs():
    assert generate_synthetic(seed=42) != generate_synthetic(seed=7)
