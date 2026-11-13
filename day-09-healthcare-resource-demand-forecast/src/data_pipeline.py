"""Day 9 — Healthcare Resource Demand Forecast: data pipeline.

Fetches CDC NSSP ED visits (COVID-19, Flu, RSV) and the HHS hospital
bed-capacity timeseries (both Socrata, no key), verifies the counts the
brief probed (NSSP 25,116 rows; bed series 81,713 rows), builds the
national Combined respiratory ED series (161 weeks), the state series
and the national weekly bed-utilisation series, then runs the forecast
(src.forecast) and writes the committed processed files (plan.md §3.5).

Usage (from the project root):
    python -m src.data_pipeline --live        # fetch + process + forecast
    python -m src.data_pipeline --use-cache   # reuse cached raw, no download
    python -m src.data_pipeline --offline     # recompute derived tables
                                              # from committed CSVs; never
                                              # clobbers data_source.json
    python -m src.data_pipeline --synthetic   # labelled-synthetic fallback

Data-size exception (plan §3.4): the raw NSSP JSON is ~2 MB and the raw
bed JSON ~80k rows, so ``data/raw/nssp_ed_visits.json``,
``data/raw/bed_capacity.json`` and ``data/raw/*_synthetic.json`` are
git-ignored and downloaded at build time. Committed provenance is
``data/raw/sample_rows.json`` (≤ 1,000 rows per dataset) and the compact
processed CSVs (``data/`` < 5 MB, no file > 1 MB).

Two verified quirks, handled here and documented in data/README.md:
- There is NO ``Combined`` pathogen value in the NSSP data; Combined is
  the sum of the three pathogen percentages (same denominator — total
  ED visits — so summing is valid).
- 72 rows have NULL ``percent_visits`` — in the JSON the key is simply
  absent. They are treated as missing, never as 0; the audit (count +
  geography/weeks) is recorded in data_source.json.
- The bed ``*_coverage`` columns hold *counts* of hospitals reporting
  that field (not 0/1 as the brief assumed). A state-day counts as fully
  covered for the bed calculation when ``inpatient_beds_coverage`` ==
  ``inpatient_beds_used_coverage`` (both present and > 0): the same
  hospitals reported the numerator and the denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from src import forecast as forecast_mod

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

NSSP_URL = "https://data.cdc.gov/resource/vutn-jzwm.json?$limit=50000"
BED_URL_TEMPLATE = (
    "https://healthdata.gov/resource/g62h-syeh.json?$limit=50000&$offset={offset}"
)
NSSP_METADATA_URL = "https://data.cdc.gov/api/views/vutn-jzwm"
NSSP_COMPANION_GUIDE = (
    "https://www.cdc.gov/ncird/surveillance/respiratory-illnesses/"
    "index.html#companion-guide"
)
ATTRIBUTION_NSSP = (
    "CDC National Syndromic Surveillance Program (NSSP), Emergency "
    "Department Visits — COVID-19, Flu, RSV, via CDC Open Data "
    "(data.cdc.gov/resource/vutn-jzwm)."
)
ATTRIBUTION_BED = (
    "U.S. Department of Health and Human Services, COVID-19 Reported "
    "Patient Impact and Hospital Capacity by State Timeseries, via "
    "healthdata.gov (resource g62h-syeh)."
)
LICENCE = "US federal public domain"

NSSP_RAW_NAME = "nssp_ed_visits.json"
BED_RAW_NAME = "bed_capacity.json"
NSSP_SYNTHETIC_NAME = "nssp_ed_visits_synthetic.json"
SAMPLE_ROWS_NAME = "sample_rows.json"

EXPECTED_NSSP_ROWS = 25_116
EXPECTED_BED_ROWS = 81_713
EXPECTED_NSSP_FIRST = "2023-10-07"
EXPECTED_NSSP_LAST = "2026-10-31"
EXPECTED_BED_FIRST = "2020-01-01"
EXPECTED_BED_LAST = "2024-04-27"
EXPECTED_WEEKS = 161
SEED = 42
NSSP_SAMPLE_ROWS = 1_000
# Bed rows are wide (~129 fields, ~7 KB each as JSON), so the bed sample
# is capped at 100 rows (~0.7 MB) to keep sample_rows.json under 1 MB;
# the NSSP sample is 1,000 rows (~0.15 MB). Both caps are within the
# plan's "≤ 1,000 rows per dataset".
BED_SAMPLE_ROWS = 100
HEADERS = {"User-Agent": "60-day-data-ai-portfolio/day-09 (research project)"}
PATHOGENS = ["COVID-19", "Influenza", "RSV"]
PATHOGEN_COLUMNS = {
    "COVID-19": "covid_pct",
    "Influenza": "flu_pct",
    "RSV": "rsv_pct",
}
NATIONAL_GEOGRAPHY = "United States"
BED_END_DATE = "2024-04-27"

# Synthetic fallback (brief §4; only if the live NSSP fetch fails).
SYNTHETIC_GENERATOR = {
    "weeks": 161,
    "base_pct": 1.5,
    "winter_peak_pp": 5.0,
    "winter_peak_centre_week": 52,
    "winter_peak_sigma_weeks": 6,
    "noise_sigma_pp": 0.4,
    "seed": 42,
    "pathogen_shares": {"COVID-19": 0.30, "Influenza": 0.55, "RSV": 0.15},
}


def _get_json(url: str) -> list[dict]:
    """GET a Socrata JSON endpoint; one retry after 60 s on 429/5xx."""
    last_exc: Exception | None = None
    for attempt in (1, 2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=120)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(
                    f"HTTP {resp.status_code} for {url}", response=resp
                )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise TypeError(f"unexpected JSON shape from {url}: {type(data)}")
            return data
        except (requests.RequestException, requests.HTTPError) as exc:
            last_exc = exc
            print(f"fetch attempt {attempt} failed: {exc}", file=sys.stderr)
            if attempt == 1:
                print("waiting 60 s before the single retry", file=sys.stderr)
                time.sleep(60)
    raise RuntimeError(f"fetch failed after 2 attempts: {url}") from last_exc


def fetch_nssp(limit: int = 50000) -> list[dict]:
    """Fetch the full NSSP table in one call.

    ``limit`` must be 50000: Socrata's default limit is 1,000 and a
    fetch without it is silently truncated (Day 6 lesson).
    """
    url = f"https://data.cdc.gov/resource/vutn-jzwm.json?$limit={limit}"
    rows = _get_json(url)
    print(f"fetched NSSP: {len(rows):,} rows from {url}")
    return rows


def fetch_bed_capacity(limit: int = 50000) -> list[dict]:
    """Fetch the full bed-capacity table in paged calls ($offset pages).

    Same $limit rule as the NSSP call; never assume one call returns
    the whole table (81,713 rows need two pages at $limit=50000).
    """
    rows: list[dict] = []
    offset = 0
    while True:
        url = BED_URL_TEMPLATE.format(offset=offset)
        page = _get_json(url)
        rows.extend(page)
        print(f"fetched bed page offset={offset}: {len(page):,} rows")
        if len(page) < limit:
            break
        offset += limit
    print(f"fetched bed capacity: {len(rows):,} rows total")
    return rows


def _to_nssp_frame(rows: list[dict]) -> pd.DataFrame:
    """Raw NSSP rows → frame; ``percent_visits`` cast to float.

    Rows with a missing ``percent_visits`` key (the JSON simply omits
    it) become NaN — missing, never 0.
    """
    frame = pd.DataFrame.from_records(rows)
    frame["week_end"] = pd.to_datetime(frame["week_end"]).dt.strftime("%Y-%m-%d")
    frame["percent_visits"] = pd.to_numeric(
        frame.get("percent_visits"), errors="coerce"
    )
    return frame


def audit_nulls(frame: pd.DataFrame) -> dict:
    """Audit NULL ``percent_visits`` rows: count + geography/weeks.

    Also counts the national weeks affected (a week is Combined-missing
    if any of its three pathogen values is missing).
    """
    nulls = frame[frame["percent_visits"].isna()]
    by_geo = (
        nulls.groupby("geography")["week_end"]
        .apply(lambda s: sorted(s.unique().tolist()))
        .to_dict()
    )
    national_null_weeks = sorted(
        nulls[nulls["geography"] == NATIONAL_GEOGRAPHY]["week_end"].unique().tolist()
    )
    return {
        "n_null_percent_visits": len(nulls),
        "null_share": round(float(len(nulls) / max(len(frame), 1)), 4),
        "null_by_geography": {
            geo: {"n_rows": len(nulls[nulls["geography"] == geo]), "weeks": weeks}
            for geo, weeks in sorted(by_geo.items())
        },
        "national_weeks_affected": national_null_weeks,
        "n_national_weeks_affected": len(national_null_weeks),
    }


def build_combined(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot pathogen rows to columns and sum the three pathogen %s.

    Returns one row per geography × week with ``covid_pct``,
    ``flu_pct``, ``rsv_pct`` and ``combined_pct``. A week is
    Combined-missing (NaN, never 0) if any of its three pathogen values
    is missing.
    """
    frame = df.copy()
    frame["week_end"] = pd.to_datetime(frame["week_end"]).dt.strftime("%Y-%m-%d")
    pivoted = frame.pivot_table(
        index=["geography", "week_end"],
        columns="pathogen",
        values="percent_visits",
        aggfunc="first",
    ).reset_index()
    for pathogen, column in PATHOGEN_COLUMNS.items():
        if pathogen not in pivoted.columns:
            pivoted[column] = np.nan
        pivoted = pivoted.rename(columns={pathogen: column})
    cols = list(PATHOGEN_COLUMNS.values())
    pivoted["combined_pct"] = pivoted[cols].sum(axis=1, skipna=False)
    # The source values carry one decimal; round so the CSVs store exact
    # 1-decimal values (2.2, not 2.1999999999999997 from float addition).
    for col in [*cols, "combined_pct"]:
        pivoted[col] = pivoted[col].round(1)
    return (
        pivoted[
            ["geography", "week_end", "covid_pct", "flu_pct", "rsv_pct", "combined_pct"]
        ]
        .sort_values(["geography", "week_end"])
        .reset_index(drop=True)
    )


