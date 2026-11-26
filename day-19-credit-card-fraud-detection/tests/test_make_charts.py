"""Day 19 tests for src/make_charts.py — all 4 charts from processed CSVs.

Charts are drawn into a temporary directory (monkeypatched CHARTS_DIR)
so the test never overwrites the committed PNGs. The builders read
processed CSVs only, so these tests also run in CI without the raw file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src import make_charts as mc

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"


def _is_png(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(8) == b"\x89PNG\r\n\x1a\n"


def test_all_four_charts_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each chart function writes a non-empty PNG into the charts dir."""
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    for build in (
        mc.chart_01_class_imbalance,
        mc.chart_02_pr_curves,
        mc.chart_03_threshold_tradeoff,
        mc.chart_04_cost_curve,
    ):
        path = build()
        assert path.exists()
        assert path.stat().st_size > 10_000
        assert _is_png(path)


def test_amount_hist_covers_both_classes() -> None:
    """The committed histogram has 40 bins x 2 classes and sums to the data."""
    hist = pd.read_csv(PROCESSED_DIR / "amount_hist.csv")
    assert len(hist) == 80
    totals = hist.groupby("Class")["count"].sum()
    # Amount > 0 rows only: 284,807 minus the zero-Amount rows.
    assert int(totals.loc[0]) + int(totals.loc[1]) <= 284_807
    assert int(totals.loc[1]) <= 492
    assert int(totals.loc[1]) > 400  # most frauds have Amount > 0
    assert bool((hist["bin_right"] > hist["bin_left"]).all())


def test_main_builds_all_charts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """make_charts.main() returns 0 and writes all 4 PNGs."""
    monkeypatch.setattr(mc, "CHARTS_DIR", tmp_path)
    assert mc.main([]) == 0
    names = {path.name for path in tmp_path.iterdir()}
    assert names == {
        "01_class_imbalance.png",
        "02_pr_curves.png",
        "03_threshold_tradeoff.png",
        "04_cost_curve.png",
    }
