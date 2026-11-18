"""Data pipeline for Day 11 — Inventory Demand Forecast.

One plain full download of the UCI Online Retail ZIP (the server ignores
Range headers — no ranged fetch), ordered cleaning with every exclusion
counted, the 52-full-week ISO series (2010-12-06 → 2011-12-04), top-20
SKU selection with the >= 30/52 coverage rule, and the committed
processed files + data_source.json. Offline mode regenerates the derived
tables/charts from the committed CSVs and never clobbers a live
data_source.json.
"""

import argparse
import json
import math
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    from src.clustering import (
        demand_pattern_stats,
        kmeans_crosscheck,
        summarise_clusters,
    )
    from src.forecast import (
        METHODS,
        aggregate_winner,
        backtest,
        build_forecast,
        select_cluster_winner,
        wape,
    )
    from src.reorder import build_reorder_list
except ImportError:  # running as a script from inside src/
    from clustering import (  # type: ignore[no-redef]
        demand_pattern_stats,
        kmeans_crosscheck,
        summarise_clusters,
    )
    from forecast import (  # type: ignore[no-redef]
        METHODS,
        aggregate_winner,
        backtest,
        build_forecast,
        select_cluster_winner,
        wape,
    )
    from reorder import build_reorder_list  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
DATA_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
DOI = "10.24432/C5BW33"
ATTRIBUTION = (
    "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5BW33"
)
FULL_WEEK_START = pd.Timestamp("2010-12-06")
FULL_WEEK_END = pd.Timestamp("2011-12-04")
N_FULL_WEEKS = 52
TRAIN_WEEKS = 48

ADJUSTMENT_STOCK_CODES = {
    "POST",
    "DOT",
    "M",
    "D",
    "BANK CHARGES",
    "CRUK",
    "C2",
    "AMAZONFEE",
}
ADJUSTMENT_DESCRIPTIONS = {
    "POSTAGE",
    "DISCOUNT",
    "MANUAL",
    "BANK CHARGES",
    "AMAZON FEE",
    "CRUK",
}


