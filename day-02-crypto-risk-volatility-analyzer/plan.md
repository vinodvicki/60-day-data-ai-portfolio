# Day 02 — Crypto Risk & Volatility Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-06) + this plan. **If brief and
plan disagree, the plan wins and the difference is noted in §11.** The coder
must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 02 | Crypto Risk & Volatility Analyzer —
Problem / analysis: Compare drawdowns, rolling volatility, correlations, and
risk-adjusted historical returns to assess portfolio exposure. GitHub
deliverable: Risk comparison dashboard and plain-language risk notes."

| Item | Value |
|---|---|
| Window | 2025-11-06 → 2026-11-06 (365-day span, inclusive of both endpoint dates) |
| Coins | Bitcoin (BTC, slug `bitcoin`), Ethereum (ETH, slug `ethereum`), Solana (SOL, slug `solana`) |
| Source | CoinGecko public API, no key required (see §3) |
| Expected rows | **366 daily observations per coin, 1,098 rows total** in the processed daily frame (Day 1 precedent, window shifted one day — the coder must verify the actual row count and report it; do not assume it) |
| Scope | Descriptive, historical risk analysis only. **No buy/sell recommendation, no price prediction, no investment advice.** Past volatility and drawdowns do not predict future risk. |

## 1. Problem statement + audience

**Problem.** A holder of Bitcoin, Ethereum and Solana knows the prices went up
and down over the past year, but not how much risk each coin actually carried:
how far each one fell from its peak and how long it took to climb back, how
jumpy its day-to-day moves were, whether the three coins tended to fall
together (so holding all three gave little protection), and how much return
each delivered for each unit of risk taken. Day 1 described *what happened* to
prices; Day 2 measures *how risky it was to hold them*.

**Audience / decision-maker.** A non-expert investor (or prospective holder)
assessing portfolio exposure — someone who owns, or is considering owning,
one or more of BTC / ETH / SOL and wants a plain-language answer to "how bad
could a bad stretch get, and did the return justify the ride?" They are not a
quantitative analyst: every metric in the dashboard, notebook and notes must
be explained in plain words with its number attached, and nothing may read as
investment advice. The dashboard is the decision aid; `outputs/insights_summary.md`
is the plain-language risk notes that go with it.

## 2. Research questions (risk-focused)

1. **Drawdown — how far did each coin fall from its peak, and did it recover?**
   Max drawdown, current drawdown, peak-to-trough days, recovery status/days,
   and longest underwater period, per coin. Which coin fell furthest, and
   which was still furthest below its peak on 2026-11-06?
2. **Volatility — how jumpy were day-to-day moves, and when was each coin at its jumpiest?**
   Rolling 30-day annualised volatility per coin (mean, median, maximum, and
   when the maximum occurred). Was one coin consistently calmer than the others?
3. **Correlation — did the coins fall together?** Pearson correlation of daily
   returns, pairwise (BTC–ETH, BTC–SOL, ETH–SOL), full window and latest 90
   days. Does holding all three coins diversify risk, or do they move as one?
4. **Risk-adjusted return — how much return per unit of risk?** Annualised
   Sharpe and Sortino ratios (0% risk-free rate) per coin. Did the coin with
   the highest total return also deliver the best return per unit of risk?
5. **Tail risk — how bad was a bad day?** Historical one-day VaR 95% and CVaR
   95% per coin. On a typical bad day, how much could a holder expect to lose,
   and how much worse was the average loss on the very worst 5% of days?
6. **Exposure summary — which coin carried the most risk overall?** Combining
   drawdown, volatility, correlation and tail risk: rank the three coins by
   risk carried over the window and state, in plain language, what that means
   for someone holding all three.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

- **Base URL (public, no key required):** `https://api.coingecko.com/api/v3`
- **Primary endpoint — exact date range (preferred for reproducibility, same as Day 1):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
GET https://api.coingecko.com/api/v3/coins/solana/market_chart/range?vs_currency=usd&from=1762387200&to=1793923200
```

`from = 1762387200` (2025-11-06 00:00 UTC), `to = 1793923200` (2026-11-06 00:00 UTC),
Unix seconds. Coin IDs are slugs (`bitcoin`, `ethereum`, `solana`), not tickers.
- **Fallback endpoint — rolling window (use only if `/range` fails):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=365
```

