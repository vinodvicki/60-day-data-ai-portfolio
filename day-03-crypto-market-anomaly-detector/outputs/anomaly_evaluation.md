# Day 03 — Crypto Market Anomaly Detector: Evaluation Report

*The report card on the detector itself. All numbers are recomputed from
`data/processed/anomaly_timeline.csv`, `data/processed/injected_anomalies.csv`
and `data/processed/crypto_daily_injected.csv` (window 2025-11-07 → 2026-11-07).
Educational analysis only — not investment advice. Anomalies flagged here are
statistical outliers in price and volume. They are not evidence of
manipulation, and no flagged pattern should be presented as such.*

## The ground-truth problem

There is no ground-truth manipulation label for real crypto data: no public
dataset labels which historical days were manipulation, and the roadmap
explicitly forbids presenting anomalies as proven manipulation. Evaluation is
therefore done on **injected anomalies only** (30 planted anomalies of known
type, §2), plus a baseline-vs-model comparison (§1).

## 1. Baseline vs model comparison (real data)

Contamination for the Isolation Forest was set equal to the observed baseline
flag rate: **0.0368** (37 baseline flags / 1,005 flaggable rows). The first 30
days per coin are a warm-up with no z-scores (return_z is first valid on day
31; volume_z on day 60), so the flaggable universe is 1,005 rows, not 1,098.

### Per coin and overall

| Coin | Flaggable rows | Baseline flags | Baseline rate | Forest flags | Both | Baseline-only | Forest-only | Total flagged |
|---|---|---|---|---|---|---|---|---|
| Bitcoin (BTC) | 335 | 14 | 4.2% | 13 | 8 | 6 | 5 | 19 |
| Ethereum (ETH) | 335 | 13 | 3.9% | 13 | 8 | 5 | 5 | 18 |
| Solana (SOL) | 335 | 10 | 3.0% | 13 | 6 | 4 | 7 | 17 |
| **Overall** | **1,005** | **37** | **3.7%** | **39** | **22** | **15** | **17** | **54** |

### Flags by rule (a day can trigger several rules)

| Rule | Overall | BTC | ETH | SOL |
|---|---|---|---|---|
| R1 — return shock (\|return_z\| ≥ 3) | 27 | 12 | 10 | 5 |
| R2 — volume surge (volume_z ≥ 3 and volume_ratio ≥ 2) | 11 | 3 | 4 | 4 |
| R3 — joint shock (\|return_z\| ≥ 2 and volume_z ≥ 2) | 15 | 5 | 4 | 6 |

### Flags by severity

| Severity | Overall | BTC | ETH | SOL |
|---|---|---|---|---|
| High | 10 | 4 | 3 | 3 |
| Medium | 23 | 9 | 9 | 5 |
| Low | 21 | 6 | 6 | 9 |

### Overlap

- **Jaccard overlap (both ÷ union) = 22 / 54 = 0.407** (target ≥ 0.30 — **PASS**).
- The methods flag comparable counts by construction (contamination = baseline
  rate), so the remaining difference is about *which* days: 15 baseline-only
  days are mostly sharp single-variable moves the forest ranked just below its
  cut-off, and 17 forest-only days are joint patterns no single rule catches.

## 2. Injected-anomaly evaluation (±1-day tolerance, n = 30)

30 anomalies were planted in a copy of the daily frame (never in the real
data), each built from the coin's trailing 30-day window ending the day
before the injection, per the §4.4 amendment: 10 price spikes (the day's
return set to +4.0 × the trailing return std, reversing the next day), 10
volume surges (volume set to 5.0 × the trailing mean volume, no price
change), 10 joint shocks (return +3.0 × the trailing return std and volume
5.0 × the trailing mean volume). One per calendar month per coin, 10 per
coin; every injection is recorded in `data/processed/injected_anomalies.csv`
with a `construction` column stating how it was built. The identical
baseline + forest pipeline ran on the injected copy. A mandatory harness
self-check asserts every plant clears its target rule's bar on the injected
frame (price spike |return_z| ≥ 3; volume surge volume_z ≥ 3 and
volume_ratio ≥ 2; joint shock |return_z| ≥ 2 and volume_z ≥ 2) — all 30
plants pass. The tightest margin is the joint shock on SOL 2026-09-19
(volume_z 2.07, bar ≥ 2); the other two plants that failed the original
3.0× joint volume are SOL 2026-08-26 (volume_z 2.46) and ETH 2026-09-02
(2.41). The joint volume multiple is 5.0×, not 3.0×, because 3.0× failed
the self-check on those three plants and 4.0× was verified by exact
simulation to fail too (SOL 2026-09-19 volume_z 1.76) — the trailing
log-volume-ratio mean (0.32) cannot be ignored in the z-score arithmetic.

### Precision / recall / F1 per method

