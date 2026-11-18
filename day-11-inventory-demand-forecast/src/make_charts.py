"""Charts for Day 11 — exactly 4 PNGs (plan §7), matplotlib Agg,
offline from the processed CSVs + data_source.json only.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from src.forecast import DISPLAY_NAMES, FORECASTERS
except ImportError:  # pragma: no cover
    from forecast import DISPLAY_NAMES, FORECASTERS  # type: ignore[no-redef]

FOOTNOTE = (
    "Source: UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 — "
    "historical 2010–2011 data, trend extrapolation, not a seasonal prediction"
)
CLUSTERS = ["smooth", "erratic", "intermittent", "lumpy"]
CLUSTER_COLOURS = {
    "smooth": "#2e7d32",
    "erratic": "#1565c0",
    "intermittent": "#ef6c00",
    "lumpy": "#c62828",
}
METHOD_COLOURS = {
    "naive": "#9e9e9e",
    "moving_average": "#8d6e63",
    "croston_sba": "#ef6c00",
    "holt": "#1565c0",
    "gradient_boosting": "#6a1b9a",
}


def _footnote(fig: plt.Figure) -> None:
    fig.text(0.01, 0.005, FOOTNOTE, fontsize=7, color="#555555", ha="left")


def _load(day_dir: Path):
    proc = day_dir / "data" / "processed"
    record = json.loads((proc / "data_source.json").read_text(encoding="utf-8"))
    return {
        "weekly": pd.read_csv(proc / "weekly_demand.csv", parse_dates=["week_start"]),
        "aggregate": pd.read_csv(
            proc / "weekly_aggregate.csv", parse_dates=["week_start"]
        ),
        "sku": pd.read_csv(proc / "sku_summary.csv"),
        "backtest": pd.read_csv(proc / "backtest.csv"),
        "reorder": pd.read_csv(proc / "reorder_list.csv"),
        "forecast": pd.read_csv(proc / "forecast.csv"),
        "record": record,
    }


def chart_01(data: dict, out: Path) -> None:
    """Forecast vs actual on the primary holdout (weeks 49–52)."""
    weekly, aggregate, sku = data["weekly"], data["aggregate"], data["sku"]
    winners = data["record"]["winners_per_cluster"]
    agg_winner = data["record"]["aggregate_winner"]
    top4 = sku.sort_values("revenue_gbp", ascending=False).head(4)
    cluster_of = dict(zip(sku["stock_code"], sku["cluster"]))
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    fig.suptitle(
        "Forecast vs actual — primary holdout, weeks 49–52 (2011-11-07 → 2011-12-04)",
        fontsize=13,
        fontweight="bold",
    )
    panels = [("AGGREGATE", "Aggregate — all cleaned SKUs", agg_winner, aggregate)]
    for _, row in top4.iterrows():
        code = row["stock_code"]
        sub = weekly[weekly["stock_code"] == code].sort_values("week_start")
        panels.append(
            (
                code,
                f"{code} — {row['description'].strip()}",
                winners[cluster_of[code]],
                sub,
            )
        )
    for ax, (code, title, winner, frame) in zip(axes.flat, panels):
        frame = frame.sort_values("week_start")
        weeks = pd.to_datetime(frame["week_start"])
        units = frame["units"].to_numpy(dtype=float)
        train = pd.Series(units[:48], index=weeks[:48])
        winner_fc = FORECASTERS[winner](train, horizon=4)
        naive_fc = FORECASTERS["naive"](train, horizon=4)
        ax.plot(weeks, units, color="#333333", lw=1.5, label="Actual")
        ax.plot(
            weeks.iloc[48:52],
            winner_fc,
            marker="o",
            color="#1565c0",
            lw=1.8,
            label=f"Winner: {DISPLAY_NAMES[winner]}",
        )
        ax.plot(
            weeks.iloc[48:52],
            naive_fc,
            marker="s",
            color="#9e9e9e",
            lw=1.2,
            ls="--",
            label="Naïve",
        )
        ax.axvspan(
            weeks.iloc[48],
            weeks.iloc[51] + pd.Timedelta(days=6),
            color="#fff3cd",
            alpha=0.7,
            zorder=0,
        )
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("Units / week")
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=7, loc="upper left")
    axes.flat[-1].axis("off")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_02(data: dict, out: Path) -> None:
    """WAPE by method × cluster (primary holdout), with naïve reference."""
    bt, sku = data["backtest"], data["sku"]
    cluster_of = dict(zip(sku["stock_code"], sku["cluster"]))
    primary = bt[bt["origin"] == 48].copy()
    primary = primary[primary["stock_code"] != "AGGREGATE"]
    primary["cluster"] = primary["stock_code"].map(cluster_of)
    methods = ["naive", "moving_average", "croston_sba", "holt", "gradient_boosting"]
    # Volume-weighted WAPE per method × cluster (weights = actual holdout units).
    # Actual holdout totals per SKU from weekly demand.
    weekly = data["weekly"]
    holdout_totals = (
        weekly[weekly["week_start"] >= pd.Timestamp("2011-11-07")]
        .groupby("stock_code")["units"]
        .sum()
    )
    primary["actual_total"] = primary["stock_code"].map(holdout_totals)
    groups = CLUSTERS + ["overall"]
    values: dict[str, dict[str, float]] = {g: {} for g in groups}
    for group in groups:
        sub = primary if group == "overall" else primary[primary["cluster"] == group]
        for method in methods:
            m = sub[sub["method"] == method]
            if len(m) and m["wape"].notna().any():
                w = m["actual_total"].to_numpy(dtype=float)
                v = m["wape"].to_numpy(dtype=float)
                mask = ~np.isnan(v)
                values[group][method] = float(
                    np.sum(v[mask] * w[mask]) / np.sum(w[mask])
                )
    winners = data["record"]["winners_per_cluster"]
    winner_text = ", ".join(
        f"{c}: {DISPLAY_NAMES[winners[c]]}" for c in CLUSTERS if winners.get(c) != "n/a"
    )
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(groups))
    width = 0.15
    for i, method in enumerate(methods):
        vals = [values[g].get(method, np.nan) for g in groups]
        ax.bar(
            x + (i - 2) * width,
            [v * 100 if not np.isnan(v) else 0 for v in vals],
            width,
            color=METHOD_COLOURS[method],
            label=DISPLAY_NAMES[method],
        )
    naive_overall = values["overall"].get("naive", np.nan)
    if not np.isnan(naive_overall):
        ax.axhline(
            naive_overall * 100,
            color="#c62828",
            ls="--",
            lw=1.2,
            label=f"Naïve overall (beat this): {naive_overall*100:.1f}%",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([g.capitalize() for g in groups])
    ax.set_ylabel("WAPE on primary holdout (%)")
    ax.set_title(
        "Method comparison by WAPE — primary holdout (weeks 49–52)\n"
        f"Winners per cluster: {winner_text}",
        fontsize=11,
    )
    ax.legend(fontsize=8, ncol=2)
    ax.set_ylim(
        0, max(100, max(v * 100 for g in groups for v in values[g].values()) * 1.15)
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_03(data: dict, out: Path) -> None:
    """ADI vs CV² scatter with SBC quadrants; top-20 SKUs highlighted."""
    record = data["record"]
    stats = pd.DataFrame(record["all_sku_pattern_stats"])
    sku = data["sku"]
    top20 = set(sku["stock_code"])
    fig, ax = plt.subplots(figsize=(10, 6))
    for cluster in CLUSTERS:
        sub = stats[stats["cluster"] == cluster]
        rest = sub[~sub["stock_code"].isin(top20)]
        ax.scatter(
            rest["adi"],
            rest["cv2"],
            s=6,
            alpha=0.45,
            color=CLUSTER_COLOURS[cluster],
            label=f"{cluster} (n={len(sub)})",
        )
    top = stats[stats["stock_code"].isin(top20)]
    ax.scatter(
        top["adi"],
        top["cv2"],
        s=70,
        facecolors="none",
        edgecolors="#111111",
        linewidths=1.2,
        label="Top-20 SKU",
        zorder=5,
    )
    # Spread label offsets vertically (sorted by CV²) so the ADI ≈ 1
    # cluster of top-20 labels stays readable; x is log-scaled (labelled)
    # because ADI runs 1–52.
    for i, (_, row) in enumerate(top.sort_values("cv2").iterrows()):
        ax.annotate(
            str(row["stock_code"]),
            (row["adi"], row["cv2"]),
            fontsize=6.5,
            xytext=(4, ((i * 13) % 39) - 19),
            textcoords="offset points",
        )
    ax.axvline(1.32, color="#333333", ls="--", lw=1)
    ax.axhline(0.49, color="#333333", ls="--", lw=1)
    # Quadrant labels placed in their actual quadrants (smooth = low ADI,
    # low CV², bottom-left; erratic = low ADI, high CV², top-left;
    # intermittent = high ADI, low CV², bottom-right; lumpy = high/high).
    label_box = {
        "boxstyle": "round,pad=0.2",
        "facecolor": "white",
        "alpha": 0.75,
        "edgecolor": "none",
    }
    ax.text(
        0.02,
        0.02,
        "Smooth",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        bbox=label_box,
    )
    ax.text(
        0.02,
        0.97,
        "Erratic",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        va="top",
        bbox=label_box,
    )
    ax.text(
        0.98,
        0.02,
        "Intermittent",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="right",
        bbox=label_box,
    )
    ax.text(
        0.98,
        0.97,
        "Lumpy",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="right",
        va="top",
        bbox=label_box,
    )
    ax.set_xscale("log")
    ax.set_xlabel("ADI — average inter-demand interval (weeks, log scale)")
    ax.set_ylabel("CV² — squared coefficient of variation (non-zero weeks)")
    ax.set_title(
        "Demand-pattern clustering — every SKU with any demand "
        f"(n={len(stats)}); top-20 SKUs circled and labelled",
        fontsize=11,
    )
    ax.set_xlim(0.9, 60)
    ax.set_ylim(0, max(3, stats["cv2"].max() * 1.05))
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=5)
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_04(data: dict, out: Path) -> None:
    """Reorder list: forecast 4-week units + safety stock = order-up-to."""
    reorder = data["reorder"].sort_values("order_up_to_units", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 7))
    y = np.arange(len(reorder))
    colours = [CLUSTER_COLOURS[c] for c in reorder["cluster"]]
    ax.barh(
        y,
        reorder["forecast_4w_units"],
        color=colours,
        alpha=0.85,
        label="Forecast 4-week units",
    )
    ax.barh(
        y,
        reorder["safety_stock_units"],
        left=reorder["forecast_4w_units"],
        color=colours,
        alpha=0.35,
        hatch="//",
        edgecolor="#333333",
        label="Safety stock",
    )
    for i, (_, row) in enumerate(reorder.iterrows()):
        flag = (
            " ← review manually"
            if row["stockout_risk_flag"] == "review-manually"
            else ""
        )
        ax.text(
            row["order_up_to_units"] + 200,
            i,
            f"{row['order_up_to_units']:,.0f} ({row['cluster']}, "
            f"{row['service_level']:.0%}){flag}",
            va="center",
            fontsize=8,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(
        [
            f"{c} — {d.strip()}"
            for c, d in zip(reorder["stock_code"], reorder["description"])
        ],
        fontsize=8,
    )
    ax.set_xlabel("Units (order-up-to level S = forecast 4-week units + safety stock)")
    ax.set_title(
        "Proposed reorder list — order-up-to level per top-20 SKU\n"
        "Assumes zero on-hand stock and a 1-week lead time",
        fontsize=11,
    )
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, reorder["order_up_to_units"].max() * 1.85)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def build_charts(day_dir: Path) -> list[Path]:
    """Build all 4 charts; returns the written paths."""
    day_dir = Path(day_dir)
    charts_dir = day_dir / "outputs" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    data = _load(day_dir)
    outputs = []
    for name, fn in [
        ("01_forecast_vs_actual.png", chart_01),
        ("02_method_wape.png", chart_02),
        ("03_demand_pattern_clusters.png", chart_03),
        ("04_reorder_list.png", chart_04),
    ]:
        out = charts_dir / name
        fn(data, out)
        outputs.append(out)
    return outputs


def main() -> int:
    day_dir = Path(__file__).resolve().parents[1]
    for path in build_charts(day_dir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
