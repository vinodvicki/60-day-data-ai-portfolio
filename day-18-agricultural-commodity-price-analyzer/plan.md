# Day 18 — Agricultural Commodity Price Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-25) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Study commodity price seasonality,
variability, and past shocks to support planning decisions. GitHub
deliverable: Commodity price tracking dashboard."
**Core skills:** Regression, weather joins, time-series forecasting, GIS.
**Suggested data:** USDA Quick Stats; NOAA weather; US Drought Monitor.

| Item | Value |
|---|---|
| Fetch date | 2026-11-25 |
| Price source | FRED fredgraph.csv, no key — IMF Primary Commodity Prices via FRED: PMAIZMTUSDM (maize), PWHEAMTUSDM (wheat), PSOYBUSDM (soybeans), USD/metric ton, monthly, 1992-01 → 2026-09 (verified HTTP 200, 2026-11-25) |
| Weather source | Open-Meteo ERA5 archive, Iowa + Illinois centroids — copied from Day 16's committed raw JSONs (verified 2026-11-23) |
| Drought source | US Drought Monitor REST API, state DSCI Iowa + Illinois — copied from Day 17's committed raw CSVs (verified 2026-11-24) |
| County map source | Day 17's committed `county_year.csv` (county × year growing-season D2+ share) — copied into this day's `data/raw/`; GeoJSON fetched at chart time (verified 2026-11-24) |
| Commodities / geography | Maize, wheat, soybeans; global benchmark prices joined to Iowa + Illinois (Corn Belt) weather/drought at the annual level |
| Window | Monthly prices 1992-01 → 2026-09 (417 months/commodity; 2026 partial Jan–Sep); annual join 2000–2025 (26 years) |
| Deliverable | Commodity price tracking dashboard (README + `outputs/insights_summary.md` + Streamlit dashboard + 4 charts + notebook) |
| Scope | Price seasonality, variability, past shocks, weather/drought join, 12-month maize forecast, county drought map for the worst shock year. No USDA farm-gate prices (no key — brief §1d). No price prediction beyond the labelled Holt-Winters extrapolation. |

## 1. Problem statement + audience

**Problem.** A grower, buyer or planner deciding when to sell, store or buy
grain needs to know three things: when prices usually rise and fall within
the year, how violently they can move, and what past shocks looked like.
This project answers all three from one open series — 34 years of monthly
IMF benchmark prices for maize, wheat and soybeans via FRED — then joins
the annual price moves to Corn Belt growing-season weather and drought, so
the 2012 drought spike and the 2022 war spike can be read against the
conditions that produced them.

**Four hard limits, stated up front and labelled on every surface (README,
notebook, insights, dashboard, charts):**

1. **Global benchmark prices, not USDA farm-gate prices.** USDA Quick
   Stats needs an API key (HTTP 401 without one, brief §1d) and no key
   is available to this run, so the prices are IMF global benchmarks
   via FRED. They move with the same shocks as US farm prices but are
   not state-level and are not farm-gate — say so wherever the series
   are described.
2. **Latest price month is 2026-09.** The IMF source lags ~2 months.
   2026 is a partial year (Jan–Sep) and is excluded from annual means
   and from the weather/drought join; it is shown in the monthly series
   and labelled partial everywhere.
3. **Weather/drought join is annual, 2-state, 26 years.** The drivers
   are Iowa + Illinois growing-season means — a proxy for the Corn Belt
   crop, not a national weather average. Correlations on 26 annual
   points carry wide uncertainty; report p-values, never causal claims.
4. **The forecast is a trend extrapolation, not a market prediction.**
   Holt-Winters on a monthly global benchmark series, 12 months ahead,
   with an 80% interval and a backtest against seasonal naïve. Label it
   as such on every surface.

**Audience / decision-maker.** A farm planner or data reviewer who wants a
reproducible price analysis: the exact sources and URLs, the seasonal
pattern with numbers, the shock list with dates and sizes, the
weather/drought associations with p-values, the forecast with its
backtest error, and every published number matching the committed CSVs.

## 2. Decisions (frozen)

