# Data provenance — Day 18 Agricultural Commodity Price Analyzer

**Status:** LIVE — fetched 2026-11-25.

## Sources

| File | Source | Endpoint / origin | Window | Rows | Size |
|---|---|---|---|---|---|
| `fred_maize.csv` | IMF Primary Commodity Prices via FRED | `fredgraph.csv?id=PMAIZMTUSDM` | 1992-01 → 2026-09 | 417 | 12,463 B |
| `fred_wheat.csv` | IMF Primary Commodity Prices via FRED | `fredgraph.csv?id=PWHEAMTUSDM` | 1992-01 → 2026-09 | 417 | 12,522 B |
| `fred_soybeans.csv` | IMF Primary Commodity Prices via FRED | `fredgraph.csv?id=PSOYBUSDM` | 1992-01 → 2026-09 | 417 | 12,121 B |
| `weather_iowa.json` | Open-Meteo ERA5 archive (CC BY 4.0) | copied from Day 16 (fetch 2026-11-23) | daily 2000–2025 | 9,496 days | 292,112 B |
| `weather_illinois.json` | Open-Meteo ERA5 archive (CC BY 4.0) | copied from Day 16 (fetch 2026-11-23) | daily 2000–2025 | 9,496 days | 291,473 B |
| `dsci_iowa.csv` | U.S. Drought Monitor REST API | copied from Day 17 (fetch 2026-11-24) | weekly 2000–2025 | 1,357 | 24,390 B |
| `dsci_illinois.csv` | U.S. Drought Monitor REST API | copied from Day 17 (fetch 2026-11-24) | weekly 2000–2025 | 1,357 | 29,504 B |
| `county_d2plus_day17.csv` | U.S. Drought Monitor county % area, via Day 17 | copied from Day 17 `data/processed/county_year.csv` (fetch 2026-11-24) | county × year 2000–2025 | 5,226 | 365,052 B |

Total committed raw: ~1.0 MB (under the 5 MB/day rule; every file under
1 MB). No key, no account, no credential anywhere. **USDA Quick Stats
was not used**: its API returns HTTP 401 without a key and no key was
available to this run. `PCORNUSDM` is not a valid FRED series (HTTP 404);
maize is `PMAIZMTUSDM`.

## Fetch outcome

- FRED: 3/3 calls HTTP 200 on 2026-11-25. Latest observation 2026-09-01
  for all three series (IMF source lags ~2 months). 2026 is a partial
  year (Jan–Sep) and is excluded from `annual_summary.csv` and from the
  weather/drought join.
- Weather and drought files were copied from Days 16/17, not re-fetched
  (their endpoints were verified in those builds). The pipeline falls
  back to a live fetch if a copy is missing.
- The county GeoJSON (`counties_geo.json`, 3,216,816 B) is fetched at
  chart time by `make_charts.py` and cached locally — it is
  **git-ignored, not committed**. The local cache is deleted after the
  chart build (it is re-fetched whenever the chart is rebuilt). If the
  download fails, chart 04 falls back to a labelled top-15 county bar
  chart.

## Processed files

| File | Rows | Contents |
|---|---|---|
| `monthly_prices.csv` | 1,251 | date, commodity, price_usd_per_t, log_return (417 months × 3) |
| `annual_summary.csv` | 102 | year, commodity, annual mean/max/min price, annual volatility, YoY % change (full years 1992–2025) |
| `seasonality.csv` | 72 | commodity, month, window (full / last10y), month mean price, seasonal index, n_months |
| `shocks.csv` | 76 | shock months: date, commodity, price, log return, rolling 24m std, top10 flag |
| `annual_join.csv` | 26 | year, annual mean price + YoY % per commodity, GS temp mean, GS precip total/anomaly, GS DSCI mean (+ per-state) |
| `correlations.csv` | 9 | commodity × driver Pearson r + p-value |
| `regression_maize.csv` | 1 | OLS of maize YoY % on GS DSCI + precip anomaly (R², coefficients, p-values) |
| `forecast_maize.csv` | 12 | Holt-Winters maize forecast 2026-10 → 2027-09 with 80% interval |
| `county_shock_2012.csv` | 201 | fips, county, state, 2012 GS D2+ %, rank |
| `cross_correlations.csv` | 6 | pair × window Pearson r of monthly log returns |
| `data_source.json` | — | provenance + backtest summary (+ manual_validation, added by the tester) |

## Regeneration

```bash
.venv/bin/python -m src.data_pipeline --live     # fetch + build
.venv/bin/python -m src.data_pipeline --offline  # replay from raw files
.venv/bin/python -m src.make_charts              # rebuild the 4 charts
```

The offline run reproduces the processed files byte-for-byte except
`data_source.json` timestamps — and it does not clobber the live
provenance record (a live run preserves an existing
`manual_validation` section). Do not re-run `--live` after the tester
fills in `manual_validation` without re-adding it.

## Cleaning rules (plan §3.2)

1. Prices: 417 months per commodity, no missing months, prices > 0,
   no NaN — a gap stops the pipeline, never silently forward-filled.
2. Log returns are ln(P_t / P_{t-1}); the first month per commodity is
   NaN and is dropped from return-based tables only.
3. Growing season is April–September. Weather: daily → GS totals/means
   per state, then the two-state mean. Precipitation < 0 is an error.
4. Drought: weekly DSCI → GS mean per state, then the two-state mean;
   DSCI asserted 0–500.
5. Join is an inner join on year for 2000–2025 (26 rows). 2026 is
   excluded (partial year). No imputation anywhere.
