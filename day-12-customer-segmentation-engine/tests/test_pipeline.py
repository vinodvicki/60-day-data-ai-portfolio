"""Tests for Day 12 — Customer Segmentation Engine.

Covers cleaning rules, RFM definitions, percentile-rank scoring, the
KMeans decider (plan §2.0), k-selection, segment naming, SBC quadrants,
the agreement rate, one-action-per-segment, the SQL check, the
offline-does-not-clobber-data_source regression and the data-size rule.
Fixtures are small synthetic frames; the live numbers are asserted
from the committed CSVs.
"""

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.actions import action_for, build_actions, gbp_at_stake
from src.clustering import (
    PROTOTYPES,
    agreement_rate,
    choose_k,
    classify_sbc,
    cluster_customers,
    name_segments,
    sbc_stats,
    select_k,
)
from src.data_pipeline import (
    ADJUSTMENT_DESCRIPTIONS,
    ADJUSTMENT_STOCK_CODES,
    clean_transactions,
    generate_synthetic,
    run_offline,
)
from src.rfm import compute_rfm, line_revenue, score_rfm

PROC = ROOT / "data" / "processed"
SNAPSHOT = pd.Timestamp("2011-12-10")


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "InvoiceNo": ["1001", "C1002", "1003", "1004", "1005", "1006", "1007"],
            "StockCode": ["A1", "A1", "POST", "A2", "A2", "A3", "A3"],
            "Description": [
                "Widget",
                "Widget",
                "POSTAGE",
                "Gadget",
                "Gadget",
                None,
                "Thing",
            ],
            "Quantity": [5, -2, 1, 0, 3, 2, 4],
            "InvoiceDate": ["2010-12-06 10:00"] * 7,
            "UnitPrice": [2.0, 2.0, 1.0, 0.0, 3.0, 1.5, 1.5],
            "CustomerID": [1.0, 1.0, np.nan, 2.0, np.nan, 3.0, 3.0],
            "Country": ["United Kingdom"] * 7,
        }
    )


def _cleaned_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": [1, 1, 1, 2, 3],
            "invoice_no": ["1001", "1002", "1001", "1003", "1004"],
            "invoice_date": pd.to_datetime(
                [
                    "2011-12-09 10:00",
                    "2011-12-05 10:00",
                    "2011-12-09 11:00",
                    "2011-11-01 10:00",
                    "2010-12-01 10:00",
                ]
            ),
            "line_revenue": [10.0, 20.0, 5.0, 100.0, 7.0],
        }
    )


def test_revenue_is_quantity_times_price():
    assert line_revenue(5, 2.0) == 10.0
    assert line_revenue(3, 1.5) == 4.5


def test_cancellations_excluded():
    cleaned, counts = clean_transactions(_raw_frame())
    assert counts["n_cancelled_rows"] == 1
    assert counts["n_cancelled_invoices"] == 1
    assert not cleaned["invoice_no"].str.startswith("C").any()


def test_nonpositive_quantity_and_price_excluded():
    _, counts = clean_transactions(_raw_frame())
    assert counts["n_nonpositive_quantity"] == 1  # row 1004, qty 0
    # Price is counted after the quantity step, so row 1004 (price 0) is
    # already gone and no further row has price <= 0.
    assert counts["n_nonpositive_price"] == 0
    cleaned, _ = clean_transactions(_raw_frame())
    assert (cleaned["quantity"] > 0).all()
    assert (cleaned["unit_price"] > 0).all()


def test_adjustment_codes_excluded():
    _, counts = clean_transactions(_raw_frame())
    assert counts["n_adjustment_rows"] == 1  # POST / POSTAGE row
    cleaned, _ = clean_transactions(_raw_frame())
    assert not cleaned["stock_code"].isin(ADJUSTMENT_STOCK_CODES).any()
    assert not cleaned["description"].str.upper().isin(ADJUSTMENT_DESCRIPTIONS).any()


