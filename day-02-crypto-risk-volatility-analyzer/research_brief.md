# Day 2 — Crypto Risk & Volatility Analyzer: Research Brief

**Project:** 60-Day Data Analytics + AI Portfolio, Day 2
**Roadmap entry (verbatim):** "DAY 02 | Crypto Risk & Volatility Analyzer — Problem / analysis: Compare drawdowns, rolling volatility, correlations, and risk-adjusted historical returns to assess portfolio exposure. GitHub deliverable: Risk comparison dashboard and plain-language risk notes."
**Business question:** For the same three coins (Bitcoin, Ethereum, Solana) over the past year, how much risk did each one actually carry — how far did it fall from its peak, how jumpy were its daily moves, how closely did the coins move together, and how much return did each deliver per unit of risk taken?
**Scope note:** Descriptive, historical risk analysis only. **No buy/sell recommendation, no price prediction, no investment advice.** Past volatility and drawdowns do not predict future risk.
**Research date:** 2026-11-06 | **Verified via:** CoinGecko official docs (docs.coingecko.com) + CoinGecko Support knowledge base as verified on Day 1 (2026-11-05), plus one lightweight live check today (ping endpoint, HTTP 200 — see §6). No full dataset was fetched by the researcher; the live fetch is the coder's job.

---

## 1. API — verified

**Base URL (public, no key required):** `https://api.coingecko.com/api/v3`

**Primary endpoint — exact date range (preferred for reproducibility, same as Day 1):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
GET https://api.coingecko.com/api/v3/coins/solana/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
```

**Fallback endpoint — rolling window (use only if `/range` fails):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=365
```

**Date range:** 2025-11-06 → 2026-11-06 (365-day span, inclusive of both endpoint dates).
- `from = 1762387200` (2025-11-06 00:00 UTC), `to = 1793923200` (2026-11-06 00:00 UTC). Unix seconds.
- Public (keyless) API is limited to the past 365 days; `days=max` or older windows require a Pro key.
- Expected shape (by the Day 1 precedent, same method, window shifted one day): **366 daily observations per coin, 1,098 rows total** in the processed daily frame. The coder must verify the actual row count and report it; do not assume it.

**Coin IDs are slugs, not tickers:** `bitcoin`, `ethereum`, `solana` (not BTC/ETH/SOL).

**`interval` parameter — do NOT pass it.** The task draft listed `interval=daily`, but Day 1 verified against the official docs that granularity is automatic when `interval` is omitted (1 day → 5-minutely; 2–90 days → hourly; **>90 days → daily, 00:00 UTC**) and that explicit 5m/hourly intervals are Enterprise-only. At `days=365` / a 365-day range the data is daily without any `interval` argument. Passing `interval=daily` is unnecessary and is not a documented public-API parameter value — the coder must omit it, exactly as Day 1 did.

**Optional sanity-check endpoint (current price):**

```
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true
```

---

## 2. Response fields (verified against official docs, Day 1)

Each `market_chart` / `market_chart/range` call returns a JSON object with three arrays of `[timestamp, value]` pairs:

| Field | Contents | Units |
|---|---|---|
| `prices` | `[timestamp_ms, price]` | timestamp = **milliseconds since Unix epoch (UTC)**; price in USD |
| `market_caps` | `[timestamp_ms, market_cap]` | USD |
| `total_volumes` | `[timestamp_ms, 24h trading volume]` | USD |

Notes:
- All three arrays share the same timestamps; merge on timestamp into one daily frame with columns `date, coin, price, market_cap, volume` (date = YYYY-MM-DD, UTC). Day 2 needs `price` for every metric; `market_cap` and `volume` are kept for provenance/context but no volume metric is required.
- `market_chart` returns **close prices only** — no open/high/low. No intraday or OHLC metric is in scope for Day 2.
- Reuse the Day 1 daily frame shape where it fits; Day 2's processed metrics file is a new file (name per `plan.md`), not an edit of Day 1's CSVs.

