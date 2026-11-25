"""Day 18 Agricultural Commodity Price Analyzer: data pipeline.

Fetches monthly IMF benchmark prices for maize, wheat and soybeans from
FRED (fredgraph.csv, no key), reuses Day 16's Corn Belt weather
(Open-Meteo ERA5 archive) and Day 17's US Drought Monitor state DSCI and
county D2+ aggregates, and joins them into one annual price / weather /
drought dataset plus seasonality, shock, correlation, regression and
forecast tables.

Modes:
    --live       fetch prices from FRED, then build (default)
    --offline    replay from committed raw files, no network
    --use-cache  use raw files if present, else fetch

The county GeoJSON (3.2 MB) is NOT committed: it is fetched at chart time
by make_charts.py and cached locally (git-ignored). All other raw files
are small and committed as the provenance record.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

# --- Frozen configuration (plan.md §2/§3) ---------------------------------

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DAY16_DIR = ROOT.parent / "day-16-crop-yield-prediction"
DAY17_DIR = ROOT.parent / "day-17-drought-impact-analyzer"

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SERIES = {
    "maize": "PMAIZMTUSDM",
    "wheat": "PWHEAMTUSDM",
    "soybeans": "PSOYBUSDM",
}
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
USDM_BASE = "https://usdmdataservices.unl.edu/api"
GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)

STATES = {
    "iowa": {"fips": "19", "abbr": "IA"},
    "illinois": {"fips": "17", "abbr": "IL"},
}
WEATHER_CENTROIDS = {
    "iowa": {"latitude": 41.8780, "longitude": -93.0977},
    "illinois": {"latitude": 40.6331, "longitude": -89.3985},
}

GROWING_MONTHS = (4, 5, 6, 7, 8, 9)  # April-September inclusive
START_YEAR = 2000
END_YEAR = 2025
PRICE_START = "1992-01-01"
PRICE_END = "2026-09-01"
EXPECTED_PRICE_MONTHS = 417  # 1992-01 .. 2026-09 inclusive
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
        status = exc.response.status_code if exc.response is not None else 0
        if status >= 500:
            time.sleep(10)
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            return resp
        raise


def _download(url: str, dest: Path, params: dict[str, Any] | None = None) -> None:
    """Download a URL to a file (text content, UTF-8)."""
    resp = _get_with_retry(url, params=params)
    dest.write_text(resp.text, encoding="utf-8")


def _copy_or_fetch(
    src_dir: Path, filename: str, dest: Path, url: str | None = None
) -> str:
    """Copy a reused raw file from a sibling day folder, else fetch it.

    Returns "copied from day-XX" or "live fetch". Raises if neither works.
    """
    src = src_dir / filename
    if src.exists():
        dest.write_bytes(src.read_bytes())
        return f"copied from {src_dir.name}"
    if url is None:
        raise FileNotFoundError(f"reused raw file missing: {src} (no URL fallback)")
    _download(url, dest)
    return "live fetch"


# --- Prices -----------------------------------------------------------------


def fetch_prices(mode: str) -> dict[str, str]:
    """Ensure the three FRED raw CSVs exist; return {commodity: provenance}."""
    provenance: dict[str, str] = {}
    for commodity, series_id in SERIES.items():
        dest = RAW_DIR / f"fred_{commodity}.csv"
        if mode in ("offline", "use-cache") and dest.exists():
            provenance[commodity] = "committed cache"
            continue
        if mode == "offline":
            raise FileNotFoundError(f"offline mode needs committed raw file: {dest}")
        _download(FRED_BASE, dest, params={"id": series_id})
        provenance[commodity] = "live fetch"
    return provenance


def clean_prices() -> pd.DataFrame:
    """Read the three FRED raw CSVs into one monthly price table.

    Returns 1,251 rows (417 months x 3 commodities) with columns
    date, commodity, price_usd_per_t, log_return. A missing month or a
    non-positive price stops the build — never silently forward-filled.
    """
    frames: list[pd.DataFrame] = []
    for commodity, series_id in SERIES.items():
        path = RAW_DIR / f"fred_{commodity}.csv"
        raw = pd.read_csv(path)
        if series_id not in raw.columns:
            raise ValueError(f"{path}: expected column {series_id}")
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(raw["observation_date"]),
                "commodity": commodity,
                "price_usd_per_t": pd.to_numeric(raw[series_id], errors="coerce"),
            }
        )
        if frame["price_usd_per_t"].isna().any():
            raise ValueError(f"{commodity}: non-numeric price in {path}")
        if (frame["price_usd_per_t"] <= 0).any():
            raise ValueError(f"{commodity}: non-positive price in {path}")
        if len(frame) != EXPECTED_PRICE_MONTHS:
            raise ValueError(
                f"{commodity}: {len(frame)} months, expected "
                f"{EXPECTED_PRICE_MONTHS}"
            )
        expected = pd.date_range(PRICE_START, PRICE_END, freq="MS")
        if (
            not frame["date"]
            .reset_index(drop=True)
            .equals(pd.Series(expected, name="date"))
        ):
            raise ValueError(f"{commodity}: missing or extra months in {path}")
        frame = frame.sort_values("date").reset_index(drop=True)
        frame["log_return"] = np.log(
            frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
        )
        frames.append(frame)
    monthly = pd.concat(frames, ignore_index=True)
    return monthly


# --- Weather (Open-Meteo, reused from Day 16) -------------------------------


def ensure_weather(mode: str) -> dict[str, str]:
    """Ensure the two weather JSONs exist; return {state: provenance}."""
    provenance: dict[str, str] = {}
    for state in ("iowa", "illinois"):
        dest = RAW_DIR / f"weather_{state}.json"
        if dest.exists():
            provenance[state] = "committed cache"
            continue
        centroid = WEATHER_CENTROIDS[state]
        url = (
            f"{WEATHER_URL}?latitude={centroid['latitude']}"
            f"&longitude={centroid['longitude']}"
            "&start_date=2000-01-01&end_date=2025-12-31"
            "&daily=temperature_2m_mean,temperature_2m_max,precipitation_sum"
            "&timezone=America%2FChicago"
        )
        if mode == "offline":
            raise FileNotFoundError(f"offline mode needs committed raw file: {dest}")
        _download(url, dest)
        provenance[state] = "live fetch"
    return provenance


def build_weather_features(daily_json: dict[str, Any]) -> pd.DataFrame:
    """Daily weather JSON -> one row per year (growing-season aggregates)."""
    daily = daily_json["daily"]
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_mean": daily["temperature_2m_mean"],
            "precip": daily["precipitation_sum"],
        }
    )
    if (frame["precip"] < 0).any():
        raise ValueError("negative precipitation in weather data")
    frame = frame[frame["date"].dt.month.isin(GROWING_MONTHS)]
    grouped = frame.groupby(frame["date"].dt.year).agg(
        gs_temp_mean_c=("temp_mean", "mean"),
        gs_precip_total_mm=("precip", "sum"),
    )
    return grouped.reset_index().rename(columns={"date": "year"})


# --- Drought (USDM state DSCI, reused from Day 17) --------------------------


def ensure_dsci(mode: str) -> dict[str, str]:
    """Ensure the two state DSCI CSVs exist; return {state: provenance}."""
    provenance: dict[str, str] = {}
    for state, cfg in STATES.items():
        dest = RAW_DIR / f"dsci_{state}.csv"
        if dest.exists():
            provenance[state] = "committed cache"
            continue
        url = (
            f"{USDM_BASE}/StateStatistics/GetDSCI?aoi={cfg['fips']}"
            "&startdate=1/1/2000&enddate=12/31/2025&statisticsType=1"
        )
        if mode == "offline":
            raise FileNotFoundError(f"offline mode needs committed raw file: {dest}")
        _download(url, dest)
        provenance[state] = "live fetch"
    return provenance


def aggregate_state_annual(dsci: pd.DataFrame, state: str) -> pd.DataFrame:
    """Weekly state DSCI -> one row per year (growing-season mean DSCI)."""
    frame = dsci.copy()
    frame["map_date"] = pd.to_datetime(frame["MapDate"].astype(str), format="%Y%m%d")
    frame["dsci"] = pd.to_numeric(frame["DSCI"], errors="coerce")
    if frame["dsci"].isna().any():
        raise ValueError(f"{state}: non-numeric DSCI")
    if ((frame["dsci"] < 0) | (frame["dsci"] > 500)).any():
        raise ValueError(f"{state}: DSCI outside 0-500")
    frame = frame[frame["map_date"].dt.month.isin(GROWING_MONTHS)]
    grouped = frame.groupby(frame["map_date"].dt.year).agg(
        gs_dsci_mean=("dsci", "mean"),
    )
    out = grouped.reset_index().rename(columns={"map_date": "year"})
    abbr = STATES[state]["abbr"].lower()
    out = out.rename(columns={"gs_dsci_mean": f"gs_dsci_mean_{abbr}"})
    return out


# --- County D2+ (reused from Day 17 processed county_year.csv) -------------


def load_county_2012() -> pd.DataFrame:
    """2012 growing-season D2+ share per county (IA + IL, 201 counties)."""
    path = RAW_DIR / "county_d2plus_day17.csv"
    raw = pd.read_csv(path, dtype={"fips": str})
    frame = raw[raw["year"] == 2012].copy()
    if len(frame) != 201:
        raise ValueError(f"expected 201 counties for 2012, got {len(frame)}")
    for state, expected in EXPECTED_COUNTIES.items():
        abbr = STATES[state]["abbr"]
        n = frame[frame["state"] == abbr]["fips"].nunique()
        if n != expected:
            raise ValueError(f"{state}: {n} counties for 2012, expected {expected}")
    out = pd.DataFrame(
        {
            "fips": frame["fips"].astype(str).str.zfill(5),
            "county": frame["county"],
            "state": frame["state"],
            "gs_d2plus_pct_2012": frame["gs_d2plus_pct"],
        }
    ).sort_values("gs_d2plus_pct_2012", ascending=False)
    out["rank"] = range(1, len(out) + 1)
    return out.reset_index(drop=True)


# --- Annual tables ----------------------------------------------------------


def build_annual_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """Annual price stats per commodity, full years only (1992-2025)."""
    full = monthly[monthly["date"].dt.year <= END_YEAR].copy()
    rows: list[dict[str, Any]] = []
    for (year, commodity), group in full.groupby([full["date"].dt.year, "commodity"]):
        group = group.sort_values("date")
        rows.append(
            {
                "year": int(year),
                "commodity": commodity,
                "annual_mean_price": float(group["price_usd_per_t"].mean()),
                "annual_max_price": float(group["price_usd_per_t"].max()),
                "annual_min_price": float(group["price_usd_per_t"].min()),
                "annual_volatility": float(group["log_return"].std()),
            }
        )
    annual = pd.DataFrame(rows).sort_values(["commodity", "year"])
    annual["yoy_pct_change"] = (
        annual.groupby("commodity")["annual_mean_price"].pct_change() * 100
    )
    return annual.reset_index(drop=True)


def build_annual_join(
    annual_summary: pd.DataFrame,
    weather: dict[str, pd.DataFrame],
    dsci: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Join annual prices to Corn Belt growing-season weather + drought.

    26 rows (2000-2025). Weather/DSCI are the two-state (IA+IL) means;
    per-state DSCI columns are kept so the numbers are checkable.
    """
    join = pd.DataFrame({"year": range(START_YEAR, END_YEAR + 1)})
    for commodity in SERIES:
        sub = annual_summary[annual_summary["commodity"] == commodity][
            ["year", "annual_mean_price", "yoy_pct_change"]
        ]
        sub = sub.rename(
            columns={
                "annual_mean_price": f"{commodity}_annual_mean_price",
                "yoy_pct_change": f"{commodity}_yoy_pct_change",
            }
        )
        join = join.merge(sub, on="year", how="inner")
    weather_mean = weather["iowa"][
        ["year", "gs_temp_mean_c", "gs_precip_total_mm"]
    ].rename(
        columns={
            "gs_temp_mean_c": "gs_temp_mean_c_ia",
            "gs_precip_total_mm": "gs_precip_total_mm_ia",
        }
    )
    weather_mean = weather_mean.merge(
        weather["illinois"][["year", "gs_temp_mean_c", "gs_precip_total_mm"]].rename(
            columns={
                "gs_temp_mean_c": "gs_temp_mean_c_il",
                "gs_precip_total_mm": "gs_precip_total_mm_il",
            }
        ),
        on="year",
        how="inner",
    )
    weather_mean["gs_temp_mean_c"] = (
        weather_mean["gs_temp_mean_c_ia"] + weather_mean["gs_temp_mean_c_il"]
    ) / 2
    weather_mean["gs_precip_total_mm"] = (
        weather_mean["gs_precip_total_mm_ia"] + weather_mean["gs_precip_total_mm_il"]
    ) / 2
    join = join.merge(
        weather_mean[["year", "gs_temp_mean_c", "gs_precip_total_mm"]],
        on="year",
        how="inner",
    )
    precip_mean = float(join["gs_precip_total_mm"].mean())
    join["gs_precip_anomaly_mm"] = join["gs_precip_total_mm"] - precip_mean
    join["gs_precip_anomaly_pct"] = join["gs_precip_anomaly_mm"] / precip_mean * 100
    dsci_mean = dsci["iowa"][["year", "gs_dsci_mean_ia"]].merge(
        dsci["illinois"][["year", "gs_dsci_mean_il"]],
        on="year",
        how="inner",
    )
    dsci_mean["gs_dsci_mean"] = (
        dsci_mean["gs_dsci_mean_ia"] + dsci_mean["gs_dsci_mean_il"]
    ) / 2
    join = join.merge(dsci_mean, on="year", how="inner")
    if len(join) != 26:
        raise ValueError(f"expected 26 annual join rows, got {len(join)}")
    if join.isna().any().any():
        raise ValueError("NaN in annual join table")
    return join


