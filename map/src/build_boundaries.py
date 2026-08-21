"""Filter the 2020 Census TIGER/Line CA tract shapefile down to San Diego
County (FIPS 06073) and write it out as GeoJSON for the map layer.

Usage:
    python src/build_boundaries.py
"""

import os

import geopandas as gpd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

SHAPEFILE_PATH = os.path.join(DATA_DIR, "tl_2020_06_tract", "tl_2020_06_tract.shp")
OUTPUT_PATH = os.path.join(DATA_DIR, "tracts_06073.geojson")

SAN_DIEGO_COUNTY_FIPS = "073"


def main():
    tracts = gpd.read_file(SHAPEFILE_PATH)

    sd_tracts = tracts[tracts["COUNTYFP"] == SAN_DIEGO_COUNTY_FIPS].copy()
    sd_tracts = sd_tracts.to_crs(epsg=4326)

    # Keep it lean: GEOID (join key) + geometry + a couple of readable fields.
    sd_tracts = sd_tracts[["GEOID", "NAME", "ALAND", "AWATER", "geometry"]]
    sd_tracts = sd_tracts.rename(columns={"GEOID": "geoid", "NAME": "tract_name"})

    sd_tracts.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"Wrote {len(sd_tracts)} San Diego County (FIPS 06073) tracts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
