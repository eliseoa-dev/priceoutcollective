"""Build the standalone San Diego affordability choropleth map.

- Base choropleth of all tracts, colored by coverage_pct (red=low, green=high)
- Bold outline overlay on featured tracts
- DivIcon text labels on featured tracts (neighborhood name + coverage %)
- Tooltips on featured tracts with vulnerability_rate, median_gap, coverage_pct
- Title + legend
- Exported as a standalone HTML file (no server required)

Usage:
    python src/build_map.py
"""

import json
import math
import os

import branca.colormap as cm
import folium
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

GEOJSON_PATH = os.path.join(DATA_DIR, "tracts_06073.geojson")
METRICS_PATH = os.path.join(OUTPUT_DIR, "geo_metrics.csv")
# featured_tracts_named.csv = select_featured.py's featured_tracts.csv, with a
# neighborhood_name column added via a one-off SANDAG/TIGER boundary lookup.
# Regenerate names manually after any change to the featured-tract selection.
FEATURED_PATH = os.path.join(OUTPUT_DIR, "featured_tracts_named.csv")
MAP_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "sd_affordability_map.html")

# Fallback center/zoom used only before fit_bounds() takes over in main().
SAN_DIEGO_CENTER = [32.85, -117.15]

# Featured-tract centroids closer together than this (in degrees, ~ok as a
# flat-earth approximation over a metro-scale area) get their labels pushed
# apart with leader lines instead of stacked on top of each other.
LABEL_CLUSTER_THRESHOLD_DEG = 0.025
LABEL_OFFSET_DEG = 0.035

CATEGORY_LABELS = {
    "priced_out": "Already priced out",
    "on_edge": "On the edge (near 100% coverage)",
    "stable_baseline": "Stable baseline",
}
CATEGORY_COLORS = {
    "priced_out": "#8B0000",
    "on_edge": "#B8860B",
    "stable_baseline": "#00441b",
}


def load_data():
    with open(GEOJSON_PATH) as f:
        geojson = json.load(f)

    metrics = pd.read_csv(METRICS_PATH, dtype={"geo_id": str})
    featured = pd.read_csv(FEATURED_PATH, dtype={"geo_id": str})

    return geojson, metrics, featured


def build_choropleth(m, geojson, metrics):
    metrics_indexed = metrics.set_index("geo_id")
    coverage_by_geoid = metrics_indexed["coverage_pct"].to_dict()

    # Clip the color scale so a handful of extreme outliers don't wash out
    # the mid-range contrast that matters most for reading the map.
    vmin, vmax = 40, 160
    colormap = cm.LinearColormap(
        colors=["#a50026", "#f46d43", "#fee08b", "#a6d96a", "#1a9850"],
        vmin=vmin,
        vmax=vmax,
        caption="Income coverage of the Household Living Budget (%)",
    )

    def style_function(feature):
        geoid = feature["properties"]["geoid"]
        coverage = coverage_by_geoid.get(geoid)
        if coverage is None:
            return {"fillColor": "#cccccc", "color": "#999999", "weight": 0.3, "fillOpacity": 0.4}
        return {
            "fillColor": colormap(max(vmin, min(vmax, coverage))),
            "color": "#666666",
            "weight": 0.3,
            "fillOpacity": 0.75,
        }

    # Attach coverage/vulnerability/gap onto each feature's properties so
    # the base-layer tooltip can show them for every tract, not just featured ones.
    for feature in geojson["features"]:
        geoid = feature["properties"]["geoid"]
        row = metrics_indexed.loc[geoid] if geoid in metrics_indexed.index else None
        feature["properties"]["coverage_pct"] = round(float(row["coverage_pct"]), 1) if row is not None else None
        feature["properties"]["vulnerability_rate"] = round(float(row["vulnerability_rate"]), 1) if row is not None else None

    folium.GeoJson(
        geojson,
        name="Coverage by tract",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["geoid", "tract_name", "coverage_pct", "vulnerability_rate"],
            aliases=["Tract GEOID:", "Tract name:", "Coverage %:", "Vulnerability rate %:"],
            sticky=True,
        ),
    ).add_to(m)

    colormap.add_to(m)
    return colormap


