"""Data pipeline for Day 14 — Voter Turnout Analytics.

Downloads the two UF Election Lab turnout CSVs, parses the ambiguous
5th column by content, concatenates them (adding ``YEAR=2024`` to the
2024 file), runs the recompute and VEP-reconciliation cross-checks,
cross-checks the 2024 numerator against EAVS for sampled states,
checks the Census shapefile join, and writes the five processed
tables plus ``data_source.json``.

Modes (Day 1 pattern):
- ``--live``: download everything, build everything (default).
- ``--use-cache``: reuse cached raw CSVs, still write ``data_source.json``.
- ``--offline``: rebuild the derived tables and charts from the
  committed CSVs only — no network, and never clobbers a live
  ``data_source.json`` (skips writing it entirely when a live record
  already exists, plan §3.5).
- ``--synthetic``: build the labelled-synthetic fallback (brief §4,
  seed 42) instead of the real download — last resort only, and it
  never overwrites real data.

Decider rules (plan §2.0): UF VEP is authoritative; EAVS is a
cross-check only and never overrides, averages, or enters a committed
turnout table. Outliers are flagged and kept. Comparisons are
like-with-like within cycle type only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    from src.turnout import (
        RECOMPUTE_TOLERANCE_PP,
        VEP_RECONCILIATION_TOLERANCE,
        correlate,
        cycle_type,
        felon_share_vap,
        flag_outliers,
        overseas_share_vep,
        parse_column5,
        recompute_vep,
        skewness,
        vep_turnout,
    )
except ImportError:  # pragma: no cover - running as a script from src/
    from turnout import (  # type: ignore[no-redef]
        RECOMPUTE_TOLERANCE_PP,
        VEP_RECONCILIATION_TOLERANCE,
        correlate,
        cycle_type,
        felon_share_vap,
        flag_outliers,
        overseas_share_vep,
        parse_column5,
        recompute_vep,
        skewness,
        vep_turnout,
    )

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

UF_1980_2022_URL = (
    "https://election.lab.ufl.edu/data-downloads/turnoutdata/"
    "Turnout_1980_2022_v1.2.csv"
)
UF_2024_URL = (
    "https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv"
)
DOC_1980_2022_URL = (
    "https://election.lab.ufl.edu/data-downloads/turnoutdata/"
    "Turnout_1980_2022_v1.2_doc.txt"
)
DOC_2024_URL = (
    "https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4_doc.txt"
)
SHAPEFILE_URL = (
    "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"
)
EAVS_URL = (
    "https://www.eac.gov/sites/default/files/2025-06/"
    "2024_EAVS_for_Public_Release_nolabel_V1_csv.zip"
)
EAVS_INDEX_URL = "https://www.eac.gov/research-and-data/datasets-codebooks-and-surveys"

UF_1980_2022_FILE = "Turnout_1980_2022_v1.2.csv"
UF_2024_FILE = "Turnout_2024G_v0.4.csv"
SHAPEFILE_FILE = "cb_2024_us_state_500k.zip"
EAVS_FILE = "2024_EAVS_for_Public_Release_nolabel_V1_csv.zip"

EXPECTED_SIZES = {UF_1980_2022_FILE: 116830, UF_2024_FILE: 8378}
SHAPEFILE_SIZE = 3242450
EAVS_SIZE = 2076499

FETCH_DATE = "2026-11-21"

#: 50 states + DC, in the order the UF files list them.
JURISDICTIONS: list[tuple[str, str]] = [
    ("Alabama", "AL"),
    ("Alaska", "AK"),
    ("Arizona", "AZ"),
    ("Arkansas", "AR"),
    ("California", "CA"),
    ("Colorado", "CO"),
    ("Connecticut", "CT"),
    ("Delaware", "DE"),
    ("District of Columbia", "DC"),
    ("Florida", "FL"),
    ("Georgia", "GA"),
    ("Hawaii", "HI"),
    ("Idaho", "ID"),
    ("Illinois", "IL"),
    ("Indiana", "IN"),
    ("Iowa", "IA"),
    ("Kansas", "KS"),
    ("Kentucky", "KY"),
    ("Louisiana", "LA"),
    ("Maine", "ME"),
    ("Maryland", "MD"),
    ("Massachusetts", "MA"),
    ("Michigan", "MI"),
    ("Minnesota", "MN"),
    ("Mississippi", "MS"),
    ("Missouri", "MO"),
    ("Montana", "MT"),
    ("Nebraska", "NE"),
    ("Nevada", "NV"),
    ("New Hampshire", "NH"),
    ("New Jersey", "NJ"),
    ("New Mexico", "NM"),
    ("New York", "NY"),
    ("North Carolina", "NC"),
    ("North Dakota", "ND"),
    ("Ohio", "OH"),
    ("Oklahoma", "OK"),
    ("Oregon", "OR"),
    ("Pennsylvania", "PA"),
    ("Rhode Island", "RI"),
    ("South Carolina", "SC"),
    ("South Dakota", "SD"),
    ("Tennessee", "TN"),
    ("Texas", "TX"),
    ("Utah", "UT"),
    ("Vermont", "VT"),
    ("Virginia", "VA"),
    ("Washington", "WA"),
    ("West Virginia", "WV"),
    ("Wisconsin", "WI"),
    ("Wyoming", "WY"),
]

#: States sampled for the EAVS 2024 numerator cross-check (plan §3.3).
EAVS_SAMPLED_STATES = ["CO", "CA"]
#: Extra states spot-checked against EAVS; disagreements are disclosed, UF stands.
EAVS_EXTRA_STATES = ["AR", "TX"]

ATTRIBUTION = (
    "Source: Michael McDonald, University of Florida Election Lab, "
    "General Election Turnout Rates 1980–2022 v1.2 and 2024 General "
    "Election Turnout Rates v0.4 (https://election.lab.ufl.edu/voter-turnout/), "
    "CC BY 4.0. Retrieved 2026-11-21."
)


def download_file(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` (one retry after 60 s on 429/5xx).

    Returns the destination path. Raises on a non-200 response after
    the retry — the build fails loudly rather than proceeding with a
    truncated file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: str = ""
    for attempt in (1, 2):
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            dest.write_bytes(response.content)
            return dest
        last_error = f"HTTP {response.status_code}"
        if response.status_code in (429, 500, 502, 503, 504) and attempt == 1:
            time.sleep(60)
            continue
        break
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def fetch_doc_versions() -> dict[str, str]:
    """Read both UF documentation files in full; record version + date."""
    record: dict[str, str] = {}
    for label, url in (
        ("1980_2022", DOC_1980_2022_URL),
        ("2024", DOC_2024_URL),
    ):
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        version = ""
        date = ""
        for line in response.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("Version:"):
                version = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Date:"):
                date = stripped.split(":", 1)[1].strip()
        record[f"doc_{label}_version"] = version
        record[f"doc_{label}_date"] = date
    return record


def load_turnout_csv(path: Path) -> pd.DataFrame:
    """Read a raw UF CSV as text — column 5 must stay text for content parsing."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _to_float(series: pd.Series) -> pd.Series:
    """Parse a text column of comma-grouped numbers / percents to float.

    Blank strings become missing (NaN), never zero.
    """
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_column5_series(
    values: pd.Series,
) -> tuple[pd.Series, pd.Series, dict[str, int]]:
    """Split an ambiguous 5th column into (source_url, vote_count) + parse counts."""
    urls: list[str | None] = []
    votes: list[float | None] = []
    counts = {"url": 0, "digits": 0, "blank": 0}
    for raw in values:
        url, vote = parse_column5(str(raw))
        urls.append(url)
        votes.append(vote)
        if url is not None:
            counts["url"] += 1
        elif vote is not None:
            counts["digits"] += 1
        else:
            counts["blank"] += 1
    return (
        pd.Series(urls, index=values.index),
        pd.Series(votes, index=values.index),
        counts,
    )