def _assert_counts(
    monthly: pd.DataFrame,
    annual_summary: pd.DataFrame,
    annual_join: pd.DataFrame,
    county_2012: pd.DataFrame,
) -> None:
    """Frozen cross-checks (plan §3.3) before any processed file is trusted."""
    for commodity in SERIES:
        n = len(monthly[monthly["commodity"] == commodity])
        if n != EXPECTED_PRICE_MONTHS:
            raise ValueError(
                f"{commodity}: {n} months, expected {EXPECTED_PRICE_MONTHS}"
            )
    if len(annual_summary) != 34 * 3:
        raise ValueError(f"expected 102 annual summary rows, got {len(annual_summary)}")
    if 2026 in set(annual_summary["year"]):
        raise ValueError("2026 must be excluded from annual_summary (partial year)")
    if len(annual_join) != 26:
        raise ValueError(f"expected 26 annual join rows, got {len(annual_join)}")
    if len(county_2012) != 201:
        raise ValueError(f"expected 201 counties for 2012, got {len(county_2012)}")
    worst_year = int(annual_join.loc[annual_join["gs_dsci_mean"].idxmax(), "year"])
    if worst_year != 2012:
        raise ValueError(f"expected 2012 as worst drought year, got {worst_year}")
    # Direction checks: 2022 maize above 2021 (war spike), 2020 below 2019.
    maize = annual_summary[annual_summary["commodity"] == "maize"].set_index("year")
    if not maize.loc[2022, "annual_mean_price"] > maize.loc[2021, "annual_mean_price"]:
        raise ValueError("direction check failed: 2022 maize not above 2021")
    if not maize.loc[2020, "annual_mean_price"] < maize.loc[2019, "annual_mean_price"]:
        raise ValueError("direction check failed: 2020 maize not below 2019")