def build_national_series(df: pd.DataFrame) -> pd.DataFrame:
    """National weekly series: 161 rows, geography == "United States"."""
    combined = build_combined(df)
    national = combined[combined["geography"] == NATIONAL_GEOGRAPHY].copy()
    return national.drop(columns=["geography"]).reset_index(drop=True)


def build_state_series(df: pd.DataFrame) -> pd.DataFrame:
    """State weekly series: 51 geographies × 161 weeks (minus NULLs)."""
    combined = build_combined(df)
    states = combined[combined["geography"] != NATIONAL_GEOGRAPHY].copy()
    return states.sort_values(["geography", "week_end"]).reset_index(drop=True)


def coverage_share(df: pd.DataFrame) -> float:
    """Share of state-days fully covered for the bed calculation.

    ``*_coverage`` columns hold counts of hospitals reporting that
    field. A state-day is fully covered when the bed numerator and
    denominator were reported by the same hospitals, i.e.
    ``inpatient_beds_coverage == inpatient_beds_used_coverage``
    (both present and > 0).
    """
    if (
        "inpatient_beds_coverage" not in df.columns
        or "inpatient_beds_used_coverage" not in df.columns
    ):
        return float("nan")
    beds_cov = pd.to_numeric(df["inpatient_beds_coverage"], errors="coerce")
    used_cov = pd.to_numeric(df["inpatient_beds_used_coverage"], errors="coerce")
    full = (beds_cov > 0) & (beds_cov == used_cov)
    return float(full.mean())