- **`interval` parameter — do NOT pass it.** Granularity is automatic when
  `interval` is omitted (>90 days → daily, 00:00 UTC). Passing
  `interval=daily` is unnecessary and is not a documented public-API parameter
  value — omit it, exactly as Day 1 did.
- **Optional sanity-check endpoint (current price):**
  `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true`

Each call returns JSON with three arrays of `[timestamp, value]` pairs:
`prices` (`[timestamp_ms, price]`, USD), `market_caps` (USD),
`total_volumes` (USD, 24h trading volume). Timestamps are milliseconds since
Unix epoch (UTC); all three arrays share the same timestamps. Merge on
timestamp into one daily frame with columns `date, coin, price, market_cap,
volume` (date = YYYY-MM-DD, UTC). Day 2 needs `price` for every metric;
`market_cap` and `volume` are kept for provenance/context but no volume metric
is required. `market_chart` returns **close prices only** — no open/high/low;
no intraday or OHLC metric is in scope.

### 3.2 Fetch rules

- **Only 3 calls** (one per coin). **≥5 seconds between calls, one retry after
  60 s on 429, then stop and fall back** to cached/synthetic data (§3.5).
  Never hammer the API. Official public-API limit: **5–15 calls/minute**;
  HTTP 429 is the signal (response carries a `Retry-After` header).
- **No-key first.** Day 1 proved the no-key call returns HTTP 200 for all
  three coins; the coder must still test the no-key call first and report the
  actual HTTP status per coin.
- **Demo-key fallback (kept, not required):** optional CoinGecko Demo key read
  only from the `COINGECKO_DEMO_API_KEY` **environment variable, never
  hard-coded**, sent as header `x-cg-demo-api-key`, used only if the no-key
  call returns 401/403. No key is stored anywhere in the repo. No `.env` file,
  no key in code, no key in any committed file.
- **Researcher live check (2026-11-06, 13:57 UTC):** `GET
  https://api.coingecko.com/api/v3/ping` returned **HTTP 200** in 1.66 s with
  body `{"gecko_says":"(V3) To the Moon!"}`. No full dataset was fetched by
  the researcher; the live fetch is the coder's job.

### 3.3 Data provenance

- `data/README.md` (coder writes it) records: provider, endpoint used, window,
  access date, keyless vs key, row counts per coin, and the licence/attribution
  note (§3.4). `data/processed/data_source.json` records `source` (`"live"` or
  `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null` for
  live data, `42` for synthetic), plus window and coins.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under
  1 MB each, under 5 MB per day folder — because the raw files are the
  provenance record. **`.gitignore` must NOT exclude `data/`.** Anything larger
  must be `.gitignore`d and regenerated by the pipeline.
- **Day 1 numbers are NOT Day 2 findings.** Day 1 verified (window
  2025-11-05 → 2026-11-05): BTC max drawdown −44.7237% (peak $105,951.50 on
  2025-11-11 → trough $58,566.09 on 2026-07-01), BTC–ETH full-window
  correlation 0.906 (0.890 latest 90d). Day 2's window is shifted one day
  later, so every metric must be recomputed from Day 2's own data — do not
  copy Day 1's figures into Day 2's outputs.

### 3.4 Licence / attribution

- CoinGecko data is free for use via the public API; **CoinGecko requires
  attribution** (API Terms Clause 3). Include on the dashboard and in the repo
  README, legible, size 10+: **"Powered by CoinGecko"** with a link to
  coingecko.com.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched
  series locally for the project only.
- Dashboard and notes must carry the disclaimer: *"Educational analysis only —
  not investment advice."*
- Code in this repo is MIT (see `LICENSE`); CoinGecko data is under separate
  CoinGecko terms, not MIT. **Unresolved licensing tension (carried from Day 1,
  Stage 2):** CoinGecko API Terms Clause 6 bars selling, renting, leasing,
  sub-licensing, re-distributing or syndicating API access without an executed
  agreement; the Demo (free) plan does not include commercial rights, and
  attribution alone does not grant them. CoinGecko support defines
  redistribution as providing data / API access for others to retrieve and use
  beyond viewing it in the product, and says cached or reformatted data is not
  automatically exempt. However, **no CoinGecko page found states explicitly
  whether committing verbatim raw API JSON to a public GitHub repo counts as
  redistribution**, so this is unresolved and no legal certainty is claimed.
  Day 1 kept the raw JSONs committed as the provenance record; Day 2 follows
  the same rule and states the tension honestly in `data/README.md`.
