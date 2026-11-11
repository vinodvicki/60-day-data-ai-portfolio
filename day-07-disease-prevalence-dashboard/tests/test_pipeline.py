"""Day 7 — Disease Prevalence Dashboard: offline pytest suite.

Covers metrics.py (pure math), the committed CSVs matching
data_source.json, the population-weighted roll-up (hand-checked), the
matched-county change table, the Kentucky/Pennsylvania coverage gap, the
suppressed Loving County row, the offline path never clobbering the live
record (Day 5/6 lesson), and the synthetic fallback staying labelled.
Runs from the repo root and from inside the day folder.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline as pipeline
from src.metrics import (
    estimated_cases,
    median_ci_width,
    spread_stats,
    top_bottom,
    weighted_rate,
    yoy_change,
)

PROCESSED = ROOT / "data" / "processed"
SLUGS = {
    "DIABETES": "diabetes",
    "COPD": "copd",
    "CASTHMA": "asthma",
    "CHD": "chd",
    "STROKE": "stroke",
    "OBESITY": "obesity",
}


def _record() -> dict:
    return json.loads((PROCESSED / "data_source.json").read_text())


def _prevalence(measure: str) -> pd.DataFrame:
    return pd.read_csv(
        PROCESSED / f"prevalence_{SLUGS[measure]}.csv",
        dtype={"year": str, "locationid": str},
    )


# ---------------------------------------------------------------------------
# (1) Docs exist (replaces the scaffold smoke test)
# ---------------------------------------------------------------------------


def test_readme_exists_and_nonempty():
    assert (ROOT / "README.md").read_text().strip() != ""


def test_data_readme_exists():
    assert (ROOT / "data" / "README.md").exists()


# ---------------------------------------------------------------------------
# (2) Pure metrics — hand-checked
# ---------------------------------------------------------------------------


def test_estimated_cases_claiborne_hand_check():
    # Claiborne parish, LA, diabetes 2023 (verified probe value):
    # 22.8% of 11,034 adults = 2,515.752 -> 2,516.
    assert estimated_cases(22.8, 11034) == 2516
    assert estimated_cases(10.0, 1000) == 100


def test_weighted_rate_hand_check_and_beats_naive_mean():
    # Two counties: 10% of 1,000 adults + 20% of 2,000 adults.
    # Weighted: 100 * (100 + 400) / 3000 = 16.67%, naive mean = 15%.
    assert weighted_rate(500, 3000) == pytest.approx(16.6667, abs=0.001)
    assert weighted_rate(500, 3000) != pytest.approx(15.0)


def test_weighted_rate_rejects_zero_population():
    with pytest.raises(ValueError):
        weighted_rate(10, 0)


def test_yoy_change_points_and_percent():
    pp, pct = yoy_change(10.0, 12.0)
    assert pp == pytest.approx(2.0)
    assert pct == pytest.approx(20.0)
    pp, pct = yoy_change(12.0, 11.0)
    assert pp == pytest.approx(-1.0)
    assert pct == pytest.approx(-8.333, abs=0.001)


def test_spread_stats():
    stats = spread_stats(pd.Series([1.0, 2.0, 3.0, 4.0, 100.0]))
    assert stats["n"] == 5
    assert stats["min"] == 1.0
    assert stats["max"] == 100.0
    assert stats["range"] == 99.0
    assert stats["median"] == 3.0
    assert stats["iqr"] == pytest.approx(2.0)


def test_median_ci_width():
    assert median_ci_width(pd.Series([10.0, 20.0]), pd.Series([13.0, 24.0])) == 3.5


def test_top_bottom_ordering():
    df = pd.DataFrame(
        {
            "locationname": ["B", "A", "C"],
            "data_value": [5.0, 9.0, 1.0],
        }
    )
    top, bottom = top_bottom(df, "data_value", n=2)
    assert list(top["locationname"]) == ["A", "B"]
    assert list(bottom["locationname"]) == ["C", "B"]


# ---------------------------------------------------------------------------
# (3) Committed data matches the provenance record
# ---------------------------------------------------------------------------


def test_no_us_rows_in_prevalence_csvs():
    for measure in SLUGS:
        df = _prevalence(measure)
        assert "US" not in set(df["stateabbr"]), measure


def test_row_counts_match_data_source():
    record = _record()
    for measure in SLUGS:
        df = _prevalence(measure)
        # Fetched rows minus the US aggregate row minus the suppressed row.
        for year in ("2022", "2023"):
            fetched = record["row_counts"][f"{measure}_{year}"]
            expected = (
                fetched
                - 1
                - record["rows_without_published_value"][f"{measure}_{year}"]
            )
            assert len(df[df["year"] == year]) == expected, (measure, year)


def test_no_missing_values_and_geo_in_range():
    for measure in SLUGS:
        df = _prevalence(measure)
        assert df["data_value"].notna().all()
        assert df["totalpop18plus"].gt(0).all()
        assert df["est_cases"].ge(0).all()
        assert df["lon"].between(-180, -60).all()
        assert df["lat"].between(18, 72).all()


def test_state_rate_matches_hand_computation():
    # Louisiana diabetes 2023, recomputed from the county CSV:
    # 100 * sum(est_cases) / sum(totalpop18plus).
    prev = _prevalence("DIABETES")
    la = prev[(prev["year"] == "2023") & (prev["stateabbr"] == "LA")]
    hand = 100 * la["est_cases"].sum() / la["totalpop18plus"].sum()
    state = pd.read_csv(PROCESSED / "state_prevalence.csv", dtype={"year": str})
    row = state[
        (state["measureid"] == "DIABETES")
        & (state["year"] == "2023")
        & (state["stateabbr"] == "LA")
    ].iloc[0]
    assert row["state_rate"] == pytest.approx(hand, abs=0.01)
    # And it must differ from the naive mean of county percentages.
    assert row["state_rate"] != pytest.approx(la["data_value"].mean(), abs=0.01)


def test_change_rows_are_consistent():
    record = _record()
    for measure, slug in SLUGS.items():
        ch = pd.read_csv(PROCESSED / f"change_{slug}.csv")
        assert len(ch) == record["unmatched_counties"][measure]["matched"]
        assert (
            (ch["value_2023"] - ch["value_2022"]) - ch["pp_change"]
        ).abs().max() < 0.011


def test_ky_pa_absent_2023_present_2022():
    # Coverage gap verified against the live API: the 2025 release has no
    # rows for Kentucky or Pennsylvania (all six measures).
    for measure in SLUGS:
        df = _prevalence(measure)
        assert set(df[df["year"] == "2023"]["stateabbr"]) == set(
            df[df["year"] == "2022"]["stateabbr"]
        ) - {"KY", "PA"}


def test_suppressed_loving_county_row():
    record = _record()
    assert record["rows_without_published_value"]["DIABETES_2023"] == 1
    assert record["footnote_star_rows"]["DIABETES_2023"] == 1
    df = _prevalence("DIABETES")
    assert "48301" not in set(df[df["year"] == "2023"]["locationid"])
    assert "48301" in set(df[df["year"] == "2022"]["locationid"])


def test_data_size_limits():
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if path.is_file():
            assert path.stat().st_size <= 1_000_000, path
            total += path.stat().st_size
    assert total <= 5_000_000


def test_charts_exist_and_nonempty():
    for name in (
        "01_state_ranking.png",
        "02_county_distribution.png",
        "03_change_2022_2023.png",
        "04_measure_comparison.png",
    ):
        path = ROOT / "outputs" / "charts" / name
        assert path.exists() and path.stat().st_size > 10_000, name


def test_state_geojson_covers_all_states():
    # The dashboard choropleth uses this bundled file (not the Plotly CDN
    # topojson, which returns 403 in this environment). 51 features: the
    # 50 states + DC, no Puerto Rico.
    geo = json.loads((PROCESSED / "us_states.geojson").read_text())
    assert geo["type"] == "FeatureCollection"
    abbrs = {f["properties"]["abbr"] for f in geo["features"]}
    assert len(geo["features"]) == 51
    state = pd.read_csv(PROCESSED / "state_prevalence.csv", dtype={"year": str})
    assert abbrs == set(state["stateabbr"].unique())
    assert "PR" not in abbrs


def test_state_map_renders_all_states():
    import matplotlib.pyplot as plt

    from src.state_map import state_map_figure

    geo = json.loads((PROCESSED / "us_states.geojson").read_text())
    state = pd.read_csv(PROCESSED / "state_prevalence.csv", dtype={"year": str})
    for year in ("2022", "2023"):
        sy = state[(state["measureid"] == "DIABETES") & (state["year"] == year)]
        fig = state_map_figure(sy, geo, f"Diabetes {year}")
        patches = fig.axes[0].collections[0].get_paths()
        assert len(patches) == sum(
            (
                len(f["geometry"]["coordinates"])
                if f["geometry"]["type"] == "Polygon"
                else sum(len(p) for p in f["geometry"]["coordinates"])
            )
            for f in geo["features"]
        )
        plt.close(fig)


# ---------------------------------------------------------------------------
# (4) Offline and synthetic paths (Day 5/6 lessons)
# ---------------------------------------------------------------------------


def test_offline_does_not_clobber_live_data_source(tmp_path, monkeypatch):
    work = tmp_path / "processed"
    shutil.copytree(PROCESSED, work)
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", work)
    before = (work / "data_source.json").read_bytes()
    pipeline.run_offline()
    after = (work / "data_source.json").read_bytes()
    assert before == after
    assert json.loads(after)["source"] == "live"


def test_offline_reproduces_state_table(tmp_path, monkeypatch):
    work = tmp_path / "processed"
    shutil.copytree(PROCESSED, work)
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", work)
    before = pd.read_csv(work / "state_prevalence.csv", dtype={"year": str})
    pipeline.run_offline()
    after = pd.read_csv(work / "state_prevalence.csv", dtype={"year": str})
    pd.testing.assert_frame_equal(before, after)


def test_synthetic_is_labelled_and_leaves_live_files_alone(tmp_path, monkeypatch):
    live_before = (PROCESSED / "data_source.json").read_bytes()
    work = tmp_path / "processed"
    raw = tmp_path / "raw"
    work.mkdir()
    raw.mkdir()
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", work)
    monkeypatch.setattr(pipeline, "RAW_DIR", raw)
    record = pipeline.run_synthetic()
    assert record["source"] == "synthetic"
    assert record["synthetic"] is True and record["seed"] == 42
    assert (PROCESSED / "data_source.json").read_bytes() == live_before
    assert (raw / "places_synthetic.json").exists()
