"""Data pipeline for Day 12 — Customer Segmentation Engine.

One plain full download of the UCI Online Retail CSV (primary; legacy
XLSX fallback), ordered cleaning with every exclusion counted, RFM per
customer, percentile-rank scoring, KMeans segmentation (the decider,
plan §2.0), SBC cross-check, segment profile + actions, and the
committed processed files + data_source.json. Offline mode regenerates
the derived tables/charts from the committed CSVs and never clobbers a
live data_source.json.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:
    from src.actions import build_actions
    from src.clustering import (
        agreement_rate,
        build_agreement_table,
        build_sbc_summary,
        build_segment_profile,
        choose_k,
        cluster_customers,
        name_segments,
        sbc_stats,
        select_k,
    )
    from src.rfm import compute_rfm, score_rfm
except ImportError:  # running as a script from inside src/
    from actions import build_actions  # type: ignore[no-redef]
    from clustering import (  # type: ignore[no-redef]
        agreement_rate,
        build_agreement_table,
        build_sbc_summary,
        build_segment_profile,
        choose_k,
        cluster_customers,
        name_segments,
        sbc_stats,
        select_k,
    )
    from rfm import compute_rfm, score_rfm  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
CSV_URL = "https://archive.ics.uci.edu/static/public/352/data.csv"
XLSX_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/"
    "Online%20Retail.xlsx"
)
DOI = "10.24432/C5BW33"
ATTRIBUTION = (
    "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5BW33"
)
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


def download_retail_csv(url: str, dest: Path) -> Path:
    """One plain full download (server ignores Range headers).

    One retry after 60 s on HTTP 429/5xx, then raise.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        try:
            resp = requests.get(url, timeout=300)
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


def load_raw_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="ISO-8859-1")