def build_bed_series(df: pd.DataFrame) -> pd.DataFrame:
    """National weekly bed utilisation (state-sum ratio, plan §3.2 r.5).

    Weekly aggregation by ISO week ending Saturday (``W-SAT``, matching
    the NSSP week-ending Saturdays). Utilisation is
    Σ inpatient_beds_used / Σ inpatient_beds per week — NOT the mean
    of the per-state ratios. ICU occupancy is computed the same way
    (Σ staffed_adult_icu_bed_occupancy / Σ total_staffed_adult_icu_beds).
    Only state-days with full coverage (see ``coverage_share``) enter
    the sums.
    """
    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for col in (
        "inpatient_beds",
        "inpatient_beds_used",
        "total_staffed_adult_icu_beds",
        "staffed_adult_icu_bed_occupancy",
    ):
        frame[col] = pd.to_numeric(frame.get(col), errors="coerce")
    beds_cov = pd.to_numeric(frame.get("inpatient_beds_coverage"), errors="coerce")
    used_cov = pd.to_numeric(frame.get("inpatient_beds_used_coverage"), errors="coerce")
    frame["full_coverage"] = (beds_cov > 0) & (beds_cov == used_cov)
    covered = frame[frame["full_coverage"]].copy()
    covered["week_end"] = (
        covered["date"].dt.to_period("W-SAT").dt.end_time.dt.strftime("%Y-%m-%d")
    )
    weekly = covered.groupby("week_end").agg(
        beds_total=("inpatient_beds", "sum"),
        beds_used=("inpatient_beds_used", "sum"),
        icu_beds_total=("total_staffed_adult_icu_beds", "sum"),
        icu_occupied=("staffed_adult_icu_bed_occupancy", "sum"),
        states_reporting=("state", "nunique"),
    )
    weekly["bed_utilisation"] = weekly["beds_used"] / weekly["beds_total"]
    weekly["icu_occupancy"] = weekly["icu_occupied"] / weekly["icu_beds_total"]
    # Ratios are stored to 4 decimals (0.01 pp precision); the underlying
    # sums are exact integers.
    weekly["bed_utilisation"] = weekly["bed_utilisation"].round(4)
    weekly["icu_occupancy"] = weekly["icu_occupancy"].round(4)
    out = (
        weekly.reset_index()[
            [
                "week_end",
                "bed_utilisation",
                "icu_occupancy",
                "beds_total",
                "beds_used",
                "states_reporting",
            ]
        ]
        .sort_values("week_end")
        .reset_index(drop=True)
    )
    return out