# --- Provenance -------------------------------------------------------------


def _provenance(
    price_prov: dict[str, str],
    weather_prov: dict[str, str],
    dsci_prov: dict[str, str],
    monthly: pd.DataFrame,
    backtest: dict[str, Any],
) -> dict[str, Any]:
    """Provenance record written to data/processed/data_source.json."""
    return {
        "project": "Day 18 — Agricultural Commodity Price Analyzer",
        "generated_at_utc": date.today().isoformat(),
        "synthetic": False,
        "sources": {
            "prices": {
                "source": "IMF Primary Commodity Prices via FRED "
                "(Federal Reserve Bank of St. Louis)",
                "endpoint": FRED_BASE + "?id=<SERIES>",
                "series": SERIES,
                "provenance": price_prov,
                "window": f"{PRICE_START} to {PRICE_END}",
                "frequency": "monthly",
                "rows_per_commodity": EXPECTED_PRICE_MONTHS,
                "note": "2026 is a partial year (Jan-Sep only); "
                "IMF source lags ~2 months. USDA Quick Stats not used: "
                "API requires a key (HTTP 401 without one) and no key "
                "was available to this run.",
            },
            "weather": {
                "source": "Open-Meteo ERA5 archive (CC BY 4.0)",
                "endpoint": WEATHER_URL,
                "provenance": weather_prov,
                "copied_from": "day-16-crop-yield-prediction",
                "fetch_date": "2026-11-23",
                "note": "Iowa + Illinois centroids, daily, 2000-2025; "
                "growing-season (Apr-Sep) aggregates. NOAA GHCN-daily "
                "recorded as the roadmap cross-check, not fetched.",
            },
            "drought": {
                "source": "U.S. Drought Monitor (NDMC/USDA/NOAA)",
                "endpoint": USDM_BASE + "/StateStatistics/GetDSCI",
                "provenance": dsci_prov,
                "copied_from": "day-17-drought-impact-analyzer",
                "fetch_date": "2026-11-24",
            },
            "county_d2plus_2012": {
                "source": "U.S. Drought Monitor county % area, via Day 17",
                "copied_from": "day-17-drought-impact-analyzer "
                "data/processed/county_year.csv",
                "fetch_date": "2026-11-24",
                "rows": 201,
            },
            "county_geojson": {
                "source": "US Census Bureau boundaries via plotly datasets",
                "url": GEOJSON_URL,
                "note": "Fetched at chart time, cached locally, NOT committed.",
            },
        },
        "row_counts": {
            "monthly_prices": len(monthly),
            "months_per_commodity": EXPECTED_PRICE_MONTHS,
        },
        "backtest": backtest,
    }


