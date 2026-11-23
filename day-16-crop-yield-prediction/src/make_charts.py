"""Day 16 Crop Yield Prediction: charts.

Reads processed CSVs only (no network, no model code) and writes the four
charts in ``outputs/charts/``. Chart 04 is a plotly scatter_geo station
map saved with kaleido.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11})

# (state, latitude, longitude) — typed tuples so mypy can check the plot calls.
STATIONS: list[tuple[str, float, float]] = [
    ("Iowa", 41.8780, -93.0977),
    ("Illinois", 40.6331, -89.3985),
]


def chart_yield_history(df: pd.DataFrame, path: Path) -> None:
    """Yield 2000–2025 with train/held-out shading and a train-only trend."""
    train = df[df["split"] == "train"]
    slope, intercept = np.polyfit(train["year"], train["yield_t_per_ha"], 1)

    _, ax = plt.subplots(figsize=(10, 5.5))
    ax.axvspan(2000, 2019.5, color="#e8f0e8", label="Train years (2000–2019)")
    ax.axvspan(2019.5, 2025.5, color="#fde8e8", label="Held-out years (2020–2025)")
    ax.plot(
        df["year"],
        df["yield_t_per_ha"],
        "o-",
        color="#1f6f3f",
        lw=2,
        label="Actual yield",
    )
    ax.plot(
        train["year"],
        slope * train["year"] + intercept,
        "--",
        color="#888888",
        lw=1.5,
        label=f"Train trend (+{slope:.3f} t/ha/yr)",
    )
    dip = df.loc[df["year"] == 2012].iloc[0]
    ax.annotate(
        f"2012 drought dip\n{dip['yield_t_per_ha']:.2f} t/ha",
        xy=(2012, dip["yield_t_per_ha"]),
        xytext=(2005.5, dip["yield_t_per_ha"] - 1.6),
        arrowprops={"arrowstyle": "->", "color": "#555555"},
        fontsize=10,
    )
    last = df.iloc[-1]
    ax.annotate(
        f"2025: {last['yield_t_per_ha']:.2f} t/ha",
        xy=(2025, last["yield_t_per_ha"]),
        xytext=(2021.5, last["yield_t_per_ha"] + 0.6),
        arrowprops={"arrowstyle": "->", "color": "#555555"},
        fontsize=10,
    )
    ax.set_xlim(1999.5, 2025.5)
    ax.set_ylim(7, 12.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Maize yield (t/ha)")
    ax.set_title(
        "USA maize yield, 2000–2025\n(1 t/ha = 15.93 bu/acre; FAO via Our World in Data)"
    )
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def chart_actual_vs_predicted(
    predictions: pd.DataFrame, results: pd.DataFrame, path: Path
) -> None:
    """Held-out actual vs winner prediction vs naive-last, 2020–2025."""
    winner = str(results.loc[results["is_winner"], "model"].iloc[0])
    winner_rmse = float(
        results.loc[results["is_winner"], "heldout_rmse_t_per_ha"].iloc[0]
    )
    naive_rmse = float(
        results.loc[results["model"] == "naive_last", "heldout_rmse_t_per_ha"].iloc[0]
    )
    years = predictions["year"].to_numpy()
    x = np.arange(len(years))
    width = 0.25

    _, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(
        x - width,
        predictions["actual_t_per_ha"],
        width,
        label="Actual",
        color="#1f6f3f",
    )
    ax.bar(
        x, predictions[winner], width, label=f"{winner} (predicted)", color="#2f7fc1"
    )
    ax.bar(
        x + width,
        predictions["naive_last"],
        width,
        label="Naive: last year's yield",
        color="#c98a2f",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in years])
    ax.set_ylim(9.5, 12.5)
    ax.set_xlabel("Held-out year")
    ax.set_ylabel("Maize yield (t/ha)")
    ax.set_title(
        f"Held-out years: actual vs predicted\n"
        f"{winner} RMSE {winner_rmse:.3f} t/ha vs naive-last RMSE {naive_rmse:.3f} t/ha"
    )
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def chart_drivers(drivers: pd.DataFrame, path: Path) -> None:
    """Standardised OLS coefficients with Pearson r annotated."""
    ordered = drivers.sort_values("ols_std_coef")
    _, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#c0392b" if v < 0 else "#1f6f3f" for v in ordered["ols_std_coef"]]
    ax.barh(ordered["feature"], ordered["ols_std_coef"], color=colors)
    ax.axvline(0, color="#333333", lw=1)
    for i, (_, row) in enumerate(ordered.iterrows()):
        ax.text(
            row["ols_std_coef"] + (0.05 if row["ols_std_coef"] >= 0 else -0.05),
            i,
            f"r = {row['pearson_r']:+.2f}",
            va="center",
            ha="left" if row["ols_std_coef"] >= 0 else "right",
            fontsize=10,
        )
    ax.set_xlabel("Standardised OLS coefficient (t/ha per 1 SD of the feature)")
    # Wide left margin: negative-bar r-annotations sit inside the axes
    # instead of colliding with the y-tick labels (tester defect D-2).
    ax.set_xlim(-0.75, 1.05)
    ax.set_title(
        "What moves with US maize yield — driver analysis\n"
        "Association, not causation (n = 26 years)"
    )
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def chart_station_map(path: Path) -> None:
    """GIS element: the two Corn Belt weather stations (matplotlib route).

    The plan's first choice (plotly + kaleido) fails in this environment:
    kaleido 1.2.0 raises ``RuntimeError: Chromium.get_cli() received invalid
    args`` against plotly 7.1.0, so the plan's matplotlib fallback runs
    instead. Schematic lon/lat map — centroids only, no state boundaries.
    """
    _, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(-100, -84)
    ax.set_ylim(36, 46)
    ax.set_xlabel("Longitude (°W, shown as negative)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title(
        "Corn Belt weather proxy — 2 stations (Iowa + Illinois centroids)\n"
        "Schematic lon/lat map; markers are the exact coordinates used"
    )
    ax.grid(alpha=0.3)
    # Shaded Corn Belt band (approximate, labelled as such).
    ax.axhspan(40, 43.5, color="#e8f0e8", label="Core Corn Belt band (approx.)")
    for state, lat, lon in STATIONS:
        ax.plot(
            lon,
            lat,
            "o",
            ms=14,
            color="#1f6f3f",
            markeredgecolor="#0d3d1e",
            markeredgewidth=1.5,
        )
        ax.annotate(
            f"{state}\n{lat:.4f}, {lon:.4f}",
            xy=(lon, lat),
            xytext=(8, 10),
            textcoords="offset points",
            fontsize=11,
        )
    ax.legend(loc="lower left", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PROCESSED_DIR / "yield_weather.csv")
    predictions = pd.read_csv(PROCESSED_DIR / "heldout_predictions.csv")
    results = pd.read_csv(PROCESSED_DIR / "model_results.csv")
    drivers = pd.read_csv(PROCESSED_DIR / "driver_importance.csv")

    chart_yield_history(df, CHARTS_DIR / "01_yield_history.png")
    chart_actual_vs_predicted(
        predictions, results, CHARTS_DIR / "02_actual_vs_predicted.png"
    )
    chart_drivers(drivers, CHARTS_DIR / "03_feature_drivers.png")
    chart_station_map(CHARTS_DIR / "04_weather_stations_map.png")
    for name in sorted(p.name for p in CHARTS_DIR.glob("*.png")):
        print(name)


if __name__ == "__main__":
    main()
