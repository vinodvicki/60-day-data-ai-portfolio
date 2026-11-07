# Day 03 — Crypto Market Anomaly Detector: Insights

*Plain-language anomaly notes for a non-expert reader. All numbers come from
`data/processed/anomaly_timeline.csv` and `outputs/anomaly_evaluation.md`
(window 2025-11-07 → 2026-11-07, 366 days per coin). Educational analysis only —
not investment advice. Anomalies flagged here are statistical outliers in price and volume. They are not evidence of manipulation, and no flagged pattern should be presented as such.*

## Finding 1 — 54 unusual days, spread evenly across the three coins

An **unusual day** is a day whose price or volume move stood out from that coin's own recent behaviour — measured against its trailing 30 days, not against the other coins and not against the whole year at once. A −8% day in a calm month is unusual; the same −8% day in a month when every day moved ±6% is not.

- **54 days were flagged** out of 1,005 flaggable days (the first 30 days per coin are a warm-up with no z-scores). That is 37 days by the transparent z-score rules (R1–R3) and 39 by the Isolation Forest, with 22 flagged by both.
- **Bitcoin had the most flags (19), then Ethereum (18), then Solana (17)** — no coin dominated. By rule: return shocks (R1) were the commonest trigger (27 days), then joint shocks (R3, 15 days), then volume surges (R2, 11 days).
- **10 flags were High severity, 23 Medium, 21 Low.** High means a move of at least 4 trailing standard deviations, or two rules firing together.
- The flags were **not** spread evenly through the year: **16 of the 54 fell in February 2026 and 11 in August 2026** — the two sharpest stretches of the year — while April, May and July 2026 had none at all.

See `outputs/charts/01_anomaly_timeline.png` and `outputs/charts/03_flag_counts_severity.png`.

## Finding 2 — The two methods mostly agree, and the disagreements are informative

The Isolation Forest's contamination was set equal to the baseline flag rate (3.7%), so both methods flag about the same *number* of days — the interesting question is *which* days.

- **22 days were flagged by both methods, 15 by the rules only, 17 by the forest only.** The overlap (Jaccard) is 0.41 — comfortably above the 0.30 target — so the methods substantially agree.
- **A day flagged by both deserves more confidence** than a day flagged by only one. All 10 High-severity flags were flagged by both methods, including the single most extreme day for all three coins: **2026-08-20**, when Ethereum rose 17.5% (return z = 10.8, volume 3.8× its 30-day average), Solana rose 10.8% (z = 6.6, 3.2×) and Bitcoin rose 7.1% (z = 5.8, 2.1×).
- **Forest-only flags are the joint patterns no single rule catches.** For example, Ethereum rose 6.2% on 2025-12-10 (return z = 1.8, volume 1.2× its average, 30-day volatility 68% annualised) — no rule crossed its threshold, but the combination of a solid rise, slightly heavy volume and elevated volatility was jointly unusual. The timeline says so explicitly for every forest-only flag, instead of pretending a rule fired.
- The worst sell-off flag was **Bitcoin −14.1% on 2026-02-06** (return z = −5.7), in the February cluster.

See `outputs/charts/02_return_volume_scatter.png` and `outputs/charts/03_flag_counts_severity.png`.

## Finding 3 — The detector finds all planted anomalies; the forest alone misses volume-only surges

Because there is no labelled record of which real days were "real" anomalies, the detector was tested on **30 deliberately planted anomalies** of known type, each built from the coin's trailing 30-day window (price spikes +4.0× the trailing return std, volume surges 5.0× the trailing mean volume, joint shocks +3.0× trailing std and 5.0× trailing mean volume), with a ±1-day tolerance. A harness self-check confirms every plant clears its target rule's bar before it enters the evaluation.

- **The two methods together found 30 of 30 (recall 1.00, target ≥ 0.80)** — price spikes 10 of 10, volume surges 10 of 10, joint shocks 10 of 10. The baseline rules alone also found all 30.
- **Precision was 0.974 (target ≥ 0.50).** Of the 78 flags on the injected copy, 76 are either planted anomalies or genuine unusual real days the detector also flags on the clean data; only 2 are false positives. A single flag should still be treated as a starting point for investigation, not a conclusion.
- **The Isolation Forest alone found only 22 of 30 — and all 8 misses were volume surges.** A single high-volume day with an ordinary return is not, on its own, among the most anomalous days on the forest's five features. The rules catch all 8, so the union misses none, but a forest-only reading would under-detect volume-only events.
- The full report card, including the per-method tables, is in `outputs/anomaly_evaluation.md`.

See `outputs/charts/04_evaluation.png`.

## Recommendation (analytical next step — never investment advice)

**Strengthen the forest's volume sensitivity:** the next iteration of this detector should give the Isolation Forest a way to see volume-only events — for example, a dedicated volume feature or a separate volume-only model — and then re-run the same 30 planted anomalies to see whether forest recall rises above its current 0.73 without the baseline flag rate leaving the 2–5% band. Until then, treat any single volume-only flag as weak evidence on its own, and put more weight on days flagged by both methods.

## Limitations

- Flagged days are statistical outliers in price and volume — unusual patterns requiring investigation. They are not evidence of manipulation, and no flagged pattern should be presented as such.
- A fixed ±3σ rule over-flags in volatile regimes and under-flags in calm ones; the trailing window mitigates this but does not remove it.
- Isolation Forest scores are relative rankings, not probabilities, and 365 days per coin is a small sample for unsupervised learning.
- The model cannot distinguish a genuine market event from a data error or from manipulation.
- Evaluation is on planted anomalies only; there is no ground-truth label for real market days.
