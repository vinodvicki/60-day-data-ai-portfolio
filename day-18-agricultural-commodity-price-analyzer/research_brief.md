# Day 18 — Agricultural Commodity Price Analyzer: Research Brief

**Status:** VERIFIED — one lean pass, 2026-11-25.
**Business question:** How do US agricultural commodity prices move through
the year and across years — seasonality, variability, and past shocks — so
a planner can time buying, selling, and storage decisions?

Roadmap entry (Phase 2, Agriculture & Farming): *"Study commodity price
seasonality, variability, and past shocks to support planning decisions."*
Deliverable: Commodity price tracking dashboard. Core skills: Regression,
weather joins, time-series forecasting, GIS. Suggested data: USDA Quick
Stats; NOAA weather; US Drought Monitor.

## 1. Data sources — verified 2026-11-25 (one pass, no re-search later)

### 1a. Commodity prices — FRED fredgraph.csv (NEW for Day 18, no key)

- **Endpoint:** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`
  — FRED's public graph-download endpoint. No key, no account, no login.
- **Verified calls (all HTTP 200, 2026-11-25):**
  - Maize (corn), IMF global price, USD per metric ton —
    `PMAIZMTUSDM`: 1992-01-01 → 2026-09-01, first 109.586, last 236.916.
  - Wheat, IMF global price, USD per metric ton — `PWHEAMTUSDM`:
    1992-01-01 → 2026-09-01, first 169.955, last 246.852.
  - Soybeans, IMF global price, USD per metric ton — `PSOYBUSDM`:
    1992-01-01 → 2026-09-01, first 208.610, last 481.722.
  - File format: two columns, `observation_date,<SERIES>`; monthly
    frequency; one row per month; ~12.5 KB per series.
- **Wrong ID found and discarded:** `PCORNUSDM` returns HTTP 404 (the
  series page is also 404). Maize is `PMAIZMTUSDM`, not `PCORNUSDM`.
  Do not use `PCORNUSDM` anywhere.
- **Latest-data lag:** the newest observation is 2026-09-01 for all three
  series (IMF source data lags ~2 months behind the build date). Disclose
  this on every surface: the window is 1992-01 → 2026-09, 417 monthly
  observations per commodity (2026 is a partial year: Jan–Sep only).
- **Terms / attribution:** FRED data is free to use with attribution.
  Underlying source is the IMF Primary Commodity Prices database.
  Attribute "Source: FRED (Federal Reserve Bank of St. Louis), IMF
  Primary Commodity Prices" on README, insights, notebook, dashboard.
- **Pipeline calls (exactly 3):** one fredgraph.csv download per series,
  cached as raw CSVs in `data/raw/`. Retry once after 10 s on a 5xx;
  stop after that and fall back to the committed cache
  (`--offline` / `--use-cache`).
- **Why FRED, not USDA:** see §1d. FRED is the documented no-key source
  the task brief names for this case, and it gives a clean monthly
  1992–2026 series for exactly the three row crops Days 16–17 studied.

### 1b. Weather join — reuse Day 16's verified Open-Meteo weather (do NOT re-fetch to verify)

- **Source:** Open-Meteo ERA5 archive API, no key —
  `https://archive-api.open-meteo.com/v1/archive`, daily
  `temperature_2m_mean,temperature_2m_max,precipitation_sum`,
  Iowa (41.8780, −93.0977) + Illinois (40.6331, −89.3985) centroids,
  2000–2025 (verified HTTP 200, 9,132 days Iowa 2000–2024, 0 missing,
  2026-11-23 by Day 16).
- **Reuse:** copy Day 16's committed raw weather JSONs
  (`weather_iowa.json`, `weather_illinois.json`) into this day's
  `data/raw/` and record the copy in `data_source.json` (source, fetch
  date 2026-11-23, copied from Day 16, not re-downloaded). The pipeline
  aggregates daily precipitation and mean temperature to growing-season
  (Apr–Sep) totals/means per state-year for the weather join.
- **NOAA GHCN-daily** (Des Moines station, HTTP 200, 5,106,240 B,
  2026-11-23, Day 16 brief §1c) is recorded as the roadmap's "NOAA
  weather" cross-check; not fetched (Open-Meteo already supplies the
  same daily fields).

### 1c. Drought join — reuse Day 17's verified USDM state DSCI (do NOT re-fetch to verify)

- **Source:** US Drought Monitor REST API, no key —
  `https://usdmdataservices.unl.edu/api/StateStatistics/GetDSCI`,
  Iowa (FIPS 19) + Illinois (FIPS 17), weekly, 2000–2025 (verified
  HTTP 200, 1,305 weekly rows per state, 2026-11-24 by Day 17).
- **Reuse:** copy Day 17's committed raw files (`dsci_iowa.csv`,
  `dsci_illinois.csv`) into this day's `data/raw/` and record the copy
  in `data_source.json`. The pipeline aggregates weekly DSCI to
  growing-season (Apr–Sep) mean DSCI per state-year for the drought join.
- **DSCI definition** (USDM): DSCI = 1×(% area D0) + 2×(% D1) + 3×(% D2)
  + 4×(% D3) + 5×(% D4). Range 0 (no drought) to 500 (whole area in D4).
- **GIS note:** Day 17 verified the plotly county GeoJSON
  (`https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json`,
  HTTP 200, 3,216,816 B, 3,221 features, 2026-11-24) — do NOT commit it
  (3.2 MB breaks the < 1 MB/file rule). The Day 18 county map, if the
  plan calls for one, fetches it at chart-build time with a 10 s timeout
  and falls back to the committed state-level choropleth (plotly
  `choropleth`, `locationmode = "USA-states"`, no external file) if the
  download fails. Day 17's committed `county_year.csv` (365,052 B,
  county × year growing-season D2+ share) may be reused as the map's
  data source instead of re-aggregating county data — the planner
  decides; either way the map shows where drought hit hardest in the
  worst shock year.

