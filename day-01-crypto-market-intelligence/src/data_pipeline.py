"""Day 1 — Crypto Market Intelligence: fetch -> clean -> metrics -> save.

Source: CoinGecko public API (https://api.coingecko.com/api/v3).
Descriptive analytics only. Educational analysis only — not investment advice.

Fetch rules (see research_brief.md / plan.md):
- 3 calls only (one per coin), >=5 s between calls.
- Preferred endpoint: /coins/{id}/market_chart/range (from=1762300800,
  to=1793836800); fallback: /coins/{id}/market_chart?days=365.
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

COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCY = "usd"
FROM_TS = 1762300800  # 2025-11-05 00:00 UTC
TO_TS = 1793836800  # 2026-11-05 00:00 UTC
BASE_URL = "https://api.coingecko.com/api/v3"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Synthetic-fallback parameters (research_brief §6 / plan §4.4).
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


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add, per coin, on the daily frame:

    - daily_return = price_t / price_{t-1} - 1
    - return_7d = price_t / price_{t-7} - 1
    - vol_30d_annualised = std(daily_return, 30d) * sqrt(365)  (365, NOT 252)
    - drawdown = price_t / running_max(price) - 1
    - relative_volume = volume_t / mean(volume, 30d)
    - turnover = volume / market_cap
    - corr_btc_eth_90d = 90-day rolling Pearson correlation of BTC vs ETH
      daily returns (same value on BTC and ETH rows for that date; NaN for SOL).

    Returns the metrics frame with columns
    [date, coin, daily_return, return_7d, vol_30d_annualised, drawdown,
     relative_volume, turnover, corr_btc_eth_90d].
    """
    df = df.sort_values(["coin", "date"]).copy()
    df["daily_return"] = df.groupby("coin")["price"].pct_change()
    df["return_7d"] = df.groupby("coin")["price"].pct_change(7)
    df["vol_30d_annualised"] = df.groupby("coin")["daily_return"].transform(
        lambda s: s.rolling(30).std(ddof=1) * np.sqrt(365)
    )
    df["running_max"] = df.groupby("coin")["price"].cummax()
    df["drawdown"] = df["price"] / df["running_max"] - 1
    df["relative_volume"] = df.groupby("coin")["volume"].transform(
        lambda s: s / s.rolling(30).mean()
    )
    df["turnover"] = df["volume"] / df["market_cap"]

    # BTC-ETH correlation of daily returns: full window + 90d rolling.
    piv = df.pivot(index="date", columns="coin", values="daily_return")
    corr_90d = None
    if "bitcoin" in piv.columns and "ethereum" in piv.columns:
        corr_90d = piv["bitcoin"].rolling(90).corr(piv["ethereum"])
    df["corr_btc_eth_90d"] = np.nan
    if corr_90d is not None:
        mapping = corr_90d.to_dict()
        mask = df["coin"].isin(["bitcoin", "ethereum"])
        df.loc[mask, "corr_btc_eth_90d"] = df.loc[mask, "date"].map(mapping)
    df = df.drop(columns=["running_max"])
    cols = [
        "date",
        "coin",
        "daily_return",
        "return_7d",
        "vol_30d_annualised",
        "drawdown",
        "relative_volume",
        "turnover",
        "corr_btc_eth_90d",
    ]
    return df[cols]


def btc_eth_correlation(metrics: pd.DataFrame) -> dict:
    """Full-window Pearson correlation of BTC vs ETH daily returns."""
    piv = metrics.pivot(index="date", columns="coin", values="daily_return")
    if "bitcoin" not in piv.columns or "ethereum" not in piv.columns:
        return {"full": float("nan"), "latest_90d": float("nan")}
    full = float(piv["bitcoin"].corr(piv["ethereum"]))
    rolling = piv["bitcoin"].rolling(90).corr(piv["ethereum"])
    return {"full": full, "latest_90d": float(rolling.iloc[-1])}


