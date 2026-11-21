"""Charts for Day 14 — Voter Turnout Analytics (exactly 4, matplotlib).

All charts are drawn from the committed processed CSVs only (chart 01
also needs the downloaded Census shapefile — see the offline note in
plan §3.4). Every chart is footnoted with the source + CC BY 4.0
attribution and the coverage, states its denominator in the title,
and uses the fixed cycle-type palette (presidential blue, midterm
grey). No chart mixes cycle types without labelling them; no chart
draws a trend line through alternating cycle types.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from numpy.typing import NDArray

try:
    from src.turnout import MIDTERM_COLOUR, PRESIDENTIAL_COLOUR
except ImportError:  # pragma: no cover - running as a script from src/
    from turnout import MIDTERM_COLOUR, PRESIDENTIAL_COLOUR  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
CHARTS = ROOT / "outputs" / "charts"

SOURCE_FOOTNOTE = (
    "Source: Michael McDonald, University of Florida Election Lab, General Election "
    "Turnout Rates 1980–2022 v1.2 and 2024 General Election Turnout Rates v0.4, "
    "CC BY 4.0 — VEP turnout = ballots counted ÷ voting-eligible population."
)
COVERAGE_FOOTNOTE = (
    "Coverage: general elections 1980–2024, 50 states + DC + US total; "
    "pre-2010 national figures estimated."
)
CMAP = "Blues"


def _footnote(fig: plt.Figure, extra: str = "") -> None:
    """Add the standard source + coverage footnotes to a figure."""
    text = SOURCE_FOOTNOTE + "\n" + COVERAGE_FOOTNOTE
    if extra:
        text += "\n" + extra
    fig.text(0.01, 0.005, text, fontsize=7, color="#555555", ha="left", va="bottom")


def _rate_range(state_2024: pd.DataFrame) -> tuple[float, float]:
    """Min/max 2024 VEP turnout across the 51 jurisdictions (shared scale)."""
    rates = state_2024.loc[~state_2024["is_national"].astype(bool), "vep_turnout_rate"]
    return float(rates.min()), float(rates.max())


def build_chart_01_map(root: Path = ROOT) -> Path | None:
    """State choropleth: 2024 VEP turnout by state (plan §7 chart 01).

    Returns the PNG path, or ``None`` when the shapefile is absent
    (offline rule, plan §3.4 — the committed PNG stands, never a broken chart).
    """
    import geopandas as gpd

    proc = root / "data" / "processed"
    state_2024 = pd.read_csv(proc / "state_2024.csv")
    shp_dir = root / "data" / "raw" / "shapefile"
    shps = list(shp_dir.glob("*.shp")) if shp_dir.exists() else []
    if not shps:
        print("Shapefile absent — chart 01 not regenerated (committed PNG stands).")
        return None
    geo = gpd.read_file(shps[0])
    states = state_2024[~state_2024["is_national"].astype(bool)].copy()
    merged = geo.merge(states, left_on="STUSPS", right_on="state_abv", how="inner")
    if len(merged) != 51:
        raise ValueError(f"Choropleth join produced {len(merged)} states, expected 51")
    vmin, vmax = _rate_range(state_2024)
    norm = Normalize(vmin=vmin, vmax=vmax)

    ak = merged[merged["STUSPS"] == "AK"].copy()
    ak["geometry"] = ak.geometry.scale(xfact=0.35, yfact=0.35, origin=(0, 0)).translate(
        xoff=-61.0, yoff=7.0
    )
    hi = merged[merged["STUSPS"] == "HI"].copy()
    hi["geometry"] = hi.geometry.translate(xoff=55.0, yoff=4.5)

    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_axes((0.02, 0.12, 0.96, 0.78))
    ax.set_axis_off()
    conus = merged[~merged["STUSPS"].isin(["AK", "HI"])]
    conus.plot(
        column="vep_turnout_rate",
        cmap=CMAP,
        norm=norm,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
    )
    ak.plot(
        column="vep_turnout_rate",
        cmap=CMAP,
        norm=norm,
        ax=ax,
        edgecolor="#888888",
        linewidth=0.4,
    )
    hi.plot(
        column="vep_turnout_rate",
        cmap=CMAP,
        norm=norm,
        ax=ax,
        edgecolor="#888888",
        linewidth=0.4,
    )
    ax.set_xlim(-125, -66)
    ax.set_ylim(20, 50)
    ax.text(-115, 23.2, "Alaska", fontsize=8, ha="center")
    ax.text(-102.5, 21.6, "Hawaii", fontsize=8, ha="center")
    # DC is too small to see at this scale — mark and label it.
    dc_rate = float(states.loc[states["state_abv"] == "DC", "vep_turnout_rate"].iloc[0])
    ax.plot([-77.0], [38.9], marker="o", color="#08306b", markersize=4)
    ax.annotate(
        f"DC {dc_rate:.2f}%",
        xy=(-77.0, 38.9),
        xytext=(-95.0, 48.2),
        fontsize=8,
        arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 0.8},
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#cccccc", "pad": 1.5},
    )
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.01)
    cbar.set_label("2024 VEP turnout (%)", fontsize=9)
    fig.suptitle(
        "2024 general election — VEP turnout by state (%)",
        fontsize=14,
        fontweight="bold",
    )
    _footnote(
        fig,
        "Alaska and Hawaii shown in inset positions; DC labelled (too small to "
        "colour at this scale). 2024 figures are the lab's preliminary v0.4 release.",
    )
    out = CHARTS / "01_turnout_map_2024.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def build_chart_02_time(root: Path = ROOT) -> Path:
    """National VEP turnout 1980–2024, split by cycle type (plan §7 chart 02)."""
    national = pd.read_csv(root / "data" / "processed" / "national_series.csv")
    fig, ax = plt.subplots(figsize=(11, 6))
    for cycle, colour, marker, label in (
        ("presidential", PRESIDENTIAL_COLOUR, "o", "Presidential years"),
        ("midterm", MIDTERM_COLOUR, "s", "Midterm years"),
    ):
        series = national[national["cycle_type"] == cycle].sort_values("year")
        solid = series[~series["national_estimated"].astype(bool)]
        estimated = series[series["national_estimated"].astype(bool)]
        ax.plot(
            solid["year"],
            solid["vep_turnout_rate"],
            color=colour,
            marker=marker,
            label=label,
            linewidth=2,
        )
        if len(estimated):
            ax.plot(
                estimated["year"],
                estimated["vep_turnout_rate"],
                color=colour,
                marker=marker,
                markerfacecolor="white",
                markeredgewidth=1.5,
                linestyle="None",
                label=f"{label} — estimated (pre-2010)",
            )
    row_2024 = national[national["year"] == 2024].iloc[0]
    ax.annotate(
        f"2024: {float(row_2024['vep_turnout_rate']):.2f}% (preliminary v0.4)",
        xy=(2024, float(row_2024["vep_turnout_rate"])),
        xytext=(2006, 70),
        fontsize=9,
        arrowprops={"arrowstyle": "->", "color": "#333333"},
    )
    ax.set_xlabel("General election year")
    ax.set_ylabel("VEP turnout (%)")
    ax.set_title(
        "National VEP turnout, 1980–2024 — presidential vs midterm years",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_ylim(30, 75)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=9)
    fig.subplots_adjust(bottom=0.24)
    _footnote(
        fig,
        "Each series connects only years of the same cycle type; no line crosses "
        "cycle types. National VEP turnout is not reported in the file for 1980–1996.",
    )
    out = CHARTS / "02_turnout_over_time.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def _build_chart_03_figure(root: Path = ROOT) -> tuple[plt.Figure, NDArray[np.object_]]:
    """Build the chart-03 figure (top 10 / bottom 10 ranking) without saving.

    Split out of :func:`build_chart_03_ranking` so the regression test can
    inspect the legend / label geometry on the live figure (D-1).
    """
    state_2024 = pd.read_csv(root / "data" / "processed" / "state_2024.csv")
    states = state_2024[~state_2024["is_national"].astype(bool)].copy()
    us_rate = float(
        state_2024.loc[state_2024["is_national"].astype(bool), "vep_turnout_rate"].iloc[
            0
        ]
    )
    top = states.sort_values(
        ["vep_turnout_rate", "state_abv"], ascending=[False, True]
    ).head(10)
    bottom = states.sort_values(
        ["vep_turnout_rate", "state_abv"], ascending=[True, True]
    ).head(10)
    vmin, vmax = _rate_range(state_2024)
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(CMAP)

    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
    for ax, frame, title in (
        (axes[0], top.iloc[::-1], "Top 10 states — 2024 VEP turnout (%)"),
        (axes[1], bottom.iloc[::-1], "Bottom 10 states — 2024 VEP turnout (%)"),
    ):
        colours = [cmap(norm(float(v))) for v in frame["vep_turnout_rate"]]
        ax.barh(
            frame["state"], frame["vep_turnout_rate"], color=colours, edgecolor="white"
        )
        ax.axvline(
            us_rate,
            color="#c0392b",
            linestyle="--",
            linewidth=1.5,
            label=f"US total {us_rate:.2f}%",
        )
        for i, (_, row) in enumerate(frame.iterrows()):
            ax.text(
                float(row["vep_turnout_rate"]) + 0.4,
                i,
                f"{float(row['vep_turnout_rate']):.2f}%  (rank {int(row['rank_vep'])})",
                va="center",
                fontsize=9,
            )
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlim(0, vmax + 12)
        ax.grid(axis="x", alpha=0.3)
        # D-1: the legend used to sit inside the data area (lower right),
        # where it covered the Iowa "70.95% (rank 10)" label. It now sits
        # outside the axes, to the right, clear of every bar label.
        ax.legend(fontsize=9, loc="center left", bbox_to_anchor=(1.01, 0.5))
    axes[1].set_xlabel("2024 VEP turnout (%)")
    fig.suptitle(
        "State ranking — 2024 VEP turnout, top 10 and bottom 10",
        fontsize=13,
        fontweight="bold",
    )
    _footnote(
        fig,
        "Rank 1 = highest VEP turnout. US total shown as a reference line, never ranked.",
    )
    return fig, axes


def build_chart_03_ranking(root: Path = ROOT) -> Path:
    """Top 10 and bottom 10 states by 2024 VEP turnout (plan §7 chart 03)."""
    fig, _axes = _build_chart_03_figure(root)
    out = CHARTS / "03_state_ranking_2024.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def build_chart_04_scatter(root: Path = ROOT) -> Path:
    """Demographic indicators vs 2024 VEP turnout (plan §7 chart 04).

    Three small-multiple scatter panels, each annotated with Pearson r,
    Spearman rho, n and p. Association only — not a causal claim.
    """
    state_2024 = pd.read_csv(root / "data" / "processed" / "state_2024.csv")
    correlations = pd.read_csv(root / "data" / "processed" / "correlations.csv")
    states = state_2024[~state_2024["is_national"].astype(bool)].copy()
    panels: list[tuple[str, str, str, np.ndarray]] = [
        (
            "noncitizen_pct",
            "Noncitizen share of VAP (%)",
            "Noncitizen share",
            states["noncitizen_pct"].to_numpy(dtype=float),
        ),
        (
            "felon_share_vap",
            "Ineligible-felon share of VAP (%)",
            "Felon share",
            states["felon_share_vap"].to_numpy(dtype=float) * 100.0,
        ),
        (
            "overseas_share_vep",
            "Overseas eligible share of VEP (%)",
            "Overseas share",
            states["overseas_share_vep"].to_numpy(dtype=float) * 100.0,
        ),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    y = states["vep_turnout_rate"].to_numpy(dtype=float)
    for ax, (indicator, xlabel, title, x) in zip(axes, panels, strict=True):
        row = correlations[correlations["indicator"] == indicator].iloc[0]
        n = int(row["n"])
        if n >= 3 and not np.isnan(x).all():
            ax.scatter(x, y, s=28, color=PRESIDENTIAL_COLOUR, alpha=0.8)
            annotation = (
                f"Pearson r = {float(row['pearson_r']):.2f} (p = {float(row['pearson_p']):.3g})\n"
                f"Spearman ρ = {float(row['spearman_r']):.2f} (p = {float(row['spearman_p']):.3g})\n"
                f"n = {n}"
            )
        else:
            ax.set_xticks([])
            annotation = (
                "n = 0 — no association computable:\n"
                "the lab does not apportion eligible\n"
                "overseas voters to states."
            )
        ax.set_xlabel(xlabel, fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.text(
            0.05,
            0.95,
            annotation,
            transform=ax.transAxes,
            fontsize=8.5,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"},
        )
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("2024 VEP turnout (%)")
    fig.subplots_adjust(bottom=0.28)
    fig.suptitle(
        "Demographic indicators vs 2024 VEP turnout — association only",
        fontsize=13,
        fontweight="bold",
    )
    _footnote(
        fig,
        "Association only — not a causal claim. Each dot is one state (51 states + DC; "
        "US total excluded). Correlation is not causation.",
    )
    out = CHARTS / "04_demographic_scatter.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def build_all_charts(root: Path = ROOT) -> list[Path]:
    """Build all four charts; chart 01 is skipped if the shapefile is absent."""
    built: list[Path] = []
    chart_01 = build_chart_01_map(root)
    if chart_01 is not None:
        built.append(chart_01)
    built.append(build_chart_02_time(root))
    built.append(build_chart_03_ranking(root))
    built.append(build_chart_04_scatter(root))
    for path in built:
        print(f"Chart written: {path} ({path.stat().st_size} bytes)")
    return built


if __name__ == "__main__":
    build_all_charts()