### 1d. USDA Quick Stats — NOT used (key required, none available)

- **Finding:** the USDA Quick Stats API returns HTTP 401 without a key
  (verified Day 16, brief §1a). A key needs a free USDA signup that
  cannot be completed from here. **No key is available to this run.**
- **Decision (per the task brief):** use the documented no-key source
  above (FRED commodity series, §1a) instead. **NEVER put any API key
  or credential in any file.** Record this substitution plainly in the
  README and insights as a disclosed limitation: prices here are IMF
  global benchmark prices via FRED, not USDA NASS farm-gate prices.
  A future run with a USDA key could swap in NASS state prices without
  changing the pipeline shape.
- **What the substitution costs:** global benchmark prices move with the
  same shocks as US farm prices (2012 drought, 2022 war spike) but are
  not state-level and are not farm-gate. The analysis therefore answers
  "when do prices spike and how big are the moves" at the national /
  global level, and joins them to Corn Belt weather/drought at the
  annual level. State this explicitly; do not present the series as
  USDA farm prices.

## 2. Metrics to compute

- **Monthly price levels** per commodity (USD/t), 1992-01 → 2026-09,
  417 months each; 2026 partial (Jan–Sep).
- **Seasonality:** mean price by calendar month (12 values per
  commodity), seasonal index = month mean / overall mean; peak and
  trough months; seasonal amplitude (max index − min index).
- **Variability:** annual mean, annual standard deviation of monthly
  log returns, coefficient of variation of the annual mean, max
  drawdown (peak-to-trough, %) and its dates, 12-month rolling
  volatility (std of monthly log returns).
- **Past shocks:** largest single-month moves (±%), largest 12-month
  moves, and named shock windows to test — 2007–08 food-price crisis,
  2012 US drought, 2020 COVID trough, 2022 Russia–Ukraine war spike.
  A shock is a month with |log return| ≥ 2× the series' rolling
  24-month return std; report the count and the top 10 by |return|.
- **Weather / drought join (annual, 2000–2025):** per year, per
  commodity — annual mean price and YoY % change vs growing-season
  (Apr–Sep) mean temperature, growing-season precipitation total,
  and growing-season mean DSCI (Iowa + Illinois average). Pearson r
  and p-value for price change vs each driver; OLS regression of YoY
  price change on growing-season DSCI + precipitation anomaly (report
  R², coefficients, p-values — association only, never causal).
- **Forecast (time-series, per the roadmap's "time-series forecasting"
  skill):** Holt-Winters / ETS on the monthly maize series (the
  bellwether crop) for the next 12 months, with an 80% interval, plus
  a 3-origin rolling backtest vs a seasonal-naïve baseline (RMSE).
  Label it plainly as a trend extrapolation from a monthly global
  benchmark series, not a market prediction.
- **Cross-commodity:** pairwise correlations of monthly log returns
  (maize–wheat, maize–soy, wheat–soy) over the full window and the
  latest 10 years.

## 3. Definitions and rules

- **Log return:** ln(P_t / P_{t−1}) on monthly closes. All volatility,
  correlation, and shock work uses log returns, never raw % changes.
- **Growing season:** April–September inclusive, per the Day 16/17
  convention.
- **Drawdown:** from a running peak of the monthly price level to the
  subsequent trough, in %; report the worst per commodity with dates.
- **Partial year:** 2026 (Jan–Sep) is excluded from annual means and
  from the weather/drought join; it is shown in the monthly series
  and labelled partial everywhere.
- **Units:** USD per metric ton throughout. A bu/acre-style conversion
  is NOT applicable to prices; do not invent one. (For context only:
  1 metric ton of maize ≈ 39.37 bushels.)
- **No synthetic price data.** If FRED is unreachable, the build stops
  and reports the blocker — the committed raw CSVs are the cache, and
  an offline run replays them. Synthetic prices would defeat the
  purpose of a price analyzer.

## 4. Verification log (this pass only)

| Check | Result |
|---|---|
| FRED PMAIZMTUSDM fredgraph.csv | HTTP 200, 2026-11-25 — 1992-01 → 2026-09, 12,463 B |
| FRED PWHEAMTUSDM fredgraph.csv | HTTP 200, 2026-11-25 — 1992-01 → 2026-09, 12,522 B |
| FRED PSOYBUSDM fredgraph.csv | HTTP 200, 2026-11-25 — 1992-01 → 2026-09, 12,121 B |
| FRED PCORNUSDM | HTTP 404 — wrong ID, discarded |
| USDA Quick Stats API | HTTP 401 without key (Day 16) — no key available, not used |
| Open-Meteo weather | Reused from Day 16 (HTTP 200, 2026-11-23) — not re-searched |
| USDM state DSCI | Reused from Day 17 (HTTP 200, 2026-11-24) — not re-searched |
| Plotly county GeoJSON | Reused from Day 17 (HTTP 200, 2026-11-24) — not re-downloaded |

## 5. Handoff to planner

- **Next role's first step:** read this brief + the roadmap entry, then
  write `plan.md` with the exact file tree, the 4 chart definitions,
  and the §8 success checklist. The plan decides: (a) whether the GIS
  chart is a county map from Day 17's `county_year.csv` or a state
  choropleth of 2012 DSCI; (b) the forecast method (Holt-Winters vs
  ETS) for the maize 12-month outlook; (c) the exact shock windows
  to annotate on the price chart.
- **Known gaps:** latest price month is 2026-09 (IMF lag); prices are
  global benchmarks, not USDA farm-gate; weather/drought joins are
  annual (2000–2025) and Corn Belt only (IA + IL average), not
  national.
