"""Day 7 — Disease Prevalence Dashboard: data pipeline.

Fetches CDC PLACES county estimates (2025 release = 2023, 2024 release =
2022) from CDC Open Data (Socrata, no key), cleans them per plan.md §3.2,
and writes compact per-measure CSVs plus state and change tables.

Usage (from the project root):
    python -m src.data_pipeline --live       # fetch from CDC, write outputs
    python -m src.data_pipeline --offline    # regenerate derived tables
                                             # from committed CSVs, no network
    python -m src.data_pipeline --synthetic  # labelled-synthetic fallback
    python -m src.data_pipeline --live --keep-raw  # also keep raw JSONs
                                             # under the system temp dir

Fetch discipline (Day 6 lesson — no silent truncation): for every measure
and release, run the $select=count(*) check FIRST, then fetch in
$limit=5000 pages, then assert rows fetched == count. One retry per page
after 5 s; on a second failure, stop and report — never proceed short.

Raw-data rule (plan §3.3): the full raw Socrata JSON for 12
measure-releases is ~23 MB, over the 5 MB/day limit, so raw responses go
to a temporary directory and are DELETED after processing. Only a 36-row
provenance sample (data/raw/sample_rows.json) is committed. Full raw is
regenerable with `--live`. Synthetic raw goes to
data/raw/*_synthetic.json (git-ignored) and never overwrites live files.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from src.metrics import estimated_cases, median_ci_width, weighted_rate, yoy_change

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

BASE_URL = "https://data.cdc.gov/resource"
DATASETS = {"2023": "swc5-untb", "2022": "fu4u-a9bh"}
RELEASES = {"2023": "2025 release", "2022": "2024 release"}
MEASURES = {
    "DIABETES": "diabetes",
    "COPD": "copd",
    "CASTHMA": "asthma",
    "CHD": "chd",
    "STROKE": "stroke",
    "OBESITY": "obesity",
}
MEASURE_LABELS = {
    "DIABETES": "Diabetes",
    "COPD": "COPD",
    "CASTHMA": "Current asthma",
    "CHD": "Coronary heart disease",
    "STROKE": "Stroke",
    "OBESITY": "Obesity",
}
# Plausible 2023 crude-prevalence ranges (%, adults 18+) used ONLY for the
# labelled-synthetic fallback (seed 42). Live data never touches these.
SYNTHETIC_RANGES = {
    "DIABETES": (8.0, 24.0),
    "COPD": (3.0, 12.0),
    "CASTHMA": (6.0, 13.0),
    "CHD": (3.0, 10.0),
    "STROKE": (1.5, 6.0),
    "OBESITY": (25.0, 45.0),
}
SELECT_FIELDS = (
    "year,stateabbr,statedesc,locationname,locationid,measureid,measure,"
    "short_question_text,data_value,data_value_footnote_symbol,"
    "data_value_footnote,low_confidence_limit,"
    "high_confidence_limit,totalpopulation,totalpop18plus,geolocation"
)
PAGE_SIZE = 5000
REQUEST_SLEEP_S = 1.0
HEADERS = {"User-Agent": "60-day-data-ai-portfolio/day-07 (research project)"}
SOURCE_NOTE = (
    "CDC PLACES: Local Data for Better Health, County Data, 2025 release "
    "(2023 estimates) and 2024 release (2022 estimates), via CDC Open Data "
    "(data.cdc.gov). Model-based estimates from BRFSS."
)

PREVALENCE_COLS = [
    "year",
    "stateabbr",
    "locationname",
    "locationid",
    "measureid",
    "data_value",
    "totalpop18plus",
    "est_cases",
    "lon",
    "lat",
]


def _get(session: requests.Session, dataset: str, params: dict) -> list:
    """One Socrata GET with a single retry after 5 s on 429/5xx."""
    url = f"{BASE_URL}/{dataset}.json"
    for attempt in (1, 2):
        resp = session.get(url, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        if attempt == 1 and resp.status_code in (429, 500, 502, 503, 504):
            time.sleep(5)
            continue
        raise RuntimeError(
            f"Socrata request failed: {url} {params} -> HTTP {resp.status_code}"
        )
    raise RuntimeError("unreachable")  # pragma: no cover


def count_rows(session: requests.Session, measure: str, year: str) -> int:
    """Q1: expected row count for one measure/release (anti-truncation)."""
    rows = _get(
        session,
        DATASETS[year],
        {
            "$select": "count(*)",
            "$where": f"measureid='{measure}' AND datavaluetypeid='CrdPrv'",
        },
    )
    return int(rows[0]["count"])


def fetch_measure(session: requests.Session, measure: str, year: str) -> list[dict]:
    """Q2: full fetch for one measure/release, paginated, count-asserted."""
    expected = count_rows(session, measure, year)
    rows: list[dict] = []
    offset = 0
    while True:
        page = _get(
            session,
            DATASETS[year],
            {
                "$select": SELECT_FIELDS,
                "$where": f"measureid='{measure}' AND datavaluetypeid='CrdPrv'",
                "$limit": PAGE_SIZE,
                "$offset": offset,
            },
        )
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(REQUEST_SLEEP_S)
    if len(rows) != expected:
        raise RuntimeError(
            f"TRUNCATED FETCH: {measure} {year}: got {len(rows)} rows, "
            f"expected {expected} — refusing to proceed"
        )
    return rows


def _to_float(value: object) -> float:
    """float() that tolerates a missing value as NaN (CI limits only)."""
    if value is None or value == "":
        return float("nan")
    return float(value)  # type: ignore[arg-type]


def rows_to_frame(rows: list[dict]) -> tuple[pd.DataFrame, int]:
    """Parse raw Socrata rows into the cleaned county frame (plan §3.2).

    Returns (frame, n_no_value): rows whose data_value is missing are
    dropped and counted. Socrata omits null fields from the JSON, so a
    suppressed row arrives with no data_value key at all — verified
    2026-11-11: exactly 1 such row per measure in the 2025 release, the
    footnote-'*' row. It has no published value to analyse, so dropping
    it (and recording the count) is correct; the brief's assumption that
    the '*' row keeps a value was wrong — see plan §11.
    """
    n_no_value = sum(1 for r in rows if r.get("data_value") is None)
    rows = [r for r in rows if r.get("data_value") is not None]
    records = []
    for r in rows:
        lon, lat = None, None
        geo = r.get("geolocation") or {}
        coords = geo.get("coordinates") or []
        if len(coords) == 2:
            lon, lat = float(coords[0]), float(coords[1])
        # The national aggregate row (stateabbr='US') omits locationname
        # and geolocation — tolerate missing optional fields here; the
        # strict county-row check below still fails loudly on bad data.
        records.append(
            {
                "year": str(r["year"]),
                "stateabbr": r["stateabbr"],
                "statedesc": r.get("statedesc") or r["stateabbr"],
                "locationname": r.get("locationname") or r.get("statedesc") or "",
                "locationid": str(r["locationid"]).zfill(5),
                "measureid": r["measureid"],
                "data_value": float(r["data_value"]),
                "low_ci": _to_float(r.get("low_confidence_limit")),
                "high_ci": _to_float(r.get("high_confidence_limit")),
                "totalpopulation": int(float(r.get("totalpopulation") or 0)),
                "totalpop18plus": int(float(r.get("totalpop18plus") or 0)),
                "footnote": str(r.get("data_value_footnote_symbol") or ""),
                "lon": lon,
                "lat": lat,
            }
        )
    df = pd.DataFrame.from_records(records)
    if df["data_value"].isna().any():
        raise RuntimeError("live fetch contains missing data_value — refusing")
    counties = df[df["stateabbr"] != "US"]
    if counties["locationname"].eq("").any() or counties["totalpop18plus"].le(0).any():
        raise RuntimeError("county rows with missing name or population — refusing")
    # Missing coordinates are tolerated per plan §3.2 rule 3: the county is
    # kept in tables but excluded from the bubble map; the count is logged.
    n_no_geo = int(counties["lon"].isna().sum())
    if n_no_geo:
        print(f"note: {n_no_geo} county rows have no coordinates")
    df["est_cases"] = [
        estimated_cases(v, p) for v, p in zip(df["data_value"], df["totalpop18plus"])
    ]
    return df, n_no_value


def build_derived(
    county: pd.DataFrame, us_values: dict
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame, dict]:
    """Build per-measure prevalence/change frames, state table, quality meta.

    `county` is the cleaned county-only frame (US row already dropped).
    `us_values` maps (measureid, year) -> published US aggregate value.
    Returns (prevalence frames, change frames, state table, meta dict).
    """
    prevalence: dict[str, pd.DataFrame] = {}
    change: dict[str, pd.DataFrame] = {}
    state_rows: list[dict] = []
    meta: dict = {"unmatched": {}, "national": {}, "median_ci_width": {}}
    for measure, slug in MEASURES.items():
        m = county[county["measureid"] == measure].copy()
        prev = m[PREVALENCE_COLS].copy()
        prev = prev.sort_values(["year", "stateabbr", "locationname"]).reset_index(
            drop=True
        )
        prev["data_value"] = prev["data_value"].round(1)
        prev["lon"] = prev["lon"].round(3)
        prev["lat"] = prev["lat"].round(3)
        prevalence[slug] = prev

        # Median CI width per measure-year (M7), county rows only.
        for year in ("2022", "2023"):
            my = m[m["year"] == year]
            meta["median_ci_width"][f"{measure}_{year}"] = round(
                median_ci_width(my["low_ci"], my["high_ci"]), 2
            )

        # National population-weighted rate (M5) vs published US row.
        for year in ("2022", "2023"):
            my = m[m["year"] == year]
            nat = round(
                weighted_rate(my["est_cases"].sum(), my["totalpop18plus"].sum()), 2
            )
            us = us_values.get((measure, year))
            meta["national"][f"{measure}_{year}"] = {
                "weighted": nat,
                "us_row": us,
                "gap_pp": round(nat - us, 2) if us is not None else None,
            }

        # Year-over-year change on matched counties only (M3).
        a = m[m["year"] == "2022"].set_index("locationid")
        b = m[m["year"] == "2023"].set_index("locationid")
        matched = sorted(set(a.index) & set(b.index))
        meta["unmatched"][measure] = {
            "only_2022": len(set(a.index) - set(b.index)),
            "only_2023": len(set(b.index) - set(a.index)),
            "matched": len(matched),
        }
        rows = []
        for loc in matched:
            ra, rb = a.loc[loc], b.loc[loc]
            pp, pct = yoy_change(float(ra["data_value"]), float(rb["data_value"]))
            rows.append(
                {
                    "locationid": loc,
                    "locationname": rb["locationname"],
                    "stateabbr": rb["stateabbr"],
                    "measureid": measure,
                    "value_2022": round(float(ra["data_value"]), 1),
                    "value_2023": round(float(rb["data_value"]), 1),
                    "pp_change": round(pp, 2),
                    "pct_change": round(pct, 1),
                }
            )
        change[slug] = (
            pd.DataFrame.from_records(rows)
            .sort_values("locationid")
            .reset_index(drop=True)
        )

        # State roll-up, population-weighted (M4).
        for year in ("2022", "2023"):
            my = m[m["year"] == year]
            for abbr, g in my.groupby("stateabbr"):
                state_rows.append(
                    {
                        "year": year,
                        "stateabbr": abbr,
                        "statedesc": str(g["statedesc"].iloc[0]),
                        "measureid": measure,
                        "state_rate": round(
                            weighted_rate(
                                g["est_cases"].sum(), g["totalpop18plus"].sum()
                            ),
                            2,
                        ),
                        "totalpop18plus": int(g["totalpop18plus"].sum()),
                        "est_cases": int(g["est_cases"].sum()),
                        "n_counties": len(g),
                    }
                )
    state = (
        pd.DataFrame.from_records(state_rows)
        .sort_values(["measureid", "year", "stateabbr"])
        .reset_index(drop=True)
    )
    return prevalence, change, state, meta


def write_outputs(
    prevalence: dict,
    change: dict,
    state: pd.DataFrame,
    meta: dict,
    source_record: dict,
) -> None:
    """Write all committed processed files (plan §3.3)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for slug, df in prevalence.items():
        df.to_csv(PROCESSED_DIR / f"prevalence_{slug}.csv", index=False)
    for slug, df in change.items():
        df.to_csv(PROCESSED_DIR / f"change_{slug}.csv", index=False)
    state.to_csv(PROCESSED_DIR / "state_prevalence.csv", index=False)
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(source_record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(prevalence)} prevalence files, {len(change)} change files")
    print(
        f"state rows: {len(state)}; data/ total KB: "
        f"{sum(p.stat().st_size for p in (PROCESSED_DIR).rglob('*') if p.is_file()) / 1000:.0f}"
    )


