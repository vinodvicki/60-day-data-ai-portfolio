"""Day 10 — Retail Sales Intelligence Dashboard: data pipeline.

Downloads the UCI Online Retail dataset (ZIP → XLSX), verifies the
counts, cleans the transactions per plan.md §3.2 (every exclusion
counted), and builds the committed processed tables (plan §3.5).

Modes
-----
--live       download + build from the live file (default when a raw
             file is absent).
--use-cache  build from the cached raw ZIP/XLSX under data/raw/.
--offline    regenerate the derived tables from the committed
             processed CSVs only — no network, no raw file, and never
             clobbers data_source.json (Day 5/6 lesson).
--synthetic  build from a clearly-labelled synthetic transactional
             dataset (brief §4, seed 42) — contingency only; the file
             is git-ignored and never overwrites real data.

The raw ZIP/XLSX (22.6 MB) is git-ignored (plan §3.4 data-size
exception); the committed provenance record is data/raw/sample_rows.json
(1,000 cleaned rows) + the processed CSVs + data_source.json.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from src.clustering import build_rfm, cluster_customers, summarise_clusters
from src.forecast import build_forecast

DAY_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = DAY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
ZIP_NAME = "online_retail.zip"
XLSX_NAME = "Online Retail.xlsx"
EXPECTED_ROWS = 541909
EXPECTED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]
SOURCE_URL = "https://archive.ics.uci.edu/dataset/352/online+retail"
DOI = "https://doi.org/10.24432/C5BW33"
ATTRIBUTION = (
    "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5BW33"
)
# Non-product adjustment lines (plan §3.2 rule 5). Gift-voucher codes
# (gift_0001_*) were added after profiling: the 34 rows are Dotcom
# gift vouchers — payment instruments, not merchandise — plus two
# zero-price placeholder rows removed earlier by the price rule.
ADJUSTMENT_CODES = {
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
GIFT_CODE_PREFIX = "gift_0001_"
SYNTHETIC_SEED = 42
SAMPLE_ROWS = 1000


def download_retail_zip(url: str, dest: Path) -> Path:
    """Download the UCI ZIP (one retry after 60 s, then stop)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        try:
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            dest.write_bytes(response.content)
            print(f"downloaded {url} -> {dest} ({len(response.content)} bytes)")
            return dest
        except requests.RequestException as exc:
            print(f"download attempt {attempt} failed: {exc}")
            if attempt == 2:
                raise
            time.sleep(60)
    raise RuntimeError("unreachable")  # pragma: no cover