def download_retail_zip(url: str, dest: Path) -> Path:
    """One plain full download (server ignores Range headers)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt == 1:
                time.sleep(60)
                continue
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return dest
        except requests.RequestException:
            if attempt == 1:
                time.sleep(60)
                continue
            raise
    raise RuntimeError("download failed after one retry")


def load_raw_xlsx(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the plan §3.2 cleaning rules IN ORDER, counting exclusions."""
    counts: dict = {}
    raw_rows = len(df)
    counts["raw_rows"] = raw_rows
    counts["raw_columns"] = list(df.columns)
    work = df.copy().rename(
        columns={
            "InvoiceNo": "invoice_no",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "UnitPrice": "unit_price",
            "CustomerID": "customer_id",
            "Country": "country",
        }
    )
    work["invoice_date"] = pd.to_datetime(work["invoice_date"], errors="coerce")
    n_bad_dates = int(work["invoice_date"].isna().sum())
    counts["n_unparseable_dates"] = n_bad_dates
    work = work[work["invoice_date"].notna()]
    counts["date_range_raw"] = [
        str(work["invoice_date"].min()),
        str(work["invoice_date"].max()),
    ]
    counts["n_saturday_rows"] = int((work["invoice_date"].dt.day_of_week == 5).sum())
    invoice_no = work["invoice_no"].astype(str).str.strip()
    is_cancelled = invoice_no.str.startswith("C")
    counts["n_cancelled_rows"] = int(is_cancelled.sum())
    counts["n_cancelled_invoices"] = int(work.loc[is_cancelled, "invoice_no"].nunique())
    work = work[~is_cancelled]
    n_qty = int((work["quantity"] <= 0).sum())
    counts["n_nonpositive_quantity"] = n_qty
    work = work[work["quantity"] > 0]
    n_price = int((work["unit_price"] <= 0).sum())
    counts["n_nonpositive_price"] = n_price
    work = work[work["unit_price"] > 0]
    stock_code = work["stock_code"].astype(str).str.strip().str.upper()
    desc = work["description"].astype(str).str.strip().str.upper()
    is_adjustment = stock_code.isin(ADJUSTMENT_STOCK_CODES) | desc.isin(
        ADJUSTMENT_DESCRIPTIONS
    )
    counts["n_adjustment_rows"] = int(is_adjustment.sum())
    counts["adjustment_stock_codes_present"] = sorted(
        set(stock_code[is_adjustment].tolist())
    )
    counts["adjustment_stock_codes"] = sorted(ADJUSTMENT_STOCK_CODES)
    counts["adjustment_descriptions"] = sorted(ADJUSTMENT_DESCRIPTIONS)
    counts["adjustment_codes_added"] = []
    work = work[~is_adjustment]
    missing_desc = work["description"].isna() | (
        work["description"].astype(str).str.strip() == ""
    )
    counts["n_missing_description"] = int(missing_desc.sum())
    work = work[~missing_desc]
    work = work.copy()
    work["line_revenue"] = work["quantity"] * work["unit_price"]
    counts["n_missing_customer_id"] = int(work["customer_id"].isna().sum())
    counts["missing_customer_id_share"] = (
        float(counts["n_missing_customer_id"] / len(work)) if len(work) else 0.0
    )
    counts["cleaned_rows"] = len(work)
    counts["cleaned_revenue_gbp"] = float(work["line_revenue"].sum())
    counts["cleaned_units"] = int(work["quantity"].sum())
    counts["cleaned_orders"] = int(work["invoice_no"].nunique())
    counts["confirmed_date_range"] = [
        str(work["invoice_date"].min()),
        str(work["invoice_date"].max()),
    ]
    # Partial weeks: outside the 52 full weeks (plan §3.2 rule 9).
    in_full = (work["invoice_date"].dt.normalize() >= FULL_WEEK_START) & (
        work["invoice_date"].dt.normalize() <= FULL_WEEK_END
    )
    counts["n_partial_week_rows"] = int((~in_full).sum())
    counts["n_full_week_rows"] = int(in_full.sum())
    work = work.assign(
        week_start=(
            work["invoice_date"].dt.normalize()
            - pd.to_timedelta(work["invoice_date"].dt.day_of_week, unit="D")
        )
    )
    return work, counts


def build_weekly_demand(df: pd.DataFrame) -> pd.DataFrame:
    """Long weekly demand, 52 full weeks only (plan §4.1)."""
    full = df[
        (df["week_start"] >= FULL_WEEK_START) & (df["week_start"] <= FULL_WEEK_END)
    ]
    # Group by week + StockCode only: the same StockCode can carry more
    # than one Description spelling in the raw file, so grouping by
    # Description would split one SKU's demand across rows.
    desc_mode = full.groupby("stock_code")["description"].agg(
        lambda s: s.mode().iloc[0]
    )
    weekly = (
        full.groupby(["week_start", "stock_code"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "units"})
    )
    weekly["description"] = weekly["stock_code"].map(desc_mode)
    # Complete the 20×52 grid later in select_top_skus; here return observed.
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    return weekly.sort_values(["stock_code", "week_start"]).reset_index(drop=True)


def _full_week_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"week_start": pd.date_range(FULL_WEEK_START, periods=N_FULL_WEEKS, freq="7D")}
    )


