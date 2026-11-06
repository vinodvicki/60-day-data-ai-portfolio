"""Day 2 — Crypto Risk & Volatility Analyzer dashboard (Streamlit).

Reads ONLY data/processed/*.csv (never calls the API).
Educational analysis only — not investment advice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LABELS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
}

st.set_page_config(
    page_title="Crypto Risk & Volatility — BTC vs ETH vs SOL",
    layout="wide",
)
st.title("Crypto Risk & Volatility — BTC vs ETH vs SOL")
st.markdown(
    "**Powered by [CoinGecko](https://www.coingecko.com)** | "
    "Educational analysis only — not investment advice."
)

# --- Load processed data only -------------------------------------------------
daily = pd.read_csv(PROCESSED_DIR / "crypto_daily.csv", parse_dates=["date"])
summary = pd.read_csv(PROCESSED_DIR / "crypto_risk_summary.csv")
correlations = pd.read_csv(PROCESSED_DIR / "crypto_correlations.csv")

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
    default=["bitcoin", "ethereum", "solana"],
    format_func=lambda c: LABELS[c],
)
if not coins:
    st.warning("Select at least one coin in the sidebar.")
    st.stop()

d = daily[daily["coin"].isin(coins)].copy()
s = summary[summary["coin"].isin(coins)].copy()

# --- Summary risk table -------------------------------------------------------
st.subheader("Summary risk table (full window)")
st.markdown(
    "Drawdown = how far the price fell from its highest point. "
    "Volatility = how jumpy day-to-day moves were. "
    "Sharpe / Sortino = return per unit of risk (0% risk-free rate) — "
    "higher is better, but only on past data. "
    "VaR 95% = the loss on a typical bad day; CVaR 95% = the average loss "
    "on the worst 5% of days."
)
rows_dd = []
rows_risk = []
for coin in coins:
    g = d[d["coin"] == coin].sort_values("date").reset_index(drop=True)
    row = s[s["coin"] == coin].iloc[0]
    recovery = (
        f"{int(row['recovery_days'])} days"
        if bool(row["recovered_by_end"])
        else f"not recovered ({int(row['recovery_days'])}d since trough)"
    )
    rows_dd.append(
        {
            "Coin": LABELS[coin],
            "Total return": f"{row['total_return']:+.1%}",
            "Max drawdown": f"{row['max_drawdown']:.1%}",
            "Current drawdown": f"{row['current_drawdown']:.1%}",
            "Peak → trough": (
                f"{row['peak_date']} → {row['trough_date']} "
                f"({int(row['peak_to_trough_days'])}d)"
            ),
            "Recovery": recovery,
        }
    )
    rows_risk.append(
        {
            "Coin": LABELS[coin],
            "Mean 30d vol": f"{row['vol_30d_mean']:.1%}",
            "Median 30d vol": f"{row['vol_30d_median']:.1%}",
            "Max 30d vol": f"{row['vol_30d_max']:.1%}",
            "Sharpe": f"{row['sharpe']:.2f}",
            "Sortino": f"{row['sortino']:.2f}",
            "VaR 95%": f"{row['var_95']:.1%}",
            "CVaR 95%": f"{row['cvar_95']:.1%}",
        }
    )
# Split into two tables (D2): the single 12-column table was wider than a
# 1400 px viewport and hid the volatility / risk columns.
st.markdown("**Returns and drawdowns**")
st.dataframe(pd.DataFrame(rows_dd), use_container_width=True, hide_index=True)
st.markdown("**Volatility and tail risk (annualised vol, 0% risk-free)**")
st.dataframe(pd.DataFrame(rows_risk), use_container_width=True, hide_index=True)

# --- Correlations -------------------------------------------------------------
st.subheader("Correlations — did the coins fall together?")
st.markdown(
    "Correlation of daily returns: +1 means the coins moved together, "
    "0 means no link. High correlation means holding all three gave "
    "little protection when one fell."
)
st.dataframe(correlations, use_container_width=True, hide_index=True)

# --- 1. Drawdown ---------------------------------------------------------------
st.subheader("1 · Drawdown — fall from peak (%)")
dd = d.copy()
dd["drawdown_pct"] = dd["drawdown"] * 100
dd_wide = dd.pivot(index="date", columns="coin", values="drawdown_pct")
dd_wide.columns = [LABELS[c] for c in dd_wide.columns]
st.line_chart(dd_wide, y_label="Drawdown from peak (%)")
st.caption(
    "Drawdown = price / running peak − 1. 0% means the coin is at a new "
    "high for the window. Powered by CoinGecko (coingecko.com)."
)

# --- 2. Rolling volatility ------------------------------------------------------
st.subheader("2 · Volatility — 30-day rolling annualised volatility")
vol = d.copy()
vol["vol_pct"] = vol["vol_30d_ann"] * 100
vol_wide = vol.pivot(index="date", columns="coin", values="vol_pct")
vol_wide.columns = [LABELS[c] for c in vol_wide.columns]
st.line_chart(vol_wide, y_label="30-day rolling volatility, annualised (%)")
st.caption(
    "Realised volatility: std. dev. of daily returns over 30 days, "
    "annualised with √365 (crypto trades every day). "
    "Powered by CoinGecko (coingecko.com)."
)

# --- 3. Correlation heatmap ------------------------------------------------------
st.subheader("3 · Correlation heatmap — daily returns (full window)")
piv = d.pivot(index="date", columns="coin", values="daily_return")
corr = piv.corr()
st.plotly_chart(
    px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdYlGn",
        zmin=-1,
        zmax=1,
        labels={"color": "Correlation"},
    ),
    use_container_width=True,
)
st.caption(
    "Pearson correlation of daily returns, full window. "
    "Latest-90d values are in the table above. "
    "Powered by CoinGecko (coingecko.com)."
)

# --- 4. Risk-adjusted returns + VaR ----------------------------------------------
st.subheader("4 · Risk-adjusted returns and tail risk")
st.markdown(
    "Total return (%) is its own panel, and the Sharpe and Sortino ratios "
    "(0% risk-free rate) are a separate panel — they are ratios, not "
    "percents, so they are never plotted on the return axis — and every "
    "bar carries its value. Bottom: one-day historical VaR 95% and "
    "CVaR 95% — the loss on a typical bad day, and the average loss on "
    "the worst 5% of days."
)
# Sharpe / Sortino are ratios (≈ −0.4 to −0.9), not percents — plotting
# them on the total-return axis made them invisible slivers (D1). A
# twin axis in Plotly overlapped the grouped bars, so the ratios get
# their own separate panel instead, with a value label on every bar.
coin_labels = [LABELS[c] for c in s["coin"]]
fig_ret = go.Figure(
    go.Bar(
        x=coin_labels,
        y=s["total_return"] * 100,
        name="Total return (%)",
        text=[f"{v:+.1f}%" for v in s["total_return"] * 100],
        textposition="outside",
        marker_color="#2E86AB",
    )
)
fig_ret.update_layout(yaxis_title="Total return (%)", showlegend=False)
st.plotly_chart(fig_ret, use_container_width=True)
fig_ratios = go.Figure()
fig_ratios.add_trace(
    go.Bar(
        x=coin_labels,
        y=s["sharpe"],
        name="Sharpe (annualised)",
        text=[f"{v:.2f}" for v in s["sharpe"]],
        textposition="outside",
        marker_color="#F6AE2D",
    )
)
fig_ratios.add_trace(
    go.Bar(
        x=coin_labels,
        y=s["sortino"],
        name="Sortino (annualised)",
        text=[f"{v:.2f}" for v in s["sortino"]],
        textposition="outside",
        marker_color="#6A994E",
    )
)
fig_ratios.update_layout(
    barmode="group", yaxis_title="Sharpe / Sortino (ratio, 0% risk-free)"
)
st.plotly_chart(fig_ratios, use_container_width=True)
tail = s.melt(
    id_vars="coin",
    value_vars=["var_95", "cvar_95"],
    var_name="metric",
    value_name="value",
)
tail["value"] = tail["value"] * 100
st.plotly_chart(
    px.bar(
        tail,
        x="coin",
        y="value",
        color="metric",
        barmode="group",
        labels={"coin": "Coin", "value": "Daily loss (%)", "metric": "Metric"},
    ),
    use_container_width=True,
)

st.divider()
st.markdown(
    "Powered by [CoinGecko](https://www.coingecko.com). "
    "Educational analysis only — not investment advice. "
    "Close prices only (no OHLC); daily granularity; 366 daily observations "
    "per coin (2025-11-06 → 2026-11-06). Sharpe and Sortino use a 0% "
    "risk-free rate; VaR / CVaR are one-day historical figures on daily "
    "returns. Past volatility and drawdowns do not predict future risk."
)