def process_raw_rows(all_rows: dict[str, list[dict]], source: str, extra: dict) -> dict:
    """Shared clean+derive+write path for live and synthetic raw rows.

    `all_rows` maps "MEASURE_YEAR" -> raw Socrata-shaped rows. Returns the
    source record written to data_source.json.
    """
    counts: dict = {}
    footnote_stars: dict = {}
    rows_without_value: dict = {}
    us_values: dict = {}
    sample: list[dict] = []
    frames: list[pd.DataFrame] = []
    for key, rows in sorted(all_rows.items()):
        measure, year = key.split("_")
        counts[f"{measure}_{year}"] = len(rows)
        sample.extend(rows[:3])
        us_row = [r for r in rows if r.get("stateabbr") == "US"]
        if us_row:
            us_values[(measure, year)] = float(us_row[0]["data_value"])
        footnote_stars[f"{measure}_{year}"] = sum(
            1 for r in rows if (r.get("data_value_footnote_symbol") or "") == "*"
        )
        df, n_no_value = rows_to_frame(rows)
        rows_without_value[f"{measure}_{year}"] = n_no_value
        n_us = int((df["stateabbr"] == "US").sum())
        df = df[df["stateabbr"] != "US"].copy()
        print(
            f"{measure} {year}: {len(rows)} rows fetched, {n_us} US row(s) "
            f"dropped, {n_no_value} row(s) without a published value dropped"
        )
        frames.append(df)
    county = pd.concat(frames, ignore_index=True)
    prevalence, change, state, meta = build_derived(county, us_values)
    record = {
        "source": source,
        "source_note": SOURCE_NOTE,
        "datasets": {
            "2023": {"dataset_id": DATASETS["2023"], "release": RELEASES["2023"]},
            "2022": {"dataset_id": DATASETS["2022"], "release": RELEASES["2022"]},
        },
        "measures": list(MEASURES),
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row_counts": counts,
        "us_rows_dropped_per_measure_year": 1,
        "footnote_star_rows": footnote_stars,
        "rows_without_published_value": rows_without_value,
        "unmatched_counties": meta["unmatched"],
        "national_weighted_vs_us_row": meta["national"],
        "median_ci_width_pp": meta["median_ci_width"],
        **extra,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "sample_rows.json").write_text(
        json.dumps(sample, indent=2) + "\n", encoding="utf-8"
    )
    write_outputs(prevalence, change, state, meta, record)
    return record


