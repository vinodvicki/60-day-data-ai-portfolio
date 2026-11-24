"""Day 17 Drought Impact Analyzer: chart builder.

Reads the processed CSVs only (plus the county GeoJSON for chart 04) and
writes the four frozen charts to outputs/charts/ as PNGs. Every chart has
a title, labelled axes with units, a source line, and legible type.

Chart 04 is a matplotlib choropleth drawn from the plotly county GeoJSON
polygons (no geopandas, no kaleido). If the GeoJSON cannot be fetched or
cached, it falls back to a labelled top-15 county bar chart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import matplotlib
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection

matplotlib.use("Agg")

import requests

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"
RAW_DIR = ROOT / "data" / "raw"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)
GEOJSON_PATH = RAW_DIR / "counties_geo.json"

SOURCE_LINE = (
    "Sources: U.S. Drought Monitor (NDMC/USDA/NOAA); "
    "yield: FAO via Our World in Data; weather: Open-Meteo (ERA5)."
)
WORST_YEAR = 2012

plt.rcParams.update({"font.size": 10, "axes.titlesize": 13, "axes.labelsize": 11})


def _save(fig: plt.Figure, name: str) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _source_text(fig: plt.Figure) -> None:
    fig.text(0.01, 0.005, SOURCE_LINE, fontsize=8, color="#555555")


def chart_01_dsci_trend(annual: pd.DataFrame) -> Path:
    """Annual growing-season mean DSCI (IA+IL average), 2000-2025."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        annual["year"],
        annual["gs_dsci_mean"],
        marker="o",
        linewidth=2,
        label="IA + IL average",
    )
    ax.plot(
        annual["year"],
        annual["gs_dsci_mean_iowa"],
        linewidth=1,
        alpha=0.6,
        label="Iowa",
    )
    ax.plot(
        annual["year"],
        annual["gs_dsci_mean_illinois"],
        linewidth=1,
        alpha=0.6,
        label="Illinois",
    )
    ax.axhline(100, color="red", linestyle="--", linewidth=1, label="DSCI = 100")
    worst = annual.loc[annual["gs_dsci_mean"].idxmax()]
    ax.annotate(
        f"{int(worst['year'])}: DSCI {float(worst['gs_dsci_mean']):.0f}",
        xy=(float(worst["year"]), float(worst["gs_dsci_mean"])),
        xytext=(float(worst["year"]) - 7, float(worst["gs_dsci_mean"]) + 25),
        arrowprops={"arrowstyle": "->"},
        fontsize=10,
    )
    ax.set_title("Growing-season drought severity (DSCI), 2000–2025")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean DSCI, Apr–Sep (0–500)")
    ax.set_ylim(0, max(220.0, float(annual["gs_dsci_mean"].max()) * 1.15))
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    _source_text(fig)
    return _save(fig, "01_dsci_trend.png")


def chart_02_drought_vs_yield(annual: pd.DataFrame) -> Path:
    """Scatter: growing-season DSCI vs detrended yield residual, with OLS fit."""
    from sklearn.linear_model import LinearRegression

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = annual["gs_dsci_mean"].to_numpy(dtype=float)
    y = annual["yield_resid_t_per_ha"].to_numpy(dtype=float)
    ax.scatter(x, y, s=55, zorder=3)
    for _, row in annual.iterrows():
        ax.annotate(
            str(int(row["year"])),
            (float(row["gs_dsci_mean"]), float(row["yield_resid_t_per_ha"])),
            fontsize=8,
            xytext=(3, 3),
            textcoords="offset points",
        )
    model = LinearRegression()
    model.fit(x.reshape(-1, 1), y)
    xs = pd.Series([x.min(), x.max()])
    ax.plot(xs, model.predict(xs.to_numpy().reshape(-1, 1)), color="red", linewidth=2)
    r = float(pd.Series(x).corr(pd.Series(y)))
    ax.set_title(
        "Drought severity vs detrended maize yield residual\n"
        f"Pearson r = {r:.2f} (n = {len(annual)} years)"
    )
    ax.set_xlabel("Growing-season mean DSCI (IA + IL average, 0–500)")
    ax.set_ylabel("Yield residual after removing year trend (t/ha)")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.grid(alpha=0.3)
    _source_text(fig)
    return _save(fig, "02_drought_vs_yield.png")


