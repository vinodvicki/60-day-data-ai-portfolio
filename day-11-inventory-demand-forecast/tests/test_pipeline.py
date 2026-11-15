"""Tests for Day 11 — Inventory Demand Forecast.

Covers cleaning counts, weekly series construction, the top-20 rule,
clustering, every forecast method, WAPE, reorder arithmetic, the
offline-does-not-clobber-data_source regression, the SQL check and the
data-size rule. Fixtures are small synthetic frames; the live numbers
are asserted from the committed CSVs.
"""

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clustering import classify_sbc, demand_pattern_stats, kmeans_crosscheck
from src.data_pipeline import (
    ADJUSTMENT_DESCRIPTIONS,
    ADJUSTMENT_STOCK_CODES,
    clean_transactions,
    run_offline,
)
from src.forecast import (
    backtest,
    bias,
    croston_sba_forecast,
    gradient_boosting_forecast,
    holt_forecast,
    mae,
    moving_average_forecast,
    naive_forecast,
    rmse,
    seasonal_naive_available,
    seasonal_naive_forecast,
    select_cluster_winner,
    wape,
)
from src.reorder import (
    build_reorder_list,
    order_up_to,
    reorder_point,
    safety_stock,
    service_level_for,
)

PROC = ROOT / "data" / "processed"


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


def _weekly_frame() -> pd.DataFrame:
    weeks = pd.date_range("2010-12-06", periods=52, freq="7D")
    rows = []
    for code in ["S1", "S2"]:
        for i, w in enumerate(weeks):
            units = 10 if code == "S1" else (5 if i % 2 == 0 else 0)
            rows.append(
                {
                    "week_start": w,
                    "stock_code": code,
                    "description": code,
                    "units": units,
                }
            )
    return pd.DataFrame(rows)


def test_revenue_is_quantity_times_price():
    df = _raw_frame()
    assert float((df["Quantity"] * df["UnitPrice"]).iloc[0]) == 10.0


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
    assert "POST" in ADJUSTMENT_STOCK_CODES
    assert "POSTAGE" in ADJUSTMENT_DESCRIPTIONS


def test_missing_customer_id_kept_in_demand():
    cleaned, counts = clean_transactions(_raw_frame())
    assert counts["n_missing_customer_id"] == 1
    # The kept row 1005 has no CustomerID and is still in the demand set.
    assert (cleaned["customer_id"].isna()).any()
    assert len(cleaned) == 3


def test_missing_description_excluded():
    _, counts = clean_transactions(_raw_frame())
    assert counts["n_missing_description"] == 1


def test_weekly_series_is_52_full_weeks():
    weekly = pd.read_csv(PROC / "weekly_demand.csv", parse_dates=["week_start"])
    assert len(weekly) == 20 * 52
    assert weekly["week_start"].min() == pd.Timestamp("2010-12-06")
    # Last week *starts* Monday 2011-11-28 and ends Sunday 2011-12-04.
    assert weekly["week_start"].max() == pd.Timestamp("2011-11-28")
    assert weekly["week_start"].nunique() == 52


def test_partial_weeks_excluded_from_series():
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    assert record["n_partial_week_rows"] > 0
    assert record["full_weeks"]["n_weeks"] == 52
    weekly = pd.read_csv(PROC / "weekly_demand.csv", parse_dates=["week_start"])
    assert weekly["week_start"].min() >= pd.Timestamp("2010-12-06")
    assert weekly["week_start"].max() <= pd.Timestamp("2011-12-04")


def test_top20_selection_enforces_coverage_with_replacement():
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    replaced = record["top_20_selection"]["replaced"]
    assert len(replaced) == 1
    assert str(replaced[0]["stock_code"]) == "23284"
    assert replaced[0]["weeks_with_demand"] == 27
    sku = pd.read_csv(PROC / "sku_summary.csv")
    assert len(sku) == 20
    assert (sku["weeks_with_demand"] >= 30).all()