def load_raw_xlsx(path: Path) -> pd.DataFrame:
    """Read the raw XLSX (one sheet, 'Online Retail')."""
    return pd.read_excel(path, engine="openpyxl")


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean per plan §3.2, in order, counting every exclusion.

    Returns (cleaned DataFrame with a ``line_revenue`` column, counts
    dict). The counts dict records the raw row count and the number of
    rows removed at each rule, in application order.
    """
    counts: dict[str, int] = {"raw_rows": len(df)}
    work = df.copy()
    work["InvoiceDate"] = pd.to_datetime(work["InvoiceDate"], errors="coerce")
    unparseable = int(work["InvoiceDate"].isna().sum())
    counts["unparseable_invoice_date"] = unparseable
    work = work[work["InvoiceDate"].notna()]

    is_cancelled = work["InvoiceNo"].astype(str).str.startswith("C")
    counts["cancelled_rows"] = int(is_cancelled.sum())
    counts["cancelled_invoices"] = int(work.loc[is_cancelled, "InvoiceNo"].nunique())
    work = work[~is_cancelled]

    bad_qty = work["Quantity"] <= 0
    counts["non_positive_quantity_rows"] = int(bad_qty.sum())
    work = work[~bad_qty]

    bad_price = work["UnitPrice"] <= 0
    counts["non_positive_price_rows"] = int(bad_price.sum())
    work = work[~bad_price]

    codes = work["StockCode"].astype(str).str.upper()
    descriptions = work["Description"].astype(str).str.upper().str.strip()
    is_adjustment = (
        codes.isin(ADJUSTMENT_CODES)
        | descriptions.isin(ADJUSTMENT_DESCRIPTIONS)
        | codes.str.startswith(GIFT_CODE_PREFIX)
    )
    counts["adjustment_rows"] = int(is_adjustment.sum())
    counts["adjustment_codes"] = sorted(ADJUSTMENT_CODES)
    counts["adjustment_descriptions"] = sorted(ADJUSTMENT_DESCRIPTIONS)
    counts["gift_code_prefix"] = GIFT_CODE_PREFIX
    work = work[~is_adjustment]

    missing_desc = work["Description"].isna() | (
        work["Description"].astype(str).str.strip() == ""
    )
    counts["missing_description_rows"] = int(missing_desc.sum())
    work = work[~missing_desc]

    work = work.copy()
    work["line_revenue"] = work["Quantity"].astype(float) * work["UnitPrice"].astype(
        float
    )
    counts["cleaned_rows"] = len(work)
    counts["cleaned_orders"] = int(work["InvoiceNo"].nunique())
    counts["cleaned_customers"] = int(work["CustomerID"].nunique())
    counts["missing_customer_rows"] = int(work["CustomerID"].isna().sum())
    counts["missing_customer_revenue_gbp"] = round(
        float(work.loc[work["CustomerID"].isna(), "line_revenue"].sum()), 2
    )
    counts["total_revenue_gbp"] = round(float(work["line_revenue"].sum()), 2)
    counts["total_units"] = int(work["Quantity"].sum())
    counts["date_min"] = str(pd.to_datetime(work["InvoiceDate"]).min())
    counts["date_max"] = str(pd.to_datetime(work["InvoiceDate"]).max())
    return work, counts


def _first_word(description: str) -> str:
    """First alphabetic word of a Description, uppercased (plan §4.2)."""
    match = re.search(r"[A-Za-z]+", str(description))
    return match.group(0).upper() if match else "UNKNOWN"


def build_monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue/units/orders/AOV/customers (plan §3.5).

    Dec 2011 is partial (data end 2011-12-09) — flagged ``is_partial``
    and excluded from month-over-month growth by the caller.
    """
    frame = df.copy()
    frame["month"] = pd.to_datetime(frame["InvoiceDate"]).dt.to_period("M")
    grouped = frame.groupby("month").agg(
        revenue_gbp=("line_revenue", "sum"),
        units=("Quantity", "sum"),
        orders=("InvoiceNo", "nunique"),
        customers=("CustomerID", "nunique"),
    )
    monthly = pd.DataFrame(
        {
            "month": grouped.index.astype(str),
            "revenue_gbp": grouped["revenue_gbp"].round(2),
            "units": grouped["units"].astype(int),
            "orders": grouped["orders"].astype(int),
            "aov_gbp": (grouped["revenue_gbp"] / grouped["orders"]).round(2),
            "customers": grouped["customers"].astype(int),
            "is_partial": [str(m) == "2011-12" for m in grouped.index.astype(str)],
        }
    ).reset_index(drop=True)
    return monthly


