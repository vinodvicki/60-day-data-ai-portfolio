"""Day 17 Drought Impact Analyzer: data pipeline.

Fetches weekly US Drought Monitor severity (DSCI by state, % area in each
D0-D4 class by county) for Iowa and Illinois, 2000-2025, reuses Day 16's
verified maize-yield series (FAO via Our World in Data) and Corn Belt
weather (Open-Meteo ERA5 archive), and joins them into one annual
drought-yield dataset plus county-year drought aggregates.

Modes:
    --live       fetch from the sources, then build (default)
    --offline    replay from committed raw files, no network
    --use-cache  use raw files if present, else fetch

The weekly county raw CSVs are large (~4 MB per 9-year block per state)
and are NOT committed: they are saved locally (git-ignored) and aggregated
immediately. In --offline mode the county aggregates rebuild from the
committed processed county_year.csv instead.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path
from typing import Any, cast

import pandas as pd
import requests

# --- Frozen configuration (plan.md §2/§3) ---------------------------------

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DAY16_DIR = ROOT.parent / "day-16-crop-yield-prediction"

USDM_BASE = "https://usdmdataservices.unl.edu/api"
YIELD_URL = "https://ourworldindata.org/grapher/maize-yields.csv?country=USA"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)

# FIPS codes: Iowa 19, Illinois 17.
STATES = {
    "iowa": {"fips": "19", "abbr": "IA"},
    "illinois": {"fips": "17", "abbr": "IL"},
}
WEATHER_CENTROIDS = {
    "iowa": {"latitude": 41.8780, "longitude": -93.0977},
    "illinois": {"latitude": 40.6331, "longitude": -89.3985},
}

START_YEAR = 2000
END_YEAR = 2025

# County fetch is split into blocks so one failure loses a block, not all.
COUNTY_BLOCKS = [(2000, 2008), (2009, 2017), (2018, 2025)]

# 1 tonne of corn = 39.368 bushels (56 lb/bu); 1 ha = 2.47105 acres.
BU_PER_ACRE_PER_T_PER_HA = 39.368 / 2.47105  # 15.932...

GROWING_MONTHS = (4, 5, 6, 7, 8, 9)  # April-September inclusive

EXPECTED_COUNTIES = {"iowa": 99, "illinois": 102}


# --- Fetching ---------------------------------------------------------------


def _get_with_retry(
    url: str, params: dict[str, Any] | None = None
) -> requests.Response:
    """One GET with a single retry after 10 s on a 5xx; then raise."""
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status is not None and 500 <= status < 600:
            time.sleep(10)
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            return resp
        raise


def fetch_state_dsci(state: str) -> str:
    """Download one state's weekly DSCI CSV from the USDM REST API."""
    fips = STATES[state]["fips"]
    url = f"{USDM_BASE}/StateStatistics/GetDSCI"
    params = {
        "aoi": fips,
        "startdate": "1/1/2000",
        "enddate": "12/31/2025",
        "statisticsType": "1",
    }
    return _get_with_retry(url, params=params).text


def fetch_county_block(state: str, start: int, end: int) -> str:
    """Download one state's county % area CSV for one year block."""
    abbr = STATES[state]["abbr"]
    url = f"{USDM_BASE}/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
    params = {
        "aoi": abbr,
        "startdate": f"1/1/{start}",
        "enddate": f"12/31/{end}",
        "statisticsType": "1",
    }
    return _get_with_retry(url, params=params).text


def fetch_yields() -> str:
    """Fallback: download the OWID maize-yields CSV (only if the Day 16 copy is missing)."""
    return _get_with_retry(YIELD_URL).text


def fetch_weather(state: str) -> dict[str, Any]:
    """Fallback: download one state's daily weather JSON from Open-Meteo."""
    params: dict[str, Any] = {
        **WEATHER_CENTROIDS[state],
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,temperature_2m_max,precipitation_sum",
        "timezone": "America/Chicago",
    }
    return cast(dict[str, Any], _get_with_retry(WEATHER_URL, params=params).json())


# --- Cleaning / aggregation -------------------------------------------------