# --- Main -------------------------------------------------------------------


def run(mode: str) -> dict[str, Any]:
    """Run the pipeline in the given mode; return the derived tables."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    price_prov = fetch_prices(mode)
    weather_prov = ensure_weather(mode)
    dsci_prov = ensure_dsci(mode)

    monthly = clean_prices()
    annual_summary = build_annual_summary(monthly)

    weather: dict[str, pd.DataFrame] = {}
    for state in ("iowa", "illinois"):
        raw_json = json.loads(
            (RAW_DIR / f"weather_{state}.json").read_text(encoding="utf-8")
        )
        weather[state] = build_weather_features(raw_json)
    dsci: dict[str, pd.DataFrame] = {}
    for state in ("iowa", "illinois"):
        raw_dsci = pd.read_csv(RAW_DIR / f"dsci_{state}.csv")
        dsci[state] = aggregate_state_annual(raw_dsci, state)
    annual_join = build_annual_join(annual_summary, weather, dsci)
    county_2012 = load_county_2012()

    _assert_counts(monthly, annual_summary, annual_join, county_2012)

    # The analysis module writes the derived tables (plan §6: the
    # pipeline calls it). Without this, an --offline run would rewrite
    # the base tables without the derived ones (Day 17 lesson).
    try:
        from src import analysis as _analysis
    except ImportError:  # running as a script from inside src/
        import analysis as _analysis  # type: ignore[no-redef]

    derived = _analysis.build_derived(
        PROCESSED_DIR, monthly, annual_summary, annual_join
    )

    monthly.to_csv(PROCESSED_DIR / "monthly_prices.csv", index=False)
    annual_summary.to_csv(PROCESSED_DIR / "annual_summary.csv", index=False)
    annual_join.to_csv(PROCESSED_DIR / "annual_join.csv", index=False)
    county_2012.to_csv(PROCESSED_DIR / "county_shock_2012.csv", index=False)

    if mode != "offline":
        # Offline runs must not clobber the live provenance record
        # (Day 6 lesson): only a live/cache run rewrites data_source.json,
        # and it preserves an existing manual_validation section.
        existing: dict[str, Any] = {}
        target = PROCESSED_DIR / "data_source.json"
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
        provenance = _provenance(
            price_prov, weather_prov, dsci_prov, monthly, derived["backtest"]
        )
        if "manual_validation" in existing:
            provenance["manual_validation"] = existing["manual_validation"]
        target.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return derived


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true", help="fetch, then build")
    group.add_argument("--offline", action="store_true", help="replay from raw files")
    group.add_argument(
        "--use-cache", action="store_true", help="use raw files if present"
    )
    args = parser.parse_args()
    mode = "live"
    if args.offline:
        mode = "offline"
    elif args.use_cache:
        mode = "use-cache"
    derived = run(mode)
    print(f"mode: {mode}")
    print(f"backtest: {derived['backtest']}")
    print("processed files written to", PROCESSED_DIR)


if __name__ == "__main__":
    main()
