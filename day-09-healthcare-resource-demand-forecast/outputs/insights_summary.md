# Day 09 — Healthcare Resource Demand Forecast: Insights

**Data:** CDC NSSP ED visits (25,116 rows, 161 weeks, 2023-10-07 → 2026-10-31) + HHS bed capacity (81,713 rows, 2020-01-01 → 2024-04-27). Fetched live 2026-11-13. Both sources are US federal public-domain data. Analytical exercise on public aggregate surveillance data — **not a clinical or operational decision tool.**

## Finding 1 — The next 8 weeks: a steep climb into Surge (Q1)

The published Holt-Winters forecast has national Combined respiratory ED share rising from **3.03%** (week ending 2026-11-07) to **13.87%** (week ending 2026-12-26), with bands Moderate, Moderate, High, High, Surge, Surge, Surge, Surge. The 80% prediction interval on the final week is 12.76–14.91% and the 95% interval is 12.08–15.38% (residual bootstrap, seed 42, 1,000 paths). The latest observed week (2026-10-31) is **2.3%** — COVID-19 0.5%, Influenza 1.7%, RSV 0.1%.

The season is already running hotter than last year: influenza is at 1.7%, **73.9% of the Combined total** and nearly six times its 0.3% on the same week last year (2025-11-01, Combined 0.7%). Last winter rose from 2.4% to 10.0% in eight weeks, so a steep climb is the normal seasonal shape — but the forecast's final two weeks **exceed the observed historical maximum of 10.4%** (2023-12-30). Read weeks 7–8 as a severe-season scenario, not a roster plan on their own. Chart: `outputs/charts/01_forecast.png`.

## Finding 2 — The forecast is honest, and its weak spot is interval coverage (Q2)

Holt-Winters beats the seasonal-naïve baseline clearly on point accuracy: mean backtest RMSE **0.47 pp vs 0.82 pp**, MAE 0.42 vs 0.78 pp, MAPE 42.19% vs 80.63% (3 rolling origins, 4-week horizons). It wins 2 of the 3 origins on RMSE; seasonal naïve wins the origin-8 window (0.39 vs 0.59 pp), so the win is real but not a sweep. MAPE is the least trustworthy of the three metrics — it inflates when Combined % sits near 1–2% in summer (naïve origin-12 MAPE is 149.17% on actuals near 0.7%).

The weak spot is interval coverage: the 80% intervals covered **75%** of held-out actuals for Holt-Winters (0.75 / 0.50 / 1.00 across origins) vs **92%** for seasonal naïve (1.00 / 1.00 / 0.75) against the ≈80% target. The naïve intervals are wider because its residuals are larger, so they cover more; Holt-Winters is sharper but slightly under-covers at one origin. The published intervals should be read as slightly optimistic. Chart: `outputs/charts/02_backtest.png`.

## Finding 3 — Surge is a real level, Hawaii is already there, and beds are history (Q3)

**Bands:** over 161 weeks, Low 89, Moderate 35, High 19, Surge **18** — Surge (>6%) occurred in 18 weeks, most recently 2026-01-03, so the band is an observed level, not a decorative threshold. **Geography:** the latest-4-week mean Combined % is highest in **Hawaii at 7.0% — already in Surge** — then Florida (3.4%), Louisiana (2.9%), Washington (2.8%) and Texas (2.6%). The highest single state-week ever recorded is North Carolina, 19.1% (2023-12-30).

**Staffing scenario (PLANNING ASSUMPTIONS — not measured data):** the forecast implies Moderate staffing for two weeks, High (+10% rostered shifts) for two weeks, then Surge posture (+25% rostered shifts + elective-deferral trigger) for the final four weeks. At the dashboard defaults (1,000 ED visits/week, 15% admission rate), the peak forecast week implies ~139 respiratory visits and ~21 admissions that week.

**Capacity side:** national inpatient bed utilisation averaged 72.5% over 2020–2024 (max 78.9%, week ending 2022-12-10) and was 74.95% in its final week, with adult ICU occupancy 71.65%. But the bed series **ends 2024-04-27** — it is a historical record, not current capacity — and its early-2020 weeks cover as few as 3 reporting states. Chart: `outputs/charts/03_demand_bands.png`, `outputs/charts/04_bed_capacity.png`.

## Recommendation

**Prepare Surge posture for mid-December, but stage it in two steps.** The forecast's first four weeks (Moderate → High) are inside the observed historical range and well supported by the backtest; the Surge weeks (from 2026-12-05) rest on an additive trend extrapolating past the observed maximum. A system acting on this should roster the +10% High uplift for the weeks ending 2026-11-21 and 2026-11-28, and treat the +25% Surge uplift as a contingency to confirm against the next two weeks of observed data before committing elective deferrals — re-running this same pipeline weekly costs one command and is the correct update cadence for a forecast whose outer weeks exceed history.

## Limitations

- The ED series is a **share** of visits, not a count — visit and admission numbers come only from the user-entered volume assumption (defaults 1,000/week, 15%).
- The forecast's outer weeks exceed the observed historical maximum (10.4%); the additive-trend Holt-Winters model has no ceiling and was not tuned (plan-fixed, no grid search).
- 80%-interval coverage (75%) is slightly below its ≈80% target; intervals are a touch narrow.
- MAPE inflates in low summer weeks; RMSE is the honest comparator.
- The bed series ends 2024-04-27; early-2020 weeks cover 3–38 states. Its dashed 8-week extension in chart 04 is a method illustration, not a capacity prediction.
- Iowa has reported nothing since 2026-07-04; Delaware and Georgia nothing since 2026-10-17 (national series unaffected, 0 weeks).
- 72 NULL `percent_visits` rows (0.29%) treated as missing, never 0.
- SARIMA was kept out of scope (plan §11); it remains future work, as does re-fitting with a damped trend if the outer-week overshoot persists.