---

## 3. Metric definitions (coder implements exactly these)

All metrics are computed on the daily, date-aligned frame, per coin, over the window 2025-11-06 → 2026-11-06. Use **simple (arithmetic) daily returns** throughout — not log returns — so every number in the dashboard, notebook and notes is on the same basis. All returns are in decimal (e.g. −0.02 = −2%); present them as percentages in the dashboard.

| # | Metric | Definition / formula |
|---|---|---|
| 1 | **Daily return** | `r_t = price_t / price_{t-1} − 1`. First row per coin is NaN (no prior day). |
| 2 | **Max drawdown** | Let `peak_t = max(price_0 … price_t)` (running maximum). Drawdown `dd_t = price_t / peak_t − 1` (≤ 0). Max drawdown = `min(dd_t)` over the window. Report also the **peak date** and **trough date** that produce it. |
| 3 | **Current drawdown** | `dd` on the last date (2026-11-06): `price_last / running_max_last − 1`. Zero means the coin closed the window at its window high. |
| 4 | **Drawdown duration & recovery** | For the max drawdown: **peak-to-trough days** = trough date − peak date (calendar days); **recovery days** = days from trough until price first closes at or above the peak price again; if it never recovers within the window, report **"not recovered by 2026-11-06"** and the days elapsed since the trough. Also report the **longest underwater period** (longest run of consecutive days with `dd_t < 0`) if it differs from the max-drawdown episode. |
| 5 | **Rolling 30-day volatility (annualised)** | `vol_30d_t = std(r_{t-29} … r_t) × √365`, where `std` is the sample standard deviation (ddof=1, pandas default). Use **365** (crypto trades every day), not 252. First 29 rows per coin are NaN (30-day window needs 30 returns). Also report per coin: mean, median and maximum of `vol_30d` over the window. |
| 6 | **Return correlations** | Pearson correlation of daily returns, pairwise: BTC–ETH, BTC–SOL, ETH–SOL. (a) **Full window** (all overlapping non-NaN daily returns); (b) **latest 90 days** (returns on the last 90 calendar days of the window). Report the 3×3 full-window matrix and the three latest-90d values. |
| 7 | **Sharpe ratio (annualised)** | `Sharpe = mean(r) / std(r) × √365`, computed on daily returns over the full window. **Risk-free rate assumption: 0%.** No T-bill rate is fetched; the 0% assumption is stated on the dashboard and in the notes so the figure is a pure return-per-unit-of-volatility measure. (If a future day adds a T-bill proxy, the formula becomes `mean(r − r_f_daily) / std(r − r_f_daily) × √365` with `r_f_daily = annual T-bill rate / 365` — out of scope for Day 2.) |
| 8 | **Sortino ratio (annualised)** | `Sortino = mean(r) / downside_deviation × √365`, where downside deviation = `sqrt(mean(min(r_t, 0)²))` over the full window (target/minimum acceptable return = 0). Same 0% risk-free assumption as Sharpe. Sortino penalises only downside moves, so it will be higher than Sharpe for coins whose volatility was mostly upside. |
| 9 | **Historical VaR 95% (daily)** | The 5th percentile of daily returns over the full window: `VaR_95 = percentile(r, 5)` (linear interpolation, numpy/pandas default). Report as a negative percentage, e.g. "on 95% of days the loss was no worse than −X%". State the convention in the notes: this is a **one-day, 95% historical VaR on daily returns**. |
| 10 | **Historical CVaR 95% (daily)** | Mean of the daily returns at or below VaR: `CVaR_95 = mean(r_t | r_t ≤ VaR_95)`. Always ≤ VaR (a larger expected loss). Report alongside VaR as "average loss on the worst 5% of days". |

