**Stage-2 amendment (2026-11-05):** §§4.4–4.5 below still record the original wording. Current wording is: attribution is 'Powered by CoinGecko' (CoinGecko API Terms Clause 3, legible, size 10+); synthetic data is written to data/raw/*_synthetic.json and never overwrites the live cache; the committed raw CoinGecko JSONs are kept in this public repo and the licensing tension is documented honestly in data/README.md — the question whether that counts as redistribution is unresolved, no legal certainty is claimed. See data/README.md for the current statement.

# Day 1 — Crypto Market Intelligence Dashboard: Build Plan

**Project:** 60-Day Data Analytics + AI Portfolio, Day 1
**Plan date:** 2026-11-05
**Source of truth:** `research_brief.md` (same folder) — the coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap source:** `~/workspace/user/files/60_Day_Data_Analytics_AI_GitHub_Project_Roadmap_0_4qxt.pdf` (also copied into this folder)
**Status:** Plan only — no code has been written.

---

## 1. Problem

Retail crypto observers (and hiring managers reviewing this portfolio) can see today's price, but not how the major coins actually behaved over the past year: which one had stronger momentum, which was more volatile, where liquidity dried up, and how deep and long the worst falls were.

**Business question (from the roadmap):** *How did Bitcoin and Ethereum differ in price momentum, realized volatility, liquidity proxies, and drawdown over the past 365 days?* Solana is included as a third comparator where it adds contrast, not as a co-lead.

**Scope — hard limits:**
- Descriptive analytics only. **No buy/sell recommendation, no price prediction, no investment advice.**
- No OHLC / ATR analysis (`/ohlc` is out of scope); `market_chart` returns close prices only.
- Window: 2025-11-05 → 2026-11-05 (365 days, daily granularity). The public CoinGecko API cannot go older than 365 days without a Pro key.

## 2. Audience / decision-maker

| Audience | What they need from this dashboard |
|---|---|
| Retail crypto observer | A plain-English answer to "which coin was steadier, which moved harder, and when did it hurt most?" — readable without a finance degree. |
| Hiring manager / data-analyst portfolio reviewer | Evidence of end-to-end craft: documented data provenance, reproducible pipeline, labelled charts, honest limitations, and a validated metric. |
| Future self (Days 2–60) | A reusable template: fetch → clean → metrics → charts → Streamlit app, so later days copy the structure, not reinvent it. |

## 3. Questions the dashboard must answer (2–3)

1. **Momentum:** Over 365 days, which coin gained more on a like-for-like basis (price indexed to 100 on day 1), and when did the lead change hands?
2. **Volatility & drawdown:** Which coin was more volatile (30-day rolling annualised volatility) and which suffered the deeper / longer drawdown from its peak?
3. **Liquidity:** Did trading volume (relative volume vs its 30-day mean, and turnover = volume / market cap) spike, dry up, or stay flat around the biggest price moves — and did BTC and ETH behave differently?

Each question maps to at least one chart (see §7) and at least one finding in `outputs/insights_summary.md`.

---

## 4. Data

### 4.1 Source (verified — do not re-verify)

- **Base URL:** `https://api.coingecko.com/api/v3` — public, no key required (see caveat in §4.3).
- **Primary endpoint (rolling window):**
  - `GET /coins/bitcoin/market_chart?vs_currency=usd&days=365`
  - `GET /coins/ethereum/market_chart?vs_currency=usd&days=365`
  - `GET /coins/solana/market_chart?vs_currency=usd&days=365`
- **Preferred endpoint for reproducibility (exact range):** same three coins via `/coins/{id}/market_chart/range?vs_currency=usd&from=1762300800&to=1793836800` (`from` = 2025-11-05 00:00 UTC, `to` = 2026-11-05 00:00 UTC, Unix seconds). Use this one in the pipeline; fall back to `days=365` only if `range` fails.
- **Coin IDs are slugs, not tickers:** `bitcoin`, `ethereum`, `solana`.
- **Optional sanity check:** `GET /simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true` — use only to confirm the API is alive / prices are sane; do not count it as a data call.
- **Response:** JSON with `prices`, `market_caps`, `total_volumes` — each an array of `[timestamp_ms, value]` pairs. All three arrays share timestamps. Granularity is automatic: at `days=365` (or a 365-day range) it is **daily, 00:00 UTC**. Do **not** pass `interval` (explicit 5m/hourly intervals are Enterprise-only).

### 4.2 Fetch rules (rate limits — verified)

- Official public limit: **5–15 calls/min**. Day 1 needs only **3 calls** (one per coin).
- **≥5 seconds between calls. One retry after 60 s on HTTP 429 (honour the `Retry-After` header if present), then stop and fall back** (§4.4). Never hammer the API.
- A free Demo key (register at coingecko.com/en/api/pricing) raises the limit to ~30–100/min — optional, not required for Day 1.

### 4.3 The one unverified conflict — test order (mandatory)

A third-party guide claims `/market_chart` "now requires a demo key on the public host". The official docs still list it under the Demo/Keyless API, so the plan treats it as keyless — but the coder **must test in this order and record the actual HTTP status in `data/README.md`**:
1. **No-key call first.** If 200 → proceed keyless.
2. If **401/403** → register the free Demo key, retry with header `x-cg-demo-api-key: <key>`. The key must come from the user / secure store — **never hard-code it, never commit it** (see §9).
3. If still failing after the 429 retry rule → synthetic fallback (§4.4).

### 4.4 Offline / failure fallback

1. Reuse a cached copy in `data/raw/` if one exists from a previous successful fetch.
2. Otherwise generate a **clearly labelled synthetic dataset** for development only: geometric Brownian motion, seeded per coin — BTC daily drift 0.0008, σ 0.035; ETH drift 0.0006, σ 0.045; SOL drift 0.0005, σ 0.06; 365 daily points from 2025-11-05; starting prices BTC $100,000 / ETH $3,500 / SOL $180; volumes as log-normal noise around each coin's typical daily volume.
3. Mark **every chart, the app banner, and the README: "SYNTHETIC DATA — API unavailable on <date>"** and re-fetch real data before publishing. Never present synthetic data as real CoinGecko data.
   Synthetic output goes to data/raw/{coin}_market_chart_synthetic.json; the live data/raw/{coin}_market_chart.json cache is never overwritten.

### 4.5 Attribution & licence

- CoinGecko requests attribution. Include on the dashboard and in the README: **"Data source: CoinGecko (coingecko.com)"** with a link.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched series locally for this project only.
- Dashboard + README must carry: *"Educational analysis only — not investment advice."*

---

## 5. File tree (exact — match the roadmap template)

```
day-01-crypto-market-intelligence/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE                     # MIT
├── research_brief.md           # already present — do not overwrite
├── plan.md                     # this file
├── data/
│   ├── README.md               # provenance log (see §6)
│   ├── raw/
│   │   ├── bitcoin_market_chart.json
│   │   ├── ethereum_market_chart.json
│   │   └── solana_market_chart.json
│   └── processed/
│       ├── crypto_daily.csv    # one row per coin per day: date, coin, price, market_cap, volume
│       └── crypto_metrics.csv  # daily returns, 7d return, 30d vol, drawdown, rel. volume, turnover
├── notebooks/
│   └── analysis.ipynb          # exploratory analysis; must run top-to-bottom without errors
├── src/
│   ├── data_pipeline.py        # fetch → clean → metrics → save (see §6)
│   └── app.py                  # Streamlit dashboard (see §7)
├── outputs/
│   ├── insights_summary.md     # 3 findings + 1 actionable recommendation
│   └── charts/
│       ├── 01_price_indexed.png
│       ├── 02_rolling_volatility.png
│       ├── 03_drawdown.png
│       ├── 04_relative_volume.png
│       └── 05_summary_table.png   # optional; table as an image if easier than text
├── screenshots/
│   └── dashboard.png           # full Streamlit app screenshot for the README
└── tests/
    └── test_pipeline.py        # smoke tests (see §8)
```

Notes:
- `data/raw/*.json` are the verbatim API responses — never edit them by hand.
- `data/processed/*.csv` are regenerated by `src/data_pipeline.py`; they are the only data the notebook and app read.
- Keep the repo lean: raw JSON + processed CSVs are small (365 rows × 3 coins); do not commit anything else large. `.gitignore` must exclude `__pycache__/`, `.venv/`, `.streamlit/secrets.toml`, and any `*.key` / credential files.

---

## 6. Per-file responsibilities

### `README.md` (repo front door)
- Title, one-paragraph problem statement, audience, and the business question.
- How to run: `pip install -r requirements.txt`, `python src/data_pipeline.py`, `streamlit run src/app.py`.
- Data provenance: source, endpoint, window (2025-11-05 → 2026-11-05), fetch date, keyless vs Demo-key outcome, attribution line, disclaimer.
- Sample outputs: embed `outputs/charts/01_price_indexed.png` and `02_rolling_volatility.png` + `screenshots/dashboard.png`; link `outputs/insights_summary.md`.
- Limitations: close prices only (no OHLC/ATR), 365-day public-API cap, daily granularity, volume is a liquidity *proxy* (exchange-reported 24h volume, not order-book depth), synthetic-data flag if applicable.
- License note (MIT).

### `data/README.md` (provenance log — fill in during the build)
- Fetch timestamp (UTC), endpoint used (`range` vs `days=365`), HTTP status per coin, keyless or Demo-key, number of rows returned per coin, date range actually covered, any gaps/duplicates found and how handled, and whether the data is real or synthetic (with date).

### `data/raw/` and `data/processed/`
- Raw: verbatim JSON per coin, named exactly as in the tree.
- Processed `crypto_daily.csv` columns: `date, coin, price, market_cap, volume` (date = YYYY-MM-DD, UTC).
- Processed `crypto_metrics.csv` columns: `date, coin, daily_return, return_7d, vol_30d_annualised, drawdown, relative_volume, turnover` (+ `corr_btc_eth_90d` as a separate small CSV or a column on BTC rows — coder's choice, document it in `data/README.md`).

### `src/data_pipeline.py` — the only script that touches the API
Function signatures (exact names; coder may add private helpers prefixed `_`):

```python
COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCY = "usd"
FROM_TS = 1762300800   # 2025-11-05 00:00 UTC
TO_TS = 1793836800     # 2026-11-05 00:00 UTC
BASE_URL = "https://api.coingecko.com/api/v3"

def fetch_coin_chart(coin: str, api_key: str | None = None) -> dict:
    """One GET to /coins/{coin}/market_chart/range (fallback: market_chart?days=365).
    Sleeps >=5s before the call (caller's pacing is acceptable if documented).
    One retry after 60s on 429. Raises RuntimeError after that so the caller
    can fall back. Sends x-cg-demo-api-key header only if api_key is given."""

def fetch_all_coins(api_key: str | None = None) -> dict[str, dict]:
    """Calls fetch_coin_chart for each coin in COINS; returns {coin: raw_json}."""

def clean_chart(raw: dict, coin: str) -> pd.DataFrame:
    """Merges prices/market_caps/total_volumes on timestamp_ms -> DataFrame
    with columns [date, coin, price, market_cap, volume]; date as YYYY-MM-DD
    (UTC); drops duplicate timestamps; sorts by date; asserts no NaNs in price."""

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Adds, per coin, on the daily frame:
    - daily_return = price_t / price_{t-1} - 1
    - return_7d = price_t / price_{t-7} - 1
    - vol_30d_annualised = std(daily_return, 30d) * sqrt(365)  (365, NOT 252)
    - drawdown = price_t / running_max(price) - 1  (also record max drawdown
      value + peak-to-recovery duration per coin for the summary)
    - relative_volume = volume_t / mean(volume, 30d)
    - turnover = volume / market_cap
    Also computes BTC-ETH Pearson correlation of daily returns (full window
    and 90-day rolling) and returns it alongside the metrics frame."""

def save_outputs(daily: pd.DataFrame, metrics: pd.DataFrame, raw: dict) -> None:
    """Writes raw JSONs to data/raw/, crypto_daily.csv and crypto_metrics.csv
    to data/processed/. Creates directories if missing."""

def generate_synthetic(seed: int = 42) -> dict[str, dict]:
    """Deterministic GBM fallback per the parameters in §4.4. Returns data in
    the same shape as the API response so clean_chart() works unchanged.
    Only called when fetch fails AND no cache exists."""

def main() -> None:
    """Orchestrates: fetch (or cache, or synthetic) -> clean -> compute_metrics
    -> save_outputs. Prints a short run summary (rows per coin, date range,
    real vs synthetic). Reads an optional Demo key ONLY from the
    COINGECKO_DEMO_API_KEY environment variable — never from a file in the repo."""
```

### `notebooks/analysis.ipynb`
- Exploratory analysis that mirrors the pipeline: load `data/processed/crypto_daily.csv` + `crypto_metrics.csv`, reproduce each metric independently (spot-check the pipeline), and draft the charts that become `outputs/charts/*.png`. Must run top-to-bottom cleanly. Keep it readable: markdown headings per question (§3), short code cells, one chart per question minimum.

### `src/app.py` — Streamlit dashboard
- Reads **only** `data/processed/*.csv` (never calls the API).
- Page title: "Crypto Market Intelligence — BTC vs ETH vs SOL (365 days)".
- Header banner: attribution "Data source: CoinGecko (coingecko.com)" + disclaimer "Educational analysis only — not investment advice." + data window + a red "SYNTHETIC DATA" banner if applicable.
- Sidebar: coin multi-select (default BTC + ETH, SOL optional), date-range slider (default full window).
- Four views (each a labelled chart with title, axis labels, units, legend, source note):
  1. **Price indexed to 100** — normalised price (`price / first price × 100`) for selected coins; this is the momentum comparison.
  2. **Volume trends** — daily volume (log scale toggle) and/or relative volume (`volume / 30d mean`) per coin; note volume is a liquidity proxy.
  3. **Rolling volatility comparison** — 30-day rolling annualised volatility, BTC vs ETH (SOL optional), same axes.
  4. **Drawdown timeline** — drawdown-from-peak (%) over time per coin, with the max-drawdown value and duration annotated.
- Below the charts: a summary table of the six metrics per coin (total return, 7d return at end of window, mean & max 30d volatility, max drawdown + duration, mean relative volume, mean turnover, BTC-ETH correlation).
- Key numbers in the UI must come from the processed CSVs, not hard-coded.

### `outputs/insights_summary.md`
- Exactly: **3 findings** (each tied to a question in §3 and a chart) **+ 1 actionable recommendation**. "Actionable" here means an analytical next step (e.g. "extend the window / add a fourth coin / track turnover weekly"), **not** investment advice. Include the metric values that support each finding.

### `outputs/charts/*.png`
- Generated from the notebook or a small chart script reusing the processed CSVs — one file per view in §7, numbered as in the tree. Every chart: title, labelled axes with units, legend, data-window + "Source: CoinGecko" footnote. Consistent style across all five (same palette, same font sizes, readable at README width).

### `screenshots/dashboard.png`
- Full-page screenshot of the running Streamlit app (all four views visible or scrolled-captured); used in the README.

### `tests/test_pipeline.py`
- Smoke tests only (no network): `clean_chart` on a small hand-built raw dict; `compute_metrics` on a tiny synthetic frame (check daily return, 7d return, drawdown sign, volatility > 0); `generate_synthetic` is deterministic (same seed → same output) and returns 365 rows per coin. Run with `pytest tests/`.

### `requirements.txt`
- Pin the minimum needed: `pandas`, `numpy`, `matplotlib`, `streamlit`, `requests`, `pytest`. No version pins stricter than needed for reproducibility; record the versions actually used in `data/README.md` or the README.

### `.gitignore`
- `__pycache__/`, `.venv/`, `venv/`, `.streamlit/secrets.toml`, `*.key`, `.env`, `*.log`. Do **not** ignore `data/` (the small CSVs/JSONs are part of the deliverable).

### `LICENSE`
- MIT, copyright holder "Victor" (portfolio owner), year 2026.

---

## 7. Charts (minimum 2 labelled charts — target 4 + summary table)

| # | File | Question | Type |
|---|---|---|---|
| 1 | `01_price_indexed.png` | Momentum | Line: price indexed to 100, BTC vs ETH (+ SOL) |
| 2 | `02_rolling_volatility.png` | Volatility | Line: 30d rolling annualised volatility |
| 3 | `03_drawdown.png` | Drawdown | Line/area: drawdown from peak (%) |
| 4 | `04_relative_volume.png` | Liquidity | Line: relative volume (volume / 30d mean) |
| 5 | `05_summary_table.png` (optional) | All | Summary table of the six metrics per coin |

The Streamlit app shows views 1–4 interactively; the PNGs are the static, README-ready versions.

---

## 8. Success criteria checklist (from the roadmap — all must pass)

- [ ] Problem statement + audience/decision-maker written (README §1–2; this plan §1–2).
- [ ] Data provenance documented: source, endpoint, window, fetch date, keyless/Demo-key outcome, row counts (`data/README.md`).
- [ ] 2+ labelled charts produced (target 4 + summary table; every chart titled, axes labelled with units, source noted).
- [ ] 3 findings + 1 actionable recommendation in `outputs/insights_summary.md` (no investment advice).
- [ ] README with setup instructions, sample outputs (embedded charts + dashboard screenshot), and limitations.
- [ ] No credentials in the repo (no API key, no `.env`, no secrets file); no huge files committed.
- [ ] **One metric manually validated:** pick one (recommended: max drawdown for BTC) and verify it by hand — e.g. in the notebook, print the peak price/date, the trough price/date, and compute `(trough / peak − 1)` independently of `compute_metrics`, and record the matching values in `data/README.md` and `insights_summary.md`. If they disagree, fix the pipeline, don't adjust the hand check.
- [ ] Pipeline runs end-to-end from a clean checkout: `pip install -r requirements.txt` → `python src/data_pipeline.py` → `streamlit run src/app.py` renders without errors.
- [ ] Notebook runs top-to-bottom without errors.

---

## 9. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| CoinGecko `/market_chart` now requires a Demo key (401/403) | Medium — one unverified third-party claim | Test no-key first (§4.3); Demo-key fallback via `COINGECKO_DEMO_API_KEY` env var only; record outcome in `data/README.md` |
| Rate limit 429 | Low (3 calls, ≥5 s spacing) | One retry after 60 s, then stop; fall back to cache/synthetic (§4.4) |
| API unreachable / network block | Low | Cached `data/raw/` first, then deterministic synthetic data, clearly labelled; re-fetch before publishing |
| `market_chart/range` behaves differently from `days=365` | Low | Fall back to `days=365`; log which endpoint was used; verify row counts (~365) and date coverage |
| Streamlit app fails to render | Low | Smoke test: run `streamlit run src/app.py`, screenshot it, fix before calling the day done; app reads only local CSVs so API state can't break it |
| Synthetic data mistaken for real | Medium impact | Labelling on every chart + app banner + README + `data/README.md`; never publish synthetic as real |
| Credential leak | Low impact if guarded | No key in code, no `.env` in repo, `.gitignore` covers secrets; key only via env var |

---

## 10. Build order (coder's sequence)

1. `src/data_pipeline.py` — fetch (test order §4.3) → clean → metrics → save. Run it; inspect `data/processed/*.csv` row counts and date ranges.
2. `data/README.md` — log provenance + the manual metric validation (§8).
3. `notebooks/analysis.ipynb` — reproduce metrics, draft charts, write the findings.
4. `outputs/charts/*.png` — finalise the four charts from the notebook.
5. `outputs/insights_summary.md` — 3 findings + 1 recommendation, with numbers.
6. `src/app.py` — Streamlit dashboard (reads processed CSVs only); screenshot to `screenshots/dashboard.png`.
7. `tests/test_pipeline.py` — smoke tests; run `pytest tests/`.
8. `README.md`, `requirements.txt`, `.gitignore`, `LICENSE` (MIT) — polish last, README embeds the charts + screenshot.
9. Final pass against the §8 checklist; fix gaps before declaring Day 1 done.

## 11. Token-optimisation note (for the coder)

- **Reuse this plan + `research_brief.md`. Do not run extra web searches.** All endpoints, parameters, rate limits, metric definitions, and fallback parameters are already verified and written down here.
- Do not re-verify the API docs. The only live check allowed is the fetch itself (§4.3 test order) — its result goes in `data/README.md`.
- If a step is ambiguous, prefer the simplest interpretation that satisfies the §8 checklist, note the choice in `data/README.md`, and move on. Do not go searching for a "better" approach.
- Keep dependencies minimal (`requirements.txt` §6) and reuse the processed CSVs everywhere — notebook, charts, and app all read the same two files.