def run_live(keep_raw: bool) -> dict:
    """Fetch all 12 measure-releases from CDC Open Data and process them."""
    session = requests.Session()
    tmpdir = Path(tempfile.mkdtemp(prefix="day07_raw_")) if keep_raw else None
    all_rows: dict[str, list[dict]] = {}
    try:
        for measure in MEASURES:
            for year in ("2023", "2022"):
                rows = fetch_measure(session, measure, year)
                all_rows[f"{measure}_{year}"] = rows
                if tmpdir is not None:
                    (tmpdir / f"{measure}_{year}.json").write_text(
                        json.dumps(rows), encoding="utf-8"
                    )
                time.sleep(REQUEST_SLEEP_S)
    finally:
        session.close()
    record = process_raw_rows(all_rows, "live", {})
    if tmpdir is not None:
        print(f"raw JSONs kept at {tmpdir} (NOT in data/ — do not commit)")
    return record


def run_synthetic() -> dict:
    """Labelled-synthetic fallback (seed 42). Never overwrites live files."""
    import numpy as np

    rng = np.random.default_rng(42)
    states = [
        "CA",
        "TX",
        "FL",
        "NY",
        "LA",
        "MS",
        "AL",
        "GA",
        "OH",
        "PA",
        "MI",
        "NC",
        "AZ",
        "WA",
        "CO",
        "MN",
        "WI",
        "KY",
        "WV",
        "NM",
    ]
    all_rows: dict[str, list[dict]] = {}
    for measure, (lo, hi) in SYNTHETIC_RANGES.items():
        for year in ("2023", "2022"):
            rows = []
            for i in range(200):
                st = states[i % len(states)]
                base = rng.uniform(lo, hi)
                val = round(
                    base if year == "2023" else base * rng.uniform(0.95, 1.05), 1
                )
                pop18 = int(rng.integers(5_000, 400_000))
                rows.append(
                    {
                        "year": year,
                        "stateabbr": st,
                        "statedesc": st,
                        "locationname": f"Synthetic County {i + 1:03d}",
                        "locationid": f"{i + 1:05d}",
                        "measureid": measure,
                        "measure": MEASURE_LABELS[measure],
                        "short_question_text": MEASURE_LABELS[measure],
                        "data_value": val,
                        "low_confidence_limit": round(max(0.1, val - 2.5), 1),
                        "high_confidence_limit": round(val + 2.5, 1),
                        "totalpopulation": int(pop18 * 1.3),
                        "totalpop18plus": pop18,
                        "data_value_footnote_symbol": "",
                        "data_value_footnote": "",
                        "datasource": "SYNTHETIC",
                        "geolocation": {
                            "type": "Point",
                            "coordinates": [
                                round(float(rng.uniform(-125, -66)), 3),
                                round(float(rng.uniform(25, 49)), 3),
                            ],
                        },
                    }
                )
            # One synthetic US aggregate row, dropped by the shared path.
            rows.append(
                {
                    "year": year,
                    "stateabbr": "US",
                    "statedesc": "United States",
                    "locationname": "United States",
                    "locationid": "00000",
                    "measureid": measure,
                    "measure": MEASURE_LABELS[measure],
                    "short_question_text": MEASURE_LABELS[measure],
                    "data_value": round((lo + hi) / 2, 1),
                    "low_confidence_limit": round((lo + hi) / 2 - 1, 1),
                    "high_confidence_limit": round((lo + hi) / 2 + 1, 1),
                    "totalpopulation": 330_000_000,
                    "totalpop18plus": 260_000_000,
                    "data_value_footnote_symbol": "",
                    "data_value_footnote": "",
                    "datasource": "SYNTHETIC",
                    "geolocation": {"type": "Point", "coordinates": [-98.0, 39.0]},
                }
            )
            all_rows[f"{measure}_{year}"] = rows
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "places_synthetic.json").write_text(
        json.dumps(all_rows, indent=2) + "\n", encoding="utf-8"
    )
    return process_raw_rows(all_rows, "synthetic", {"synthetic": True, "seed": 42})


