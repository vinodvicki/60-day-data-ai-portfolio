"""Day 17 Drought Impact Analyzer: analysis.

Pure functions over the processed CSVs: yield detrending, the three frozen
drought/yield correlations, drought-year case studies, the AR(1) DSCI
forecast, and the county ranking. No network access, no raw-file reads.

Run standalone: ``python -m src.analysis`` reads
``data/processed/annual_drought_yield.csv`` (written by the pipeline),
adds the yield-residual columns in place, and writes
``correlation_results.csv`` and ``ar1_forecast.csv``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"

# Frozen correlations (plan §2.2): (variable column, slope units).
CORRELATIONS = [
    ("gs_dsci_mean", "t/ha per DSCI point"),
    ("gs_precip_anomaly_mm", "t/ha per mm"),
    ("jul_precip_anomaly_mm", "t/ha per mm"),
]

BACKTEST_YEAR = 2025
FORECAST_YEAR = 2026


def detrend_yield(annual: pd.DataFrame) -> pd.DataFrame:
    """Add the linear year trend fit and the yield residual (t/ha).

    Returns a copy with ``yield_trend_fit_t_per_ha`` and
    ``yield_resid_t_per_ha`` columns. The trend slope (t/ha/yr) is stored
    in the frame's attrs for the caller to report.
    """
    frame = annual.copy()
    model = LinearRegression()
    model.fit(frame[["year"]].to_numpy(dtype=float), frame["yield_t_per_ha"])
    frame["yield_trend_fit_t_per_ha"] = model.predict(
        frame[["year"]].to_numpy(dtype=float)
    )
    frame["yield_resid_t_per_ha"] = (
        frame["yield_t_per_ha"] - frame["yield_trend_fit_t_per_ha"]
    )
    frame.attrs["trend_slope_t_per_ha_per_year"] = float(model.coef_[0])
    frame.attrs["trend_intercept_t_per_ha"] = float(model.intercept_)
    return frame


def compute_correlations(annual: pd.DataFrame) -> pd.DataFrame:
    """The three frozen correlations of drought/rain vs detrended yield.

    Each row: variable, pearson_r, p_value, r_squared, ols_slope,
    slope_units, n. Primary result is against the detrended residual;
    the raw-yield correlation is added for transparency.
    """
    rows = []
    y_resid = annual["yield_resid_t_per_ha"].to_numpy(dtype=float)
    y_raw = annual["yield_t_per_ha"].to_numpy(dtype=float)
    for variable, units in CORRELATIONS:
        x = annual[variable].to_numpy(dtype=float)
        r, p = stats.pearsonr(x, y_resid)
        slope_model = LinearRegression()
        slope_model.fit(x.reshape(-1, 1), y_resid)
        r_raw, p_raw = stats.pearsonr(x, y_raw)
        rows.append(
            {
                "variable": variable,
                "pearson_r": float(r),
                "p_value": float(p),
                "r_squared": float(r) ** 2,
                "ols_slope": float(slope_model.coef_[0]),
                "slope_units": units,
                "n": len(annual),
                "pearson_r_raw_yield": float(r_raw),
                "p_value_raw_yield": float(p_raw),
            }
        )
    return pd.DataFrame(rows)


def worst_drought_years(annual: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """The n worst drought years by growing-season mean DSCI."""
    return (
        annual.sort_values("gs_dsci_mean", ascending=False)
        .head(n)[
            [
                "year",
                "gs_dsci_mean",
                "gs_precip_anomaly_mm",
                "gs_precip_anomaly_pct",
                "yield_t_per_ha",
                "yield_resid_t_per_ha",
            ]
        ]
        .reset_index(drop=True)
    )


def worst_county_in_year(county_year: pd.DataFrame, year: int) -> dict[str, object]:
    """The hardest-hit county in a given year (max growing-season D2+ %)."""
    subset = county_year[county_year["year"] == year]
    row = subset.loc[subset["gs_d2plus_pct"].idxmax()]
    return {
        "year": year,
        "county": str(row["county"]),
        "state": str(row["state"]),
        "fips": str(row["fips"]),
        "gs_d2plus_pct": float(row["gs_d2plus_pct"]),
        "gs_dsci": float(row["gs_dsci"]),
    }


def fit_ar1(series: pd.Series) -> tuple[float, float, float]:
    """OLS AR(1): y_t = a + b * y_{t-1}. Returns (intercept, slope, resid_std)."""
    values = series.to_numpy(dtype=float)
    x = values[:-1].reshape(-1, 1)
    y = values[1:]
    model = LinearRegression()
    model.fit(x, y)
    resid = y - model.predict(x)
    resid_std = float(np.std(resid, ddof=2))
    return float(model.intercept_), float(model.coef_[0]), resid_std


def ar1_forecast_table(annual: pd.DataFrame) -> pd.DataFrame:
    """Backtest the AR(1) on 2025, then refit on all years for 2026.

    Columns: year, actual, ar1_forecast, naive_forecast, ar1_abs_error,
    naive_abs_error, lower, upper. The 2026 row has no actual; its
    interval is the forecast +/- 1 residual std of the full fit.
    """
    series = annual.sort_values("year")["gs_dsci_mean"]

    train = series.iloc[:-1]  # 2000-2024: the backtest fit never sees 2025
    a_b, b_b, _ = fit_ar1(train)
    forecast_2025 = a_b + b_b * float(series.iloc[-2])
    actual_2025 = float(series.iloc[-1])
    naive_2025 = float(series.iloc[-2])

    a_f, b_f, resid_std = fit_ar1(series)
    forecast_2026 = a_f + b_f * actual_2025

    return pd.DataFrame(
        [
            {
                "year": BACKTEST_YEAR,
                "actual": actual_2025,
                "ar1_forecast": forecast_2025,
                "naive_forecast": naive_2025,
                "ar1_abs_error": abs(forecast_2025 - actual_2025),
                "naive_abs_error": abs(naive_2025 - actual_2025),
                "lower": np.nan,
                "upper": np.nan,
            },
            {
                "year": FORECAST_YEAR,
                "actual": np.nan,
                "ar1_forecast": forecast_2026,
                "naive_forecast": actual_2025,
                "ar1_abs_error": np.nan,
                "naive_abs_error": np.nan,
                "lower": forecast_2026 - resid_std,
                "upper": forecast_2026 + resid_std,
            },
        ]
    )


def top_counties(summary: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top n counties by mean growing-season D2+ % over 2000-2025."""
    return summary.sort_values("mean_d2plus_pct", ascending=False).head(n)