### 2.1 Research questions (exactly 3)

1. When within the year do maize, wheat and soybean prices typically peak
   and trough, and how large is the seasonal swing?
2. How variable are prices — worst drawdowns, largest single-month and
   12-month moves — and which named shock windows (2007–08, 2012, 2020,
   2022) show up in the data, at what size?
3. Do Corn Belt growing-season weather and drought move with annual
   price changes — and does a Holt-Winters forecast of maize beat a
   seasonal-naïve baseline on a rolling backtest?

### 2.2 Other frozen decisions

- **Units:** USD per metric ton throughout. Log returns are
  ln(P_t / P_{t−1}) on monthly prices. All volatility, correlation and
  shock work uses log returns, never raw % changes.
- **Growing season:** April–September inclusive (Day 16/17 convention).
  A USDM week belongs to the growing season if its MapDate month is
  4–9. Weather aggregates use daily values with dates in Apr–Sep.
- **Seasonality:** seasonal index per calendar month = mean price in
  that month / overall mean price (computed on the full 1992–2026
  window, all months). Peak/trough month = max/min index. Amplitude =
  max index − min index. Also report the same on the last 10 full years
  (2016–2025) as a stability check — one table, no extra charts.
- **Shock rule (frozen):** a shock month is a month with |log return|
  ≥ 2× the series' rolling 24-month return std (std computed on the
  trailing 24 months, min 24 observations). Report the count per
  commodity and the top 10 months by |log return| across all three.
  Named windows to annotate on chart 01: 2007-01 → 2008-06 (food-price
  crisis), 2012-06 → 2012-12 (US drought), 2020-02 → 2020-05 (COVID
  trough), 2022-02 → 2022-06 (Russia–Ukraine war spike).
- **Drawdown:** from a running peak of the monthly price level to the
  subsequent trough, in %; report the worst per commodity with peak
  and trough dates. 12-month rolling volatility = std of monthly log
  returns over the trailing 12 months, annualised × sqrt(12).
- **Weather/drought join (annual, 2000–2025, 26 rows):** per year —
  annual mean price and YoY % change per commodity; growing-season
  mean temperature (°C), growing-season precipitation total (mm) and
  anomaly vs the 2000–2025 mean, growing-season mean DSCI (IA+IL
  average). Pearson r + two-sided p-value (scipy) for YoY price change
  vs each driver, per commodity (9 correlations, reported in one
  table). OLS regression (sklearn) of maize YoY price change on
  growing-season DSCI + precipitation anomaly: report R², both
  coefficients with units, both p-values. Association only, never causal.
- **Forecast (frozen):** Holt-Winters (statsmodels
  `ExponentialSmoothing`, additive trend + additive seasonality,
  seasonal_periods=12) on the monthly maize series. Backtest: 3 origins
  (fit through 2023-09, 2024-09, 2025-09; forecast the next 12 months
  each) vs a seasonal-naïve baseline (same month last year); report
  mean RMSE for both. Then refit on the full series and forecast
  2026-10 → 2027-09 with an 80% interval = forecast ± 1.2816 ×
  backtest residual std. Labelled "statistical extrapolation, not a
  market prediction" on every surface.
- **Cross-commodity:** pairwise Pearson correlations of monthly log
  returns (maize–wheat, maize–soy, wheat–soy) over the full window and
  over the latest 10 years (2016-10 → 2026-09).
- **GIS chart (frozen — decision (a) from the brief):** chart 04 is a
  county choropleth of the 2012 growing-season mean % area in D2+
  (severe+ drought) for all 201 Iowa + Illinois counties, drawn from
  Day 17's committed `county_year.csv` (copied into this day's
  `data/raw/`) and the plotly county GeoJSON polygons with matplotlib.
  2012 is the worst drought year (Day 17) and the drought shock window
  in the price series — the map shows where that shock hit hardest.
  Fallback if the GeoJSON fetch fails: a labelled top-15 county bar
  chart (same data, same ranking).
- **Charts:** exactly 4, matplotlib, to scale and legible (§7). No
  plotly, no geopandas, no kaleido (Day 16/17 note).
