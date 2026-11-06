"""Smoke tests for src/data_pipeline.py — fast, offline, no network."""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import data_pipeline
from data_pipeline import (
    btc_eth_correlation,
    clean_chart,
    compute_metrics,
    generate_synthetic,
    max_drawdown_info,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COINS = ("bitcoin", "ethereum", "solana")


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


def _raise_network(*args, **kwargs):
    raise AssertionError("network called")


def _copy_committed_raw(raw_dir: Path) -> None:
    src_raw = PROJECT_ROOT / "data" / "raw"
    for coin in COINS:
        shutil.copy(
            src_raw / f"{coin}_market_chart.json",
            raw_dir / f"{coin}_market_chart.json",
        )


def test_offline_uses_cache_without_network(tmp_path, monkeypatch):
    """--offline reads the committed cache, makes no network call."""
    monkeypatch.setattr(requests, "get", _raise_network)
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    raw_dir.mkdir()
    proc_dir.mkdir()
    _copy_committed_raw(raw_dir)
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw_dir)
    monkeypatch.setattr(data_pipeline, "PROCESSED_DIR", proc_dir)
    monkeypatch.setattr(sys, "argv", ["data_pipeline", "--offline"])
    data_pipeline.main()
    daily = pd.read_csv(proc_dir / "crypto_daily.csv", parse_dates=["date"])
    assert len(daily) == 1098
    assert daily.groupby("coin").size().tolist() == [366, 366, 366]
    source = json.loads((proc_dir / "data_source.json").read_text())
    assert source["source"] == "cache"
    assert source["synthetic"] is False
    assert source["seed"] is None


def test_synthetic_never_overwrites_live_cache(tmp_path, monkeypatch):
    """Synthetic output goes to *_synthetic.json; live cache untouched."""
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    raw_dir.mkdir()
    proc_dir.mkdir()
    live_bytes = {}
    live_mtime = {}
    for coin in COINS:
        path = raw_dir / f"{coin}_market_chart.json"
        path.write_text(json.dumps({"marker": coin}))
        live_bytes[coin] = path.read_bytes()
        live_mtime[coin] = path.stat().st_mtime_ns
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw_dir)
    monkeypatch.setattr(data_pipeline, "PROCESSED_DIR", proc_dir)
    monkeypatch.setattr(data_pipeline, "DATA_SOURCE", "synthetic")
    synth = generate_synthetic(seed=42)
    daily = pd.concat([clean_chart(synth[c], c) for c in COINS], ignore_index=True)
    metrics = compute_metrics(daily)
    data_pipeline.save_outputs(daily, metrics, synth)
    for coin in COINS:
        path = raw_dir / f"{coin}_market_chart.json"
        assert path.read_bytes() == live_bytes[coin]
        assert path.stat().st_mtime_ns == live_mtime[coin]
        assert (raw_dir / f"{coin}_market_chart_synthetic.json").exists()
    source = json.loads((proc_dir / "data_source.json").read_text())
    assert source["synthetic"] is True
    assert source["seed"] == 42


def test_synthetic_file_does_not_satisfy_cache(tmp_path, monkeypatch):
    """Only *_synthetic.json present: _load_cache() returns None."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for coin in COINS:
        (raw_dir / f"{coin}_market_chart_synthetic.json").write_text(
            json.dumps({"marker": coin})
        )
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw_dir)
    assert data_pipeline._load_cache() is None


def test_committed_csvs_match_published_findings():
    """Committed CSVs reproduce every published headline number."""
    proc_dir = PROJECT_ROOT / "data" / "processed"
    daily = pd.read_csv(proc_dir / "crypto_daily.csv", parse_dates=["date"])
    metrics = pd.read_csv(proc_dir / "crypto_metrics.csv", parse_dates=["date"])
    assert len(daily) == 1098
    assert daily.groupby("coin").size().tolist() == [366, 366, 366]
    assert daily["date"].min() == pd.Timestamp("2025-11-05")
    assert daily["date"].max() == pd.Timestamp("2026-11-05")

    expected_return = {"bitcoin": -0.207, "ethereum": -0.262, "solana": -0.385}
    expected_vol = {"bitcoin": 0.415, "ethereum": 0.574, "solana": 0.597}
    expected_dd = {"bitcoin": -0.447, "ethereum": -0.562, "solana": -0.629}
    for coin, g in daily.groupby("coin"):
        total_return = g["price"].iloc[-1] / g["price"].iloc[0] - 1
        assert total_return == pytest.approx(expected_return[coin], abs=0.001)
    for coin, g in metrics.groupby("coin"):
        assert g["vol_30d_annualised"].mean() == pytest.approx(
            expected_vol[coin], abs=0.001
        )
        assert g["drawdown"].min() == pytest.approx(expected_dd[coin], abs=0.001)

    corr = btc_eth_correlation(metrics)
    assert corr["full"] == pytest.approx(0.906, abs=0.002)
    assert corr["latest_90d"] == pytest.approx(0.890, abs=0.002)

    # max_drawdown_info stringifies dates, so feed it YYYY-MM-DD strings
    # (as clean_chart produces) rather than parsed Timestamps.
    daily_str = daily.copy()
    daily_str["date"] = daily_str["date"].dt.strftime("%Y-%m-%d")
    btc = max_drawdown_info(daily_str)["bitcoin"]
    assert btc["max_drawdown"] == pytest.approx(-0.447237, abs=0.000001)
    assert btc["peak_date"] == "2025-11-11"
    assert btc["peak_price"] == pytest.approx(105951.50, abs=0.01)
    assert btc["trough_date"] == "2026-07-01"
    assert btc["trough_price"] == pytest.approx(58566.09, abs=0.01)


def test_make_charts_imports_offline():
    """make_charts imports with no network; committed data is not synthetic."""
    import make_charts

    assert make_charts._synthetic() is False


def test_app_and_charts_attribution():
    """Attribution is 'Powered by CoinGecko', never 'Source: CoinGecko'."""
    src_dir = PROJECT_ROOT / "src"
    for name in ("app.py", "make_charts.py"):
        text = (src_dir / name).read_text()
        assert "Powered by CoinGecko" in text
        assert "Data source: CoinGecko" not in text
        assert "Source: CoinGecko" not in text


def test_notebook_root_resolution():
    """Notebook resolves its root from its own location, not cwd alone."""
    nb = json.loads((PROJECT_ROOT / "notebooks" / "analysis.ipynb").read_text())
    first_code = next(c for c in nb["cells"] if c["cell_type"] == "code")
    source = "".join(first_code["source"])
    assert "_find_root" in source
    assert "Path.cwd().parent if (Path.cwd() / 'src').exists()" not in source
