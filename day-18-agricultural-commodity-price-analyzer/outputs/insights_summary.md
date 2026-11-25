# Day 18 — Agricultural Commodity Price Analyzer: Insights

**Status:** VERIFIED — all numbers match the committed CSVs in
`data/processed/` (2026-11-25).

## Finding 1 — Seasonality is small and pre-harvest

Prices peak in late spring and trough at harvest, on both the full
window (1992–2026) and the last 10 full years (2016–2025). Seasonal
index (1.00 = annual mean):

| Commodity | Peak month | Index | Trough month | Index | Amplitude |
|---|---|---|---|---|---|
| Maize | May | 1.037 | Sep | 0.968 | 0.069 |
| Wheat | May | 1.031 | Aug | 0.983 | 0.048 |
| Soybeans | Jun | 1.042 | Oct | 0.942 | 0.099 |

On the last 10 years maize still peaks in May (1.053) and wheat in May
(1.086); soybeans peak in May (1.035) instead of June. The seasonal
swing is worth roughly 5–10% — real money on a harvest, but small next
to the shocks in Finding 2. (Chart: `02_seasonality.png`.)

## Finding 2 — The shocks dwarf the seasons

Worst peak-to-trough drawdowns: wheat **−69.65%** (Mar 2008 → Nov 2016),
maize **−63.21%** (May 1996 → Jul 2000), soybeans **−50.99%** (Aug 2012 →
May 2019). 76 shock months flagged (|monthly log return| ≥ 2× the
rolling 24-month return std): maize 21, wheat 30, soybeans 25. Largest
single-month moves: wheat −26.0% (Oct 2008), maize −25.2% (Sep 1996),
wheat +25.0% (Jul 2012). Maize over the named windows: 2007–08
food-price crisis +73.85%; 2012 US drought +15.49%; 2020 COVID trough
−14.67%; 2022 Russia–Ukraine war spike +14.71%. Maize 12-month rolling
volatility peaked at 40.8% annualised in Nov 2008; wheat at 47.1% in
Oct 2008. (Charts: `01_price_levels.png`, `03_volatility_shocks.png`.)

## Finding 3 — No significant annual weather/drought association (the honest null)

Across 26 annual points (2000–2025), YoY price change vs growing-season
temperature, precipitation and DSCI: every |r| ≤ 0.15, every p-value
above 0.46. The maize OLS regression on DSCI + precipitation anomaly
has R² = 0.016 (p = 0.552 / 0.647). Global benchmark prices move on
global supply and demand, not on two-state Corn Belt weather in the
same year. The 2012 drought *does* show in the monthly data — maize
jumped +22.0% in July 2012 alone, the largest positive maize month in
the series — but the 2012 annual mean rose only +2.26% YoY because
prices were already high in 2011. In 2012 the Corn Belt averaged a
growing-season DSCI of 200.4 with precipitation 182.7 mm (−30.7%)
below the 2000–2025 mean; Massac County, IL had 73.9% of its area in
severe+ (D2+) drought, Pulaski County 72.3%, Hardin County 71.7%.
The three crops move together: monthly log-return correlations
maize–soybeans 0.624, maize–wheat 0.546, wheat–soybeans 0.481.
(Chart: `04_county_map.png`.)

**Forecast (labelled extrapolation, not a market prediction).**
Holt-Winters on monthly maize prices, 12 months ahead (Oct 2026 →
Sep 2027): $239.56/t in Oct 2026, $252.31/t in May 2027, $240.81/t by
Sep 2027 (80% interval ±$33.14/t). Backtest on 3 origins:
Holt-Winters mean RMSE $23.38/t vs $41.74/t for the seasonal-naïve
baseline (same month last year).

## Recommendation

**Sell into the late-spring peak and do not count on the weather to
tell you the annual price.** The seasonal edge is 5–10% (maize peaks
in May, troughs at harvest in September); the drawdown risk is 50–70%.
A planner should treat May as the selling window, keep storage for the
harvest trough, and hedge the shock risk — the 2008 and 2012 moves show
a single month can move prices 25%. The weather/drought join is not a
pricing signal at the annual level: use the monthly shock watch (this
dashboard's shock table) instead of an annual weather model.
