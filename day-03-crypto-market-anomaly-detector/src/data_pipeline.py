"""Day 3 — Crypto Market Anomaly Detector: fetch -> clean -> features
-> rules + Isolation Forest -> injection + evaluation -> save.

Source: CoinGecko public API (https://api.coingecko.com/api/v3).
Descriptive, historical anomaly analysis only. Flagged days are
statistical outliers in price and volume — never presented as proven
manipulation. Educational analysis only — not investment advice.

Fetch rules (see research_brief.md / plan.md):
- 3 calls only (one per coin), >=5 s between calls.
- Preferred endpoint: /coins/{id}/market_chart/range (from=1762473600,
  to=1794009600, i.e. 2025-11-07 -> 2026-11-07); fallback:
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
    from src.anomaly import (
        build_timeline,
        compute_features,
        evaluate,
        inject_anomalies,
        run_detection,
    )
except ImportError:  # run as a script: python src/data_pipeline.py
    from anomaly import (  # type: ignore[no-redef]
        build_timeline,
        compute_features,
        evaluate,
        inject_anomalies,
        run_detection,
    )

COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCY = "usd"
FROM_TS = 1762473600  # 2025-11-07 00:00 UTC
TO_TS = 1794009600  # 2026-11-07 00:00 UTC
BASE_URL = "https://api.coingecko.com/api/v3"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Synthetic-fallback parameters (research_brief §5 / plan §3.5).
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
    """Add the §4.1 features, per coin, to the cleaned daily frame.

    Returns the featured frame (see anomaly.compute_features): daily
    return, volume ratio, trailing z-scores, 30-day annualised
    volatility, drawdown and volatility regime.
    """
    return compute_features(daily)


def run_anomaly_analysis(daily: pd.DataFrame) -> dict:
    """Run the full anomaly analysis on the featured daily frame.

    Returns a dict with the real-data detection frame, the anomaly
    timeline, the injected featured frame, the injection labels and
    the evaluation dict (injected-anomaly precision/recall/F1 plus the
    baseline-vs-forest Jaccard overlap). Contamination is set from the
    observed baseline flag rate on the real data (plan §4.4a).
    """
    detected, contamination = run_detection(daily)
    timeline = build_timeline(detected)
    injected_raw, labels = inject_anomalies(
        daily[["date", "coin", "price", "market_cap", "volume"]],
        n=30,
        seed=42,
    )
    injected_featured = compute_features(injected_raw)
    injected_detected, _inj_contamination = run_detection(injected_featured)
    # Amended precision rule (§4.4, 2026-11-07): a flag on the injected
    # run is a true positive if it matches an injection or a flag the
    # detector also raises on the clean data (the timeline set).
    clean_flags = detected[detected["baseline_flagged"] | detected["is_anomaly"]][
        ["date", "coin"]
    ]
    evaluation = evaluate(
        injected_detected, labels, tolerance_days=1, clean_flags=clean_flags
    )
    evaluation["contamination"] = contamination
    # Baseline-vs-forest overlap on the REAL data (§4.4a) — the
    # Jaccard inside evaluate() is from the injected run, so the
    # real-data overlap is recorded separately here.
    real_base = set(
        map(
            tuple,
            detected.loc[detected["baseline_flagged"], ["date", "coin"]].values,
        )
    )
    real_forest = set(
        map(tuple, detected.loc[detected["is_anomaly"], ["date", "coin"]].values)
    )
    real_union = real_base | real_forest
    evaluation["n_baseline_real"] = len(real_base)
    evaluation["n_forest_real"] = len(real_forest)
    evaluation["n_both_real"] = len(real_base & real_forest)
    evaluation["jaccard_real"] = (
        len(real_base & real_forest) / len(real_union) if real_union else 0.0
    )
    return {
        "detected": detected,
        "timeline": timeline,
        "injected_featured": injected_featured,
        "injected_labels": labels,
        "evaluation": evaluation,
        "contamination": contamination,
    }


def save_outputs(
    daily: pd.DataFrame,
    analysis: dict,
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
    analysis["injected_featured"].to_csv(
        PROCESSED_DIR / "crypto_daily_injected.csv", index=False
    )
    analysis["timeline"].to_csv(PROCESSED_DIR / "anomaly_timeline.csv", index=False)
    analysis["injected_labels"].to_csv(
        PROCESSED_DIR / "injected_anomalies.csv", index=False
    )
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(
            {
                "source": DATA_SOURCE,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "synthetic": DATA_SOURCE == "synthetic",
                "seed": 42 if DATA_SOURCE == "synthetic" else None,
                "window": {"from": "2025-11-07", "to": "2026-11-07"},
                "coins": COINS,
            },
            indent=2,
        )
    )


def generate_synthetic(seed: int = 42) -> dict[str, dict]:
    """Deterministic GBM fallback (research_brief §5 / plan §3.5).

    365 daily points from 2025-11-07; BTC drift 0.0008 σ 0.035,
    ETH drift 0.0006 σ 0.045, SOL drift 0.0005 σ 0.06; starting prices
    BTC $100,000 / ETH $3,500 / SOL $180; volumes log-normal noise
    around each coin's typical daily volume. Returns data in the same
    shape as the API response so clean_chart() works unchanged.
    Only called when fetch fails AND no cache exists.
    """
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2025-11-07", tz="UTC")
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
    """Orchestrate: fetch (or cache, or synthetic) -> clean -> features
    -> rules + forest -> injection + evaluation -> save.

    Reads an optional Demo key ONLY from the COINGECKO_DEMO_API_KEY
    environment variable — never from a file in the repo.

    --offline / --use-cache: skip the network entirely; use only the
    committed data/raw/*.json cache (never generate synthetic data).
    Exits non-zero if no cache exists.
    """
    global DATA_SOURCE
    parser = argparse.ArgumentParser(
        description="Crypto Anomaly Detector pipeline: fetch, clean, "
        "features, rules + forest, injection + evaluation."
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
    analysis = run_anomaly_analysis(daily)
    save_outputs(daily, analysis, raw)

    print(f"\nData source: {DATA_SOURCE.upper()}")
    for coin in COINS:
        g = daily[daily["coin"] == coin]
        print(f"  {coin}: {len(g)} rows, {g['date'].min()} to {g['date'].max()}")
    ev = analysis["evaluation"]
    tl = analysis["timeline"]
    detected = analysis["detected"]
    flaggable = detected["return_z"].notna()
    real_baseline = int(detected.loc[flaggable, "baseline_flagged"].sum())
    print(
        f"Baseline flag rate: {real_baseline / int(flaggable.sum()):.1%} "
        f"({real_baseline} flags, post-warm-up universe "
        f"{int(flaggable.sum())} rows)"
    )
    print(f"Contamination used: {analysis['contamination']:.4f}")
    print(
        f"Timeline flags: {len(tl)} "
        f"(both={int((tl['flagged_by'] == 'both').sum())}, "
        f"baseline-only={int((tl['flagged_by'] == 'baseline').sum())}, "
        f"forest-only={int((tl['flagged_by'] == 'forest').sum())})"
    )
    print(f"Jaccard overlap: {ev['jaccard']:.3f}")
    for method in ("baseline", "forest", "union"):
        m = ev[method]
        print(
            f"  {method}: precision {m['precision']:.3f}, "
            f"recall {m['recall']:.3f}, F1 {m['f1']:.3f} "
            f"(TP {m['tp']}/{ev['n_injected']}, FP {m['fp']})"
        )
    print(f"Per-type recall (union): {ev['per_type_recall']}")
    if DATA_SOURCE == "synthetic":
        print(
            "Wrote data/raw/*_market_chart_synthetic.json "
            "(synthetic — live cache untouched), "
            "data/processed/crypto_daily.csv, "
            "data/processed/crypto_daily_injected.csv, "
            "data/processed/anomaly_timeline.csv, "
            "data/processed/injected_anomalies.csv"
        )
    else:
        print(
            "Wrote data/raw/*.json, data/processed/crypto_daily.csv, "
            "data/processed/crypto_daily_injected.csv, "
            "data/processed/anomaly_timeline.csv, "
            "data/processed/injected_anomalies.csv"
        )


if __name__ == "__main__":
    main()