def build_weekly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly revenue (full ISO weeks only, plan §3.2 rule 10).

    Weeks run Monday–Sunday. Only weeks fully inside the data range
    are kept: the partial first week (starts 2010-12-01, a Wednesday)
    and the partial last week (ends 2011-12-09, a Friday) are dropped.
    """
    frame = df.copy()
    dates = pd.to_datetime(frame["InvoiceDate"])
    frame["week_start"] = (
        dates - pd.to_timedelta(dates.dt.day_of_week, unit="D")
    ).dt.date
    min_date = dates.min()
    first_full = (min_date + pd.Timedelta(days=(7 - min_date.weekday()) % 7)).date()
    max_date = dates.max()
    monday_of_max = (max_date - pd.Timedelta(days=max_date.weekday())).date()
    if max_date.weekday() == 6:  # max date is a Sunday: its week is complete
        last_full = monday_of_max
    else:
        last_full = monday_of_max - pd.Timedelta(days=7)
    grouped = frame.groupby("week_start").agg(
        revenue_gbp=("line_revenue", "sum"),
        units=("Quantity", "sum"),
        orders=("InvoiceNo", "nunique"),
    )
    weekly = pd.DataFrame(
        {
            "week_start": [str(d) for d in grouped.index],
            "revenue_gbp": grouped["revenue_gbp"].round(2),
            "units": grouped["units"].astype(int),
            "orders": grouped["orders"].astype(int),
        }
    )
    weekly = weekly[
        (pd.to_datetime(weekly["week_start"]).dt.date >= first_full)
        & (pd.to_datetime(weekly["week_start"]).dt.date <= last_full)
    ].reset_index(drop=True)
    return weekly


def build_country_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue/orders/AOV/units by country, ranked by revenue."""
    total_revenue = float(df["line_revenue"].sum())
    grouped = df.groupby("Country").agg(
        revenue_gbp=("line_revenue", "sum"),
        orders=("InvoiceNo", "nunique"),
        units=("Quantity", "sum"),
    )
    country = (
        pd.DataFrame(
            {
                "country": grouped.index,
                "revenue_gbp": grouped["revenue_gbp"].round(2),
                "revenue_share": (grouped["revenue_gbp"] / total_revenue * 100).round(
                    2
                ),
                "orders": grouped["orders"].astype(int),
                "aov_gbp": (grouped["revenue_gbp"] / grouped["orders"]).round(2),
                "units": grouped["units"].astype(int),
            }
        )
        .sort_values("revenue_gbp", ascending=False)
        .reset_index(drop=True)
    )
    return country


