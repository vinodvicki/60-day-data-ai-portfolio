"""Reorder logic for Day 11 — Inventory Demand Forecast.

All inputs are ASSUMPTIONS (plan §4.5): 1-week lead time, 95% service
level (z = 1.65) for smooth/erratic SKUs, 90% (z = 1.28) for
intermittent/lumpy SKUs, safety stock z·σ·√LT, order-up-to from zero
on-hand. Pure functions, no I/O, no network.
"""

import numpy as np
import pandas as pd

SERVICE_LEVELS = {
    "smooth": (0.95, 1.65),
    "erratic": (0.95, 1.65),
    "intermittent": (0.90, 1.28),
    "lumpy": (0.90, 1.28),
}

REORDER_COLUMNS = [
    "stock_code",
    "description",
    "cluster",
    "winning_method",
    "forecast_4w_units",
    "mean_weekly_units",
    "sigma_weekly_units",
    "safety_stock_units",
    "reorder_point_units",
    "order_up_to_units",
    "implied_order_zero_on_hand_units",
    "service_level",
    "stockout_risk_flag",
    "reorder_point_2wk_units",
]


def service_level_for(cluster: str) -> tuple[float, float]:
    """(service_level, z) for a demand-pattern cluster."""
    return SERVICE_LEVELS.get(cluster, (0.95, 1.65))


def safety_stock(sigma: float, z: float, lead_time_weeks: float = 1.0) -> float:
    """SS = z · σ · √(lead time in weeks)."""
    return float(z * sigma * np.sqrt(lead_time_weeks))


def reorder_point(mean_weekly: float, lead_time_weeks: float, ss: float) -> float:
    """ROP = mean weekly demand × lead time + safety stock."""
    return float(mean_weekly * lead_time_weeks + ss)


def order_up_to(forecast_4w: float, ss: float) -> float:
    """Order-up-to level S = forecast 4-week demand + safety stock."""
    return float(forecast_4w + ss)


def build_reorder_list(
    sku_summary: pd.DataFrame, forecasts: pd.DataFrame, winners: dict
) -> pd.DataFrame:
    """The 14-column reorder list (plan §4.5), one row per top-20 SKU.

    ``sku_summary`` may carry training-window columns
    ``mean_weekly_train`` / ``sigma_weekly_train`` (σ over weeks 1–48,
    non-zero weeks only for intermittent/lumpy); otherwise the
    52-week ``mean_weekly_units`` and a ``sigma_weekly_units`` column
    are used. ``winners`` maps cluster → winning method (a SKU-keyed
    mapping is also accepted). ``forecasts`` is the published
    ``forecast.csv`` frame; the 4-week total is summed per SKU.
    """
    forecast_4w = (
        forecasts[forecasts["stock_code"] != "AGGREGATE"]
        .groupby("stock_code")["forecast_units"]
        .sum()
    )
    rows = []
    for _, sku in sku_summary.iterrows():
        code = sku["stock_code"]
        cluster = str(sku["cluster"])
        winner = winners.get(cluster, winners.get(code, "n/a"))
        mean_weekly = float(
            sku["mean_weekly_train"]
            if "mean_weekly_train" in sku and pd.notna(sku["mean_weekly_train"])
            else sku["mean_weekly_units"]
        )
        sigma = float(
            sku["sigma_weekly_train"]
            if "sigma_weekly_train" in sku and pd.notna(sku["sigma_weekly_train"])
            else sku.get("sigma_weekly_units", 0.0)
        )
        service_level, z = service_level_for(cluster)
        ss = safety_stock(sigma, z, lead_time_weeks=1.0)
        rop = reorder_point(mean_weekly, 1.0, ss)
        rop_2wk = float(mean_weekly * 2 + z * sigma * np.sqrt(2.0))
        s_level = order_up_to(float(forecast_4w.get(code, 0.0)), ss)
        flag = (
            "review-manually" if cluster == "lumpy" or winner == "croston_sba" else "ok"
        )
        rows.append(
            {
                "stock_code": code,
                "description": sku["description"],
                "cluster": cluster,
                "winning_method": winner,
                "forecast_4w_units": float(forecast_4w.get(code, 0.0)),
                "mean_weekly_units": mean_weekly,
                "sigma_weekly_units": sigma,
                "safety_stock_units": ss,
                "reorder_point_units": rop,
                "order_up_to_units": s_level,
                "implied_order_zero_on_hand_units": float(max(s_level, 0.0)),
                "service_level": service_level,
                "stockout_risk_flag": flag,
                "reorder_point_2wk_units": rop_2wk,
            }
        )
    out = pd.DataFrame(rows, columns=REORDER_COLUMNS)
    return out.sort_values("order_up_to_units", ascending=False).reset_index(drop=True)
