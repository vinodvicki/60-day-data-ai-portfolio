"""Smoke tests for Day 17: the committed processed files and charts exist
and have the expected shape. No network, no raw files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"


def test_readme_exists() -> None:
    assert (ROOT / "README.md").read_text().strip() != ""


def test_data_readme_exists() -> None:
    assert (ROOT / "data" / "README.md").exists()


def test_annual_table_shape() -> None:
    annual = pd.read_csv(PROCESSED_DIR / "annual_drought_yield.csv")
    assert len(annual) == 26
    assert annual["year"].tolist() == list(range(2000, 2026))
    required = {
        "year",
        "yield_t_per_ha",
        "yield_bu_per_acre",
        "yield_resid_t_per_ha",
        "gs_dsci_mean",
        "gs_dsci_mean_iowa",
        "gs_dsci_mean_illinois",
        "gs_dsci_max",
        "weeks_dsci_ge100",
        "gs_precip_total_mm",
        "gs_precip_anomaly_mm",
        "gs_precip_anomaly_pct",
        "jul_precip_anomaly_mm",
    }
    assert required.issubset(set(annual.columns))
    assert not annual.isna().any().any()
    # 2012 is the worst drought year in the series.
    assert int(annual.loc[annual["gs_dsci_mean"].idxmax(), "year"]) == 2012


def test_correlation_results_shape() -> None:
    corr = pd.read_csv(PROCESSED_DIR / "correlation_results.csv")
    assert len(corr) == 3
    assert set(corr["variable"]) == {
        "gs_dsci_mean",
        "gs_precip_anomaly_mm",
        "jul_precip_anomaly_mm",
    }
    assert (corr["n"] == 26).all()
    assert ((corr["p_value"] >= 0) & (corr["p_value"] <= 1)).all()
    assert ((corr["pearson_r"] >= -1) & (corr["pearson_r"] <= 1)).all()


def test_county_files_shape() -> None:
    county_year = pd.read_csv(PROCESSED_DIR / "county_year.csv")
    assert len(county_year) == 201 * 26
    assert county_year["fips"].nunique() == 201
    assert county_year["state"].value_counts().to_dict() == {
        "IA": 99 * 26,
        "IL": 102 * 26,
    }
    assert not county_year[["gs_d2plus_pct", "gs_dsci"]].isna().any().any()
    summary = pd.read_csv(PROCESSED_DIR / "county_summary.csv")
    assert len(summary) == 201
    assert summary["mean_d2plus_pct"].is_monotonic_decreasing


def test_ar1_forecast_shape() -> None:
    forecast = pd.read_csv(PROCESSED_DIR / "ar1_forecast.csv")
    assert forecast["year"].tolist() == [2025, 2026]
    row_2026 = forecast.loc[forecast["year"] == 2026].iloc[0]
    assert (
        float(row_2026["lower"])
        < float(row_2026["ar1_forecast"])
        < float(row_2026["upper"])
    )


def test_charts_exist_and_nonempty() -> None:
    for name in [
        "01_dsci_trend.png",
        "02_drought_vs_yield.png",
        "03_precip_anomaly.png",
        "04_county_map.png",
    ]:
        path = CHARTS_DIR / name
        assert path.exists(), f"missing chart {name}"
        assert path.stat().st_size > 10_000, f"chart {name} suspiciously small"
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"{name} is not a PNG"


def test_data_source_json() -> None:
    provenance = json.loads(
        (PROCESSED_DIR / "data_source.json").read_text(encoding="utf-8")
    )
    assert provenance["synthetic"] is False
    assert provenance["row_counts"]["annual_rows"] == 26
    assert provenance["row_counts"]["county_year_rows"] == 5226
    assert "U.S. Drought Monitor" in json.dumps(provenance)


def test_readme_embeds_charts() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in [
        "01_dsci_trend.png",
        "02_drought_vs_yield.png",
        "03_precip_anomaly.png",
        "04_county_map.png",
    ]:
        assert f"outputs/charts/{name}" in readme, f"{name} not embedded in README"
    assert "screenshots/dashboard.png" in readme