def chart_03_precip_anomaly(annual: pd.DataFrame) -> Path:
    """Growing-season precipitation anomaly bars + yield residual line."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = [
        "#2c7fb8" if v >= 0 else "#b15928" for v in annual["gs_precip_anomaly_mm"]
    ]
    ax.bar(annual["year"], annual["gs_precip_anomaly_mm"], color=colors, width=0.8)
    ax.set_title(
        "Growing-season precipitation anomaly vs the 2000–2025 mean\n"
        "(blue = wetter than average, brown = drier)"
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Precipitation anomaly, Apr–Sep (mm)")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax2 = ax.twinx()
    ax2.plot(
        annual["year"],
        annual["yield_resid_t_per_ha"],
        color="black",
        marker="o",
        markersize=4,
        linewidth=1.5,
        label="Yield residual",
    )
    ax2.set_ylabel("Yield residual (t/ha)")
    ax2.legend(loc="upper right")
    ax.grid(alpha=0.3)
    _source_text(fig)
    return _save(fig, "03_precip_anomaly.png")


def _load_geojson() -> dict[str, Any] | None:
    """County GeoJSON from the local cache, else a live fetch (10 s timeout)."""
    if GEOJSON_PATH.exists():
        return cast(
            dict[str, Any], json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        )
    try:
        resp = requests.get(GEOJSON_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        GEOJSON_PATH.write_text(json.dumps(data), encoding="utf-8")
        return cast(dict[str, Any], data)
    except requests.RequestException:
        return None


def _polygons_for_feature(feature: dict[str, Any]) -> list[list[tuple[float, float]]]:
    """All exterior rings of one GeoJSON feature as (lon, lat) lists."""
    geom = feature["geometry"]
    rings: list[list[tuple[float, float]]] = []
    if geom["type"] == "Polygon":
        rings.append([(float(x), float(y)) for x, y in geom["coordinates"][0]])
    elif geom["type"] == "MultiPolygon":
        for polygon in geom["coordinates"]:
            rings.append([(float(x), float(y)) for x, y in polygon[0]])
    return rings


def chart_04_county_map(summary: pd.DataFrame) -> Path:
    """Choropleth: mean % of county area in D2+ drought, 2000–2025.

    Falls back to a labelled top-15 county bar chart if the GeoJSON is
    unavailable (plan §3.1).
    """
    geo = _load_geojson()
    # FIPS reads back from CSV as an int (19001); normalise to zero-padded
    # strings or the GeoJSON join matches nothing and the map is empty.
    summary = summary.copy()
    summary["fips"] = summary["fips"].astype(str).str.zfill(5)
    values = summary.set_index("fips")["mean_d2plus_pct"].to_dict()
    top3 = summary.sort_values("mean_d2plus_pct", ascending=False).head(3)
    if geo is None:
        return _chart_04_fallback(summary)

    wanted = {fips for fips in values}
    polys: list[list[tuple[float, float]]] = []
    poly_values: list[float] = []
    centroids: dict[str, tuple[float, float]] = {}
    for feature in geo["features"]:
        fips = str(feature["id"]).zfill(5)
        if fips not in wanted:
            continue
        rings = _polygons_for_feature(feature)
        polys.extend(rings)
        poly_values.extend([float(values[fips])] * len(rings))
        xs = [p[0] for ring in rings for p in ring]
        ys = [p[1] for ring in rings for p in ring]
        centroids[fips] = (sum(xs) / len(xs), sum(ys) / len(ys))
    if not polys:
        raise ValueError("no county polygons matched the GeoJSON (FIPS join failed)")

    fig, ax = plt.subplots(figsize=(10, 6))
    collection = PolyCollection(polys, cmap="YlOrRd", edgecolor="white", linewidths=0.4)
    collection.set_array(pd.Series(poly_values).to_numpy(dtype=float))
    collection.set_clim(0, max(poly_values) if poly_values else 1)
    ax.add_collection(collection)
    all_x = [p[0] for ring in polys for p in ring]
    all_y = [p[1] for ring in polys for p in ring]
    ax.set_xlim(min(all_x) - 0.5, max(all_x) + 0.5)
    ax.set_ylim(min(all_y) - 0.5, max(all_y) + 0.5)
    ax.set_aspect("equal")
    ax.set_title(
        "Where drought hit hardest: mean % of county area in severe+ (D2+) drought\n"
        "Growing season (Apr–Sep), 2000–2025 — Iowa + Illinois (201 counties)"
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    for _, row in top3.iterrows():
        fips = str(row["fips"]).zfill(5)
        if fips in centroids:
            lon, lat = centroids[fips]
            ax.annotate(
                f"{row['county']}, {row['state']}: {float(row['mean_d2plus_pct']):.1f}%",
                xy=(lon, lat),
                fontsize=9,
                fontweight="bold",
                bbox={"facecolor": "white", "alpha": 0.8, "pad": 2},
            )
    fig.colorbar(
        collection,
        ax=ax,
        shrink=0.8,
        label="Mean % of county area in D2+ drought",
    )
    _source_text(fig)
    return _save(fig, "04_county_map.png")


def _chart_04_fallback(summary: pd.DataFrame) -> Path:
    """Labelled fallback: top-15 counties by mean D2+ % (plan §3.1)."""
    top15 = summary.sort_values("mean_d2plus_pct", ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        [f"{c}, {s}" for c, s in zip(top15["county"], top15["state"])],
        top15["mean_d2plus_pct"],
        color="#b15928",
    )
    ax.invert_yaxis()
    ax.set_title(
        "Top 15 counties by mean % of area in severe+ (D2+) drought, 2000–2025\n"
        "(FALLBACK — county GeoJSON unavailable, so the map is a ranking)"
    )
    ax.set_xlabel("Mean % of county area in D2+ drought, growing season")
    ax.grid(axis="x", alpha=0.3)
    _source_text(fig)
    return _save(fig, "04_county_map.png")


def build_all() -> dict[str, Path]:
    """Build all four charts; return {name: path}."""
    annual = pd.read_csv(PROCESSED_DIR / "annual_drought_yield.csv")
    summary = pd.read_csv(PROCESSED_DIR / "county_summary.csv")
    return {
        "01_dsci_trend": chart_01_dsci_trend(annual),
        "02_drought_vs_yield": chart_02_drought_vs_yield(annual),
        "03_precip_anomaly": chart_03_precip_anomaly(annual),
        "04_county_map": chart_04_county_map(summary),
    }


def main() -> None:
    paths = build_all()
    for name, path in paths.items():
        print(f"{name}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
