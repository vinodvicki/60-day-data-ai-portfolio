# Day 1 — Crypto Market Intelligence Dashboard: Research Brief

**Project:** 60-Day Data Analytics + AI Portfolio, Day 1
**Business question:** How did Bitcoin and Ethereum differ in price momentum, realised volatility, liquidity proxies, and drawdown over a chosen historical window?
**Scope note:** Descriptive analytics only. **No buy/sell recommendation, no price prediction, no investment advice.**
**Research date:** 2026-11-05 | **Verified via:** CoinGecko official docs (docs.coingecko.com) + CoinGecko Support knowledge base, one lean search pass (2 queries).

---

## 1. API — verified

**Base URL (public, no key required):** `https://api.coingecko.com/api/v3`

**Primary endpoint — historical chart (rolling window):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=365
```

**Alternative endpoint — exact date range (preferred for reproducibility):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1762300800&to=1793836800
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1762300800&to=1793836800
GET https://api.coingecko.com/api/v3/coins/solana/market_chart/range?vs_currency=usd&from=1762300800&to=1793836800
```

**Date range:** 2025-11-05 → 2026-11-05 (365 days).
- `from = 1762300800` (2025-11-05 00:00 UTC), `to = 1793836800` (2026-11-05 00:00 UTC). Unix seconds.
- Public (keyless) API is limited to the past 365 days; `days=max` or older windows require a Pro key.

**Coin IDs are slugs, not tickers:** `bitcoin`, `ethereum`, `solana` (not BTC/ETH/SOL).

**Optional sanity-check endpoint (current price):**

```
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true
```

**Example request (curl):**

```bash
curl -s "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365"
```

---

## 2. Response fields (verified against official docs)

Each `market_chart` / `market_chart/range` call returns a JSON object with three arrays of `[timestamp, value]` pairs:

| Field | Contents | Units |
|---|---|---|
| `prices` | `[timestamp_ms, price]` | timestamp = **milliseconds since Unix epoch (UTC)**; price in USD |
| `market_caps` | `[timestamp_ms, market_cap]` | USD |
| `total_volumes` | `[timestamp_ms, 24h trading volume]` | USD |

Notes:
- All three arrays share the same timestamps; merge on timestamp into one daily frame with columns `date, price, market_cap, volume`.
- `market_chart` returns **close prices only** — no open/high/low. For ATR-style ranges use `/coins/{id}/ohlc` instead (out of scope for Day 1).
- **Granularity is automatic** when `interval` is omitted: 1 day → 5-minutely; 2–90 days → hourly; **>90 days → daily (00:00 UTC)**. At `days=365` the data is daily — exactly what this dashboard needs. Do not pass `interval` (explicit 5m/hourly intervals are Enterprise-only).
- `market_chart/range` accepts ISO date strings (`YYYY-MM-DD`) or Unix seconds for `from`/`to`.

---

## 3. Metrics to compute

All computed on the daily, date-aligned frame (BTC vs ETH; SOL as optional third comparator).

| # | Metric | Definition |
|---|---|---|
| 1 | **Daily return** | `price_t / price_{t-1} − 1` (log return optional: `ln(price_t / price_{t-1})`) |
| 2 | **7-day rolling return** | `price_t / price_{t-7} − 1` — short-term momentum |
| 3 | **30-day rolling volatility (annualised)** | `std(daily returns, 30-day window) × √365` — realised volatility; use 365 (crypto trades every day), not 252 |
| 4 | **Max drawdown** | `min(price_t / running_max(price) − 1)` over the window; also report drawdown duration (days from peak to recovery) |
| 5 | **Relative volume (liquidity proxy)** | `volume_t / mean(volume, 30-day window)`; plus `volume / market_cap` (turnover) as a second liquidity proxy |
| 6 | **Correlation** | Pearson correlation of daily returns, BTC vs ETH (and vs SOL if included), over the full window and in 90-day rolling windows |

**Dashboard views:** (a) normalised price index (both = 100 on day 1) for momentum comparison; (b) 30-day rolling volatility chart; (c) drawdown-from-peak chart; (d) relative-volume chart; (e) summary table of the six metrics per coin.

---

## 4. Rate limits & caution

- **Official (CoinGecko Support): Public API = 5–15 calls/minute**, varying with global usage. HTTP 429 is the signal; the response carries a `Retry-After` header (observed 60 s in third-party probes).
- Third-party sources quote wider figures (~3/min observed under burst, ~30/min Demo tier) — treat the official 5–15/min as the planning number and be conservative.
- **Day 1 needs only 3 calls** (one per coin) — well inside the limit if spaced out. Rule: **≥5 seconds between calls, one retry after 60 s on 429, then stop and fall back to cached/synthetic data** (see §6). Never hammer the API.
- A free Demo API key (register at coingecko.com/en/api/pricing) raises the limit to ~30–100 calls/min — optional upgrade, not required for Day 1.

---

## 5. Licence / attribution

- CoinGecko data is free for use via the public API; **CoinGecko requests attribution** when its data is used. Include on the dashboard and in the repo README: **"Data source: CoinGecko (coingecko.com)"** with a link.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched series locally for the project only.
- Dashboard must carry the disclaimer: *"Educational analysis only — not investment advice."*

---

## 6. Synthetic-fallback note (if the API is unreachable)

If all requests fail (429 loop, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful fetch if one exists (`data/raw/`).
2. Otherwise generate a **clearly labelled synthetic dataset** for development only: geometric Brownian motion seeded per coin (BTC: daily drift 0.0008, daily σ 0.035; ETH: drift 0.0006, σ 0.045; SOL: drift 0.0005, σ 0.06), 365 daily points from 2025-11-05, starting prices BTC $100,000 / ETH $3,500 / SOL $180, volumes as log-normal noise around each coin's typical daily volume. Mark every chart and the README **"SYNTHETIC DATA — API unavailable on <date>"** and re-fetch real data before publishing.
3. Never present synthetic data as real CoinGecko data.

---

## 7. Verification status

- ✅ Endpoint paths, parameters, response fields, granularity rules, 365-day public limit, and official 5–15/min rate limit confirmed against CoinGecko official docs/support (docs.coingecko.com, support.coingecko.com), accessed 2026-11-05.
- ⚠️ **One unverified conflict:** a third-party guide claims `/market_chart` "now requires a demo key on the public host". The official endpoint overview still lists it under the Demo/Keyless API, so it is treated as keyless — but the build step must test the no-key call first and report the actual HTTP status. If it returns 401/403, register the free Demo key and retry with header `x-cg-demo-api-key`.
- No live API call was made during this research step (verification was docs-only, per the lean-search instruction).
