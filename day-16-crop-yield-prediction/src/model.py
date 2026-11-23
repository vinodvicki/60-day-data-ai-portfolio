"""Day 16 Crop Yield Prediction: models + driver analysis.

Trains OLS, Ridge and a Random Forest on 2000–2019 and scores them on the
held-out years 2020–2025, alongside two naive baselines. All
standardisation is fit on train years only (no leakage). Deterministic:
seed 42 everywhere. Reads ``data/processed/yield_weather.csv`` and writes
``model_results.csv``, ``heldout_predictions.csv`` and
``driver_importance.csv``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"

FEATURES = [
    "year",
    "gs_temp_mean",
    "gs_precip_total",
    "jul_temp_mean",
    "jul_precip_total",
    "jun_precip_total",
    "heat_days_gs",
]
TARGET = "yield_t_per_ha"
BU_PER_ACRE = 39.368 / 2.47105  # 15.932... (see data_pipeline.py)

MODEL_ORDER = ["OLS", "Ridge", "RandomForest"]
BASELINES = ["naive_last", "naive_mean"]


def compute_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    """RMSE / MAE / R² / bias for one set of predictions."""
    actual_arr = np.asarray(actual, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(actual_arr, pred)))
    return {
        "rmse": rmse,
        "mae": float(mean_absolute_error(actual_arr, pred)),
        "r2": float(r2_score(actual_arr, pred)),
        "bias": float(np.mean(pred - actual_arr)),
    }


def train_models(
    train: pd.DataFrame,
) -> dict[str, object]:
    """Fit the three models on train years only; return fitted artefacts."""
    x_train = train[FEATURES].to_numpy(dtype=float)
    y_train = train[TARGET].to_numpy(dtype=float)

    scaler = StandardScaler().fit(x_train)
    x_train_scaled = scaler.transform(x_train)

    ols = LinearRegression().fit(x_train, y_train)
    ols_std = LinearRegression().fit(x_train_scaled, y_train)
    ridge = Ridge(alpha=1.0).fit(x_train_scaled, y_train)
    forest = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=1)
    forest.fit(x_train, y_train)
    return {
        "OLS": ols,
        "OLS_standardised": ols_std,
        "Ridge": ridge,
        "RandomForest": forest,
        "scaler": scaler,
    }


def predict_all(models: dict[str, object], frame: pd.DataFrame) -> pd.DataFrame:
    """Predictions for every model on the given frame (train or held-out)."""
    x = frame[FEATURES].to_numpy(dtype=float)
    scaler = models["scaler"]
    assert isinstance(scaler, StandardScaler)
    x_scaled = scaler.transform(x)
    ols = models["OLS"]
    ridge = models["Ridge"]
    forest = models["RandomForest"]
    assert isinstance(ols, LinearRegression)
    assert isinstance(ridge, Ridge)
    assert isinstance(forest, RandomForestRegressor)
    return pd.DataFrame(
        {
            "OLS": ols.predict(x),
            "Ridge": ridge.predict(x_scaled),
            "RandomForest": forest.predict(x),
        },
        index=frame.index,
    )


def baseline_predictions(train: pd.DataFrame, heldout: pd.DataFrame) -> pd.DataFrame:
    """Naive baselines for the held-out years.

    ``naive_last`` predicts this year's yield = last year's ACTUAL yield
    (one-step persistence; the previous year's harvest is observed data,
    so this uses no future information). ``naive_mean`` predicts the
    train-period mean yield every year.
    """
    full = pd.concat([train, heldout]).sort_values("year").reset_index(drop=True)
    actual_by_year = dict(zip(full["year"], full[TARGET]))
    train_mean_yield = float(train[TARGET].mean())
    n = len(heldout)
    return pd.DataFrame(
        {
            "naive_last": [actual_by_year[int(y) - 1] for y in heldout["year"]],
            "naive_mean": np.full(n, train_mean_yield),
        },
        index=heldout.index,
    )


def pick_winner(results: pd.DataFrame) -> str:
    """Lowest held-out RMSE; within 0.01 t/ha the simpler model wins."""
    models_only = results[results["model"].isin(MODEL_ORDER)].copy()
    best_rmse = float(models_only["heldout_rmse_t_per_ha"].min())
    tied = models_only[models_only["heldout_rmse_t_per_ha"] <= best_rmse + 0.01]
    for name in MODEL_ORDER:  # OLS first = simplest wins ties
        if name in set(tied["model"]):
            return name
    raise ValueError("no winner found")


def driver_analysis(
    frame: pd.DataFrame,
    train: pd.DataFrame,
    heldout: pd.DataFrame,
    models: dict[str, object],
) -> pd.DataFrame:
    """Pearson r, standardised OLS coefficients, RF permutation importance."""
    ols_std = models["OLS_standardised"]
    forest = models["RandomForest"]
    assert isinstance(ols_std, LinearRegression)
    assert isinstance(forest, RandomForestRegressor)

    x_heldout = heldout[FEATURES].to_numpy(dtype=float)
    y_heldout = heldout[TARGET].to_numpy(dtype=float)
    perm = permutation_importance(
        forest,
        x_heldout,
        y_heldout,
        n_repeats=30,
        random_state=42,
        scoring="neg_root_mean_squared_error",
    )
    rows = []
    for i, feature in enumerate(FEATURES):
        rows.append(
            {
                "feature": feature,
                "pearson_r": float(frame[feature].corr(frame[TARGET])),
                "ols_std_coef": float(ols_std.coef_[i]),
                "rf_perm_importance": float(perm.importances_mean[i]),
            }
        )
    return pd.DataFrame(rows)


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Train, score, write the three processed outputs; return them + winner."""
    df = pd.read_csv(PROCESSED_DIR / "yield_weather.csv")
    train = df[df["split"] == "train"].reset_index(drop=True)
    heldout = df[df["split"] == "heldout"].reset_index(drop=True)
    if len(train) != 20 or len(heldout) != 6:
        raise ValueError(
            f"expected 20 train / 6 held-out rows, got {len(train)} / {len(heldout)}"
        )

    models = train_models(train)
    pred_heldout = predict_all(models, heldout)
    pred_train = predict_all(models, train)
    base_heldout = baseline_predictions(train, heldout)

    results_rows = []
    for name in MODEL_ORDER:
        held = compute_metrics(heldout[TARGET], pred_heldout[name].to_numpy())
        tr = compute_metrics(train[TARGET], pred_train[name].to_numpy())
        results_rows.append(
            {
                "model": name,
                "heldout_rmse_t_per_ha": held["rmse"],
                "heldout_rmse_bu_per_acre": held["rmse"] * BU_PER_ACRE,
                "heldout_mae_t_per_ha": held["mae"],
                "heldout_mae_bu_per_acre": held["mae"] * BU_PER_ACRE,
                "heldout_r2": held["r2"],
                "heldout_bias_t_per_ha": held["bias"],
                "train_rmse_t_per_ha": tr["rmse"],
                "train_r2": tr["r2"],
            }
        )
    for name in BASELINES:
        held = compute_metrics(heldout[TARGET], base_heldout[name].to_numpy())
        results_rows.append(
            {
                "model": name,
                "heldout_rmse_t_per_ha": held["rmse"],
                "heldout_rmse_bu_per_acre": held["rmse"] * BU_PER_ACRE,
                "heldout_mae_t_per_ha": held["mae"],
                "heldout_mae_bu_per_acre": held["mae"] * BU_PER_ACRE,
                "heldout_r2": held["r2"],
                "heldout_bias_t_per_ha": held["bias"],
                "train_rmse_t_per_ha": float("nan"),
                "train_r2": float("nan"),
            }
        )
    results = pd.DataFrame(results_rows)
    winner = pick_winner(results)
    results["is_winner"] = results["model"] == winner

    predictions = pd.DataFrame(
        {
            "year": heldout["year"],
            "actual_t_per_ha": heldout[TARGET],
            "actual_bu_per_acre": heldout["yield_bu_per_acre"],
            "OLS": pred_heldout["OLS"],
            "Ridge": pred_heldout["Ridge"],
            "RandomForest": pred_heldout["RandomForest"],
            "naive_last": base_heldout["naive_last"],
            "naive_mean": base_heldout["naive_mean"],
        }
    )
    drivers = driver_analysis(df, train, heldout, models)

    results.to_csv(PROCESSED_DIR / "model_results.csv", index=False)
    predictions.to_csv(PROCESSED_DIR / "heldout_predictions.csv", index=False)
    drivers.to_csv(PROCESSED_DIR / "driver_importance.csv", index=False)
    return results, predictions, drivers, winner


def main() -> None:
    results, _, _, winner = run()
    print(
        results[["model", "heldout_rmse_t_per_ha", "heldout_r2"]].to_string(index=False)
    )
    print(f"winner: {winner}")


if __name__ == "__main__":
    main()
