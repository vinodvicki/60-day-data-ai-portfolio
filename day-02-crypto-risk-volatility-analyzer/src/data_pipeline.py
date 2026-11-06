"""Day 2 — Crypto Risk & Volatility Analyzer: fetch -> clean -> metrics -> save.

Source: CoinGecko public API (https://api.coingecko.com/api/v3).
Descriptive, historical risk analysis only.
Educational analysis only — not investment advice.

Fetch rules (see research_brief.md / plan.md):
- 3 calls only (one per coin), >=5 s between calls.
- Preferred endpoint: /coins/{id}/market_chart/range (from=1762387200,
  to=1793923200, i.e. 2025-11-06 -> 2026-11-06); fallback:
  /coins/{id}/market_chart?days=365. NO interval parameter.
- One retry after 60 s on HTTP 429 (honour Retry-After if present).
- Optional Demo key ONLY from the COINGECKO_DEMO_API_KEY environment
  variable, sent as x-cg-demo-api-key, and ONLY used when supplied.
  Never hard-code or commit a key.
- If fetch fails and no cache exists, deterministic synthetic GBM data
  (seed=42) is generated and clearly labelled SYNTHETIC everywhere.
  Synthetic output goes to data/raw/{coin}_market_chart_synthetic.json
  only — it never overwrites the live cache
  data/raw/{coin}_market_chart.json.
- Offline mode: `python3 src/data_pipeline.py --offline` (or
  `--use-cache`) uses only the committed data/raw/*.json cache, makes no
  network calls, never generates synthetic data, and exits non-zero if
  no cache exists.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:  # run as a module: python -m src.data_pipeline
    from src.risk_metrics import (
        daily_returns,
        drawdown_series,
        max_drawdown_info,
        return_correlations,
        rolling_volatility,
        sharpe_ratio,
        sortino_ratio,
        var_cvar_95,
    )
except ImportError:  # run as a script: python src/data_pipeline.py
    from risk_metrics import (  # type: ignore[no-redef]
        daily_returns,
        drawdown_series,
        max_drawdown_info,
        return_correlations,
        rolling_volatility,
        sharpe_ratio,
        sortino_ratio,
        var_cvar_95,
    )

COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCY = "usd"
FROM_TS = 1762387200  # 2025-11-06 00:00 UTC
TO_TS = 1793923200  # 2026-11-06 00:00 UTC
BASE_URL = "https://api.coingecko.com/api/v3"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Synthetic-fallback parameters (research_brief §6 / plan §3.5).
_SYNTH_PARAMS = {
    "bitcoin": {
        "drift": 0.0008,
        "sigma": 0.035,
        "start": 100_000.0,
        "volume": 30e9,
        "supply": 19.8e6,
    },
    "ethereum": {
        "drift": 0.0006,
        "sigma": 0.045,
        "start": 3_500.0,
        "volume": 15e9,
        "supply": 120.0e6,
    },
    "solana": {
        "drift": 0.0005,
        "sigma": 0.06,
        "start": 180.0,
        "volume": 3e9,
        "supply": 540.0e6,
    },
}
# Set by main(); "live" | "cache" | "synthetic".
DATA_SOURCE = "live"


def _headers(api_key: str | None) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key
    return headers


def fetch_coin_chart(coin: str, api_key: str | None = None) -> dict:
    """One GET to /coins/{coin}/market_chart/range (fallback: market_chart?days=365).

    Sleeps >=5s before the call. One retry after 60s on 429 (honouring
    Retry-After when present). Sends x-cg-demo-api-key only if api_key
    is given. Raises RuntimeError after the retry so the caller can
    fall back to cache / synthetic data.
    """
    time.sleep(5)
    urls = [
        (
            f"{BASE_URL}/coins/{coin}/market_chart/range"
            f"?vs_currency={VS_CURRENCY}&from={FROM_TS}&to={TO_TS}"
        ),
        f"{BASE_URL}/coins/{coin}/market_chart?vs_currency={VS_CURRENCY}&days=365",
    ]
    last_error: Exception | None = None
    for url in urls:
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=_headers(api_key), timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                break  # network error: try the fallback endpoint once
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                if attempt == 0:
                    wait = 60
                    try:
                        wait = int(resp.headers.get("Retry-After", 60))
                    except ValueError:
                        pass
                    print(f"  [{coin}] 429 rate-limited; retrying after {wait}s ...")
                    time.sleep(wait)
                    continue
                last_error = RuntimeError(f"{coin}: HTTP 429 after retry")
                break
            if resp.status_code in (401, 403):
                last_error = RuntimeError(
                    f"{coin}: HTTP {resp.status_code} — Demo API key required"
                )
                break
            last_error = RuntimeError(f"{coin}: HTTP {resp.status_code} from {url}")
            break
        # If the range endpoint failed for a non-429 reason, fall through
        # to the days=365 endpoint; if that also failed, last_error stands.
        if isinstance(last_error, RuntimeError) and "429" in str(last_error):
            break
    raise RuntimeError(str(last_error) if last_error else f"{coin}: fetch failed")


def fetch_all_coins(api_key: str | None = None) -> dict[str, dict]:
    """Calls fetch_coin_chart for each coin in COINS; returns {coin: raw_json}."""
    return {coin: fetch_coin_chart(coin, api_key=api_key) for coin in COINS}


def clean_chart(raw: dict, coin: str) -> pd.DataFrame:
    """Merge prices/market_caps/total_volumes on timestamp_ms -> daily frame.

    Returns columns [date, coin, price, market_cap, volume]; date as
    YYYY-MM-DD (UTC); duplicate timestamps dropped; sorted by date;
    asserts no NaNs in price.
    """
    prices = pd.DataFrame(raw["prices"], columns=["ts_ms", "price"])
    caps = pd.DataFrame(raw["market_caps"], columns=["ts_ms", "market_cap"])
    vols = pd.DataFrame(raw["total_volumes"], columns=["ts_ms", "volume"])
    df = prices.merge(caps, on="ts_ms").merge(vols, on="ts_ms")
    df = df.drop_duplicates(subset="ts_ms").sort_values("ts_ms")
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.strftime(
        "%Y-%m-%d"
    )
    # One row per calendar day (range endpoint is daily at this window, but
    # guard against any intraday duplicates by keeping the last of the day).
    df = df.drop_duplicates(subset="date", keep="last")
    out = df[["date", "price", "market_cap", "volume"]].copy()
    out.insert(1, "coin", coin)
    out = out.reset_index(drop=True)
    assert out["price"].notna().all(), f"{coin}: NaN price after cleaning"
    return out[["date", "coin", "price", "market_cap", "volume"]]


def compute_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Add, per coin, daily_return, drawdown and 30-day annualised volatility.

    Returns columns [date, coin, price, market_cap, volume, daily_return,
    drawdown, vol_30d_ann]. First daily_return per coin is NaN; first 29
    vol_30d_ann values per coin are NaN.
    """
    df = daily.sort_values(["coin", "date"]).copy()
    frames = []
    for coin, g in df.groupby("coin", sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        g["daily_return"] = daily_returns(g["price"])
        g["drawdown"] = drawdown_series(g["price"])
        g["vol_30d_ann"] = rolling_volatility(g["daily_return"])
        frames.append(g)
    out = pd.concat(frames, ignore_index=True)
    return out[
        [
            "date",
            "coin",
            "price",
            "market_cap",
            "volume",
            "daily_return",
            "drawdown",
            "vol_30d_ann",
        ]
    ]


def build_risk_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Per-coin summary table (plan §4 derived table), one row per coin.

    Columns: coin, total_return, max_drawdown, current_drawdown,
    peak_date, peak_price, trough_date, trough_price,
    peak_to_trough_days, recovery_days, recovered_by_end,
    longest_underwater_days, vol_30d_mean, vol_30d_median, vol_30d_max,
    vol_30d_max_date, sharpe, sortino, var_95, cvar_95.
    """
    rows = []
    for coin, g in daily.groupby("coin", sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        info = max_drawdown_info(g["price"], g["date"])
        rets = g["daily_return"].dropna()
        vol = g["vol_30d_ann"]
        var_cvar = var_cvar_95(rets)
        vol_max_idx = int(vol.idxmax()) if vol.notna().any() else None
        rows.append(
            {
                "coin": coin,
                "total_return": float(g["price"].iloc[-1] / g["price"].iloc[0] - 1),
                "max_drawdown": info["max_drawdown"],
                "current_drawdown": float(g["drawdown"].iloc[-1]),
                "peak_date": info["peak_date"],
                "peak_price": info["peak_price"],
                "trough_date": info["trough_date"],
                "trough_price": info["trough_price"],
                "peak_to_trough_days": info["peak_to_trough_days"],
                "recovery_days": info["recovery_days"],
                "recovered_by_end": info["recovered_by_end"],
                "longest_underwater_days": info["longest_underwater_days"],
                "vol_30d_mean": float(vol.mean()),
                "vol_30d_median": float(vol.median()),
                "vol_30d_max": float(vol.max()),
                "vol_30d_max_date": (
                    str(g["date"].iloc[vol_max_idx]) if vol_max_idx is not None else ""
                ),
                "sharpe": sharpe_ratio(rets),
                "sortino": sortino_ratio(rets),
                "var_95": var_cvar["var_95"],
                "cvar_95": var_cvar["cvar_95"],
            }
        )
    return pd.DataFrame(rows)


def build_correlations(daily: pd.DataFrame) -> pd.DataFrame:
    """Pairwise correlations: one row per pair, full window + latest 90d."""
    piv = daily.pivot(index="date", columns="coin", values="daily_return")
    corr = return_correlations(piv)
    full = corr["full"]
    rows = []
    coins = list(piv.columns)
    for i, a in enumerate(coins):
        for b in coins[i + 1 :]:
            rows.append(
                {
                    "pair": f"{a}-{b}",
                    "full_window": float(full.loc[a, b]),
                    "latest_90d": corr["latest_90d"][f"{a}-{b}"],
                }
            )
    return pd.DataFrame(rows)


def save_outputs(
    daily: pd.DataFrame,
    summary: pd.DataFrame,
    correlations: pd.DataFrame,
    raw: dict,
) -> None:
    """Write raw JSONs to data/raw/, CSVs + data_source.json to data/processed/.

    Raw JSON destination depends on DATA_SOURCE: when "synthetic", each
    coin is written ONLY to data/raw/{coin}_market_chart_synthetic.json
    and the live cache data/raw/{coin}_market_chart.json is never
    written, touched, or deleted. When "live" or "cache", each coin is
    written to data/raw/{coin}_market_chart.json and no
    *_synthetic.json file is written.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for coin, payload in raw.items():
        if DATA_SOURCE == "synthetic":
            dest = RAW_DIR / f"{coin}_market_chart_synthetic.json"
        else:
            dest = RAW_DIR / f"{coin}_market_chart.json"
        dest.write_text(json.dumps(payload))
    daily.to_csv(PROCESSED_DIR / "crypto_daily.csv", index=False)
    summary.to_csv(PROCESSED_DIR / "crypto_risk_summary.csv", index=False)
    correlations.to_csv(PROCESSED_DIR / "crypto_correlations.csv", index=False)
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(
            {
                "source": DATA_SOURCE,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "synthetic": DATA_SOURCE == "synthetic",
                "seed": 42 if DATA_SOURCE == "synthetic" else None,
                "window": {"from": "2025-11-06", "to": "2026-11-06"},
                "coins": COINS,
            },
            indent=2,
        )
    )


