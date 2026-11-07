"""Tests for Day 2 — Crypto Risk & Volatility Analyzer. Offline, no network."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import data_pipeline
from data_pipeline import (
    build_correlations,
    clean_chart,
    compute_daily,
    generate_synthetic,
)
from risk_metrics import (
    daily_returns,
    drawdown_series,
    max_drawdown_info,
    return_correlations,
    rolling_volatility,
    sharpe_ratio,
    sortino_ratio,
    var_cvar_95,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COINS = ("bitcoin", "ethereum", "solana")


def _raw(prices, caps=None, vols=None, start="2025-11-06"):
    n = len(prices)
    caps = caps if caps is not None else [1_000_000.0] * n
    vols = vols if vols is not None else [10_000.0] * n
    base = pd.Timestamp(start, tz="UTC").value // 10**6
    ts = [base + i * 86_400_000 for i in range(n)]
    return {
        "prices": [[t, p] for t, p in zip(ts, prices)],
        "market_caps": [[t, c] for t, c in zip(ts, caps)],
        "total_volumes": [[t, v] for t, v in zip(ts, vols)],
    }


def _dates(n, start="2025-11-06"):
    return pd.Series(pd.date_range(start, periods=n, freq="D").strftime("%Y-%m-%d"))


# --- 1. Drawdown formula on a hand-computed series ---------------------------
def test_drawdown_series_hand_computed():
    prices = pd.Series([100.0, 110.0, 105.0, 90.0, 95.0, 110.0])
    dd = drawdown_series(prices)
    # Running max: 100, 110, 110, 110, 110, 110
    expected = pd.Series([0.0, 0.0, 105 / 110 - 1, 90 / 110 - 1, 95 / 110 - 1, 0.0])
    pd.testing.assert_series_equal(dd, expected)


def test_max_drawdown_info_peak_trough_duration():
    prices = pd.Series([100.0, 110.0, 105.0, 90.0, 95.0, 110.0])
    info = max_drawdown_info(prices, _dates(6))
    assert info["max_drawdown"] == pytest.approx(90 / 110 - 1)
    assert info["peak_date"] == "2025-11-07"  # price 110
    assert info["peak_price"] == pytest.approx(110.0)
    assert info["trough_date"] == "2025-11-09"  # price 90
    assert info["trough_price"] == pytest.approx(90.0)
    assert info["peak_to_trough_days"] == 2
    # Recovers to >= 110 on 2025-11-11, i.e. 2 days after the trough.
    assert info["recovered_by_end"] is True
    assert info["recovery_days"] == 2
    # Underwater from 2025-11-08 to 2025-11-10: 3 consecutive days.
    assert info["longest_underwater_days"] == 3


def test_max_drawdown_info_not_recovered():
    prices = pd.Series([100.0, 120.0, 100.0, 80.0, 90.0])
    info = max_drawdown_info(prices, _dates(5))
    assert info["max_drawdown"] == pytest.approx(80 / 120 - 1)
    assert info["recovered_by_end"] is False
    # Trough 2025-11-09, window ends 2025-11-10: 1 day elapsed.
    assert info["recovery_days"] == 1


# --- 2. Rolling volatility ----------------------------------------------------
def test_rolling_volatility_annualisation_and_nans():
    returns = pd.Series([0.01, -0.02, 0.005, 0.03, -0.01] * 12)
    vol = rolling_volatility(returns, window=30)
    assert vol.iloc[:29].isna().all()  # first 29 are NaN
    assert vol.iloc[29:].notna().all()
    # Hand check: std of the first 30 returns, ddof=1, x sqrt(365).
    expected = returns.iloc[:30].std(ddof=1) * np.sqrt(365)
    assert vol.iloc[29] == pytest.approx(expected)
    # Annualisation uses sqrt(365), not sqrt(252).
    assert vol.iloc[29] == pytest.approx(
        returns.iloc[:30].std(ddof=1) * np.sqrt(365), rel=1e-12
    )
    assert vol.iloc[29] != pytest.approx(
        returns.iloc[:30].std(ddof=1) * np.sqrt(252), rel=1e-6
    )


def test_daily_returns_simple_not_log():
    prices = pd.Series([100.0, 110.0, 99.0])
    rets = daily_returns(prices)
    assert pd.isna(rets.iloc[0])
    assert rets.iloc[1] == pytest.approx(0.10)
    assert rets.iloc[2] == pytest.approx(99 / 110 - 1)


# --- 3. Sharpe / Sortino on a known series ------------------------------------
def test_sharpe_sortino_known_series():
    returns = pd.Series([0.02, -0.01, 0.03, -0.02, 0.01, 0.00, 0.02, -0.01])
    assert sharpe_ratio(returns) == pytest.approx(
        returns.mean() / returns.std(ddof=1) * np.sqrt(365)
    )
    downside = np.sqrt(np.mean(np.minimum(returns.to_numpy(), 0.0) ** 2))
    assert sortino_ratio(returns) == pytest.approx(
        returns.mean() / downside * np.sqrt(365)
    )
    # Sortino penalises only downside moves, so it exceeds Sharpe here.
    assert sortino_ratio(returns) > sharpe_ratio(returns)


# --- 4. VaR / CVaR --------------------------------------------------------------
def test_var_cvar_95():
    returns = pd.Series(np.linspace(-0.10, 0.10, 101))
    result = var_cvar_95(returns)
    assert result["var_95"] == pytest.approx(np.percentile(returns, 5))
    tail = returns[returns <= result["var_95"]]
    assert result["cvar_95"] == pytest.approx(tail.mean())
    assert result["cvar_95"] <= result["var_95"]


# --- 5. Correlations on constructed series --------------------------------------
def test_return_correlations_perfect_and_known():
    idx = pd.date_range("2025-11-06", periods=120, freq="D")
    a = pd.Series(np.linspace(-0.05, 0.05, 120), index=idx)
    b = a * 2  # perfectly correlated with a
    c = -a  # perfectly anti-correlated with a
    df = pd.DataFrame({"bitcoin": a, "ethereum": b, "solana": c})
    result = return_correlations(df)
    assert result["full"].loc["bitcoin", "ethereum"] == pytest.approx(1.0)
    assert result["full"].loc["bitcoin", "solana"] == pytest.approx(-1.0)
    assert result["full"].loc["ethereum", "solana"] == pytest.approx(-1.0)
    # Latest-90d window agrees on these constructed series.
    assert result["latest_90d"]["bitcoin-ethereum"] == pytest.approx(1.0)
    assert result["latest_90d"]["bitcoin-solana"] == pytest.approx(-1.0)
    assert result["latest_90d"]["ethereum-solana"] == pytest.approx(-1.0)


def test_build_correlations_matches_recompute():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    corr = build_correlations(daily)
    assert set(corr["pair"]) == {
        "bitcoin-ethereum",
        "bitcoin-solana",
        "ethereum-solana",
    }
    committed = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "crypto_correlations.csv"
    )
    pd.testing.assert_frame_equal(corr, committed)


# --- 6. Synthetic fallback -------------------------------------------------------
def test_generate_synthetic_deterministic_365_points():
    first = generate_synthetic(seed=42)
    second = generate_synthetic(seed=42)
    assert first == second  # deterministic
    for coin in COINS:
        assert len(first[coin]["prices"]) == 365
        first_ts = first[coin]["prices"][0][0]
        assert (
            pd.Timestamp(first_ts, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            == "2025-11-06"
        )
        assert first[coin]["prices"][0][1] == pytest.approx(
            {"bitcoin": 100_000.0, "ethereum": 3_500.0, "solana": 180.0}[coin]
        )


# --- 7. Synthetic never overwrites the live cache --------------------------------
def test_synthetic_does_not_satisfy_cache_check(tmp_path, monkeypatch):
    monkeypatch.setattr(data_pipeline, "RAW_DIR", tmp_path)
    (tmp_path / "bitcoin_market_chart_synthetic.json").write_text("{}")
    assert data_pipeline._load_cache() is None


def test_save_outputs_synthetic_keeps_live_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data_pipeline, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(data_pipeline, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(data_pipeline, "DATA_SOURCE", "synthetic")
    live = tmp_path / "raw" / "bitcoin_market_chart.json"
    live.parent.mkdir(parents=True)
    live.write_text('{"sentinel": true}')
    raw = {"bitcoin": {"prices": [[1762387200000, 100.0]]}}
    daily = pd.DataFrame(
        {
            "date": ["2025-11-06"],
            "coin": ["bitcoin"],
            "price": [100.0],
            "market_cap": [1.0],
            "volume": [1.0],
            "daily_return": [np.nan],
            "drawdown": [0.0],
            "vol_30d_ann": [np.nan],
        }
    )
    summary = pd.DataFrame({"coin": ["bitcoin"]})
    correlations = pd.DataFrame({"pair": ["bitcoin-ethereum"]})
    data_pipeline.save_outputs(daily, summary, correlations, raw)
    assert live.read_text() == '{"sentinel": true}'  # untouched
    assert (tmp_path / "raw" / "bitcoin_market_chart_synthetic.json").exists()
    source = json.loads((tmp_path / "processed" / "data_source.json").read_text())
    assert source["synthetic"] is True
    assert source["seed"] == 42


# --- 8. Offline mode ---------------------------------------------------------------
def test_offline_mode_runs_without_network(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    raw_dir.mkdir()
    for coin in COINS:
        src = PROJECT_ROOT / "data" / "raw" / f"{coin}_market_chart.json"
        (raw_dir / f"{coin}_market_chart.json").write_text(src.read_text())
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw_dir)
    monkeypatch.setattr(data_pipeline, "PROCESSED_DIR", proc_dir)
    monkeypatch.setattr(sys, "argv", ["data_pipeline.py", "--offline"])
    data_pipeline.main()
    daily = pd.read_csv(proc_dir / "crypto_daily.csv")
    assert len(daily) == 1098
    source = json.loads((proc_dir / "data_source.json").read_text())
    assert source["source"] == "cache"
    assert source["synthetic"] is False
    assert source["seed"] is None


# --- 9. Committed CSVs match the published findings --------------------------------
def test_committed_daily_recomputes_btc_max_drawdown():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    summary = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "crypto_risk_summary.csv"
    )
    btc = daily[daily["coin"] == "bitcoin"].sort_values("date").reset_index(drop=True)
    assert len(btc) == 366
    assert btc["date"].min() == "2025-11-06"
    assert btc["date"].max() == "2026-11-06"
    # Hand recompute from the CSV: peak price/date -> trough price/date.
    peak_price = btc["price"].max()
    peak_idx = int(btc["price"].idxmax())
    trough = btc.iloc[peak_idx:]
    trough_idx = int(trough["price"].idxmin())
    recomputed = btc["price"].iloc[trough_idx] / peak_price - 1
    published = summary[summary["coin"] == "bitcoin"]["max_drawdown"].iloc[0]
    assert recomputed == pytest.approx(published, abs=1e-9)
    # The drawdown column itself must agree with price / running max - 1.
    running_max = btc["price"].cummax()
    pd.testing.assert_series_equal(
        btc["drawdown"],
        btc["price"] / running_max - 1,
        check_names=False,
    )


def test_daily_frame_shape_and_nans():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    assert len(daily) == 1098
    assert list(daily.columns) == [
        "date",
        "coin",
        "price",
        "market_cap",
        "volume",
        "daily_return",
        "drawdown",
        "vol_30d_ann",
    ]
    for coin, g in daily.groupby("coin"):
        assert len(g) == 366
        assert g["daily_return"].isna().sum() == 1  # first row per coin
        assert g["vol_30d_ann"].isna().sum() == 30  # first 29 + first return NaN


def test_risk_summary_cvar_le_var():
    summary = pd.read_csv(
        PROJECT_ROOT / "data" / "processed" / "crypto_risk_summary.csv"
    )
    assert len(summary) == 3
    assert (summary["cvar_95"] <= summary["var_95"]).all()
    assert (summary["max_drawdown"] < 0).all()
    assert (summary["current_drawdown"] <= 0).all()


# --- 10. Notebook _find_root() ------------------------------------------------------
def _notebook_first_code_cell_source():
    nb = json.loads((PROJECT_ROOT / "notebooks" / "analysis.ipynb").read_text())
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            return "".join(cell["source"])
    raise AssertionError("no code cell in notebook")


def test_notebook_find_root_resolves():
    # Tell the exec'd cell where the notebook lives, as Jupyter/nbconvert
    # would: _find_root() resolves from the notebook's own location, so the
    # test must not depend on pytest's working directory (CI runs from the
    # repo root, not the day folder).
    namespace: dict = {"__file__": str(PROJECT_ROOT / "notebooks" / "analysis.ipynb")}
    exec(_notebook_first_code_cell_source(), namespace)  # noqa: S102
    assert namespace["_find_root"]() == PROJECT_ROOT


def test_notebook_find_root_fails_outside_project(tmp_path, monkeypatch):
    copy = tmp_path / "analysis.ipynb"
    copy.write_text((PROJECT_ROOT / "notebooks" / "analysis.ipynb").read_text())
    namespace: dict = {"__file__": str(copy)}
    monkeypatch.chdir(tmp_path)
    # The first code cell calls _find_root() at import time, so exec itself raises.
    with pytest.raises(FileNotFoundError):
        exec(_notebook_first_code_cell_source(), namespace)  # noqa: S102


# --- 11. Attribution ------------------------------------------------------------------
def test_powered_by_coingecko_attribution():
    app_src = (PROJECT_ROOT / "src" / "app.py").read_text()
    assert "Powered by CoinGecko" in app_src
    assert "coingecko.com" in app_src
    charts_src = (PROJECT_ROOT / "src" / "make_charts.py").read_text()
    assert "Powered by CoinGecko" in charts_src
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "Powered by CoinGecko" in readme
    assert "Educational analysis only" in app_src
    assert "not investment advice" in app_src.lower()


# --- 12. clean_chart --------------------------------------------------------------------
def test_clean_chart_merges_and_dedupes():
    raw = _raw([100.0, 110.0, 105.0])
    raw["prices"].append(raw["prices"][1])  # duplicate timestamp
    df = clean_chart(raw, "bitcoin")
    assert list(df.columns) == ["date", "coin", "price", "market_cap", "volume"]
    assert len(df) == 3
    assert df["date"].tolist() == ["2025-11-06", "2025-11-07", "2025-11-08"]
    assert df["price"].notna().all()


def test_compute_daily_adds_risk_columns():
    raw = _raw([100.0 + i for i in range(40)])
    daily = compute_daily(clean_chart(raw, "bitcoin"))
    assert list(daily.columns) == [
        "date",
        "coin",
        "price",
        "market_cap",
        "volume",
        "daily_return",
        "drawdown",
        "vol_30d_ann",
    ]
    assert daily["daily_return"].isna().sum() == 1
    assert daily["vol_30d_ann"].isna().sum() == 30
    assert (daily["drawdown"] <= 0).all()
