"""Tests for Day 3 — Crypto Market Anomaly Detector. Offline, no network."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import data_pipeline
from anomaly import (
    FEATURE_COLUMNS,
    apply_rules,
    build_timeline,
    compute_features,
    evaluate,
    fit_isolation_forest,
    generate_explanation,
    inject_anomalies,
    run_detection,
)
from data_pipeline import clean_chart, compute_daily, generate_synthetic

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COINS = ("bitcoin", "ethereum", "solana")


def _raw(prices, caps=None, vols=None, start="2025-11-07"):
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


def _daily_frame(prices, vols=None, coin="bitcoin", start="2025-11-07"):
    """A small clean daily frame (no features) for one coin."""
    n = len(prices)
    dates = pd.date_range(start, periods=n, freq="D").strftime("%Y-%m-%d")
    vols = vols if vols is not None else [10_000.0] * n
    return pd.DataFrame(
        {
            "date": dates,
            "coin": [coin] * n,
            "price": prices,
            "market_cap": [p * 19.8e6 for p in prices],
            "volume": vols,
        }
    )


def _featured(n=60, seed=0):
    """A featured frame with mildly noisy returns (no extreme moves)."""
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, size=n)))
    vols = 10_000.0 * np.exp(rng.normal(0, 0.1, size=n))
    return compute_features(_daily_frame(prices, vols=vols))


# --- 1. Trailing z-score on a hand-computed series ---------------------------
def test_trailing_z_score_excludes_today_and_warms_up():
    # 40 days of flat 1% returns, then one +10% day: the z-score on the
    # +10% day must use only the 30 flat days before it (mean 0.01,
    # std 0 -> z is inf/NaN), so use slightly noisy flat returns instead.
    rng = np.random.default_rng(7)
    base_rets = rng.normal(0.001, 0.01, size=40)
    prices = [100.0]
    for r in base_rets:
        prices.append(prices[-1] * (1 + r))
    prices = np.array(prices)
    # Append a +10% jump day.
    prices = np.append(prices, prices[-1] * 1.10)
    feat = compute_features(_daily_frame(prices))
    assert feat["return_z"].iloc[:31].isna().all()  # 30-day warm-up + first return NaN
    assert feat["return_z"].iloc[31:].notna().all()
    # Hand check on the jump day (index 41): trailing 30 returns are
    # base_rets[10:40] (the 30 daily returns before the jump, excluding today).
    prior = pd.Series(base_rets[10:40])
    jump_ret = feat["daily_return"].iloc[41]
    expected = (jump_ret - prior.mean()) / prior.std(ddof=1)
    assert feat["return_z"].iloc[41] == pytest.approx(expected, rel=1e-9)
    # No look-ahead: the z on day 35 must not use the jump day's return.
    prior35 = pd.Series(base_rets[4:34])
    expected35 = (feat["daily_return"].iloc[35] - prior35.mean()) / prior35.std(ddof=1)
    assert feat["return_z"].iloc[35] == pytest.approx(expected35, rel=1e-9)


def test_volume_ratio_excludes_today():
    vols = [10_000.0] * 40 + [40_000.0]
    prices = [100.0 * (1.001**i) for i in range(41)]
    feat = compute_features(_daily_frame(prices, vols=vols))
    # Day 40 volume is 4x the trailing 30-day mean of 10,000 (today excluded).
    assert feat["volume_ratio"].iloc[40] == pytest.approx(4.0)
    assert feat["volume_ratio"].iloc[:30].isna().all()
    assert feat["log_volume_ratio"].iloc[40] == pytest.approx(np.log(4.0))


# --- 2. Rules R1 / R2 / R3 ------------------------------------------------------
def test_rules_fire_only_at_threshold():
    feat = _featured()
    # Force a return shock: overwrite one post-warm-up day's return_z.
    feat = feat.copy()
    feat.loc[40, "return_z"] = 3.5
    feat.loc[40, "volume_z"] = 0.5
    feat.loc[41, "return_z"] = 2.9  # just below R1
    feat.loc[41, "volume_z"] = 0.5
    feat.loc[42, "return_z"] = 0.5
    feat.loc[42, "volume_z"] = 3.5
    feat.loc[42, "volume_ratio"] = 2.5  # R2 fires
    feat.loc[43, "return_z"] = 0.5
    feat.loc[43, "volume_z"] = 3.5
    feat.loc[43, "volume_ratio"] = 1.5  # R2 floor blocks it
    feat.loc[44, "return_z"] = 2.5
    feat.loc[44, "volume_z"] = 2.5  # R3 fires (both >= 2)
    feat.loc[45, "return_z"] = 2.5
    feat.loc[45, "volume_z"] = 1.5  # R3 does not fire
    out = apply_rules(feat)
    assert out.loc[40, "rules_triggered"] == "R1"
    assert out.loc[40, "baseline_flagged"]
    assert not out.loc[41, "baseline_flagged"]
    assert out.loc[42, "rules_triggered"] == "R2"
    assert not out.loc[43, "baseline_flagged"]  # volume_ratio < 2 blocks R2
    assert out.loc[44, "rules_triggered"] == "R3"
    assert not out.loc[45, "baseline_flagged"]


# --- 3. Severity tiers -----------------------------------------------------------
def test_severity_tiers():
    feat = _featured()
    feat = feat.copy()
    feat.loc[40, "return_z"] = 4.5  # R1 with |z| >= 4 -> High
    feat.loc[40, "volume_z"] = 0.0
    feat.loc[41, "return_z"] = 3.1  # R1 at threshold -> Medium
    feat.loc[41, "volume_z"] = 0.0
    feat.loc[42, "return_z"] = 3.5  # R1 + R2 together -> High
    feat.loc[42, "volume_z"] = 3.5
    feat.loc[42, "volume_ratio"] = 2.5
    feat.loc[43, "return_z"] = 2.5  # R3 only -> Low
    feat.loc[43, "volume_z"] = 2.5
    out = apply_rules(feat)
    assert out.loc[40, "severity"] == "High"
    assert out.loc[41, "severity"] == "Medium"
    assert out.loc[42, "severity"] == "High"
    assert out.loc[43, "severity"] == "Low"
    assert out.loc[44, "severity"] == ""  # unflagged


# --- 4. Isolation Forest determinism + 5 features --------------------------------
def test_isolation_forest_deterministic_and_five_features():
    assert len(FEATURE_COLUMNS) == 5
    feat = _featured(n=120)
    _m1, out1 = fit_isolation_forest(feat, contamination=0.05)
    _m2, out2 = fit_isolation_forest(feat, contamination=0.05)
    pd.testing.assert_series_equal(
        out1["isolation_forest_score"], out2["isolation_forest_score"]
    )
    assert (out1["is_anomaly"] == out2["is_anomaly"]).all()
    # Warm-up rows (missing features) are never scored.
    assert out1["isolation_forest_score"].iloc[:30].isna().all()
    assert not out1["is_anomaly"].iloc[:30].any()
    # Roughly the contamination share is flagged.
    assert 0.02 <= out1["is_anomaly"].mean() <= 0.10


def test_run_detection_contamination_is_baseline_rate():
    feat = _featured(n=120)
    feat = feat.copy()
    feat.loc[40, "return_z"] = 3.5  # force exactly one baseline flag
    _det, contamination = run_detection(feat)
    flaggable = feat["return_z"].notna()
    ruled = apply_rules(feat)
    expected = float(ruled.loc[flaggable, "baseline_flagged"].mean())
    assert contamination == pytest.approx(expected)
    # With no baseline flags at all, the fallback contamination is 0.03.
    _det2, contamination2 = run_detection(_featured(n=120))
    assert contamination2 == pytest.approx(0.03)


# --- 5. Injection harness ----------------------------------------------------------
def _noisy_daily_frame(seed=0):
    """A 366-day-per-coin frame with realistic noisy returns/volumes.

    Constant returns would give a zero trailing return std, so a
    trailing-σ plant could never clear its bar — the harness self-check
    would (correctly) fail. Realistic noise is required here.
    """
    rng = np.random.default_rng(seed)
    frames = []
    for coin in COINS:
        rets = rng.normal(0.001, 0.02, size=366)
        prices = 100.0 * np.exp(np.cumsum(rets))
        vols = 10_000.0 * np.exp(rng.normal(0, 0.3, size=366))
        frames.append(_daily_frame(prices, vols=vols, coin=coin))
    return pd.concat(frames, ignore_index=True)


def test_inject_anomalies_exact_spread_and_real_frame_unmodified():
    daily = _noisy_daily_frame(seed=0)
    original = daily.copy()
    injected, labels = inject_anomalies(daily, n=30, seed=42)
    pd.testing.assert_frame_equal(daily, original)  # input unmodified
    assert len(labels) == 30
    assert set(labels["type"]) == {"price_spike", "volume_surge", "joint_shock"}
    assert labels.groupby("type").size().to_dict() == {
        "price_spike": 10,
        "volume_surge": 10,
        "joint_shock": 10,
    }
    assert labels.groupby("coin").size().to_dict() == {c: 10 for c in COINS}
    assert set(labels["construction"]) == {
        "4.0x trailing return std",
        "5.0x trailing mean volume",
        "3.0x trailing return std + 5.0x trailing mean volume",
    }
    # Deterministic: same seed, same labels.
    _inj2, labels2 = inject_anomalies(daily, n=30, seed=42)
    pd.testing.assert_frame_equal(labels, labels2)
    # Spread across the year: no two injections for one coin in the same month.
    labels["month"] = labels["date"].str[:7]
    assert (labels.groupby(["coin", "month"]).size() <= 1).all()
    # New magnitudes (§4.4 amendment): each plant is built from the
    # trailing 30-day window ending the day before the injection, on the
    # injected frame — so the construction identities hold exactly.
    feat = compute_features(injected)
    for _, lab in labels.iterrows():
        g = feat[feat["coin"] == lab["coin"]].reset_index(drop=True)
        pos = int(g.index[g["date"] == lab["date"]][0])
        rets = g["daily_return"]
        sigma = rets.iloc[pos - 30 : pos].std(ddof=1)
        mean_vol = g["volume"].iloc[pos - 30 : pos].mean()
        if lab["type"] == "price_spike":
            assert lab["magnitude"] == pytest.approx(rets.iloc[pos], rel=1e-9)
            assert rets.iloc[pos] == pytest.approx(4.0 * sigma, rel=1e-9)
        elif lab["type"] == "volume_surge":
            assert lab["magnitude"] == pytest.approx(5.0)
            assert g["volume"].iloc[pos] == pytest.approx(5.0 * mean_vol, rel=1e-9)
        else:  # joint_shock
            assert lab["magnitude"] == pytest.approx(rets.iloc[pos], rel=1e-9)
            assert rets.iloc[pos] == pytest.approx(3.0 * sigma, rel=1e-9)
            assert g["volume"].iloc[pos] == pytest.approx(5.0 * mean_vol, rel=1e-9)
    # Harness self-check property: every plant clears its target rule's
    # bar on the injected frame (price |return_z| >= 3; volume
    # volume_z >= 3 and volume_ratio >= 2; joint both >= 2).
    for _, lab in labels.iterrows():
        row = feat[(feat["coin"] == lab["coin"]) & (feat["date"] == lab["date"])].iloc[
            0
        ]
        if lab["type"] == "price_spike":
            assert abs(row["return_z"]) >= 3
        elif lab["type"] == "volume_surge":
            assert row["volume_z"] >= 3 and row["volume_ratio"] >= 2
        else:
            assert abs(row["return_z"]) >= 2 and row["volume_z"] >= 2


def test_inject_anomalies_self_check_fails_loudly_on_degenerate_frame():
    # Constant 0.1% returns: the trailing return std is zero, so a
    # trailing-σ price plant has a zero return and cannot clear its
    # bar — the harness must fail loudly, never silently evaluate it.
    daily = pd.concat(
        [_daily_frame([100.0 * (1.001**i) for i in range(366)], coin=c) for c in COINS],
        ignore_index=True,
    )
    with pytest.raises(AssertionError, match="HARNESS BUG"):
        inject_anomalies(daily, n=30, seed=42)


# --- 6. Evaluation with +/-1-day tolerance -------------------------------------------
def test_evaluate_tolerance_and_known_metrics():
    detected = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-10", "2026-01-12", "2026-02-01", "2026-03-05"]
            ),
            "coin": ["bitcoin", "bitcoin", "ethereum", "bitcoin"],
            "baseline_flagged": [True, True, False, True],
            "is_anomaly": [False, False, True, False],
        }
    )
    injected = pd.DataFrame(
        {
            "date": ["2026-01-11", "2026-02-01", "2026-03-05"],
            "coin": ["bitcoin", "ethereum", "bitcoin"],
            "type": ["price_spike", "volume_surge", "joint_shock"],
            "magnitude": [1.15, 4.0, 1.08],
        }
    )
    result = evaluate(detected, injected, tolerance_days=1)
    # Baseline: flags on 01-10 (within 1 day of 01-11) and 03-05 hit;
    # 01-12 is also within 1 day of 01-11 but matches the same injection,
    # so TP = 2 of 3, FP = 0 (every baseline flag is near an injection).
    assert result["baseline"]["tp"] == 2
    assert result["baseline"]["fp"] == 0
    assert result["baseline"]["recall"] == pytest.approx(2 / 3)
    assert result["baseline"]["precision"] == pytest.approx(1.0)
    # Forest: only the 02-01 flag, which matches exactly: TP 1, FP 0.
    assert result["forest"]["tp"] == 1
    assert result["forest"]["recall"] == pytest.approx(1 / 3)
    # Union: all three injections found.
    assert result["union"]["recall"] == pytest.approx(1.0)
    assert result["union"]["tp"] == 3
    # Jaccard: baseline {01-10, 01-12, 03-05} vs forest {02-01}: no overlap.
    assert result["jaccard"] == pytest.approx(0.0)
    # Per-type recall (union): all three types found.
    assert result["per_type_recall"] == {
        "price_spike": 1.0,
        "volume_surge": 1.0,
        "joint_shock": 1.0,
    }


def test_evaluate_strict_tolerance_misses_next_day_flag():
    detected = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-12"]),
            "coin": ["bitcoin"],
            "baseline_flagged": [True],
            "is_anomaly": [False],
        }
    )
    injected = pd.DataFrame(
        {
            "date": ["2026-01-10"],
            "coin": ["bitcoin"],
            "type": ["price_spike"],
            "magnitude": [1.15],
        }
    )
    result = evaluate(detected, injected, tolerance_days=1)
    assert result["baseline"]["tp"] == 0  # 2 days away: not a detection
    assert result["baseline"]["fp"] == 1


def test_evaluate_amended_precision_counts_clean_flags_as_true_positives():
    # §4.4 amendment: a flag matching an injection OR a clean-data flag
    # is a true positive; only a flag matching neither is a false
    # positive. Recall is unchanged (matched injections / 30).
    detected = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-10", "2026-02-01", "2026-03-05"]),
            "coin": ["bitcoin", "bitcoin", "bitcoin"],
            "baseline_flagged": [True, True, True],
            "is_anomaly": [False, False, False],
        }
    )
    injected = pd.DataFrame(
        {
            "date": ["2026-01-11"],
            "coin": ["bitcoin"],
            "type": ["price_spike"],
            "magnitude": [0.16],
            "construction": ["4.0x trailing return std"],
        }
    )
    clean_flags = pd.DataFrame(
        {"date": ["2026-02-01"], "coin": ["bitcoin"]}  # the 02-01 flag is real
    )
    old = evaluate(detected, injected, tolerance_days=1)
    assert old["baseline"]["tp"] == 1  # only the 01-11 injection found
    assert old["baseline"]["fp"] == 2  # old rule: both other flags are FP
    assert old["baseline"]["precision"] == pytest.approx(1 / 3)
    new = evaluate(detected, injected, tolerance_days=1, clean_flags=clean_flags)
    # Recall unchanged: still 1 of 1 injections found.
    assert new["baseline"]["tp"] == 1
    assert new["baseline"]["recall"] == old["baseline"]["recall"]
    # The 02-01 flag now counts as a true positive (matches a clean flag);
    # only the 03-05 flag, matching neither, is a false positive.
    assert new["baseline"]["tp_flags"] == 2
    assert new["baseline"]["fp"] == 1
    assert new["baseline"]["precision"] == pytest.approx(2 / 3)
    # A clean flag one day away also counts (±1-day tolerance applies).
    clean_shifted = pd.DataFrame({"date": ["2026-02-02"], "coin": ["bitcoin"]})
    shifted = evaluate(detected, injected, tolerance_days=1, clean_flags=clean_shifted)
    assert shifted["baseline"]["tp_flags"] == 2
    assert shifted["baseline"]["fp"] == 1


# --- 7. Synthetic fallback -------------------------------------------------------
def test_generate_synthetic_deterministic_365_points():
    first = generate_synthetic(seed=42)
    second = generate_synthetic(seed=42)
    assert first == second  # deterministic
    for coin in COINS:
        assert len(first[coin]["prices"]) == 365
        first_ts = first[coin]["prices"][0][0]
        assert (
            pd.Timestamp(first_ts, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            == "2025-11-07"
        )
        assert first[coin]["prices"][0][1] == pytest.approx(
            {"bitcoin": 100_000.0, "ethereum": 3_500.0, "solana": 180.0}[coin]
        )


# --- 8. Synthetic never overwrites the live cache --------------------------------
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
    raw = {"bitcoin": {"prices": [[1762473600000, 100.0]]}}
    daily = pd.DataFrame(
        {
            "date": ["2025-11-07"],
            "coin": ["bitcoin"],
            "price": [100.0],
            "market_cap": [1.0],
            "volume": [1.0],
            "daily_return": [np.nan],
            "drawdown": [0.0],
            "vol_30d_ann": [np.nan],
        }
    )
    analysis = {
        "injected_featured": daily,
        "timeline": pd.DataFrame(columns=["date"]),
        "injected_labels": pd.DataFrame(columns=["date"]),
    }
    data_pipeline.save_outputs(daily, analysis, raw)
    assert live.read_text() == '{"sentinel": true}'  # untouched
    assert (tmp_path / "raw" / "bitcoin_market_chart_synthetic.json").exists()
    source = json.loads((tmp_path / "processed" / "data_source.json").read_text())
    assert source["synthetic"] is True
    assert source["seed"] == 42


# --- 9. Offline mode ---------------------------------------------------------------
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
    assert (proc_dir / "anomaly_timeline.csv").exists()
    assert len(pd.read_csv(proc_dir / "injected_anomalies.csv")) == 30


# --- 10. Committed CSVs match the published findings --------------------------------
def test_committed_daily_frame_shape_and_columns():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    assert len(daily) == 1098
    assert list(daily.columns) == [
        "date",
        "coin",
        "price",
        "market_cap",
        "volume",
        "daily_return",
        "abs_return",
        "volume_ratio",
        "log_volume_ratio",
        "vol_30d_ann",
        "drawdown",
        "return_z",
        "volume_z",
        "vol_regime",
    ]
    for coin, g in daily.groupby("coin"):
        assert len(g) == 366
        assert g["date"].min() == "2025-11-07"
        assert g["date"].max() == "2026-11-07"
        assert g["daily_return"].isna().sum() == 1  # first row per coin
        assert g["return_z"].isna().sum() == 31  # 30-day warm-up + first return NaN
        assert (
            g["volume_z"].isna().sum() == 60
        )  # volume_z needs 30 prior log-volume ratios


def test_committed_timeline_recomputes_flag_return_z():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    timeline = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "anomaly_timeline.csv")
    # Hand recompute Ethereum 2026-08-20 return_z from the CSV: trailing
    # 30-day mean/std of daily returns before that day (excluding today).
    eth = daily[daily["coin"] == "ethereum"].sort_values("date").reset_index(drop=True)
    idx = int(eth.index[eth["date"] == "2026-08-20"][0])
    prior = eth["daily_return"].iloc[idx - 30 : idx]
    recomputed = (eth["daily_return"].iloc[idx] - prior.mean()) / prior.std(ddof=1)
    published = timeline[
        (timeline["coin"] == "ethereum") & (timeline["date"] == "2026-08-20")
    ]["return_z"].iloc[0]
    assert recomputed == pytest.approx(published, abs=1e-9)
    assert recomputed == pytest.approx(10.838289024100376, abs=1e-9)


def test_timeline_matches_recomputed_union():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    timeline = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "anomaly_timeline.csv")
    detected, _cont = run_detection(daily)
    expected = detected[detected["baseline_flagged"] | detected["is_anomaly"]]
    assert len(timeline) == len(expected)
    assert set(timeline["flagged_by"]) <= {"baseline", "forest", "both"}
    assert set(timeline["severity"]) <= {"High", "Medium", "Low"}
    assert timeline["explanation"].str.len().min() > 20
    assert not timeline["explanation"].str.contains("manipulation").any()
    # Every timeline row is traceable: date+coin exists in the daily frame.
    keys = set(zip(daily["date"], daily["coin"]))
    assert {(d, c) for d, c in zip(timeline["date"], timeline["coin"])} <= keys


# --- 11. Notebook _find_root() ------------------------------------------------------
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


# --- 12. Attribution + ethics guard --------------------------------------------------
def test_powered_by_coingecko_attribution_and_ethics():
    app_src = (PROJECT_ROOT / "src" / "app.py").read_text()
    assert "Powered by CoinGecko" in app_src
    assert "coingecko.com" in app_src
    assert "use_container_width" not in app_src  # deprecated API must not appear
    assert "width='stretch'" in app_src or 'width="stretch"' in app_src
    charts_src = (PROJECT_ROOT / "src" / "make_charts.py").read_text()
    assert "Powered by CoinGecko" in charts_src
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "Powered by CoinGecko" in readme
    assert "Educational analysis only" in app_src
    assert "not investment advice" in app_src.lower()
    ethics = "Anomalies flagged here are statistical outliers in price and volume."
    assert ethics in readme
    assert ethics in app_src
    insights = (PROJECT_ROOT / "outputs" / "insights_summary.md").read_text()
    assert ethics in insights
    # "manipulation" appears in the insights only in the ethics sentence
    # (twice) and in the plan-mandated limits wording ("cannot distinguish
    # ... from manipulation") — never as an accusation about a flagged day.
    assert insights.lower().count("manipulation") <= 3


# --- 13. clean_chart --------------------------------------------------------------------
def test_clean_chart_merges_and_dedupes():
    raw = _raw([100.0, 110.0, 105.0])
    raw["prices"].append(raw["prices"][1])  # duplicate timestamp
    df = clean_chart(raw, "bitcoin")
    assert list(df.columns) == ["date", "coin", "price", "market_cap", "volume"]
    assert len(df) == 3
    assert df["date"].tolist() == ["2025-11-07", "2025-11-08", "2025-11-09"]
    assert df["price"].notna().all()


def test_compute_daily_adds_feature_columns():
    raw = _raw([100.0 + i for i in range(40)])
    daily = compute_daily(clean_chart(raw, "bitcoin"))
    assert "return_z" in daily.columns
    assert "volume_ratio" in daily.columns
    assert "vol_regime" in daily.columns
    assert daily["daily_return"].isna().sum() == 1
    assert daily["return_z"].isna().sum() == 31
    assert (daily["drawdown"] <= 0).all()


# --- 14. Explanations ----------------------------------------------------------------------
def test_generate_explanation_uses_row_numbers_only():
    row = pd.Series(
        {
            "coin": "bitcoin",
            "date": "2026-03-14",
            "daily_return": -0.082,
            "return_z": -3.4,
            "volume_ratio": 2.6,
            "volume_z": 2.1,
            "vol_30d_ann": 0.55,
            "rules_triggered": "R1",
        }
    )
    text = generate_explanation(row)
    assert "8.2%" in text and "-3.4" in text and "2.6x" in text
    assert "manipulation" not in text.lower()
    assert "caused by" not in text.lower()
    forest_row = row.copy()
    forest_row["rules_triggered"] = ""
    forest_text = generate_explanation(forest_row)
    assert "Isolation Forest only" in forest_text


def test_build_timeline_columns():
    daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "crypto_daily.csv")
    detected, _cont = run_detection(daily)
    timeline = build_timeline(detected)
    assert list(timeline.columns) == [
        "date",
        "coin",
        "price",
        "daily_return",
        "volume",
        "volume_ratio",
        "return_z",
        "volume_z",
        "vol_30d_ann",
        "vol_regime",
        "drawdown",
        "rules_triggered",
        "isolation_forest_score",
        "flagged_by",
        "severity",
        "explanation",
    ]
    assert len(timeline) == 54