def select_top_skus(
    df: pd.DataFrame, n: int = 20, min_weeks: int = 30
) -> tuple[pd.DataFrame, list, list]:
    """Rank SKUs by revenue over the 52 full weeks; enforce the coverage
    rule (>= min_weeks weeks with demand), replacing failures with the
    next-ranked passer. Returns (summary, selected_codes, replaced)."""
    full = df[
        (df["week_start"] >= FULL_WEEK_START) & (df["week_start"] <= FULL_WEEK_END)
    ].copy()
    # Rank by StockCode only (same Description-spelling issue as above).
    desc_mode = full.groupby("stock_code")["description"].agg(
        lambda s: s.mode().iloc[0]
    )
    revenue = (
        full.groupby("stock_code", as_index=False)["line_revenue"]
        .sum()
        .rename(columns={"line_revenue": "revenue_gbp"})
    )
    revenue["description"] = revenue["stock_code"].map(desc_mode)
    revenue = revenue.sort_values("revenue_gbp", ascending=False).reset_index(drop=True)
    total_revenue = float(revenue["revenue_gbp"].sum())
    # Weeks with demand: group weekly sums then count > 0.
    weekly_units = full.groupby(["week_start", "stock_code"], as_index=False)[
        "quantity"
    ].sum()
    weeks_with_demand = weekly_units.groupby("stock_code").size()
    selected: list[str] = []
    replaced: list[dict[str, Any]] = []
    for _, row in revenue.iterrows():
        if len(selected) >= n:
            break
        code = row["stock_code"]
        n_weeks = int(weeks_with_demand.get(code, 0))
        if n_weeks >= min_weeks:
            selected.append(code)
        else:
            replaced.append(
                {
                    "stock_code": code,
                    "description": row["description"],
                    "revenue_gbp": float(row["revenue_gbp"]),
                    "weeks_with_demand": n_weeks,
                    "reason": f"only {n_weeks} weeks with demand (< {min_weeks})",
                }
            )
    summary = revenue[revenue["stock_code"].isin(selected)].copy()
    summary["revenue_share"] = summary["revenue_gbp"] / total_revenue
    summary = summary.set_index("stock_code").loc[selected].reset_index()
    return summary, selected, replaced


def build_aggregate_demand(df: pd.DataFrame) -> pd.DataFrame:
    """52-row aggregate weekly units across all cleaned SKUs."""
    full = df[
        (df["week_start"] >= FULL_WEEK_START) & (df["week_start"] <= FULL_WEEK_END)
    ]
    agg = (
        full.groupby("week_start", as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "units"})
    )
    weeks = _full_week_frame()
    agg = weeks.merge(agg, on="week_start", how="left").fillna({"units": 0})
    agg["units"] = agg["units"].astype(int)
    return agg.sort_values("week_start").reset_index(drop=True)