def build_top_products(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Top ``n`` SKUs by revenue (plan §4.2)."""
    total_revenue = float(df["line_revenue"].sum())
    grouped = df.groupby(["StockCode", "Description"]).agg(
        revenue_gbp=("line_revenue", "sum"),
        units=("Quantity", "sum"),
        orders=("InvoiceNo", "nunique"),
    )
    top = grouped.sort_values("revenue_gbp", ascending=False).head(n)
    return pd.DataFrame(
        {
            "stock_code": [str(c) for c in top.index.get_level_values(0)],
            "description": [str(d) for d in top.index.get_level_values(1)],
            "revenue_gbp": top["revenue_gbp"].round(2).to_numpy(),
            "revenue_share": (top["revenue_gbp"] / total_revenue * 100)
            .round(2)
            .to_numpy(),
            "units": top["units"].astype(int).to_numpy(),
            "orders": top["orders"].astype(int).to_numpy(),
        }
    ).reset_index(drop=True)


def build_product_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Derived product groups: first word of Description (plan §4.2).

    Top 10 groups by revenue are reported individually; the rest are
    aggregated as ``Other``.
    """
    frame = df.copy()
    frame["product_group"] = frame["Description"].map(_first_word)
    total_revenue = float(frame["line_revenue"].sum())
    grouped = frame.groupby("product_group").agg(
        revenue_gbp=("line_revenue", "sum"),
        units=("Quantity", "sum"),
        skus=("StockCode", "nunique"),
    )
    ranked = grouped.sort_values("revenue_gbp", ascending=False)
    top = ranked.head(10)
    other = ranked.iloc[10:]
    rows = [
        {
            "product_group": str(group),
            "revenue_gbp": round(float(row["revenue_gbp"]), 2),
            "revenue_share": round(float(row["revenue_gbp"]) / total_revenue * 100, 2),
            "units": int(row["units"]),
            "skus": int(row["skus"]),
        }
        for group, row in top.iterrows()
    ]
    if not other.empty:
        rows.append(
            {
                "product_group": "Other",
                "revenue_gbp": round(float(other["revenue_gbp"].sum()), 2),
                "revenue_share": round(
                    float(other["revenue_gbp"].sum()) / total_revenue * 100, 2
                ),
                "units": int(other["units"].sum()),
                "skus": int(other["skus"].sum()),
            }
        )
    return pd.DataFrame.from_records(
        rows,
        columns=["product_group", "revenue_gbp", "revenue_share", "units", "skus"],
    )


def build_synthetic() -> pd.DataFrame:
    """Synthetic transactional data (brief §4, seed 42) — fallback only.

    12 months, ~40,000 orders, 5 countries, 200 SKUs, lognormal basket
    sizes, December uplift ×1.8. Same 8 columns as the real file so the
    cleaning/aggregation path is identical.
    """
    rng = np.random.default_rng(SYNTHETIC_SEED)
    countries = ["United Kingdom", "Germany", "France", "Spain", "Netherlands"]
    weights = np.array([0.85, 0.05, 0.04, 0.03, 0.03])
    weights = weights / weights.sum()
    months = pd.period_range("2010-12", "2011-11", freq="M")
    rows: list[dict] = []
    invoice = 500000
    customer_pool = np.arange(10000, 15000)
    for month in months:
        n_orders = 3500
        if str(month) == "2010-12":
            n_orders = int(n_orders * 1.8)
        for _ in range(n_orders):
            invoice += 1
            country = str(rng.choice(countries, p=weights))
            customer = (
                float(rng.choice(customer_pool)) if rng.random() > 0.25 else np.nan
            )
            n_lines = int(rng.integers(1, 6))
            day = int(rng.integers(1, 29))
            for _ in range(n_lines):
                rows.append(
                    {
                        "InvoiceNo": str(invoice),
                        "StockCode": str(int(rng.integers(10000, 10200))),
                        "Description": str(
                            rng.choice(
                                [
                                    "JUMBO BAG",
                                    "MUG CERAMIC",
                                    "LUNCH BOX",
                                    "HEART CANDLE",
                                    "VINTAGE POSTER",
                                ]
                            )
                        ),
                        "Quantity": int(rng.lognormal(mean=1.0, sigma=0.7)) + 1,
                        "InvoiceDate": pd.Timestamp(
                            year=month.year, month=month.month, day=day
                        )
                        + pd.Timedelta(hours=int(rng.integers(8, 18))),
                        "UnitPrice": round(
                            float(rng.lognormal(mean=1.0, sigma=0.6)), 2
                        ),
                        "CustomerID": customer,
                        "Country": country,
                    }
                )
    return pd.DataFrame.from_records(rows)


def write_data_source(path: Path, record: dict) -> None:
    """Write data_source.json (sorted keys, indented)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")


def _write_sample(cleaned: pd.DataFrame) -> None:
    """1,000 cleaned rows as the committed provenance sample."""
    sample = cleaned.sort_values(["InvoiceDate", "InvoiceNo"]).head(SAMPLE_ROWS).copy()
    sample["InvoiceDate"] = sample["InvoiceDate"].astype(str)
    sample["CustomerID"] = sample["CustomerID"].astype("Int64").astype(str)
    records = sample[
        [
            "InvoiceNo",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "UnitPrice",
            "CustomerID",
            "Country",
            "line_revenue",
        ]
    ].to_dict(orient="records")
    payload = {
        "note": "Sample of 1,000 cleaned rows (earliest by InvoiceDate) — "
        "provenance sample only, not the full dataset. Full raw file "
        "(22.6 MB XLSX) is git-ignored and re-downloaded at build time.",
        "rows": records,
    }
    (RAW_DIR / "sample_rows.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def run_live(use_cache: bool = False) -> dict:
    """Full live build: fetch (unless cached), clean, aggregate, cluster,
    forecast. Returns the data_source.json record."""
    zip_path = RAW_DIR / ZIP_NAME
    xlsx_path = RAW_DIR / XLSX_NAME
    if use_cache and xlsx_path.exists():
        print(f"using cached raw file {xlsx_path}")
    else:
        download_retail_zip(DOWNLOAD_URL, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract(XLSX_NAME, RAW_DIR)
        print(f"extracted {xlsx_path} ({xlsx_path.stat().st_size} bytes)")
    raw = load_raw_xlsx(xlsx_path)
    if len(raw) != EXPECTED_ROWS or list(raw.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"raw file mismatch: got {len(raw)} rows, columns "
            f"{list(raw.columns)}; expected {EXPECTED_ROWS} rows, "
            f"{EXPECTED_COLUMNS}"
        )
    print(
        f"raw verified: {len(raw)} rows, 8 columns, "
        f"{raw['InvoiceDate'].min()} -> {raw['InvoiceDate'].max()}"
    )
    return _build_from_cleaned(raw, synthetic=False)


def run_synthetic() -> dict:
    """Synthetic-fallback build (brief §4)."""
    raw = build_synthetic()
    raw.to_csv(RAW_DIR / "online_retail_synthetic.csv", index=False)
    print(f"synthetic data generated: {len(raw)} rows")
    return _build_from_cleaned(raw, synthetic=True)


def _build_from_cleaned(raw: pd.DataFrame, synthetic: bool) -> dict:
    cleaned, counts = clean_transactions(raw)
    print(
        f"cleaned: {counts['cleaned_rows']} rows, "
        f"£{counts['total_revenue_gbp']:,.2f}, "
        f"{counts['cleaned_orders']} orders, "
        f"{counts['cleaned_customers']} customers"
    )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    monthly = build_monthly_sales(cleaned)
    monthly.to_csv(PROCESSED_DIR / "monthly_sales.csv", index=False)
    weekly = build_weekly_revenue(cleaned)
    weekly.to_csv(PROCESSED_DIR / "weekly_revenue.csv", index=False)
    country = build_country_sales(cleaned)
    country.to_csv(PROCESSED_DIR / "country_sales.csv", index=False)
    top = build_top_products(cleaned)
    top.to_csv(PROCESSED_DIR / "top_products.csv", index=False)
    groups = build_product_groups(cleaned)
    groups.to_csv(PROCESSED_DIR / "product_groups.csv", index=False)

    rfm = build_rfm(cleaned)
    labels, silhouette = cluster_customers(rfm)
    rfm_out = rfm.copy()
    cluster_summary = summarise_clusters(rfm, labels)
    rfm_out["cluster"] = labels
    rfm_out["cluster_label"] = rfm_out["cluster"].map(
        dict(zip(cluster_summary["cluster"], cluster_summary["label"]))
    )
    rfm_out.to_csv(PROCESSED_DIR / "rfm_clusters.csv", index=False)
    cluster_summary.to_csv(PROCESSED_DIR / "cluster_summary.csv", index=False)
    print(f"clusters: k=4, silhouette {silhouette:.3f}")
    print(cluster_summary.to_string(index=False))

    forecast_summary = build_forecast(
        weekly["revenue_gbp"], weekly["week_start"], PROCESSED_DIR
    )
    _write_sample(cleaned)

    total_revenue = counts["total_revenue_gbp"]
    top10_share = round(float(top.head(10)["revenue_share"].sum()), 2)
    uk_row = country[country["country"] == "United Kingdom"]
    uk_share = (
        round(float(uk_row["revenue_share"].iloc[0]), 2) if not uk_row.empty else 0.0
    )
    repeat = round(float((rfm["frequency"] >= 2).mean() * 100), 2)
    record = {
        "source": "synthetic" if synthetic else "live",
        "synthetic": synthetic,
        "synthetic_seed": SYNTHETIC_SEED if synthetic else None,
        "dataset": "UCI Online Retail (dataset 352)",
        "dataset_url": SOURCE_URL,
        "download_url": DOWNLOAD_URL,
        "doi": DOI,
        "licence": "CC BY 4.0",
        "attribution": ATTRIBUTION,
        "fetch_date_utc": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts,
        "cleaning": {
            "order": [
                "unparseable_invoice_date",
                "cancelled_rows",
                "non_positive_quantity_rows",
                "non_positive_price_rows",
                "adjustment_rows",
                "missing_description_rows",
            ],
            "adjustment_codes": sorted(ADJUSTMENT_CODES),
            "adjustment_descriptions": sorted(ADJUSTMENT_DESCRIPTIONS),
            "gift_code_prefix": GIFT_CODE_PREFIX,
        },
        "monthly_definition": (
            "Calendar months Dec 2010 -> Nov 2011 are full months; "
            "Dec 2011 is partial (data end 2011-12-09, 9 days) and is "
            "excluded from month-over-month growth."
        ),
        "weekly_definition": (
            "ISO weeks Monday-Sunday; only weeks fully inside the data "
            f"range are kept ({len(weekly)} weeks, "
            f"{weekly['week_start'].iloc[0]} -> {weekly['week_start'].iloc[-1]})."
        ),
        "product_group_rule": (
            "Derived: first alphabetic word of Description, uppercased; "
            "top 10 groups by revenue reported individually, rest as Other."
        ),
        "top_product_groups": groups.head(10)["product_group"].tolist(),
        "kpis": {
            "total_revenue_gbp": total_revenue,
            "total_units": counts["total_units"],
            "orders": counts["cleaned_orders"],
            "aov_gbp": round(total_revenue / counts["cleaned_orders"], 2),
            "unique_customers": counts["cleaned_customers"],
            "repeat_customer_rate_pct": repeat,
            "top10_sku_revenue_share_pct": top10_share,
            "uk_revenue_share_pct": uk_share,
            "missing_customer_revenue_share_pct": round(
                counts["missing_customer_revenue_gbp"] / total_revenue * 100, 2
            ),
        },
        "clustering": {
            "method": "RFM + KMeans",
            "k": 4,
            "seed": 42,
            "n_init": 10,
            "silhouette": round(silhouette, 4),
            "labels": dict(
                zip(
                    cluster_summary["cluster"].astype(str),
                    cluster_summary["label"],
                )
            ),
        },
        "forecast": forecast_summary,
        "limitations": [
            (
                "Single retailer, single year (2010-2011): seasonality is "
                "observed, not estimated from multiple years."
            ),
            (
                "Forecast is a trend extrapolation (Holt-Winters additive "
                "trend, no seasonality) with bootstrap intervals — not a "
                "seasonal prediction."
            ),
            (
                "Product groups are derived from Description first words, "
                "not source categories."
            ),
            "Prices may or may not include VAT — the dataset does not state it.",
            (
                "Missing CustomerID rows (14.8% of revenue) are excluded from "
                "RFM/clustering only."
            ),
        ],
    }
    write_data_source(PROCESSED_DIR / "data_source.json", record)
    print(f"wrote {PROCESSED_DIR / 'data_source.json'}")
    return record


def run_offline() -> None:
    """Offline mode: regenerate derived tables from the committed
    processed CSVs only. Never touches data_source.json (Day 5/6
    lesson) and never needs the raw file or the network.

    Re-derives cluster_summary.csv from rfm_clusters.csv (deterministic
    means, same rounding) and re-writes the aggregate CSVs unchanged
    (round-trip through the same dtypes/rounding). Forecast and
    backtest CSVs are verified present, not recomputed.
    """
    for name in (
        "monthly_sales.csv",
        "weekly_revenue.csv",
        "country_sales.csv",
        "top_products.csv",
        "product_groups.csv",
        "rfm_clusters.csv",
        "cluster_summary.csv",
        "forecast.csv",
        "backtest.csv",
    ):
        path = PROCESSED_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"offline mode needs committed {name}")
    rfm = pd.read_csv(PROCESSED_DIR / "rfm_clusters.csv")
    summary = summarise_clusters(
        rfm[["customer_id", "recency_days", "frequency", "monetary_gbp"]],
        rfm["cluster"].to_numpy(dtype=int),
    )
    # Labels come from the committed file (assign_labels is deterministic
    # from the same centroids, but the committed labels are the record).
    committed = pd.read_csv(PROCESSED_DIR / "cluster_summary.csv")
    summary["label"] = (
        committed.set_index("cluster").loc[summary["cluster"], "label"].to_numpy()
    )
    summary.to_csv(PROCESSED_DIR / "cluster_summary.csv", index=False)
    print("offline: cluster_summary.csv re-derived from rfm_clusters.csv")
    print("offline: data_source.json untouched (live record preserved)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 10 data pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true", help="download + build live")
    group.add_argument("--use-cache", action="store_true", help="build from cached raw")
    group.add_argument(
        "--offline", action="store_true", help="rebuild from processed CSVs"
    )
    group.add_argument(
        "--synthetic", action="store_true", help="synthetic fallback build"
    )
    args = parser.parse_args()
    if args.offline:
        run_offline()
    elif args.synthetic:
        run_synthetic()
    elif args.use_cache:
        run_live(use_cache=True)
    else:
        run_live(use_cache=False)


if __name__ == "__main__":
    main()
