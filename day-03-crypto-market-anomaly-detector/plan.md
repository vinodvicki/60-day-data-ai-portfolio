# Day 03 — Crypto Market Anomaly Detector: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Amendment 2026-11-07:** §4.4 evaluation design amended (tester send-back,
D1/D2) — see the "§4.4 amendment" subsection below; detector, thresholds and
targets unchanged. Rework in progress: coder → tester re-verification.
**Source of truth:** `research_brief.md` (2026-11-07) + this plan. **If brief and
plan disagree, the plan wins and the difference is noted in §11.** The coder
must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Flag unusual price-volume patterns with a
baseline or unsupervised anomaly model; do not present anomalies as proven
manipulation. GitHub deliverable: Anomaly timeline, model evaluation, and
signal explanations. Core skills: Python, Pandas, time-series analysis,
Plotly, anomaly detection. Suggested data: CoinGecko public market data;
public historical price/volume series."

| Item | Value |
|---|---|
| Window | 2025-11-07 → 2026-11-07 (365-day span, inclusive of both endpoint dates) |
| Coins | Bitcoin (BTC, slug `bitcoin`), Ethereum (ETH, slug `ethereum`), Solana (SOL, slug `solana`) |
| Source | CoinGecko public API, no key required (see §3) |
| Expected rows | **365 daily observations per coin, ~1,095 rows total** in the processed daily frame (Day 2 precedent, window shifted one day — the coder must verify the actual row count and report it; do not assume it). **~1,005 flaggable rows** after the 30-day warm-up (§4) |
| Scope | Descriptive, historical anomaly analysis only. **No buy/sell recommendation, no price prediction, no investment advice.** Flagged days are statistical outliers in price and volume — **never presented as proven manipulation** (§4.5). |

## 1. Problem statement + audience

**Problem.** A holder of Bitcoin, Ethereum and Solana can see that prices and
volumes moved sharply on some days over the past year, but cannot tell which
days were genuinely unusual and which were just normal crypto noise: a −8%
day in a calm month means something different from a −8% day in a month when
every day moved ±6%, and a price jump with no volume behind it means
something different from the same jump on four times the usual volume. Day 1
described *what happened* to prices and Day 2 measured *how risky it was to
hold them*; Day 3 flags the specific days whose price–volume pattern stood
out from each coin's own recent behaviour, explains each flag in plain
language from the numbers on that day, and checks honestly how well the
detector works — because there is no labelled ground truth for real market
days, the check is done on deliberately injected anomalies plus a
baseline-vs-model comparison (§4.4).

**Audience / decision-maker.** A non-expert holder (or prospective holder)
of BTC / ETH / SOL who wants a plain-language answer to "which days were
actually unusual, why, and how much should I trust the flag?" They are not a
quantitative analyst: every flag in the dashboard, notebook and notes must be
explained in plain words with its numbers attached, and nothing may read as
an accusation of manipulation or as investment advice. The dashboard is the
decision aid; `outputs/insights_summary.md` is the plain-language anomaly
notes and `outputs/anomaly_evaluation.md` is the honest report card on the
detector itself.

## 2. Research questions (anomaly-focused — exactly 3)

1. **Which days were unusual, and why?** For each coin, which post-warm-up
   days were flagged by the rolling z-score baseline rules (R1 return shock,
   R2 volume surge, R3 joint shock) and/or by the Isolation Forest, with what
   severity (High / Medium / Low), and what plain-language explanation does
   each flag carry? Which coin had the most flagged days, and were the flags
   concentrated in particular months or spread across the year?
2. **Do the two methods agree — and where do they disagree?** How many days
   did the baseline rules and the Isolation Forest flag in common, and how
   many did each flag alone (overlap / Jaccard)? Does a day flagged by both
   deserve more confidence than a day flagged by only one, and what does a
   forest-only flag look like in the numbers?
3. **How good is the detector, really?** On ~30 injected anomalies of known
   type (price spike, volume surge, joint shock), what are the precision,
   recall and F1 of each method and of their union (±1-day tolerance), and
   per-type recall — is any pattern type systematically missed? Measured
   against the §4.4 targets, is the detector good enough to trust, and where
   are its blind spots?

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

- **Base URL (public, no key required):** `https://api.coingecko.com/api/v3`
- **Primary endpoint — exact date range (preferred for reproducibility, same as Days 1–2):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1762473600&to=1794009600
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1762473600&to=1794009600
GET https://api.coingecko.com/api/v3/coins/solana/market_chart/range?vs_currency=usd&from=1762473600&to=1794009600
```

`from = 1762473600` (2025-11-07 00:00 UTC), `to = 1794009600` (2026-11-07
00:00 UTC), Unix seconds. These are exactly Day 2's timestamps shifted by
+86,400 s (one day). Coin IDs are slugs (`bitcoin`, `ethereum`, `solana`),
not tickers.
- **Fallback endpoint — rolling window (use only if `/range` fails for a non-429 reason):**

```
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365
GET https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=365
```

- **`interval` parameter — do NOT pass it.** Granularity is automatic when
  `interval` is omitted (>90 days → daily, 00:00 UTC). Passing
  `interval=daily` is unnecessary and is not a documented public-API parameter
  value — omit it, exactly as Days 1–2 did.
- **Optional sanity-check endpoint (current price):**
  `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true&include_market_cap=true`

Each call returns JSON with three arrays of `[timestamp, value]` pairs:
`prices` (`[timestamp_ms, price]`, USD), `market_caps` (USD),
`total_volumes` (USD, 24h trading volume). Timestamps are milliseconds since
Unix epoch (UTC); all three arrays share the same timestamps. Merge on
timestamp into one daily frame with columns `date, coin, price, market_cap,
volume` (date = YYYY-MM-DD, UTC), exactly as Day 2's `clean_chart` did:
drop duplicate timestamps, keep the last row per calendar day (UTC),
assert no NaN prices. `market_chart` returns **close prices only** — no
open/high/low; no intraday or OHLC metric is in scope.

### 3.2 Fetch rules

- **Only 3 calls** (one per coin). **≥5 seconds between calls, one retry after
  60 s on 429, then stop and fall back** to cached/synthetic data (§3.5).
  Never hammer the API. Official public-API limit: **5–15 calls/minute**;
  HTTP 429 is the signal (response carries a `Retry-After` header — honour
  it if present). Timeout: 30 s per request.
- **No-key first.** Days 1–2 proved the no-key call returns HTTP 200 for all
  three coins; the coder must still test the no-key call first and report the
  actual HTTP status per coin.
- **Demo-key fallback (kept, not required):** optional CoinGecko Demo key read
  only from the `COINGECKO_DEMO_API_KEY` **environment variable, never
  hard-coded**, sent as header `x-cg-demo-api-key`, used only if the no-key
  call returns 401/403. Do not retry the no-key call repeatedly on 401/403.
  No key is stored anywhere in the repo. No `.env` file, no key in code, no
  key in any committed file.

### 3.3 Data provenance

- `data/README.md` (coder writes it) records: provider, endpoint used, window,
  access date, keyless vs key, row counts per coin, and the licence/attribution
  note (§3.4). `data/processed/data_source.json` records `source` (`"live"`,
  `"cache"` or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed`
  (`null` for live data, `42` for synthetic), plus window and coins.
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline
  pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s
  `source` field to `"cache"`. Before publishing, the coder/optimizer must
  either **re-run the pipeline live** (restoring `"live"`) or **restore the
  field by hand with the true value and record the correction** in
  `data/README.md`. A published `data_source.json` that says `"cache"` when
  the data was in fact fetched live is a defect; the publisher's frozen-tree
  check (§8) includes verifying this field.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under
  1 MB each, under 5 MB per day folder — because the raw files are the
  provenance record. **`.gitignore` must NOT exclude `data/`.** Anything larger
  must be `.gitignore`d and regenerated by the pipeline.