def build_featured_overlay(m, geojson, featured):
    featured_ids = set(featured["geo_id"])
    featured_lookup = featured.set_index("geo_id")

    featured_features = [f for f in geojson["features"] if f["properties"]["geoid"] in featured_ids]
    featured_geojson = {"type": "FeatureCollection", "features": featured_features}

    def style_function(feature):
        geoid = feature["properties"]["geoid"]
        category = featured_lookup.loc[geoid, "category"]
        return {
            "fillOpacity": 0,
            "color": CATEGORY_COLORS.get(category, "#000000"),
            "weight": 4,
        }

    def tooltip_fields_row(geoid):
        row = featured_lookup.loc[geoid]
        return row

    # Build tooltip text per-feature since content differs (category-specific).
    for feature in featured_geojson["features"]:
        geoid = feature["properties"]["geoid"]
        row = featured_lookup.loc[geoid]
        feature["properties"]["category_label"] = CATEGORY_LABELS.get(row["category"], row["category"])
        feature["properties"]["neighborhood_name"] = row.get("neighborhood_name", "")
        feature["properties"]["vulnerability_rate_fmt"] = f"{row['vulnerability_rate']:.1f}%"
        feature["properties"]["median_gap_fmt"] = f"${row['median_gap']:,.0f}"
        feature["properties"]["coverage_pct_fmt"] = f"{row['coverage_pct']:.1f}%"

    folium.GeoJson(
        featured_geojson,
        name="Featured tracts (outline)",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["geoid", "neighborhood_name", "tract_name", "category_label", "coverage_pct_fmt", "vulnerability_rate_fmt", "median_gap_fmt"],
            aliases=["Tract GEOID:", "Neighborhood:", "Tract name:", "Category:", "Coverage:", "Vulnerability rate:", "Median gap:"],
            sticky=True,
        ),
    ).add_to(m)

    return featured_geojson


def _cluster_by_proximity(points, threshold_deg):
    """Group point indices into clusters via single-link distance (union-find).
    Any two points within threshold_deg of each other end up in the same
    cluster, even if that chains through an intermediate point."""
    n = len(points)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj

    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            dist = ((lon1 - lon2) ** 2 + (lat1 - lat2) ** 2) ** 0.5
            if dist <= threshold_deg:
                union(i, j)

    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    return list(clusters.values())


def add_featured_labels(m, featured_geojson):
    label_layer = folium.FeatureGroup(name="Featured tract labels")

    features = featured_geojson["features"]
    centroids = [_polygon_centroid(f["geometry"]) for f in features]

    valid_idx = [i for i, c in enumerate(centroids) if c is not None]
    clusters = _cluster_by_proximity([centroids[i] for i in valid_idx], LABEL_CLUSTER_THRESHOLD_DEG)

    for cluster in clusters:
        member_idx = [valid_idx[i] for i in cluster]
        is_crowded = len(member_idx) > 1

        for slot, idx in enumerate(member_idx):
            feature = features[idx]
            props = feature["properties"]
            geoid = props["geoid"]
            coverage_fmt = props["coverage_pct_fmt"]
            label_name = props.get("neighborhood_name") or geoid[-4:]
            category = props.get("category_label", "")
            color = CATEGORY_COLORS.get(
                next((k for k, v in CATEGORY_LABELS.items() if v == category), None), "#000000"
            )

            lon, lat = centroids[idx]

            if is_crowded:
                # Spread crowded labels around the cluster on a small circle,
                # and draw a leader line back to the tract's true centroid so
                # it's unambiguous which label belongs to which tract.
                angle = math.pi / 2 + (2 * math.pi * slot / len(member_idx))
                label_lat = lat + LABEL_OFFSET_DEG * math.sin(angle)
                label_lon = lon + LABEL_OFFSET_DEG * math.cos(angle) / math.cos(math.radians(lat))

                folium.PolyLine(
                    locations=[[lat, lon], [label_lat, label_lon]],
                    color=color,
                    weight=1.5,
                    opacity=0.8,
                    dash_array="2,4",
                ).add_to(label_layer)
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=1,
                ).add_to(label_layer)
            else:
                label_lat, label_lon = lat, lon

            label_html = (
                f'<div style="font-size:11px;font-weight:700;color:{color};'
                f'background:rgba(255,255,255,0.9);padding:2px 5px;border-radius:3px;'
                f'border:1px solid {color};white-space:nowrap;transform:translate(-50%,-50%);">'
                f'{label_name} &middot; {coverage_fmt}</div>'
            )
            folium.Marker(
                location=[label_lat, label_lon],
                icon=folium.DivIcon(html=label_html),
            ).add_to(label_layer)

    label_layer.add_to(m)