Precision is flag-level under the amended rule: a flag is a true positive
if it matches (same coin, ±1 day) an injected anomaly **or** a flag the
detector also raises on the clean (uninjected) data — the injected copy
still contains all 54 genuine unusual real days, so reproducing a
clean-data flag is the detector doing its real job, not an error. A flag
counts as a false positive only if it matches neither. Recall is matched
injections ÷ 30. "TP" below is matched injections (the recall numerator);
precision uses TP flags (injections + clean flags matched), shown in
parentheses.

| Method | TP (of 30) | FP | Flags | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Baseline rules | 30 | 0 | 60 | 1.000 (60 TP flags) | 1.000 | 1.000 |
| Isolation Forest | 22 | 2 | 60 | 0.967 (58 TP flags) | 0.733 | 0.834 |
| **Union (either method)** | **30** | **2** | **78** | **0.974 (76 TP flags)** | **1.000** | **0.987** |

Jaccard on the injected run is 0.538 (42 both / 78 union). The forest's
two false positives are flags that appear only on the injected run and
match neither an injection nor a clean-data flag; the baseline has none.

### Per-type recall (union method)

| Type | Found | Recall |
|---|---|---|
| Price spike | 10 / 10 | 1.00 |
| Volume surge | 10 / 10 | 1.00 |
| Joint shock | 10 / 10 | 1.00 |

### Missed injections (union)

None — the union finds all 30 planted anomalies. The baseline rules alone
also miss none. The Isolation Forest alone misses 8, all volume surges:

| Date | Coin | Type |
|---|---|---|
| 2026-04-06 | Ethereum | volume_surge |
| 2026-04-28 | Bitcoin | volume_surge |
| 2026-05-30 | Solana | volume_surge |
| 2026-06-11 | Ethereum | volume_surge |
| 2026-06-24 | Bitcoin | volume_surge |
| 2026-07-05 | Solana | volume_surge |
| 2026-07-20 | Bitcoin | volume_surge |
| 2026-08-16 | Ethereum | volume_surge |

## 3. Targets — pass / fail

| Metric | Target | Actual | Verdict |
|---|---|---|---|
| Injected-anomaly recall (union) | ≥ 0.80 | 1.000 (30 / 30) | **PASS** |
| Injected-anomaly precision (union) | ≥ 0.50 | 0.974 (76 / 78 flags) | **PASS** |
| Baseline-vs-forest overlap (Jaccard, real data) | ≥ 0.30 | 0.407 | **PASS** |
| Baseline flag rate on real data | 2–5% of post-warm-up days | 3.7% (37 / 1,005) | **PASS** |
| Per-type recall — price spike | ≥ 0.60 | 1.00 | **PASS** |
| Per-type recall — volume surge | ≥ 0.60 | 1.00 | **PASS** |
| Per-type recall — joint shock | ≥ 0.60 | 1.00 | **PASS** |

## 4. Diagnosis — no misses, one remaining method-level blind spot

**All five §4.4 targets pass on the regenerated evaluation** (see §3).
This is the second rework of the evaluation design, not a detector change:
the §4.4 amendment rebuilt the injections relative to trailing history
(price spike +4.0σ_ret, volume surge 5.0× trailing mean volume, joint
shock +3.0σ_ret / 5.0× trailing mean volume, with the mandatory harness
self-check) and fixed the precision rule so genuine unusual real days
count as true positives, and amendment 2 raised the joint volume multiple
from 3.0× to 5.0× after 3.0× failed the self-check on three plants. The
detector itself — R1–R3 thresholds, Isolation Forest, features — is
unchanged from the original build, and the real-data flags are unchanged
(54 flags, Jaccard 0.407, baseline rate 3.7%).

**The forest alone still misses volume-only surges.** The forest finds
22 of 30 injected anomalies; all 8 misses are volume surges (listed in
§2). The mechanism: a single high-volume day with an ordinary return is
not, on its own, among the most anomalous 3.7% of days on the forest's
five features — the forest needs a joint pattern (return + volume +
volatility) to rank a day that high. The baseline rules catch all 8, so
the union misses none, but a forest-only reading would under-detect
volume-only events. This is a known limitation of the forest in
isolation, stated here rather than hidden in the union average.

**What was not done:** thresholds were fixed in the plan before evaluation ran
and were **not** tuned to make the injected set pass. The injection
magnitudes and the precision rule were fixed by the planner's amendments
because the original measurement was defective (planted anomalies that
were not anomalous relative to history; genuine real days scored as
false positives) — the detector was never re-tuned after seeing a
number. The remaining honest caveat is the thin self-check margin on the
worst joint plant (SOL 2026-09-19, volume_z 2.07 against a bar of 2):
the pipeline is fully deterministic (committed CSVs, seed 42, fixed
algorithm), so 2.07 is the exact reproduced value, and the self-check
will fail loudly if any future data change erodes it.