def run() -> dict[str, object]:
    """Run the full analysis over the processed CSVs and write outputs."""
    annual = pd.read_csv(PROCESSED_DIR / "annual_drought_yield.csv")
    county_year = pd.read_csv(PROCESSED_DIR / "county_year.csv")
    summary = pd.read_csv(PROCESSED_DIR / "county_summary.csv")

    annual = detrend_yield(annual)
    trend_slope = float(annual.attrs["trend_slope_t_per_ha_per_year"])
    correlations = compute_correlations(annual)
    forecast = ar1_forecast_table(annual)

    annual.to_csv(PROCESSED_DIR / "annual_drought_yield.csv", index=False)
    correlations.to_csv(PROCESSED_DIR / "correlation_results.csv", index=False)
    forecast.to_csv(PROCESSED_DIR / "ar1_forecast.csv", index=False)

    worst = worst_drought_years(annual, 3)
    worst_year = int(worst.iloc[0]["year"])
    worst_county = worst_county_in_year(county_year, worst_year)
    top10 = top_counties(summary, 10)
    return {
        "trend_slope": trend_slope,
        "correlations": correlations,
        "forecast": forecast,
        "worst_years": worst,
        "worst_county": worst_county,
        "top_counties": top10,
    }


def main() -> None:
    out = run()
    trend_slope = out["trend_slope"]
    assert isinstance(trend_slope, float)
    correlations = out["correlations"]
    assert isinstance(correlations, pd.DataFrame)
    forecast = out["forecast"]
    assert isinstance(forecast, pd.DataFrame)
    dsci_row = correlations.loc[correlations["variable"] == "gs_dsci_mean"].iloc[0]
    print(
        f"trend_slope={trend_slope:.4f} t/ha/yr "
        f"dsci_r={float(dsci_row['pearson_r']):.3f} "
        f"p={float(dsci_row['p_value']):.4g} "
        f"forecast_2026={float(forecast.loc[forecast['year'] == 2026, 'ar1_forecast'].iloc[0]):.1f}"
    )


if __name__ == "__main__":
    main()