def clean_state_dsci(csv_text: str, state: str) -> pd.DataFrame:
    """Parse one state's weekly DSCI CSV; assert weekly, 0-500, complete."""
    from io import StringIO

    raw = pd.read_csv(StringIO(csv_text))
    if list(raw.columns) != ["Name", "MapDate", "DSCI"]:
        raise ValueError(f"{state}: unexpected DSCI columns {list(raw.columns)}")
    frame = raw.rename(columns={"MapDate": "map_date", "DSCI": "dsci"})
    frame["map_date"] = pd.to_datetime(frame["map_date"].astype(str), format="%Y%m%d")
    frame = frame[["map_date", "dsci"]].sort_values("map_date").reset_index(drop=True)
    if frame["dsci"].isna().any():
        raise ValueError(f"{state}: missing DSCI values")
    if ((frame["dsci"] < 0) | (frame["dsci"] > 500)).any():
        raise ValueError(f"{state}: DSCI outside 0-500")
    if frame["map_date"].duplicated().any():
        raise ValueError(f"{state}: duplicate DSCI weeks")
    if frame["map_date"].iloc[0] != pd.Timestamp("2000-01-04"):
        raise ValueError(
            f"{state}: first DSCI week is {frame['map_date'].iloc[0]}, expected 2000-01-04"
        )
    return frame


def clean_county_block(csv_text: str, state: str) -> pd.DataFrame:
    """Parse one county % area CSV block; assert the % columns sum to 100.

    The USDM columns are cumulative (D0 = % in D0 or worse), so the
    exclusive shares are None, D0-D1, D1-D2, D2-D3, D3-D4, D4. The USDM
    DSCI weights the exclusive shares 1..5, which with cumulative
    columns is algebraically D0 + D1 + D2 + D3 + D4 (max 500) -- see
    ``county_dsci_proxy``. We assert that, plus each column in 0-100
    and monotone D0 >= D1 >= D2 >= D3 >= D4.
    """
    from io import StringIO

    raw = pd.read_csv(StringIO(csv_text))
    expected = [
        "MapDate",
        "FIPS",
        "County",
        "State",
        "None",
        "D0",
        "D1",
        "D2",
        "D3",
        "D4",
        "ValidStart",
        "ValidEnd",
        "StatisticFormatID",
    ]
    if list(raw.columns) != expected:
        raise ValueError(f"{state}: unexpected county columns {list(raw.columns)}")
    frame = raw.rename(
        columns={
            "MapDate": "map_date",
            "FIPS": "fips",
            "County": "county",
            "State": "state",
            "ValidStart": "valid_start",
            "ValidEnd": "valid_end",
        }
    )
    frame["map_date"] = pd.to_datetime(frame["map_date"].astype(str), format="%Y%m%d")
    frame["valid_start"] = pd.to_datetime(frame["valid_start"])
    frame["fips"] = frame["fips"].astype(str).str.zfill(5)
    for col in ["None", "D0", "D1", "D2", "D3", "D4"]:
        if frame[col].isna().any():
            raise ValueError(f"{state}: missing values in {col}")
        if ((frame[col] < 0) | (frame[col] > 100)).any():
            raise ValueError(f"{state}: {col} outside 0-100")
    total = frame["None"] + frame["D0"]
    if (total - 100.0).abs().max() > 0.05:
        raise ValueError(
            f"{state}: None + D0 deviates from 100 by {(total - 100.0).abs().max():.3f}"
        )
    if (
        (frame["D0"] < frame["D1"])
        | (frame["D1"] < frame["D2"])
        | (frame["D2"] < frame["D3"])
        | (frame["D3"] < frame["D4"])
    ).any():
        raise ValueError(
            f"{state}: drought classes are not monotone D0>=D1>=D2>=D3>=D4"
        )
    if frame["fips"].str.len().ne(5).any():
        raise ValueError(f"{state}: non-5-digit FIPS present")
    return frame


