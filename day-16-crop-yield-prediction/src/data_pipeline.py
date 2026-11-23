"""Day 16 Crop Yield Prediction: data pipeline.

Fetches USA maize yields (FAO via Our World in Data) and Corn Belt weather
(Open-Meteo ERA5 archive, Iowa + Illinois centroids), aggregates daily
weather into growing-season features, and joins them into one annual
dataset. No model code lives here.

Modes:
    --live       fetch from the sources, then build (default)
    --offline    replay from committed raw files, no network
    --use-cache  use raw files if present, else fetch

Raw files are committed (small: < 1 MB each). ``data_source.json`` records
provenance; a re-run overwrites it, so the tester's manual-validation
section must be re-added after any --live re-run.
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

YIELD_URL = "https://ourworldindata.org/grapher/maize-yields.csv?country=USA"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

STATES = {
    "iowa": {"latitude": 41.8780, "longitude": -93.0977},
    "illinois": {"latitude": 40.6331, "longitude": -89.3985},
}

START_YEAR = 2000
END_YEAR = 2025
TRAIN_END = 2019
HELDOUT_START = 2020

# 1 tonne of corn = 39.368 bushels (56 lb/bu); 1 ha = 2.47105 acres.
BU_PER_ACRE_PER_T_PER_HA = 39.368 / 2.47105  # 15.932...

FEATURES = [
    "year",
    "gs_temp_mean",
    "gs_precip_total",
    "jul_temp_mean",
    "jul_precip_total",
    "jun_precip_total",
    "heat_days_gs",
]

GROWING_MONTHS = (4, 5, 6, 7, 8, 9)  # April–September inclusive
HEAT_THRESHOLD_C = 30.0


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


def fetch_yields() -> str:
    """Download the OWID maize-yields CSV; return its text."""
    return _get_with_retry(YIELD_URL).text


def fetch_weather(state: str) -> dict[str, Any]:
    """Download one state's daily weather JSON from Open-Meteo."""
    params: dict[str, Any] = {
        **STATES[state],
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,temperature_2m_max,precipitation_sum",
        "timezone": "America/Chicago",
    }
    return cast(dict[str, Any], _get_with_retry(WEATHER_URL, params=params).json())


# --- Cleaning / feature building -------------------------------------------


def clean_yields(csv_text: str) -> pd.DataFrame:
    """Filter the OWID CSV to USA 2000–2025; assert 26 complete rows."""
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


