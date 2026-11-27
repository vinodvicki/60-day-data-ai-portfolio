"""Tests for the Day 20 pipeline — raw/processed shape and offline replay.

The pipeline is exercised in --offline mode against the committed raw
cache (no network in tests). Live-fetch behaviour is covered by the
coder's verified run; these tests pin the shape and the frozen file list.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data_pipeline import (
    SERIES,
    build_processed,
    generate_synthetic,
    load_raw,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# Frozen processed-file list (plan.md §4) — the pipeline must write exactly
# these 8 files and nothing else.
EXPECTED_PROCESSED = {
    "monthly_panel.csv",
    "cpi_history.csv",
    "yoy_inflation.csv",
    "category_cumulative.csv",
    "real_earnings.csv",
    "basket_cost.csv",
    "summary_stats.csv",
    "data_source.json",
}


def test_all_raw_files_present() -> None:
    for series_id in SERIES:
        path = RAW_DIR / f"{series_id}.csv"
        assert path.exists(), f"missing raw file {path}"
        assert path.stat().st_size > 0
        assert path.stat().st_size < 1_000_000


def test_raw_files_are_small_in_total() -> None:
    total = sum(p.stat().st_size for p in RAW_DIR.glob("*.csv"))
    assert total < 5_000_000


def test_load_raw_parses_dates_and_values() -> None:
    frame = load_raw("CPIAUCSL")
    assert list(frame.columns) == ["date", "value"]
    assert frame["date"].iloc[0] == pd.Timestamp("1947-01-01")
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-10-01")
    # October 2025 is present as a row with a missing value (BLS did not
    # publish it) — the row must be kept, not dropped.
    oct25 = frame[frame["date"] == "2025-10-01"]
    assert len(oct25) == 1
    assert pd.isna(oct25["value"].iloc[0])


def test_processed_files_match_frozen_list() -> None:
    on_disk = {p.name for p in PROCESSED_DIR.iterdir()}
    assert on_disk == EXPECTED_PROCESSED


def test_monthly_panel_shape_and_window() -> None:
    panel = pd.read_csv(PROCESSED_DIR / "monthly_panel.csv", parse_dates=["date"])
    assert len(panel) == 248  # Mar 2006 - Oct 2026 incl. the missing Oct 2025
    assert panel["date"].iloc[0] == pd.Timestamp("2006-03-01")
    assert panel["date"].iloc[-1] == pd.Timestamp("2026-10-01")
    assert panel["headline_cpi"].isna().sum() == 1  # only Oct 2025
    assert panel["hourly_earnings"].isna().sum() == 0  # earnings has Oct 2025


def test_headline_values_match_raw() -> None:
    panel = pd.read_csv(PROCESSED_DIR / "monthly_panel.csv", parse_dates=["date"])
    oct26 = panel[panel["date"] == "2026-10-01"].iloc[0]
    assert oct26["headline_cpi"] == pytest.approx(337.476)
    assert oct26["hourly_earnings"] == pytest.approx(38.00)


def test_yoy_matches_hand_computation() -> None:
    # Sep 2026 YoY from the raw values: 336.298 / 324.245 - 1 = 3.717%.
    yoy_df = pd.read_csv(PROCESSED_DIR / "yoy_inflation.csv", parse_dates=["date"])
    sep26 = yoy_df[yoy_df["date"] == "2026-09-01"].iloc[0]
    assert sep26["headline_yoy_pct"] == pytest.approx(
        336.298 / 324.245 * 100 - 100, abs=1e-6
    )
    # Oct 2026 YoY is undefined (no Oct 2025 CPI).
    oct26 = yoy_df[yoy_df["date"] == "2026-10-01"].iloc[0]
    assert pd.isna(oct26["headline_yoy_pct"])


def test_basket_cost_matches_hand_computation() -> None:
    # Mar 2006 headline CPI 199.?? -> basket $100; Oct 2026 = 100*337.476/CPI(2006-03).
    basket = pd.read_csv(PROCESSED_DIR / "basket_cost.csv", parse_dates=["date"])
    panel = pd.read_csv(PROCESSED_DIR / "monthly_panel.csv", parse_dates=["date"])
    base_cpi = float(panel[panel["date"] == "2006-03-01"]["headline_cpi"].iloc[0])
    expected = 100.0 * 337.476 / base_cpi
    assert basket["basket_cost_usd"].iloc[-1] == pytest.approx(expected, abs=1e-9)
    assert basket["purchasing_power_usd"].iloc[-1] == pytest.approx(
        100.0 / 337.476, abs=1e-9
    )


def test_real_earnings_matches_hand_computation() -> None:
    real = pd.read_csv(PROCESSED_DIR / "real_earnings.csv", parse_dates=["date"])
    # Oct 2026: 38.00 / 337.476 * 100 = $11.26 in 1982-84 dollars.
    assert real["real_usd_per_hour"].iloc[-1] == pytest.approx(
        38.0 / 337.476 * 100, abs=1e-9
    )
    assert real["real_indexed"].iloc[0] == pytest.approx(100.0)


def test_summary_stats_row_per_series() -> None:
    summary = pd.read_csv(PROCESSED_DIR / "summary_stats.csv")
    assert len(summary) == 10
    assert set(summary["series"]) == {label for _s, label in SERIES.values()}


def test_data_source_json_records_provenance() -> None:
    meta = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    assert meta["synthetic"] is False
    assert meta["window_end"] == "2026-10-01"
    assert meta["n_months"] == 248
    assert "FRED" in meta["source"]
    assert "Bureau of Labor Statistics" in meta["attribution"]


def test_offline_rebuild_is_reproducible() -> None:
    frames = {sid: load_raw(sid) for sid in SERIES}
    tables = build_processed(frames, synthetic=False)
    panel = tables["monthly_panel"]
    assert isinstance(panel, pd.DataFrame)
    on_disk = pd.read_csv(PROCESSED_DIR / "monthly_panel.csv", parse_dates=["date"])
    pd.testing.assert_frame_equal(
        panel.reset_index(drop=True), on_disk, check_dtype=False
    )


def test_synthetic_fallback_builds() -> None:
    frames = generate_synthetic(seed=42)
    tables = build_processed(frames, synthetic=True)
    panel = tables["monthly_panel"]
    assert isinstance(panel, pd.DataFrame)
    assert len(panel) == 248
    meta = tables["data_source"]
    assert isinstance(meta, dict)
    assert meta["synthetic"] is True