- **Dependencies:** reuse the Day 17 verified pins + statsmodels
  0.15.0 (verified in Day 11's venv): pandas 3.1.1, numpy 2.5.4,
  matplotlib 3.11.2, streamlit 1.66.1, requests 2.34.2, pytest 9.2.0,
  jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1, scipy 1.18.1,
  statsmodels 0.15.0. No new dependency without a plan change.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Prices (live, 3 HTTP calls total):**
  - GET `https://fred.stlouisfed.org/graph/fredgraph.csv?id=PMAIZMTUSDM`
    → `data/raw/fred_maize.csv` (~12.5 KB). Columns
    `observation_date,PMAIZMTUSDM`.
  - GET `https://fred.stlouisfed.org/graph/fredgraph.csv?id=PWHEAMTUSDM`
    → `data/raw/fred_wheat.csv` (~12.5 KB).
  - GET `https://fred.stlouisfed.org/graph/fredgraph.csv?id=PSOYBUSDM`
    → `data/raw/fred_soybeans.csv` (~12.1 KB).
  - Expect 417 rows each (1992-01 → 2026-09). One retry after 10 s on
    a 5xx, then stop and fall back to the committed cache. No key.
  - **Do NOT fetch `PCORNUSDM`** — HTTP 404, wrong ID (brief §1a).
- **Weather (copy, not a fetch):** copy Day 16's
  `weather_iowa.json` and `weather_illinois.json` to `data/raw/`.
  Record `copied_from: day-16`, `fetch_date: 2026-11-23` in
  `data_source.json`. If missing, the pipeline may GET the Open-Meteo
  archive URL as a fallback (brief §1b).
- **Drought (copy, not a fetch):** copy Day 17's `dsci_iowa.csv` and
  `dsci_illinois.csv` to `data/raw/`. Record `copied_from: day-17`,
  `fetch_date: 2026-11-24`. If missing, the pipeline may GET the USDM
  GetDSCI URLs as a fallback (brief §1c).
- **County D2+ (copy, not a fetch):** copy Day 17's processed
  `county_year.csv` to `data/raw/county_d2plus_day17.csv`. Record
  `copied_from: day-17 processed county_year.csv`, `fetch_date:
  2026-11-24` (the underlying USDM fetch date). The pipeline reads
  only the 2012 rows from it for chart 04 and the county ranking.
- **County GeoJSON (fetch at chart time, not committed):** GET
  `https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json`
  (3,216,816 B, 3,221 features, verified 2026-11-24). Cache to
  `data/raw/counties_geo.json` locally (git-ignored). If the download
  fails, chart 04 falls back to a horizontal bar chart of the top 15
  counties by 2012 D2+ % — and the fallback is labelled on the chart.
- **Pipeline modes:** `--live` (default: fetch, then build),
  `--offline` (replay from committed raw files, no network),
  `--use-cache` (use raw files if present, else fetch). The offline run
  must reproduce the processed files byte-for-byte except
  `data_source.json` timestamps (tester checks this). In `--offline`
  mode the GeoJSON is not fetched (chart 04 uses the cached file if
  present, else the labelled bar fallback — and the chart code must
  not fail the build when the GeoJSON is absent).

### 3.2 Cleaning rules (frozen — the tester tests these)

1. Prices: parse `observation_date` as YYYY-MM-DD (first of month);
   assert price > 0, no NaN, no missing months in 1992-01 → 2026-09
   (417 rows per commodity after the fetch; a missing month stops the
   pipeline with a clear message — never silently forward-filled).
   Rename the value column to `price_usd_per_t` and add a `commodity`
   column (`maize` / `wheat` / `soybeans`).
2. Log returns: `log_return = ln(P_t / P_{t−1})`; first month per
   commodity is NaN and is dropped from return-based tables only
   (never from the price-level table).
3. Weather: same as Day 16 §3.2 rules 2–3 (daily → growing-season
   totals/means per state, then the two-state mean). Precipitation < 0
   → error, never silently clipped. Growing-season months Apr–Sep.
4. Drought: parse `MapDate` as YYYYMMDD; assert DSCI integer 0–500,
   no NaN; growing-season weeks are MapDate month 4–9; annual
   `gs_dsci_mean` per state, then the two-state mean.
5. Join: inner join on `year` for 2000–2025 (26 rows expected). 2026
   is excluded from the join (partial year). Add `yoy_pct_change` per
   commodity = annual-mean price change vs the previous year, in %.
6. No imputation anywhere. A failed assertion stops the pipeline with
   a clear message — it never writes partial processed files.

### 3.3 Cross-checks (frozen — run before the tester starts)

- Row counts: 417 price rows/commodity; 26 rows in the annual join
  table; 201 counties in the 2012 county table.
- 2012 is the worst drought year by gs DSCI mean (Day 17 verified:
  gs DSCI mean 200.4) — the tester verifies the direction, not a
  number from memory.
- The 2022 maize price level is above the 2021 level (war-spike
  direction check); the 2020 annual mean is below 2019 (COVID-trough
  direction check). Direction only — exact values come from the data.
- Hand-validation metric (§4.4): maize price for 2012-09 (the drought
  peak month), computed independently from `data/raw/fred_maize.csv`
  and compared to `monthly_prices.csv` — exact match required.

### 3.4 Data-size and commit rule (READ CAREFULLY)

Small raw data IS committed: raw files under 1 MB each, under 5 MB per
day. Committed raw: `fred_maize.csv` (~12.5 KB), `fred_wheat.csv`
(~12.5 KB), `fred_soybeans.csv` (~12.1 KB), `weather_iowa.json`
(~292 KB), `weather_illinois.json` (~291 KB), `dsci_iowa.csv`
(~24 KB), `dsci_illinois.csv` (~30 KB), `county_d2plus_day17.csv`
(~365 KB) — total raw ~1.0 MB. **NOT committed** (git-ignored,
documented in `data/README.md`): `data/raw/counties_geo.json`
(3.2 MB). `.gitignore` must NOT exclude `data/` as a whole — only the
named large-file pattern. Processed files are all < 1 MB.
`data_source.json` records source URLs, fetch date, row counts,
`synthetic: false`, the Day 16/17 copy provenance, and the
manual-validation section (added by the tester, §4.4 — a `--live`
re-run drops it; do NOT re-run `--live` after the tester fills it).

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

- `data/processed/monthly_prices.csv` — 1,251 rows (417 × 3): date,
  commodity, price_usd_per_t, log_return.
- `data/processed/annual_summary.csv` — 34 rows (1992–2025 full years):
  year, commodity, annual_mean_price, annual_max_price,
  annual_min_price, annual_volatility (std of monthly log returns),
  yoy_pct_change (NaN for 1992). 2026 excluded (partial).
- `data/processed/seasonality.csv` — 36 rows (12 months × 3
  commodities): commodity, month, month_mean_price, seasonal_index,
  n_months; plus a `window` column (`full` / `last10y`) — 72 rows
  total (both windows in one file).
- `data/processed/shocks.csv` — shock months only: date, commodity,
  price_usd_per_t, log_return, rolling_24m_std, shock_flag; plus a
  `top10` flag for the 10 largest |log return| months across all three.
- `data/processed/annual_join.csv` — 26 rows (2000–2025): year,
  annual mean price + YoY % change per commodity (6 columns),
  gs_temp_mean_c, gs_precip_total_mm, gs_precip_anomaly_mm,
  gs_precip_anomaly_pct, gs_dsci_mean, gs_dsci_mean_ia,
  gs_dsci_mean_il.
- `data/processed/correlations.csv` — 9 rows (3 commodities × 3
  drivers): commodity, driver, pearson_r, p_value, n.
- `data/processed/regression_maize.csv` — 1 row: intercept, coef_dsci,
  coef_precip_anomaly, r_squared, p_dsci, p_precip, n.
- `data/processed/forecast_maize.csv` — 12 rows (2026-10 → 2027-09):
  date, forecast, lo_80, hi_80; plus a `backtest` section recorded in
  `data_source.json` (3 origins, HW RMSE vs seasonal-naïve RMSE).
- `data/processed/county_shock_2012.csv` — 201 rows: fips, county,
  state, gs_d2plus_pct_2012, rank.
- `data/processed/cross_correlations.csv` — 6 rows (3 pairs × 2
  windows): pair, window, pearson_r, p_value, n.
- `data/processed/data_source.json` — provenance + manual validation.

### 3.6 Fallback, licence, attribution

- No synthetic price data (brief §3). If FRED is unreachable and no
  committed raw exists, the pipeline fails loudly.
- Attribution: "Prices: IMF Primary Commodity Prices via FRED
  (Federal Reserve Bank of St. Louis). Weather: Open-Meteo ERA5
  archive (CC BY 4.0). Drought: U.S. Drought Monitor (NDMC/USDA/NOAA).
  County boundaries: US Census Bureau via plotly datasets (public
  domain)." USDA Quick Stats / NOAA GHCN named in the README with the
  reason each was not used live (brief §1).

## 4. Analysis — definitions (from the brief, frozen)

### 4.1 Seasonality

- Seasonal index per commodity per calendar month = month mean / overall
  mean, full window (1992–2026) and last-10-full-years window
  (2016–2025). Peak/trough months and amplitude (max − min index) per
  commodity per window, reported in the insights and README.

### 4.2 Variability and shocks

- Max drawdown per commodity (peak date, trough date, %); annual
  volatility (std of monthly log returns within the year); 12-month
  rolling volatility series (for chart 03); shock months per the §2.2
  rule; top 10 months by |log return| across all three commodities.
  Named-window check: report the maize price change over each of the 4
  named windows in §2.2 (start-month to end-month, %).

### 4.3 Weather/drought join and regression

- Pearson r + two-sided p-value via `scipy.stats.pearsonr` for YoY
  price change vs each driver, per commodity (9 rows). OLS (sklearn
  LinearRegression) of maize YoY % change on gs DSCI + precipitation
  anomaly (mm); report R², coefficients (pp per DSCI point, pp per mm),
  p-values via scipy `stats.linregress` on each predictor separately
  for the p-values (or statsmodels OLS — coder decides, plan §11
  records the choice; the file must carry the p-values either way).
- Cross-commodity log-return correlations: Pearson r + p-value, full
  window and latest 10 years.

### 4.4 Forecast

- Holt-Winters (statsmodels `ExponentialSmoothing`, additive trend +
  additive seasonality, seasonal_periods=12) on monthly maize prices.
  Backtest: 3 origins (fit through 2023-09, 2024-09, 2025-09;
  forecast the next 12 months each), RMSE per origin and mean RMSE,
  vs seasonal naïve (same month last year) on the same 12-month
  windows. Refit on the full series; forecast 2026-10 → 2027-09.
  80% interval = forecast ± 1.2816 × backtest residual std (residuals
  = actual − forecast across the 3 backtest origins, 36 points).

### 4.5 Hand-validation (tester — record in data_source.json)

- Metric: maize price for 2012-09, read directly from
  `data/raw/fred_maize.csv` with a one-liner and compared to
  `monthly_prices.csv` — exact match required (diff 0.0).

## 5. File tree (exact)

```
day-18-agricultural-commodity-price-analyzer/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── .pre-commit-config.yaml
├── research_brief.md  plan.md
├── coder_handoff.md  test_report.md  optimizer_handoff.md  publisher_handoff.md
├── checkpoint-stage1-researcher.md  checkpoint-stage2-planner.md
├── data/
│   ├── README.md
│   ├── raw/            # fred_maize.csv, fred_wheat.csv, fred_soybeans.csv,
│   │                   # weather_iowa.json, weather_illinois.json,
│   │                   # dsci_iowa.csv, dsci_illinois.csv,
│   │                   # county_d2plus_day17.csv (committed)
│   │                   # counties_geo.json (git-ignored, chart-time fetch)
│   └── processed/      # monthly_prices.csv, annual_summary.csv,
│                       # seasonality.csv, shocks.csv, annual_join.csv,
│                       # correlations.csv, regression_maize.csv,
│                       # forecast_maize.csv, county_shock_2012.csv,
│                       # cross_correlations.csv, data_source.json
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py   # fetch (3 calls) + clean + aggregate + join; --live/--offline/--use-cache
│   ├── analysis.py        # seasonality, variability, shocks, join, regression, forecast
│   ├── make_charts.py     # 4 charts (§7); GeoJSON fetch + matplotlib choropleth
│   └── app.py             # Streamlit dashboard
├── outputs/
│   ├── insights_summary.md
│   └── charts/            # 01_price_levels.png  02_seasonality.png
│                          # 03_volatility_shocks.png  04_county_map.png
├── screenshots/dashboard.png
└── tests/
    ├── test_pipeline.py
    ├── test_analysis.py
    └── test_smoke.py
```

## 6. Per-file responsibilities

- `src/data_pipeline.py` — only file that touches the network or the raw
  files; writes all 11 processed files; CLI flags `--live/--offline/--use-cache`;
  assertions per §3.2; never writes partial outputs.
- `src/analysis.py` — pure functions over the processed CSVs
  (seasonality, drawdown, shocks, join correlations, regression,
  Holt-Winters forecast, cross-commodity correlations); no network, no
  raw reads; writes `seasonality.csv`, `shocks.csv`,
  `correlations.csv`, `regression_maize.csv`, `forecast_maize.csv`,
  `cross_correlations.csv` (the pipeline calls it, or it runs
  standalone — coder decides, plan §11 records the choice).
- `src/make_charts.py` — reads processed CSVs only (+ GeoJSON fetch for
  chart 04); writes the 4 PNGs to `outputs/charts/`; every chart has a
  title, labelled axes with units, source line, and a legible font size
  (≥ 9 pt at final size).
- `src/app.py` — Streamlit dashboard: KPI row (latest maize price,
  worst drawdown, 2026-09 maize price vs 2025 mean), price-level chart,
  seasonality chart, shocks table, forecast chart, county map
  (matplotlib figure), methods + limitations section. Must render
  without error on a fresh port.
- `notebooks/analysis.ipynb` — reproduces the monthly table, the
  seasonal indices, the top-10 shocks, the 9 correlations, the
  regression and the forecast from the processed CSVs; root resolved
  from the notebook file location (AGENTS.md lesson e); runs
  top-to-bottom with 0 error cells.
- `tests/test_pipeline.py` — cleaning/aggregation rules on small
  synthetic frames (price parsing, missing-month assertion, log
  returns, growing-season filter, DSCI aggregation, join row count).
- `tests/test_analysis.py` — seasonal index sums to ~12 per commodity
  (full window); drawdown on a known synthetic series; shock rule on a
  known series; Pearson r on a known synthetic series; forecast
  function returns 12 rows with lo ≤ forecast ≤ hi.
- `tests/test_smoke.py` — processed files exist with expected columns
  and row counts; no NaN in the annual join table; charts exist and
  are non-empty PNGs; `data_source.json` has `synthetic: false`.
- `data/README.md` — per-file provenance, the size rule, the
  git-ignored GeoJSON, and how to regenerate everything with one command.
- `README.md` — problem, audience, the 4 limits (§1), setup, how to run,
  the 3 findings + recommendation, Visuals section with the 4 chart
  images **embedded at build time** (Day 9/16 lesson), Dashboard preview
  with `screenshots/dashboard.png` embedded, limitations, attribution.
- `outputs/insights_summary.md` — 3 findings + 1 actionable
  recommendation, every number matching the committed CSVs.

## 7. Charts (exactly 4, matplotlib, to scale, legible)

1. `01_price_levels.png` — monthly price levels 1992–2026 for maize,
   wheat, soybeans on one axis (USD/t), with the 4 named shock windows
   (§2.2) shaded and labelled; y from 0.
2. `02_seasonality.png` — seasonal index by calendar month (3 lines,
   one per commodity), horizontal line at 1.0, peak/trough months
   annotated per commodity.
3. `03_volatility_shocks.png` — two panels: (a) 12-month rolling
   volatility (annualised, %) for the 3 commodities; (b) bars of the
   top 10 shock months by |log return| (commodity-labelled). Both
   panels share the message that volatility clusters around shocks.
4. `04_county_map.png` — choropleth of 2012 growing-season mean % area
   in D2+ (severe+ drought) per county (IA + IL, 201 counties),
   matplotlib polygons from the county GeoJSON, colourbar "% of county
   area in severe+ drought, growing season 2012"; top-3 counties
   labelled. Fallback (§3.1): top-15 county bar chart, labelled as the
   fallback.

## 8. Success criteria checklist (§8 — all must pass)

- [ ] Problem statement + audience written (README)
- [ ] Data provenance documented (data/README.md)
- [ ] 2+ labelled charts produced (4 produced, §7)
- [ ] 3 findings + 1 actionable recommendation (outputs/insights_summary.md)
- [ ] README with setup instructions, sample outputs, limitations
- [ ] No credentials in the repo; no huge files committed
- [ ] One metric manually validated and recorded (§4.5)
- [ ] Pipeline runs end-to-end from a clean checkout
- [ ] Notebook runs top-to-bottom without errors
- [ ] County map renders (chart 04) with all 201 counties joined by FIPS
- [ ] Seasonality indices, shock list, and forecast backtest all reported with numbers
- [ ] Holt-Winters 12-month forecast labelled as a statistical extrapolation
- [ ] 4 chart images embedded in the day README Visuals section at build time

## 9. Risks & mitigations

- **FRED fredgraph.csv changes or blocks the request** — mitigated by
  the committed raw CSVs (the offline replay needs no network) and by
  the one-retry-then-stop rule; a failed live fetch with a committed
  cache present is a warning, not a build failure.
- **GeoJSON fetch fails at chart time** — mitigated by the labelled
  top-15 bar fallback (§3.1, §7).
- **Weak annual correlations (n = 26)** — report them honestly with
  p-values; a null result is a finding, not a failure. Do not add
  variables to chase significance.
- **Holt-Winters fails to converge on a trending series** — fall back
  to damped-trend Holt-Winters (`damped_trend=True`) and record the
  choice in §11; if that also fails, the forecast step reports the
  failure and the dashboard shows the backtest only.
- **2026 partial year contaminating annual stats** — mitigated by the
  §3.2 rule 5 exclusion (2026 out of `annual_summary.csv` and the
  join); the tester asserts 2026 is absent from both files.

## 10. Build order

1. Coder: venv + pinned deps → `data_pipeline.py` (fetch + aggregate)
   → run `--live`, verify §3.3 cross-checks → `analysis.py` →
   `make_charts.py` → `app.py` → notebook → README/data README/insights
   → black/ruff/mypy/pytest → handoff.
2. Tester: re-run pytest + coverage, smoke test on a fresh port with a
   real screenshot, hand-validate §4.5, chart legibility check.
3. Optimizer: fix gaps only, re-run gates, update root README/docs.
4. Publisher: frozen-tree check (incl. `data/raw/`), stage manifests
   for the push (PNGs first via browser, then text batches), verify
   live page renders, hand the staged list to the parent.

## 11. Plan-vs-brief differences

- None on sources or metrics. The brief's forecast method choice
  ("Holt-Winters / ETS") is frozen here as Holt-Winters with additive
  trend + additive seasonality, seasonal_periods=12 (§2.2).
- The brief's GIS option (a) is decided: chart 04 is a county
  choropleth of 2012 D2+ share from Day 17's committed
  `county_year.csv`, copied into this day's `data/raw/` as
  `county_d2plus_day17.csv` (§3.1) — no new county aggregation work.
- The brief said "the 4 named shock windows to test"; the plan freezes
  their exact date ranges in §2.2.
- The annual join table gains `gs_dsci_mean_ia` / `gs_dsci_mean_il`
  columns so the hand-validation path and per-state values are
  checkable from a committed file (same pattern as Day 17 §11).