def test_missing_customer_id_excluded_from_rfm_but_counted():
    cleaned, counts = clean_transactions(_raw_frame())
    # Row 1005 (qty 3 × £3.00) has no CustomerID: kept in the cleaned
    # frame, counted, and excluded from RFM by compute_rfm.
    assert counts["n_missing_customer_id"] == 1
    assert counts["revenue_missing_customer_gbp"] == pytest.approx(9.0)
    rfm = compute_rfm(cleaned, SNAPSHOT)
    assert 1 in rfm["customer_id"].tolist()
    assert len(rfm) == 2  # customers 1 and 3 only
    assert counts["cleaned_revenue_gbp"] == pytest.approx(10.0 + 9.0 + 6.0)


def test_snapshot_is_max_date_plus_one_day():
    _cleaned, counts = clean_transactions(_raw_frame())
    max_date = pd.Timestamp(counts["confirmed_date_range"][1])
    # Fixture max date is 2010-12-06 10:00 → snapshot 2010-12-07.
    assert (max_date.normalize() + pd.Timedelta(days=1)) == pd.Timestamp("2010-12-07")


def test_rfm_recency_frequency_monetary_on_fixtures():
    rfm = compute_rfm(_cleaned_frame(), SNAPSHOT)
    c1 = rfm[rfm["customer_id"] == 1].iloc[0]
    # Last seen 2011-12-09 → Recency 1 (calendar-date difference).
    assert int(c1["recency_days"]) == 1
    # Two distinct invoices (1001 counted once despite two lines).
    assert int(c1["frequency"]) == 2
    assert float(c1["monetary_gbp"]) == pytest.approx(35.0)
    c3 = rfm[rfm["customer_id"] == 3].iloc[0]
    assert int(c3["recency_days"]) == 374
    assert int(c3["frequency"]) == 1
    assert float(c3["monetary_gbp"]) == pytest.approx(7.0)


def test_percentile_scores_in_range_monotonic_ties_share_and_r_inverted():
    rfm = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "recency_days": [1, 10, 10, 100, 374],
            "frequency": [1, 1, 5, 5, 20],
            "monetary_gbp": [10.0, 10.0, 50.0, 50.0, 500.0],
        }
    )
    scored = score_rfm(rfm)
    for col in ("r_score", "f_score", "m_score"):
        assert scored[col].between(1, 5).all()
    # Most recent customer scores R = 5; least recent scores R = 1.
    assert int(scored.loc[scored["customer_id"] == 1, "r_score"].iloc[0]) == 5
    assert int(scored.loc[scored["customer_id"] == 5, "r_score"].iloc[0]) == 1
    # Ties share a score (F = 1 twice, F = 5 twice, M = 10 twice).
    assert scored.loc[scored["frequency"] == 1, "f_score"].nunique() == 1
    assert scored.loc[scored["frequency"] == 5, "f_score"].nunique() == 1
    assert scored.loc[scored["monetary_gbp"] == 10.0, "m_score"].nunique() == 1
    # Monotonic: higher F/M never scores lower.
    assert scored.sort_values("frequency")["f_score"].is_monotonic_increasing
    assert scored.sort_values("monetary_gbp")["m_score"].is_monotonic_increasing


def test_rfm_code_and_score_arithmetic():
    rfm = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "recency_days": [1, 10, 50, 100, 374],
            "frequency": [50, 20, 10, 5, 1],
            "monetary_gbp": [9999.0, 5000.0, 1000.0, 100.0, 10.0],
        }
    )
    scored = score_rfm(rfm)
    # Customer 1 is best on every axis: 5, 5, 5 → code 555, score 15.
    best = scored[scored["customer_id"] == 1].iloc[0]
    assert int(best["rfm_code"]) == 555
    assert int(best["rfm_score"]) == 15
    # Customer 5 is worst on every axis: 1, 1, 1 → code 111, score 3.
    worst = scored[scored["customer_id"] == 5].iloc[0]
    assert int(worst["rfm_code"]) == 111
    assert int(worst["rfm_score"]) == 3