def build_features(daily: dict[str, Any]) -> pd.DataFrame:
    """Aggregate one state's daily weather into annual growing-season features.

    Expects the Open-Meteo ``daily`` dict with ``time``,
    ``temperature_2m_mean``, ``temperature_2m_max`` and
    ``precipitation_sum``. Returns one row per year (2000–2025).
    """
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "tmean": daily["temperature_2m_mean"],
            "tmax": daily["temperature_2m_max"],
            "precip": daily["precipitation_sum"],
        }
    )
    if frame[["tmean", "tmax", "precip"]].isna().any().any():
        raise ValueError("missing daily weather values")
    if (frame["precip"] < 0).any():
        raise ValueError("negative precipitation values")
    # Full 2000–2025 coverage is validated by the caller (build_dataset
    # asserts 26 joined rows); here only contiguity within 2000–2025.
    frame = frame.sort_values("date").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise ValueError("duplicate weather dates")
    gaps = frame["date"].diff().dropna()
    if (gaps != pd.Timedelta(days=1)).any():
        raise ValueError("weather dates are not contiguous daily")
    if frame["date"].min().year < START_YEAR or frame["date"].max().year > END_YEAR:
        raise ValueError("weather dates outside 2000–2025")

    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    gs = frame[frame["month"].isin(GROWING_MONTHS)]
    july = frame[frame["month"] == 7]
    june = frame[frame["month"] == 6]

    rows = []
    for year, group in gs.groupby("year"):
        july_group = july[july["year"] == year]
        june_group = june[june["year"] == year]
        rows.append(
            {
                "year": int(year),
                "gs_temp_mean": float(group["tmean"].mean()),
                "gs_precip_total": float(group["precip"].sum()),
                "jul_temp_mean": float(july_group["tmean"].mean()),
                "jul_precip_total": float(july_group["precip"].sum()),
                "jun_precip_total": float(june_group["precip"].sum()),
                "heat_days_gs": int((group["tmax"] > HEAT_THRESHOLD_C).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def build_dataset(
    yields: pd.DataFrame, weather_by_state: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Join yields with the two-state average weather features."""
    averaged = (
        pd.concat(weather_by_state.values()).groupby("year").mean(numeric_only=True)
    )
    averaged = averaged.reset_index()
    joined = yields.merge(averaged, on="year", how="inner")
    if len(joined) != END_YEAR - START_YEAR + 1:
        raise ValueError(f"expected 26 joined rows, got {len(joined)}")
    joined["yield_bu_per_acre"] = joined["yield_t_per_ha"] * BU_PER_ACRE_PER_T_PER_HA
    joined["split"] = joined["year"].apply(
        lambda y: "train" if y <= TRAIN_END else "heldout"
    )
    cols = ["year", "yield_t_per_ha", "yield_bu_per_acre", *FEATURES[1:], "split"]
    return joined[cols]


# --- Orchestration ----------------------------------------------------------


def load_raw() -> tuple[str, dict[str, dict[str, Any]]]:
    """Read the committed raw files (offline mode)."""
    csv_text = (RAW_DIR / "maize_yields_owid.csv").read_text(encoding="utf-8")
    weather = {
        state: json.loads(
            (RAW_DIR / f"weather_{state}.json").read_text(encoding="utf-8")
        )
        for state in STATES
    }
    return csv_text, weather


def run(mode: str) -> pd.DataFrame:
    """Fetch (or replay) raw data, build the dataset, write processed files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "offline":
        csv_text, weather_raw = load_raw()
        fetched_from = "committed raw files (offline)"
        fetched_live = False
    elif mode == "use-cache":
        if (RAW_DIR / "maize_yields_owid.csv").exists() and all(
            (RAW_DIR / f"weather_{s}.json").exists() for s in STATES
        ):
            csv_text, weather_raw = load_raw()
            fetched_from = "committed raw files (cache)"
            fetched_live = False
        else:
            csv_text, weather_raw = _fetch_all()
            fetched_from = "live fetch"
            fetched_live = True
    else:  # live
        csv_text, weather_raw = _fetch_all()
        fetched_from = "live fetch"
        fetched_live = True

    yields = clean_yields(csv_text)
    features = {
        state: build_features(raw["daily"]) for state, raw in weather_raw.items()
    }
    dataset = build_dataset(yields, features)

    dataset.to_csv(PROCESSED_DIR / "yield_weather.csv", index=False)
    if not fetched_live:
        # An offline/cache replay must not clobber the live provenance
        # record (fetch date, source, and the tester's manual_validation
        # section in data_source.json).
        return dataset
    provenance = {
        "project": "Day 16 — Crop Yield Prediction",
        "fetch_date": date.today().isoformat(),
        "fetched_from": fetched_from,
        "synthetic": False,
        "sources": {
            "yields": {
                "provider": "FAO via Our World in Data",
                "url": YIELD_URL,
                "licence": "CC BY 4.0",
                "unit": "tonnes per hectare",
                "rows_usa_2000_2025": len(yields),
            },
            "weather": {
                "provider": "Open-Meteo ERA5 archive",
                "url": WEATHER_URL,
                "licence": "CC BY 4.0",
                "states": {
                    state: {
                        "latitude": cfg["latitude"],
                        "longitude": cfg["longitude"],
                        "days": len(raw["daily"]["time"]),
                    }
                    for state, cfg, raw in zip(
                        STATES, STATES.values(), weather_raw.values()
                    )
                },
            },
        },
        "unit_conversion": {
            "t_per_ha_to_bu_per_acre": BU_PER_ACRE_PER_T_PER_HA,
            "note": "1 tonne corn = 39.368 bu; 1 ha = 2.47105 acres",
        },
        "split": {
            "train_years": f"{START_YEAR}–{TRAIN_END}",
            "heldout_years": f"{HELDOUT_START}–{END_YEAR}",
        },
        "row_counts": {
            "yield_rows": len(yields),
            "joined_rows": len(dataset),
            "train_rows": int((dataset["split"] == "train").sum()),
            "heldout_rows": int((dataset["split"] == "heldout").sum()),
        },
        "note": (
            "USDA Quick Stats (roadmap suggestion) needs an API key "
            "(HTTP 401 without one), so FAO/OWID national yields are used; "
            "weather is a 2-state Corn Belt proxy (Iowa + Illinois average), "
            "not a national average. See research_brief.md."
        ),
    }
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    return dataset


def _fetch_all() -> tuple[str, dict[str, dict[str, Any]]]:
    """Fetch all three raw sources live and commit the raw files."""
    csv_text = fetch_yields()
    (RAW_DIR / "maize_yields_owid.csv").write_text(csv_text, encoding="utf-8")
    weather_raw = {}
    for state in STATES:
        raw = fetch_weather(state)
        weather_raw[state] = raw
        (RAW_DIR / f"weather_{state}.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
    return csv_text, weather_raw


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
    dataset = run(mode)
    print(
        f"mode={mode} rows={len(dataset)} train={(dataset['split'] == 'train').sum()} "
        f"heldout={(dataset['split'] == 'heldout').sum()}"
    )


if __name__ == "__main__":
    main()
