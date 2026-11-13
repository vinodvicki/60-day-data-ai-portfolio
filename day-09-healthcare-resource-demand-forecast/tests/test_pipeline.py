"""Day 9 — Healthcare Resource Demand Forecast: offline pytest suite.

Covers the Combined construction (sum of 3 pathogen %s), the 72 NULLs
treated as missing (never 0), the $limit=50000 fetch rule (no silent
truncation), the national series shape and latest week (161 weeks,
2026-10-31 at 2.3%), the bed state-sum ratio (not the mean of ratios),
the demand-band thresholds incl. boundaries, seasonal naïve = same week
last year, the pure metric functions with hand-checked fixtures, the
bootstrap intervals containing the point forecast and widening with
horizon, the 3-origin backtest design, the offline path never clobbering
the live record (Day 5/6 lesson), the synthetic fallback staying labelled
and never overwriting live files, the data-size rule, and the SQL-vs-
pandas check. Runs from the repo root and from inside the day folder.
Optimizer regression tests (2026-11-13, D-1/D-2/D-3): the corrected
winter-rise claim (2.4%, not 0.7%) in the insights summary and the
notebook, and the honest chart footnotes in src/make_charts.py.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline as pipeline
from src.forecast import (
    bootstrap_intervals,
    classify_band,
    holt_winters_forecast,
    rolling_backtest,
    seasonal_naive_forecast,
)
from src.metrics import (
    interval_coverage,
    mae,
    mape,
    rmse,
    seasonal_naive_predict,
)

PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


def _record() -> dict:
    return json.loads((PROCESSED / "data_source.json").read_text())


def _national() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "national_combined.csv")


# --- Fixtures ---------------------------------------------------------------
NSSP_FIXTURE = pd.DataFrame(
    {
        "week_end": ["2026-10-24"] * 3 + ["2026-10-31"] * 3,
        "pathogen": ["COVID-19", "Influenza", "RSV"] * 2,
        "geography": ["United States"] * 6,
        # 2026-10-24 is complete (0.4 + 1.2 + 0.1 = 1.7);
        # 2026-10-31 is missing RSV -> Combined must be NaN, never 1.7+0.5.
        "percent_visits": [0.4, 1.2, 0.1, 0.5, 1.7, np.nan],
    }
)

BED_FIXTURE = pd.DataFrame(
    {
        "date": ["2024-04-20", "2024-04-20", "2024-04-27", "2024-04-27"],
        "state": ["AA", "BB", "AA", "BB"],
        "inpatient_beds": [100, 300, 100, 300],
        "inpatient_beds_used": [80, 150, 90, 120],
        "inpatient_beds_coverage": [10, 10, 10, 10],
        "inpatient_beds_used_coverage": [10, 10, 10, 10],
        "total_staffed_adult_icu_beds": [20, 40, 20, 40],
        "staffed_adult_icu_bed_occupancy": [10, 20, 12, 24],
    }
)


# --- Combined construction / NULL rule --------------------------------------
def test_combined_is_sum_of_three_pathogens():
    combined = pipeline.build_combined(NSSP_FIXTURE)
    row = combined[combined["week_end"] == "2026-10-24"].iloc[0]
    assert row["covid_pct"] == pytest.approx(0.4)
    assert row["flu_pct"] == pytest.approx(1.2)
    assert row["rsv_pct"] == pytest.approx(0.1)
    assert row["combined_pct"] == pytest.approx(1.7)


def test_null_pathogen_makes_combined_missing_never_zero():
    combined = pipeline.build_combined(NSSP_FIXTURE)
    row = combined[combined["week_end"] == "2026-10-31"].iloc[0]
    assert pd.isna(row["rsv_pct"])
    assert pd.isna(row["combined_pct"])
    assert row["combined_pct"] != 0.0


def test_null_audit_counts_72_and_names_geographies():
    record = _record()
    audit = record["null_audit"]
    assert audit["n_null_percent_visits"] == 72
    assert audit["null_share"] == pytest.approx(0.0029)
    assert set(audit["null_by_geography"]) == {"Delaware", "Georgia", "Iowa"}
    assert audit["n_national_weeks_affected"] == 0


# --- Fetch rule / counts ----------------------------------------------------
def test_fetch_urls_carry_limit_50000():
    assert "$limit=50000" in pipeline.NSSP_URL
    assert "$limit=50000" in pipeline.BED_URL_TEMPLATE
    assert "$offset=" in pipeline.BED_URL_TEMPLATE


def test_live_counts_recorded():
    record = _record()
    assert record["source"] == "live"
    assert record["synthetic"] is False
    assert record["nssp_rows"] == 25_116
    assert record["bed_rows"] == 81_713
    assert record["national_weeks"] == 161
    assert record["bed_weeks"] == 226


def test_national_series_shape_and_latest_week():
    national = _national()
    assert len(national) == 161
    assert national["week_end"].iloc[0] == "2023-10-07"
    assert national["week_end"].iloc[-1] == "2026-10-31"
    latest = national.iloc[-1]
    assert latest["covid_pct"] == pytest.approx(0.5)
    assert latest["flu_pct"] == pytest.approx(1.7)
    assert latest["rsv_pct"] == pytest.approx(0.1)
    # Hand validation: 0.5 + 1.7 + 0.1 = 2.3, recomputed independently.
    assert 0.5 + 1.7 + 0.1 == pytest.approx(2.3)
    assert latest["combined_pct"] == pytest.approx(2.3)


def test_state_series_has_51_geographies():
    states = pd.read_csv(PROCESSED / "state_combined.csv")
    assert states["geography"].nunique() == 51
    assert "United States" not in set(states["geography"])
    assert len(states) == 8_187


# --- Bed series -------------------------------------------------------------
def test_bed_utilisation_is_state_sum_ratio_not_mean_of_ratios():
    bed = pipeline.build_bed_series(BED_FIXTURE)
    assert len(bed) == 2
    # Week 2024-04-20: (80 + 150) / (100 + 300) = 0.575, NOT the mean
    # of the per-state ratios (0.8 + 0.5) / 2 = 0.65.
    first = bed[bed["week_end"] == "2024-04-20"].iloc[0]
    assert first["bed_utilisation"] == pytest.approx(0.575)
    assert first["bed_utilisation"] != pytest.approx(0.65)
    assert first["icu_occupancy"] == pytest.approx(30 / 60)
    assert first["beds_total"] == 400
    assert first["beds_used"] == 230


def test_bed_series_range_and_end_date():
    bed = pd.read_csv(PROCESSED / "bed_utilisation.csv")
    assert bed["week_end"].iloc[0] == "2020-01-04"
    assert bed["week_end"].iloc[-1] == "2024-04-27"
    assert len(bed) == 226
    assert bed["bed_utilisation"].between(0, 1).all()


def test_coverage_share_definition():
    # Both fixture rows have equal numerator/denominator coverage counts.
    assert pipeline.coverage_share(BED_FIXTURE) == pytest.approx(1.0)
    mixed = BED_FIXTURE.copy()
    mixed.loc[0, "inpatient_beds_used_coverage"] = 9
    assert pipeline.coverage_share(mixed) == pytest.approx(0.75)


# --- Demand bands -----------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected",
    [
        (0.0, "Low"),
        (1.99, "Low"),
        (2.0, "Moderate"),
        (3.99, "Moderate"),
        (4.0, "High"),
        (5.99, "High"),
        (6.0, "Surge"),
        (10.4, "Surge"),
    ],
)
def test_band_thresholds_including_boundaries(value, expected):
    assert classify_band(value) == expected


def test_band_history_counts_match_forecast_record():
    record = _record()
    history = pd.read_csv(PROCESSED / "band_history.csv")
    assert len(history) == 161
    counts = history["band"].value_counts().to_dict()
    assert counts == record["forecast"]["band_counts_history"]
    assert counts == {"Low": 89, "Moderate": 35, "High": 19, "Surge": 18}
    assert record["forecast"]["observed_max_combined_pct"] == pytest.approx(10.4)


# --- Metrics (hand-checked) -------------------------------------------------
def test_rmse_hand_check():
    # sqrt(mean((0, 0, 1)^2)) = sqrt(1/3).
    assert rmse([1, 2, 3], [1, 2, 4]) == pytest.approx(0.577350269, rel=1e-6)


def test_mae_hand_check():
    assert mae([1, 2, 3], [1, 2, 4]) == pytest.approx(1 / 3)


def test_mape_hand_check():
    # (0 + 0 + (1/3)) / 3 * 100 = 11.111...%.
    assert mape([1, 2, 3], [1, 2, 4]) == pytest.approx(100 / 9)


def test_interval_coverage_hand_check():
    assert interval_coverage([1, 2, 3], [0, 1, 2], [2, 3, 4]) == pytest.approx(1.0)
    assert interval_coverage([1, 2, 3], [0, 0, 0], [1.5, 1.5, 1.5]) == pytest.approx(
        1 / 3
    )


def test_metrics_reject_mismatched_lengths():
    with pytest.raises(ValueError):
        rmse([1, 2], [1])
    with pytest.raises(ValueError):
        interval_coverage([1, 2], [0], [2, 2])


# --- Forecasting ------------------------------------------------------------
def test_seasonal_naive_is_same_week_last_year():
    series = pd.Series(np.arange(60, dtype=float))
    forecast = seasonal_naive_forecast(series, horizon=4)
    assert list(forecast) == [8.0, 9.0, 10.0, 11.0]
    assert list(seasonal_naive_predict(np.arange(60, dtype=float), 2)) == [8.0, 9.0]


def test_holt_winters_forecast_length_and_finite():
    series = _national()["combined_pct"]
    point, fitted = holt_winters_forecast(series, horizon=8)
    assert len(point) == 8
    assert np.isfinite(point).all()
    assert np.isfinite(np.asarray(fitted.resid)).all()


def test_bootstrap_intervals_contain_point_and_widen():
    residuals = np.array([-0.5, -0.2, 0.0, 0.2, 0.5] * 20, dtype=float)
    point = np.array([2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
    intervals = bootstrap_intervals(residuals, point, n_paths=1000, seed=42)
    assert (intervals["lo_80"] <= point).all()
    assert (intervals["hi_80"] >= point).all()
    assert (intervals["lo_95"] <= intervals["lo_80"]).all()
    assert (intervals["hi_95"] >= intervals["hi_80"]).all()
    width_80 = intervals["hi_80"] - intervals["lo_80"]
    assert width_80[-1] > width_80[0]


def test_backtest_design_three_origins_four_week_horizons():
    series = _national()["combined_pct"]
    backtest = rolling_backtest(series)
    assert len(backtest) == 6  # 3 origins x 2 methods
    assert set(backtest["origin"]) == {12, 8, 4}
    assert set(backtest["method"]) == {"holt_winters", "seasonal_naive"}
    assert backtest["coverage_80"].between(0, 1).all()
    assert (backtest["rmse"] > 0).all()


def test_committed_backtest_matches_design():
    backtest = pd.read_csv(PROCESSED / "backtest.csv")
    assert len(backtest) == 6
    assert set(backtest["origin"]) == {12, 8, 4}
    record = _record()
    assert record["forecast"]["published_method"] == "holt_winters"
    assert record["forecast"]["mean_rmse"]["holt_winters"] < (
        record["forecast"]["mean_rmse"]["seasonal_naive"]
    )


def test_forecast_csv_shape_bands_and_interval_ordering():
    forecast = pd.read_csv(PROCESSED / "forecast.csv")
    assert len(forecast) == 8
    assert forecast["week_end"].iloc[0] == "2026-11-07"
    assert forecast["week_end"].iloc[-1] == "2026-12-26"
    assert set(forecast["band"]) <= {"Low", "Moderate", "High", "Surge"}
    assert (forecast["lo_95"] <= forecast["lo_80"]).all()
    assert (forecast["lo_80"] <= forecast["forecast_pct"]).all()
    assert (forecast["forecast_pct"] <= forecast["hi_80"]).all()
    assert (forecast["hi_80"] <= forecast["hi_95"]).all()
    assert list(forecast["band"]) == [
        "Moderate",
        "Moderate",
        "High",
        "High",
        "Surge",
        "Surge",
        "Surge",
        "Surge",
    ]


# --- Offline / synthetic guards ---------------------------------------------
def _copy_committed(tmp_path: Path) -> tuple[Path, Path]:
    processed = tmp_path / "processed"
    raw = tmp_path / "raw"
    processed.mkdir()
    raw.mkdir()
    for name in (
        "national_combined.csv",
        "state_combined.csv",
        "bed_utilisation.csv",
        "forecast.csv",
        "backtest.csv",
        "band_history.csv",
        "data_source.json",
    ):
        shutil.copy(PROCESSED / name, processed / name)
    shutil.copy(RAW / "sample_rows.json", raw / "sample_rows.json")
    return processed, raw


def test_offline_run_does_not_clobber_data_source(tmp_path, monkeypatch):
    processed, raw = _copy_committed(tmp_path)
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", processed)
    monkeypatch.setattr(pipeline, "RAW_DIR", raw)
    before = (processed / "data_source.json").read_bytes()
    before_forecast = (processed / "forecast.csv").read_bytes()
    pipeline.run_offline()
    assert (processed / "data_source.json").read_bytes() == before
    assert (processed / "forecast.csv").read_bytes() == before_forecast


def test_synthetic_never_overwrites_live_files(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    raw = tmp_path / "raw"
    processed.mkdir()
    raw.mkdir()
    live = raw / pipeline.NSSP_RAW_NAME
    live.write_text('[{"week_end": "2023-10-07"}]', encoding="utf-8")
    bed_rows = BED_FIXTURE.to_dict(orient="records")
    (raw / pipeline.BED_RAW_NAME).write_text(json.dumps(bed_rows), encoding="utf-8")
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", processed)
    monkeypatch.setattr(pipeline, "RAW_DIR", raw)
    pipeline.run_synthetic()
    assert live.read_text(encoding="utf-8") == '[{"week_end": "2023-10-07"}]'
    assert (raw / pipeline.NSSP_SYNTHETIC_NAME).exists()
    record = json.loads((processed / "data_source.json").read_text())
    assert record["synthetic"] is True
    assert record["source"] == "synthetic"
    assert record["seed"] == 42


def test_synthetic_generator_is_deterministic():
    first = pipeline.build_synthetic_nssp_rows()
    second = pipeline.build_synthetic_nssp_rows()
    assert first == second
    assert len(first) == 161 * 52 * 3


# --- Data-size rule / provenance --------------------------------------------
def test_no_committed_file_over_1mb_and_data_under_5mb():
    # Git-ignored raw full JSONs are excluded: only committed files count.
    ignored_names = {
        pipeline.NSSP_RAW_NAME,
        pipeline.BED_RAW_NAME,
    }
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        if path.name in ignored_names or path.name.endswith("_synthetic.json"):
            continue
        assert path.stat().st_size <= 1_000_000, f"{path} over 1 MB"
        total += path.stat().st_size
    assert total < 5_000_000, f"committed data/ total {total} over 5 MB"


def test_sample_rows_is_capped_and_labelled():
    sample = json.loads((RAW / "sample_rows.json").read_text())
    assert len(sample["nssp"]) <= 1000
    assert len(sample["bed"]) <= 1000
    assert (RAW / "sample_rows.json").stat().st_size <= 1_000_000


def test_charts_exist():
    for name in (
        "01_forecast.png",
        "02_backtest.png",
        "03_demand_bands.png",
        "04_bed_capacity.png",
    ):
        path = ROOT / "outputs" / "charts" / name
        assert path.exists() and path.stat().st_size > 10_000


# --- SQL check (plan §4.7) --------------------------------------------------
def test_sql_matches_pandas_for_season_and_lag():
    national = _national().copy()
    national["week_end"] = pd.to_datetime(national["week_end"])
    national["season"] = national["week_end"].dt.month.map(
        lambda m: (
            "Winter"
            if m in (12, 1, 2)
            else (
                "Spring"
                if m in (3, 4, 5)
                else ("Summer" if m in (6, 7, 8) else "Autumn")
            )
        )
    )
    national["lag_4w"] = national["combined_pct"].shift(4)
    pandas_means = national.groupby("season")["combined_pct"].mean().round(4)
    pandas_lag = national["lag_4w"].dropna().round(4).tolist()

    conn = sqlite3.connect(":memory:")
    national.to_sql("weekly", conn, index=False)
    rows = conn.execute(
        "SELECT season, ROUND(AVG(combined_pct), 4) FROM weekly "
        "GROUP BY season ORDER BY season"
    ).fetchall()
    sql_means = {season: value for season, value in rows}
    for season, value in pandas_means.items():
        assert sql_means[season] == pytest.approx(value, abs=1e-4)
    lag_rows = conn.execute(
        "SELECT combined_pct FROM weekly ORDER BY week_end LIMIT 157"
    ).fetchall()
    sql_lag = [round(row[0], 4) for row in lag_rows]
    assert sql_lag == pandas_lag
    conn.close()


# --- Optimizer regression tests (D-1, D-2, D-3) -----------------------------
def test_winter_rise_claim_is_2_4_pct_not_0_7():
    """D-1: last winter rose 2.4% (2024-12-07) -> 10.0% (2025-02-01).

    The 0.7% figure was the Combined value on 2025-11-01 (same week last
    year) and was wrongly conflated with the start of the eight-week
    rise. Grounded against the committed national series, not the docs.
    """
    national = _national().set_index("week_end")["combined_pct"]
    assert national["2024-12-07"] == pytest.approx(2.4)
    assert national["2025-02-01"] == pytest.approx(10.0)

    insights = (ROOT / "outputs" / "insights_summary.md").read_text()
    assert "rose from 2.4% to 10.0% in eight weeks" in insights
    assert "rose from 0.7% to 10.0% in eight weeks" not in insights

    notebook = json.loads((ROOT / "notebooks" / "analysis.ipynb").read_text())
    cell5 = "".join(notebook["cells"][5]["source"])
    assert "rose from 2.4% to 10.0% in eight weeks" in cell5
    assert "rose from 0.7% to 10.0% in eight weeks" not in cell5


def test_chart_footnotes_are_honest():
    """D-2/D-3: chart 01 discloses the >observed-max forecast; chart 04
    no longer claims a zoomed y-axis (the axis is matplotlib-auto, 0 to
    ~88, and the wording now says so)."""
    source = (ROOT / "src" / "make_charts.py").read_text()
    assert "zoomed to the data range" not in source
    assert "y-axis starts at 0" in source
    # The disclosure spans two adjacent string literals in the source,
    # so assert both halves rather than the joined sentence.
    assert "Forecast weeks 7–8 exceed the" in source
    assert "observed historical maximum" in source
