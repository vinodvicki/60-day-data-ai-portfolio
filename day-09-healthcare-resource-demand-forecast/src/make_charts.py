"""Generate the four static charts from data/processed/*.csv.

Run: python -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries the source footnote and the disclaimer that
this is public aggregate surveillance data, not a clinical or operational
decision tool; the bed chart adds the HHS source and the series end-date
2024-04-27. When the data is synthetic, every chart carries a
SYNTHETIC DATA label.

Honest-chart rules for this day: axes start at 0 where the value is a
share that can reach 0 (charts 01–03); the bed chart's y-axis starts
at 0 (matplotlib-auto upper limit, data range 0.0–78.9%) and says so in
its label; no truncated axes; chart 04(a)
shows an 8-week Holt-Winters extension of the bed series as a dashed
historical-method illustration only — the series ends 2024-04-27 and the
extension is NOT a current capacity prediction.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import forecast as forecast_mod

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

SOURCE_FOOTNOTE = (
    "Source: CDC NSSP via CDC Open Data (vutn-jzwm) — public aggregate "
    "surveillance data, not a clinical or operational decision tool."
)
BED_FOOTNOTE = (
    "Source: HHS hospital bed capacity via healthdata.gov (g62h-syeh); "
    "series ends 2024-04-27 — historical record, not current capacity."
)
DISCLAIMER = (
    "Public aggregate surveillance data, not a clinical or operational decision tool."
)
BLUE = "#1b6ca8"
LIGHT = "#7fb3d5"
ORANGE = "#d35400"
GREEN = "#1e8449"
GREY = "#5d6d7e"
BAND_COLOURS = {
    "Low": "#1e8449",
    "Moderate": "#d4ac0d",
    "High": "#d35400",
    "Surge": "#922b21",
}

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def _record() -> dict:
    return json.loads((PROCESSED_DIR / "data_source.json").read_text())


def _is_synthetic() -> bool:
    return bool(_record().get("synthetic"))


def _footnote(fig: plt.Figure, extra: str = "") -> None:
    text = SOURCE_FOOTNOTE + (f" {extra}" if extra else "")
    if _is_synthetic():
        text = "SYNTHETIC DATA — labelled fallback, not real data. " + text
    wrapped = "\n".join(textwrap.wrap(text, 115))
    fig.text(0.01, 0.02, wrapped, fontsize=8, color=GREY, ha="left", va="bottom")


def _load() -> dict[str, pd.DataFrame]:
    frames = {}
    for name in (
        "national_combined",
        "state_combined",
        "bed_utilisation",
        "forecast",
        "backtest",
        "band_history",
    ):
        frames[name] = pd.read_csv(PROCESSED_DIR / f"{name}.csv")
    return frames


def _save(fig: plt.Figure, name: str) -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS_DIR / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote outputs/charts/{name}")


def chart_01_forecast(frames: dict[str, pd.DataFrame], record: dict) -> None:
    """National Combined % history + 8-week forecast with intervals."""
    national = frames["national_combined"].copy()
    national["week_end"] = pd.to_datetime(national["week_end"])
    forecast = frames["forecast"].copy()
    forecast["week_end"] = pd.to_datetime(forecast["week_end"])
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(
        national["week_end"],
        national["combined_pct"],
        color=BLUE,
        lw=1.5,
        label="Observed Combined %",
    )
    ax.fill_between(
        forecast["week_end"],
        forecast["lo_95"],
        forecast["hi_95"],
        color=LIGHT,
        alpha=0.45,
        label="95% prediction interval",
    )
    ax.fill_between(
        forecast["week_end"],
        forecast["lo_80"],
        forecast["hi_80"],
        color=LIGHT,
        alpha=0.75,
        label="80% prediction interval",
    )
    ax.plot(
        forecast["week_end"],
        forecast["forecast_pct"],
        color=ORANGE,
        lw=2,
        marker="o",
        ms=4,
        label=f"{record['forecast']['published_method'].replace('_', ' ').title()} forecast",
    )
    for _, row in forecast.iterrows():
        ax.annotate(
            row["band"],
            (row["week_end"], row["hi_95"]),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=8,
            color=GREY,
        )
    latest = national.iloc[-1]
    ax.annotate(
        f"Latest: {latest['combined_pct']:.1f}% (week ending "
        f"{latest['week_end'].strftime('%Y-%m-%d')})",
        (latest["week_end"], latest["combined_pct"]),
        textcoords="offset points",
        xytext=(-10, 14),
        ha="right",
        fontsize=9,
        color=BLUE,
        weight="bold",
    )
    ax.axvline(latest["week_end"], color=GREY, ls="--", lw=0.8)
    ax.set_title("Respiratory ED share: history + 8-week forecast")
    ax.set_xlabel("Week ending")
    ax.set_ylabel("Combined % of all ED visits (pp)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    _footnote(
        fig,
        "Forecast weeks labelled with their demand band (Low <2%, "
        "Moderate 2–4%, High 4–6%, Surge >6%). Intervals: residual "
        "bootstrap, seed 42, 1,000 paths. Forecast weeks 7–8 exceed the "
        f"observed historical maximum "
        f"({record['forecast']['observed_max_combined_pct']:.1f}%) — read "
        "them as a severe-season scenario.",
    )
    _save(fig, "01_forecast.png")


def chart_02_backtest(frames: dict[str, pd.DataFrame], record: dict) -> None:
    """Backtest RMSE by origin + 80%-interval coverage by origin."""
    backtest = frames["backtest"]
    winner = record["forecast"]["published_method"]
    winner_label = winner.replace("_", " ").title()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    origins = sorted(backtest["origin"].unique())
    width = 0.35
    x = np.arange(len(origins))
    for i, method in enumerate(["holt_winters", "seasonal_naive"]):
        sub = backtest[backtest["method"] == method].set_index("origin").loc[origins]
        ax1.bar(
            x + (i - 0.5) * width,
            sub["rmse"],
            width,
            label=method.replace("_", " ").title(),
            color=BLUE if method == "holt_winters" else ORANGE,
        )
        ax2.bar(
            x + (i - 0.5) * width,
            sub["coverage_80"] * 100,
            width,
            label=method.replace("_", " ").title(),
            color=BLUE if method == "holt_winters" else ORANGE,
        )
    ax1.set_title("(a) Backtest RMSE by origin (lower is better)")
    ax1.set_xlabel("Origin (weeks before end of series)")
    ax1.set_ylabel("RMSE (percentage points)")
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(o) for o in origins])
    ax1.set_ylim(bottom=0)
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.3)
    ax2.set_title("(b) 80%-interval coverage by origin (target ≈ 80%)")
    ax2.set_xlabel("Origin (weeks before end of series)")
    ax2.set_ylabel("Coverage (%)")
    ax2.set_xticks(x)
    ax2.set_xticklabels([str(o) for o in origins])
    ax2.set_ylim(0, 100)
    ax2.axhline(80, color=GREEN, ls="--", lw=1.2, label="80% target")
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    fig.suptitle(
        f"Backtest: {winner_label} wins on mean RMSE "
        f"({record['forecast']['mean_rmse'][winner]:.2f} pp)",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.94])
    _footnote(
        fig,
        "Rolling-origin backtest: 3 origins (12 / 8 / 4 weeks before the "
        "end), 4-week horizons. MAPE is reported alongside RMSE/MAE in "
        "backtest.csv — it inflates when Combined % is near 1–2% in summer.",
    )
    _save(fig, "02_backtest.png")


def chart_03_bands(frames: dict[str, pd.DataFrame], record: dict) -> None:
    """National history coloured by demand band + top-5-state panel."""
    history = frames["band_history"].copy()
    history["week_end"] = pd.to_datetime(history["week_end"])
    states = frames["state_combined"].copy()
    states["week_end"] = pd.to_datetime(states["week_end"])
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 5.5), gridspec_kw={"width_ratios": [1.7, 1.3]}
    )
    for band, colour in BAND_COLOURS.items():
        sub = history[history["band"] == band]
        ax1.scatter(
            sub["week_end"], sub["combined_pct"], s=12, color=colour, label=band
        )
    for threshold in (2, 4, 6):
        ax1.axhline(threshold, color=GREY, ls=":", lw=1)
        ax1.text(
            history["week_end"].iloc[-1],
            threshold + 0.15,
            f"{threshold}%",
            fontsize=8,
            color=GREY,
            ha="right",
        )
    ax1.set_title("(a) National Combined % by demand band")
    ax1.set_xlabel("Week ending")
    ax1.set_ylabel("Combined % of all ED visits (pp)")
    ax1.set_ylim(bottom=0)
    ax1.legend(title="Band", fontsize=9)
    ax1.grid(axis="y", alpha=0.3)
    # Top-5 states by latest-4-week mean Combined %.
    latest_weeks = states["week_end"].max()
    recent = states[states["week_end"] > latest_weeks - pd.Timedelta(weeks=4)]
    top5 = (
        recent.groupby("geography")["combined_pct"]
        .mean()
        .sort_values(ascending=True)
        .tail(5)
    )
    ax2.barh(
        top5.index,
        top5.values,
        color=[BAND_COLOURS[forecast_mod.classify_band(v)] for v in top5.values],
    )
    for i, value in enumerate(top5.values):
        ax2.text(value + 0.1, i, f"{value:.1f}%", va="center", fontsize=9)
    ax2.set_title("(b) Top 5 states — latest-4-week mean")
    ax2.set_xlabel("Combined % (pp)")
    ax2.set_xlim(0, max(top5.values) * 1.25)
    ax2.grid(axis="x", alpha=0.3)
    observed_max = float(history["combined_pct"].max())
    surge_n = int((history["band"] == "Surge").sum())
    fig.suptitle(
        f"Demand bands: observed max {observed_max:.1f}% — "
        f"Surge (>6%) occurred in {surge_n} of {len(history)} weeks",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.94])
    _footnote(
        fig,
        "Bands: Low <2%, Moderate 2–4%, High 4–6%, Surge >6%. Surge is a "
        "real historical level here (18 of 161 weeks), not just a planning "
        "threshold.",
    )
    _save(fig, "03_demand_bands.png")


def chart_04_bed(frames: dict[str, pd.DataFrame], record: dict) -> None:
    """Bed utilisation history (+ HW illustration) and staffing table."""
    bed = frames["bed_utilisation"].copy()
    bed["week_end"] = pd.to_datetime(bed["week_end"])
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 5.5), gridspec_kw={"width_ratios": [1.7, 1.3]}
    )
    ax1.plot(
        bed["week_end"],
        bed["bed_utilisation"] * 100,
        color=BLUE,
        lw=1.2,
        label="Inpatient bed utilisation",
    )
    ax1.plot(
        bed["week_end"],
        bed["icu_occupancy"] * 100,
        color=ORANGE,
        lw=1.2,
        label="Adult ICU occupancy",
    )
    # 8-week Holt-Winters extension: a historical-method illustration
    # only — the series ends 2024-04-27, so this is NOT a current
    # capacity prediction.
    series = pd.Series(bed["bed_utilisation"].to_numpy(dtype=float))
    point, fitted = forecast_mod.holt_winters_forecast(series, 8)
    intervals = forecast_mod.bootstrap_intervals(
        np.asarray(fitted.resid, dtype=float)[
            np.isfinite(np.asarray(fitted.resid, dtype=float))
        ],
        point,
    )
    future_weeks = [
        bed["week_end"].iloc[-1] + pd.Timedelta(weeks=i + 1) for i in range(8)
    ]
    ax1.plot(
        future_weeks,
        point * 100,
        color=BLUE,
        lw=1.5,
        ls="--",
        label="HW 8-week extension (illustration only)",
    )
    ax1.fill_between(
        future_weeks,
        intervals["lo_80"] * 100,
        intervals["hi_80"] * 100,
        color=LIGHT,
        alpha=0.5,
    )
    ax1.annotate(
        "Series ends\n2024-04-27",
        (bed["week_end"].iloc[-1], bed["bed_utilisation"].iloc[-1] * 100),
        textcoords="offset points",
        xytext=(-60, 18),
        fontsize=9,
        color=BLUE,
        weight="bold",
    )
    ax1.set_title("(a) National weekly bed utilisation, 2020–2024")
    ax1.set_xlabel("Week ending")
    ax1.set_ylabel("Utilisation (%)")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(axis="y", alpha=0.3)
    ax2.axis("off")
    ax2.set_title("(b) Staffing scenario by demand band")
    rows = [
        ["Low", "Baseline roster", "—"],
        ["Moderate", "Baseline (monitor)", "—"],
        ["High", "+10% rostered shifts", "+10%"],
        ["Surge", "+25% shifts, defer electives", "+25%"],
    ]
    table = ax2.table(
        cellText=rows,
        colLabels=["Band", "Staffing posture", "Uplift"],
        colWidths=[0.24, 0.56, 0.20],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.8)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor(LIGHT)
        elif col == 0:
            cell.set_facecolor(BAND_COLOURS[rows[row - 1][0]])
            cell.set_text_props(color="white", weight="bold")
    ax2.text(
        0.5,
        0.08,
        "PLANNING ASSUMPTIONS — not measured data",
        ha="center",
        fontsize=9,
        weight="bold",
        color=ORANGE,
        transform=ax2.transAxes,
    )
    fig.suptitle(
        "Capacity side: bed utilisation is a historical record (ends 2024-04-27)",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.16, 1, 0.94])
    _footnote(
        fig,
        BED_FOOTNOTE + " Utilisation = Σ beds used / Σ beds per week "
        "(state-sum ratio, y-axis starts at 0). Early-2020 "
        "weeks reflect few reporting states (3–38) — treat the 2020 "
        "segment as thinly reported. The dashed extension re-runs the "
        "same Holt-Winters machinery on the historical series for "
        "illustration only. " + DISCLAIMER,
    )
    _save(fig, "04_bed_capacity.png")


def main() -> int:
    record = _record()
    frames = _load()
    chart_01_forecast(frames, record)
    chart_02_backtest(frames, record)
    chart_03_bands(frames, record)
    chart_04_bed(frames, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
