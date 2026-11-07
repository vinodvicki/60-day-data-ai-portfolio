# Research Brief — Day 3: Crypto Market Anomaly Detector

**Project:** Day 3 of the 60-day Data + AI portfolio
**Roadmap entry (exact):** "Flag unusual price-volume patterns with a baseline or unsupervised anomaly model; do not present anomalies as proven manipulation. GitHub deliverable: Anomaly timeline, model evaluation, and signal explanations. Core skills: Python, Pandas, time-series analysis, Plotly, anomaly detection. Suggested data: CoinGecko public market data; public historical price/volume series."
**Date written:** 2026-11-07 (researcher role, role 1 of 6)
**Status:** Research only — no live data was fetched. Fetching is the coder's job.

---

## 1. Verified source, endpoint, and parameters

### Source

**CoinGecko public API** — `https://api.coingecko.com/api/v3`. Same source as Days 1–2, verified working keyless on both days (HTTP 200 for all three coins). No new endpoint search was needed; this brief reuses the Day 2 pipeline (`day-02-crypto-risk-volatility-analyzer/src/data_pipeline.py`) verbatim for fetch/clean.

### Coins and window

| Item | Value |
|---|---|
| Coins | `bitcoin`, `ethereum`, `solana` |
| Currency | `usd` |
| Window | **2025-11-07 → 2026-11-07** (365 days, 1-year window ending today, 2026-11-07) |
| Expected rows | 365 days × 3 coins = **~1,095 rows** (364 usable daily returns per coin after the first-day diff) |
| `from` (unix, UTC) | **1762473600** (2025-11-07 00:00 UTC) |
| `to` (unix, UTC) | **1794009600** (2026-11-07 00:00 UTC) |

Timestamps computed with `python3 -c` from `datetime(..., tzinfo=timezone.utc)`; they are exactly Day 2's values (1762387200 / 1793923200) shifted by +86,400 s (one day), which cross-checks the arithmetic.

### Endpoint (primary)

```
GET https://api.coingecko.com/api/v3/coins/{id}/market_chart/range?vs_currency=usd&from=1762473600&to=1794009600
```

Response fields: `prices`, `market_caps`, `total_volumes` — each a list of `[timestamp_ms, value]`. Clean exactly as Day 2 (`clean_chart`): merge the three series on `ts_ms`, drop duplicate timestamps, keep the last row per calendar day (UTC, `YYYY-MM-DD`), assert no NaN prices. Output columns: `date, coin, price, market_cap, volume`.

### Fallback endpoint

```
GET https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=365
```

Use only if the `/range` call fails for a non-429 reason. **No `interval` parameter** on either call (Day 1/2 finding: the range endpoint returns daily points at this window without it).

### Rate limits and retry rule (verified Days 1–2)

- **3 calls only** (one per coin), **≥ 5 s between calls**.
- Public no-key limit observed: roughly **5–15 calls/min**; staying at 3 calls with 5 s spacing is well inside it.
- **One retry after 60 s on HTTP 429**, honouring the `Retry-After` header if present. After the retry, fail over to cache, then synthetic (see §5).
- HTTP 401/403 → the Demo-key path may be needed; do not retry the no-key call repeatedly.
- Demo key (if ever needed) comes **only** from the `COINGECKO_DEMO_API_KEY` environment variable, sent as the `x-cg-demo-api-key` header. **Never hard-code or commit a key.** The no-key path worked on Days 1–2, so the key path is a fallback only.
- Timeout: 30 s per request.

### Reused Day 2 features

The detector builds on the Day 2 pipeline, which already computes per coin: `daily_return`, `drawdown` (from running peak), and `vol_30d_ann` (30-day rolling annualised volatility; first 29 values NaN). Day 2's verified reference numbers for the shifted window's predecessor (2025-11-06 → 2026-11-06) were: max drawdowns BTC −44.72%, ETH −56.24%, SOL −62.85%; BTC–ETH return correlation 0.908; Sharpe BTC −0.49, ETH −0.41, SOL −0.65; VaR 95% BTC −3.38%, ETH −4.67%, SOL −5.29%. These are context only — Day 3 recomputes everything on its own window and must not copy Day 2's numbers into its outputs.