def sanitise_json_value(value):
    """Recursively replace non-finite floats (NaN / +/-inf) with None.

    Python's json module writes bare NaN/Infinity literals, which are not
    strict JSON; sanitising here keeps every data_source.json write
    strict-JSON-safe. Values are unchanged — only the representation of
    "no value" changes from NaN to null.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: sanitise_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitise_json_value(v) for v in value]
    return value


def write_data_source(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sanitise_json_value(record), indent=2, default=str),
        encoding="utf-8",
    )


def _complete_weekly(weekly: pd.DataFrame, codes: list) -> pd.DataFrame:
    """Expand to the full 20 × 52 grid (zero weeks included)."""
    weeks = _full_week_frame()
    grid = weeks.merge(pd.DataFrame({"stock_code": codes}), how="cross")
    desc = weekly.drop_duplicates("stock_code").set_index("stock_code")["description"]
    out = grid.merge(weekly, on=["week_start", "stock_code"], how="left")
    out["units"] = out["units"].fillna(0).astype(int)
    out["description"] = out["stock_code"].map(desc)
    return out.sort_values(["stock_code", "week_start"]).reset_index(drop=True)


def _train_stats(
    weekly_complete: pd.DataFrame, clusters: dict | None = None
) -> pd.DataFrame:
    """Training-window (weeks 1-48) mean and sigma per SKU.

    Sigma uses non-zero weeks only for intermittent/lumpy SKUs (cluster
    taken from the 52-week classification when supplied).
    """
    train_weeks = pd.date_range(FULL_WEEK_START, periods=TRAIN_WEEKS, freq="7D")
    train = weekly_complete[weekly_complete["week_start"].isin(train_weeks)]
    rows = []
    for code, sub in train.groupby("stock_code"):
        vals = sub["units"].to_numpy(dtype=float)
        cluster = (clusters or {}).get(code, "smooth")
        if cluster in ("intermittent", "lumpy"):
            nz = vals[vals > 0]
            sigma = float(nz.std(ddof=1)) if len(nz) >= 2 else 0.0
        else:
            sigma = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
        rows.append(
            {
                "stock_code": code,
                "mean_weekly_train": float(vals.mean()),
                "sigma_weekly_train": sigma,
            }
        )
    return pd.DataFrame(rows)


def run_live(day_dir: Path, use_cache: bool = False) -> dict:
    """Full live build from the downloaded XLSX. Returns data_source record."""
    day_dir = Path(day_dir)
    raw_dir = day_dir / "data" / "raw"
    proc_dir = day_dir / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / "online_retail.zip"
    xlsx_path = raw_dir / "Online Retail.xlsx"
    if use_cache and xlsx_path.exists():
        pass
    elif use_cache and zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(raw_dir)
    else:
        download_retail_zip(DATA_URL, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(raw_dir)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"expected XLSX not found: {xlsx_path}")
    raw = load_raw_xlsx(xlsx_path)
    if len(raw) != 541909 or list(raw.columns) != [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]:
        raise ValueError(
            f"raw file check failed: {len(raw)} rows, columns {list(raw.columns)}"
        )
    cleaned, counts = clean_transactions(raw)
    weekly_obs = build_weekly_demand(cleaned)
    top_summary, selected, replaced = select_top_skus(cleaned)
    weekly = _complete_weekly(weekly_obs, selected)
    aggregate = build_aggregate_demand(cleaned)
    # Demand-pattern stats over ALL SKUs with any demand in the 52 weeks.
    all_stats = demand_pattern_stats(weekly_obs)
    cluster_summary = summarise_clusters(all_stats)
    # SKU summary for the top 20.
    top_stats = all_stats[all_stats["stock_code"].isin(selected)].set_index(
        "stock_code"
    )
    rev_map = dict(zip(top_summary["stock_code"], top_summary["revenue_gbp"]))
    total_rev_full = float(
        cleaned[
            (cleaned["week_start"] >= FULL_WEEK_START)
            & (cleaned["week_start"] <= FULL_WEEK_END)
        ]["line_revenue"].sum()
    )
    sku_summary = pd.DataFrame(
        {
            "stock_code": selected,
            "description": [str(top_stats.loc[c, "description"]) for c in selected],
            "revenue_gbp": [float(rev_map[c]) for c in selected],
            "revenue_share": [float(rev_map[c]) / total_rev_full for c in selected],
            "total_units": [float(top_stats.loc[c, "total_units"]) for c in selected],
            "weeks_with_demand": [
                int(top_stats.loc[c, "weeks_with_demand"]) for c in selected
            ],
            "mean_weekly_units": [
                float(top_stats.loc[c, "mean_weekly_units"]) for c in selected
            ],
            "adi": [float(top_stats.loc[c, "adi"]) for c in selected],
            "cv2": [float(top_stats.loc[c, "cv2"]) for c in selected],
            "cluster": [str(top_stats.loc[c, "cluster"]) for c in selected],
        }
    )
    # KMeans cross-check on the top 200 SKUs by revenue.
    # Revenue ranking for the top 200 SKUs.
    full = cleaned[
        (cleaned["week_start"] >= FULL_WEEK_START)
        & (cleaned["week_start"] <= FULL_WEEK_END)
    ]
    rev_rank = (
        full.groupby("stock_code")["line_revenue"].sum().sort_values(ascending=False)
    )
    top200_codes = list(rev_rank.head(200).index)
    top200_stats = all_stats[all_stats["stock_code"].isin(top200_codes)]
    _, agreement = kmeans_crosscheck(top200_stats)
    # Backtest on the full backtest table (all series) for winner selection.
    pivot = weekly.pivot_table(
        index="week_start", columns="stock_code", values="units", aggfunc="sum"
    ).fillna(0)
    pivot.index = pd.to_datetime(pivot.index)
    agg_series = aggregate.set_index("week_start")["units"]
    agg_series.index = pd.to_datetime(agg_series.index)
    all_backtest_rows = []
    for code in selected:
        bt = backtest(pivot[code])
        bt["stock_code"] = code
        bt["cluster"] = str(top_stats.loc[code, "cluster"])
        bt["actual_total"] = float(
            pivot[code].iloc[TRAIN_WEEKS : TRAIN_WEEKS + 4].sum()
        )
        all_backtest_rows.append(bt)
    bt_agg = backtest(agg_series)
    bt_agg["stock_code"] = "AGGREGATE"
    bt_agg["cluster"] = "aggregate"
    bt_agg["actual_total"] = float(agg_series.iloc[TRAIN_WEEKS : TRAIN_WEEKS + 4].sum())
    all_backtest_rows.append(bt_agg)
    all_bt = pd.concat(all_backtest_rows, ignore_index=True)
    winners = {}
    for cluster in ["smooth", "erratic", "intermittent", "lumpy"]:
        winners[cluster] = select_cluster_winner(all_bt, cluster)
    agg_winner = aggregate_winner(all_bt)
    forecast_df, full_bt = build_forecast(
        weekly, sku_summary, winners, agg_winner, aggregate=agg_series
    )
    # Published backtest CSV: committed columns only.
    backtest_csv = full_bt[
        ["origin", "method", "stock_code", "wape", "mae", "rmse", "bias"]
    ].copy()
    # Reorder list needs training-window stats.
    clusters_52 = dict(zip(sku_summary["stock_code"], sku_summary["cluster"]))
    train_stats = _train_stats(weekly, clusters=clusters_52)
    sku_enriched = sku_summary.merge(train_stats, on="stock_code", how="left")
    reorder_df = build_reorder_list(sku_enriched, forecast_df, winners)
    # In-sample vs holdout WAPE on the aggregate (naïve one-step check).
    insample = _insample_wape_aggregate(agg_series)
    # Write processed files.
    weekly.to_csv(proc_dir / "weekly_demand.csv", index=False)
    aggregate.to_csv(proc_dir / "weekly_aggregate.csv", index=False)
    sku_summary.to_csv(proc_dir / "sku_summary.csv", index=False)
    cluster_summary.to_csv(proc_dir / "cluster_summary.csv", index=False)
    forecast_df.to_csv(proc_dir / "forecast.csv", index=False)
    backtest_csv.to_csv(proc_dir / "backtest.csv", index=False)
    reorder_df.to_csv(proc_dir / "reorder_list.csv", index=False)
    # Sample: 1,000 cleaned rows, deterministic.
    sample = cleaned.sample(n=min(1000, len(cleaned)), random_state=42)
    sample_out = sample.drop(columns=["line_revenue", "week_start"]).copy()
    sample_out["invoice_date"] = sample_out["invoice_date"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    sample_out = sample_out.where(pd.notna(sample_out), None)
    (raw_dir / "sample_rows.json").write_text(
        json.dumps(sample_out.to_dict(orient="records"), indent=1, default=str),
        encoding="utf-8",
    )
    # Headline numbers.
    primary = full_bt[full_bt["origin"] == TRAIN_WEEKS]
    overall_wape = {}
    for method in METHODS:
        sub = primary[
            (primary["method"] == method) & (primary["stock_code"] != "AGGREGATE")
        ]
        if len(sub) and sub["wape"].notna().any():
            overall_wape[method] = _volume_weighted(sub)
    record = {
        "source": "live",
        "url": DATA_URL,
        "dataset_page": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "doi": DOI,
        "attribution": ATTRIBUTION,
        "licence": "CC BY 4.0",
        "fetch_timestamp": pd.Timestamp.now(tz="America/Los_Angeles").isoformat(),
        "raw_rows": counts["raw_rows"],
        "raw_columns": counts["raw_columns"],
        "page_feature_count_note": (
            "Dataset page header says '# Features 6' while the variables "
            "table lists 8 columns; the file itself is authoritative "
            "(8 columns verified)."
        ),
        "confirmed_date_range": counts["confirmed_date_range"],
        "n_saturday_rows": counts["n_saturday_rows"],
        "no_saturday_transactions": counts["n_saturday_rows"] == 0,
        "cleaning_counts_in_order": {
            "n_unparseable_dates": counts["n_unparseable_dates"],
            "n_cancelled_rows": counts["n_cancelled_rows"],
            "n_cancelled_invoices": counts["n_cancelled_invoices"],
            "n_nonpositive_quantity": counts["n_nonpositive_quantity"],
            "n_nonpositive_price": counts["n_nonpositive_price"],
            "n_adjustment_rows": counts["n_adjustment_rows"],
            "n_missing_description": counts["n_missing_description"],
        },
        "cleaned_rows": counts["cleaned_rows"],
        "cleaned_revenue_gbp": counts["cleaned_revenue_gbp"],
        "cleaned_units": counts["cleaned_units"],
        "cleaned_orders": counts["cleaned_orders"],
        "n_missing_customer_id": counts["n_missing_customer_id"],
        "missing_customer_id_share": counts["missing_customer_id_share"],
        "n_partial_week_rows": counts["n_partial_week_rows"],
        "n_full_week_rows": counts["n_full_week_rows"],
        "full_weeks": {
            "n_weeks": N_FULL_WEEKS,
            "first_week_start": str(FULL_WEEK_START.date()),
            "last_week_start": str((FULL_WEEK_END - pd.Timedelta(days=6)).date()),
            "last_week_end": "2011-12-04",
            "partial_first_week": "2010-12-01 to 2010-12-05 (excluded)",
            "partial_last_week": "2011-12-05 to 2011-12-09 (excluded)",
            "december_2011_partial_month": True,
        },
        "adjustment_stock_codes": counts["adjustment_stock_codes"],
        "adjustment_descriptions": counts["adjustment_descriptions"],
        "adjustment_codes_added": counts["adjustment_codes_added"],
        "top_20_selection": {
            "rule": "revenue-ranked over the 52 full weeks; demand in >= 30/52 weeks",
            "selected": selected,
            "replaced": replaced,
            "top_20_revenue_share": float(sku_summary["revenue_share"].sum()),
            "total_revenue_full_weeks_gbp": total_rev_full,
        },
        "clustering": {
            "method": "Syntetos-Boylan ADI/CV2",
            "adi_cutoff": 1.32,
            "cv2_cutoff": 0.49,
            "quadrant_counts": {
                row["cluster"]: int(row["n_skus"])
                for _, row in cluster_summary.iterrows()
            },
            "quadrant_unit_shares": {
                row["cluster"]: float(row["share_units"])
                for _, row in cluster_summary.iterrows()
            },
            "n_skus_with_demand": len(all_stats),
            "kmeans_crosscheck": {
                "k": 4,
                "top_n_skus": 200,
                "features": ["mean_weekly_units", "cv", "adi", "trend_slope"],
                "agreement_rate": float(agreement),
                "seed": 42,
            },
        },
        "all_sku_pattern_stats": [
            {
                "stock_code": str(r["stock_code"]),
                "adi": float(r["adi"]),
                "cv2": float(r["cv2"]),
                "cluster": str(r["cluster"]),
                "total_units": float(r["total_units"]),
            }
            for _, r in all_stats.iterrows()
        ],
        "methods": METHODS,
        "backtest": {
            "primary_origin": "train weeks 1-48, forecast weeks 49-52 (2011-11-07 to 2011-12-04)",
            "supplementary_origin": "train weeks 1-29, forecast weeks 30-33 (2011-06-27 to 2011-07-24)",
            "primary_metric": "WAPE",
            "overall_volume_weighted_wape_primary": overall_wape,
            "seasonal_naive_note": (
                "Seasonal naive is unavailable on both backtest origins "
                "(y(t-52) does not exist for a 52-week series); it falls "
                "back to naive, its WAPE is n/a and it never contends "
                "for winner selection."
            ),
            "in_sample_wape_aggregate": insample,
        },
        "winners_per_cluster": winners,
        "aggregate_winner": agg_winner,
        "reorder_assumptions": {
            "lead_time_weeks": 1,
            "review_period_weeks": 1,
            "service_level_smooth_erratic": 0.95,
            "z_smooth_erratic": 1.65,
            "service_level_intermittent_lumpy": 0.90,
            "z_intermittent_lumpy": 1.28,
            "safety_stock_formula": "SS = z * sigma * sqrt(lead time in weeks)",
            "sigma_window": "training weeks 1-48; non-zero weeks only for intermittent/lumpy",
            "on_hand_assumption": "zero on-hand; order-up-to level S is the deliverable",
            "forecast": "4-week trend extrapolation from one retailer, one year — NOT a seasonal prediction",
        },
        "synthetic": False,
        "versions": _versions(),
    }
    write_data_source(proc_dir / "data_source.json", record)
    return record


def _volume_weighted(frame: pd.DataFrame) -> float:
    weights = frame["actual_total"].to_numpy(dtype=float)
    wapes = frame["wape"].to_numpy(dtype=float)
    mask = ~np.isnan(wapes) & (weights > 0)
    return float(np.sum(wapes[mask] * weights[mask]) / np.sum(weights[mask]))


def _insample_wape_aggregate(series: pd.Series) -> dict:
    """One-step-ahead in-sample WAPE on the aggregate training window."""
    train = series.iloc[:TRAIN_WEEKS]
    vals = train.to_numpy(dtype=float)
    # None marks seasonal naïve as not defined here (the 48-week training
    # window has no lag-52 history); holt / gradient boosting use NaN for
    # "not computed cheaply". The distinction is preserved in the record.
    out: dict[str, float | None] = {}
    # Naïve one-step: forecast y[t] = y[t-1].
    out["naive"] = wape(vals[1:], vals[:-1])
    # 4-week moving average one-step.
    preds = np.array([np.mean(vals[max(0, t - 4) : t]) for t in range(4, len(vals))])
    out["moving_average"] = wape(vals[4:], preds)
    # Croston-SBA one-step (stateful, refit prefix each step — small series).
    from src.forecast import croston_sba_forecast  # local import for clarity

    croston_preds = []
    for t in range(4, len(vals)):
        croston_preds.append(float(croston_sba_forecast(train.iloc[:t], horizon=1)[0]))
    out["croston_sba"] = wape(vals[4:], np.array(croston_preds))
    # Holt / gradient boosting have no cheap one-step in-sample analogue
    # here; their holdout WAPE is the reported accuracy measure.
    out["holt"] = float("nan")
    out["gradient_boosting"] = float("nan")
    out["seasonal_naive"] = None
    return out


def _versions() -> dict:
    import matplotlib
    import sklearn
    import statsmodels

    return {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "scikit-learn": sklearn.__version__,
        "statsmodels": statsmodels.__version__,
        "openpyxl": __import__("openpyxl").__version__,
    }


def run_offline(day_dir: Path) -> None:
    """Regenerate derived tables/charts from committed CSVs.

    Never writes data_source.json when a live record already exists.
    """
    day_dir = Path(day_dir)
    proc_dir = day_dir / "data" / "processed"
    ds_path = proc_dir / "data_source.json"
    live_exists = False
    record = {}
    if ds_path.exists():
        record = json.loads(ds_path.read_text(encoding="utf-8"))
        live_exists = record.get("source") == "live"
    weekly = pd.read_csv(proc_dir / "weekly_demand.csv", parse_dates=["week_start"])
    aggregate = pd.read_csv(
        proc_dir / "weekly_aggregate.csv", parse_dates=["week_start"]
    )
    sku_summary = pd.read_csv(proc_dir / "sku_summary.csv")
    # Recompute backtest + forecast from the committed weekly series.
    agg_series = aggregate.set_index("week_start")["units"]
    agg_series.index = pd.to_datetime(agg_series.index)
    winners = record.get("winners_per_cluster", {}) if record else {}
    agg_winner = record.get("aggregate_winner", "naive") if record else "naive"
    if not winners:
        # Re-derive winners from a fresh backtest over the top 20.
        pivot = weekly.pivot_table(
            index="week_start", columns="stock_code", values="units", aggfunc="sum"
        ).fillna(0)
        rows = []
        for code in sku_summary["stock_code"]:
            bt = backtest(pivot[code])
            bt["stock_code"] = code
            bt["cluster"] = str(
                sku_summary.loc[sku_summary["stock_code"] == code, "cluster"].iloc[0]
            )
            bt["actual_total"] = float(
                pivot[code].iloc[TRAIN_WEEKS : TRAIN_WEEKS + 4].sum()
            )
            rows.append(bt)
        bt_agg = backtest(agg_series)
        bt_agg["stock_code"] = "AGGREGATE"
        bt_agg["cluster"] = "aggregate"
        bt_agg["actual_total"] = float(
            agg_series.iloc[TRAIN_WEEKS : TRAIN_WEEKS + 4].sum()
        )
        rows.append(bt_agg)
        all_bt = pd.concat(rows, ignore_index=True)
        winners = {
            c: select_cluster_winner(all_bt, c)
            for c in ["smooth", "erratic", "intermittent", "lumpy"]
        }
        agg_winner = aggregate_winner(all_bt)
    forecast_df, full_bt = build_forecast(
        weekly, sku_summary, winners, agg_winner, aggregate=agg_series
    )
    backtest_csv = full_bt[
        ["origin", "method", "stock_code", "wape", "mae", "rmse", "bias"]
    ].copy()
    forecast_df.to_csv(proc_dir / "forecast.csv", index=False)
    backtest_csv.to_csv(proc_dir / "backtest.csv", index=False)
    # Reorder list: training stats from the committed weekly series.
    clusters_52 = dict(zip(sku_summary["stock_code"], sku_summary["cluster"]))
    train_stats = _train_stats(weekly, clusters=clusters_52)
    sku_enriched = sku_summary.merge(train_stats, on="stock_code", how="left")
    reorder_df = build_reorder_list(sku_enriched, forecast_df, winners)
    reorder_df.to_csv(proc_dir / "reorder_list.csv", index=False)
    # Charts from the processed CSVs.
    sys.path.insert(0, str(day_dir))
    from src.make_charts import build_charts

    build_charts(day_dir)
    if not live_exists and not ds_path.exists():
        write_data_source(
            ds_path,
            {
                "source": "offline",
                "note": "Regenerated offline from committed CSVs; no live fetch.",
                "synthetic": False,
            },
        )
    # If a live record exists, data_source.json is left byte-identical.


def generate_synthetic(day_dir: Path) -> Path:
    """Synthetic fallback (seed 42) — only when explicitly authorised.

    Never overwrites real data; output is git-ignored.
    """
    rng = np.random.default_rng(42)
    weeks = pd.date_range(FULL_WEEK_START, periods=N_FULL_WEEKS, freq="7D")
    rows = []
    for i in range(20):
        base = float(rng.lognormal(mean=4.0, sigma=0.8))
        for w, week in enumerate(weeks):
            uplift = 1.4 if week.month == 12 else 1.0
            lam = base * uplift * (1 + 0.02 * w)
            units = int(rng.poisson(lam)) if rng.random() > 0.1 else 0
            rows.append(
                {
                    "week_start": week.strftime("%Y-%m-%d"),
                    "stock_code": f"SYN{i:03d}",
                    "description": f"Synthetic SKU {i}",
                    "units": units,
                }
            )
    out = Path(day_dir) / "data" / "raw" / "weekly_synthetic.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Day 11 data pipeline")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--use-cache", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--day-dir", type=str, default=str(ROOT))
    args = parser.parse_args(argv)
    day_dir = Path(args.day_dir)
    if args.synthetic:
        path = generate_synthetic(day_dir)
        print(f"synthetic written to {path} (SYNTHETIC — NOT REAL DATA)")
        return 0
    if args.offline:
        run_offline(day_dir)
        print("offline regeneration complete (data_source.json untouched if live)")
        return 0
    run_live(day_dir, use_cache=args.use_cache)
    print("live build complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
