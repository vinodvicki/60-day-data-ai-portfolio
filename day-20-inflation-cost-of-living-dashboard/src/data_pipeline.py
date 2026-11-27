"""Day 20 Inflation & Cost of Living Dashboard: data pipeline.

Fetches the 10 FRED series (research_brief.md §1a, no key) and builds the
frozen processed set (plan.md §4): 8 CSVs + data_source.json.

Modes:
- --live: download each series from fredgraph.csv, save to data/raw/,
  then build.
- --offline: build from the committed data/raw/ cache, no network.
- --use-cache: use data/raw/ when present, otherwise fetch.

Synthetic fallback (brief §4, seed 42): only ever written to
data/raw/<SERIES>_synthetic.csv and only when --synthetic is passed
explicitly; it never overwrites a real raw file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:
    from src.analysis import (
        basket_cost,
        cumulative_since,
        indexed,
        mom,
        purchasing_power,
        real_earnings,
        summarise_series,
        yoy,
    )
except ImportError:  # pragma: no cover - fallback for direct script runs
    from analysis import (  # type: ignore[no-redef]
        basket_cost,
        cumulative_since,
        indexed,
        mom,
        purchasing_power,
        real_earnings,
        summarise_series,
        yoy,
    )

BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Series ID -> (short name, human label). Verified 2026-11-27, brief §1a.
SERIES: dict[str, tuple[str, str]] = {
    "CPIAUCSL": ("headline_cpi", "CPI-U All Items, SA"),
    "CPILFESL": ("core_cpi", "CPI-U Less Food & Energy, SA"),
    "CPIFABSL": ("food_at_home", "CPI-U Food at Home, SA"),
    "CPIENGSL": ("energy", "CPI-U Energy, SA"),
    "CPIHOSSL": ("housing", "CPI-U Housing, SA"),
    "CPITRNSL": ("transportation", "CPI-U Transportation, SA"),
    "CPIAPPSL": ("apparel", "CPI-U Apparel, SA"),
    "CPIMEDSL": ("medical_care", "CPI-U Medical Care, SA"),
    "CPIEDUSL": ("education", "CPI-U Education, SA"),
    "CES0500000003": ("hourly_earnings", "Avg Hourly Earnings, Total Private, SA"),
}

CATEGORIES = [
    "food_at_home",
    "energy",
    "housing",
    "transportation",
    "apparel",
    "medical_care",
    "education",
]

JOINT_START = pd.Timestamp("2006-03-01")
BASE_MONTH = pd.Timestamp("2006-03-01")
BASKET_BASE_COST = 100.0

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def fetch_series(series_id: str, session: requests.Session) -> pd.DataFrame:
    """Download one FRED series as a (date, value) frame. One retry on 5xx."""
    url = f"{BASE_URL}?id={series_id}"
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code == 200:
                break
            last_error = RuntimeError(f"HTTP {resp.status_code} for {series_id}")
        except requests.RequestException as exc:  # pragma: no cover - network
            last_error = exc
        if attempt == 0:
            time.sleep(30)
    else:
        raise RuntimeError(f"Failed to fetch {series_id}: {last_error}")
    from io import StringIO

    frame = pd.read_csv(StringIO(resp.text))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    # Keep rows with a missing value (e.g. Oct 2025, not published by BLS):
    # dropping them would shift every later YoY by one month.
    return frame.reset_index(drop=True)


def load_raw(series_id: str) -> pd.DataFrame:
    """Load a committed raw CSV for one series."""
    path = RAW_DIR / f"{series_id}.csv"
    frame = pd.read_csv(path)
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    # Keep rows with a missing value (e.g. Oct 2025, not published by BLS):
    # dropping them would shift every later YoY by one month.
    return frame.reset_index(drop=True)


def generate_synthetic(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Labelled synthetic fallback (brief §4). Never overwrites real data."""
    rng = np.random.default_rng(seed)
    months = pd.date_range("2006-03-01", "2026-10-01", freq="MS")
    n = len(months)
    trend = 2.5 / 100.0 / 12.0
    noise = rng.normal(0.0, 0.003, n)
    headline = 200.0 * 1.0
    values = [headline]
    for i in range(1, n):
        values.append(values[-1] * (1.0 + trend + float(noise[i])))
    headline_s = pd.Series(values, index=months)
    drift = {
        "CPIFABSL": 0.001,
        "CPIENGSL": 0.0,
        "CPIHOSSL": 0.003,
        "CPITRNSL": 0.0,
        "CPIAPPSL": -0.005,
        "CPIMEDSL": 0.008,
        "CPIEDUSL": -0.002,
    }
    out: dict[str, pd.DataFrame] = {}
    for series_id in SERIES:
        if series_id == "CPIAUCSL":
            s = headline_s
        elif series_id == "CPILFESL":
            s = headline_s * 1.01
        elif series_id == "CES0500000003":
            earn = [20.0]
            for i in range(1, n):
                earn.append(
                    earn[-1] * (1.0 + 0.03 / 12.0 + float(rng.normal(0, 0.002)))
                )
            s = pd.Series(earn, index=months)
        else:
            vol = 0.02 if series_id == "CPIENGSL" else 0.003
            vals = [float(headline_s.iloc[0])]
            for i in range(1, n):
                step = trend + drift[series_id] / 12.0 + float(rng.normal(0, vol))
                vals.append(vals[-1] * (1.0 + step))
            s = pd.Series(vals, index=months)
        frame = pd.DataFrame({"date": s.index, "value": s.to_numpy()})
        out[series_id] = frame
    return out