---

## 2. Anomaly-method recommendation

### Recommended combination (baseline + unsupervised model)

**Baseline: rolling z-score rules** (transparent, explainable, no training) **PLUS an Isolation Forest** on engineered features (captures multi-feature patterns the single-variable rules miss). Both flag the same days; agreement/disagreement between them is itself a finding.

### Feature definitions (all per coin, computed on the cleaned daily frame)

| Feature | Definition |
|---|---|
| `daily_return` | `price[t] / price[t-1] − 1` (first day per coin: NaN) |
| `abs_return` | `abs(daily_return)` |
| `volume_ratio` | `volume[t] / mean(volume[t-30 … t-1])` — today's volume vs its own trailing 30-day mean (excludes today, so a spike is not diluted by itself). First 30 days: NaN. |
| `log_volume_ratio` | `log(volume_ratio)` — used for z-scoring, because volume is right-skewed |
| `vol_30d_ann` | 30-day rolling annualised volatility of daily returns, `std(returns[t-29 … t]) × sqrt(365)` (Day 2 definition, reused) |
| `drawdown` | `price[t] / max(price[≤ t]) − 1` (≤ 0; Day 2 definition, reused) |
| `return_z` | `(daily_return − mean(daily_return[t-30 … t-1])) / std(daily_return[t-30 … t-1])` — 30-day trailing window, excluding today |
| `volume_z` | `(log_volume_ratio − mean(log_volume_ratio[t-30 … t-1])) / std(log_volume_ratio[t-30 … t-1])` — same trailing window |
| `vol_regime` | `vol_30d_ann / median(vol_30d_ann)` — whether today sits in a high-volatility regime relative to the coin's own year |

Trailing (not centred, not full-window) windows are mandatory: a centred or full-window z-score leaks future information into "today's" score. The first 30 days per coin have no z-scores and are excluded from flagging (warm-up period).

### Baseline rules (deterministic, the comparison standard)

A day is **baseline-flagged** if **any** of the following holds:

