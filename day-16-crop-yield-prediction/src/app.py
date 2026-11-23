"""Day 16 Crop Yield Prediction: Streamlit dashboard.

Reads processed CSVs only. Shows the yield history, the held-out
evaluation, the driver analysis and the station map, with the four
limitations stated on the page.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

st.set_page_config(page_title="Crop Yield Prediction — Day 16", layout="wide")
st.title("🌽 Crop Yield Prediction — US Maize, 2000–2025")
st.markdown(
    "Estimating USA maize yield from growing-season temperature and rainfall, "
    "scored on six held-out years (2020–2025) the models never saw."
)

df = pd.read_csv(PROCESSED_DIR / "yield_weather.csv")
results = pd.read_csv(PROCESSED_DIR / "model_results.csv")
predictions = pd.read_csv(PROCESSED_DIR / "heldout_predictions.csv")
drivers = pd.read_csv(PROCESSED_DIR / "driver_importance.csv")

winner_row = results.loc[results["is_winner"]].iloc[0]
winner = str(winner_row["model"])
winner_rmse = float(winner_row["heldout_rmse_t_per_ha"])
latest = df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Best model (held-out)", winner)
col2.metric(
    "Held-out RMSE",
    f"{winner_rmse:.3f} t/ha",
    f"{winner_rmse * 39.368 / 2.47105:.2f} bu/acre",
)
col3.metric(
    "2025 yield (actual)",
    f"{float(latest['yield_t_per_ha']):.2f} t/ha",
    f"{float(latest['yield_bu_per_acre']):.1f} bu/acre",
)
col4.metric("Years modelled", "26", "20 train · 6 held-out")

st.sidebar.header("Explore")
model_choice = st.sidebar.selectbox(
    "Model shown in the held-out table", ["OLS", "Ridge", "RandomForest"]
)
year_min, year_max = st.sidebar.slider(
    "Year range (history chart data)",
    min_value=int(df["year"].min()),
    max_value=int(df["year"].max()),
    value=(int(df["year"].min()), int(df["year"].max())),
)
shown = df[(df["year"] >= year_min) & (df["year"] <= year_max)]

st.header("Yield history")
st.image(str(CHARTS_DIR / "01_yield_history.png"), use_container_width=True)
st.dataframe(
    shown[["year", "yield_t_per_ha", "yield_bu_per_acre", "split"]],
    use_container_width=True,
    hide_index=True,
)

st.header("Held-out evaluation (2020–2025)")
st.image(str(CHARTS_DIR / "02_actual_vs_predicted.png"), use_container_width=True)
st.dataframe(
    results[
        [
            "model",
            "heldout_rmse_t_per_ha",
            "heldout_mae_t_per_ha",
            "heldout_r2",
            "heldout_bias_t_per_ha",
            "is_winner",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)
st.subheader(f"Held-out predictions — {model_choice}")
table = predictions[["year", "actual_t_per_ha", model_choice, "naive_last"]].copy()
table["error"] = table[model_choice] - table["actual_t_per_ha"]
st.dataframe(table, use_container_width=True, hide_index=True)

st.header("Driver analysis — association, not causation")
st.image(str(CHARTS_DIR / "03_feature_drivers.png"), use_container_width=True)
st.dataframe(drivers, use_container_width=True, hide_index=True)
st.markdown(
    "Drivers are statistical associations over 26 annual rows. "
    "A feature that moves with yield is not proof that it causes yield."
)

st.header("Where the weather comes from (GIS)")
st.image(str(CHARTS_DIR / "04_weather_stations_map.png"), use_container_width=True)
st.markdown(
    "Weather is the average of two Corn Belt centroids (Iowa 41.8780, "
    "−93.0977; Illinois 40.6331, −89.3985) — a proxy for the national "
    "yield series, not a national weather average."
)

st.header("Limitations — read before trusting the numbers")
st.markdown(
    "- **National yield, 2-state weather proxy:** see above.\n"
    "- **Small sample:** 26 annual rows, 20 for training. Held-out errors "
    "are the honest measure; R² on 6 points is noisy.\n"
    "- **Association, not causation:** drivers describe co-movement only.\n"
    "- **No USDA state data:** the USDA Quick Stats API needs a key "
    "(HTTP 401 without one), so FAO/OWID national yields are used instead. "
    "With a key, state-level NASS yields could replace the national series "
    "without changing the pipeline shape.\n"
    "- **No 2026 forecast:** the latest actual is the 2025 harvest."
)
st.caption(
    "Yield: FAO via Our World in Data (CC BY 4.0). "
    "Weather: Open-Meteo ERA5 archive (CC BY 4.0)."
)
