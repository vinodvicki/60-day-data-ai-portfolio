"""Day 18 Agricultural Commodity Price Analyzer: charts.

Four matplotlib charts, drawn to scale and legible (plan §7). Chart 04 is
a county choropleth of 2012 growing-season D2+ drought share (Iowa +
Illinois), drawn from the plotly county GeoJSON polygons with matplotlib;
it falls back to a labelled top-15 county bar chart when the GeoJSON is
unavailable. Run: python -m src.make_charts (from the day folder).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.collections import PolyCollection

try:
    from src import analysis as _analysis
except ImportError:  # running as a script from inside src/
    import analysis as _analysis  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
CHARTS_DIR = ROOT / "outputs" / "charts"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)
GEOJSON_PATH = RAW_DIR / "counties_geo.json"

COLORS = {"maize": "#b15928", "wheat": "#2c6e8f", "soybeans": "#4c7a3f"}
LABELS = {"maize": "Maize", "wheat": "Wheat", "soybeans": "Soybeans"}
MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _save(fig: plt.Figure, name: str) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _source_text(fig: plt.Figure) -> None:
    fig.text(
        0.01,
        0.005,
        "Source: IMF Primary Commodity Prices via FRED; "
        "weather: Open-Meteo ERA5; drought: U.S. Drought Monitor.",
        fontsize=8,
        color="#555555",
    )


def chart_01_price_levels(monthly: pd.DataFrame) -> Path:
    """Monthly price levels 1992-2026, 3 commodities, shock windows shaded."""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for commodity in ("maize", "wheat", "soybeans"):
        sub = monthly[monthly["commodity"] == commodity].sort_values("date")
        ax.plot(
            sub["date"],
            sub["price_usd_per_t"],
            color=COLORS[commodity],
            linewidth=1.4,
            label=LABELS[commodity],
        )
    ylim_top = 660
    ax.set_ylim(0, ylim_top)
    levels = [0.97, 0.88]
    short_labels = {
        "2007-08 food-price crisis": "2007–08 food crisis",
        "2012 US drought": "2012 drought",
        "2020 COVID trough": "2020 COVID trough",
        "2022 Russia-Ukraine war spike": "2022 war spike",
    }
    for i, (start, end, label) in enumerate(_analysis.SHOCK_WINDOWS):
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="#f2c94c", alpha=0.25)
        ax.text(
            pd.Timestamp(start),
            ylim_top * levels[i % 2],
            short_labels[label],
            fontsize=8,
            va="top",
            ha="left",
        )
    ax.set_title("Agricultural commodity prices, 1992–2026 (USD per metric ton)")
    ax.set_xlabel("Year")
    ax.set_ylabel("USD per metric ton")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    _source_text(fig)
    return _save(fig, "01_price_levels.png")


def chart_02_seasonality(seasonality: pd.DataFrame) -> Path:
    """Seasonal index by calendar month (full window), 3 commodities."""
    fig, ax = plt.subplots(figsize=(10, 5))
    full = seasonality[seasonality["window"] == "full"]
    for commodity in ("maize", "wheat", "soybeans"):
        sub = full[full["commodity"] == commodity].sort_values("month")
        ax.plot(
            sub["month"],
            sub["seasonal_index"],
            color=COLORS[commodity],
            marker="o",
            markersize=4,
            linewidth=1.6,
            label=LABELS[commodity],
        )
    ax.axhline(1.0, color="#888888", linestyle="--", linewidth=1)
    ax.text(
        0.02,
        0.96,
        "Peaks: Maize May 1.04 · Wheat May 1.03 · Soybeans Jun 1.04",
        transform=ax.transAxes,
        fontsize=9,
        va="top",
        ha="left",
        bbox={"facecolor": "white", "alpha": 0.85, "pad": 3, "edgecolor": "#cccccc"},
    )
    ax.set_xlim(1, 12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_title("Seasonality: price index by calendar month (1.00 = annual mean)")
    ax.set_xlabel("Calendar month")
    ax.set_ylabel("Seasonal index")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    _source_text(fig)
    return _save(fig, "02_seasonality.png")


def chart_03_volatility_shocks(monthly: pd.DataFrame, shocks: pd.DataFrame) -> Path:
    """Two panels: 12-month rolling volatility; top-10 shock months."""
    vol = _analysis.rolling_volatility(monthly)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    for commodity in ("maize", "wheat", "soybeans"):
        sub = vol[vol["commodity"] == commodity].sort_values("date")
        ax1.plot(
            sub["date"],
            sub["rolling_vol_12m_pct"],
            color=COLORS[commodity],
            linewidth=1.3,
            label=LABELS[commodity],
        )
    ax1.set_title("12-month rolling volatility of monthly log returns (annualised %)")
    ax1.set_ylabel("Volatility, %")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    top10 = shocks[shocks["top10"]].copy()
    top10 = top10.sort_values("log_return", key=lambda s: s.abs(), ascending=True)
    labels = [
        f"{row['date'].strftime('%Y-%m')} {LABELS[row['commodity']]}"
        for _, row in top10.iterrows()
    ]
    bar_colors = [COLORS[c] for c in top10["commodity"]]
    ax2.barh(labels, top10["log_return"] * 100, color=bar_colors)
    ax2.set_title("Top 10 shock months by |monthly log return| (%)")
    ax2.set_xlabel("Monthly log return, %")
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _source_text(fig)
    return _save(fig, "03_volatility_shocks.png")


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


def chart_04_county_map(county: pd.DataFrame) -> Path:
    """Choropleth: 2012 growing-season % of county area in D2+ drought.

    Falls back to a labelled top-15 county bar chart if the GeoJSON is
    unavailable (plan §3.1).
    """
    geo = _load_geojson()
    # FIPS reads back from CSV as an int (19001); normalise to zero-padded
    # strings or the GeoJSON join matches nothing and the map is empty.
    county = county.copy()
    county["fips"] = county["fips"].astype(str).str.zfill(5)
    values = county.set_index("fips")["gs_d2plus_pct_2012"].to_dict()
    top3 = county.sort_values("gs_d2plus_pct_2012", ascending=False).head(3)
    if geo is None:
        return _chart_04_fallback(county)

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
        "Where the 2012 drought hit hardest: % of county area in severe+ (D2+) drought\n"
        "Growing season (Apr–Sep) 2012 — Iowa + Illinois (201 counties)"
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    # The three hardest-hit counties cluster in southern Illinois, so
    # their labels are spread with leader arrows instead of sitting on
    # the centroids (which overlapped each other and the colourbar).
    # Short labels keep them inside the axes.
    offsets = [(-135, 14), (-60, -32), (14, -32)]
    for (_, row), offset in zip(top3.iterrows(), offsets):
        fips = str(row["fips"]).zfill(5)
        if fips in centroids:
            lon, lat = centroids[fips]
            ax.annotate(
                f"{row['county'].replace(' County', '')} "
                f"{float(row['gs_d2plus_pct_2012']):.1f}%",
                xy=(lon, lat),
                xytext=offset,
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                arrowprops={"arrowstyle": "-", "color": "#333333", "lw": 0.8},
                bbox={"facecolor": "white", "alpha": 0.85, "pad": 2},
            )
    fig.colorbar(
        collection,
        ax=ax,
        shrink=0.8,
        label="% of county area in D2+ drought, growing season 2012",
    )
    _source_text(fig)
    return _save(fig, "04_county_map.png")


def _chart_04_fallback(county: pd.DataFrame) -> Path:
    """Labelled fallback: top-15 counties by 2012 D2+ % (plan §3.1)."""
    top15 = county.sort_values("gs_d2plus_pct_2012", ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        [f"{c}, {s}" for c, s in zip(top15["county"], top15["state"])],
        top15["gs_d2plus_pct_2012"],
        color="#b15928",
    )
    ax.invert_yaxis()
    ax.set_title(
        "Top 15 counties by % of area in severe+ (D2+) drought, growing season 2012\n"
        "(FALLBACK — county GeoJSON unavailable, so the map is a ranking)"
    )
    ax.set_xlabel("% of county area in D2+ drought, growing season 2012")
    ax.grid(axis="x", alpha=0.3)
    _source_text(fig)
    return _save(fig, "04_county_map.png")


def build_all() -> dict[str, Path]:
    """Build all four charts; return {name: path}."""
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_prices.csv", parse_dates=["date"])
    seasonality = pd.read_csv(PROCESSED_DIR / "seasonality.csv")
    shocks = pd.read_csv(PROCESSED_DIR / "shocks.csv", parse_dates=["date"])
    county = pd.read_csv(PROCESSED_DIR / "county_shock_2012.csv", dtype={"fips": str})
    return {
        "01_price_levels": chart_01_price_levels(monthly),
        "02_seasonality": chart_02_seasonality(seasonality),
        "03_volatility_shocks": chart_03_volatility_shocks(monthly, shocks),
        "04_county_map": chart_04_county_map(county),
    }


def main() -> None:
    paths = build_all()
    for name, path in paths.items():
        print(f"{name}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