def test_kmeans_uses_log1p_and_scaling():
    from src.clustering import _scaled_features

    rfm = pd.DataFrame(
        {
            "recency_days": [1, 300, 5, 200, 50],
            "frequency": [1, 2, 30, 3, 10],
            "monetary_gbp": [10.0, 20.0, 50000.0, 30.0, 1000.0],
        }
    )
    scaled = _scaled_features(rfm)
    # Every scaled column has mean ~0 and std ~1: Monetary's raw scale
    # (tens of thousands) cannot dominate Recency/Frequency.
    assert np.allclose(scaled.mean(axis=0), 0.0, atol=1e-10)
    assert np.allclose(scaled.std(axis=0, ddof=0), 1.0, atol=1e-10)


def test_kmeans_deterministic():
    rfm = pd.read_csv(PROC / "rfm_table.csv")
    first = cluster_customers(rfm, 2)
    second = cluster_customers(rfm, 2)
    assert np.array_equal(first, second)


def test_k_selection_argmax_with_smaller_k_tie_break():
    selection = pd.DataFrame(
        {"k": [2, 3, 4], "sse": [100.0, 80.0, 70.0], "silhouette": [0.50, 0.505, 0.40]}
    )
    # k = 3 is argmax but within 0.01 of k = 2 → smaller k wins.
    assert choose_k(selection) == 2
    selection2 = pd.DataFrame(
        {"k": [2, 3, 4], "sse": [100.0, 80.0, 70.0], "silhouette": [0.40, 0.60, 0.55]}
    )
    assert choose_k(selection2) == 3


def test_k_selection_shape_on_fixture():
    rfm = pd.DataFrame(
        {
            "recency_days": [1, 2, 3, 200, 250, 300, 5, 180],
            "frequency": [20, 18, 15, 1, 1, 2, 12, 1],
            "monetary_gbp": [5000.0, 4000.0, 3000.0, 50.0, 40.0, 60.0, 2000.0, 80.0],
        }
    )
    selection = select_k(rfm, k_range=range(2, 4))
    assert list(selection["k"]) == [2, 3]
    assert selection["silhouette"].between(-1, 1).all()
    assert (selection["sse"].diff().dropna() < 0).all()  # elbow: SSE falls with k


def test_segment_naming_follows_prototype_rule():
    medians = pd.DataFrame(
        {
            "median_r_score": [5.0, 1.0],
            "median_f_score": [5.0, 1.0],
            "median_m_score": [5.0, 1.0],
        },
        index=[0, 1],
    )
    mapping = name_segments(medians)
    assert mapping == {0: "Champions", 1: "Lost"}
    # Distinct names per cluster, even for identical median triples.
    medians_tied = pd.DataFrame(
        {
            "median_r_score": [2.0, 2.0],
            "median_f_score": [2.0, 2.0],
            "median_m_score": [2.0, 2.0],
        },
        index=[0, 1],
    )
    tied = name_segments(medians_tied)
    assert len(set(tied.values())) == 2
    assert "Hibernating" in tied.values()


def test_decider_segment_equals_kmeans_label_mapping():
    """Plan §2.0: the segment column must reproduce from KMeans labels."""
    rfm = pd.read_csv(PROC / "rfm_table.csv")
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    labels = cluster_customers(rfm, record["chosen_k"])
    medians = (
        rfm.assign(kmeans_cluster=labels)
        .groupby("kmeans_cluster")
        .agg(
            median_r_score=("r_score", "median"),
            median_f_score=("f_score", "median"),
            median_m_score=("m_score", "median"),
        )
    )
    mapping = name_segments(medians)
    reproduced = pd.Series(labels).map(mapping)
    assert (reproduced.values == rfm["segment"].values).all()
    assert (pd.Series(labels).values == rfm["kmeans_cluster"].values).all()


def test_decider_no_customer_assigned_by_rfm_score_rule_alone():
    """If segments came from the RFM-score rule, the nearest-prototype
    name of each customer's own (R, F, M) scores would equal their
    segment. On the committed table it disagrees for 2,830 of 4,334
    customers — KMeans, not the score rule, decides."""
    rfm = pd.read_csv(PROC / "rfm_table.csv")
    proto = dict(PROTOTYPES)

    def rule_name(row):
        triple = (row["r_score"], row["f_score"], row["m_score"])
        return min(
            proto.items(),
            key=lambda kv: sum((a - b) ** 2 for a, b in zip(triple, kv[1])),
        )[0]

    rule = rfm.apply(rule_name, axis=1)
    n_disagree = int((rule != rfm["segment"]).sum())
    assert n_disagree > 0
    assert n_disagree == 2830


