# Day 16 — Crop Yield Prediction: Insights

**Headline finding:** Ridge regression is the best of the three models on
the six held-out years (2020–2025) at RMSE **0.540 t/ha (8.61 bu/acre)** —
but **no model beats the naive "last year's yield" baseline (RMSE 0.287
t/ha)**. The weather + trend models are useful for driver analysis, not yet
for forecasting.

## Q1 — How accurately can 2020–2025 yields be estimated, and which model wins?

- **Ridge wins** among the models: held-out RMSE 0.540 t/ha, MAE 0.441,
  bias +0.441 (it over-predicts). OLS: RMSE 0.785, MAE 0.694, bias +0.694.
  Random Forest: RMSE 0.592, MAE 0.492, bias −0.492 (it under-predicts —
  trees cannot extrapolate the rising trend, so its predictions sit flat
  near 10.6 t/ha while actuals run 10.76–11.71).
- In-sample the picture flips: Random Forest looks best on train
  (RMSE 0.214, R² 0.950) and Ridge worst (0.350) — a textbook warning that
  train fit says nothing about held-out performance on 20 rows.
- Held-out R² is negative for every model (Ridge −2.20). That is not a bug:
  the six held-out yields sit in a narrow band (10.76–11.71 t/ha) while the
  errors are ~0.5 t/ha, so the models explain less of that small variance
  than the held-out mean does. RMSE/MAE are the primary metrics; R² on 6
  points is secondary and labelled as such.

## Q2 — Which weather drivers matter, and in which direction?

- The `year` trend dominates (Pearson r = +0.83 with yield;
  standardised OLS coefficient +0.87) — technology and practice lift yields
  about +0.13 t/ha per year on the train trend.
- **Heat hurts.** `heat_days_gs` (Apr–Sep days above 30 °C) has the
  strongest weather coefficient (−0.49 standardised) and July mean
  temperature is next (−0.37, r = −0.39). Growing-season rainfall overall is
  near-neutral (r = +0.03) once the trend is accounted for, but July
  rainfall (r = +0.23) and June rainfall (r = +0.23) are mildly positive.
- Random Forest permutation importance agrees that no single weather feature
  dominates once the trend is in the model (all weather importances below
  0.01 RMSE units on the held-out set) — the forest leans on the trend it
  cannot extrapolate, which is why it under-predicts.
- Language guardrail: these are **associations, not causation**. A feature
  that moves with yield is not proof of causation.

## Q3 — Does any model beat the naive baselines?

- **No.** `naive_last` (this year's yield = last year's actual yield)
  scores RMSE 0.287 t/ha and MAE 0.268 — better than Ridge (0.540), Random
  Forest (0.592) and OLS (0.785). Yields rose smoothly through 2020–2025,
  so persistence is a hard baseline to beat with 20 training years.
- **Yes, against the weaker baseline:** every model beats `naive_mean`
  (train-period mean yield, RMSE 1.479 t/ha) by a wide margin.

## The 2012 story in one year

2012 had the lowest yield in the series (**7.73 t/ha**) with Iowa
growing-season rain of **423.6 mm** (vs 1041.9 mm in 2010) and **51 heat
days** (Illinois: 402.4 mm, 59 heat days). It is the single year where the
weather signal is unmistakable — and the reason drought severity belongs in
the next iteration (Day 17).

## Recommendation (analytical next step)

Do not use this model to forecast next year's yield — use it to watch heat.
The next iteration should (a) get a USDA Quick Stats key and rebuild on
state-level NASS yields matched to the same states' weather, which removes
the national-vs-2-state proxy mismatch, and (b) add drought severity as a
feature, since 2012 shows the signal the current seven features miss.

## Limitations

- **National yield, 2-state weather proxy:** Iowa + Illinois average, not a
  national average (~35% of US corn output — reasonable, but a proxy).
- **Small sample:** 26 annual rows, 20 for training; no hyperparameter
  tuning was done (tuning on 6 held-out years would leak the test set).
- **Association, not causation** for all driver statements.
- **No USDA state data** (API key required, HTTP 401 without one).
- **No 2026 forecast:** the latest actual is the 2025 harvest, 11.71 t/ha
  (186.48 bu/acre). 2024 yield hand-validated: 11.253324 t/ha = 179.28
  bu/acre, diff 0.0.
