"""Tests for Day 20 chart builders — charts render from processed CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.make_charts import (
    chart_basket_cost,
    chart_category_divergence,
    chart_headline_yoy,
    chart_real_earnings,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

EXPECTED_CHARTS = [
    "01_headline_yoy.png",
    "02_category_divergence.png",
    "03_real_earnings.png",
    "04_basket_cost.png",
]


def _is_png(path: Path) -> bool:
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_all_four_charts_exist_and_are_png() -> None:
    for name in EXPECTED_CHARTS:
        path = CHARTS_DIR / name
        assert path.exists(), f"missing chart {name}"
        assert path.stat().st_size > 10_000
        assert _is_png(path)


def test_chart_headline_yoy_renders(tmp_path: Path) -> None:
    yoy_df = pd.read_csv(PROCESSED_DIR / "yoy_inflation.csv")
    out = chart_headline_yoy(yoy_df, tmp_path / "01.png")
    assert _is_png(out)
    assert out.stat().st_size > 10_000


def test_chart_category_divergence_renders(tmp_path: Path) -> None:
    cum_df = pd.read_csv(PROCESSED_DIR / "category_cumulative.csv")
    out = chart_category_divergence(cum_df, tmp_path / "02.png")
    assert _is_png(out)
    assert out.stat().st_size > 10_000


def test_chart_real_earnings_renders(tmp_path: Path) -> None:
    real_df = pd.read_csv(PROCESSED_DIR / "real_earnings.csv")
    out = chart_real_earnings(real_df, tmp_path / "03.png")
    assert _is_png(out)
    assert out.stat().st_size > 10_000


def test_chart_basket_cost_renders(tmp_path: Path) -> None:
    basket_df = pd.read_csv(PROCESSED_DIR / "basket_cost.csv")
    out = chart_basket_cost(basket_df, tmp_path / "04.png")
    assert _is_png(out)
    assert out.stat().st_size > 10_000


def test_charts_are_1280_wide() -> None:
    from PIL import Image

    for name in EXPECTED_CHARTS:
        with Image.open(CHARTS_DIR / name) as img:
            assert img.width == 1280, f"{name} is {img.width}px wide, expected 1280"