def max_drawdown_info(df: pd.DataFrame) -> dict[str, dict]:
    """Per coin: max drawdown, peak/trough dates and prices, recovery duration.

    Duration = days from peak to trough (peak-to-trough); also reports
    days from peak to first recovery to a new high, if it occurred.
    """
    info: dict[str, dict] = {}
    for coin, g in df.groupby("coin"):
        g = g.sort_values("date").reset_index(drop=True)
        running_max = g["price"].cummax()
        dd = g["price"] / running_max - 1
        trough_idx = int(dd.idxmin())
        peak_price = float(running_max.iloc[trough_idx])
        peak_idx = int(g["price"].iloc[: trough_idx + 1].idxmax())
        trough_price = float(g["price"].iloc[trough_idx])
        # First date after the trough when price again reaches the peak price.
        after = g.iloc[trough_idx + 1 :]
        recovered = after[after["price"] >= peak_price]
        recovery_days = (
            int(
                (
                    pd.to_datetime(recovered["date"].iloc[0])
                    - pd.to_datetime(g["date"].iloc[peak_idx])
                ).days
            )
            if len(recovered)
            else None
        )
        info[coin] = {
            "max_drawdown": float(dd.iloc[trough_idx]),
            "peak_date": str(g["date"].iloc[peak_idx]),
            "peak_price": peak_price,
            "trough_date": str(g["date"].iloc[trough_idx]),
            "trough_price": trough_price,
            "peak_to_trough_days": int(
                (
                    pd.to_datetime(g["date"].iloc[trough_idx])
                    - pd.to_datetime(g["date"].iloc[peak_idx])
                ).days
            ),
            "peak_to_recovery_days": recovery_days,
        }
    return info


def save_outputs(daily: pd.DataFrame, metrics: pd.DataFrame, raw: dict) -> None:
    """Write raw JSONs to data/raw/, CSVs to data/processed/.

    Raw JSON destination depends on DATA_SOURCE: when "synthetic", each
    coin is written ONLY to data/raw/{coin}_market_chart_synthetic.json
    and the live cache data/raw/{coin}_market_chart.json is never
    written, touched, or deleted. When "live" or "cache", each coin is
    written to data/raw/{coin}_market_chart.json and no
    *_synthetic.json file is written.

    Also writes data/processed/data_source.json recording whether the
    data is live CoinGecko data, cached data, or synthetic (read by the
    Streamlit app and the charts so SYNTHETIC is labelled everywhere).
    The JSON always carries a "seed" key: 42 when synthetic, else None.
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
    metrics.to_csv(PROCESSED_DIR / "crypto_metrics.csv", index=False)
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(
            {
                "source": DATA_SOURCE,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "synthetic": DATA_SOURCE == "synthetic",
                "seed": 42 if DATA_SOURCE == "synthetic" else None,
            },
            indent=2,
        )
    )


def generate_synthetic(seed: int = 42) -> dict[str, dict]:
    """Deterministic GBM fallback (research_brief §6 / plan §4.4).

    365 daily points from 2025-11-05; BTC drift 0.0008 σ 0.035,
    ETH drift 0.0006 σ 0.045, SOL drift 0.0005 σ 0.06; starting prices
    BTC $100,000 / ETH $3,500 / SOL $180; volumes log-normal noise
    around each coin's typical daily volume. Returns data in the same
    shape as the API response so clean_chart() works unchanged.
    Only called when fetch fails AND no cache exists.
    """
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2025-11-05", tz="UTC")
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
        description="Crypto Market Intelligence pipeline: fetch, clean, metrics."
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
    api_key = os.environ.get("COINGECKO_DEMO_API_KEY") or None
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
        # Any fetch failure falls back to cache, then synthetic (plan §4.4).
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

    daily = pd.concat([clean_chart(raw[c], c) for c in COINS], ignore_index=True)
    metrics = compute_metrics(daily)
    save_outputs(daily, metrics, raw)

    dd_info = max_drawdown_info(daily)
    corr = btc_eth_correlation(metrics)
    print(f"\nData source: {DATA_SOURCE.upper()}")
    for coin in COINS:
        g = daily[daily["coin"] == coin]
        print(
            f"  {coin}: {len(g)} rows, {g['date'].min()} to {g['date'].max()}, "
            f"total return {(g['price'].iloc[-1] / g['price'].iloc[0] - 1):+.1%}, "
            f"max drawdown {dd_info[coin]['max_drawdown']:.1%}"
        )
    print(
        f"  BTC-ETH daily-return correlation (full window): {corr['full']:.3f} "
        f"(latest 90d: {corr['latest_90d']:.3f})"
    )
    if DATA_SOURCE == "synthetic":
        print(
            "Wrote data/raw/*_market_chart_synthetic.json "
            "(synthetic — live cache untouched), "
            "data/processed/crypto_daily.csv, "
            "data/processed/crypto_metrics.csv"
        )
    else:
        print(
            "Wrote data/raw/*.json, data/processed/crypto_daily.csv, "
            "data/processed/crypto_metrics.csv"
        )


if __name__ == "__main__":
    main()
