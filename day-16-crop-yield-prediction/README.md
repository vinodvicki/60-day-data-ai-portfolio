# Day 16 — Crop Yield Prediction

> **60-Day Data Analytics + AI Portfolio, Day 16.**
> Estimating USA maize yield from historical harvest, temperature and
> rainfall — and scoring the models on six held-out years they never saw.

## Problem

Can US corn yield be estimated from growing-season weather? This project
joins 26 years of national maize yield (2000–2025) with Corn Belt
temperature and rainfall, fits three regression models on 2000–2019, and
evaluates them on the held-out years 2020–2025 — with the drivers shown
alongside the errors, so the reader can judge whether the model earns trust.

## Dataset

| Source | What | Window | Rows | Access |
|---|---|---|---|---|
| FAO via Our World in Data — `ourworldindata.org/grapher/maize-yields.csv?country=USA` | USA maize yield, t/ha | 2000–2025 | 26, 0 missing | Keyless, fetched 2026-11-23 |
| Open-Meteo ERA5 archive — `archive-api.open-meteo.com/v1/archive` | Daily mean/max temperature + precipitation, Iowa (41.8780, −93.0977) + Illinois (40.6331, −89.3985) centroids | 2000–2025 | 9,497 days per state, 0 missing | Keyless, fetched 2026-11-23 |

Licence: both CC BY 4.0. Attribution: "Yield: FAO via Our World in Data.
Weather: Open-Meteo (ERA5)". Raw files are committed under `data/raw/`
(952 KB total). The roadmap's suggested USDA Quick Stats API needs an API
key (HTTP 401 without one), so FAO/OWID national yields are used instead;
NOAA GHCN-daily was verified as a cross-check only, and the US Drought
Monitor download needs an interactive form (drought is Day 17's subject).
See `research_brief.md` for the full verification record.

## Tools

Python 3.12.3, pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
streamlit 1.66.1, requests 2.34.2, scikit-learn 1.9.1, scipy 1.18.1
(pinned in `requirements.txt`).

## Method

1. **Fetch + clean** (`src/data_pipeline.py`): filter OWID to USA 2000–2025;
   aggregate daily weather per state into growing-season features
   (April–September), then average Iowa + Illinois.
2. **Features (7):** `year` (technology trend), `gs_temp_mean`,
   `gs_precip_total`, `jul_temp_mean`, `jul_precip_total`,
   `jun_precip_total`, `heat_days_gs` (Apr–Sep days with max > 30 °C).
3. **Models** (`src/model.py`): OLS, Ridge (α = 1.0), RandomForest
   (300 trees, seed 42) — all fit on train years only; standardisation fit
   on train only. Baselines: `naive_last` (this year's yield = last year's
   actual yield) and `naive_mean` (train-period mean).
4. **Evaluation:** RMSE / MAE / R² / bias on the 6 held-out years
   (2020–2025). Winner = lowest held-out RMSE; ties within 0.01 t/ha go to
   the simpler model. Driver analysis: Pearson r, standardised OLS
   coefficients, Random Forest permutation importance (30 repeats, seed 42).

## Key insights

- **Best model: Ridge — held-out RMSE 0.540 t/ha (8.61 bu/acre), MAE 0.441,
  bias +0.441.** OLS scores 0.785 and Random Forest 0.592 t/ha.
- **But the honest headline is that no model beats the naive baseline:**
  predicting "last year's yield" scores RMSE 0.287 t/ha (4.57 bu/acre) on
  the same six years — yields rose smoothly through 2020–2025, so
  persistence is hard to beat. All models beat the train-mean baseline
  (RMSE 1.479 t/ha). Held-out R² is negative for every model because the
  six held-out yields sit in a narrow band (10.76–11.71 t/ha) while errors
  are ~0.5 t/ha — R² on 6 points is a secondary metric here.
- **Heat is the clearest weather driver:** more days above 30 °C
  (standardised OLS coefficient −0.49) and hotter Julys (−0.37, r = −0.39)
  move with lower yields; July and June rainfall are mildly positive
  (r ≈ +0.23). The `year` trend dominates (r = +0.83). Drivers are
  associations, not causation.
- **2012 is the story in one year:** the drought year had the lowest yield
  in the series (7.73 t/ha) with Iowa growing-season rain of 423.6 mm
  (vs 1041.9 mm in 2010) and 51 heat days.
- **2024 yield hand-validated: 11.253324 t/ha = 179.28 bu/acre** (recomputed
  from the raw CSV by hand; diff 0.0). 2025 yield: 11.71 t/ha (186.48 bu/acre).

## Visuals

- `outputs/charts/01_yield_history.png` — yield 2000–2025, train/held-out
  shading, train trend, 2012 dip annotated.
- `outputs/charts/02_actual_vs_predicted.png` — held-out actual vs winner
  prediction vs naive-last.
- `outputs/charts/03_feature_drivers.png` — standardised OLS coefficients
  with Pearson r (association, not causation).
- `outputs/charts/04_weather_stations_map.png` — the two Corn Belt weather
  stations (schematic lon/lat map; the plotly/kaleido route failed in this
  environment, so the plan's matplotlib fallback was used).
- `screenshots/dashboard.png` — real capture of the running Streamlit app.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/data_pipeline.py --live        # fetch + build (or --offline to replay)
python src/model.py                        # train + score
python src/make_charts.py                  # 4 charts
pytest tests/ -q --cov=src --cov-fail-under=30
streamlit run src/app.py                   # dashboard on http://localhost:8501
```

## Limitations

- **National yield, 2-state weather proxy.** Weather is the Iowa + Illinois
  average, not a national average — reasonable (the two states are ~35% of
  US corn output) but a proxy, stated everywhere the features appear.
- **Small sample.** 26 annual rows, 20 for training. Held-out RMSE/MAE are
  the honest measures; R² on 6 points is noisy.
- **Association, not causation.** Drivers describe co-movement only.
- **No USDA state data.** The Quick Stats API needs a key; with one,
  state-level NASS yields could replace the national series without
  changing the pipeline shape.
- **No 2026 forecast.** The latest actual is the 2025 harvest (11.71 t/ha).

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Victor.