- **No copying code or tutorials from the web.** All code is Victor's own
  original work, written from the brief and this plan.

### 3.5 Synthetic fallback rules (if the API is unreachable)

If all requests fail (429 loop, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful fetch if one exists (`data/raw/`).
2. Otherwise generate a **clearly labelled synthetic dataset** for development
   only, using the Day 1 parameters verbatim so results stay comparable:
   geometric Brownian motion, **seed 42** (deterministic), BTC daily drift
   0.0008 σ 0.035; ETH drift 0.0006 σ 0.045; SOL drift 0.0005 σ 0.06;
   365 daily points from **2025-11-06**; starting prices BTC $100,000 /
   ETH $3,500 / SOL $180; volumes as log-normal noise around each coin's
   typical daily volume. Mark every chart, the app and the README
   **"SYNTHETIC DATA — API unavailable on 2026-11-06"** and re-fetch real
   data before publishing.
3. Synthetic output goes to `data/raw/{coin}_market_chart_synthetic.json`
   **only** — it must never overwrite the live cache
   `data/raw/{coin}_market_chart.json`. `data/processed/data_source.json`
   records `"synthetic": true` **and** `"seed": 42` when synthetic is used
   (`"seed": null` for live data). Synthetic files are git-ignored
   (`data/raw/*_synthetic.json` in `.gitignore`); live `data/raw/*.json` are
   committed.
4. Never present synthetic data as real CoinGecko data.
   `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
   committed cache with no network and never generates synthetic data.

## 4. KPI / metric definitions (copied verbatim from the brief — do not redefine)

All metrics are computed on the daily, date-aligned frame, per coin, over the
window 2025-11-06 → 2026-11-06. Use **simple (arithmetic) daily returns**
throughout — not log returns — so every number in the dashboard, notebook and
notes is on the same basis. All returns are in decimal (e.g. −0.02 = −2%);
present them as percentages in the dashboard.

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
| 10 | **Historical CVaR 95% (daily)** | Mean of the daily returns at or below VaR: `CVaR_95 = mean(r_t \| r_t ≤ VaR_95)`. Always ≤ VaR (a larger expected loss). Report alongside VaR as "average loss on the worst 5% of days". |

**Derived summary table (per coin, for the dashboard + notes):** total return over
the window (`price_last / price_first − 1`), max drawdown, current drawdown,
peak-to-trough days + recovery status, mean/median/max 30-day annualised
volatility, full-window Sharpe, Sortino, daily VaR 95%, daily CVaR 95%. Plus the
correlation matrix (full window + latest 90d).

**Plain-language risk notes (required):** `outputs/insights_summary.md` must
explain, for a non-expert reader, in plain words: what a drawdown means ("how
far the price fell from its highest point and how long it took to climb
back"), what volatility means ("how jumpy day-to-day moves were"), what
correlation means ("whether the coins tended to fall together — high
correlation means little protection from holding more than one"), what
Sharpe/Sortino mean ("how much return you got for each unit of risk — higher
is better, but only on past data"), and what VaR/CVaR mean ("on a typical bad
day you could expect to lose about X%; on the very worst days the average loss
was Y%"). Every plain-language claim must cite the matching number from the
summary table. No investment advice.

**Conventions the coder must not re-decide:** simple (not log) daily returns;
annualisation × √365 (not √252); risk-free rate 0% for Sharpe/Sortino; VaR/CVaR
are one-day historical figures on daily returns (5th percentile / mean of the
tail). If any of these is unworkable, send it back to the planner with the
exact point — do not silently substitute a different convention.

## 5. Exact file tree (mirror Day 1's shape)

```
day-02-crypto-risk-volatility-analyzer/
├── README.md
├── LICENSE                     # MIT (scaffolded; keep as-is)
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── research_brief.md
├── plan.md                     # this file
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── bitcoin_market_chart.json
│   │   ├── ethereum_market_chart.json
│   │   └── solana_market_chart.json
│   │   └── *_market_chart_synthetic.json   # only if fallback used; git-ignored, never committed
│   └── processed/
│       ├── crypto_daily.csv          # 1,098 rows expected (366/coin): date, coin, price, market_cap, volume, daily_return, drawdown, vol_30d_ann
│       ├── crypto_risk_summary.csv   # 3 rows (one per coin): total return, max/current drawdown, peak/trough dates, peak-to-trough + recovery, longest underwater, mean/median/max vol_30d, Sharpe, Sortino, VaR 95%, CVaR 95%
│       ├── crypto_correlations.csv   # pairwise rows: BTC–ETH, BTC–SOL, ETH–SOL × full-window + latest-90d (or 3×3 matrix + 90d columns — coder picks one shape and documents it)
│       └── data_source.json          # source, generated_at_utc, synthetic, seed (null live / 42 synthetic), window, coins
├── notebooks/
│   └── analysis.ipynb          # executes end-to-end offline via nbconvert
├── src/
│   ├── data_pipeline.py        # fetch, clean, metrics, synthetic fallback, save outputs
│   ├── risk_metrics.py         # pure metric functions (see §6)
│   ├── make_charts.py          # regenerates exactly the 4 PNGs in §7, offline from committed CSVs
│   └── app.py                  # Streamlit risk-comparison dashboard
├── outputs/
│   ├── insights_summary.md     # plain-language risk notes + 1 actionable recommendation
│   └── charts/
│       ├── 01_drawdown.png
│       ├── 02_rolling_volatility.png
│       ├── 03_correlation_heatmap.png
│       └── 04_risk_adjusted_returns_var.png
├── screenshots/
│   └── dashboard.png           # REAL capture of the running app (see §6)
└── tests/
    └── test_pipeline.py        # pytest, offline, ≥7 tests (see §6)
```

Build only what this tree lists. No extra files, no extra charts, no extra
dependencies. (Day 1's `publish_checklist.md` / `test_report.md` are produced
by later roles, not by the coder; the coder must not pre-create them.)

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `README.md` | Problem + audience (§1), dataset summary (source, endpoint, window, access date, row counts, licence note), tools, method (metric list + 0% risk-free + √365 conventions), key insights (filled with real numbers after the run), visuals (the 4 charts embedded), how to run, limitations, "Powered by CoinGecko" attribution + "Educational analysis only — not investment advice." disclaimer. |
| `data/README.md` | Provenance (§3.3): provider, endpoint, window, access date, keyless vs key, row counts per coin, licence/attribution note + unresolved redistribution tension stated honestly, commit rule, one manually validated metric (by hand, with the numbers), versions used for this build. |
| `data/raw/*.json` | Verbatim CoinGecko `/market_chart/range` responses, one per coin. Committed (small, <1 MB each). Never overwritten by synthetic data. |
| `data/processed/crypto_daily.csv` | Daily frame, 1,098 rows expected: `date, coin, price, market_cap, volume, daily_return, drawdown, vol_30d_ann`. First daily_return per coin NaN; first 29 vol_30d_ann per coin NaN. |
| `data/processed/crypto_risk_summary.csv` | 3 rows, one per coin, with every field in §4's derived summary table. This file is the single source of truth for every number in the README, dashboard, notebook and notes — all four must agree with it. |
| `data/processed/crypto_correlations.csv` | Pairwise correlations: BTC–ETH, BTC–SOL, ETH–SOL, full window and latest 90d. |
| `data/processed/data_source.json` | `source`, `generated_at_utc`, `synthetic` (bool), `seed` (`null` live / `42` synthetic), window, coins. |
| `src/data_pipeline.py` | Fetch (no-key first, Demo-key env fallback, ≥5 s spacing, one 60 s retry on 429, then fallback), clean/merge into the daily frame, call `risk_metrics` functions, `generate_synthetic(seed=42)`, `--offline` / `--use-cache` mode (runs from committed cache, no network, never generates synthetic data), `save_outputs()` writing raw JSONs + processed CSVs + `data_source.json`. Mirror Day 1's function shapes (`fetch_coin_chart`, `fetch_all_coins`, `clean_chart`, `save_outputs`, `generate_synthetic`, `_load_cache`, `main`) so the tester can reuse the Day 1 test patterns. |
| `src/risk_metrics.py` | Pure, testable metric functions, no I/O, no network: `daily_returns(prices)`, `drawdown_series(prices)` + `max_drawdown_info(...)` (max drawdown, peak/trough dates, peak-to-trough days, recovery days/status, longest underwater period), `rolling_volatility(returns, window=30)` (annualised × √365, ddof=1), `return_correlations(returns_df)` (full window + latest 90d), `sharpe_ratio(returns)` and `sortino_ratio(returns)` (0% risk-free, × √365), `var_cvar_95(returns)` (5th percentile + mean of the tail). Each function takes plain Series/DataFrames and returns plain values — the notebook and `app.py` import them, never re-implement them. |
| `src/make_charts.py` | `python -m src.make_charts` regenerates **exactly the 4 PNGs in §7** in `outputs/charts/`, offline from the committed processed CSVs only (no network, no API). Every chart: title, labelled axes with units, legend where needed, source note ("Source: CoinGecko" or "SYNTHETIC DATA — API unavailable on 2026-11-06" when synthetic), readable at dashboard size. Must not create extra PNGs. |
| `src/app.py` | Streamlit risk-comparison dashboard: coin multi-select (default all three), summary risk table (the §4 derived table), the 4 charts (or their data rendered natively), plain-language explainer for each metric next to its number, 0% risk-free assumption stated, "Powered by CoinGecko" attribution (legible, size 10+) + "Educational analysis only — not investment advice." disclaimer, synthetic banner if `data_source.json` says synthetic. Must not crash on edge cases — Day 1 lesson (b): the `idxmin`/`IndexError` bug was caught only by rendering the app, so sort/reset indexes before any positional lookup. |
| `notebooks/analysis.ipynb` | Full analysis top-to-bottom, offline: load processed CSVs, recompute the summary table via `risk_metrics`, reproduce the 4 charts, answer each §2 question with numbers. Resolve the project root from the notebook file's own location via `_find_root()` (check for `data/processed/crypto_daily.csv` from the notebook's directory upward); **never from `Path.cwd()` alone** — Day 1 lesson (e). A copy executed outside the project must fail with a clear `FileNotFoundError`. Must execute end-to-end offline via nbconvert (CI runs it). |
| `tests/test_pipeline.py` | pytest, offline, **≥7 tests** (target 10–14, mirroring Day 1's 14). Must cover at minimum: (1) drawdown formula on a hand-computed series (peak/trough/duration); (2) rolling-volatility annualisation (√365, ddof=1, first 29 NaN); (3) Sharpe/Sortino on a known series (0% risk-free); (4) VaR/CVaR 95% (5th percentile + tail mean, CVaR ≤ VaR); (5) correlation values on constructed series (perfect +1 / known value, full + 90d windows); (6) synthetic generation deterministic with seed 42 and 365 points from 2025-11-06; (7) synthetic never overwrites the live cache and `*_synthetic.json` does not satisfy the cache check; (8) `--offline`/`--use-cache` runs without network; (9) committed CSVs match the published findings in README/insights (recompute one metric from the CSVs); (10) notebook `_find_root()` resolves correctly; (11) "Powered by CoinGecko" attribution present in app + charts/README. Replace the scaffold `tests/test_smoke.py` (delete it — do not keep both test files). |
| `outputs/insights_summary.md` | Plain-language risk notes (§4): one finding per §2 question (each citing its number from `crypto_risk_summary.csv` / `crypto_correlations.csv` and its chart), **one actionable recommendation** (an analytical next step, e.g. what to monitor or check next — never investment advice), limitations. |
| `outputs/charts/*.png` | Exactly 4 PNGs (§7), regenerated by `src/make_charts.py`. No extra PNGs in this folder — CI asserts the count is exactly 4. |
| `screenshots/dashboard.png` | **REAL capture of the running Streamlit app** (full page), taken during the coder's smoke test — not a composite of the static charts. Day 1 lesson: the composite screenshot had to be replaced by a real capture; do it right first time. If a real capture is genuinely impossible, flag it explicitly as a composite in the handoff and in the README caption — do not silently pass a composite off as a screenshot. |
| `requirements.txt` | Pinned exact `==` versions, verified in the build venv (Python 3.12): `pandas`, `numpy`, `matplotlib`, `plotly`, `streamlit`, `requests`, `pytest`, **`jupyter==1.1.1` + `nbformat==5.11.1`** (required — CI executes the notebook via nbconvert). No new runtime dependency without a plan change. Pin at optimizer time from the venv that actually ran, as Day 1 did; the scaffold's Day 1 pins are a starting point, not verified Day 2 pins. |
| `pyproject.toml` | Ruff + black settings mirroring Day 1 exactly: `[tool.ruff] line-length = 88, target-version = "py312"`, `[tool.black] line-length = 88`, `[tool.pytest.ini_options] testpaths = ["tests"]`. Dev tools (ruff 0.17.4, black 26.10.1) are pinned once in the portfolio-root `requirements-dev.txt`, shared by all days. |
| `.gitignore` | Mirror Day 1 exactly: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, plus `data/raw/*_synthetic.json` (synthetic fallback output is never committed; live `data/raw/*.json` IS committed). **Must NOT exclude `data/`** — diff `.gitignore` against this plan before sign-off (Day 1 lesson d). |
| `LICENSE` | MIT, keep as scaffolded. |

### Coder environment (Day 1 lessons applied)

- Create `.venv` with the pinned deps installed and hand it off working —
  the tester provisions nothing and must never install the project's own deps
  from scratch; if the venv is missing the tester reports "blocked: no venv".
- Run `black` + `ruff` **before** handoff (Day 1 lesson: lint left to the end
  cost a full fix cycle). `black --check` + `ruff check` must pass on `src/`
  and `tests/`.
- Capture the real `screenshots/dashboard.png` during the coder's own smoke
  test (fresh port 8502+, never assume 8501 is free; kill the server and
  verify the port is free afterwards — Day 1 lesson c).
- One writer per file; build only what this plan lists; no extra web searches.

## 7. Charts (exactly 4 — CI asserts the count)

`python -m src.make_charts` regenerates exactly these 4 PNGs, offline from the
committed processed CSVs. All 4 must be well-labelled (title, axes with units,
legend, source note) and legible at dashboard size.

| # | Filename | Content |
|---|---|---|
| 1 | `01_drawdown.png` | **Drawdown chart** — drawdown (%) over time for BTC, ETH, SOL on one axis (0% line marked), so the depth and duration of each coin's worst fall are visible at a glance. Annotate each coin's max drawdown (value + trough date). |
| 2 | `02_rolling_volatility.png` | **Rolling-volatility chart** — 30-day annualised volatility (%) over time for all three coins on one axis. Annotate each coin's maximum vol_30d (value + date). |
| 3 | `03_correlation_heatmap.png` | **Correlation heatmap** — 3×3 full-window Pearson correlation matrix of daily returns, values labelled in every cell, colour scale fixed −1 to +1. Latest-90d pairwise values shown as text alongside (or in the caption). |
| 4 | `04_risk_adjusted_returns_var.png` | **Risk-adjusted returns / VaR comparison chart** — grouped bars per coin: total return, Sharpe and Sortino (twin axis or normalised panel — label clearly, do not plot unlike units on one axis without labelling), plus a VaR 95% / CVaR 95% panel (daily loss %, negative bars, CVaR ≤ VaR visible). One figure, two clearly labelled panels. |

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoint, collection date, licence/attribution ("Powered by CoinGecko"), row counts — in `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (fetch → clean → metrics → charts, with `--offline` mode) + KPI definitions (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 2 produces exactly 4 (§7), plus a functional evaluation report: the Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding per §2 question) + **one actionable recommendation** (analytical next step, never investment advice)
- [ ] README with setup instructions, sample outputs (summary table + chart thumbnails), and limitations
- [ ] No credentials / private records in the repo; no huge raw files committed (raw JSONs <1 MB each, <5 MB per day folder); `.gitignore` does not exclude `data/`
- [ ] One metric manually validated by hand and recorded in `data/README.md` (e.g. recompute one coin's max drawdown from the CSV: peak price/date → trough price/date → percentage, matching to ≤1e-9 as Day 1 did)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r requirements.txt`, `python -m src.data_pipeline --offline`, `python -m src.make_charts`, `pytest tests/ -q`)
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert, with `_find_root()`)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

Per AGENTS.md / Day 1 retrospective, the coder hands off only when **all** of
the following hold; the tester verifies in the coder's venv and provisions nothing:

1. `.venv` exists with pinned deps installed (requirements.txt matches the venv
   that actually ran).
2. `black --check src tests` and `ruff check src tests` pass (exit 0).
3. `pytest tests/ -q` passes (≥7 tests, offline).
4. `.gitignore` matches §6 (in particular: does NOT exclude `data/`; excludes
   only `data/raw/*_synthetic.json`).
5. `screenshots/dashboard.png` is a REAL capture of the running app (or
   explicitly flagged as a composite in the handoff + README caption).
6. `python -m src.make_charts` regenerates exactly 4 PNGs in
   `outputs/charts/` (offline, from committed CSVs); notebook executes
   end-to-end offline via nbconvert.
7. Every number in README / dashboard / notebook / insights matches
   `data/processed/crypto_risk_summary.csv` and `crypto_correlations.csv`.

**Tester smoke gate (mandatory, for the tester's reference):** start
`streamlit run src/app.py` on a fresh port (8502 or higher, never 8501);
confirm HTTP 200 on `/` and on `/_stcore/health` with a clean server log;
capture a full-page screenshot to `screenshots/dashboard.png`; kill the server
and verify the port is free; record port, HTTP statuses and screenshot size in
`test_report.md`.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| CoinGecko 429 / outage on fetch day | ≥5 s spacing, one 60 s retry, then cached → synthetic (§3.5); synthetic is labelled everywhere and re-fetched before publishing. |
| `interval=daily` passed by habit | Brief §1 forbids it; this plan repeats the ban; tester checks the fetch code. |
| Log returns / √252 / non-zero risk-free substituted by habit | §4 formulas are verbatim from the brief; tester validates Sharpe/Sortino/VaR against hand-computed values. |
| Day 1 figures copied into Day 2 outputs | §3.3 forbids it; tester recomputes one metric from Day 2's own CSVs. |
| Dashboard crash invisible to pytest (Day 1 lesson b) | Mandatory Streamlit smoke gate (§9) + real screenshot. |
| `.gitignore` silently dropping raw data (Day 1 lesson d) | §6 diff check at coder handoff; publisher frozen-tree check before push. |
| Screenshot going missing before push (Day 1 lesson) | Treat `screenshots/dashboard.png` as a checked deliverable; verify it exists at every handoff; publisher re-verifies immediately before pushing. |
| Notebook cwd trap (Day 1 lesson e) | `_find_root()` from the notebook file's own location; CI executes it via nbconvert. |
| Chart count drift (extra PNG breaks CI) | `make_charts.py` writes exactly the 4 files in §7 and no others; CI asserts count == 4. |

## 11. Brief-vs-plan differences

**None.** This plan adopts the brief's endpoints, window, metric definitions
(§4, verbatim), synthetic parameters (seed 42, §3.5) and licence notes without
change. Additions made by the plan (not contradictions): the processed-file
names the brief left to the plan (`crypto_daily.csv`,
`crypto_risk_summary.csv`, `crypto_correlations.csv`, `data_source.json`
with a `seed` field), the split of metric code into `src/risk_metrics.py`
(the brief names no module; the pipeline module keeps Day 1's shape), the
exact 4 chart filenames (§7), and the ≥7-test list (§6). If the coder finds
any of these unworkable, it goes back to the planner with the exact point —
the coder does not silently substitute a different convention.

## 12. Build order (coder)

1. `.venv` + pinned deps → 2. `src/risk_metrics.py` (pure functions) →
   3. `src/data_pipeline.py` (fetch → clean → metrics → save; verify 1,098
   rows, report HTTP status per coin) → 4. `pytest` on the metric tests as
   they land → 5. `src/make_charts.py` (exactly 4 PNGs) →
   6. `notebooks/analysis.ipynb` (offline, `_find_root()`) →
   7. `src/app.py` + smoke test + real `screenshots/dashboard.png` →
   8. `README.md`, `data/README.md`, `outputs/insights_summary.md` (numbers
   from the CSVs only) → 9. `black` + `ruff` + full `pytest` + handoff
   checklist (§9).
