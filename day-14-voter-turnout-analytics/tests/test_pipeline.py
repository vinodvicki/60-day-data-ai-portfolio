"""Tests for Day 14 — Voter Turnout Analytics.

Fixture tests cover the pure turnout functions; file tests verify the
committed tables against the plan's rules (decider rules §2.0,
recompute within 0.05 pp, no EAVS figure in any turnout table,
flagged outliers retained, cycle types never mixed without labelling,
offline reproducibility with tolerance — Day 9 lesson).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

# The day folder must be on sys.path before the src imports: the
# orchestrator runs pytest from the portfolio root (Day 12 pattern).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_pipeline import (
    clean_turnout,
    generate_synthetic,
    load_turnout_csv,
    recompute_check,
    run,
)
from src.turnout import (
    correlate,
    cycle_type,
    felon_share_vap,
    flag_outliers,
    overseas_share_vep,
    parse_column5,
    pp_change,
    recompute_vep,
    skewness,
    top_bottom,
    vap_turnout,
    vep_turnout,
)

PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


def _long() -> pd.DataFrame:
    """Load the committed long table."""
    return pd.read_csv(PROC / "turnout_long.csv")


def _fixture_frame() -> pd.DataFrame:
    """Small fixture frame with a planted outlier and a planted mismatch."""
    return pd.DataFrame(
        {
            "year": [2024, 2024, 2024, 2020, 2020],
            "state": ["Alpha", "Beta", "Gamma", "Alpha", "Beta"],
            "state_abv": ["AA", "BB", "GG", "AA", "BB"],
            "is_national": [False] * 5,
            "cycle_type": ["presidential"] * 5,
            "total_ballots_counted": [1000.0, 2000.0, 3000.0, 900.0, 1800.0],
            "vep": [2000.0, 2500.0, 3000.0, 2000.0, 2500.0],
            "vep_turnout_rate": [50.0, 80.0, 100.0, 45.0, 72.0],
            "vap_turnout_rate": [40.0, 70.0, 90.0, 36.0, 60.0],
        }
    )


def test_parse_column5_url() -> None:
    """A source URL is stored as SOURCE_URL, never parsed as a vote count."""
    url, votes = parse_column5(
        "https://www.eac.gov/sites/default/files/2023-06/2022_EAVS_Report_508c.pdf"
    )
    assert url is not None and url.startswith("https://")
    assert votes is None


def test_parse_column5_digits() -> None:
    """An all-digits value is a vote count, not a URL."""
    url, votes = parse_column5("117,069,210")
    assert url is None
    assert votes == 117069210.0


def test_parse_column5_blank() -> None:
    """A blank value is missing in both fields, never zero."""
    url, votes = parse_column5("")
    assert url is None and votes is None
    url, votes = parse_column5(None)
    assert url is None and votes is None


def test_2020_row_url_never_a_vote_count() -> None:
    """Real 2020 rows: column 5 holds URLs; no 2020 row yields a vote count."""
    raw = load_turnout_csv(RAW / "Turnout_1980_2022_v1.2.csv")
    rows_2020 = raw[raw["YEAR"] == "2020"]
    assert len(rows_2020) == 52
    for value in rows_2020["VOTE_FOR_HIGHEST_OFFICE"]:
        _, votes = parse_column5(str(value))
        assert votes is None


def test_year_2024_added_on_concatenation() -> None:
    """The 2024 file has no YEAR column; concatenation adds YEAR=2024."""
    long, _counts = clean_turnout(
        load_turnout_csv(RAW / "Turnout_1980_2022_v1.2.csv"),
        load_turnout_csv(RAW / "Turnout_2024G_v0.4.csv"),
    )
    assert set(long["year"].unique()) == set(range(1980, 2025, 2))
    assert int((long["year"] == 2024).sum()) == 52
    assert len(long) == 1196


def test_vep_recompute_matches_file_rate() -> None:
    """Recomputed VEP turnout matches the file rate within 0.05 pp on every row."""
    long = _long()
    both = long.dropna(subset=["total_ballots_counted", "vep", "vep_turnout_rate"])
    diffs = (both["vep_turnout_recomputed"] - both["vep_turnout_rate"]).abs()
    assert len(both) == 987
    assert float(diffs.max()) <= 0.05


def test_spot_check_2024_us_vep_turnout() -> None:
    """2024 US VEP turnout: 156,766,239 / 243,803,423 = 64.30% from the committed CSVs."""
    long = _long()
    row = long[(long["year"] == 2024) & (long["state_abv"] == "US")].iloc[0]
    assert float(row["total_ballots_counted"]) == 156766239.0
    assert float(row["vep"]) == 243803423.0
    assert vep_turnout(156766239.0, 243803423.0) == pytest.approx(64.30, abs=0.01)
    assert float(row["vep_turnout_rate"]) == 64.30


def test_recompute_check_raises_on_planted_mismatch() -> None:
    """A recompute gap over 0.05 pp fails the build loudly (plan §3.3)."""
    long = _long()
    planted = long.copy()
    mask = (planted["year"] == 2024) & (planted["state_abv"] == "WI")
    planted.loc[mask, "vep_turnout_rate"] = 77.00  # recomputed is 76.66
    with pytest.raises(ValueError, match="Recompute check failed"):
        recompute_check(planted)


def test_vap_turnout_below_vep_turnout() -> None:
    """VAP turnout is lower than VEP turnout wherever both exist (plan §4.1)."""
    long = _long()
    both = long.dropna(subset=["vap_turnout_rate", "vep_turnout_rate"])
    assert len(both) > 900
    assert bool((both["vap_turnout_rate"] < both["vep_turnout_rate"]).all())


def test_cycle_type_derivation() -> None:
    """2024 is presidential, 2022 is midterm (plan §2.0 Rule 4)."""
    assert cycle_type(2024) == "presidential"
    assert cycle_type(2020) == "presidential"
    assert cycle_type(2022) == "midterm"
    assert cycle_type(2018) == "midterm"


def test_pp_change_within_cycle_type_only() -> None:
    """pp change compares 2024 with 2020 (both presidential), never with 2022."""
    assert pp_change(64.30, 65.99) == pytest.approx(-1.69, abs=0.01)
    state_2024 = pd.read_csv(PROC / "state_2024.csv")
    long = _long()
    for _, row in state_2024[~state_2024["is_national"].astype(bool)].iterrows():
        prior = long[(long["year"] == 2020) & (long["state_abv"] == row["state_abv"])]
        if len(prior) and not pd.isna(prior.iloc[0]["vep_turnout_rate"]):
            expected = float(row["vep_turnout_rate"]) - float(
                prior.iloc[0]["vep_turnout_rate"]
            )
            assert float(row["pp_change_vs_2020"]) == pytest.approx(expected, abs=0.01)


def test_pre_2010_null_ballots_stay_null() -> None:
    """Pre-2010 state ballots are null by design and stay null — never filled."""
    long = _long()
    early = long[(long["year"] < 2010) & (~long["is_national"])]
    assert int(early["total_ballots_counted"].isna().sum()) == 200
    national_early = long[(long["year"] < 1998) & (long["is_national"])]
    assert national_early["vep_turnout_rate"].isna().all()


def test_vep_reconciliation_flags_planted_mismatch() -> None:
    """VEP arithmetic that does not reconcile is flagged (plan §3.2 rule 5)."""
    # Correct row: VAP 100000, 10% noncitizen, 1000 felons, 0 overseas -> VEP 89000.
    assert recompute_vep(100000.0, 10.0, 1000.0, 0.0) == pytest.approx(89000.0)
    # Planted mismatch: file VEP 80000 vs recomputed 89000 -> 11.25% off.
    rel = abs(89000.0 - 80000.0) / 80000.0
    assert rel > 0.005
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    assert record["cleaning_counts"]["vep_reconciliation_flagged_rows"] == 0
    assert record["cleaning_counts"]["vep_reconciliation_max_rel_diff"] < 0.005


def test_outlier_flagging_fixture() -> None:
    """A planted outlier is flagged by the 1.5xIQR fence (plan §2.0 Rule 3)."""
    series = pd.Series([50.0, 51.0, 52.0, 53.0, 54.0, 52.0, 51.0, 50.0, 90.0])
    flagged = flag_outliers(series)
    assert len(flagged) == 1
    assert float(flagged.iloc[0]["value"]) == 90.0
    assert str(flagged.iloc[0]["rule"]) in ("iqr", "iqr+z", "z")


def test_flagged_outliers_remain_in_tables() -> None:
    """Every flagged state stays in turnout_long.csv and the 2024 ranking."""
    long = _long()
    outliers = pd.read_csv(PROC / "outliers.csv")
    assert len(outliers) == 5
    for _, row in outliers.iterrows():
        match = long[
            (long["year"] == int(row["year"])) & (long["state_abv"] == row["state_abv"])
        ]
        assert len(match) == 1
        assert float(match.iloc[0]["vep_turnout_rate"]) == pytest.approx(
            float(row["vep_turnout_rate"]), abs=0.01
        )


def test_correlate_returns_n_r_p_and_handles_constant() -> None:
    """correlate() returns n, r, p on fixtures and does not crash on a constant series."""
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([2.0, 4.0, 5.0, 4.0, 5.0])
    result = correlate(x, y)
    assert result["n"] == 5
    assert result["pearson_r"] is not None and result["pearson_p"] is not None
    assert result["spearman_r"] is not None and result["spearman_p"] is not None
    constant = correlate(pd.Series([3.0, 3.0, 3.0, 3.0]), y)
    assert constant["n"] == 4
    assert constant["pearson_r"] is None and constant["spearman_r"] is None


def test_correlations_table_has_n_r_p() -> None:
    """correlations.csv carries n, r and p for every indicator (plan §4.3)."""
    corr = pd.read_csv(PROC / "correlations.csv")
    assert list(corr["indicator"]) == [
        "noncitizen_pct",
        "felon_share_vap",
        "overseas_share_vep",
    ]
    assert set(corr["scope"]) == {"2024_states"}
    assert int(corr.loc[corr["indicator"] == "noncitizen_pct", "n"].iloc[0]) == 51
    assert int(corr.loc[corr["indicator"] == "overseas_share_vep", "n"].iloc[0]) == 0


def test_top_bottom_deterministic_tie_break() -> None:
    """Ties break by state abbreviation, so the ranking is reproducible."""
    frame = pd.DataFrame(
        {"state_abv": ["ZZ", "AA", "MM"], "vep_turnout_rate": [70.0, 70.0, 60.0]}
    )
    top, bottom = top_bottom(frame, "vep_turnout_rate", 2)
    assert list(top["state_abv"]) == ["AA", "ZZ"]
    assert list(bottom["state_abv"]) == ["MM", "AA"]


def test_state_2024_has_51_jurisdictions() -> None:
    """state_2024.csv: 51 jurisdictions ranked, US total flagged separately."""
    state_2024 = pd.read_csv(PROC / "state_2024.csv")
    assert len(state_2024) == 52
    states = state_2024[~state_2024["is_national"].astype(bool)]
    assert len(states) == 51
    assert set(states["rank_vep"].astype(int)) == set(range(1, 52))
    us = state_2024[state_2024["is_national"].astype(bool)]
    assert len(us) == 1
    assert float(us.iloc[0]["vep_turnout_rate"]) == 64.30
    assert pd.isna(us.iloc[0]["rank_vep"])


def test_sql_vs_pandas_agreement() -> None:
    """SQL check (§4.5): SQLite and pandas agree on cycle-type means and the top state."""
    long = _long()
    states = long[~long["is_national"]]
    pandas_means = states.groupby("cycle_type")["vep_turnout_rate"].mean()
    pandas_top = (
        states[states["year"] == 2024]
        .sort_values(["vep_turnout_rate", "state_abv"], ascending=[False, True])
        .iloc[0]
    )
    conn = sqlite3.connect(":memory:")
    states.to_sql("turnout", conn, index=False)
    cursor = conn.execute(
        "SELECT cycle_type, AVG(vep_turnout_rate) FROM turnout "
        "WHERE vep_turnout_rate IS NOT NULL GROUP BY cycle_type"
    )
    sql_means = {row[0]: row[1] for row in cursor.fetchall()}
    for cycle in ("presidential", "midterm"):
        assert sql_means[cycle] == pytest.approx(float(pandas_means[cycle]), rel=1e-9)
    sql_top = conn.execute(
        "SELECT state_abv, vep_turnout_rate FROM turnout WHERE year = 2024 "
        "ORDER BY vep_turnout_rate DESC, state_abv ASC LIMIT 1"
    ).fetchone()
    assert sql_top is not None
    assert sql_top[0] == str(pandas_top["state_abv"])
    assert sql_top[1] == pytest.approx(float(pandas_top["vep_turnout_rate"]), rel=1e-9)
    conn.close()


def test_offline_run_does_not_clobber_data_source() -> None:
    """Offline run skips writing data_source.json when a live record exists (§3.5)."""
    path = PROC / "data_source.json"
    before = path.read_bytes()
    run("offline")
    assert path.read_bytes() == before


def test_offline_reproduction_within_tolerance() -> None:
    """Offline reproduction matches the committed tables within tolerance (Day 9 lesson)."""
    before = pd.read_csv(PROC / "turnout_long.csv")
    run("offline")
    after = pd.read_csv(PROC / "turnout_long.csv")
    assert len(before) == len(after)
    for column in ("vep_turnout_rate", "vap_turnout_rate", "vep_turnout_recomputed"):
        diff = (before[column] - after[column]).abs()
        assert float(diff.max()) <= 0.01


def test_synthetic_never_overwrites_live_files() -> None:
    """The synthetic fallback is deterministic and never touches the real CSVs."""
    first = generate_synthetic(seed=42)
    second = generate_synthetic(seed=42)
    assert len(first) == 1196
    assert first.equals(second)
    assert bool((first["vap"] > first["vep"]).all())
    import hashlib

    def _hashes() -> dict[str, str]:
        return {
            name: hashlib.sha256((RAW / name).read_bytes()).hexdigest()
            for name in ("Turnout_1980_2022_v1.2.csv", "Turnout_2024G_v0.4.csv")
        }

    hashes_before = _hashes()
    generate_synthetic(seed=42)
    assert _hashes() == hashes_before


def test_data_size_rule_committed_files() -> None:
    """No committed file over 1 MB; committed data/ under 5 MB (plan §3.4)."""
    ignored_names = {
        "cb_2024_us_state_500k.zip",
        "2024_EAVS_for_Public_Release_nolabel_V1_csv.zip",
    }
    ignored_dirs = {"shapefile", "eavs"}
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        if path.name in ignored_names or any(
            part in ignored_dirs for part in path.parts
        ):
            continue
        assert path.stat().st_size < 1_000_000, f"{path} is over 1 MB"
        total += path.stat().st_size
    assert total < 5_000_000


def test_gitignore_matches_plan() -> None:
    """Shapefile + EAVS excluded; the two UF CSVs and data/ itself NOT excluded (§3.4)."""
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "cb_2024_us_state_500k.zip" in text
    assert "shapefile/" in text
    assert "2024_EAVS_for_Public_Release_nolabel_V1_csv.zip" in text
    assert "eavs/" in text
    assert "Turnout_1980_2022_v1.2.csv" not in text
    assert "Turnout_2024G_v0.4.csv" not in text
    lines = [line.strip() for line in text.splitlines()]
    assert "data/" not in lines and "data" not in lines


def test_no_eavs_figure_in_committed_turnout_tables() -> None:
    """EAVS is a cross-check only — no EAVS figure appears in any committed turnout table."""
    eavs_only_values = ("16164330", "3240754", "1122179", "11488820")
    uf_values = ("16140044", "3241120")
    for name in (
        "turnout_long.csv",
        "national_series.csv",
        "state_2024.csv",
        "correlations.csv",
        "outliers.csv",
    ):
        text = (PROC / name).read_text(encoding="utf-8")
        for value in eavs_only_values:
            assert value not in text, f"EAVS value {value} leaked into {name}"
    state_2024 = (PROC / "state_2024.csv").read_text(encoding="utf-8")
    for value in uf_values:
        assert value in state_2024


def test_skewness_reported_per_cycle_type() -> None:
    """Skewness is reported per cycle type (a number, not a judgement — §4.4)."""
    long = _long()
    pres = long[(~long["is_national"]) & (long["cycle_type"] == "presidential")]
    mid = long[(~long["is_national"]) & (long["cycle_type"] == "midterm")]
    assert skewness(pres["vep_turnout_rate"]) == pytest.approx(-0.27, abs=0.01)
    assert skewness(mid["vep_turnout_rate"]) == pytest.approx(0.06, abs=0.01)
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    assert record["derived_tables"]["skewness_presidential_pooled"] == pytest.approx(
        -0.27, abs=0.01
    )


def test_charts_exist() -> None:
    """Exactly 4 charts, all non-empty PNGs (plan §7)."""
    charts = sorted((ROOT / "outputs" / "charts").glob("*.png"))
    assert len(charts) == 4
    assert [path.name for path in charts] == [
        "01_turnout_map_2024.png",
        "02_turnout_over_time.png",
        "03_state_ranking_2024.png",
        "04_demographic_scatter.png",
    ]
    for path in charts:
        assert path.stat().st_size > 10_000


def test_chart_03_legend_outside_data_area() -> None:
    """Regression test for D-1: the chart-03 legend must sit outside the
    data area and must not overlap any bar label (Iowa's "70.95%
    (rank 10)" was partly hidden behind the legend)."""
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    from src.make_charts import _build_chart_03_figure

    fig, axes = _build_chart_03_figure()
    try:
        fig.canvas.draw()
        canvas = fig.canvas
        assert isinstance(canvas, FigureCanvasAgg)
        renderer = canvas.get_renderer()
        for ax in axes:
            legend = ax.get_legend()
            assert legend is not None
            legend_box = legend.get_window_extent(renderer)
            axes_box = ax.get_window_extent()
            assert not legend_box.overlaps(
                axes_box
            ), "chart-03 legend overlaps the data area"
            for text in ax.texts:
                assert not text.get_window_extent(renderer).overlaps(
                    legend_box
                ), f"chart-03 legend overlaps the label {text.get_text()!r}"
    finally:
        plt.close(fig)


def test_helper_functions() -> None:
    """Small pure helpers behave: shares, overseas share, recompute VEP."""
    assert felon_share_vap(1000.0, 100000.0) == pytest.approx(0.01)
    assert felon_share_vap(1000.0, 0.0) is None
    assert overseas_share_vep(3000.0, 150000.0) == pytest.approx(0.02)
    assert overseas_share_vep(None, 150000.0) is None
    assert recompute_vep(100000.0, 10.0, 1000.0, 500.0) == pytest.approx(89500.0)
    assert vap_turnout(50000.0, 100000.0) == pytest.approx(50.0)
    assert vep_turnout(50000.0, 0.0) is None


def test_fixture_values() -> None:
    """Fixture frame sanity: values used by the other fixture tests."""
    frame = _fixture_frame()
    assert vep_turnout(1000.0, 2000.0) == pytest.approx(50.0)
    assert len(frame) == 5