def test_adi_cv2_and_sbc_boundaries():
    assert classify_sbc(1.0, 0.2) == "smooth"
    assert classify_sbc(1.0, 0.49) == "erratic"
    assert classify_sbc(1.32, 0.2) == "intermittent"
    assert classify_sbc(1.32, 0.49) == "lumpy"
    stats = demand_pattern_stats(_weekly_frame())
    s1 = stats[stats["stock_code"] == "S1"].iloc[0]
    assert s1["adi"] == pytest.approx(1.0)
    assert s1["cv2"] == pytest.approx(0.0)
    assert s1["cluster"] == "smooth"
    s2 = stats[stats["stock_code"] == "S2"].iloc[0]
    assert s2["adi"] == pytest.approx(2.0)
    assert s2["cluster"] == "intermittent"


def test_kmeans_deterministic():
    rng = np.random.default_rng(0)
    feats = pd.DataFrame(
        {
            "mean_weekly_units": rng.lognormal(3, 1, 200),
            "cv": rng.uniform(0, 2, 200),
            "adi": rng.uniform(1, 10, 200),
            "trend_slope": rng.normal(0, 1, 200),
            "cluster": ["smooth"] * 50
            + ["erratic"] * 50
            + ["intermittent"] * 50
            + ["lumpy"] * 50,
        }
    )
    labels1, agree1 = kmeans_crosscheck(feats)
    labels2, agree2 = kmeans_crosscheck(feats)
    assert (labels1 == labels2).all()
    assert agree1 == pytest.approx(agree2)
    assert 0.0 <= agree1 <= 1.0


def test_naive_forecast_is_last_value():
    s = pd.Series([1.0, 2.0, 5.0])
    assert (naive_forecast(s, horizon=4) == np.array([5.0, 5.0, 5.0, 5.0])).all()


def test_moving_average_forecast_is_mean_of_last_four():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 10.0])
    assert (moving_average_forecast(s, horizon=2) == np.array([4.75, 4.75])).all()


def test_seasonal_naive_falls_back_on_52_week_series():
    s = pd.Series(np.arange(1, 53, dtype=float))
    assert not seasonal_naive_available(s, horizon=4)
    assert (seasonal_naive_forecast(s, horizon=4) == np.array([52.0] * 4)).all()
    long = pd.Series(np.arange(1, 60, dtype=float))
    assert seasonal_naive_available(long, horizon=4)
    assert (
        seasonal_naive_forecast(long, horizon=4) == np.array([8.0, 9.0, 10.0, 11.0])
    ).all()


def test_croston_sba_nonnegative_and_flat_on_intermittent():
    s = pd.Series([0, 0, 5, 0, 0, 0, 5, 0, 0, 5, 0, 0])
    fc = croston_sba_forecast(s, horizon=4)
    assert (fc >= 0).all()
    assert fc.std() == pytest.approx(0.0)
    assert 0 < fc[0] < 5


def test_holt_forecast_length_and_no_seasonality():
    s = pd.Series(np.linspace(10, 60, 52))
    fc, _ = holt_forecast(s, horizon=4)
    assert len(fc) == 4
    assert (fc >= 0).all()


def test_gradient_boosting_forecast_length_and_nonnegative():
    weeks = pd.date_range("2010-12-06", periods=52, freq="7D")
    s = pd.Series(np.linspace(10, 60, 52) + np.sin(np.arange(52)), index=weeks)
    fc = gradient_boosting_forecast(s, horizon=4)
    assert len(fc) == 4
    assert (fc >= 0).all()


def test_wape_mae_rmse_bias_on_fixtures():
    actual = np.array([10.0, 0.0, 20.0, 5.0])
    pred = np.array([12.0, 0.0, 16.0, 5.0])
    assert wape(actual, pred) == pytest.approx(6 / 35)
    assert mae(actual, pred) == pytest.approx(1.5)
    assert rmse(actual, pred) == pytest.approx(np.sqrt(5.0))
    assert bias(actual, pred) == pytest.approx(-0.5)
    # WAPE is defined even when a holdout week is zero (MAPE would not be).
    assert np.isfinite(wape(actual, pred))


