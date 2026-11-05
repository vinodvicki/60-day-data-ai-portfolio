"""Day 1 — Crypto Market Intelligence Dashboard (Streamlit).

Reads ONLY data/processed/*.csv (never calls the API).
Educational analysis only — not investment advice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(
    page_title="Crypto Market Intelligence — BTC vs ETH vs SOL",
    layout="wide",
)
st.title("Crypto Market Intelligence — BTC vs ETH vs SOL (365 days)")
st.caption(
    "Data source: CoinGecko (coingecko.com) | "
    "Educational analysis only — not investment advice."
)

# --- Load processed data only -------------------------------------------------
daily = pd.read_csv(PROCESSED_DIR / "crypto_daily.csv", parse_dates=["date"])
metrics = pd.read_csv(PROCESSED_DIR / "crypto_metrics.csv", parse_dates=["date"])

source_info = {}
source_path = PROCESSED_DIR / "data_source.json"
if source_path.exists():
    source_info = json.loads(source_path.read_text())
IS_SYNTHETIC = bool(source_info.get("synthetic", False))
if IS_SYNTHETIC:
    st.error(
        "⚠️ SYNTHETIC DATA — CoinGecko API was unavailable when this data "
        "was generated. Do not treat these values as real market data."
    )

window = f"{daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}"
st.caption(f"Data window: {window} (daily, UTC)")

# --- Sidebar ------------------------------------------------------------------
coins = st.sidebar.multiselect(
    "Coins",
    options=["bitcoin", "ethereum", "solana"],
    default=["bitcoin", "ethereum"],
    format_func=lambda c: {
        "bitcoin": "Bitcoin (BTC)",
        "ethereum": "Ethereum (ETH)",
        "solana": "Solana (SOL)",
    }[c],
)
if not coins:
    st.warning("Select at least one coin in the sidebar.")
    st.stop()

min_date, max_date = daily["date"].min().date(), daily["date"].max().date()
date_range = st.sidebar.slider(
    "Date range", min_value=min_date, max_value=max_date, value=(min_date, max_date)
)
log_volume = st.sidebar.checkbox("Volume chart: log scale", value=False)

d = daily[
    (daily["coin"].isin(coins))
    & (daily["date"] >= pd.Timestamp(date_range[0]))
    & (daily["date"] <= pd.Timestamp(date_range[1]))
].copy()
m = metrics[
    (metrics["coin"].isin(coins))
    & (metrics["date"] >= pd.Timestamp(date_range[0]))
    & (metrics["date"] <= pd.Timestamp(date_range[1]))
].copy()
d["price_indexed"] = d.groupby("coin")["price"].transform(lambda s: s / s.iloc[0] * 100)

# --- 1. Price indexed to 100 ---------------------------------------------------
st.subheader("1 · Momentum — price indexed to 100 (first day = 100)")
fig = px.line(
    d,
    x="date",
    y="price_indexed",
    color="coin",
    labels={
        "date": "Date",
        "price_indexed": "Price index (first day = 100)",
        "coin": "Coin",
    },
)
fig.update_layout(legend_title_text="Coin")
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Source: CoinGecko. Indexed prices make momentum comparable "
    "across coins with very different price levels."
)

# --- 2. Volume trends -----------------------------------------------------------
st.subheader("2 · Liquidity — trading volume and relative volume")
st.plotly_chart(
    px.line(
        d,
        x="date",
        y="volume",
        color="coin",
        log_y=log_volume,
        labels={"date": "Date", "volume": "24h trading volume (USD)", "coin": "Coin"},
    ),
    use_container_width=True,
)
st.plotly_chart(
    px.line(
        m,
        x="date",
        y="relative_volume",
        color="coin",
        labels={
            "date": "Date",
            "relative_volume": "Relative volume (volume / 30-day mean)",
            "coin": "Coin",
        },
    ),
    use_container_width=True,
)
st.caption(
    "Volume is a liquidity proxy (exchange-reported 24h volume, "
    "not order-book depth). Relative volume = 1 means volume is at "
    "its 30-day average. Source: CoinGecko."
)

# --- 3. Rolling volatility ------------------------------------------------------
st.subheader("3 · Volatility — 30-day rolling annualised volatility")
st.plotly_chart(
    px.line(
        m,
        x="date",
        y="vol_30d_annualised",
        color="coin",
        labels={
            "date": "Date",
            "vol_30d_annualised": "30-day rolling volatility, annualised (×√365)",
            "coin": "Coin",
        },
    ),
    use_container_width=True,
)
st.caption(
    "Realised volatility: std. dev. of daily returns over 30 days, "
    "annualised with √365 (crypto trades every day). Source: CoinGecko."
)

# --- 4. Drawdown timeline -------------------------------------------------------
st.subheader("4 · Drawdown — fall from peak (%)")
mm = m.copy()
mm["drawdown_pct"] = mm["drawdown"] * 100
st.plotly_chart(
    px.line(
        mm,
        x="date",
        y="drawdown_pct",
        color="coin",
        labels={
            "date": "Date",
            "drawdown_pct": "Drawdown from peak (%)",
            "coin": "Coin",
        },
    ),
    use_container_width=True,
)
st.caption(
    "Drawdown = price / running peak − 1. 0% means the coin is at a "
    "new high for the window. Source: CoinGecko."
)

# --- Summary table ---------------------------------------------------------------
st.subheader("Summary table (full window)")
rows = []
for coin, g in daily.groupby("coin"):
    # Reset the index: idxmin/idxmax return labels from the full frame,
    # which are out of bounds as positional indexes on a 366-row group.
    g = g.sort_values("date").reset_index(drop=True)
    mg = metrics[metrics["coin"] == coin].sort_values("date").reset_index(drop=True)
    total_return = g["price"].iloc[-1] / g["price"].iloc[0] - 1
    running_max = g["price"].cummax()
    dd = g["price"] / running_max - 1
    trough_idx = int(dd.idxmin())
    peak_idx = int(g["price"].iloc[: trough_idx + 1].idxmax())
    rows.append(
        {
            "Coin": coin,
            "Total return": f"{total_return:+.1%}",
            "7d return (end of window)": f"{mg['return_7d'].iloc[-1]:+.1%}",
            "Mean 30d volatility (ann.)": f"{mg['vol_30d_annualised'].mean():.1%}",
            "Max 30d volatility (ann.)": f"{mg['vol_30d_annualised'].max():.1%}",
            "Max drawdown": f"{dd.min():.1%}",
            "Peak-to-trough (days)": int(
                (g["date"].iloc[trough_idx] - g["date"].iloc[peak_idx]).days
            ),
            "Mean relative volume": f"{mg['relative_volume'].mean():.2f}×",
            "Mean turnover (vol / mkt cap)": f"{mg['turnover'].mean():.3f}",
        }
    )
summary = pd.DataFrame(rows)
btc_eth = metrics.pivot(index="date", columns="coin", values="daily_return")
corr = (
    float(btc_eth["bitcoin"].corr(btc_eth["ethereum"]))
    if {"bitcoin", "ethereum"} <= set(btc_eth.columns)
    else float("nan")
)
st.dataframe(summary, use_container_width=True, hide_index=True)
st.write(
    f"**BTC–ETH correlation of daily returns (full window): {corr:.3f}** "
    f"(90-day rolling correlation is in `crypto_metrics.csv`, "
    f"column `corr_btc_eth_90d`)."
)

st.divider()
st.caption(
    "Data source: CoinGecko (coingecko.com). "
    "Educational analysis only — not investment advice. "
    "Close prices only (no OHLC); daily granularity; 365-day window "
    "is the public-API limit."
)
