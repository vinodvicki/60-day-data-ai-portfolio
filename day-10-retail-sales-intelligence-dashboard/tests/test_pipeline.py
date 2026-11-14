"""Day 10 — Retail Sales Intelligence Dashboard: offline pytest suite.

Covers the cleaning rules in order (cancellations, non-positive
quantity/price, adjustment codes, missing descriptions), the monthly
partial-December flag and MoM skip, the full-weeks-only weekly series,
the top-10 concentration sum, RFM construction, KMeans determinism and
silhouette range, the naïve and Holt-Winters forecasts, the bootstrap
intervals containing the point forecast and widening with horizon, the
2-origin backtest design, the offline path never clobbering the live
record (Day 5/6 lesson) with tolerance-based comparison (Day 9 CI
flake lesson — never byte-exact on regenerated floats), the synthetic
fallback staying labelled and never overwriting live files, the
data-size rule, and the SQL-vs-pandas check. Runs from the repo root
and from inside the day folder.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline as pipeline
from src.clustering import build_rfm, cluster_customers
from src.forecast import (
    bootstrap_intervals,
    holt_winters_forecast,
    naive_forecast,
    rolling_backtest,
)
from src.metrics import (
    aov,
    line_revenue,
    mae,
    month_over_month,
    repeat_rate,
    revenue_share,
    rmse,
)

PROCESSED = ROOT / "data" / "processed"


def _fixture_rows() -> pd.DataFrame:
    """Small cleaned-shape fixture: 2 customers, 3 orders, known revenue."""
    return pd.DataFrame(
        {
            "InvoiceNo": ["1001", "1001", "1002", "1003", "1003"],
            "StockCode": ["85123A", "85099B", "85123A", "22423", "85099B"],
            "Description": [
                "WHITE HANGING HEART",
                "JUMBO BAG RED",
                "WHITE HANGING HEART",
                "REGENCY CAKESTAND",
                "JUMBO BAG RED",
            ],
            "Quantity": [2, 3, 1, 1, 4],
            "InvoiceDate": pd.to_datetime(
                ["2011-01-03", "2011-01-03", "2011-02-10", "2011-03-15", "2011-03-15"]
            ),
            "UnitPrice": [2.50, 1.00, 2.50, 10.00, 1.00],
            "CustomerID": [111.0, 111.0, 111.0, 222.0, 222.0],
            "Country": ["United Kingdom"] * 5,
        }
    )


def _raw_rows() -> pd.DataFrame:
    """Raw-shape fixture exercising every cleaning rule."""
    rows = _fixture_rows()
    extra = pd.DataFrame(
        {
            "InvoiceNo": ["C1004", "1005", "1006", "1007", "1008"],
            "StockCode": ["85123A", "85123A", "85123A", "POST", "85123A"],
            "Description": [
                "WHITE HANGING HEART",
                "WHITE HANGING HEART",
                "WHITE HANGING HEART",
                "POSTAGE",
                None,
            ],
            "Quantity": [-1, 0, 2, 1, 1],
            "InvoiceDate": pd.to_datetime(["2011-04-01"] * 5),
            "UnitPrice": [2.50, 2.50, 0.00, 2.00, 2.50],
            "CustomerID": [333.0, 333.0, 333.0, np.nan, 333.0],
            "Country": ["United Kingdom"] * 5,
        }
    )
    return pd.concat([rows, extra], ignore_index=True)


# --- metrics (pure functions, hand-checked) ---------------------------------


def test_line_revenue():
    assert line_revenue(3, 2.50) == 7.50
    assert line_revenue(80995, 2.08) == pytest.approx(168469.60, abs=0.01)


def test_aov_and_repeat_rate():
    assert aov(10283243.98, 19776) == pytest.approx(519.99, abs=0.01)
    assert repeat_rate([1, 2, 3, 1]) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        aov(100.0, 0)


def test_revenue_share():
    assert revenue_share(174484.74, 10283243.98) == pytest.approx(1.70, abs=0.01)
    assert revenue_share(8759372.58, 10283243.98) == pytest.approx(85.18, abs=0.01)


def test_rmse_mae_hand_checked():
    assert rmse([3.0, 5.0], [3.0, 5.0]) == 0.0
    assert rmse([0.0, 0.0], [3.0, 4.0]) == pytest.approx(3.5355339, abs=1e-6)
    assert mae([0.0, 0.0], [3.0, 4.0]) == pytest.approx(3.5)


def test_month_over_month_skips_partial():
    # None marks a partial month; its growth and the next month's are None.
    result = month_over_month([100.0, 110.0, None])
    assert result[0] is None and result[2] is None
    assert result[1] == pytest.approx(10.0)
    result = month_over_month([100.0, None, 120.0])
    assert result == [None, None, None]
    result = month_over_month([508952.87, 1457745.53])
    assert result[0] is None
    assert result[1] == pytest.approx(186.42, abs=0.01)


# --- cleaning (plan §3.2, in order) ------------------------------------------


def test_clean_removes_cancellations_first():
    cleaned, counts = pipeline.clean_transactions(_raw_rows())
    assert counts["raw_rows"] == 10
    assert counts["cancelled_rows"] == 1
    assert counts["cancelled_invoices"] == 1
    assert not cleaned["InvoiceNo"].astype(str).str.startswith("C").any()


def test_clean_removes_non_positive_quantity_and_price():
    _, counts = pipeline.clean_transactions(_raw_rows())
    assert counts["non_positive_quantity_rows"] == 1
    assert counts["non_positive_price_rows"] == 1


def test_clean_removes_adjustment_lines():
    _, counts = pipeline.clean_transactions(_raw_rows())
    assert counts["adjustment_rows"] == 1
    cleaned, _ = pipeline.clean_transactions(_raw_rows())
    assert "POST" not in cleaned["StockCode"].astype(str).str.upper().values


def test_clean_counts_and_revenue():
    cleaned, counts = pipeline.clean_transactions(_raw_rows())
    # 10 raw - 1 cancelled - 1 qty - 1 price - 1 adjustment - 1 missing desc = 5
    assert counts["cleaned_rows"] == 5
    assert counts["missing_description_rows"] == 1
    assert counts["total_revenue_gbp"] == pytest.approx(24.50, abs=0.01)
    assert (cleaned["line_revenue"] == cleaned["Quantity"] * cleaned["UnitPrice"]).all()


def test_cleaned_totals_match_committed_csvs():
    monthly = pd.read_csv(PROCESSED / "monthly_sales.csv")
    assert monthly["revenue_gbp"].sum() == pytest.approx(10283243.98, abs=0.01)
    assert monthly["orders"].sum() == 19776
    assert monthly["units"].sum() == 5577139


# --- monthly / weekly series -------------------------------------------------


def test_monthly_december_2011_is_partial():
    monthly = pd.read_csv(PROCESSED / "monthly_sales.csv")
    assert len(monthly) == 13
    dec11 = monthly[monthly["month"] == "2011-12"].iloc[0]
    assert bool(dec11["is_partial"]) is True
    assert dec11["revenue_gbp"] == pytest.approx(615501.60, abs=0.01)
    assert (
        monthly["revenue_gbp"].idxmax()
        == monthly[monthly["month"] == "2011-11"].index[0]
    )
    assert monthly.loc[monthly["month"] == "2011-11", "revenue_gbp"].iloc[
        0
    ] == pytest.approx(1457745.53, abs=0.01)


def test_weekly_series_is_full_weeks_only():
    weekly = pd.read_csv(PROCESSED / "weekly_revenue.csv")
    assert len(weekly) == 51
    assert weekly["week_start"].iloc[0] == "2010-12-06"
    assert weekly["week_start"].iloc[-1] == "2011-11-28"
    starts = pd.to_datetime(weekly["week_start"])
    assert (starts.dt.day_of_week == 0).all()  # every week starts Monday
    # Weekly total must be less than the monthly total (two partial weeks dropped).
    assert weekly["revenue_gbp"].sum() < 10283243.98
    assert weekly["revenue_gbp"].sum() > 9000000


def test_weekly_builder_drops_partial_weeks():
    frame = pd.DataFrame(
        {
            "InvoiceNo": ["1", "2", "3"],
            "StockCode": ["A", "A", "A"],
            "Description": ["X", "X", "X"],
            "Quantity": [1, 1, 1],
            "InvoiceDate": pd.to_datetime(["2010-12-01", "2010-12-06", "2010-12-12"]),
            "UnitPrice": [10.0, 10.0, 10.0],
            "CustomerID": [1.0, 1.0, 1.0],
            "Country": ["United Kingdom"] * 3,
            "line_revenue": [10.0, 10.0, 10.0],
        }
    )
    weekly = pipeline.build_weekly_revenue(frame)
    assert len(weekly) == 1
    assert weekly["week_start"].iloc[0] == "2010-12-06"


# --- product mix / country ----------------------------------------------------


def test_top10_concentration_sums_correctly():
    top = pd.read_csv(PROCESSED / "top_products.csv")
    assert len(top) == 20
    assert top["revenue_share"].head(10).sum() == pytest.approx(9.41, abs=0.01)
    assert top.iloc[0]["description"] == "REGENCY CAKESTAND 3 TIER"
    assert top.iloc[0]["revenue_gbp"] == pytest.approx(174484.74, abs=0.01)
    assert top["revenue_gbp"].is_monotonic_decreasing


def test_top_sku_single_wholesale_order():
    top = pd.read_csv(PROCESSED / "top_products.csv")
    birdie = top[top["stock_code"] == "23843"].iloc[0]
    assert birdie["orders"] == 1
    assert birdie["units"] == 80995


def test_country_uk_share_and_aov():
    country = pd.read_csv(PROCESSED / "country_sales.csv")
    uk = country[country["country"] == "United Kingdom"].iloc[0]
    assert uk["revenue_share"] == pytest.approx(85.18, abs=0.01)
    assert uk["aov_gbp"] == pytest.approx(489.24, abs=0.01)
    assert country["revenue_share"].sum() == pytest.approx(100.0, abs=0.05)
    netherlands = country[country["country"] == "Netherlands"].iloc[0]
    assert netherlands["aov_gbp"] == pytest.approx(3052.57, abs=0.01)


def test_product_groups_top_and_other():
    groups = pd.read_csv(PROCESSED / "product_groups.csv")
    assert len(groups) == 11  # top 10 + Other
    assert groups.iloc[0]["product_group"] == "SET"
    assert groups.iloc[0]["revenue_share"] == pytest.approx(7.35, abs=0.01)
    assert groups["revenue_share"].sum() == pytest.approx(100.0, abs=0.05)
    assert groups.iloc[-1]["product_group"] == "Other"


# --- RFM + clustering ---------------------------------------------------------


def test_rfm_on_fixture():
    cleaned, _ = pipeline.clean_transactions(_fixture_rows())
    rfm = build_rfm(cleaned)
    assert len(rfm) == 2
    c111 = rfm[rfm["customer_id"] == 111].iloc[0]
    assert c111["frequency"] == 2
    assert c111["monetary_gbp"] == pytest.approx(10.50, abs=0.01)
    assert c111["recency_days"] == 33  # last purchase 2011-02-10, end 2011-03-15


def test_missing_customer_excluded_from_rfm_only():
    _cleaned, counts = pipeline.clean_transactions(_raw_rows())
    assert counts["missing_customer_rows"] == 0  # fixture has none after cleaning
    monthly = pd.read_csv(PROCESSED / "monthly_sales.csv")
    assert monthly["customers"].sum() > 0
    record = json.loads((PROCESSED / "data_source.json").read_text())
    assert record["kpis"]["missing_customer_revenue_share_pct"] == pytest.approx(
        14.80, abs=0.01
    )


def test_clustering_deterministic_and_silhouette_in_range():
    rfm = pd.read_csv(PROCESSED / "rfm_clusters.csv")
    labels1, score1 = cluster_customers(rfm)
    labels2, score2 = cluster_customers(rfm)
    assert (labels1 == labels2).all()
    assert score1 == score2
    assert -1.0 <= score1 <= 1.0
    assert score1 == pytest.approx(0.6163, abs=0.001)
    assert len(set(labels1)) == 4


def test_cluster_summary_matches_rfm():
    summary = pd.read_csv(PROCESSED / "cluster_summary.csv")
    rfm = pd.read_csv(PROCESSED / "rfm_clusters.csv")
    assert summary["n_customers"].sum() == len(rfm) == 4334
    assert summary["share_customers"].sum() == pytest.approx(100.0, abs=0.05)
    assert summary["share_revenue"].sum() == pytest.approx(100.0, abs=0.05)
    champions = summary[summary["label"] == "Champions"].iloc[0]
    assert champions["n_customers"] == 13
    assert champions["share_revenue"] == pytest.approx(18.68, abs=0.01)
    assert set(summary["label"]) == {
        "Champions",
        "Big spenders",
        "Occasional buyers",
        "Lapsed",
    }


# --- forecast -----------------------------------------------------------------


def test_naive_forecast_is_last_value():
    series = pd.Series([100.0, 120.0, 140.0])
    assert (naive_forecast(series, 4) == np.array([140.0] * 4)).all()


def test_holt_winters_forecast_length_and_direction():
    weekly = pd.read_csv(PROCESSED / "weekly_revenue.csv")
    point, _ = holt_winters_forecast(weekly["revenue_gbp"], 8)
    assert len(point) == 8
    assert np.isfinite(point).all()
    assert (point > 0).all()


def test_bootstrap_intervals_contain_point_and_widen():
    point = np.array([100.0, 110.0, 120.0])
    residuals = np.array([-5.0, 5.0, -3.0, 3.0, 0.0, 2.0, -2.0])
    intervals = bootstrap_intervals(residuals, point)
    assert (intervals["lo_80"] <= point).all()
    assert (intervals["hi_80"] >= point).all()
    assert (intervals["lo_95"] <= intervals["lo_80"]).all()
    assert (intervals["hi_95"] >= intervals["hi_80"]).all()
    widths_80 = intervals["hi_80"] - intervals["lo_80"]
    assert widths_80[-1] >= widths_80[0]


def test_backtest_design_two_origins():
    weekly = pd.read_csv(PROCESSED / "weekly_revenue.csv")
    backtest = rolling_backtest(weekly["revenue_gbp"])
    assert set(backtest["origin"]) == {8, 16}
    assert set(backtest["method"]) == {"holt_winters", "naive"}
    assert len(backtest) == 4
    committed = pd.read_csv(PROCESSED / "backtest.csv")
    for _, row in committed.iterrows():
        match = backtest[
            (backtest["origin"] == row["origin"])
            & (backtest["method"] == row["method"])
        ].iloc[0]
        assert match["rmse"] == pytest.approx(row["rmse"], abs=0.01)


def test_forecast_csv_shape_and_winner():
    forecast = pd.read_csv(PROCESSED / "forecast.csv")
    assert len(forecast) == 8
    assert forecast["week_start"].iloc[0] == "2011-12-05"
    assert (forecast["lo_80"] <= forecast["forecast_gbp"]).all()
    assert (forecast["hi_80"] >= forecast["forecast_gbp"]).all()
    record = json.loads((PROCESSED / "data_source.json").read_text())
    assert record["forecast"]["published_method"] == "holt_winters"
    assert (
        record["forecast"]["mean_rmse"]["holt_winters"]
        < record["forecast"]["mean_rmse"]["naive"]
    )


# --- offline / synthetic / size / SQL ----------------------------------------


def test_offline_run_does_not_clobber_data_source():
    record_path = PROCESSED / "data_source.json"
    before = record_path.read_bytes()
    summary_before = pd.read_csv(PROCESSED / "cluster_summary.csv")
    pipeline.run_offline()
    assert record_path.read_bytes() == before
    summary_after = pd.read_csv(PROCESSED / "cluster_summary.csv")
    pd.testing.assert_frame_equal(
        summary_before,
        summary_after,
        check_exact=False,
        rtol=1e-6,
        atol=0.01,
    )


def test_synthetic_generator_is_labelled_and_separate():
    synth = pipeline.build_synthetic()
    assert len(synth) > 10000
    assert list(synth.columns) == pipeline.EXPECTED_COLUMNS
    assert (synth["InvoiceNo"].astype(str).str.startswith("C") == False).all()
    # The synthetic file name is distinct from the live raw files.
    assert (pipeline.RAW_DIR / "online_retail_synthetic.csv").name != pipeline.XLSX_NAME
    assert (pipeline.RAW_DIR / "online_retail_synthetic.csv").name != pipeline.ZIP_NAME


def test_no_committed_file_over_1mb_and_data_under_5mb():
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if path.is_file() and path.suffix not in {".zip", ".xlsx"}:
            assert path.stat().st_size < 1_000_000, f"{path} over 1 MB"
            total += path.stat().st_size
    assert total < 5_000_000, f"data/ total {total} over 5 MB"


def test_gitignore_excludes_raw_but_not_data():
    gitignore = (ROOT / ".gitignore").read_text()
    assert "data/raw/online_retail.zip" in gitignore
    assert "data/raw/Online Retail.xlsx" in gitignore
    assert "data/raw/*_synthetic.csv" in gitignore
    assert "data/" not in gitignore.replace("data/raw/", "")


def test_sql_matches_pandas():
    monthly = pd.read_csv(PROCESSED / "monthly_sales.csv")
    country = pd.read_csv(PROCESSED / "country_sales.csv")
    conn = sqlite3.connect(":memory:")
    monthly.to_sql("monthly_sales", conn, index=False)
    country.to_sql("country_sales", conn, index=False)
    sql_monthly = pd.read_sql(
        "SELECT month, revenue_gbp FROM monthly_sales ORDER BY month", conn
    )
    pd.testing.assert_frame_equal(
        sql_monthly,
        monthly[["month", "revenue_gbp"]].reset_index(drop=True),
        check_exact=False,
        rtol=1e-9,
        atol=0.01,
    )
    sql_top5 = pd.read_sql(
        "SELECT country, revenue_gbp FROM country_sales ORDER BY revenue_gbp DESC LIMIT 5",
        conn,
    )
    pd.testing.assert_frame_equal(
        sql_top5,
        country[["country", "revenue_gbp"]].head(5).reset_index(drop=True),
        check_exact=False,
        rtol=1e-9,
        atol=0.01,
    )
    conn.close()