def test_sbc_quadrant_boundaries_and_single_order():
    assert classify_sbc(1.32, 0.49) == "Smooth"
    assert classify_sbc(1.32, 0.50) == "Erratic"
    assert classify_sbc(1.33, 0.49) == "Intermittent"
    assert classify_sbc(1.33, 0.50) == "Lumpy"
    assert classify_sbc(float("nan"), float("nan")) == "Single-order"


def test_sbc_stats_single_and_multi_order():
    orders = pd.DataFrame(
        {
            "customer_id": [1, 2, 2, 2],
            "invoice_no": ["A", "B", "C", "D"],
            "invoice_date": pd.to_datetime(
                ["2011-01-01", "2011-01-01", "2011-01-08", "2011-01-15"]
            ),
            "line_revenue": [100.0, 10.0, 20.0, 30.0],
        }
    )
    stats = sbc_stats(orders)
    single = stats[stats["customer_id"] == 1].iloc[0]
    assert single["sbc_quadrant"] == "Single-order"
    multi = stats[stats["customer_id"] == 2].iloc[0]
    assert multi["adi_weeks"] == pytest.approx(1.0)  # weekly orders
    assert multi["cv2"] == pytest.approx(0.25)  # std 10 / mean 20, squared
    assert multi["sbc_quadrant"] == "Smooth"


def test_agreement_rate_fixtures():
    perfect = pd.DataFrame({"Smooth": [10, 0], "Erratic": [0, 8]}, index=["A", "B"])
    assert agreement_rate(perfect) == pytest.approx(1.0)
    partial = pd.DataFrame({"Smooth": [10, 3], "Erratic": [2, 8]}, index=["A", "B"])
    # Greedy: A→Smooth (10), then B→Erratic (8): 18/23.
    assert agreement_rate(partial) == pytest.approx(18 / 23)
    # Single-order column is excluded from the denominator.
    with_single = partial.copy()
    with_single["Single-order"] = [5, 5]
    assert agreement_rate(with_single) == pytest.approx(18 / 23)


def test_one_action_per_segment_with_gbp_at_stake():
    profile = pd.read_csv(PROC / "segment_profile.csv")
    segments = profile[profile["segment"] != "Unattributed (no CustomerID)"]
    assert len(segments) == 2  # k = 2: Champions + Hibernating
    for _, row in segments.iterrows():
        assert gbp_at_stake(row) == pytest.approx(float(row["revenue_gbp"]))
        action = action_for(str(row["segment"]), row)
        assert f"£{float(row['revenue_gbp']):,.2f}" in action
    assert build_actions(profile)["action"].notna().all()
    assert int((segments["action"] == "").sum()) == 0
    unattributed = profile[profile["segment"] == "Unattributed (no CustomerID)"]
    assert unattributed["action"].iloc[0] == "—"


def test_sql_vs_pandas_agreement():
    """Plan §4.6: in-memory SQLite vs pandas on the committed CSVs."""
    rfm = pd.read_csv(PROC / "rfm_table.csv")
    profile = pd.read_csv(PROC / "segment_profile.csv")
    con = sqlite3.connect(":memory:")
    rfm.to_sql("rfm", con, index=False)
    profile.to_sql("profile", con, index=False)
    sql = pd.read_sql_query(
        "SELECT segment, COUNT(*) AS n, SUM(monetary_gbp) AS revenue "
        "FROM rfm GROUP BY segment ORDER BY revenue DESC",
        con,
    )
    for _, row in sql.iterrows():
        prow = profile[profile["segment"] == row["segment"]].iloc[0]
        assert int(row["n"]) == int(prow["n_customers"])
        assert float(row["revenue"]) == pytest.approx(float(prow["revenue_gbp"]))
    top_sql = sql.iloc[0]["segment"]
    top_pd = profile.iloc[0]["segment"]
    assert top_sql == top_pd == "Champions"


