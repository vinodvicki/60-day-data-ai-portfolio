# Day 02 — Crypto Risk & Volatility Analyzer: Insights

*Plain-language risk notes for a non-expert reader. All numbers come from
`data/processed/crypto_risk_summary.csv` and `data/processed/crypto_correlations.csv`
(window 2025-11-06 → 2026-11-06, 366 days per coin). Educational analysis only —
not investment advice. Past volatility and drawdowns do not predict future risk.*

## Finding 1 — Drawdown: every coin fell a long way from its peak, and none climbed back

A **drawdown** is how far the price fell from its highest point, and how long it took to climb back. Think of it as the worst dip you would have had to sit through.

- **Solana fell furthest: −62.9%.** It peaked at $167.38 on 2025-11-11 and bottomed at $62.18 on 2026-06-07 — a 208-day slide — and had still not recovered by 2026-11-06 (152 days after the bottom). It closed the window 46.7% below its peak.
- **Ethereum fell −56.2%** (peak $3,578.80 on 2025-11-10 → trough $1,566.01 on 2026-06-26, 228 days), also not recovered, closing 37.5% below its peak.
- **Bitcoin fell least, −44.7%** (peak $105,951.50 on 2025-11-11 → trough $58,566.09 on 2026-07-01, 232 days), also not recovered, closing 28.3% below its peak.
- All three coins spent about **360 of the 366 days underwater** — below a previous high — so there was almost no point in the year when a holder was sitting at a new high.

See `outputs/charts/01_drawdown.png`.

## Finding 2 — Volatility: Solana was the jumpiest, Bitcoin the calmest

**Volatility** is how jumpy day-to-day moves were. A 60% annualised volatility means daily moves were typically large enough that, if they kept up that pace for a year, prices would swing by roughly that much.

- **Solana** averaged **59.6%** annualised 30-day volatility (median 59.7%, worst stretch 106.5% on 2026-02-28).
- **Ethereum** averaged **57.4%** (median 56.3%, worst 104.2% on 2026-02-26).
- **Bitcoin** averaged **41.5%** (median 39.9%, worst 82.5% on 2026-03-05) — clearly calmer than the other two, but still very jumpy by the standards of most investments.
- All three hit their jumpiest stretch in **late February / early March 2026**, at the same time.

See `outputs/charts/02_rolling_volatility.png`.

## Finding 3 — Correlation: the coins fell together, so holding all three gave little protection

**Correlation** measures whether the coins tended to move together. +1 means they moved in lockstep; 0 means no link. High correlation means little protection from holding more than one — when one falls, the others usually fall too.

- Full window: **BTC–ETH 0.91, BTC–SOL 0.87, ETH–SOL 0.88.**
- Latest 90 days: **BTC–ETH 0.90, BTC–SOL 0.85, ETH–SOL 0.84** — still very high, so the coins did not start moving independently near the end of the window.
- In plain terms: spreading money across these three coins did **not** spread the risk much, because they behaved almost like one asset.

See `outputs/charts/03_correlation_heatmap.png`.

## Finding 4 — Risk-adjusted return: the worst faller was also the worst deal per unit of risk

**Sharpe and Sortino** measure how much return you got for each unit of risk you took — higher is better, but only on past data. (Both use a 0% risk-free rate here, so they are pure return-per-unit-of-volatility. Sortino counts only downside moves, so it is higher than Sharpe when a coin's volatility was mostly upside.)

- Every Sharpe and Sortino is **negative**, because all three coins lost money: total returns were **BTC −26.8%, ETH −34.7%, SOL −45.1%**. So the ranking is about who lost least per unit of risk.
- **Ethereum was least bad (Sharpe −0.41, Sortino −0.59)**, then Bitcoin (−0.49 / −0.69), then Solana (−0.65 / −0.92).
- The coin with the highest total loss (Solana, −45.1%) also delivered the worst return per unit of risk — the extra risk bought no extra return over this window.

See `outputs/charts/04_risk_adjusted_returns_var.png`.

## Finding 5 — Tail risk: how bad was a bad day?

**VaR 95%** answers "on a typical bad day, how much could I expect to lose?" — it is the loss that was beaten on only 5% of days. **CVaR 95%** answers "on the very worst days, how bad was it on average?"

- **Bitcoin:** on 95% of days the loss was no worse than **−3.4%**; on the worst 5% of days the average loss was **−5.0%**.
- **Ethereum:** VaR 95% **−4.7%**; average loss on the worst 5% of days **−6.8%**.
- **Solana:** VaR 95% **−5.3%**; average loss on the worst 5% of days **−7.1%**.
- So a bad day for Solana was roughly one-and-a-half times as bad as a bad day for Bitcoin, and the very worst days were worse still — the tail is heavier than the typical bad day suggests.

See `outputs/charts/04_risk_adjusted_returns_var.png`.

## Finding 6 — Exposure summary: which coin carried the most risk overall?

**Solana carried the most risk on every measure**: the deepest drawdown (−62.9%), the jumpiest daily moves (59.6% mean volatility), the worst bad days (VaR −5.3%, CVaR −7.1%) and the worst return per unit of risk (Sharpe −0.65). **Ethereum sat in the middle** on drawdown (−56.2%), volatility (57.4%) and tail risk (VaR −4.7%), with the least-bad risk-adjusted return (Sharpe −0.41). **Bitcoin was the calmest of the three** (drawdown −44.7%, volatility 41.5%, VaR −3.4%) while still losing 26.8% and closing 28.3% below its peak. And because the three coins moved together (correlations 0.84–0.91), holding all three did not diversify the risk away — the portfolio's risk was close to the risk of its riskiest coin.

## Recommendation (analytical next step — never investment advice)

**Re-run this same risk check on a rolling basis and watch two things:** (1) whether the latest-90-day correlations stay above ~0.85 — if they fall, the coins are starting to move independently and holding more than one would begin to offer real protection; and (2) whether any coin's 30-day volatility breaks above its 2026-02/03 peak (BTC 82.5%, ETH 104.2%, SOL 106.5% annualised) or its current drawdown deepens past its max drawdown — either would mean the risk regime has got worse than anything in this window. A useful next analysis is to repeat the drawdown/volatility/VaR comparison against a non-crypto asset (for example a broad stock index) to see how much of this risk is crypto-specific.

## Limitations

- One 365-day window (2025-11-06 → 2026-11-06); a different window could rank the coins differently.
- Close prices only, daily granularity — intraday falls worse than the daily close are not captured.
- Sharpe/Sortino use a 0% risk-free rate and all three coins fell, so the ratios compare losses per unit of risk, not gains.
- VaR/CVaR are historical, one-day figures on past daily returns; they describe how bad past bad days were, not how bad a future one could be.
- No buy/sell recommendation, no price prediction, no investment advice.