def generate_synthetic(seed: int = 42) -> dict[str, dict]:
    """Deterministic GBM fallback (research_brief §6 / plan §3.5).

    365 daily points from 2025-11-06; BTC drift 0.0008 σ 0.035,
    ETH drift 0.0006 σ 0.045, SOL drift 0.0005 σ 0.06; starting prices
    BTC $100,000 / ETH $3,500 / SOL $180; volumes log-normal noise
    around each coin's typical daily volume. Returns data in the same
    shape as the API response so clean_chart() works unchanged.
    Only called when fetch fails AND no cache exists.
    """
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2025-11-06", tz="UTC")
    out: dict[str, dict] = {}
    for coin in COINS:
        p = _SYNTH_PARAMS[coin]
        n = 365
        rets = rng.normal(p["drift"], p["sigma"], size=n)
        rets[0] = 0.0
        prices = p["start"] * np.exp(np.cumsum(rets))
        vols = p["volume"] * np.exp(rng.normal(0, 0.4, size=n))
        caps = prices * p["supply"]
        ts_ms = [(start + pd.Timedelta(days=i)).value // 10**6 for i in range(n)]
        out[coin] = {
            "prices": [[int(t), float(v)] for t, v in zip(ts_ms, prices)],
            "market_caps": [[int(t), float(v)] for t, v in zip(ts_ms, caps)],
            "total_volumes": [[int(t), float(v)] for t, v in zip(ts_ms, vols)],
        }
    return out


def _load_cache() -> dict[str, dict] | None:
    # Loads only the exact live-cache filenames
    # {coin}_market_chart.json; a *_synthetic.json file alone never
    # satisfies the cache (it is ignored here by construction).
    cached = {}
    for coin in COINS:
        path = RAW_DIR / f"{coin}_market_chart.json"
        if not path.exists():
            return None
        cached[coin] = json.loads(path.read_text())
    return cached


def main() -> None:
    """Orchestrate: fetch (or cache, or synthetic) -> clean -> metrics -> save.

    Reads an optional Demo key ONLY from the COINGECKO_DEMO_API_KEY
    environment variable — never from a file in the repo.

    --offline / --use-cache: skip the network entirely; use only the
    committed data/raw/*.json cache (never generate synthetic data).
    Exits non-zero if no cache exists.
    """
    global DATA_SOURCE
    parser = argparse.ArgumentParser(
        description="Crypto Risk & Volatility pipeline: fetch, clean, metrics."
    )
    parser.add_argument(
        "--offline",
        "--use-cache",
        dest="offline",
        action="store_true",
        help="Use cached data/raw/*.json only; make no network calls "
        "and never generate synthetic data",
    )
    args = parser.parse_args()
    api_key = os.environ.get("COINGECKO_DEMO_API_KEY")
    raw: dict[str, dict] | None = None
    if args.offline:
        cached = _load_cache()
        if cached is None:
            print("Offline mode: no cached data/raw/*.json found; cannot fetch.")
            raise SystemExit(1)
        raw = cached
        DATA_SOURCE = "cache"
        print("Offline mode: using cached data/raw/ JSON (no network).")
    else:
        try:
            print(
                "Fetching CoinGecko market_chart/range (no key first unless "
                "COINGECKO_DEMO_API_KEY is set) ..."
            )
            raw = fetch_all_coins(api_key=api_key)
            DATA_SOURCE = "live"
            print("Live CoinGecko fetch succeeded.")
        # Any fetch failure falls back to cache, then synthetic (plan §3.5).
        except Exception as exc:  # noqa: BLE001
            print(f"Live fetch failed: {exc}")
            cached = _load_cache()
            if cached is not None:
                raw = cached
                DATA_SOURCE = "cache"
                print("Using cached data/raw/ JSON.")
            else:
                raw = generate_synthetic(seed=42)
                DATA_SOURCE = "synthetic"
                print(
                    "SYNTHETIC DATA — API unavailable; using deterministic "
                    "GBM fallback (seed=42). Do not present as real data."
                )

    daily_raw = pd.concat([clean_chart(raw[c], c) for c in COINS], ignore_index=True)
    daily = compute_daily(daily_raw)
    summary = build_risk_summary(daily)
    correlations = build_correlations(daily)
    save_outputs(daily, summary, correlations, raw)

    print(f"\nData source: {DATA_SOURCE.upper()}")
    for coin in COINS:
        g = daily[daily["coin"] == coin]
        row = summary[summary["coin"] == coin].iloc[0]
        print(
            f"  {coin}: {len(g)} rows, {g['date'].min()} to {g['date'].max()}, "
            f"total return {row['total_return']:+.1%}, "
            f"max drawdown {row['max_drawdown']:.1%}"
        )
    print(correlations.to_string(index=False))
    if DATA_SOURCE == "synthetic":
        print(
            "Wrote data/raw/*_market_chart_synthetic.json "
            "(synthetic — live cache untouched), "
            "data/processed/crypto_daily.csv, "
            "data/processed/crypto_risk_summary.csv, "
            "data/processed/crypto_correlations.csv"
        )
    else:
        print(
            "Wrote data/raw/*.json, data/processed/crypto_daily.csv, "
            "data/processed/crypto_risk_summary.csv, "
            "data/processed/crypto_correlations.csv"
        )


if __name__ == "__main__":
    main()