def test_committed_counts_match_data_source():
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    rfm = pd.read_csv(PROC / "rfm_table.csv")
    assert record["raw_rows"] == 541909
    assert record["cleaned_rows"] == 527795
    assert record["cleaned_revenue_gbp"] == pytest.approx(10283243.98, abs=0.01)
    assert record["rfm"]["snapshot_date"] == "2011-12-10"
    assert len(rfm) == 4334
    assert record["chosen_k"] == 2
    assert record["agreement_rate"] == pytest.approx(0.5154, abs=0.001)
    assert record["revenue_missing_customer_share"] == pytest.approx(0.1480, abs=0.001)


def test_offline_run_does_not_clobber_data_source():
    """Day 5/6 lesson: --offline skips writing data_source.json when a
    live record exists; regenerated tables match within tolerance."""
    with tempfile.TemporaryDirectory() as tmp:
        day = Path(tmp) / "day12"
        shutil.copytree(
            ROOT,
            day,
            ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"),
        )
        ds_path = day / "data" / "processed" / "data_source.json"
        before = ds_path.read_bytes()
        profile_before = pd.read_csv(day / "data" / "processed" / "segment_profile.csv")
        run_offline(day)
        assert ds_path.read_bytes() == before  # byte-identical
        profile_after = pd.read_csv(day / "data" / "processed" / "segment_profile.csv")
        pd.testing.assert_frame_equal(
            profile_before, profile_after, check_exact=False, rtol=1e-6, atol=0.01
        )


def test_synthetic_never_overwrites_live_files():
    with tempfile.TemporaryDirectory() as tmp:
        day = Path(tmp) / "day12"
        (day / "data" / "raw").mkdir(parents=True)
        live = day / "data" / "raw" / "data.csv"
        live.write_text("live-data", encoding="utf-8")
        out = generate_synthetic(day)
        assert out.name.endswith("_synthetic.csv")
        assert live.read_text(encoding="utf-8") == "live-data"
        assert out.exists()


def test_data_size_rule():
    """No committed file > 1 MB; data/ total < 5 MB (git-ignored raw
    CSV/XLSX excluded — they are not committed)."""
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        if path.name in ("data.csv", "Online Retail.xlsx"):
            continue
        assert path.stat().st_size <= 1_000_000, f"{path} exceeds 1 MB"
        total += path.stat().st_size
    assert total < 5_000_000, f"data/ total {total} exceeds 5 MB"


def test_no_committed_file_over_1mb():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.name in ("data.csv", "Online Retail.xlsx"):
            continue
        assert path.stat().st_size <= 1_000_000, f"{path} exceeds 1 MB"


def test_chart_02_revenue_bars_use_one_neutral_colour(monkeypatch, tmp_path):
    """D-1 regression (optimizer): chart 02 revenue bars must all share
    one neutral colour so the legend swatch matches every bar — the old
    per-segment colours made the single brown swatch misreadable."""
    import matplotlib.colors
    import matplotlib.pyplot as plt

    from src import make_charts

    # chart_02 closes its figure; keep it open so its bars can be read.
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)
    data = make_charts._load(ROOT)
    out = tmp_path / "02_segment_value.png"
    make_charts.chart_02(data, out)
    assert out.exists()
    ax = plt.gcf().axes[0]
    bars = list(ax.patches)
    assert len(bars) == 4  # 2 segments x 2 series
    revenue_bars = bars[2:]  # second barh call = revenue series
    colours = {tuple(b.get_facecolor()) for b in revenue_bars}
    assert len(colours) == 1
    assert colours == {matplotlib.colors.to_rgba("#455a64")}


def test_dashboard_surfaces_action_and_gbp_without_scrolling():
    """D-2 regression (optimizer): app.py must show a compact action
    table (segment / n / revenue / action / £ at stake) before the full
    18-column profile table, so the deliverable is visible at 1200 px
    without horizontal scrolling."""
    src = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    compact = '["segment", "n_customers", "revenue_gbp", "action", "gbp_at_stake"]'
    assert compact in src
    assert src.index(compact) < src.index("st.dataframe(profile")