- **R1 — return shock:** `|return_z| ≥ 3` (a daily move ≥ 3 trailing standard deviations from the coin's own recent mean).
- **R2 — volume surge:** `volume_z ≥ 3` **and** `volume_ratio ≥ 2` (volume at least double its 30-day average *and* statistically extreme in log terms; the ratio floor stops tiny absolute volumes from tripping the z-rule on quiet days).
- **R3 — joint shock:** `|return_z| ≥ 2` **and** `volume_z ≥ 2` on the same day (a moderate price move *with* a moderate volume surge — the classic "unusual price-volume pattern" the roadmap names).

Severity tiers for the timeline: **High** = R1 or R2 with `|z| ≥ 4`, or R1+R2 together; **Medium** = any single rule at threshold; **Low** = R3 only.

### Unsupervised model: Isolation Forest

- **Algorithm:** `sklearn.ensemble.IsolationForest`, `contamination` set from the baseline flag rate (see §3 — start at the observed baseline rate, e.g. ~0.03–0.05, and report the value used), `random_state=42`, `n_estimators=200`.
- **Input features (per coin, standardised with the coin's own trailing statistics — no cross-coin scaling, so a volatile coin does not mask a quiet one):** `daily_return`, `abs_return`, `volume_ratio` (log-transformed), `vol_30d_ann`, `drawdown`. Five features, all defined above; no new data needed.
- **Output:** `anomaly_score` (decision function, lower = more anomalous) and a binary `is_anomaly` from the fitted contamination threshold.
- **Why this combination is defensible:**
  1. The z-score baseline is fully transparent — every flag can be traced to one number on one day, which is what the signal explanations (§4) need.
  2. Isolation Forest needs no labels (none exist — see §3), handles the non-linear joint behaviour of return + volume + volatility that single-variable rules miss, and is a standard, well-understood unsupervised baseline for this exact problem.
  3. The two methods cross-check each other: a day flagged by both is a high-confidence "unusual pattern"; a day flagged by only one is reported as such, with the reason visible.
  4. Everything is computed from the same three public series (price, volume, market cap) already fetched — no extra API calls, no new data risk.
- **Limits (must be stated in the README and the notebook):**
  - Crypto returns are heavy-tailed and volatility clusters, so a fixed ±3σ rule over-flags in volatile regimes and under-flags in calm ones; the trailing window and the `vol_regime` feature mitigate this but do not remove it.
  - Isolation Forest scores are relative rankings, not probabilities — "anomaly score −0.12" has no absolute meaning outside this dataset.
  - The model cannot distinguish a genuine market event (e.g. an ETF headline, a network upgrade) from a data error or from manipulation. It flags *statistical unusualness only*.
  - 365 days per coin is a small sample for unsupervised learning; results are descriptive, not a production detector.
  - **Ethics guard (roadmap-mandated):** anomalies are *never* presented as proven manipulation. Every output labels them "unusual patterns requiring investigation" (§4).

### Suggested dependency

`scikit-learn` (pinned, e.g. `scikit-learn==1.7.x` — coder to pin the exact version installed in the build venv). No other new runtime dependency: Pandas, NumPy, Plotly, Streamlit already in the Day 1/2 stack.

---

## 3. Evaluation plan

### The ground-truth problem

**There is no ground-truth manipulation label for real crypto data.** No public dataset labels which historical days were manipulation, and the roadmap explicitly forbids presenting anomalies as proven manipulation. Therefore evaluation is done on **injected anomalies only**, plus a baseline-vs-model comparison. This must be stated in the README, notebook, and insights summary.

### (a) Baseline vs model comparison

Report, per coin and overall:

- Number and % of days flagged by the baseline rules (and by each rule R1/R2/R3 separately).
- Number and % flagged by Isolation Forest.
- Overlap: days flagged by both / baseline-only / model-only (a small table or Venn-style count). Report the Jaccard overlap (intersection ÷ union).
- The `contamination` used for the forest, set equal to the baseline flag rate so the two methods flag comparable counts — then any difference is about *which* days, not *how many*.
- Sanity expectation: with ~1,095 rows and a ±3σ-style rule, the baseline should flag roughly **2–5% of days** (of the ~1,005 post-warm-up rows). If it flags <1% or >10%, the thresholds or the window are wrong and the planner/coder must revisit §2 before proceeding.

### (b) Injected-anomaly evaluation (precision/recall-style)

1. Take a **copy** of the cleaned daily frame; never inject into the real data. Keep the real and injected datasets in separate files (`crypto_daily.csv` vs `crypto_daily_injected.csv`, or equivalent per the plan).
2. Inject **~30 synthetic anomalies** spread across the three coins and across the year (not clustered in one month), of three types, each with a known date/coin:
   - **Price spike:** multiply one day's price by 1.15 (and the following day's price back down, i.e. a one-day +15% jump and reversal) — tests R1 and the return features.
   - **Volume surge:** multiply one day's volume by 4× with no price change — tests R2 and the volume features.
   - **Joint shock:** one day's price ×1.08 *and* volume ×3 — tests R3 and the forest's joint detection.
   - Record every injection in a small CSV (`injected_anomalies.csv`: date, coin, type, magnitude) — this is the evaluation label set.
3. Run the *identical* baseline + forest pipeline on the injected copy.
4. Report **precision, recall, and F1** for each method (baseline rules, forest, either-method union) against the injected labels, with a tolerance of **±1 day** (an anomaly flagged on the day after an injected price spike counts as detected, because a one-day spike mechanically moves the next day's return too).
5. Report per-type recall (price spikes vs volume surges vs joint shocks) — this shows *which* pattern each method is blind to.

### What "good" looks like

| Metric | Target |
|---|---|
| Injected-anomaly recall (union of both methods) | **≥ 0.80** (at least 24 of 30 injected anomalies found) |
| Injected-anomaly precision (union) | **≥ 0.50** (at least half of all flags are real injected anomalies — the rest are genuine unusual days in the real data, which is expected, not a failure) |
| Baseline-vs-forest overlap (Jaccard) | **≥ 0.30** (the methods substantially agree; near-zero overlap means one of them is mis-specified) |
| Baseline flag rate on real data | **2–5%** of post-warm-up days (see (a)) |
| Per-type recall | No type below **0.60** — if e.g. volume-only surges are missed, say so explicitly rather than hiding it in the average |

If recall is below target, the correct response is to report the miss and diagnose (e.g. "volume surges under 3× are invisible to a 30-day trailing z because volume is noisy") — not to tune thresholds until the injected set passes, which would be overfitting to the coder's own injections. Thresholds are fixed in the plan before evaluation runs.

### Deliverables from evaluation

- `anomaly_timeline.csv` (or per plan): every flagged day with all §4 fields.
- `model_evaluation.md` / evaluation section in `outputs/insights_summary.md`: the (a) comparison table, the (b) precision/recall/F1 table, per-type recall, and the "good" targets with pass/fail marked.
- Charts (per plan): anomaly timeline (price chart with flagged days marked, per coin), and a return-vs-volume scatter with flagged points highlighted.

---

## 4. Signal-explanation format

Every flagged anomaly must be traceable to the underlying data. Each row of the anomaly timeline carries:

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
| `severity` | `High` / `Medium` / `Low` (§2) |
| `explanation` | One plain-language sentence, generated from the numbers, e.g.: "Bitcoin fell 8.2% on 2026-03-14 (return z = −3.4) while volume ran 2.6× its 30-day average — a sharp sell-off with unusually heavy trading." |

Rules for explanations:

- Every claim in the sentence must be a number in the same row. No causal claims ("caused by…", "whales sold…", "manipulation").
- If the forest flagged a day no rule caught, the explanation says so: "Flagged by the Isolation Forest only — no single rule crossed its threshold; the combination of a −2.1σ return, 1.8× volume and elevated volatility was jointly unusual."
- The dashboard and notebook show the same explanation text; there is one generator function, not hand-written copy per anomaly.

### Ethics guard (mandatory, in every public-facing output)

- Label every flagged item **"unusual pattern requiring investigation"** — never "manipulation", "suspicious trading", "pump-and-dump", or any term implying intent or wrongdoing.
- The README, dashboard header, and insights summary each carry the sentence: *"Anomalies flagged here are statistical outliers in price and volume. They are not evidence of manipulation, and no flagged pattern should be presented as such."*
- Educational analysis only — not investment advice (same disclaimer as Days 1–2).

---

## 5. Fallback parameters and open conflicts

### Synthetic fallback (identical to Days 1–2)

Only if the live fetch fails **and** no cache exists (`data/raw/{coin}_market_chart.json`). Deterministic geometric Brownian motion, **seed 42**:

| Coin | Drift (daily) | σ (daily) | Start price | Typical daily volume | Supply (for market cap) |
|---|---|---|---|---|---|
| bitcoin | 0.0008 | 0.035 | $100,000 | $30bn | 19.8m |
| ethereum | 0.0006 | 0.045 | $3,500 | $15bn | 120.0m |
| solana | 0.0005 | 0.06 | $180 | $3bn | 540.0m |

365 daily points from **2025-11-07**; volumes log-normal noise (σ 0.4) around the typical volume; market cap = price × supply. Output goes **only** to `data/raw/{coin}_market_chart_synthetic.json` — it must never overwrite the live cache. `data/processed/data_source.json` records `synthetic: true` + `seed: 42`. All downstream outputs are labelled SYNTHETIC. Note: GBM synthetic data has no real anomalies, so on synthetic data the injected-anomaly evaluation (§3b) is the *only* meaningful evaluation — the "real data" flag rate has no interpretation.

### Cache reuse note

Days 1–2 caches cover windows ending 2026-11-05/06, **not** Day 3's window ending 2026-11-07. A cache fallback for Day 3 is only valid if a Day 3 fetch has previously succeeded and written `data/raw/{coin}_market_chart.json` in the Day 3 folder. Do **not** reuse Day 1/2 raw JSONs as Day 3 data — the window differs by a day and the provenance would be wrong.

### Open conflicts / gaps (for the planner)

1. **No conflicts with Days 1–2.** Endpoint, fetch rules, cleaning, and synthetic parameters are carried over unchanged; only the window shifts by one day and the feature set extends Day 2's.
2. **Contamination is not yet fixed** — it is set from the observed baseline flag rate (§3a). The planner should state the procedure, not a hard number, and the coder reports the value actually used.
3. **Warm-up cost:** the 30-day trailing window means the first 30 days per coin (~90 rows) cannot be flagged. Acceptable; the plan should note the effective evaluation universe is ~1,005 rows, not 1,095.
4. **Volume data quality:** CoinGecko `total_volumes` is exchange-reported volume and is known to be noisy; the `volume_ratio ≥ 2` floor in R2 exists for this reason. The planner may add a note if a volume outlier looks like a data artefact rather than a market event — but it must still be flagged and explained, not silently dropped.
5. **Dependency addition:** `scikit-learn` is new for this portfolio (Days 1–2 used only pandas/numpy/requests/plotly/streamlit). The planner must add it pinned to `requirements.txt` and confirm CI installs it.

---

## Handoff (researcher → planner)

**What was produced:** exactly one file — `day-03-crypto-market-anomaly-detector/research_brief.md` (this file). No live data was fetched; no other file was written.

**Verified numbers:**
- Window 2025-11-07 → 2026-11-07; `from=1762473600`, `to=1794009600` (computed via `python3`, cross-checked as Day 2's timestamps +86,400 s).
- Expected ~1,095 rows (365 × 3 coins); ~1,005 flaggable rows after the 30-day warm-up.
- Endpoint `GET /api/v3/coins/{id}/market_chart/range?vs_currency=usd&from=1762473600&to=1794009600`, verified working keyless on Days 1–2; fallback `market_chart?days=365`; 3 calls, ≥5 s spacing, one 429 retry after 60 s.
- Synthetic GBM fallback unchanged from Days 1–2 (seed 42; BTC drift 0.0008 σ 0.035, ETH 0.0006/0.045, SOL 0.0005/0.06).

**Key decisions:**
- Baseline rolling z-score rules (R1 return shock, R2 volume surge, R3 joint shock) + Isolation Forest on 5 engineered features; contamination set from the baseline flag rate.
- Evaluation only on injected anomalies (~30, three types) plus baseline-vs-model overlap — no ground-truth manipulation label exists.
- "Good" = union recall ≥ 0.80, precision ≥ 0.50, Jaccard overlap ≥ 0.30, baseline flag rate 2–5%.
- Every flag labelled "unusual pattern requiring investigation" — never manipulation.

**Known gaps:** contamination value not yet fixed (procedure defined, value set at build time); `scikit-learn` is a new dependency needing a pinned version; Day 1/2 caches do not cover Day 3's window, so there is no valid cache fallback until a Day 3 fetch succeeds.

**Planner's first step:** take this brief as the source of truth for data, metrics, and evaluation targets, and write `plan.md` — starting with the exact file tree (including `anomaly_timeline.csv`, `injected_anomalies.csv`, and the evaluation outputs) and the per-file responsibilities for the coder.
