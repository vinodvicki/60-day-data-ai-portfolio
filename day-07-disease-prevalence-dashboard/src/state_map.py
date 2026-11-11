"""State choropleth map rendered with matplotlib (no network).

Why matplotlib and not Plotly geo: plotly.js fetches a topojson base map
from https://cdn.plot.ly for ANY geo subplot — with scope='usa' it wants
usa_110m.json, without a scope it wants world_110m.json — and that fetch
fails in this environment (403 / tunnel failure, verified 2026-11-11 via
CDP: the geo subplot throws and draws 0 paths even with an explicit
bundled geojson and all base layers disabled). A matplotlib map drawn
from the bundled data/processed/us_states.geojson renders offline,
deterministically, and is verified by the smoke-test screenshot.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

NO_DATA_COLOR = "#e5e5e5"


def _polygons(geometry: dict) -> list[list[tuple[float, float]]]:
    """GeoJSON Polygon/MultiPolygon coordinates -> list of rings."""
    rings: list[list[tuple[float, float]]] = []
    if geometry["type"] == "Polygon":
        rings = [list(map(tuple, ring)) for ring in geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            rings.extend(list(map(tuple, ring)) for ring in poly)
    return rings


def state_map_figure(state_year, geojson: dict, title: str):
    """Build the state choropleth figure for one measure-year.

    `state_year` is the state_prevalence slice (columns stateabbr,
    state_rate). States with no row (Kentucky/Pennsylvania in 2023) are
    drawn grey. Returns a matplotlib Figure (caller closes it).
    """
    rates = dict(zip(state_year["stateabbr"], state_year["state_rate"]))
    vmin = min(rates.values())
    vmax = max(rates.values())
    cmap = plt.get_cmap("Blues")
    norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    patches: list[Polygon] = []
    colors: list = []
    for feature in geojson["features"]:
        abbr = feature["properties"]["abbr"]
        for ring in _polygons(feature["geometry"]):
            patches.append(Polygon(ring, closed=True))
            if abbr in rates:
                colors.append(cmap(norm(rates[abbr])))
            else:
                colors.append(NO_DATA_COLOR)
    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.add_collection(
        PatchCollection(patches, facecolor=colors, edgecolor="white", linewidth=0.5)
    )
    ax.set_xlim(-172, -66)
    ax.set_ylim(18, 72)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Estimated prevalence, % of adults 18+")
    missing = sorted(
        {f["properties"]["abbr"] for f in geojson["features"]} - set(rates)
    )
    if missing:
        ax.text(
            0.01,
            0.01,
            f"Grey = no data in this release: {', '.join(missing)}",
            transform=ax.transAxes,
            fontsize=10,
            color="#5d6d7e",
        )
    fig.tight_layout()
    return fig