**Derived summary table (per coin, for the dashboard + notes):** total return over the window (`price_last / price_first − 1`), max drawdown, current drawdown, peak-to-trough days + recovery status, mean/median/max 30-day annualised volatility, full-window Sharpe, Sortino, daily VaR 95%, daily CVaR 95%. Plus the correlation matrix (full window + latest 90d).

**Plain-language risk notes (required deliverable):** `outputs/insights_summary.md` must explain, for a non-expert reader, in plain words: what a drawdown means ("how far the price fell from its highest point and how long it took to climb back"), what volatility means ("how jumpy day-to-day moves were"), what correlation means ("whether the coins tended to fall together — high correlation means little protection from holding more than one"), what Sharpe/Sortino mean ("how much return you got for each unit of risk — higher is better, but only on past data"), and what VaR/CVaR mean ("on a typical bad day you could expect to lose about X%; on the very worst days the average loss was Y%"). Every plain-language claim must cite the matching number from the summary table. No investment advice.

**Day 1 numbers are NOT Day 2 findings.** Day 1 verified (window 2025-11-05 → 2026-11-05): BTC max drawdown −44.7237% (peak $105,951.50 on 2025-11-11 → trough $58,566.09 on 2026-07-01), BTC–ETH full-window correlation 0.906 (0.890 latest 90d). Day 2's window is shifted one day later, so every metric must be recomputed from Day 2's own data — do not copy Day 1's figures into Day 2's outputs.

---

## 4. Rate limits & caution

- **Official (CoinGecko Support): Public API = 5–15 calls/minute**, varying with global usage. HTTP 429 is the signal; the response carries a `Retry-After` header (observed 60 s in third-party probes).
- Third-party sources quote wider figures (~3/min observed under burst, ~30/min Demo tier) — treat the official 5–15/min as the planning number and be conservative.
- **Day 2 needs only 3 calls** (one per coin) — well inside the limit if spaced out. Rule: **≥5 seconds between calls, one retry after 60 s on 429, then stop and fall back to cached/synthetic data** (see §5). Never hammer the API.
- **Demo-key fallback (kept, not required):** Day 1 proved the no-key call returns HTTP 200 for all three coins, so no key is expected to be needed. Keep the fallback in code exactly as Day 1 did: an optional CoinGecko Demo key read only from the `COINGECKO_DEMO_API_KEY` **environment variable, never hard-coded**, sent as header `x-cg-demo-api-key`, used only if the no-key call returns 401/403. No key is stored anywhere in the repo. A free Demo key raises the limit to ~30–100 calls/min — optional upgrade, not required for Day 2.

---

## 5. Licence / attribution

- CoinGecko data is free for use via the public API; **CoinGecko requires attribution** (API Terms Clause 3). Include on the dashboard and in the repo README, legible, size 10+: **"Powered by CoinGecko"** with a link to coingecko.com.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched series locally for the project only.
- Dashboard and notes must carry the disclaimer: *"Educational analysis only — not investment advice."*
- **Unresolved licensing tension (carried from Day 1, Stage 2):** the code in this repo is MIT, but the CoinGecko data is under separate CoinGecko terms, not MIT. CoinGecko API Terms Clause 6 bars selling, renting, leasing, sub-licensing, re-distributing or syndicating API access without an executed agreement; the Demo (free) plan does not include commercial rights, and attribution alone does not grant them. Redistribution or resale requires a custom licence. CoinGecko support defines redistribution as providing data / API access for others to retrieve and use beyond viewing it in the product, and says cached or reformatted data is not automatically exempt. However, **no CoinGecko page found states explicitly whether committing verbatim raw API JSON to a public GitHub repo counts as redistribution**, so this is unresolved and no legal certainty is claimed. Day 1 kept the raw JSONs committed as the provenance record; Day 2 follows the same rule (small raw data committed, see `data/README.md` in the Day 2 folder, to be written by the coder per the plan) and states the tension honestly there.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under 1 MB each, under 5 MB per day folder — because the raw files are the provenance record. `.gitignore` must NOT exclude `data/`. Anything larger must be `.gitignore`d and regenerated by the pipeline.