def run_offline() -> None:
    """Regenerate derived tables from committed CSVs; never clobber live meta.

    Day 5/6 lesson: an offline run must NOT rewrite data_source.json's
    `source: "live"` field. If a live record exists, derived tables are
    regenerated and the record is left byte-identical.
    """
    existing = PROCESSED_DIR / "data_source.json"
    if not existing.exists():
        raise RuntimeError("no data_source.json — run --live first")
    record = json.loads(existing.read_text(encoding="utf-8"))
    frames = []
    us_values: dict = {}
    for measure, slug in MEASURES.items():
        path = PROCESSED_DIR / f"prevalence_{slug}.csv"
        if not path.exists():
            raise RuntimeError(f"missing committed file: {path}")
        df = pd.read_csv(path, dtype={"locationid": str, "year": str})
        df["measureid"] = measure
        df["statedesc"] = df["stateabbr"]  # rebuilt below from state table
        frames.append(df)
    county = pd.concat(frames, ignore_index=True)
    # CIs are not stored per row in the committed CSVs; reuse the recorded
    # median widths for the offline record instead of recomputing them.
    county["low_ci"] = county["data_value"] - 1.0
    county["high_ci"] = county["data_value"] + 1.0
    state_path = PROCESSED_DIR / "state_prevalence.csv"
    old_state = pd.read_csv(state_path, dtype={"year": str})
    statedesc = {
        (r["measureid"], r["year"], r["stateabbr"]): r["statedesc"]
        for _, r in old_state.iterrows()
    }
    county["statedesc"] = [
        statedesc.get((m, y, s), s)
        for m, y, s in zip(county["measureid"], county["year"], county["stateabbr"])
    ]
    prevalence, change, state, meta = build_derived(county, us_values)
    # Restore the recorded CI widths and national values (not recomputable
    # offline from the compact CSVs) so the offline record stays honest.
    meta["median_ci_width"] = record.get("median_ci_width_pp", {})
    meta["national"] = record.get("national_weighted_vs_us_row", {})
    for slug, df in prevalence.items():
        df.to_csv(PROCESSED_DIR / f"prevalence_{slug}.csv", index=False)
    for slug, df in change.items():
        df.to_csv(PROCESSED_DIR / f"change_{slug}.csv", index=False)
    state.to_csv(PROCESSED_DIR / "state_prevalence.csv", index=False)
    print(
        "offline: derived tables regenerated; data_source.json untouched "
        f"(source={record.get('source')!r})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true")
    group.add_argument("--offline", action="store_true")
    group.add_argument("--synthetic", action="store_true")
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="keep raw JSONs under the system temp dir",
    )
    args = parser.parse_args(argv)
    try:
        if args.live:
            run_live(args.keep_raw)
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