def build_processed(
    series_frames: dict[str, pd.DataFrame], synthetic: bool
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Build the frozen 8 processed tables from the raw series frames."""
    panel = pd.DataFrame({"date": series_frames["CPIAUCSL"]["date"]})
    panel = panel.set_index("date")
    for series_id, (short, _label) in SERIES.items():
        frame = series_frames[series_id].set_index("date")
        panel[short] = frame["value"]
    panel = panel.sort_index()
    # Reindex to a complete monthly grid so shift(12) YoY alignment is
    # exact even where a month is missing (Oct 2025 was not published).
    full_index = pd.date_range(panel.index.min(), panel.index.max(), freq="MS")
    panel = panel.reindex(full_index)
    panel.index.name = "date"

    # 1. monthly_panel.csv — joint window 2006-03 -> 2026-10, all 10 series.
    joint = panel.loc[JOINT_START:].copy()
    joint = joint.reset_index()

    # 2. cpi_history.csv — headline CPI 1947 -> 2026 (long-run context).
    history = (
        panel[["headline_cpi"]].reset_index().rename(columns={"headline_cpi": "cpi"})
    )

    # 3. yoy_inflation.csv — YoY + MoM for headline, core and categories.
    yoy_frame = pd.DataFrame({"date": joint["date"]})
    yoy_frame["headline_yoy_pct"] = yoy(
        joint.set_index("date")["headline_cpi"]
    ).to_numpy()
    yoy_frame["core_yoy_pct"] = yoy(joint.set_index("date")["core_cpi"]).to_numpy()
    yoy_frame["headline_mom_pct"] = mom(
        joint.set_index("date")["headline_cpi"]
    ).to_numpy()
    for short in CATEGORIES:
        yoy_frame[f"{short}_yoy_pct"] = yoy(joint.set_index("date")[short]).to_numpy()

    # 4. category_cumulative.csv — cumulative % since 2006-03 + divergence.
    idx = joint.set_index("date")
    cum = pd.DataFrame({"date": joint["date"]})
    cum["headline_cum_pct"] = cumulative_since(
        idx["headline_cpi"], BASE_MONTH
    ).to_numpy()
    for short in CATEGORIES:
        cum[f"{short}_cum_pct"] = cumulative_since(idx[short], BASE_MONTH).to_numpy()
        cum[f"{short}_divergence_pp"] = (
            cum[f"{short}_cum_pct"] - cum["headline_cum_pct"]
        )

    # 5. real_earnings.csv — nominal, real (1982-84 $), indexed, real YoY.
    real = pd.DataFrame({"date": joint["date"]})
    real["nominal_usd_per_hour"] = joint["hourly_earnings"]
    real["real_usd_per_hour"] = real_earnings(
        idx["hourly_earnings"], idx["headline_cpi"]
    ).to_numpy()
    real["nominal_indexed"] = indexed(idx["hourly_earnings"], BASE_MONTH).to_numpy()
    real["real_indexed"] = indexed(
        real_earnings(idx["hourly_earnings"], idx["headline_cpi"]), BASE_MONTH
    ).to_numpy()
    real["real_yoy_pct"] = yoy(
        real_earnings(idx["hourly_earnings"], idx["headline_cpi"])
    ).to_numpy()

    # 6. basket_cost.csv — fixed $100 (2006-03) basket + purchasing power.
    basket = pd.DataFrame({"date": joint["date"]})
    basket["basket_cost_usd"] = basket_cost(
        idx["headline_cpi"], BASE_MONTH, BASKET_BASE_COST
    ).to_numpy()
    basket["purchasing_power_usd"] = purchasing_power(idx["headline_cpi"]).to_numpy()

    # 7. summary_stats.csv — one row per series over the joint window.
    rows = []
    for series_id, (short, label) in SERIES.items():
        rows.append(summarise_series(idx[short], BASE_MONTH, label))
    summary = pd.DataFrame(rows)

    # 8. monthly_panel.csv is `joint`; data_source.json is metadata.
    data_source: dict[str, object] = {
        "source": "FRED (Federal Reserve Bank of St. Louis), fredgraph.csv",
        "provider": "U.S. Bureau of Labor Statistics via FRED",
        "series": {sid: label for sid, (_s, label) in SERIES.items()},
        "window_start": "2006-03-01",
        "window_end": str(joint["date"].iloc[-1].date()),
        "n_months": len(joint),
        "synthetic": synthetic,
        "seed": 42 if synthetic else None,
        "accessed": str(date.today()),
        "attribution": "Source: U.S. Bureau of Labor Statistics via FRED "
        "(Federal Reserve Bank of St. Louis).",
        "assumptions": [
            "All CPI series seasonally adjusted, index base 1982-84=100.",
            "Joint window 2006-03 to 2026-10 set by earnings availability.",
            "Latest data October 2026 (FRED lag ~1 month).",
            "Real earnings deflated by headline CPI; no tax/benefits/hours adjustment.",
            "$100 basket is a fixed-basket illustration (no substitution).",
            "No forecast is made; descriptive only.",
        ],
    }
    return {
        "monthly_panel": joint,
        "cpi_history": history,
        "yoy_inflation": yoy_frame,
        "category_cumulative": cum,
        "real_earnings": real,
        "basket_cost": basket,
        "summary_stats": summary,
        "data_source": data_source,
    }


def run(mode: str) -> dict[str, int | str]:
    """Run the pipeline in one of live/offline/use-cache/synthetic modes."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    synthetic = mode == "synthetic"
    frames: dict[str, pd.DataFrame] = {}
    if synthetic:
        frames = generate_synthetic()
        for series_id, frame in frames.items():
            frame.to_csv(RAW_DIR / f"{series_id}_synthetic.csv", index=False)
    elif mode == "offline":
        for series_id in SERIES:
            frames[series_id] = load_raw(series_id)
    else:
        session = requests.Session()
        for series_id in SERIES:
            path = RAW_DIR / f"{series_id}.csv"
            if mode == "use-cache" and path.exists():
                frames[series_id] = load_raw(series_id)
            else:
                frame = fetch_series(series_id, session)
                frame.to_csv(path, index=False)
                frames[series_id] = frame
            time.sleep(1)
    tables = build_processed(frames, synthetic)
    counts: dict[str, int | str] = {}
    for name in [
        "monthly_panel",
        "cpi_history",
        "yoy_inflation",
        "category_cumulative",
        "real_earnings",
        "basket_cost",
        "summary_stats",
    ]:
        table = tables[name]
        assert isinstance(table, pd.DataFrame)
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
        counts[name] = len(table)
    meta = tables["data_source"]
    assert isinstance(meta, dict)
    with open(PROCESSED_DIR / "data_source.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    counts["synthetic"] = str(synthetic)
    counts["window_end"] = str(meta["window_end"])
    return counts


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Day 20 data pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true")
    group.add_argument("--offline", action="store_true")
    group.add_argument("--use-cache", action="store_true")
    group.add_argument("--synthetic", action="store_true")
    args = parser.parse_args(argv)
    mode = (
        "live"
        if args.live
        else (
            "offline"
            if args.offline
            else "use-cache" if args.use_cache else "synthetic"
        )
    )
    counts = run(mode)
    print(f"mode={mode} " + " ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