---

## 6. Synthetic-fallback note (if the API is unreachable)

If all requests fail (429 loop, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful fetch if one exists (`data/raw/`).
2. Otherwise generate a **clearly labelled synthetic dataset** for development only, using the Day 1 parameters verbatim so results stay comparable: geometric Brownian motion, **seed 42** (deterministic), BTC daily drift 0.0008 σ 0.035; ETH drift 0.0006 σ 0.045; SOL drift 0.0005 σ 0.06; 365 daily points from **2025-11-06**; starting prices BTC $100,000 / ETH $3,500 / SOL $180; volumes as log-normal noise around each coin's typical daily volume. Mark every chart, the app and the README **"SYNTHETIC DATA — API unavailable on 2026-11-06"** and re-fetch real data before publishing.
3. Synthetic output goes to `data/raw/{coin}_market_chart_synthetic.json` **only** — it must never overwrite the live cache `data/raw/{coin}_market_chart.json`. `data/processed/data_source.json` records `"synthetic": true` **and** `"seed": 42` when synthetic is used (`"seed": null` for live data).
4. Never present synthetic data as real CoinGecko data. `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the committed cache with no network and never generates synthetic data.

---

## 7. Verification status

- ✅ Endpoint paths, parameters, response fields, granularity rules (incl. the `interval` correction in §1), 365-day public limit, and official 5–15/min rate limit confirmed against CoinGecko official docs/support (docs.coingecko.com, support.coingecko.com), as verified on Day 1 (2026-11-05) and re-confirmed by the live check below.
- ✅ **Live check today (2026-11-06, 13:57 UTC):** `GET https://api.coingecko.com/api/v3/ping` returned **HTTP 200** in 1.66 s with body `{"gecko_says":"(V3) To the Moon!"}`. The CoinGecko public API host is reachable today. This was the researcher's single lightweight check — no full dataset was fetched.
- ✅ Day 1 already proved the no-key `/market_chart` call returns HTTP 200 for all three coins (2026-11-05); the same call shape is used for Day 2 with the window shifted one day (2025-11-06 → 2026-11-06). The coder must still test the no-key call first in the build and report the actual HTTP status per coin.
- ⚠️ **No unresolved endpoint conflict for Day 2.** The one Day 1 conflict (third-party claim that `/market_chart` "now requires a demo key") was resolved by the live test on 2026-11-05 (HTTP 200, no key). The only correction this brief makes to the task draft is the `interval=daily` parameter: it must be omitted (§1).
- ⚠️ Metric-definition choices the coder must not re-decide: simple (not log) daily returns; annualisation × √365 (not √252); risk-free rate 0% for Sharpe/Sortino; VaR/CVaR are one-day historical figures on daily returns (5th percentile / mean of the tail). If any of these is unworkable, the planner notes the change in `plan.md` — the coder does not silently substitute a different convention.

---

## 8. What the coder must NOT do

- **No copying code or tutorials from the web.** All code is Victor's own original work, written from this brief and the plan. Do not paste or adapt snippets, tutorials, or other people's repositories.
- **No extra web searches** for endpoints, parameters or metric definitions — everything needed is in this brief. If something in this brief is genuinely unworkable, send it back to the planner with the exact point, don't re-research it.
- **No hard-coded API key.** The Demo-key fallback reads only the `COINGECKO_DEMO_API_KEY` environment variable. No `.env` file, no key in code, no key in any committed file.
- **No live fetch by the researcher** — already done (ping only, §7). The coder owns the 3-call live fetch (≥5 s apart, one 60 s retry on 429, then fallback per §6).
- **No presenting synthetic data as real**, and no overwriting the live cache with synthetic data (§6).
- **No investment advice** anywhere in the dashboard, notebook, charts or notes.
