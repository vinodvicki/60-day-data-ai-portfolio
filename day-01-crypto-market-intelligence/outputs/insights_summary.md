# Day 1 — Crypto Market Intelligence: Insights Summary

**Window:** 2025-11-05 → 2026-11-05 (366 daily observations per coin)
**Source:** CoinGecko public API (`market_chart/range`, accessed 2026-11-05) — **real data, not synthetic**
**Scope:** descriptive analytics only. *Educational analysis only — not investment advice.*
No buy/sell recommendation, no price prediction.

## Summary table

| Coin | Total return | Mean 30d vol (ann.) | Max 30d vol (ann.) | Max drawdown | Peak → trough | Mean turnover |
|---|---|---|---|---|---|---|
| Bitcoin (BTC) | −20.7% ($101,481 → $80,443) | 41.5% | 82.5% (2026-03-05) | −44.7% | 232 days | 0.025 |
| Ethereum (ETH) | −26.2% ($3,285 → $2,423) | 57.4% | 104.2% (2026-02-26) | −56.2% | 228 days | 0.061 |
| Solana (SOL) | −38.5% ($155 → $96) | 59.7% | 106.5% (2026-02-28) | −62.9% | 208 days | 0.061 |

BTC–ETH correlation of daily returns: **0.906** full window (latest 90-day: 0.890);
BTC–SOL 0.869, ETH–SOL 0.875.

---

## Finding 1 — Momentum: a down year for all three, with Bitcoin losing least

Indexed to 100 on 2025-11-05, all three coins ended the window well below
their starting level (BTC 79.3, ETH 73.8, SOL 61.5). Bitcoin lost the least
(−20.7%), Ethereum lost more (−26.2%), and Solana lost the most (−38.5%).
The lead changed hands only early on: all three peaked within a week of the
start (BTC $105,952 on 2025-11-11, ETH $3,579 on 2025-11-10, SOL $167 on
2025-11-11) and none of them ever regained that peak by 2026-11-05.
*Chart: `outputs/charts/01_price_indexed.png`*

## Finding 2 — Volatility & drawdown: Bitcoin was the steadier coin, and the falls were deep and long

Bitcoin's average 30-day rolling annualised volatility was 41.5%, clearly
below Ethereum (57.4%) and Solana (59.7%); its worst 30-day volatility
(82.5%, early March 2026) was also below ETH's 104.2% and SOL's 106.5%
(both late February 2026). The same ordering shows in drawdowns: BTC's
worst fall from peak was −44.7% (peak $105,952 on 2025-11-11 → trough
$58,566 on 2026-07-01, 232 days peak-to-trough), ETH's was −56.2%
(228 days), and SOL's was −62.9% (208 days). None of the three had
recovered to its window peak by the end of the window.
*Charts: `outputs/charts/02_rolling_volatility.png`,
`outputs/charts/03_drawdown.png`*

**Manual validation:** BTC's max drawdown was recomputed by hand in
`notebooks/analysis.ipynb` — peak $105,951.50 (2025-11-11), trough
$58,566.09 (2026-07-01), `(trough / peak − 1) = −44.7237%` — matching the
pipeline's value exactly.

## Finding 3 — Liquidity: volume spiked in late August 2026, and ETH/SOL turned over far faster than BTC

Relative volume (daily volume / its 30-day mean) averaged ≈1.0 for all
three coins, but spiked to 3.0× for BTC (2026-08-22), 3.6× for ETH
(2026-08-20) and 4.0× for SOL (2026-08-23) — a clustered, cross-coin
volume surge in the same week, consistent with the three coins moving
together (BTC–ETH daily-return correlation 0.906). Turnover (volume /
market cap) tells a structural story: ETH (0.061) and SOL (0.061) turned
over roughly 2.5× faster than BTC (0.025) on average, i.e. a much larger
share of their market value changed hands each day.
*Chart: `outputs/charts/04_relative_volume.png`*

---

## Actionable recommendation (analytical next step — not investment advice)

**Extend the analysis in two directions before drawing any stronger
conclusions:** (1) add a fourth, non-crypto comparator (e.g. a broad equity
index) to test whether the late-February 2026 volatility spike and the
late-August 2026 volume surge were crypto-specific or market-wide; and
(2) track turnover weekly as a standing liquidity monitor, since the
2.5× ETH/SOL-vs-BTC turnover gap is the most persistent structural
difference in this window and the one most likely to matter for future
comparisons. Both steps reuse this pipeline unchanged — only the coin list
and a weekly aggregation are new.

## Limitations

- **Close prices only** — `market_chart` returns no open/high/low, so no
  ATR or intraday-range analysis was possible.
- **365-day public-API cap** — the window cannot be extended without a
  CoinGecko Pro key; the early-November 2025 peaks sit at the very start
  of the window, so the "peak" is partly an artefact of where the window begins.
- **Daily granularity** — intraday moves and the exact timing of the
  August 2026 volume spike are not visible.
- **Volume is a liquidity proxy** — exchange-reported 24h volume, not
  order-book depth; it can include wash trading and double-counting.
- **Correlation is not causation** — the 0.906 BTC–ETH correlation
  describes co-movement, not a driver.
- **One window, one market regime** — all three coins fell over this
  particular year; nothing here generalises to other periods.
