"""Tests for the Day 17 data pipeline: cleaning and aggregation rules.

All tests run on small synthetic frames — no network, no raw files.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import data_pipeline as dp


def test_clean_state_dsci_parses_and_validates() -> None:
    text = (
        "Name,MapDate,DSCI\n"
        "Iowa,20000104,215\n"
        "Iowa,20000111,217\n"
        "Iowa,20000118,200\n"
    )
    frame = dp.clean_state_dsci(text, "iowa")
    assert len(frame) == 3
    assert frame["map_date"].iloc[0] == pd.Timestamp("2000-01-04")
    assert frame["dsci"].tolist() == [215, 217, 200]


def test_clean_state_dsci_rejects_bad_first_week() -> None:
    text = "Name,MapDate,DSCI\nIowa,20010102,100\n"
    with pytest.raises(ValueError, match="first DSCI week"):
        dp.clean_state_dsci(text, "iowa")


def test_clean_state_dsci_rejects_out_of_range() -> None:
    text = "Name,MapDate,DSCI\nIowa,20000104,501\n"
    with pytest.raises(ValueError, match="outside 0-500"):
        dp.clean_state_dsci(text, "iowa")


def _county_csv(rows: list[str]) -> str:
    header = (
        "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4,"
        "ValidStart,ValidEnd,StatisticFormatID\n"
    )
    return header + "".join(rows)


def test_clean_county_block_ok_and_dsci_proxy() -> None:
    text = _county_csv(
        [
            (
                "20240102,19001,Adair County,IA,50.00,50.00,10.00,0.00,0.00,0.00,"
                "2024-01-02,2024-01-08,1\n"
            ),
            (
                "20240109,19001,Adair County,IA,80.00,20.00,0.00,0.00,0.00,0.00,"
                "2024-01-09,2024-01-15,1\n"
            ),
        ]
    )
    frame = dp.clean_county_block(text, "iowa")
    assert len(frame) == 2
    assert frame["fips"].tolist() == ["19001", "19001"]
    proxy = dp.county_dsci_proxy(frame)
    # Row 1: exclusive shares D0-D1=40, D1-D2=10 -> 1*40 + 2*10 = 60.
    # Row 2: D0=20, D1=0 -> 20. (Cumulative columns sum, not 1..5 weights.)
    assert proxy.tolist() == pytest.approx([60.0, 20.0])


def test_clean_county_block_rejects_bad_percent_sum() -> None:
    text = _county_csv(
        [
            (
                "20240102,19001,Adair County,IA,50.00,60.00,10.00,0.00,0.00,0.00,"
                "2024-01-02,2024-01-08,1\n"
            ),
        ]
    )
    with pytest.raises(ValueError, match="deviates from 100"):
        dp.clean_county_block(text, "iowa")


def test_clean_county_block_rejects_non_monotone_classes() -> None:
    text = _county_csv(
        [
            (
                "20240102,19001,Adair County,IA,50.00,50.00,60.00,0.00,0.00,0.00,"
                "2024-01-02,2024-01-08,1\n"
            ),
        ]
    )
    with pytest.raises(ValueError, match="not monotone"):
        dp.clean_county_block(text, "iowa")


def test_county_dsci_proxy_never_exceeds_500() -> None:
    # Regression test (2026-11-24): weighting the cumulative columns 1..5
    # double-counts and can exceed 500 (Woodbury County IA 2023 hit 704).
    text = _county_csv(
        [
            (
                "20230103,19193,Woodbury County,IA,0.00,100.00,100.00,97.72,23.45,0.00,"
                "2023-01-03,2023-01-09,1\n"
            ),
        ]
    )
    frame = dp.clean_county_block(text, "iowa")
    proxy = dp.county_dsci_proxy(frame)
    assert proxy.iloc[0] == pytest.approx(100 + 100 + 97.72 + 23.45)
    assert proxy.iloc[0] <= 500.0


def test_aggregate_state_annual_growing_season_only() -> None:
    dates = pd.to_datetime(
        ["2024-01-02", "2024-04-02", "2024-07-02", "2024-10-01", "2024-12-31"]
    )
    frame = pd.DataFrame({"map_date": dates, "dsci": [10, 100, 200, 30, 40]})
    annual = dp.aggregate_state_annual(frame, "iowa")
    assert len(annual) == 1
    # Growing-season weeks are Apr (100) and Jul (200): mean 150.
    assert annual["gs_dsci_mean_iowa"].iloc[0] == pytest.approx(150.0)
    assert annual["gs_dsci_max_iowa"].iloc[0] == pytest.approx(200.0)
    assert annual["weeks_dsci_ge100_iowa"].iloc[0] == 2


def test_aggregate_county_annual() -> None:
    frame = pd.DataFrame(
        {
            "fips": ["19001", "19001", "19001"],
            "county": ["Adair County"] * 3,
            "state": ["IA"] * 3,
            "None": [50.0, 80.0, 90.0],
            "D0": [50.0, 20.0, 10.0],
            "D1": [10.0, 0.0, 0.0],
            "D2": [0.0, 0.0, 0.0],
            "D3": [0.0, 0.0, 0.0],
            "D4": [0.0, 0.0, 0.0],
            "valid_start": pd.to_datetime(["2024-05-01", "2024-06-01", "2024-11-01"]),
        }
    )
    out = dp.aggregate_county_annual(frame)
    assert len(out) == 1
    # Growing-season weeks are May + June only (Nov is outside Apr-Sep).
    assert out["gs_d1plus_pct"].iloc[0] == pytest.approx(5.0)
    assert out["gs_d2plus_pct"].iloc[0] == pytest.approx(0.0)
    # DSCI proxy: May D0+D1 = 50+10=60, Jun D0=20 -> mean 40.
    assert out["gs_dsci"].iloc[0] == pytest.approx(40.0)


def test_clean_yields_filters_to_usa_26_rows() -> None:
    rows = ["Entity,Code,Year,Maize yield"]
    for year in range(2000, 2026):
        rows.append(f"United States,USA,{year},{8.0 + 0.1 * (year - 2000):.3f}")
    rows.append("Canada,CAN,2024,9.999")
    frame = dp.clean_yields("\n".join(rows))
    assert len(frame) == 26
    assert frame["year"].min() == 2000
    assert frame["year"].max() == 2025


def test_build_precip_features() -> None:
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    daily = {
        "time": [d.strftime("%Y-%m-%d") for d in dates],
        "precipitation_sum": [1.0] * len(dates),
    }
    out = dp.build_precip_features(daily)
    assert len(out) == 1
    # Apr-Sep has 183 days in 2024 (leap year); July has 31.
    assert out["gs_precip_total"].iloc[0] == pytest.approx(183.0)
    assert out["jul_precip_total"].iloc[0] == pytest.approx(31.0)


def test_build_precip_features_rejects_negative() -> None:
    dates = pd.date_range("2024-01-01", "2024-01-03", freq="D")
    daily = {
        "time": [d.strftime("%Y-%m-%d") for d in dates],
        "precipitation_sum": [1.0, -1.0, 1.0],
    }
    with pytest.raises(ValueError, match="negative precipitation"):
        dp.build_precip_features(daily)


def test_build_county_summary_worst_year() -> None:
    county_year = pd.DataFrame(
        {
            "fips": ["19001", "19001", "17001"],
            "county": ["Adair County", "Adair County", "Adams County"],
            "state": ["IA", "IA", "IL"],
            "year": [2024, 2025, 2024],
            "gs_d1plus_pct": [10.0, 20.0, 5.0],
            "gs_d2plus_pct": [5.0, 15.0, 2.0],
            "gs_d3plus_pct": [0.0, 1.0, 0.0],
            "gs_dsci": [70.0, 90.0, 30.0],
        }
    )
    summary = dp.build_county_summary(county_year)
    assert len(summary) == 2
    adair = summary[summary["fips"] == "19001"].iloc[0]
    assert adair["mean_d2plus_pct"] == pytest.approx(10.0)
    assert int(adair["worst_year"]) == 2025
    assert adair["worst_year_d2plus_pct"] == pytest.approx(15.0)