def _polygon_centroid(geometry):
    """Rough centroid via bounding-box midpoint of the largest polygon ring —
    avoids pulling in shapely just for label placement."""
    if geometry["type"] == "Polygon":
        rings = [geometry["coordinates"][0]]
    elif geometry["type"] == "MultiPolygon":
        rings = [poly[0] for poly in geometry["coordinates"]]
    else:
        return None

    largest_ring = max(rings, key=len)
    lons = [c[0] for c in largest_ring]
    lats = [c[1] for c in largest_ring]
    return (sum(lons) / len(lons), sum(lats) / len(lats))


def _compute_padded_bounds(features, pad_deg=0.025):
    """[[south, west], [north, east]] bounding box over a set of GeoJSON
    features, padded outward so tracts aren't flush against the map edge."""
    lons, lats = [], []
    for feature in features:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            rings = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            rings = [ring for poly in geom["coordinates"] for ring in poly]
        else:
            continue
        for ring in rings:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)

    south, north = min(lats) - pad_deg, max(lats) + pad_deg
    west, east = min(lons) - pad_deg, max(lons) + pad_deg
    return [[south, west], [north, east]]


def add_title(m):
    title_html = """
    <div style="position: fixed; top: 12px; left: 60px; z-index: 9999;
                background: rgba(255,255,255,0.92); padding: 10px 16px;
                border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3);
                font-family: sans-serif;">
      <div style="font-size:18px; font-weight:700; color:#222;">
        San Diego County Affordability Map — 2024
      </div>
      <div style="font-size:12px; color:#555; margin-top:2px;">
        Household income as a percent of the Household Living Budget (HLB), by census tract &middot; PriceOut Collective
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))


def add_category_legend(m):
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 12px; z-index: 9999;
                background: rgba(255,255,255,0.92); padding: 10px 14px;
                border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3);
                font-family: sans-serif; font-size:12px; color:#222;">
      <div style="font-weight:700; margin-bottom:6px;">Featured tracts</div>
      <div style="margin-bottom:3px;">
        <span style="display:inline-block;width:14px;height:0;border-top:4px solid #8B0000;margin-right:6px;"></span>
        Already priced out
      </div>
      <div style="margin-bottom:3px;">
        <span style="display:inline-block;width:14px;height:0;border-top:4px solid #B8860B;margin-right:6px;"></span>
        On the edge (near 100% coverage)
      </div>
      <div>
        <span style="display:inline-block;width:14px;height:0;border-top:4px solid #00441b;margin-right:6px;"></span>
        Stable baseline
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


def main():
    geojson, metrics, featured = load_data()

    m = folium.Map(location=SAN_DIEGO_CENTER, zoom_start=10, tiles="cartodbpositron")

    build_choropleth(m, geojson, metrics)
    featured_geojson = build_featured_overlay(m, geojson, featured)
    add_featured_labels(m, featured_geojson)

    # Frame the initial view on the populated area where the featured tracts
    # sit, rather than a fixed center/zoom that can land in the empty
    # backcountry/border region of the county.
    bounds = _compute_padded_bounds(featured_geojson["features"])
    # Reserve screen space at the top for the fixed title banner (~90px tall)
    # so the fit doesn't push a featured tract's label directly under it.
    m.fit_bounds(bounds, padding_top_left=[0, 90])

    add_title(m)
    add_category_legend(m)
    folium.LayerControl(collapsed=False).add_to(m)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    m.save(MAP_OUTPUT_PATH)
    print(f"Wrote standalone map to {MAP_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
