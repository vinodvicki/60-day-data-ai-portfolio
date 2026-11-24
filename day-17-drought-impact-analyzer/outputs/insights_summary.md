# Day 17 — Drought Impact Analyzer: Insights

**Question:** how much does drought severity move with US maize yield —
across years nationally, and across counties in the Corn Belt — and can a
precipitation anomaly explain the same signal more simply?
**Window:** 2000–2025 (26 years; 1,357 USDM weeks per state; 201 counties).
All numbers below match the committed CSVs in `data/processed/`.

## Finding 1 — Drought severity tracks detrended yield closely

Growing-season mean DSCI (Iowa + Illinois average) vs the yield residual
after removing the +0.116 t/ha/yr technology trend: **Pearson r = −0.61,
p = 0.0009, R² = 0.38 (n = 26)**. The OLS slope is −0.0076 t/ha per DSCI
point — each extra 100 DSCI points in the growing season is associated
with about **0.76 t/ha (12 bu/acre) less yield**. The raw-yield
correlation is far weaker (r = −0.30, p = 0.14): the technology trend
masks the drought signal until it is removed, which is why the detrended
result is the primary one. Chart: `02_drought_vs_yield.png`.

## Finding 2 — Rain totals alone do not explain yield

Growing-season precipitation anomaly vs detrended yield: **r = +0.27,
p = 0.18** (not significant); July precipitation anomaly alone:
**r = +0.24, p = 0.23**. The Drought Monitor's blend — rain, temperature,
soil moisture and impacts — carries more yield signal than rain totals
alone. The contrast year is 2023: a bigger growing-season rain deficit
than 2012 (−194 mm vs −183 mm) but near-normal July rain (+3 mm vs
−70 mm in 2012) — and yield only 0.11 t/ha below trend, against 2.24 t/ha
below trend in 2012. Timing (July, the silking month) matters more than
the season total. Chart: `03_precip_anomaly.png`.

## Finding 3 — 2012 is the case study; Iowa took the worst of it

**2012:** growing-season DSCI 200.4 (Iowa 204.2, Illinois 196.6) — the
worst in the series by 52 points over the next-worst year (2023, 148.1);
30 weeks with DSCI ≥ 100; rain −183 mm (−31%); yield 7.73 t/ha, the
lowest in 26 years and 2.24 t/ha below trend. Worst-hit county in 2012:
Massac County, IL (73.9% of the county in D2+ drought).
**Counties:** the 15 hardest-hit counties by 26-year mean D2+ share are
all in Iowa. Davis County tops the ranking (12.7% of area in D2+ on
average; worst year 2023, 67.3%), followed by Buena Vista (12.6%) and
Wapello (12.3%). The single worst county-year is Woodbury County, IA in
2023: 97.7% of the county in D2+ drought across the growing season.
Southern Illinois is the least exposed — Hancock County, IL leads the
state at 7.2%. Chart: `04_county_map.png`.

## Forecast — 2026 DSCI (AR(1), a statistical extrapolation)

Backtest on 2025 (fit 2000–2024): AR(1) forecast 49.0 vs actual 57.9
(absolute error 8.8 DSCI points); naive last-year forecast 48.6 (error
9.3). The AR(1) barely beats naive — annual drought severity is close to
a random walk. Refit on all 26 years, the **2026 forecast is 50.2, with a
±1 residual-std interval of 1.8–98.5** — a near-average year, but the
interval is so wide the forecast is barely more informative than the
mean. This is a statistical extrapolation, not a weather forecast.

## Recommendation (analytical next step — never investment advice)

Add county-level yields when a USDA Quick Stats key is available, and
re-run the county analysis as drought-severity vs yield **within**
counties: the current county ranking is drought exposure only, and the
yield relationship is proven only at year level. The next most valuable
single addition is July soil-moisture or evapotranspiration as a
predictor — the 2023-vs-2012 contrast suggests silking-month water stress
is the mechanism, and rain totals do not capture it.

## Limitations

- National yield, 2-state drought/weather (Iowa + Illinois, ~35% of US
  corn output) — a proxy, not a national average.
- No county yields (USDA Quick Stats needs a key); the county analysis is
  drought severity by county.
- Association, not causation; n = 26 annual rows; p-values reported with
  every correlation.
- The AR(1) 2026 forecast is a statistical extrapolation, not a weather
  forecast.
- Weekly county raw CSVs (~24 MB) are not committed; the committed
  `county_year.csv` aggregates are the auditable record.
