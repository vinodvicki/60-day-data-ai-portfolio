"""Tests for the Day 17 chart builder and annual join.

Charts render to a temp directory; no processed files are needed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import data_pipeline as dp
from src import make_charts as mc


def _annual_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2023, 2024, 2025],
            "yield_t_per_ha": [11.0, 11.2, 11.7],
            "yield_resid_t_per_ha": [-0.1, -0.1, 0.2],
            "gs_dsci_mean": [148.0, 49.0, 58.0],
            "gs_dsci_mean_iowa": [188.0, 64.0, 46.0],
            "gs_dsci_mean_illinois": [108.0, 34.0, 70.0],
            "gs_precip_anomaly_mm": [-194.0, -13.0, -74.0],
        }
    )


def _summary_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fips": ["19051", "19021", "17001"],
            "county": ["Davis County", "Buena Vista County", "Adams County"],
            "state": ["IA", "IA", "IL"],
            "mean_d2plus_pct": [12.7, 12.6, 5.0],
            "worst_year": [2023, 2021, 2012],
            "worst_year_d2plus_pct": [67.3, 78.1, 40.0],
            "mean_dsci": [82.8, 83.8, 60.0],
        }
    )


def test_chart_01_trend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    path = mc.chart_01_dsci_trend(_annual_frame())
    assert path.exists() and path.stat().st_size > 10_000
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_chart_02_scatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    path = mc.chart_02_drought_vs_yield(_annual_frame())
    assert path.exists() and path.stat().st_size > 10_000


def test_chart_03_precip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    path = mc.chart_03_precip_anomaly(_annual_frame())
    assert path.exists() and path.stat().st_size > 10_000


def test_chart_04_fallback_when_geojson_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    monkeypatch.setattr(mc, "_load_geojson", lambda: None)
    path = mc.chart_04_county_map(_summary_frame())
    assert path.exists() and path.stat().st_size > 10_000


def test_build_annual_dataset_joins_two_states() -> None:
    years = list(range(2000, 2026))
    yields = pd.DataFrame(
        {"year": years, "yield_t_per_ha": [8.0 + 0.1 * i for i in range(26)]}
    )
    state_annual = {
        "iowa": pd.DataFrame(
            {
                "year": years,
                "gs_dsci_mean_iowa": [50.0 + i for i in range(26)],
                "gs_dsci_max_iowa": [200.0] * 26,
                "weeks_dsci_ge100_iowa": [10] * 26,
            }
        ),
        "illinois": pd.DataFrame(
            {
                "year": years,
                "gs_dsci_mean_illinois": [30.0 + i for i in range(26)],
                "gs_dsci_max_illinois": [150.0] * 26,
                "weeks_dsci_ge100_illinois": [5] * 26,
            }
        ),
    }
    precip = {
        state: pd.DataFrame(
            {
                "year": years,
                "gs_precip_total": [600.0 - 5.0 * i for i in range(26)],
                "jul_precip_total": [70.0] * 26,
            }
        )
        for state in ("iowa", "illinois")
    }
    annual = dp.build_annual_dataset(yields, state_annual, precip)
    assert len(annual) == 26
    # DSCI mean is the two-state average: year 2000 -> (50+30)/2 = 40.
    assert annual["gs_dsci_mean"].iloc[0] == pytest.approx(40.0)
    # Precipitation anomaly is vs the 26-year mean of the two-state average.
    assert annual["gs_precip_anomaly_mm"].iloc[0] == pytest.approx(62.5)
    assert annual["gs_precip_anomaly_mm"].iloc[-1] == pytest.approx(-62.5)
    assert annual["yield_bu_per_acre"].iloc[0] == pytest.approx(
        8.0 * dp.BU_PER_ACRE_PER_T_PER_HA
    )