- **Day 2 numbers are NOT Day 3 findings.** Day 2 verified (window
  2025-11-06 → 2026-11-06, 1,098 rows): max drawdowns BTC −44.72%, ETH
  −56.24%, SOL −62.85%; BTC–ETH full-window correlation 0.908; Sharpe BTC
  −0.49, ETH −0.41, SOL −0.65; VaR 95% BTC −3.38%, ETH −4.67%, SOL −5.29%.
  These are context only — Day 3's window is shifted one day later, so every
  feature, flag and evaluation number must be recomputed from Day 3's own
  data. Do not copy Day 2's figures into Day 3's outputs.
- **Cache reuse note:** Day 1/2 caches cover windows ending 2026-11-05/06,
  **not** Day 3's window ending 2026-11-07. A cache fallback for Day 3 is
  only valid if a Day 3 fetch has previously succeeded and written
  `data/raw/{coin}_market_chart.json` in the Day 3 folder. Do **not** reuse
  Day 1/2 raw JSONs as Day 3 data — the window differs by a day and the
  provenance would be wrong.

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
  CoinGecko terms, not MIT. **Unresolved licensing tension (carried from Days
  1–2, Stage 2):** CoinGecko API Terms Clause 6 bars selling, renting, leasing,
  sub-licensing, re-distributing or syndicating API access without an executed
  agreement; the Demo (free) plan does not include commercial rights, and
  attribution alone does not grant them. CoinGecko support defines
  redistribution as providing data / API access for others to retrieve and use
  beyond viewing it in the product, and says cached or reformatted data is not
  automatically exempt. However, **no CoinGecko page found states explicitly
  whether committing verbatim raw API JSON to a public GitHub repo counts as
  redistribution**, so this is unresolved and no legal certainty is claimed.
  Days 1–2 kept the raw JSONs committed as the provenance record; Day 3
  follows the same rule and states the tension honestly in `data/README.md`.
- **No copying code or tutorials from the web.** All code is Victor's own
  original work, written from the brief and this plan.

### 3.5 Synthetic fallback rules (if the API is unreachable)