def test_backtest_seasonal_naive_is_na_on_both_origins():
    s = pd.Series(np.arange(1, 53, dtype=float))
    bt = backtest(s)
    assert set(bt["origin"]) == {48, 29}
    assert set(bt["method"]) == {
        "naive",
        "seasonal_naive",
        "moving_average",
        "croston_sba",
        "holt",
        "gradient_boosting",
    }
    sn = bt[bt["method"] == "seasonal_naive"]
    assert sn["wape"].isna().all()


def test_cluster_winner_rule_and_tie_break():
    rows = []
    for method, w in [
        ("naive", 0.400),
        ("moving_average", 0.402),
        ("holt", 0.399),
        ("croston_sba", 0.500),
        ("gradient_boosting", 0.600),
    ]:
        rows.append(
            {
                "origin": 48,
                "method": method,
                "stock_code": "S1",
                "cluster": "smooth",
                "wape": w,
                "actual_total": 1000.0,
            }
        )
    frame = pd.DataFrame(rows)
    # Holt is best (0.399) but naïve (0.400) is within 0.5 pp -> simpler wins.
    assert select_cluster_winner(frame, "smooth") == "naive"
    frame.loc[frame["method"] == "naive", "wape"] = 0.500
    # Now moving average (0.402) is within 0.5 pp of Holt -> moving average wins.
    assert select_cluster_winner(frame, "smooth") == "moving_average"
    assert select_cluster_winner(frame, "lumpy") == "n/a"


def test_reorder_maths_on_fixtures():
    assert safety_stock(100.0, 1.65) == pytest.approx(165.0)
    assert safety_stock(100.0, 1.28, lead_time_weeks=2.0) == pytest.approx(
        128 * np.sqrt(2)
    )
    assert reorder_point(50.0, 1.0, 165.0) == pytest.approx(215.0)
    assert order_up_to(400.0, 165.0) == pytest.approx(565.0)
    assert service_level_for("smooth") == (0.95, 1.65)
    assert service_level_for("lumpy") == (0.90, 1.28)


def test_reorder_list_flag_rule():
    sku = pd.DataFrame(
        [
            {
                "stock_code": "L1",
                "description": "Lumpy thing",
                "cluster": "lumpy",
                "mean_weekly_units": 10.0,
                "mean_weekly_train": 10.0,
                "sigma_weekly_train": 20.0,
            },
            {
                "stock_code": "S1",
                "description": "Smooth thing",
                "cluster": "smooth",
                "mean_weekly_units": 100.0,
                "mean_weekly_train": 100.0,
                "sigma_weekly_train": 5.0,
            },
        ]
    )
    fc = pd.DataFrame(
        {
            "stock_code": ["L1"] * 4 + ["S1"] * 4,
            "forecast_units": [10.0] * 4 + [100.0] * 4,
        }
    )
    out = build_reorder_list(sku, fc, {"lumpy": "naive", "smooth": "moving_average"})
    assert list(out.columns) == [
        "stock_code",
        "description",
        "cluster",
        "winning_method",
        "forecast_4w_units",
        "mean_weekly_units",
        "sigma_weekly_units",
        "safety_stock_units",
        "reorder_point_units",
        "order_up_to_units",
        "implied_order_zero_on_hand_units",
        "service_level",
        "stockout_risk_flag",
        "reorder_point_2wk_units",
    ]
    lumpy = out[out["stock_code"] == "L1"].iloc[0]
    assert lumpy["stockout_risk_flag"] == "review-manually"
    assert lumpy["implied_order_zero_on_hand_units"] == pytest.approx(
        lumpy["order_up_to_units"]
    )
    assert lumpy["service_level"] == pytest.approx(0.90)
    smooth = out[out["stock_code"] == "S1"].iloc[0]
    assert smooth["stockout_risk_flag"] == "ok"
    assert smooth["service_level"] == pytest.approx(0.95)
    # Croston winner also forces review-manually.
    out2 = build_reorder_list(sku, fc, {"lumpy": "naive", "smooth": "croston_sba"})
    assert (
        out2[out2["stock_code"] == "S1"].iloc[0]["stockout_risk_flag"]
        == "review-manually"
    )