def _canonical_frame(
    raw: pd.DataFrame, year: int | None
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalise one raw UF file to the canonical column set.

    ``year`` is None for the 1980–2022 file (YEAR column present) and
    2024 for the 2024 file (no YEAR column — added here, brief §1c.2).
    Column 5 is taken by position: index 4 in the 1980–2022 file,
    index 3 in the 2024 file (its header is blank).
    """
    col5_index = 4 if year is None else 3
    col5 = raw.iloc[:, col5_index]
    urls, votes, counts = _parse_column5_series(col5)
    frame = pd.DataFrame(
        {
            "year": _to_float(raw["YEAR"]).astype("Int64") if year is None else year,
            "state": raw["STATE"].astype(str).str.strip(),
            "state_abv": raw["STATE_ABV"].astype(str).str.strip(),
            "total_ballots_counted": _to_float(raw["TOTAL_BALLOTS_COUNTED"]),
            "vote_for_highest_office": votes.astype(float),
            "source_url": urls,
            "vap": _to_float(raw["VAP"]),
            "noncitizen_pct": _to_float(raw["NONCITIZEN_PCT"]),
            "ineligible_prison": _to_float(raw["INELIGIBLE_PRISON"]),
            "ineligible_probation": _to_float(raw["INELIGIBLE_PROBATION"]),
            "ineligible_parole": _to_float(raw["INELIGIBLE_PAROLE"]),
            "ineligible_felons_total": _to_float(raw["INELIGIBLE_FELONS_TOTAL"]),
            "eligible_overseas": _to_float(raw["ELIGIBLE_OVERSEAS"]),
            "vep": _to_float(raw["VEP"]),
            "vep_turnout_rate": _to_float(raw["VEP_TURNOUT_RATE"]),
            "vap_turnout_rate": _to_float(raw["VAP_TURNOUT_RATE"]),
        }
    )
    return frame, counts


def clean_turnout(
    df_1980_2022: pd.DataFrame, df_2024: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Concatenate and clean the two UF files (plan §3.2, in order).

    Returns the long frame plus a counts record: rows per file,
    concatenated/cleaned totals, duplicates dropped, null ballots per
    year, column-5 parse counts, and the VEP-reconciliation result.
    """
    frame_old, counts_old = _canonical_frame(df_1980_2022, None)
    frame_new, counts_new = _canonical_frame(df_2024, 2024)
    counts: dict[str, Any] = {
        "rows_1980_2022_file": len(frame_old),
        "rows_2024_file": len(frame_new),
        "rows_concatenated": int(len(frame_old) + len(frame_new)),
        "column5_1980_2022": counts_old,
        "column5_2024": counts_new,
    }
    long = pd.concat([frame_old, frame_new], ignore_index=True)
    long["is_national"] = long["state"] == "United States"
    # The 1980–2022 file leaves the national row's abbreviation blank;
    # the 2024 file uses "US". Normalise to "US" for the national row.
    long.loc[long["is_national"], "state_abv"] = "US"
    long["year"] = long["year"].astype(int)
    before = len(long)
    long = long.drop_duplicates(subset=["year", "state_abv"], keep="first")
    counts["duplicate_rows_dropped"] = int(before - len(long))
    long = long.sort_values(
        ["year", "is_national", "state_abv"], ascending=[True, False, True]
    )
    long = long.reset_index(drop=True)
    long["cycle_type"] = long["year"].map(cycle_type)
    # Derived shares and the recomputed rate (a check, never a replacement).
    long["vep_turnout_recomputed"] = [
        vep_turnout(b, v)
        for b, v in zip(long["total_ballots_counted"], long["vep"], strict=True)
    ]
    long["felon_share_vap"] = [
        felon_share_vap(f, v)
        for f, v in zip(long["ineligible_felons_total"], long["vap"], strict=True)
    ]
    long["overseas_share_vep"] = [
        overseas_share_vep(o, v)
        for o, v in zip(long["eligible_overseas"], long["vep"], strict=True)
    ]
    # VEP reconciliation: recompute VEP from its components per row.
    reconciled: list[float] = []
    flagged = 0
    max_rel_diff = 0.0
    for _, row in long.iterrows():
        vap = row["vap"]
        vep = row["vep"]
        if pd.isna(vap) or pd.isna(vep) or float(vep) == 0:
            reconciled.append(float("nan"))
            continue
        recomputed = recompute_vep(
            float(vap),
            float(row["noncitizen_pct"]) if not pd.isna(row["noncitizen_pct"]) else 0.0,
            (
                float(row["ineligible_felons_total"])
                if not pd.isna(row["ineligible_felons_total"])
                else 0.0
            ),
            (
                float(row["eligible_overseas"])
                if not pd.isna(row["eligible_overseas"])
                else 0.0
            ),
        )
        rel = abs(recomputed - float(vep)) / float(vep)
        reconciled.append(rel)
        max_rel_diff = max(max_rel_diff, rel)
        if rel > VEP_RECONCILIATION_TOLERANCE:
            flagged += 1
    counts["vep_reconciliation_flagged_rows"] = flagged
    counts["vep_reconciliation_max_rel_diff"] = max_rel_diff
    counts["rows_cleaned"] = len(long)
    nulls = (
        long[long["total_ballots_counted"].isna()]
        .groupby("year")
        .size()
        .astype(int)
        .to_dict()
    )
    counts["null_ballots_per_year"] = {int(k): int(v) for k, v in nulls.items()}
    counts["null_ballots_total"] = int(long["total_ballots_counted"].isna().sum())
    return long, counts


def recompute_check(df: pd.DataFrame) -> dict[str, Any]:
    """Recompute VEP turnout and compare with the file's rate (plan §3.3).

    Raises ``ValueError`` if any row differs by more than 0.05 pp —
    the build stops and reports, never silently overwrites the file rate.
    """
    both = df.dropna(subset=["total_ballots_counted", "vep", "vep_turnout_rate"])
    diffs = (both["vep_turnout_recomputed"] - both["vep_turnout_rate"]).abs()
    max_diff = float(diffs.max()) if len(diffs) else 0.0
    result: dict[str, Any] = {
        "rows_checked": len(both),
        "max_abs_diff_pp": max_diff,
        "rows_over_tolerance": int((diffs > RECOMPUTE_TOLERANCE_PP).sum()),
        "tolerance_pp": RECOMPUTE_TOLERANCE_PP,
    }
    spot_checks: dict[str, dict[str, float]] = {}
    for year, abv, label in (
        (2024, "US", "2024 United States"),
        (2022, "US", "2022 United States"),
        (2024, "CO", "2024 Colorado"),
        (2024, "CA", "2024 California"),
        (2024, "AR", "2024 Arkansas"),
    ):
        row = df[(df["year"] == year) & (df["state_abv"] == abv)]
        if len(row) == 0:
            raise ValueError(f"Spot-check row missing: {label}")
        file_rate = row.iloc[0]["vep_turnout_rate"]
        recomputed_rate = row.iloc[0]["vep_turnout_recomputed"]
        if pd.isna(file_rate) or pd.isna(recomputed_rate):
            raise ValueError(f"Spot-check row has no rate: {label}")
        spot_checks[label] = {
            "file_rate": float(file_rate),
            "recomputed_rate": float(recomputed_rate),
        }
    result["spot_checks"] = spot_checks
    expected = {
        "2024 United States": 64.30,
        "2022 United States": 46.12,
        "2024 Colorado": 73.40,
        "2024 California": 62.26,
        "2024 Arkansas": 54.06,
    }
    for label, value in expected.items():
        if abs(spot_checks[label]["file_rate"] - value) > 0.05:
            raise ValueError(f"Spot-check failed: {label} file rate is not {value}")
    if result["rows_over_tolerance"] > 0:
        raise ValueError(
            f"Recompute check failed: {result['rows_over_tolerance']} rows differ "
            f"by more than {RECOMPUTE_TOLERANCE_PP} pp (max {max_diff:.4f} pp)"
        )
    return result


def eavs_cross_check(root: Path = ROOT) -> dict[str, Any]:
    """Cross-check the 2024 numerator against EAVS 2024 (plan §3.3).

    Sums EAVS item F1a (total ballots cast) by state and compares it
    with the UF 2024 ballots counted for the sampled states. UF stands
    regardless of the result; disagreements over 0.5% are recorded.
    Returns a ``skipped`` record when the EAVS zip is absent.
    """
    record: dict[str, Any] = {
        "source": "U.S. Election Assistance Commission, 2024 EAVS, V1",
        "version": "V1",
        "url": EAVS_URL,
        "variable": "F1a (total ballots cast), summed by state",
        "sampled_states": EAVS_SAMPLED_STATES,
        "additional_states": EAVS_EXTRA_STATES,
        "status": "skipped",
    }
    eavs_zip = root / "data" / "raw" / EAVS_FILE
    if not eavs_zip.exists():
        record["note"] = "EAVS zip absent; cross-check not run"
        return record
    eavs_dir = root / "data" / "raw" / "eavs"
    if not list(eavs_dir.glob("**/*.csv")):
        with zipfile.ZipFile(eavs_zip) as zf:
            zf.extractall(eavs_dir)
    csvs = list(eavs_dir.glob("**/*.csv"))
    if not csvs:
        record["note"] = "EAVS zip contains no CSV"
        return record
    eavs = pd.read_csv(
        csvs[0], usecols=["State_Abbr", "F1a"], dtype=str, low_memory=False
    )
    eavs["ballots"] = pd.to_numeric(eavs["F1a"], errors="coerce")
    sums = eavs.groupby("State_Abbr")["ballots"].sum()
    state_2024 = pd.read_csv(root / "data" / "processed" / "state_2024.csv")
    states: dict[str, dict[str, float | bool]] = {}
    for abv in EAVS_SAMPLED_STATES + EAVS_EXTRA_STATES:
        uf_value = float(
            state_2024.loc[
                state_2024["state_abv"] == abv, "total_ballots_counted"
            ].iloc[0]
        )
        eavs_value = float(sums.loc[abv])
        diff_pct = (eavs_value - uf_value) / uf_value * 100.0
        states[abv] = {
            "uf_ballots_counted": uf_value,
            "eavs_ballots_cast": eavs_value,
            "diff_pct": diff_pct,
            "over_threshold_0.5pct": bool(abs(diff_pct) > 0.5),
        }
    record["status"] = "done"
    record["states"] = states
    record["note"] = (
        "EAVS is a survey of election administrators, not a turnout-rate "
        "source; its figures cross-check the UF numerator only. UF stands."
    )
    return record


def shapefile_join_check(root: Path = ROOT) -> dict[str, Any]:
    """Join the 2024 state table to the Census geometry (plan §3.3).

    Asserts all 51 jurisdictions (50 states + DC) joined. Returns a
    ``skipped`` record when the shapefile is absent.
    """
    record: dict[str, Any] = {
        "source": "U.S. Census Bureau, cartographic boundary file cb_2024_us_state_500k",
        "url": SHAPEFILE_URL,
        "status": "skipped",
    }
    shp_dir = root / "data" / "raw" / "shapefile"
    shps = list(shp_dir.glob("*.shp")) if shp_dir.exists() else []
    if not shps:
        record["note"] = "Shapefile absent; join check not run"
        return record
    import geopandas as gpd

    geo = gpd.read_file(shps[0])
    state_2024 = pd.read_csv(root / "data" / "processed" / "state_2024.csv")
    states = state_2024[~state_2024["is_national"].astype(bool)]
    joined_abbrs = set(geo["STUSPS"].astype(str))
    missing = sorted(set(states["state_abv"].astype(str)) - joined_abbrs)
    record["status"] = "done"
    record["shapefile_features"] = len(geo)
    record["jurisdictions_expected"] = 51
    record["jurisdictions_joined"] = len(
        set(states["state_abv"].astype(str)) & joined_abbrs
    )
    record["unmatched_abbreviations"] = missing
    if missing:
        raise ValueError(f"Shapefile join missed jurisdictions: {missing}")
    return record


def derive_tables(long: pd.DataFrame, root: Path = ROOT) -> dict[str, Any]:
    """Build the five processed tables from the cleaned long frame (plan §3.5)."""
    proc = root / "data" / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    info: dict[str, Any] = {}

    long_cols = [
        "year",
        "state",
        "state_abv",
        "is_national",
        "cycle_type",
        "total_ballots_counted",
        "vote_for_highest_office",
        "source_url",
        "vap",
        "noncitizen_pct",
        "ineligible_felons_total",
        "eligible_overseas",
        "vep",
        "vep_turnout_rate",
        "vap_turnout_rate",
        "vep_turnout_recomputed",
        "felon_share_vap",
        "overseas_share_vep",
    ]
    long[long_cols].to_csv(proc / "turnout_long.csv", index=False)
    info["turnout_long_rows"] = len(long)

    national = long[long["is_national"]].copy().sort_values("year")
    rates = {
        (int(r["year"])): (
            None if pd.isna(r["vep_turnout_rate"]) else float(r["vep_turnout_rate"])
        )
        for _, r in national.iterrows()
    }
    pp_changes: list[float | None] = []
    for y in national["year"]:
        current = rates.get(int(y))
        previous = rates.get(int(y) - 4)
        if current is None or previous is None:
            pp_changes.append(None)
        else:
            pp_changes.append(current - previous)
    national["vep_turnout_pp_change_same_cycle"] = pp_changes
    national["national_estimated"] = national["year"] < 2010
    national_series = national[
        [
            "year",
            "cycle_type",
            "total_ballots_counted",
            "vap",
            "vep",
            "vep_turnout_rate",
            "vap_turnout_rate",
            "vep_turnout_pp_change_same_cycle",
            "national_estimated",
        ]
    ]
    national_series.to_csv(proc / "national_series.csv", index=False)
    info["national_series_rows"] = len(national_series)

    # 2024 state table: 51 jurisdictions ranked by VEP turnout; US total separate.
    s2024 = long[long["year"] == 2024].copy()
    states_2024 = s2024[~s2024["is_national"]].copy()
    rates_2020 = {
        str(r["state_abv"]): float(r["vep_turnout_rate"])
        for _, r in long[(long["year"] == 2020) & (~long["is_national"])].iterrows()
        if not pd.isna(r["vep_turnout_rate"])
    }
    states_2024 = states_2024.sort_values(
        ["vep_turnout_rate", "state_abv"], ascending=[False, True]
    ).reset_index(drop=True)
    states_2024["rank_vep"] = range(1, len(states_2024) + 1)
    states_2024["pp_change_vs_2020"] = [
        (
            None
            if str(abv) not in rates_2020 or pd.isna(rate)
            else float(rate) - rates_2020[str(abv)]
        )
        for abv, rate in zip(
            states_2024["state_abv"], states_2024["vep_turnout_rate"], strict=True
        )
    ]
    flagged_2024 = flag_outliers(
        pd.Series(
            states_2024["vep_turnout_rate"].to_numpy(),
            index=states_2024["state_abv"],
        )
    )
    flagged_abbrs = {str(i) for i in flagged_2024.index}
    states_2024["is_outlier"] = states_2024["state_abv"].astype(str).isin(flagged_abbrs)
    states_frame = states_2024[
        [
            "state",
            "state_abv",
            "total_ballots_counted",
            "vep",
            "vep_turnout_rate",
            "vap_turnout_rate",
            "rank_vep",
            "pp_change_vs_2020",
            "noncitizen_pct",
            "felon_share_vap",
            "overseas_share_vep",
            "is_outlier",
        ]
    ].copy()
    states_frame["is_national"] = False
    us_frame = s2024[s2024["is_national"]].copy()
    us_frame["rank_vep"] = pd.NA
    us_frame["pp_change_vs_2020"] = pd.NA
    us_frame["is_outlier"] = False
    us_frame = us_frame[
        [
            "state",
            "state_abv",
            "total_ballots_counted",
            "vep",
            "vep_turnout_rate",
            "vap_turnout_rate",
            "rank_vep",
            "pp_change_vs_2020",
            "noncitizen_pct",
            "felon_share_vap",
            "overseas_share_vep",
            "is_outlier",
        ]
    ].copy()
    us_frame["is_national"] = True
    state_2024 = pd.concat([states_frame, us_frame], ignore_index=True)
    state_2024.to_csv(proc / "state_2024.csv", index=False)
    info["state_2024_rows"] = len(state_2024)

    # Correlations: 2024 states only, one scope (plan §4.3).
    corr_rows: list[dict[str, Any]] = []
    for indicator in ("noncitizen_pct", "felon_share_vap", "overseas_share_vep"):
        stats_result = correlate(
            states_2024[indicator].astype(float),
            states_2024["vep_turnout_rate"].astype(float),
        )
        corr_rows.append(
            {
                "indicator": indicator,
                "scope": "2024_states",
                "n": stats_result["n"],
                "pearson_r": stats_result["pearson_r"],
                "pearson_p": stats_result["pearson_p"],
                "spearman_r": stats_result["spearman_r"],
                "spearman_p": stats_result["spearman_p"],
            }
        )
    pd.DataFrame(corr_rows).to_csv(proc / "correlations.csv", index=False)
    info["correlations"] = corr_rows

    # Outliers: 2024 pass + pooled presidential pass (plan §4.4).
    outlier_rows: list[dict[str, Any]] = []
    for abv in flagged_2024.index:
        row = flagged_2024.loc[abv]
        outlier_rows.append(
            {
                "year": 2024,
                "cycle_type": "presidential",
                "state_abv": str(abv),
                "vep_turnout_rate": float(
                    states_2024.loc[
                        states_2024["state_abv"] == str(abv), "vep_turnout_rate"
                    ].iloc[0]
                ),
                "rule": str(row["rule"]),
                "statistic_value": float(row["statistic_value"]),
            }
        )
    pres = long[(~long["is_national"]) & (long["cycle_type"] == "presidential")].copy()
    pooled = flag_outliers(pres["vep_turnout_rate"])
    for idx in pooled.index:
        row = pooled.loc[idx]
        source = pres.loc[idx]
        outlier_rows.append(
            {
                "year": int(source["year"]),
                "cycle_type": "presidential",
                "state_abv": str(source["state_abv"]),
                "vep_turnout_rate": float(source["vep_turnout_rate"]),
                "rule": str(row["rule"]),
                "statistic_value": float(row["statistic_value"]),
            }
        )
    outliers = pd.DataFrame(
        outlier_rows,
        columns=[
            "year",
            "cycle_type",
            "state_abv",
            "vep_turnout_rate",
            "rule",
            "statistic_value",
        ],
    )
    outliers.to_csv(proc / "outliers.csv", index=False)
    info["outliers_rows"] = len(outliers)
    info["outliers_2024"] = [
        {"state_abv": str(a), "rule": str(flagged_2024.loc[a]["rule"])}
        for a in flagged_2024.index
    ]
    info["skewness_presidential_pooled"] = skewness(
        pres["vep_turnout_rate"].astype(float)
    )
    mid = long[(~long["is_national"]) & (long["cycle_type"] == "midterm")]
    info["skewness_midterm_pooled"] = skewness(mid["vep_turnout_rate"].astype(float))
    return info


def write_data_source(path: Path, record: dict[str, Any]) -> None:
    """Write ``data_source.json`` (sorted keys, readable indentation)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")


def generate_synthetic(seed: int = 42) -> pd.DataFrame:
    """Labelled-synthetic fallback (brief §4) — last resort only.

    51 jurisdictions x 23 elections (1980–2024 biennial), mimicking the
    real schema and marginals: VEP turnout ~46% in midterms / ~60–66%
    in presidential years, state spread roughly +/-10 pp around the
    national figure, VAP > VEP always, noncitizen share 2–15%.
    Never overwrites real data; recorded as ``synthetic: true``.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    years = list(range(1980, 2025, 2))
    state_offsets = {abv: float(rng.normal(0, 5)) for _, abv in JURISDICTIONS}
    rows: list[dict[str, Any]] = []
    for year in years:
        presidential = year % 4 == 0
        national_rate = (
            float(rng.normal(63, 2)) if presidential else float(rng.normal(46, 2))
        )
        for name, abv in JURISDICTIONS:
            rate = float(
                np.clip(national_rate + state_offsets[abv] + rng.normal(0, 1.5), 30, 80)
            )
            vap = float(rng.integers(400_000, 20_000_000))
            noncitizen = float(rng.uniform(2, 15))
            felons = float(rng.integers(0, 60_000))
            vep = vap * (1 - noncitizen / 100.0) - felons
            ballots = round(vep * rate / 100.0)
            rows.append(
                {
                    "year": year,
                    "state": name,
                    "state_abv": abv,
                    "is_national": False,
                    "cycle_type": cycle_type(year),
                    "total_ballots_counted": float(ballots),
                    "vote_for_highest_office": float(
                        ballots - int(rng.integers(0, 50_000))
                    ),
                    "source_url": None,
                    "vap": vap,
                    "noncitizen_pct": noncitizen,
                    "ineligible_felons_total": felons,
                    "eligible_overseas": float("nan"),
                    "vep": vep,
                    "vep_turnout_rate": rate,
                    "vap_turnout_rate": ballots / vap * 100.0,
                    "vep_turnout_recomputed": ballots / vep * 100.0,
                    "felon_share_vap": felons / vap,
                    "overseas_share_vep": float("nan"),
                }
            )
        # National total row.
        vap_us = 260_000_000.0
        vep_us = 243_000_000.0
        ballots_us = round(vep_us * national_rate / 100.0)
        rows.append(
            {
                "year": year,
                "state": "United States",
                "state_abv": "US",
                "is_national": True,
                "cycle_type": cycle_type(year),
                "total_ballots_counted": float(ballots_us),
                "vote_for_highest_office": float(ballots_us - 1_000_000),
                "source_url": None,
                "vap": vap_us,
                "noncitizen_pct": 8.0,
                "ineligible_felons_total": 2_600_000.0,
                "eligible_overseas": 3_300_000.0,
                "vep": vep_us,
                "vep_turnout_rate": national_rate,
                "vap_turnout_rate": ballots_us / vap_us * 100.0,
                "vep_turnout_recomputed": ballots_us / vep_us * 100.0,
                "felon_share_vap": 2_600_000.0 / vap_us,
                "overseas_share_vep": 3_300_000.0 / vep_us,
            }
        )
    return pd.DataFrame(rows)


def _existing_live_record() -> dict[str, Any] | None:
    """Return the existing ``data_source.json`` if it records a live run."""
    path = PROC / "data_source.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(record, dict) and record.get("source") == "live":
        return record
    return None


def _clean_float(value: float) -> float | None:
    """Return ``value`` unless it is NaN/infinite, in which case None (JSON-safe)."""
    if value is None or not math.isfinite(float(value)):
        return None
    return float(value)


def build_charts(root: Path = ROOT) -> None:
    """Build the four charts from the processed tables (chart 01 guarded)."""
    try:
        from src.make_charts import build_all_charts
    except ImportError:  # pragma: no cover - running as a script from src/
        from make_charts import build_all_charts  # type: ignore[no-redef]
    build_all_charts(root)


def run(mode: str) -> dict[str, Any]:
    """Run the pipeline in ``mode``; return the ``data_source.json`` record."""
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "source": mode,
        "synthetic": False,
        "seed": None,
        "fetch_date": FETCH_DATE,
        "attribution": ATTRIBUTION,
        "urls": {"1980_2022": UF_1980_2022_URL, "2024": UF_2024_URL},
        "cycle_type_rule": "presidential if YEAR % 4 == 0 else midterm",
        "metric_definitions": {
            "vep_turnout": "TOTAL_BALLOTS_COUNTED / VEP * 100 (primary metric)",
            "vap_turnout": "TOTAL_BALLOTS_COUNTED / VAP * 100 (secondary metric)",
            "pp_change": "percentage-point change within the same cycle type only",
        },
    }

    if mode == "synthetic":
        long = generate_synthetic(seed=42)
        record["synthetic"] = True
        record["seed"] = 42
        record["note"] = "SYNTHETIC — NOT REAL DATA (brief §4 fallback)"
        counts = {
            "rows_1980_2022_file": 0,
            "rows_2024_file": 0,
            "rows_concatenated": len(long),
            "rows_cleaned": len(long),
            "duplicate_rows_dropped": 0,
            "null_ballots_total": 0,
        }
    else:
        csv_old = RAW / UF_1980_2022_FILE
        csv_new = RAW / UF_2024_FILE
        if mode == "live" or (mode == "use-cache" and not csv_old.exists()):
            download_file(UF_1980_2022_URL, csv_old)
        if mode == "live" or (mode == "use-cache" and not csv_new.exists()):
            download_file(UF_2024_URL, csv_new)
        if not csv_old.exists() or not csv_new.exists():
            raise FileNotFoundError(
                "UF CSVs missing and not downloaded — run with --live, "
                "or --synthetic for the labelled fallback"
            )
        sizes = {name: (RAW / name).stat().st_size for name in EXPECTED_SIZES}
        record["csv_byte_sizes"] = sizes
        for name, expected in EXPECTED_SIZES.items():
            if sizes[name] != expected:
                raise ValueError(
                    f"Byte-size mismatch for {name}: got {sizes[name]}, "
                    f"expected {expected} — wrong file fetched"
                )
        if mode in ("live", "use-cache"):
            record.update(fetch_doc_versions())
            shp_zip = RAW / SHAPEFILE_FILE
            if not shp_zip.exists() or shp_zip.stat().st_size != SHAPEFILE_SIZE:
                download_file(SHAPEFILE_URL, shp_zip)
            shp_dir = RAW / "shapefile"
            if not list(shp_dir.glob("*.shp")):
                with zipfile.ZipFile(shp_zip) as zf:
                    zf.extractall(shp_dir)
            eavs_zip = RAW / EAVS_FILE
            if not eavs_zip.exists() or eavs_zip.stat().st_size != EAVS_SIZE:
                download_file(EAVS_URL, eavs_zip)
        long, counts = clean_turnout(
            load_turnout_csv(csv_old), load_turnout_csv(csv_new)
        )

    recompute = recompute_check(long)
    record["cleaning_counts"] = counts
    record["recompute_check"] = recompute
    info = derive_tables(long)
    record["derived_tables"] = {k: v for k, v in info.items() if k != "correlations"}
    record["correlations"] = info["correlations"]
    if mode in ("live", "use-cache"):
        record["eavs_cross_check"] = eavs_cross_check()
        record["shapefile_join"] = shapefile_join_check()
    else:
        record["eavs_cross_check"] = {"status": "not run in offline mode"}
        record["shapefile_join"] = {"status": "not run in offline mode"}
    record["manual_validation"] = {
        "metric": "2024 United States VEP turnout",
        "computation": "156766239 / 243803423 * 100",
        "result_pct": 64.30,
        "file_rate_pct": 64.30,
        "diff_pp": 0.0,
        "note": "Recomputed by hand from the committed 2024 CSV; matches the file rate to the last digit.",
    }

    if mode == "offline":
        existing = _existing_live_record()
        if existing is not None:
            print("Offline run: live data_source.json exists — not clobbering it.")
        else:
            write_data_source(PROC / "data_source.json", record)
            print("Offline run: no live record existed — wrote data_source.json.")
    else:
        write_data_source(PROC / "data_source.json", record)
    build_charts()
    return record


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m src.data_pipeline [--live|--offline|--use-cache|--synthetic]``."""
    parser = argparse.ArgumentParser(description="Day 14 voter turnout data pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--live", action="store_true", help="Download everything and build (default)"
    )
    group.add_argument(
        "--offline", action="store_true", help="Rebuild from committed CSVs only"
    )
    group.add_argument("--use-cache", action="store_true", help="Reuse cached raw CSVs")
    group.add_argument(
        "--synthetic", action="store_true", help="Labelled-synthetic fallback (seed 42)"
    )
    args = parser.parse_args(argv)
    mode = "live"
    if args.offline:
        mode = "offline"
    elif args.use_cache:
        mode = "use-cache"
    elif args.synthetic:
        mode = "synthetic"
    record = run(mode)
    print(
        f"Pipeline ({mode}) complete: {record['derived_tables']['turnout_long_rows']} long rows, "
        f"max recompute diff {record['recompute_check']['max_abs_diff_pp']:.4f} pp"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