If all requests fail (429 loop, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful Day 3 fetch if one exists
   (`data/raw/` in this day folder only — see §3.3 cache note).
2. Otherwise generate a **clearly labelled synthetic dataset** for development
   only, using the Day 1/2 parameters verbatim so results stay comparable:
   geometric Brownian motion, **seed 42** (deterministic), BTC daily drift
   0.0008 σ 0.035; ETH drift 0.0006 σ 0.045; SOL drift 0.0005 σ 0.06;
   365 daily points from **2025-11-07**; starting prices BTC $100,000 /
   ETH $3,500 / SOL $180; typical daily volumes BTC $30bn / ETH $15bn /
   SOL $3bn (log-normal noise σ 0.4 around the typical volume); market cap =
   price × supply (BTC 19.8m / ETH 120.0m / SOL 540.0m). Mark every chart,
   the app and the README **"SYNTHETIC DATA — API unavailable on
   2026-11-07"** and re-fetch real data before publishing.
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
5. **GBM synthetic data has no real anomalies**, so on synthetic data the
   injected-anomaly evaluation (§4.4b) is the *only* meaningful evaluation —
   the "real data" flag rate has no interpretation. State this in the README,
   notebook and `outputs/anomaly_evaluation.md` if the synthetic path is used.

## 4. Anomaly method — feature, rule, model and evaluation definitions (copied verbatim from the brief — do not redefine)

All features are computed on the daily, date-aligned frame, per coin, over the
window 2025-11-07 → 2026-11-07. Use **simple (arithmetic) daily returns**
throughout — not log returns — so every number in the dashboard, notebook and
notes is on the same basis. All returns are in decimal (e.g. −0.02 = −2%);
present them as percentages in the dashboard.

### 4.1 Features (all per coin, on the cleaned daily frame)

| Feature | Definition |
|---|---|
| `daily_return` | `price[t] / price[t-1] − 1` (first day per coin: NaN) |
| `abs_return` | `abs(daily_return)` |
| `volume_ratio` | `volume[t] / mean(volume[t-30 … t-1])` — today's volume vs its own trailing 30-day mean (excludes today, so a spike is not diluted by itself). First 30 days: NaN. |
| `log_volume_ratio` | `log(volume_ratio)` — used for z-scoring, because volume is right-skewed |
| `vol_30d_ann` | 30-day rolling annualised volatility of daily returns, `std(returns[t-29 … t]) × sqrt(365)` (Day 2 definition, reused; first 29 values NaN) |
| `drawdown` | `price[t] / max(price[≤ t]) − 1` (≤ 0; Day 2 definition, reused) |
| `return_z` | `(daily_return − mean(daily_return[t-30 … t-1])) / std(daily_return[t-30 … t-1])` — 30-day trailing window, excluding today |
| `volume_z` | `(log_volume_ratio − mean(log_volume_ratio[t-30 … t-1])) / std(log_volume_ratio[t-30 … t-1])` — same trailing window |
| `vol_regime` | `vol_30d_ann / median(vol_30d_ann)` — whether today sits in a high-volatility regime relative to the coin's own year |

**Trailing (not centred, not full-window) windows are mandatory:** a centred
or full-window z-score leaks future information into "today's" score. The
first 30 days per coin have no z-scores and are excluded from flagging
(warm-up period). Effective evaluation universe: **~1,005 rows** (1,095 minus
~90 warm-up rows), not 1,095.

### 4.2 Baseline rules (deterministic — the comparison standard)

A day is **baseline-flagged** if **any** of the following holds:

- **R1 — return shock:** `|return_z| ≥ 3` (a daily move ≥ 3 trailing standard deviations from the coin's own recent mean).
- **R2 — volume surge:** `volume_z ≥ 3` **and** `volume_ratio ≥ 2` (volume at least double its 30-day average *and* statistically extreme in log terms; the ratio floor stops tiny absolute volumes from tripping the z-rule on quiet days).
- **R3 — joint shock:** `|return_z| ≥ 2` **and** `volume_z ≥ 2` on the same day (a moderate price move *with* a moderate volume surge — the classic "unusual price-volume pattern" the roadmap names).

**Severity tiers for the timeline:** **High** = R1 or R2 with `|z| ≥ 4`, or
R1+R2 together; **Medium** = any single rule at threshold; **Low** = R3 only.

### 4.3 Unsupervised model: Isolation Forest

- **Algorithm:** `sklearn.ensemble.IsolationForest`, `contamination` set from
  the baseline flag rate (see §4.4a — start at the observed baseline rate,
  e.g. ~0.03–0.05, and report the value actually used), `random_state=42`,
  `n_estimators=200`.
- **Input features (per coin, standardised with the coin's own trailing
  statistics — no cross-coin scaling, so a volatile coin does not mask a
  quiet one):** `daily_return`, `abs_return`, `volume_ratio`
  (log-transformed), `vol_30d_ann`, `drawdown`. Five features, all defined
  in §4.1; no new data needed.
- **Output:** `anomaly_score` (decision function, lower = more anomalous)
  and a binary `is_anomaly` from the fitted contamination threshold.
- **Why this combination is defensible:**
  1. The z-score baseline is fully transparent — every flag can be traced to one number on one day, which is what the signal explanations (§4.6) need.
  2. Isolation Forest needs no labels (none exist — see §4.4), handles the non-linear joint behaviour of return + volume + volatility that single-variable rules miss, and is a standard, well-understood unsupervised baseline for this exact problem.
  3. The two methods cross-check each other: a day flagged by both is a high-confidence "unusual pattern"; a day flagged by only one is reported as such, with the reason visible.
  4. Everything is computed from the same three public series (price, volume, market cap) already fetched — no extra API calls, no new data risk.
- **Limits (must be stated in the README and the notebook):**
  - Crypto returns are heavy-tailed and volatility clusters, so a fixed ±3σ rule over-flags in volatile regimes and under-flags in calm ones; the trailing window and the `vol_regime` feature mitigate this but do not remove it.
  - Isolation Forest scores are relative rankings, not probabilities — "anomaly score −0.12" has no absolute meaning outside this dataset.
  - The model cannot distinguish a genuine market event (e.g. an ETF headline, a network upgrade) from a data error or from manipulation. It flags *statistical unusualness only*.
  - 365 days per coin is a small sample for unsupervised learning; results are descriptive, not a production detector.
  - **Ethics guard (roadmap-mandated, §4.5):** anomalies are *never* presented as proven manipulation.

### 4.4 Evaluation

#### The ground-truth problem

**There is no ground-truth manipulation label for real crypto data.** No
public dataset labels which historical days were manipulation, and the
roadmap explicitly forbids presenting anomalies as proven manipulation.
Therefore evaluation is done on **injected anomalies only**, plus a
baseline-vs-model comparison. This must be stated in the README, notebook,
insights summary and evaluation report.

#### (a) Baseline vs model comparison

Report, per coin and overall:

- Number and % of days flagged by the baseline rules (and by each rule R1/R2/R3 separately).
- Number and % flagged by Isolation Forest.
- Overlap: days flagged by both / baseline-only / model-only (a small table or Venn-style count). Report the Jaccard overlap (intersection ÷ union).
- The `contamination` used for the forest, set equal to the baseline flag rate so the two methods flag comparable counts — then any difference is about *which* days, not *how many*.
- Sanity expectation: with ~1,095 rows and a ±3σ-style rule, the baseline should flag roughly **2–5% of days** (of the ~1,005 post-warm-up rows). If it flags <1% or >10%, the thresholds or the window are wrong and the planner/coder must revisit §4.2 before proceeding.

#### (b) Injected-anomaly evaluation (precision/recall-style)

1. Take a **copy** of the cleaned daily frame; never inject into the real data. Keep the real and injected datasets in separate files (`crypto_daily.csv` vs `crypto_daily_injected.csv`).
2. Inject **~30 synthetic anomalies** spread across the three coins and across the year (not clustered in one month), of three types, each with a known date/coin:
   - **Price spike:** multiply one day's price by 1.15 (and the following day's price back down, i.e. a one-day +15% jump and reversal) — tests R1 and the return features.
   - **Volume surge:** multiply one day's volume by 4× with no price change — tests R2 and the volume features.
   - **Joint shock:** one day's price ×1.08 *and* volume ×3 — tests R3 and the forest's joint detection.
   - Record every injection in a small CSV (`injected_anomalies.csv`: date, coin, type, magnitude) — this is the evaluation label set.
3. Run the *identical* baseline + forest pipeline on the injected copy.
4. Report **precision, recall, and F1** for each method (baseline rules, forest, either-method union) against the injected labels, with a tolerance of **±1 day** (an anomaly flagged on the day after an injected price spike counts as detected, because a one-day spike mechanically moves the next day's return too).
5. Report per-type recall (price spikes vs volume surges vs joint shocks) — this shows *which* pattern each method is blind to.

#### What "good" looks like

| Metric | Target |
|---|---|
| Injected-anomaly recall (union of both methods) | **≥ 0.80** (at least 24 of 30 injected anomalies found) |
| Injected-anomaly precision (union) | **≥ 0.50** (at least half of all flags are real injected anomalies — the rest are genuine unusual days in the real data, which is expected, not a failure) |
| Baseline-vs-forest overlap (Jaccard) | **≥ 0.30** (the methods substantially agree; near-zero overlap means one of them is mis-specified) |
| Baseline flag rate on real data | **2–5%** of post-warm-up days (see (a)) |
| Per-type recall | No type below **0.60** — if e.g. volume-only surges are missed, say so explicitly rather than hiding it in the average |

If recall is below target, the correct response is to report the miss and
diagnose (e.g. "volume surges under 3× are invisible to a 30-day trailing z
because volume is noisy") — **not** to tune thresholds until the injected set
passes, which would be overfitting to the coder's own injections. Thresholds
are fixed in this plan before evaluation runs.

### §4.4 amendment (2026-11-07, tester send-back)

**Why.** The tester (`test_report.md`, 2026-11-07) independently recomputed
the §4.4 evaluation and confirmed two misses: **D1** union precision 0.436
(TP 24, FP 31 of 72 flags) vs target ≥ 0.50; **D2** volume-surge per-type
recall 0.50 (5/10) vs target ≥ 0.60. Both misses are defects in the
*evaluation design*, not in the detector: the detector itself is verified
correct (pytest 23/23 from both locations, manual ETH 2026-08-20 `return_z`
diff 2.4e-08, flag set reproduced exactly with symmetric difference 0). This
amendment fixes the measurement; it changes nothing about the detector.

**Defect D2 — the injections were not anomalous.** The old §4.4b planted a
volume surge as 4× the day's *own* volume. On a quiet-volume day that is only
1.5×–2.6× the trailing 30-day mean volume (`volume_z` 1.9–2.8), i.e. below
R2's z ≥ 3 bar — the planted "anomaly" was not anomalous relative to the
coin's own history, so the detector correctly ignored it and recall was
capped by the test design. The same flaw applies in principle to the price
spike: a fixed ×1.15 jump on a day whose trailing volatility is already high
can sit below R1's bar.

**New injection parameters (supersede §4.4b step 2 magnitudes).** All
magnitudes are computed from the trailing 30-day window ending the day
*before* the injection date, per coin (the same windows as §4.1), so every
planted anomaly exceeds its target rule's bar by construction:

- **Price spike (10):** set `price[t]` so the day's simple return equals
  **+4.0 × σ_ret**, where σ_ret is the trailing 30-day std of daily returns
  (excluding today); `price[t+1]` reverts to the un-injected series (one-day
  spike and reversal, as before). Expected `|return_z|` ≈ 4, above R1's ≥ 3
  bar. Record the realised % move and the 4.0σ multiple in
  `injected_anomalies.csv`.
- **Volume surge (10):** set `volume[t]` = **5.0 × mean(volume[t−30 … t−1])**.
  No price change. `volume_ratio` = 5.0 by construction (above R2's ratio
  floor of 2); log(5.0) ≈ 1.61 against the typical log-volume-ratio std of
  ~0.3–0.5 puts `volume_z` ≈ 3–5, above R2's z ≥ 3 bar.
- **Joint shock (10):** set `price[t]` so the day's return equals
  **+3.0 × σ_ret**, and `volume[t]` = **3.0 × mean(volume[t−30 … t−1])**.
  Targets R3's `|return_z|` ≥ 2 and `volume_z` ≥ 2 bars with margin on both
  axes.

Unchanged: n = 30 (10 per type), spread across the three coins and across
the year (not clustered in one month), `seed = 42`, injected copy kept
separate (`crypto_daily_injected.csv`), labels in `injected_anomalies.csv`
(add a `construction` column recording how each anomaly was built, e.g.
`4.0x trailing return std` / `5.0x trailing mean volume` /
`3.0x trailing return std + 3.0x trailing mean volume`).

**Harness self-check (new, mandatory).** After injection,
`inject_anomalies` must assert on the injected frame that each planted
anomaly clears its target rule's bar: price spike `|return_z|` ≥ 3; volume
surge `volume_z` ≥ 3 and `volume_ratio` ≥ 2; joint shock `|return_z|` ≥ 2
and `volume_z` ≥ 2. If any assertion fails, the pipeline fails loudly — a
planted anomaly that is not anomalous relative to history is a harness bug,
not a detector miss, and must never silently enter the evaluation. This
check is a property of the test design; it is not detector tuning.

**Defect D1 — precision counted genuine real days as false positives.** The
old §4.4b step 4 defined FP as any flag not within ±1 day of an injection.
But the injected copy is the real data plus 30 plants: the real window
already contains 54 flagged days (37 baseline, 39 forest, 54 union), so a
flag that is a genuine unusual real day is scored as a false positive by
construction, and precision is capped below 0.50 no matter how good the
detector is.

**New precision rule (supersedes §4.4b step 4's FP definition).** A flag on
the injected run counts as a **true positive** if it matches (same coin, ±1
day) an injected anomaly **OR** a flag the detector also raises on the clean
(uninjected) data — i.e. a member of the committed real-data flag set in
`anomaly_timeline.csv` (54 flags). A flag counts as a **false positive**
only if it matches neither. Recall is unchanged (matched injections ÷ 30).
Rationale: the injected copy contains the real data, so reproducing a
clean-data flag is the detector doing its real job, not an error; only a flag
that appears *because of* the injection process and matches nothing real is
a genuine false alarm. The clean-run flag set is already committed, so no
new run is needed to define it; the ±1-day tolerance applies to both matches
(an injection can shift a neighbouring real flag by a day through the
trailing window).

This supersedes the "What 'good' looks like" precision parenthetical: the
rest are no longer "genuine unusual days counted as false positives" — under
the amended rule they count as true positives, and precision ≥ 0.50 now means
at least half of all flags are either injected anomalies or genuine unusual
days the detector also flags on clean data.

**Targets: UNCHANGED.** Union recall ≥ 0.80, union precision ≥ 0.50,
Jaccard ≥ 0.30, per-type recall ≥ 0.60, baseline flag rate 2–5% all stand.
The targets were never the problem — the measurement was — so there is no
principled reason to move any of them. If the amended evaluation still misses
a target, the miss is reported and diagnosed as before; it is not tuned away.

**FORBIDDEN in the rework.** No change to R1–R3 thresholds (§4.2), no change
to the Isolation Forest (features, `random_state=42`, `n_estimators=200`,
contamination rule — contamination stays equal to each run's own baseline
flag rate), no re-tuning of anything after seeing the new numbers.
`compute_features`, `apply_rules`, `fit_isolation_forest`, `build_timeline`
and `generate_explanation` in `src/anomaly.py` stay exactly as-is; only
`inject_anomalies` (new magnitudes + self-check) and `evaluate` (new
precision rule) change. §6 function names and signatures are unchanged.

**Coder rework (exact scope).**

1. `src/anomaly.py`: rewrite `inject_anomalies` to the new magnitudes +
   self-check; rewrite the precision/FP part of `evaluate` to the new rule
   (recall, F1 and Jaccard definitions unchanged). Update the
   injection/evaluation tests in `tests/test_pipeline.py` to the new spec
   (tests of rules, forest, features and explanations are untouched).
2. Re-run the pipeline offline from the committed cache
   (`python -m src.data_pipeline --offline`) — no new CoinGecko fetch;
   regenerate `crypto_daily_injected.csv` and `injected_anomalies.csv`.
   Restore `data_source.json` `source` to `"live"` afterwards per §3.3 (the
   offline run flips it to `"cache"`).
3. Regenerate chart 04 (`python -m src.make_charts` — it rewrites all 4
   PNGs, but only 04 changes; verify 01–03 are byte-identical).
4. Update `outputs/anomaly_evaluation.md` (new numbers, new method
   description, pass/fail vs the unchanged targets) and any affected numbers
   in `outputs/insights_summary.md` and `README.md`. Re-execute the notebook
   so its stored outputs match.
5. Re-run `pytest` from the repo root AND from inside the day folder;
   `black --check` + `ruff check` clean. No other files change.

**Tester re-verification.** Recompute all five §4.4 targets independently
from the regenerated CSVs (same method as `test_report.md` §7 — own code, no
import of `src/anomaly`); verify the harness self-check exists and that every
planted anomaly's statistics clear its bar; re-run pytest from both
locations + lint; re-run the Streamlit smoke gate with a fresh screenshot
(chart 04 changed). Append a dated re-verification section to
`test_report.md`; the original D1/D2 findings stay on record.

**Cosmetics C1/C2 — optimizer fixes, NOT coder work.** C1: chart 3 subtitle
"§4.2" reads as "($4.2)" at small sizes — spell out "Section 4.2". C2: chart
2's top-right legend/guide corner is crowded — spread the legend and the
R1/R2/R2-floor guide labels apart. The optimizer applies these when it
re-runs `make_charts`, then re-runs pytest; the coder does not touch charts
02/03.

**Handoff to coder — what changed, why, first step.** What changed: only the
§4.4 evaluation design — injections are now built relative to trailing
history (price spike +4.0σ_ret, volume surge 5.0× trailing mean volume,
joint +3.0σ_ret / 3.0× trailing mean volume) with a mandatory harness
self-check, and precision now counts clean-data flags as true positives.
Why: the tester's independent recomputation proved both misses were
measurement defects (planted anomalies that weren't anomalous; genuine real
days scored as false positives), not detector defects. First step: open
`src/anomaly.py` and rewrite `inject_anomalies` to the new magnitudes plus
the self-check assertions, then update the injection/evaluation tests to
match — touch nothing else in the detector.

### §4.4 amendment 2 (2026-11-07, rework send-back)

**Why.** The coder implemented amendment 1 faithfully and the pipeline
failed loudly exactly as designed: 3 of 30 plants fail the mandatory
self-check (all joint shocks — SOL 2026-08-26 volume_z 1.69, ETH 2026-09-02
1.66, SOL 2026-09-19 1.32, bar ≥ 2; return side passes at 2.64–2.75). The
coder verified these fail on the original uninjected frame too, so no
implementation choice can fix them: it is a spec defect in amendment 1,
not a code defect. Root cause: the three plants' trailing 30-day
log-volume-ratio windows overlap the real 2026-08-20–25 high-volume week,
so the trailing std is 0.59–0.63 **and** the trailing mean reaches 0.32
(SOL 2026-09-19). Amendment 1's "with margin on both axes" claim assumed
a typical std of ~0.3–0.5 **and implicitly a trailing mean near zero**;
both assumptions fail at these three seed-42 dates. The correct formula
is `volume_z = (log(multiple) − trailing mean) / trailing std`, not
`log(multiple) / std`.

**Decision: option (a) — raise the joint-shock volume multiple from 3.0×
to 5.0× trailing mean volume. Return side unchanged (+3.0 × σ_ret).**
Options (b) (re-roll dates to avoid high-volume-regime windows) and (c)
(lower the joint self-check bar) were rejected: (b) is date-shopping by
rule — it would make the harness pass by avoiding hard windows and defeat
the tripwire amendment 1 deliberately installed; (c) would gut the
self-check, since the failing plants sit at volume_z 1.32–1.69 and any bar
low enough to pass them (≤ 1.32) no longer guarantees the plant clears
R3's bar, which is the self-check's whole purpose.

**Why 5.0× and not 4.0× — verified, not assumed.** The 4.0× figure was
checked by exact simulation of the coder's sequential injection algorithm
on the committed CSVs, and it **fails**: SOL 2026-09-19 gives volume_z
1.76 at 4.0× (1.83 on the original frame; the sequential frame is worse
because the 2026-08-26 joint plant sits inside its trailing window).
The arithmetic: log(4) ≈ 1.386, but (1.386 − 0.317) / 0.586 = 1.83, not
1.386 / 0.63 ≈ 2.20 — the trailing mean of 0.317 cannot be ignored. At
**5.0×** the same exact simulation passes all 10 joint shocks:

| Plant (worst cases) | \|return_z\| (bar ≥ 2) | volume_z at 5.0× (bar ≥ 2) |
|---|---|---|
| SOL 2026-08-26 | 2.64 | 2.46 |
| ETH 2026-09-02 | 2.72 | 2.41 |
| SOL 2026-09-19 (worst) | 2.75 | **2.07** |

Worst joint volume_z 2.07 (SOL 2026-09-19: (log 5 ≈ 1.609 − ~0.36) /
~0.63); worst joint |return_z| 2.46 (SOL 2026-08-26). All other 20
plants still pass (price spikes and volume surges untouched). The 2.07
margin is thin but the pipeline is fully deterministic — committed CSVs,
seed 42, fixed algorithm — so 2.07 is the exact reproduced value, not an
estimate; the self-check stays loud and will catch any future drift.

**Trade-off, stated plainly.** The joint volume multiple (5.0×) now equals
the pure volume-surge multiple (5.0×), so joint shocks are no longer the
milder type on the volume axis — amendment 1's ordering preference is
retired as unachievable in a high-volume regime. The types remain distinct:
a joint shock carries a +3.0σ return (volume surges have no price change),
and a joint plant still faces the strictly stronger R3 requirement (both
axes ≥ 2) versus the surge's single-axis bar. The new joint construction
label is `3.0x trailing return std + 5.0x trailing mean volume`.

**Unchanged.** All five §4.4 targets; R1–R3 thresholds; the Isolation
Forest; price-spike (+4.0σ_ret) and volume-surge (5.0×) magnitudes; the
amended precision rule; the self-check bars and the loud-failure mechanism;
n = 30 (10 per type), the seed-42 dates and the one-per-month-per-coin
selection rule. No date is re-rolled.

**Coder rework (exact scope — one line plus its label and test).**

1. `src/anomaly.py`, `inject_anomalies` joint-shock branch only: change
   `volume[t]` from `3.0 × mean_vol` to **`5.0 × mean_vol`**; update the
   `constructions["joint_shock"]` string to
   `3.0x trailing return std + 5.0x trailing mean volume`. Nothing else in
   `src/anomaly.py` changes — the self-check, `evaluate` (incl. the
   `clean_flags` precision wiring) and every detector function stay
   exactly as implemented in the rework.
2. `tests/test_pipeline.py`: update the rewritten injection test's joint
   construction identity and expected volume multiple (3.0× → 5.0×). No
   other test changes.
3. Then carry out amendment 1's rework steps 2–5 unchanged: re-run the
   pipeline offline from the committed cache (expect exit 0, 30 plants,
   self-check silent); regenerate `crypto_daily_injected.csv` and
   `injected_anomalies.csv`; restore `data_source.json` `source` to
   `"live"`; regenerate chart 04 (verify 01–03 byte-identical); update
   `outputs/anomaly_evaluation.md`, affected numbers in
   `outputs/insights_summary.md` and `README.md`; re-execute the notebook
   (its `evaluate` call still needs the `clean_flags` wiring plus updated
   §Q3 markdown); re-run pytest from both locations + `black --check` +
   `ruff check`.

**Tester re-verification.** As in amendment 1 (recompute all five §4.4
targets independently from the regenerated CSVs; verify the self-check
exists and every plant's statistics clear its bar; pytest from both
locations + lint; Streamlit smoke gate with a fresh screenshot), plus:
verify every joint plant's `volume_z ≥ 2` from
`crypto_daily_injected.csv` + `injected_anomalies.csv`, and record the
worst-case margin (joint volume_z 2.07, SOL 2026-09-19) in the dated
re-verification section of `test_report.md`.

**Handoff to coder — what changed, why, first step.** What changed: one
number — the joint-shock volume multiple, 3.0× → **5.0×** trailing mean
volume (return side still +3.0σ_ret). Why: amendment 1's 3.0× fails its
own self-check on 3 plants, and the seemingly safer 4.0× was verified by
exact simulation to fail too (SOL 2026-09-19 volume_z 1.76) because the
trailing log-volume-ratio mean (0.317) was left out of the arithmetic;
5.0× is the smallest multiple that clears the worst observed case
(volume_z 2.07). First step: in `src/anomaly.py` change the joint-shock
volume line to `5.0 * mean_vol` and its construction label, then run the
offline pipeline and confirm the self-check is silent.

### 4.5 Ethics guard (mandatory, in every public-facing output)

- Label every flagged item **"unusual pattern requiring investigation"** — never "manipulation", "suspicious trading", "pump-and-dump", or any term implying intent or wrongdoing.
- The README, dashboard header, and insights summary each carry the sentence: *"Anomalies flagged here are statistical outliers in price and volume. They are not evidence of manipulation, and no flagged pattern should be presented as such."*
- Educational analysis only — not investment advice (same disclaimer as Days 1–2).

### 4.6 Signal-explanation format

Every flagged anomaly must be traceable to the underlying data. Each row of
the anomaly timeline carries:

| Field | Meaning |
|---|---|
| `date`, `coin` | When and what |
| `price`, `daily_return` | Price and % move that day |
| `volume`, `volume_ratio` | Volume and multiple of its 30-day average |
| `return_z`, `volume_z` | The two z-scores (2 d.p.) |
| `vol_30d_ann`, `vol_regime` | Volatility context |
| `drawdown` | Distance from running peak |
| `rules_triggered` | e.g. `R1+R3` |
| `isolation_forest_score` | Decision-function value (2 d.p.) |
| `flagged_by` | `baseline`, `forest`, or `both` |
| `severity` | `High` / `Medium` / `Low` (§4.2) |
| `explanation` | One plain-language sentence, generated from the numbers, e.g.: "Bitcoin fell 8.2% on 2026-03-14 (return z = −3.4) while volume ran 2.6× its 30-day average — a sharp sell-off with unusually heavy trading." |

Rules for explanations:

- Every claim in the sentence must be a number in the same row. No causal claims ("caused by…", "whales sold…", "manipulation").
- If the forest flagged a day no rule caught, the explanation says so: "Flagged by the Isolation Forest only — no single rule crossed its threshold; the combination of a −2.1σ return, 1.8× volume and elevated volatility was jointly unusual."
- The dashboard and notebook show the same explanation text; there is one generator function (`generate_explanation`, §6), not hand-written copy per anomaly.

**Conventions the coder must not re-decide:** simple (not log) daily returns;
trailing 30-day windows excluding today for all z-scores; thresholds R1
|z|≥3, R2 z≥3 + ratio≥2, R3 both |z|≥2; severity tiers per §4.2;
Isolation Forest `random_state=42`, `n_estimators=200`, contamination from the
baseline flag rate; injected-anomaly tolerance ±1 day; thresholds fixed before
evaluation runs. If any of these is unworkable, send it back to the planner
with the exact point — do not silently substitute a different convention.

## 5. Exact file tree (mirror Day 2's shape)

```
day-03-crypto-market-anomaly-detector/
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
│       ├── crypto_daily.csv          # ~1,095 rows expected (365/coin): date, coin, price, market_cap, volume, daily_return, drawdown, vol_30d_ann + §4.1 features (volume_ratio, log_volume_ratio, return_z, volume_z, vol_regime)
│       ├── crypto_daily_injected.csv # copy of crypto_daily.csv with ~30 injected anomalies applied (evaluation copy only — never the real data)
│       ├── anomaly_timeline.csv      # one row per flagged day (§4.6 fields): date, coin, price, daily_return, volume, volume_ratio, return_z, volume_z, vol_30d_ann, vol_regime, drawdown, rules_triggered, isolation_forest_score, flagged_by, severity, explanation
│       ├── injected_anomalies.csv    # ~30 rows: date, coin, type (price_spike / volume_surge / joint_shock), magnitude — the evaluation label set
│       └── data_source.json          # source, generated_at_utc, synthetic, seed (null live / 42 synthetic), window, coins
├── notebooks/
│   └── analysis.ipynb          # executes end-to-end offline via nbconvert
├── src/
│   ├── data_pipeline.py        # fetch, clean, features, anomaly run, injection + evaluation, synthetic fallback, save outputs
│   ├── anomaly.py              # pure anomaly-model module (see §6) — feature engineering, rolling z-scores, rules R1–R3, Isolation Forest, injection harness, evaluation metrics, explanations
│   ├── make_charts.py          # regenerates exactly the 4 PNGs in §7, offline from committed CSVs
│   └── app.py                  # Streamlit anomaly-timeline dashboard (width='stretch', §6)
├── outputs/
│   ├── insights_summary.md     # plain-language anomaly notes + 1 actionable recommendation
│   ├── anomaly_evaluation.md   # model evaluation report (§4.4): baseline-vs-model comparison, injected-anomaly precision/recall/F1, per-type recall, targets with pass/fail — CHOSEN over folding evaluation into insights_summary.md, so the plain-language notes stay readable and the report card stands alone
│   └── charts/
│       ├── 01_anomaly_timeline.png
│       ├── 02_return_volume_scatter.png
│       ├── 03_flag_counts_severity.png
│       └── 04_evaluation.png
├── screenshots/
│   └── dashboard.png           # REAL capture of the running app (see §6)
└── tests/
    └── test_pipeline.py        # pytest, offline, ≥7 tests (see §6)
```

Build only what this tree lists. No extra files, no extra charts, no extra
dependencies. (Day 1's `publish_checklist.md` / `test_report.md` are produced
by later roles, not by the coder; the coder must not pre-create them.)

**Not in scope (deferred polish, do not add):** the Day 2 day-log item to fix
cosmetic raw-slug labels in the dashboard (e.g. `bitcoin` / `var_95` style
labels) is **deferred polish, not part of Day 3** — no label-cleanup work
belongs in this plan, and the coder must not spend Day 3 effort on it.

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `README.md` | Problem + audience (§1), dataset summary (source, endpoint, window, access date, row counts, licence note), tools, method (feature list, rules R1–R3, Isolation Forest settings, contamination value actually used, evaluation design), key insights (filled with real numbers after the run), visuals (the 4 charts embedded), how to run, limitations (§4.3), ethics-guard sentence (§4.5) + "Powered by CoinGecko" attribution + "Educational analysis only — not investment advice." disclaimer. |
| `data/README.md` | Provenance (§3.3): provider, endpoint, window, access date, keyless vs key, row counts per coin, licence/attribution note + unresolved redistribution tension stated honestly, commit rule, one manually validated metric (by hand, with the numbers — e.g. recompute one flagged day's `return_z` from the CSV), versions used for this build, and the `data_source.json` source-field correction if §3.3 applied. |
| `data/raw/*.json` | Verbatim CoinGecko `/market_chart/range` responses, one per coin. Committed (small, <1 MB each). Never overwritten by synthetic data. |
| `data/processed/crypto_daily.csv` | Daily frame, ~1,095 rows expected: `date, coin, price, market_cap, volume, daily_return, drawdown, vol_30d_ann` plus the §4.1 features (`volume_ratio`, `log_volume_ratio`, `return_z`, `volume_z`, `vol_regime`). First daily_return per coin NaN; first 30 return_z/volume_z per coin NaN (warm-up). |
| `data/processed/crypto_daily_injected.csv` | Copy of `crypto_daily.csv` with the ~30 injections of §4.4b applied. Evaluation copy only — the real frame is never modified. Same columns as `crypto_daily.csv`. |
| `data/processed/anomaly_timeline.csv` | One row per flagged day on the **real** data, with every §4.6 field. This file is the single source of truth for every flag in the README, dashboard, notebook and notes — all four must agree with it. |
| `data/processed/injected_anomalies.csv` | ~30 rows, the evaluation label set: `date, coin, type` (`price_spike` / `volume_surge` / `joint_shock`), `magnitude`. |
| `data/processed/data_source.json` | `source`, `generated_at_utc`, `synthetic` (bool), `seed` (`null` live / `42` synthetic), window, coins. Subject to the §3.3 source-field rule (re-run live or restore before publishing). |
| `src/data_pipeline.py` | Fetch (no-key first, Demo-key env fallback, ≥5 s spacing, one 60 s retry on 429, then fallback), clean/merge into the daily frame, call `anomaly.py` to compute features, rules, forest flags and the timeline, run the injection harness + evaluation on the injected copy, `generate_synthetic(seed=42)`, `--offline` / `--use-cache` mode (runs from committed cache, no network, never generates synthetic data), `save_outputs()` writing raw JSONs + processed CSVs + `data_source.json`. Mirror Day 2's function shapes (`fetch_coin_chart`, `fetch_all_coins`, `clean_chart`, `save_outputs`, `generate_synthetic`, `_load_cache`, `main`) so the tester can reuse the Day 1/2 test patterns. |
| `src/anomaly.py` | **New module — the anomaly model. Pure, testable functions, no I/O, no network.** Signatures the coder must implement (names fixed so the notebook, app and tests import them, never re-implement them): `compute_features(daily_df) -> pd.DataFrame` (adds `abs_return`, `volume_ratio`, `log_volume_ratio`, `return_z`, `volume_z`, `vol_30d_ann`, `drawdown`, `vol_regime` per §4.1; trailing windows only); `apply_rules(featured_df) -> pd.DataFrame` (adds `rules_triggered`, `severity`, `baseline_flagged` per §4.2); `fit_isolation_forest(featured_df, contamination: float, random_state: int = 42, n_estimators: int = 200) -> tuple[IsolationForest, pd.DataFrame]` (per-coin standardised 5-feature fit; adds `isolation_forest_score`, `is_anomaly`); `build_timeline(featured_df) -> pd.DataFrame` (union of baseline + forest flags, `flagged_by`, all §4.6 fields); `generate_explanation(row: pd.Series) -> str` (one plain-language sentence from the row's numbers only; forest-only wording per §4.6); `inject_anomalies(daily_df, n: int = 30, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]` (injected copy + injections label frame, spread across coins and the year, three types per §4.4b); `evaluate(detected_df, injected_df, tolerance_days: int = 1) -> dict` (precision, recall, F1 per method — baseline, forest, union — plus per-type recall and Jaccard overlap). |
| `src/make_charts.py` | `python -m src.make_charts` regenerates **exactly the 4 PNGs in §7** in `outputs/charts/`, offline from the committed processed CSVs only (no network, no API). Every chart: title, labelled axes with units, legend where needed, source note ("Source: CoinGecko" or "SYNTHETIC DATA — API unavailable on 2026-11-07" when synthetic), readable at dashboard size, drawn **to scale** (no truncated or misleading axes). Must not create extra PNGs. |
| `src/app.py` | Streamlit anomaly-timeline dashboard: coin multi-select (default all three), anomaly timeline table (the §4.6 fields, with the plain-language explanation per flag), severity filter, the 4 charts (or their data rendered natively), baseline-vs-forest overlap summary, ethics-guard sentence (§4.5) in the header, "Powered by CoinGecko" attribution (legible, size 10+) + "Educational analysis only — not investment advice." disclaimer, synthetic banner if `data_source.json` says synthetic. **Layout must use `width='stretch'` (the current Streamlit API) — never the deprecated `use_container_width`** (Day 2 day-log lesson; the deprecation must not bite Day 3). Must not crash on edge cases — Day 1 lesson (b): sort/reset indexes before any positional lookup. |
| `notebooks/analysis.ipynb` | Full analysis top-to-bottom, offline: load processed CSVs, recompute features/rules/forest flags via `anomaly.py`, reproduce the 4 charts, answer each §2 question with numbers, show the evaluation tables. Resolve the project root from the notebook file's own location via `_find_root()` (check for `data/processed/crypto_daily.csv` from the notebook's directory upward); **never from `Path.cwd()` alone** — Day 1 lesson (e). A copy executed outside the project must fail with a clear `FileNotFoundError`. Must execute end-to-end offline via nbconvert (CI runs it). |
| `tests/test_pipeline.py` | pytest, offline, **≥7 tests** (target 10–14, mirroring Day 2's 21-test bar scaled to this day's scope). Must cover at minimum: (1) trailing z-score on a hand-computed series (window excludes today — no look-ahead; first 30 NaN); (2) rules R1/R2/R3 on constructed series (each rule fires and only fires at threshold, including the R2 `volume_ratio ≥ 2` floor blocking a high-z/low-ratio day); (3) severity tiers (High/Medium/Low per §4.2); (4) Isolation Forest determinism (`random_state=42` → identical scores on re-fit) and 5-feature input; (5) injection harness (exactly the recorded injections, three types present, real frame unmodified); (6) evaluation metrics with ±1-day tolerance (a flag one day after an injection counts as detected; precision/recall/F1 on a known case); (7) synthetic generation deterministic with seed 42 and 365 points from 2025-11-07; (8) synthetic never overwrites the live cache and `*_synthetic.json` does not satisfy the cache check; (9) `--offline`/`--use-cache` runs without network; (10) committed CSVs match the published findings in README/insights (recompute one flag's `return_z` from the CSVs); (11) notebook `_find_root()` resolves correctly — **and the suite must pass both from the repo root and from inside the day folder** (Day 2 CI lesson: the Day 2 notebook test failed from the repo root because `_find_root()` was resolved against the working directory; the test must exec the notebook namespace with `__file__` set to the notebook path, and the coder must run the full suite from both locations before handoff); (12) "Powered by CoinGecko" attribution present in app + charts/README and the §4.5 ethics sentence present in README + app + insights. Replace the scaffold `tests/test_smoke.py` (delete it — do not keep both test files). |
| `outputs/insights_summary.md` | Plain-language anomaly notes (§2): one finding per §2 question (each citing its number from `anomaly_timeline.csv` / `anomaly_evaluation.md` and its chart), **one actionable recommendation** (an analytical next step, e.g. what to monitor or check next — never investment advice), limitations (§4.3), ethics-guard sentence (§4.5). Does NOT carry the evaluation tables — those live in `outputs/anomaly_evaluation.md` by this plan's choice (§5). |
| `outputs/anomaly_evaluation.md` | **Model evaluation report (this plan's choice — separate file, not folded into insights_summary.md):** the §4.4a comparison table (per coin and overall: baseline flags by rule, forest flags, both / baseline-only / forest-only, Jaccard, contamination used), the §4.4b precision/recall/F1 table (baseline, forest, union) with per-type recall, the §4.4 "good" targets with pass/fail marked, and a short diagnosis of any miss (no threshold re-tuning after the fact). Every number recomputed from `anomaly_timeline.csv`, `injected_anomalies.csv` and `crypto_daily_injected.csv`. |
| `outputs/charts/*.png` | Exactly 4 PNGs (§7), regenerated by `src/make_charts.py`. No extra PNGs in this folder — CI asserts the count is exactly 4. |
| `screenshots/dashboard.png` | **REAL capture of the running Streamlit app** (full page), taken during the coder's smoke test — not a composite of the static charts. If a real capture is genuinely impossible, flag it explicitly as a composite in the handoff and in the README caption — do not silently pass a composite off as a screenshot. |
| `requirements.txt` | Pinned exact `==` versions, verified in the build venv (Python 3.12): `pandas`, `numpy`, `matplotlib`, `plotly`, `streamlit`, `requests`, `pytest`, **`scikit-learn`** (**new for Day 3** — the coder installs the latest compatible version in the venv; the exact pin is set at optimizer time from the venv that actually ran), **`jupyter==1.1.1` + `nbformat==5.11.1`** (required — CI executes the notebook via nbconvert). No new runtime dependency without a plan change. |
| `pyproject.toml` | Ruff + black settings mirroring Day 2 exactly: `[tool.ruff] line-length = 88, target-version = "py312"`, `[tool.black] line-length = 88`, `[tool.pytest.ini_options] testpaths = ["tests"]`. Dev tools (ruff 0.17.4, black 26.10.1) are pinned once in the portfolio-root `requirements-dev.txt`, shared by all days. |
| `.gitignore` | Mirror Day 2 exactly: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, plus `data/raw/*_synthetic.json` (synthetic fallback output is never committed; live `data/raw/*.json` IS committed). **Must NOT exclude `data/`** — diff `.gitignore` against this plan before sign-off (Day 1 lesson d). |
| `LICENSE` | MIT, keep as scaffolded. |

### Coder environment (Day 1/2 lessons applied)

- Create `.venv` with the pinned deps installed (including `scikit-learn`) and hand it off working — the tester provisions nothing and must never install the project's own deps from scratch; if the venv is missing the tester reports "blocked: no venv".
- Run `black` + `ruff` **before** handoff (Day 1 lesson: lint left to the end cost a full fix cycle). `black --check` + `ruff check` must pass on `src/` and `tests/`.
- Capture the real `screenshots/dashboard.png` during the coder's own smoke test (fresh port 8502+, never assume 8501 is free; kill the server and verify the port is free afterwards — Day 1 lesson c).
- Run the full pytest suite **both from the repo root and from inside the day folder** before handoff (Day 2 CI lesson).
- One writer per file; build only what this plan lists; no extra web searches.

## 7. Charts (exactly 4 — CI asserts the count)

`python -m src.make_charts` regenerates exactly these 4 PNGs, offline from the
committed processed CSVs. All 4 must be well-labelled (title, axes with units,
legend, source note), **drawn to scale** (no truncated or misleading axes)
and legible at dashboard size.

| # | Filename | Content |
|---|---|---|
| 1 | `01_anomaly_timeline.png` | **Anomaly timeline** — price over time for BTC, ETH, SOL (one panel per coin or one axis with clear legend), with every flagged day marked by severity (High / Medium / Low) and coloured by `flagged_by` (baseline / forest / both), so when the unusual days happened — and how severe they were — is visible at a glance. Annotate the highest-severity flag per coin (date + return + volume ratio). |
| 2 | `02_return_volume_scatter.png` | **Return-vs-volume scatter with flags** — daily return (x, %) vs log volume ratio (y) for all three coins, unflagged days in muted grey, flagged days in colour by severity, with the R1/R2/R3 threshold lines drawn (dashed, labelled) so the reader can see *why* a point was flagged and how far outside normal behaviour it sits. |
| 3 | `03_flag_counts_severity.png` | **Per-coin flag counts / severity** — grouped bars per coin: flags by rule (R1 / R2 / R3) and by severity (High / Medium / Low), plus a baseline-vs-forest split (both / baseline-only / forest-only), so which coin and which pattern produced the most flags is comparable at a glance. |
| 4 | `04_evaluation.png` | **Evaluation chart** — grouped bars of precision, recall and F1 per method (baseline, forest, union) against the injected anomalies, with the §4.4 target lines drawn (recall 0.80, precision 0.50, Jaccard 0.30), plus a per-type recall panel (price spike / volume surge / joint shock, target 0.60 line). One figure, two clearly labelled panels. |

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoint, collection date, licence/attribution ("Powered by CoinGecko"), row counts — in `data/README.md` and `data/processed/data_source.json` (with the §3.3 source-field rule satisfied: live re-run or restored field before publishing)
- [ ] Repeatable prep steps documented (fetch → clean → features → rules + forest → charts, with `--offline` mode) + anomaly definitions (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 3 produces exactly 4 (§7), **drawn to scale and legible**, plus a functional evaluation report: the Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding per §2 question) + **one actionable recommendation** (analytical next step, never investment advice) + separate evaluation report (`outputs/anomaly_evaluation.md`, §4.4 tables with pass/fail) — **and all five §4.4 targets pass on the regenerated evaluation after the 2026-11-07 §4.4 amendment** (injection + precision-rule fix; tester re-verifies by independent recomputation from the regenerated CSVs; the original D1/D2 misses stay on record in `test_report.md`)
- [ ] README with setup instructions, sample outputs (timeline table + chart thumbnails), and limitations
- [ ] No credentials / private records in the repo; no huge raw files committed (raw JSONs <1 MB each, <5 MB per day folder); `.gitignore` does not exclude `data/`
- [ ] One metric manually validated by hand and recorded in `data/README.md` (e.g. recompute one flagged day's `return_z` from the CSV: trailing 30-day mean/std → z-score, matching to ≤1e-9 as Days 1–2 did)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r requirements.txt`, `python -m src.data_pipeline --offline`, `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing both from the repo root and from inside the day folder**
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert, with `_find_root()`)
- [ ] Pinned dependencies in `requirements.txt` (including `scikit-learn`, pinned at optimizer time from the venv that actually ran); `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and on `/_stcore/health`, real `screenshots/dashboard.png` captured, server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately before push (every file the READMEs reference exists on disk — charts, screenshot, CSVs, evaluation report)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

Per AGENTS.md / Day 1 retrospective, the coder hands off only when **all** of
the following hold; the tester verifies in the coder's venv and provisions nothing:

1. `.venv` exists with pinned deps installed (requirements.txt matches the venv that actually ran, including `scikit-learn`).
2. `black --check src tests` and `ruff check src tests` pass (exit 0).
3. `pytest tests/ -q` passes (≥7 tests, offline) **from the repo root AND from inside the day folder**.
4. `.gitignore` matches §6 (in particular: does NOT exclude `data/`; excludes only `data/raw/*_synthetic.json`).
5. `screenshots/dashboard.png` is a REAL capture of the running app (or explicitly flagged as a composite in the handoff + README caption).
6. `python -m src.make_charts` regenerates exactly 4 PNGs in `outputs/charts/` (offline, from committed CSVs); notebook executes end-to-end offline via nbconvert.
7. Every number in README / dashboard / notebook / insights matches `data/processed/anomaly_timeline.csv`, and every evaluation number matches `outputs/anomaly_evaluation.md` and the injected-label CSVs.
8. `data/processed/data_source.json` `source` field is correct for the published data (§3.3) — re-run live or restore before handoff.
9. `src/app.py` uses `width='stretch'` throughout — no `use_container_width` anywhere in the tree.

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
| Centred / full-window z-scores leaking future data | §4.1 mandates trailing windows excluding today; tester validates on a hand-computed series (§6, test 1). |
| Thresholds tuned after seeing the injected results (overfitting to own injections) | §4.4 forbids it: thresholds fixed in this plan; a miss is reported and diagnosed, not tuned away. |
| Baseline flag rate outside 2–5% | §4.4a sanity check: <1% or >10% means revisit §4.2 before proceeding — do not proceed to publish a mis-specified detector. |
| Day 2 figures copied into Day 3 outputs | §3.3 forbids it; tester recomputes one flag's `return_z` from Day 3's own CSVs. |
| Flagged days presented as manipulation | §4.5 ethics guard in README, dashboard header, insights and evaluation report; tester checks the wording and the absence of "manipulation" language. |
| Dashboard crash invisible to pytest (Day 1 lesson b) | Mandatory Streamlit smoke gate (§9) + real screenshot. |
| `use_container_width` deprecation (Day 2 day-log lesson) | §6 mandates `width='stretch'` in `app.py`; handoff checklist item 9 greps for the deprecated call. |
| Offline run overwriting `data_source.json` source to `"cache"` (Day 2 day-log lesson) | §3.3 rule: re-run live or restore the field before publishing; handoff checklist item 8; publisher frozen-tree check includes it. |
| `.gitignore` silently dropping raw data (Day 1 lesson d) | §6 diff check at coder handoff; publisher frozen-tree check before push. |
| Screenshot going missing before push (Day 1 lesson) | Treat `screenshots/dashboard.png` as a checked deliverable; verify it exists at every handoff; publisher re-verifies immediately before pushing. |
| Notebook cwd trap (Day 1 lesson e) + Day 2 CI failure (test passed inside the day folder, failed from the repo root) | `_find_root()` from the notebook file's own location; notebook test execs with `__file__` set to the notebook path; full suite run from both locations (§6, test 11). |
| Chart count drift (extra PNG breaks CI) | `make_charts.py` writes exactly the 4 files in §7 and no others; CI asserts count == 4. |
| `scikit-learn` missing from CI / venv | New dependency is in §6 `requirements.txt` (pinned at optimizer time); coder installs it in the venv; CI installs from the same file. |

## 11. Brief-vs-plan differences

**No contradictions.** This plan adopts the brief's endpoints, window
(2025-11-07 → 2026-11-07, `from=1762473600`, `to=1794009600`), feature
definitions (§4.1, verbatim), rules R1–R3 and severity tiers (§4.2,
verbatim), Isolation Forest settings (§4.3), evaluation design and targets
(§4.4, verbatim), explanation format and ethics guard (§4.5–4.6, verbatim)
and synthetic parameters (seed 42, §3.5) without change. Additions and
choices made by the plan (not contradictions):

- **Evaluation output chosen:** a separate `outputs/anomaly_evaluation.md`
  (the brief offered `model_evaluation.md` *or* an evaluation section in
  `insights_summary.md`); the plan chooses the separate file so the
  plain-language notes stay readable.
- **Processed-file names fixed** where the brief left them to the plan:
  `crypto_daily.csv`, `crypto_daily_injected.csv`, `anomaly_timeline.csv`,
  `injected_anomalies.csv`, `data_source.json` (with a `seed` field).
- **New module `src/anomaly.py`** with fixed function signatures (§6) — the
  brief names no module; the pipeline module keeps Day 2's shape.
- **Exact 4 chart filenames** (§7) and the ≥7-test list (§6), including the
  Day 2 CI lesson (suite must pass from the repo root AND inside the day
  folder).
- **Day-log lessons applied:** `width='stretch'` (not `use_container_width`)
  in `app.py`; the `data_source.json` `"cache"` source-field rule (§3.3);
  cosmetic raw-slug label fixes explicitly **excluded** as deferred polish.
- **3 analysis questions** (§2) instead of Day 2's 6, per this day's scope.

If the coder finds any of these unworkable, it goes back to the planner with
the exact point — the coder does not silently substitute a different
convention.

## 12. Build order (coder)

1. `.venv` + pinned deps (including `scikit-learn`) → 2. `src/anomaly.py`
   (pure functions: features → z-scores → rules → forest → explanations →
   injection → evaluation) → 3. `src/data_pipeline.py` (fetch → clean →
   features → anomaly run → injection + evaluation → save; verify ~1,095
   rows, report HTTP status per coin, report the contamination value actually
   used and the baseline flag rate) → 4. `pytest` on the anomaly tests as
   they land (from both the repo root and the day folder) → 5.
   `src/make_charts.py` (exactly 4 PNGs) → 6. `notebooks/analysis.ipynb`
   (offline, `_find_root()`) → 7. `src/app.py` + smoke test + real
   `screenshots/dashboard.png` → 8. `README.md`, `data/README.md`,
   `outputs/insights_summary.md`, `outputs/anomaly_evaluation.md` (numbers
   from the CSVs only) → 9. `black` + `ruff` + full `pytest` (both locations)
   + handoff checklist (§9).

**Token note:** this plan reuses the brief's verified numbers (endpoints,
timestamps, feature/rule definitions, evaluation targets, synthetic
parameters) verbatim — no re-verification, no extra searches. Later roles
reuse the tester's verified figures verbatim; nobody recomputes a finding
from scratch (a spot-check from the committed CSVs is the most that is ever
needed).

## 13. Handoff (planner → coder)

**What was produced:** exactly one file —
`day-03-crypto-market-anomaly-detector/plan.md` (this file). No other file was
written or modified.

**Exact file tree the coder must build:** §5 — `README.md`, `LICENSE`,
`requirements.txt` (with new `scikit-learn`), `pyproject.toml`, `.gitignore`,
`data/README.md`, `data/raw/` (3 CoinGecko JSONs), `data/processed/`
(`crypto_daily.csv`, `crypto_daily_injected.csv`, `anomaly_timeline.csv`,
`injected_anomalies.csv`, `data_source.json`), `notebooks/analysis.ipynb`,
`src/` (`data_pipeline.py`, `anomaly.py`, `make_charts.py`, `app.py`),
`outputs/` (`insights_summary.md`, `anomaly_evaluation.md`, `charts/` with
exactly 4 PNGs), `screenshots/dashboard.png`, `tests/test_pipeline.py`.
Build only what §5 lists — no extra files.

**Known gaps:** contamination value is not fixed in advance — it is set from
the observed baseline flag rate at build time and must be reported (§4.3);
`scikit-learn` has no pinned version yet (coder installs the latest
compatible version in the venv; the pin is set at optimizer time); Day 1/2
caches do not cover Day 3's window, so there is no valid cache fallback
until a Day 3 fetch succeeds; no ground-truth manipulation label exists, so
evaluation rests entirely on injected anomalies + baseline-vs-model overlap.

**Coder's first step:** create the `.venv`, install the pinned deps
**including `scikit-learn`**, then write `src/anomaly.py` first
(`compute_features` → `apply_rules` → `fit_isolation_forest`, §6) — the
pure functions everything else (pipeline, notebook, app, tests) imports.