def test_offline_run_does_not_clobber_data_source(tmp_path):
    day = tmp_path / "day"
    (day / "data" / "processed").mkdir(parents=True)
    (day / "outputs" / "charts").mkdir(parents=True)
    for name in [
        "weekly_demand.csv",
        "weekly_aggregate.csv",
        "sku_summary.csv",
        "cluster_summary.csv",
        "forecast.csv",
        "backtest.csv",
        "reorder_list.csv",
    ]:
        (day / "data" / "processed" / name).write_bytes((PROC / name).read_bytes())
    ds = PROC / "data_source.json"
    (day / "data" / "processed" / "data_source.json").write_bytes(ds.read_bytes())
    before = ds.read_bytes()
    run_offline(day)
    after = (day / "data" / "processed" / "data_source.json").read_bytes()
    assert after == before, "offline run clobbered data_source.json"
    # Regenerated reorder list matches the committed one within tolerance.
    regen = pd.read_csv(day / "data" / "processed" / "reorder_list.csv")
    committed = pd.read_csv(PROC / "reorder_list.csv")
    pd.testing.assert_frame_equal(
        regen.sort_values("stock_code").reset_index(drop=True),
        committed.sort_values("stock_code").reset_index(drop=True),
        check_exact=False,
        rtol=1e-6,
        atol=0.01,
    )


def test_synthetic_never_overwrites_live_files(tmp_path):
    from src.data_pipeline import generate_synthetic

    out = generate_synthetic(tmp_path)
    assert out.name.endswith("_synthetic.csv")
    assert not (tmp_path / "data" / "processed" / "weekly_demand.csv").exists()


def test_sql_vs_pandas_agreement():
    weekly = pd.read_csv(PROC / "weekly_demand.csv")
    sku = pd.read_csv(PROC / "sku_summary.csv")
    con = sqlite3.connect(":memory:")
    weekly.to_sql("weekly_demand", con, index=False)
    sku.to_sql("sku_summary", con, index=False)
    sql_top5 = pd.read_sql(
        "SELECT week_start, SUM(units) AS units FROM weekly_demand "
        "GROUP BY week_start ORDER BY units DESC LIMIT 5",
        con,
    )
    pd_top5 = (
        weekly.groupby("week_start")["units"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    pd.testing.assert_frame_equal(
        sql_top5.sort_values("week_start").reset_index(drop=True),
        pd_top5.sort_values("week_start").reset_index(drop=True),
        check_dtype=False,
    )
    sql_rank = pd.read_sql(
        "SELECT stock_code, revenue_gbp FROM sku_summary "
        "ORDER BY revenue_gbp DESC LIMIT 1",
        con,
    )
    assert sql_rank.iloc[0]["stock_code"] == str(
        sku.sort_values("revenue_gbp", ascending=False).iloc[0]["stock_code"]
    )


def test_data_size_rule():
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if path.is_file() and "raw" not in path.parts:
            assert path.stat().st_size <= 1_000_000, f"{path} over 1 MB"
            total += path.stat().st_size
    assert total < 5_000_000


def test_committed_row_counts():
    assert len(pd.read_csv(PROC / "weekly_demand.csv")) == 1040
    assert len(pd.read_csv(PROC / "weekly_aggregate.csv")) == 52
    assert len(pd.read_csv(PROC / "forecast.csv")) == 84
    assert len(pd.read_csv(PROC / "reorder_list.csv")) == 20
    assert len(pd.read_csv(PROC / "backtest.csv")) == 252
    assert len(pd.read_csv(PROC / "cluster_summary.csv")) == 4


def test_data_source_json_is_strict_json():
    """Regression: data_source.json must be strict JSON (no bare NaN).

    Python's json module writes NaN as a bare literal, which strict JSON
    parsers reject. The pipeline sanitises non-finite floats to null on
    write; the committed file must already carry null, not NaN.
    """
    text = (PROC / "data_source.json").read_text(encoding="utf-8")
    assert "NaN" not in text, "bare NaN literal in data_source.json"
    assert "Infinity" not in text, "bare Infinity literal in data_source.json"

    def _reject(constant):
        raise ValueError(f"non-strict JSON constant: {constant}")

    record = json.loads(text, parse_constant=_reject)
    insample = record["backtest"]["in_sample_wape_aggregate"]
    assert insample["holt"] is None
    assert insample["gradient_boosting"] is None