def write_data_source(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _write_sample_rows(nssp_rows: list[dict], bed_rows: list[dict]) -> None:
    """Committed provenance sample: ≤ 1,000 rows per dataset."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sample = {
        "nssp": nssp_rows[:NSSP_SAMPLE_ROWS],
        "bed": bed_rows[:BED_SAMPLE_ROWS],
    }
    path = RAW_DIR / SAMPLE_ROWS_NAME
    path.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {path} ({len(sample['nssp'])} NSSP + {len(sample['bed'])} "
        f"bed rows, {path.stat().st_size:,} bytes)"
    )


def _write_series_csvs(
    national: pd.DataFrame, states: pd.DataFrame, bed: pd.DataFrame
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    national.to_csv(PROCESSED_DIR / "national_combined.csv", index=False)
    states.to_csv(PROCESSED_DIR / "state_combined.csv", index=False)
    bed.to_csv(PROCESSED_DIR / "bed_utilisation.csv", index=False)
    print(
        f"wrote national_combined.csv ({len(national)} rows), "
        f"state_combined.csv ({len(states)} rows), "
        f"bed_utilisation.csv ({len(bed)} rows)"
    )


def _data_size_report() -> None:
    total = sum(
        p.stat().st_size for p in (PROJECT_ROOT / "data").rglob("*") if p.is_file()
    )
    biggest = max(
        (p.stat().st_size for p in (PROJECT_ROOT / "data").rglob("*") if p.is_file()),
        default=0,
    )
    print(f"data/ total: {total:,} bytes; largest file: {biggest:,} bytes")


def _verify_nssp(frame: pd.DataFrame, n_raw: int) -> None:
    if n_raw != EXPECTED_NSSP_ROWS:
        raise RuntimeError(
            f"NSSP row count mismatch: got {n_raw:,}, expected "
            f"{EXPECTED_NSSP_ROWS:,}"
        )
    first = frame["week_end"].min()
    last = frame["week_end"].max()
    if first != EXPECTED_NSSP_FIRST or last != EXPECTED_NSSP_LAST:
        raise RuntimeError(
            f"NSSP week range mismatch: got {first} → {last}, expected "
            f"{EXPECTED_NSSP_FIRST} → {EXPECTED_NSSP_LAST}"
        )
    print(f"verified NSSP: {n_raw:,} rows, {first} → {last}")


def _verify_bed(frame: pd.DataFrame, n_raw: int) -> None:
    if n_raw != EXPECTED_BED_ROWS:
        raise RuntimeError(
            f"bed row count mismatch: got {n_raw:,}, expected " f"{EXPECTED_BED_ROWS:,}"
        )
    first = pd.to_datetime(frame["date"]).min().strftime("%Y-%m-%d")
    last = pd.to_datetime(frame["date"]).max().strftime("%Y-%m-%d")
    if first != EXPECTED_BED_FIRST or last != EXPECTED_BED_LAST:
        raise RuntimeError(
            f"bed date range mismatch: got {first} → {last}, expected "
            f"{EXPECTED_BED_FIRST} → {EXPECTED_BED_LAST}"
        )
    print(f"verified bed series: {n_raw:,} rows, {first} → {last}")


def _load_or_fetch_nssp(use_cache: bool) -> list[dict]:
    raw_path = RAW_DIR / NSSP_RAW_NAME
    if use_cache and raw_path.exists():
        print(f"using cached NSSP raw data: {raw_path} (no download)")
        return json.loads(raw_path.read_text(encoding="utf-8"))
    rows = fetch_nssp()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(rows), encoding="utf-8")
    print(f"cached raw NSSP JSON: {raw_path} ({raw_path.stat().st_size:,} bytes)")
    return rows


def _load_or_fetch_bed(use_cache: bool) -> list[dict]:
    raw_path = RAW_DIR / BED_RAW_NAME
    if use_cache and raw_path.exists():
        print(f"using cached bed raw data: {raw_path} (no download)")
        return json.loads(raw_path.read_text(encoding="utf-8"))
    rows = fetch_bed_capacity()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(rows), encoding="utf-8")
    print(f"cached raw bed JSON: {raw_path} ({raw_path.stat().st_size:,} bytes)")
    return rows


def run_live(use_cache: bool) -> dict:
    """Fetch (or reuse the cache), verify, build series, forecast, write."""
    nssp_rows = _load_or_fetch_nssp(use_cache)
    bed_rows = _load_or_fetch_bed(use_cache)
    nssp = _to_nssp_frame(nssp_rows)
    _verify_nssp(nssp, len(nssp_rows))
    bed = pd.DataFrame.from_records(bed_rows)
    _verify_bed(bed, len(bed_rows))
    null_audit = audit_nulls(nssp)
    print(
        f"NULL audit: {null_audit['n_null_percent_visits']} NULL "
        f"percent_visits rows; national weeks affected: "
        f"{null_audit['n_national_weeks_affected']}"
    )
    national = build_national_series(nssp)
    states = build_state_series(nssp)
    if len(national) != EXPECTED_WEEKS:
        raise RuntimeError(
            f"national series has {len(national)} weeks, " f"expected {EXPECTED_WEEKS}"
        )
    bed_series = build_bed_series(bed)
    cov = coverage_share(bed)
    # State-days dropped by the full-coverage filter, counted honestly.
    beds_cov = pd.to_numeric(bed["inpatient_beds_coverage"], errors="coerce")
    used_cov = pd.to_numeric(bed["inpatient_beds_used_coverage"], errors="coerce")
    n_dropped = int(((beds_cov <= 0) | (beds_cov != used_cov)).sum())
    _write_sample_rows(nssp_rows, bed_rows)
    _write_series_csvs(national, states, bed_series)
    forecast_summary = forecast_mod.build_forecast(
        pd.Series(national["combined_pct"].to_numpy(dtype=float)),
        pd.Series(national["week_end"]),
        PROCESSED_DIR,
    )
    latest = national.iloc[-1]
    record = {
        "source": "live",
        "synthetic": False,
        "seed": SEED,
        "datasets": {
            "nssp": {
                "name": "2023 Respiratory Virus Response - NSSP Emergency "
                "Department Visits - COVID-19, Flu, RSV, Combined",
                "dataset_id": "vutn-jzwm",
                "url": NSSP_URL,
                "metadata_url": NSSP_METADATA_URL,
                "companion_guide": NSSP_COMPANION_GUIDE,
                "attribution": ATTRIBUTION_NSSP,
                "licence": LICENCE,
            },
            "bed_capacity": {
                "name": "COVID-19 Reported Patient Impact and Hospital "
                "Capacity by State Timeseries (RAW)",
                "dataset_id": "g62h-syeh",
                "url": "https://healthdata.gov/resource/g62h-syeh.json",
                "attribution": ATTRIBUTION_BED,
                "licence": LICENCE,
                "reporting_ended": BED_END_DATE,
            },
        },
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetch_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "nssp_rows": len(nssp_rows),
        "bed_rows": len(bed_rows),
        "expected_nssp_rows": EXPECTED_NSSP_ROWS,
        "expected_bed_rows": EXPECTED_BED_ROWS,
        "nssp_week_range": [EXPECTED_NSSP_FIRST, EXPECTED_NSSP_LAST],
        "bed_date_range": [EXPECTED_BED_FIRST, EXPECTED_BED_LAST],
        "national_weeks": len(national),
        "state_geographies": int(states["geography"].nunique()),
        "bed_weeks": len(bed_series),
        "null_audit": null_audit,
        "combined_construction": (
            "No Combined pathogen value exists in the NSSP data; Combined "
            "is the sum of the COVID-19, Influenza and RSV percentages "
            "(same denominator — total ED visits). A week is "
            "Combined-missing if any of its three pathogen values is missing."
        ),
        "latest_national_week": {
            "week_end": str(latest["week_end"]),
            "covid_pct": round(float(latest["covid_pct"]), 1),
            "flu_pct": round(float(latest["flu_pct"]), 1),
            "rsv_pct": round(float(latest["rsv_pct"]), 1),
            "combined_pct": round(float(latest["combined_pct"]), 1),
        },
        "bed_coverage": {
            "definition": (
                "Share of state-days where inpatient_beds_coverage == "
                "inpatient_beds_used_coverage (both > 0): the same "
                "hospitals reported the bed numerator and denominator. "
                "Coverage columns hold hospital counts, not 0/1 flags."
            ),
            "full_coverage_share": round(cov, 4),
            "state_days_dropped": n_dropped,
        },
        "bed_utilisation_method": (
            "National weekly inpatient bed utilisation = "
            "Σ inpatient_beds_used / Σ inpatient_beds per ISO week "
            "(week ending Saturday), state-sum ratio — NOT the mean of "
            "per-state ratios. ICU occupancy computed the same way. "
            f"Series ends {BED_END_DATE} (reporting ended); it is a "
            "historical record, not current capacity."
        ),
        "forecast": forecast_summary,
        "band_thresholds": {
            "Low": "< 2%",
            "Moderate": "2–4%",
            "High": "4–6%",
            "Surge": "> 6%",
        },
        "staffing_scenarios": {
            "label": "PLANNING ASSUMPTIONS — not measured data",
            "Low": "Baseline roster",
            "Moderate": "Baseline staffing (monitor)",
            "High": "+10% rostered shifts",
            "Surge": "+25% rostered shifts + elective-deferral trigger",
        },
        "volume_converter_defaults": {
            "weekly_ed_volume": 1000,
            "admission_rate": 0.15,
            "label": "planning assumptions, not measured numbers",
        },
    }
    write_data_source(PROCESSED_DIR / "data_source.json", record)
    _data_size_report()
    return record


def run_offline() -> None:
    """Recompute derived tables from the committed CSVs; no network.

    Day 5/6 lesson: an offline run must NOT rewrite the live record's
    ``source: "live"`` field (or any other data_source.json field). It
    regenerates only the derived forecast tables (forecast.csv,
    backtest.csv, band_history.csv) from the committed national series
    — deterministically (seed 42), so the outputs are byte-identical —
    and verifies every other committed file is present. The
    data_source.json hash is checked before and after.
    """
    existing = PROCESSED_DIR / "data_source.json"
    if not existing.exists():
        raise RuntimeError("no data_source.json — run --live first")
    before = hashlib.sha256(existing.read_bytes()).hexdigest()
    record = json.loads(existing.read_text(encoding="utf-8"))
    required = [
        "national_combined.csv",
        "state_combined.csv",
        "bed_utilisation.csv",
        "forecast.csv",
        "backtest.csv",
        "band_history.csv",
    ]
    for name in required:
        if not (PROCESSED_DIR / name).exists():
            raise RuntimeError(f"missing committed file: {PROCESSED_DIR / name}")
    if not (RAW_DIR / SAMPLE_ROWS_NAME).exists():
        raise RuntimeError(f"missing committed file: {RAW_DIR / SAMPLE_ROWS_NAME}")
    national = pd.read_csv(PROCESSED_DIR / "national_combined.csv")
    forecast_mod.build_forecast(
        pd.Series(national["combined_pct"].to_numpy(dtype=float)),
        pd.Series(national["week_end"]),
        PROCESSED_DIR,
    )
    after = hashlib.sha256(existing.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("offline run clobbered data_source.json")
    print(
        "offline: derived forecast tables regenerated from committed CSVs; "
        f"data_source.json untouched (source={record.get('source')!r})"
    )


# --- Synthetic fallback (brief §4; only if the live NSSP fetch fails) ----
def build_synthetic_nssp_rows() -> list[dict]:
    """Labelled-synthetic NSSP rows (seed 42) for all 52 geographies.

    161 weeks, base 1.5% + winter peak +5 pp (Gaussian bump centred
    week 52, σ = 6 weeks), weekly noise σ = 0.4 pp. Each geography gets
    a small fixed offset (σ = 0.3 pp) so states differ; the Combined
    value is split across pathogens by fixed shares.
    """
    rng = np.random.default_rng(SEED)
    gen = SYNTHETIC_GENERATOR
    weeks = pd.date_range("2023-10-07", periods=gen["weeks"], freq="7D")
    geographies = [NATIONAL_GEOGRAPHY] + [f"State-{i:02d}" for i in range(1, 52)]
    offsets = rng.normal(0, 0.3, size=len(geographies))
    rows: list[dict] = []
    for gi, geography in enumerate(geographies):
        for wi, week in enumerate(weeks):
            bump = gen["winter_peak_pp"] * float(
                np.exp(
                    -0.5
                    * (
                        (wi - gen["winter_peak_centre_week"])
                        / gen["winter_peak_sigma_weeks"]
                    )
                    ** 2
                )
            )
            combined = (
                gen["base_pct"]
                + bump
                + offsets[gi]
                + rng.normal(0, gen["noise_sigma_pp"])
            )
            combined = max(combined, 0.0)
            for pathogen, share in gen["pathogen_shares"].items():
                rows.append(
                    {
                        "week_end": week.strftime("%Y-%m-%dT00:00:00.000"),
                        "pathogen": pathogen,
                        "geography": geography,
                        "percent_visits": str(round(max(combined * share, 0.0), 1)),
                    }
                )
    return rows


def run_synthetic() -> dict:
    """Labelled-synthetic fallback. Never overwrites live files.

    Writes the synthetic NSSP rows to
    ``data/raw/nssp_ed_visits_synthetic.json`` only. The bed series
    still needs the live HHS fetch (or a cached copy) — a synthetic bed
    series is not invented; if no cached bed raw exists, this fails
    loudly with instructions.
    """
    synthetic_path = RAW_DIR / NSSP_SYNTHETIC_NAME
    live_path = RAW_DIR / NSSP_RAW_NAME
    if live_path.exists():
        print(
            "synthetic mode: live raw NSSP file exists and is left untouched "
            f"({live_path})"
        )
    rows = build_synthetic_nssp_rows()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    synthetic_path.write_text(json.dumps(rows), encoding="utf-8")
    print(f"wrote synthetic NSSP rows: {synthetic_path} ({len(rows):,} rows)")
    bed_path = RAW_DIR / BED_RAW_NAME
    if not bed_path.exists():
        raise RuntimeError(
            "synthetic mode needs a cached bed raw file "
            f"({bed_path}) or a live bed fetch — no synthetic bed series "
            "is invented. Run --live once, or re-run with the bed cache present."
        )
    bed_rows = json.loads(bed_path.read_text(encoding="utf-8"))
    nssp = _to_nssp_frame(rows)
    national = build_national_series(nssp)
    states = build_state_series(nssp)
    bed = pd.DataFrame.from_records(bed_rows)
    bed_series = build_bed_series(bed)
    _write_sample_rows(rows, bed_rows)
    _write_series_csvs(national, states, bed_series)
    forecast_summary = forecast_mod.build_forecast(
        pd.Series(national["combined_pct"].to_numpy(dtype=float)),
        pd.Series(national["week_end"]),
        PROCESSED_DIR,
    )
    record = {
        "source": "synthetic",
        "synthetic": True,
        "seed": SEED,
        "generator": SYNTHETIC_GENERATOR,
        "dataset": "SYNTHETIC fallback — live NSSP fetch unavailable (brief §4)",
        "licence": LICENCE,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetch_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "nssp_rows": len(rows),
        "bed_rows": len(bed_rows),
        "national_weeks": len(national),
        "bed_weeks": len(bed_series),
        "null_audit": audit_nulls(nssp),
        "forecast": forecast_summary,
        "band_thresholds": {
            "Low": "< 2%",
            "Moderate": "2–4%",
            "High": "4–6%",
            "Surge": "> 6%",
        },
    }
    write_data_source(PROCESSED_DIR / "data_source.json", record)
    print("SYNTHETIC — NOT REAL DATA: data_source.json records synthetic: true")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--live", action="store_true", help="fetch live data and process"
    )
    group.add_argument(
        "--offline",
        action="store_true",
        help="recompute derived tables from committed CSVs; no network",
    )
    group.add_argument(
        "--synthetic",
        action="store_true",
        help="labelled-synthetic fallback (seed 42)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="reuse cached raw data instead of downloading "
        "(implies --live when given alone)",
    )
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="kept for compatibility; raw is always cached under data/raw/",
    )
    args = parser.parse_args(argv)
    try:
        if args.live or args.use_cache:
            run_live(use_cache=args.use_cache)
        elif args.synthetic:
            run_synthetic()
        else:
            run_offline()
    except Exception as exc:  # noqa: BLE001 — fail loudly, per plan
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