def load_raw_xlsx(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")


def _verify_raw(raw: pd.DataFrame) -> None:
    if len(raw) != 541909 or list(raw.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"raw file check failed: {len(raw)} rows, columns {list(raw.columns)}"
        )


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the plan §3.2 cleaning rules IN ORDER, counting exclusions."""
    counts: dict = {}
    counts["raw_rows"] = len(df)
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
    # NOTE: the plan (§3.1) says dayfirst=True, but the CSV file itself
    # uses M/D/YYYY ("12/1/2010 8:26" = 1 Dec 2010). Parsing with
    # dayfirst=True drops 308,950 rows as unparseable and shifts the
    # range to 2010-01-12. The file is authoritative: dayfirst=False
    # gives 0 unparseable dates and the published range
    # 2010-12-01 → 2011-12-09, matching Days 10–11 (XLSX datetimes).
    work["invoice_date"] = pd.to_datetime(
        work["invoice_date"], errors="coerce", dayfirst=False
    )
    counts["n_unparseable_dates"] = int(work["invoice_date"].isna().sum())
    work = work[work["invoice_date"].notna()]
    counts["date_range_raw"] = [
        str(work["invoice_date"].min()),
        str(work["invoice_date"].max()),
    ]
    invoice_no = work["invoice_no"].astype(str).str.strip()
    is_cancelled = invoice_no.str.startswith("C")
    counts["n_cancelled_rows"] = int(is_cancelled.sum())
    counts["n_cancelled_invoices"] = int(work.loc[is_cancelled, "invoice_no"].nunique())
    work = work[~is_cancelled]
    counts["n_nonpositive_quantity"] = int((work["quantity"] <= 0).sum())
    work = work[work["quantity"] > 0]
    counts["n_nonpositive_price"] = int((work["unit_price"] <= 0).sum())
    work = work[work["unit_price"] > 0]
    stock_code = work["stock_code"].astype(str).str.strip().str.upper()
    desc_upper = work["description"].astype(str).str.strip().str.upper()
    is_adjustment = stock_code.isin(ADJUSTMENT_STOCK_CODES) | desc_upper.isin(
        ADJUSTMENT_DESCRIPTIONS
    )
    counts["n_adjustment_rows"] = int(is_adjustment.sum())
    counts["adjustment_stock_codes_present"] = sorted(
        set(stock_code[is_adjustment].tolist())
    )
    counts["adjustment_descriptions_present"] = sorted(
        set(desc_upper[is_adjustment].tolist())
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
    missing_cust = work["customer_id"].isna()
    counts["n_missing_customer_id"] = int(missing_cust.sum())
    counts["missing_customer_id_share"] = (
        float(counts["n_missing_customer_id"] / len(work)) if len(work) else 0.0
    )
    counts["revenue_missing_customer_gbp"] = float(
        work.loc[missing_cust, "line_revenue"].sum()
    )
    counts["cleaned_rows"] = len(work)
    counts["cleaned_revenue_gbp"] = float(work["line_revenue"].sum())
    counts["cleaned_units"] = int(work["quantity"].sum())
    counts["cleaned_orders"] = int(work["invoice_no"].nunique())
    counts["confirmed_date_range"] = [
        str(work["invoice_date"].min()),
        str(work["invoice_date"].max()),
    ]
    counts["revenue_missing_customer_share"] = (
        float(counts["revenue_missing_customer_gbp"] / counts["cleaned_revenue_gbp"])
        if counts["cleaned_revenue_gbp"]
        else 0.0
    )
    return work, counts


def sanitise_json_value(value):
    """Recursively replace non-finite floats (NaN / +/-inf) with None.

    Python's json module writes bare NaN/Infinity literals, which are not
    strict JSON; sanitising here keeps every data_source.json write
    strict-JSON-safe.
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


def _segment_tables(
    cleaned: pd.DataFrame, counts: dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """RFM → scores → k-selection → KMeans (decider) → naming → SBC →
    profile/agreement. Returns (rfm_table, profile, sbc_summary,
    agreement, extra_record)."""
    # Snapshot = max(InvoiceDate) + 1 day (plan §4.1): max date is
    # 2011-12-09, so snapshot is 2011-12-10.
    max_date = cleaned["invoice_date"].max()
    snapshot = max_date.normalize() + pd.Timedelta(days=1)
    rfm = compute_rfm(cleaned, snapshot)
    rfm = score_rfm(rfm)
    selection = select_k(rfm)
    k = choose_k(selection)
    labels = cluster_customers(rfm, k)
    rfm["kmeans_cluster"] = labels.astype(int)
    medians = (
        rfm.groupby("kmeans_cluster")
        .agg(
            median_r_score=("r_score", "median"),
            median_f_score=("f_score", "median"),
            median_m_score=("m_score", "median"),
        )
        .sort_index()
    )
    mapping = name_segments(medians)
    rfm["segment"] = rfm["kmeans_cluster"].map(mapping)
    # SBC per customer, from the attributed cleaned rows.
    attributed = cleaned[cleaned["customer_id"].notna()].copy()
    attributed["customer_id"] = attributed["customer_id"].astype(int)
    sbc = sbc_stats(attributed)
    rfm = rfm.merge(
        sbc[["customer_id", "adi_weeks", "cv2", "sbc_quadrant"]],
        on="customer_id",
        how="left",
    )
    profile = build_segment_profile(
        rfm,
        total_cleaned_revenue=counts["cleaned_revenue_gbp"],
        unattributed_revenue=counts["revenue_missing_customer_gbp"],
        unattributed_rows=counts["n_missing_customer_id"],
    )
    profile = build_actions(profile)
    sbc_summary = build_sbc_summary(rfm)
    agreement = build_agreement_table(rfm)
    agreement_value = agreement_rate(agreement)
    extra = {
        "snapshot_date": str(snapshot.date()),
        "max_invoice_date": str(max_date),
        "n_customers": len(rfm),
        "k_selection": [
            {
                "k": int(row["k"]),
                "sse": float(row["sse"]),
                "silhouette": float(row["silhouette"]),
            }
            for _, row in selection.iterrows()
        ],
        "chosen_k": int(k),
        "k_selection_rule": (
            "k = argmax silhouette over k = 2..8; if two k values are "
            "within 0.01 of silhouette, pick the smaller k"
        ),
        "kmeans": {
            "method": "KMeans on log1p-transformed, StandardScaler-scaled R/F/M",
            "random_state": 42,
            "n_init": 10,
            "decider": (
                "KMeans is the SOLE decider of segment assignment "
                "(plan §2.0); RFM scores name/explain; SBC is a cross-check"
            ),
        },
        "segment_naming": {
            str(int(label)): {
                "segment": mapping[int(label)],
                "median_r_score": float(medians.loc[label, "median_r_score"]),
                "median_f_score": float(medians.loc[label, "median_f_score"]),
                "median_m_score": float(medians.loc[label, "median_m_score"]),
            }
            for label in medians.index
        },
        "sbc": {
            "adi_unit": "weeks (mean inter-order gap in days / 7)",
            "cv2_base": "per-order GBP totals",
            "adi_cutoff": 1.32,
            "cv2_cutoff": 0.49,
            "quadrant_counts": {
                row["quadrant"]: int(row["n_customers"])
                for _, row in sbc_summary.iterrows()
            },
            "note": (
                "Exact theoretical cut-offs are 4/3 and 0.5 (Kostenko & "
                "Hyndman); 1.32/0.49 is the SBC-published rounded convention"
            ),
        },
        "sbc_per_customer": [
            {
                "customer_id": int(row["customer_id"]),
                "adi_weeks": float(row["adi_weeks"]),
                "cv2": float(row["cv2"]),
                "quadrant": str(row["sbc_quadrant"]),
            }
            for _, row in sbc.iterrows()
        ],
        "agreement_rate": float(agreement_value),
        "agreement_method": (
            "Greedy best one-to-one segment↔quadrant mapping over "
            "multi-order customers only (Single-order excluded); "
            "agreement = matched ÷ multi-order customers"
        ),
        "n_multi_order_customers": int((rfm["frequency"] > 1).sum()),
        "n_single_order_customers": int((rfm["frequency"] == 1).sum()),
    }
    return rfm, profile, sbc_summary, agreement, extra


def _build_from_frame(
    day_dir: Path, raw: pd.DataFrame, source: str, url: str, synthetic: bool = False
) -> dict:
    """Full build from a raw frame; writes all processed files."""
    day_dir = Path(day_dir)
    raw_dir = day_dir / "data" / "raw"
    proc_dir = day_dir / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)
    _verify_raw(raw)
    cleaned, counts = clean_transactions(raw)
    rfm, profile, sbc_summary, agreement, extra = _segment_tables(cleaned, counts)
    rfm_out = rfm[
        [
            "customer_id",
            "recency_days",
            "frequency",
            "monetary_gbp",
            "r_score",
            "f_score",
            "m_score",
            "rfm_code",
            "rfm_score",
            "kmeans_cluster",
            "segment",
            "sbc_quadrant",
        ]
    ].copy()
    rfm_out.to_csv(proc_dir / "rfm_table.csv", index=False)
    profile.to_csv(proc_dir / "segment_profile.csv", index=False)
    sbc_summary.to_csv(proc_dir / "sbc_summary.csv", index=False)
    agreement.to_csv(proc_dir / "agreement.csv", index=True)
    sample = cleaned.sample(n=min(1000, len(cleaned)), random_state=42)
    sample_out = sample.drop(columns=["line_revenue"]).copy()
    sample_out["invoice_date"] = sample_out["invoice_date"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    sample_out = sample_out.where(pd.notna(sample_out), None)
    (raw_dir / "sample_rows.json").write_text(
        json.dumps(sample_out.to_dict(orient="records"), indent=1, default=str),
        encoding="utf-8",
    )
    record = {
        "source": source,
        "url": url,
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
        "cleaning_counts_in_order": {
            "n_unparseable_dates": counts["n_unparseable_dates"],
            "n_cancelled_rows": counts["n_cancelled_rows"],
            "n_cancelled_invoices": counts["n_cancelled_invoices"],
            "n_nonpositive_quantity": counts["n_nonpositive_quantity"],
            "n_nonpositive_price": counts["n_nonpositive_price"],
            "n_adjustment_rows": counts["n_adjustment_rows"],
            "n_missing_description": counts["n_missing_description"],
        },
        "adjustment_stock_codes_present": counts["adjustment_stock_codes_present"],
        "adjustment_descriptions_present": counts["adjustment_descriptions_present"],
        "adjustment_stock_codes": counts["adjustment_stock_codes"],
        "adjustment_descriptions": counts["adjustment_descriptions"],
        "adjustment_codes_added": counts["adjustment_codes_added"],
        "cleaned_rows": counts["cleaned_rows"],
        "cleaned_revenue_gbp": counts["cleaned_revenue_gbp"],
        "cleaned_units": counts["cleaned_units"],
        "cleaned_orders": counts["cleaned_orders"],
        "n_missing_customer_id": counts["n_missing_customer_id"],
        "missing_customer_id_share": counts["missing_customer_id_share"],
        "revenue_missing_customer_gbp": counts["revenue_missing_customer_gbp"],
        "revenue_missing_customer_share": counts["revenue_missing_customer_share"],
        "rfm": {
            "snapshot_date": extra["snapshot_date"],
            "max_invoice_date": extra["max_invoice_date"],
            "n_customers": extra["n_customers"],
            "definitions": {
                "recency_days": "snapshot date − most recent InvoiceDate (days)",
                "frequency": "distinct InvoiceNo per customer",
                "monetary_gbp": "Σ (Quantity × UnitPrice) per customer, GBP",
            },
            "scoring": (
                "Percentile-rank 1–5 scores (ties share a score); R "
                "inverted; rfm_code = R·100 + F·10 + M; rfm_score = R+F+M "
                "(3–15). Scores are relative to this customer base."
            ),
        },
        "k_selection": extra["k_selection"],
        "chosen_k": extra["chosen_k"],
        "k_selection_rule": extra["k_selection_rule"],
        "kmeans": extra["kmeans"],
        "segment_naming": extra["segment_naming"],
        "sbc": extra["sbc"],
        "sbc_per_customer": extra["sbc_per_customer"],
        "agreement_rate": extra["agreement_rate"],
        "agreement_method": extra["agreement_method"],
        "n_multi_order_customers": extra["n_multi_order_customers"],
        "n_single_order_customers": extra["n_single_order_customers"],
        "synthetic": synthetic,
        "manual_validation": None,
        "versions": _versions(),
    }
    write_data_source(proc_dir / "data_source.json", record)
    return record


def run_live(day_dir: Path, use_cache: bool = False) -> dict:
    """Full live build: CSV primary, XLSX fallback (plan §3.3)."""
    day_dir = Path(day_dir)
    raw_dir = day_dir / "data" / "raw"
    csv_path = raw_dir / "data.csv"
    xlsx_path = raw_dir / "Online Retail.xlsx"
    if use_cache and csv_path.exists():
        raw = load_raw_csv(csv_path)
        return _build_from_frame(day_dir, raw, "live", CSV_URL)
    if use_cache and xlsx_path.exists():
        raw = load_raw_xlsx(xlsx_path)
        return _build_from_frame(day_dir, raw, "live", XLSX_URL)
    try:
        download_retail_csv(CSV_URL, csv_path)
        raw = load_raw_csv(csv_path)
        return _build_from_frame(day_dir, raw, "live", CSV_URL)
    except (requests.RequestException, ValueError, OSError):
        # CSV download or verification failed — fall back to the XLSX.
        download_retail_csv(XLSX_URL, xlsx_path)
        raw = load_raw_xlsx(xlsx_path)
        return _build_from_frame(day_dir, raw, "live", XLSX_URL)


def run_offline(day_dir: Path) -> None:
    """Regenerate derived tables/charts from committed CSVs.

    Never writes data_source.json when a live record already exists.
    """
    day_dir = Path(day_dir)
    proc_dir = day_dir / "data" / "processed"
    ds_path = proc_dir / "data_source.json"
    live_exists = False
    record: dict = {}
    if ds_path.exists():
        record = json.loads(ds_path.read_text(encoding="utf-8"))
        live_exists = record.get("source") == "live"
    rfm = pd.read_csv(proc_dir / "rfm_table.csv")
    profile = build_segment_profile(
        rfm,
        total_cleaned_revenue=record.get("cleaned_revenue_gbp"),
        unattributed_revenue=record.get("revenue_missing_customer_gbp", 0.0),
        unattributed_rows=record.get("n_missing_customer_id", 0),
    )
    profile = build_actions(profile)
    profile.to_csv(proc_dir / "segment_profile.csv", index=False)
    sbc_summary = build_sbc_summary(rfm)
    sbc_summary.to_csv(proc_dir / "sbc_summary.csv", index=False)
    agreement = build_agreement_table(rfm)
    agreement.to_csv(proc_dir / "agreement.csv", index=True)
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

    ~4,300 customers / ~540k line rows mimicking the real schema and
    marginals (brief §4). Never overwrites real data; output is
    git-ignored.
    """
    rng = np.random.default_rng(42)
    n_customers = 4300
    customer_ids = rng.choice(np.arange(12000, 20000), size=n_customers, replace=False)
    n_rows = 540000
    cust = rng.choice(customer_ids, size=n_rows)
    has_customer = rng.random(n_rows) < 0.90
    invoice_dates = pd.to_datetime(
        rng.integers(
            pd.Timestamp("2010-12-01").value,
            pd.Timestamp("2011-12-09").value,
            size=n_rows,
        )
    )
    quantity = rng.integers(1, 13, size=n_rows)
    tail = rng.random(n_rows) < 0.02
    quantity = np.where(tail, rng.integers(13, 200, size=n_rows), quantity)
    unit_price = np.round(rng.lognormal(mean=1.0, sigma=0.9, size=n_rows), 2)
    unit_price = np.clip(unit_price, 0.5, 50.0)
    cancelled = rng.random(n_rows) < 0.02
    quantity = np.where(cancelled, -quantity, quantity)
    invoice_no = np.array(
        [("C" if c else "") + str(536365 + i) for i, c in enumerate(cancelled)],
        dtype=object,
    )
    countries = np.where(rng.random(n_rows) < 0.90, "United Kingdom", "France")
    frame = pd.DataFrame(
        {
            "InvoiceNo": invoice_no,
            "StockCode": rng.integers(10000, 99999, size=n_rows).astype(str),
            "Description": "Synthetic product",
            "Quantity": quantity,
            "InvoiceDate": invoice_dates.strftime("%m/%d/%Y %H:%M"),
            "UnitPrice": unit_price,
            "CustomerID": np.where(has_customer, cust, np.nan),
            "Country": countries,
        }
    )
    out = Path(day_dir) / "data" / "raw" / "retail_synthetic.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    return out


def _versions() -> dict:
    import matplotlib
    import sklearn

    return {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "scikit-learn": sklearn.__version__,
        "scipy": __import__("scipy").__version__,
        "openpyxl": __import__("openpyxl").__version__,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Day 12 data pipeline")
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