def county_dsci_proxy(frame: pd.DataFrame) -> pd.Series:
    """Weekly county DSCI proxy from cumulative % columns (USDM definition).

    USDM defines DSCI as 1x the exclusive D0 share + 2x D1 + 3x D2 +
    4x D3 + 5x D4. The API columns are cumulative (D0 = % in D0 or
    worse), so the exclusive shares are D0-D1, D1-D2, D2-D3, D3-D4, D4
    and the weighted sum collapses to D0 + D1 + D2 + D3 + D4 (max 500).
    Weighting the cumulative columns 1..5 would double-count and can
    exceed 500 — that was a bug in the first build, fixed 2026-11-24.
    """
    return frame["D0"] + frame["D1"] + frame["D2"] + frame["D3"] + frame["D4"]


def aggregate_state_annual(dsci: pd.DataFrame, state: str) -> pd.DataFrame:
    """Annual growing-season aggregates from one state's weekly DSCI."""
    frame = dsci.copy()
    frame["year"] = frame["map_date"].dt.year
    frame["month"] = frame["map_date"].dt.month
    frame["is_gs"] = frame["month"].isin(GROWING_MONTHS)
    rows = []
    for year, group in frame.groupby("year"):
        gs = group[group["is_gs"]]
        rows.append(
            {
                "year": int(year),
                f"gs_dsci_mean_{state}": float(gs["dsci"].mean()),
                f"gs_dsci_max_{state}": float(group["dsci"].max()),
                f"weeks_dsci_ge100_{state}": int((group["dsci"] >= 100).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def aggregate_county_annual(frame: pd.DataFrame) -> pd.DataFrame:
    """County-year growing-season aggregates from weekly county % area."""
    frame = frame.copy()
    frame["year"] = frame["valid_start"].dt.year
    frame["month"] = frame["valid_start"].dt.month
    gs = frame[frame["month"].isin(GROWING_MONTHS)].copy()
    gs["dsci"] = county_dsci_proxy(gs)
    grouped = gs.groupby(["fips", "county", "state", "year"], as_index=False).agg(
        gs_d1plus_pct=("D1", "mean"),
        gs_d2plus_pct=("D2", "mean"),
        gs_d3plus_pct=("D3", "mean"),
        gs_dsci=("dsci", "mean"),
    )
    return grouped.sort_values(["state", "fips", "year"]).reset_index(drop=True)


def clean_yields(csv_text: str) -> pd.DataFrame:
    """Filter the OWID CSV to USA 2000-2025; assert 26 complete rows."""
    from io import StringIO

    raw = pd.read_csv(StringIO(csv_text))
    usa = raw[raw["Entity"] == "United States"].copy()
    usa = usa.rename(columns={"Year": "year", "Maize yield": "yield_t_per_ha"})
    usa = usa[["year", "yield_t_per_ha"]]
    usa = usa[(usa["year"] >= START_YEAR) & (usa["year"] <= END_YEAR)]
    usa = usa.sort_values("year").reset_index(drop=True)
    if len(usa) != END_YEAR - START_YEAR + 1:
        raise ValueError(f"expected 26 yield rows, got {len(usa)}")
    if usa["yield_t_per_ha"].isna().any():
        raise ValueError("missing yield values")
    if (usa["yield_t_per_ha"] <= 0).any():
        raise ValueError("non-positive yield values")
    if not usa["year"].is_monotonic_increasing:
        raise ValueError("years are not strictly increasing")
    return usa


def build_precip_features(daily: dict[str, Any]) -> pd.DataFrame:
    """Aggregate one state's daily weather into annual precipitation features.

    Growing-season (Apr-Sep) precipitation total and July total, per year.
    """
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "precip": daily["precipitation_sum"],
        }
    )
    if frame["precip"].isna().any():
        raise ValueError("missing daily precipitation values")
    if (frame["precip"] < 0).any():
        raise ValueError("negative precipitation values")
    frame = frame.sort_values("date").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise ValueError("duplicate weather dates")
    gaps = frame["date"].diff().dropna()
    if (gaps != pd.Timedelta(days=1)).any():
        raise ValueError("weather dates are not contiguous daily")
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    gs = frame[frame["month"].isin(GROWING_MONTHS)]
    july = frame[frame["month"] == 7]
    rows = []
    for year, group in gs.groupby("year"):
        july_group = july[july["year"] == year]
        rows.append(
            {
                "year": int(year),
                "gs_precip_total": float(group["precip"].sum()),
                "jul_precip_total": float(july_group["precip"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def build_annual_dataset(
    yields: pd.DataFrame,
    state_annual: dict[str, pd.DataFrame],
    precip_by_state: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Join yields with two-state drought + precipitation annual features."""
    annual = yields.copy()
    for table in state_annual.values():
        annual = annual.merge(table, on="year", how="inner")
    precip_avg = (
        pd.concat(precip_by_state.values())
        .groupby("year")[["gs_precip_total", "jul_precip_total"]]
        .mean()
        .reset_index()
    )
    annual = annual.merge(precip_avg, on="year", how="inner")
    if len(annual) != END_YEAR - START_YEAR + 1:
        raise ValueError(f"expected 26 annual rows, got {len(annual)}")

    annual["yield_bu_per_acre"] = annual["yield_t_per_ha"] * BU_PER_ACRE_PER_T_PER_HA
    annual["gs_dsci_mean"] = (
        annual["gs_dsci_mean_iowa"] + annual["gs_dsci_mean_illinois"]
    ) / 2.0
    annual["gs_dsci_max"] = annual[["gs_dsci_max_iowa", "gs_dsci_max_illinois"]].max(
        axis=1
    )
    annual["weeks_dsci_ge100"] = annual[
        ["weeks_dsci_ge100_iowa", "weeks_dsci_ge100_illinois"]
    ].max(axis=1)
    mean_precip = annual["gs_precip_total"].mean()
    mean_july = annual["jul_precip_total"].mean()
    annual["gs_precip_anomaly_mm"] = annual["gs_precip_total"] - mean_precip
    annual["gs_precip_anomaly_pct"] = (
        annual["gs_precip_anomaly_mm"] / mean_precip * 100.0
    )
    annual["jul_precip_anomaly_mm"] = annual["jul_precip_total"] - mean_july
    cols = [
        "year",
        "yield_t_per_ha",
        "yield_bu_per_acre",
        "gs_dsci_mean",
        "gs_dsci_mean_iowa",
        "gs_dsci_mean_illinois",
        "gs_dsci_max",
        "weeks_dsci_ge100",
        "gs_precip_total_mm",
        "gs_precip_anomaly_mm",
        "gs_precip_anomaly_pct",
        "jul_precip_anomaly_mm",
    ]
    annual = annual.rename(columns={"gs_precip_total": "gs_precip_total_mm"})
    return annual[cols]


def build_county_summary(county_year: pd.DataFrame) -> pd.DataFrame:
    """Per-county summary over 2000-2025 + worst year per county."""
    grouped = county_year.groupby(["fips", "county", "state"], as_index=False).agg(
        mean_d2plus_pct=("gs_d2plus_pct", "mean"),
        mean_dsci=("gs_dsci", "mean"),
    )
    worst_idx = county_year.groupby(["fips", "county", "state"])[
        "gs_d2plus_pct"
    ].idxmax()
    worst = county_year.loc[worst_idx, ["fips", "year", "gs_d2plus_pct"]].rename(
        columns={"year": "worst_year", "gs_d2plus_pct": "worst_year_d2plus_pct"}
    )
    summary = grouped.merge(worst, on="fips", how="left")
    return summary.sort_values("mean_d2plus_pct", ascending=False).reset_index(
        drop=True
    )


# --- Orchestration ----------------------------------------------------------


def _copy_day16_raw() -> tuple[str, dict[str, dict[str, Any]]]:
    """Copy Day 16's committed raw yield + weather files into this day's raw dir."""
    src_yield = DAY16_DIR / "data" / "raw" / "maize_yields_owid.csv"
    csv_text = src_yield.read_text(encoding="utf-8")
    (RAW_DIR / "maize_yields_owid.csv").write_text(csv_text, encoding="utf-8")
    weather_raw: dict[str, dict[str, Any]] = {}
    for state in WEATHER_CENTROIDS:
        src = DAY16_DIR / "data" / "raw" / f"weather_{state}.json"
        raw = json.loads(src.read_text(encoding="utf-8"))
        weather_raw[state] = raw
        (RAW_DIR / f"weather_{state}.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
    return csv_text, weather_raw


def load_raw_offline() -> tuple[
    dict[str, pd.DataFrame],
    pd.DataFrame | None,
    str,
    dict[str, dict[str, Any]],
]:
    """Read committed raw files (offline mode): state DSCI + Day 16 copies."""
    state_dsci = {
        state: clean_state_dsci(
            (RAW_DIR / f"dsci_{state}.csv").read_text(encoding="utf-8"), state
        )
        for state in STATES
    }
    county_year_path = PROCESSED_DIR / "county_year.csv"
    county_year = pd.read_csv(county_year_path) if county_year_path.exists() else None
    csv_text = (RAW_DIR / "maize_yields_owid.csv").read_text(encoding="utf-8")
    weather_raw = {
        state: json.loads(
            (RAW_DIR / f"weather_{state}.json").read_text(encoding="utf-8")
        )
        for state in WEATHER_CENTROIDS
    }
    return state_dsci, county_year, csv_text, weather_raw


def run(mode: str) -> dict[str, pd.DataFrame]:
    """Fetch (or replay) raw data, build the datasets, write processed files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    county_raw_available = True
    if mode == "offline":
        state_dsci, county_year, csv_text, weather_raw = load_raw_offline()
        fetched_from = "committed raw files (offline)"
        fetched_live = False
        county_raw_available = False
        if county_year is None:
            raise ValueError(
                "offline mode needs data/processed/county_year.csv "
                "(county raw files are not committed)"
            )
    elif mode == "use-cache":
        needed = (
            [RAW_DIR / f"dsci_{s}.csv" for s in STATES]
            + [RAW_DIR / "maize_yields_owid.csv"]
            + [RAW_DIR / f"weather_{s}.json" for s in WEATHER_CENTROIDS]
        )
        if all(p.exists() for p in needed):
            state_dsci, county_year, csv_text, weather_raw = load_raw_offline()
            fetched_from = "committed raw files (cache)"
            fetched_live = False
            county_raw_available = False
            if county_year is None:
                raise ValueError(
                    "cache mode needs data/processed/county_year.csv "
                    "(county raw files are not committed)"
                )
        else:
            state_dsci, county_year, csv_text, weather_raw = _fetch_all()
            fetched_from = "live fetch"
            fetched_live = True
    else:  # live
        state_dsci, county_year, csv_text, weather_raw = _fetch_all()
        fetched_from = "live fetch"
        fetched_live = True

    yields = clean_yields(csv_text)
    if county_year is None:
        raise ValueError("county-year aggregates are missing (see mode handling above)")
    precip = {
        state: build_precip_features(raw["daily"]) for state, raw in weather_raw.items()
    }
    state_annual = {
        state: aggregate_state_annual(dsci, state) for state, dsci in state_dsci.items()
    }
    annual = build_annual_dataset(yields, state_annual, precip)

    # The county D2+ signal lives in county_year.csv / county_summary.csv;
    # the annual table keeps weeks_dsci_ge100 as its drought-weeks count.
    county_summary = build_county_summary(county_year)
    _assert_counts(state_dsci, county_year, annual)

    # Enrich the annual table in the same run (plan §5: the pipeline calls
    # the analysis module). Without this, a later --offline run would
    # rewrite annual_drought_yield.csv WITHOUT the residual columns that
    # analysis.py adds, breaking byte-identical offline reproduction
    # (caught by the tester, 2026-11-24).
    from src import analysis as _analysis

    annual = _analysis.detrend_yield(annual)
    correlations = _analysis.compute_correlations(annual)
    forecast = _analysis.ar1_forecast_table(annual)

    annual.to_csv(PROCESSED_DIR / "annual_drought_yield.csv", index=False)
    correlations.to_csv(PROCESSED_DIR / "correlation_results.csv", index=False)
    forecast.to_csv(PROCESSED_DIR / "ar1_forecast.csv", index=False)
    county_year.to_csv(PROCESSED_DIR / "county_year.csv", index=False)
    county_summary.to_csv(PROCESSED_DIR / "county_summary.csv", index=False)

    if fetched_live:
        provenance = _provenance(
            fetched_from, state_dsci, county_year, annual, county_raw_available
        )
        (PROCESSED_DIR / "data_source.json").write_text(
            json.dumps(provenance, indent=2), encoding="utf-8"
        )
    return {
        "annual": annual,
        "county_year": county_year,
        "county_summary": county_summary,
    }


def _assert_counts(
    state_dsci: dict[str, pd.DataFrame],
    county_year: pd.DataFrame,
    annual: pd.DataFrame,
) -> None:
    """Frozen cross-checks (plan §3.3) before any processed file is trusted."""
    for state, dsci in state_dsci.items():
        if len(dsci) < 1300:
            raise ValueError(f"{state}: only {len(dsci)} DSCI weeks, expected ~1357")
    if len(annual) != 26:
        raise ValueError(f"expected 26 annual rows, got {len(annual)}")
    if len(county_year) != 201 * 26:
        raise ValueError(f"expected 5226 county-year rows, got {len(county_year)}")
    for state, expected in EXPECTED_COUNTIES.items():
        abbr = STATES[state]["abbr"]
        n = county_year[county_year["state"] == abbr]["fips"].nunique()
        if n != expected:
            raise ValueError(f"{state}: {n} counties, expected {expected}")
    worst_year = int(annual.loc[annual["gs_dsci_mean"].idxmax(), "year"])
    if worst_year != 2012:
        raise ValueError(f"expected 2012 as worst drought year, got {worst_year}")
    resid_2012 = annual.loc[annual["year"] == 2012, "yield_t_per_ha"].iloc[0]
    if resid_2012 >= annual["yield_t_per_ha"].max():
        raise ValueError("2012 yield is not below the series maximum (sanity check)")


def _provenance(
    fetched_from: str,
    state_dsci: dict[str, pd.DataFrame],
    county_year: pd.DataFrame,
    annual: pd.DataFrame,
    county_raw_available: bool,
) -> dict[str, Any]:
    return {
        "project": "Day 17 — Drought Impact Analyzer",
        "fetch_date": date.today().isoformat(),
        "fetched_from": fetched_from,
        "synthetic": False,
        "county_raw_available": county_raw_available,
        "sources": {
            "drought": {
                "provider": "U.S. Drought Monitor (NDMC / USDA / NOAA)",
                "api_base": USDM_BASE,
                "endpoints": {
                    "state_dsci": "StateStatistics/GetDSCI",
                    "county_area": (
                        "CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
                    ),
                },
                "states": {
                    state: {
                        "fips": cfg["fips"],
                        "weekly_rows": len(state_dsci[state]),
                        "first_week": str(state_dsci[state]["map_date"].iloc[0].date()),
                        "last_week": str(state_dsci[state]["map_date"].iloc[-1].date()),
                    }
                    for state, cfg in STATES.items()
                },
                "county_blocks": [f"{a}-{b}" for a, b in COUNTY_BLOCKS],
                "note": (
                    "Weekly county raw CSVs (~4 MB per block per state) are NOT "
                    "committed (size rule); the committed county_year.csv "
                    "aggregates are the auditable record."
                ),
            },
            "yields": {
                "provider": "FAO via Our World in Data",
                "url": YIELD_URL,
                "licence": "CC BY 4.0",
                "unit": "tonnes per hectare",
                "rows_usa_2000_2025": 26,
                "copied_from": "day-16-crop-yield-prediction/data/raw/maize_yields_owid.csv",
                "fetch_date": "2026-11-23",
            },
            "weather": {
                "provider": "Open-Meteo ERA5 archive",
                "url": WEATHER_URL,
                "licence": "CC BY 4.0",
                "states": {
                    state: {
                        "latitude": cfg["latitude"],
                        "longitude": cfg["longitude"],
                    }
                    for state, cfg in WEATHER_CENTROIDS.items()
                },
                "copied_from": "day-16-crop-yield-prediction/data/raw/weather_*.json",
                "fetch_date": "2026-11-23",
            },
            "county_boundaries": {
                "provider": "US Census Bureau via plotly datasets",
                "url": GEOJSON_URL,
                "licence": "public domain",
                "note": "Fetched at chart time, not committed (3.2 MB).",
            },
        },
        "unit_conversion": {
            "t_per_ha_to_bu_per_acre": BU_PER_ACRE_PER_T_PER_HA,
            "note": "1 tonne corn = 39.368 bu; 1 ha = 2.47105 acres",
        },
        "dsci_definition": (
            "DSCI = 1*D0 + 2*D1 + 3*D2 + 4*D3 + 5*D4 (percent of area), "
            "range 0-500. D0 abnormally dry, D1 moderate, D2 severe, "
            "D3 extreme, D4 exceptional drought."
        ),
        "row_counts": {
            "annual_rows": len(annual),
            "county_year_rows": len(county_year),
            "county_summary_rows": 201,
        },
        "note": (
            "USDA Quick Stats (roadmap suggestion) needs an API key "
            "(HTTP 401 without one), so county-level yields are out of "
            "scope; the county analysis is drought severity by county vs "
            "national yield by year. Weather is a 2-state Corn Belt proxy "
            "(Iowa + Illinois average), not a national average. "
            "See research_brief.md."
        ),
    }


def _fetch_all() -> (
    tuple[dict[str, pd.DataFrame], pd.DataFrame, str, dict[str, dict[str, Any]]]
):
    """Fetch all live sources; commit the small raw files, cache the large ones."""
    state_dsci = {}
    for state in STATES:
        text = fetch_state_dsci(state)
        (RAW_DIR / f"dsci_{state}.csv").write_text(text, encoding="utf-8")
        state_dsci[state] = clean_state_dsci(text, state)

    county_frames = []
    for state in STATES:
        for start, end in COUNTY_BLOCKS:
            text = fetch_county_block(state, start, end)
            path = RAW_DIR / f"dsci_counties_{state}_{start}_{end}.csv"
            path.write_text(text, encoding="utf-8")
            county_frames.append(clean_county_block(text, state))
    county_all = pd.concat(county_frames, ignore_index=True)
    county_year = aggregate_county_annual(county_all)

    day16_yield = DAY16_DIR / "data" / "raw" / "maize_yields_owid.csv"
    day16_weather = {
        state: DAY16_DIR / "data" / "raw" / f"weather_{state}.json"
        for state in WEATHER_CENTROIDS
    }
    if day16_yield.exists() and all(p.exists() for p in day16_weather.values()):
        csv_text, weather_raw = _copy_day16_raw()
    else:
        csv_text = fetch_yields()
        (RAW_DIR / "maize_yields_owid.csv").write_text(csv_text, encoding="utf-8")
        weather_raw = {}
        for state in WEATHER_CENTROIDS:
            raw = fetch_weather(state)
            weather_raw[state] = raw
            (RAW_DIR / f"weather_{state}.json").write_text(
                json.dumps(raw), encoding="utf-8"
            )
    return state_dsci, county_year, csv_text, weather_raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="fetch from the sources (default)"
    )
    parser.add_argument(
        "--offline", action="store_true", help="replay from committed raw files"
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="use raw files if present, else fetch",
    )
    args = parser.parse_args()
    mode = "offline" if args.offline else "use-cache" if args.use_cache else "live"
    out = run(mode)
    annual = out["annual"]
    worst = annual.loc[annual["gs_dsci_mean"].idxmax()]
    print(
        f"mode={mode} annual_rows={len(annual)} "
        f"county_year_rows={len(out['county_year'])} "
        f"worst_year={int(worst['year'])} gs_dsci_mean={float(worst['gs_dsci_mean']):.1f}"
    )


if __name__ == "__main__":
    main()
