"""Fetch the 2020 Census TIGER/Line CA tract shapefile, filter it down to San
Diego County (FIPS 06073), and write it out as GeoJSON for the map layer.

The shapefile is ~80 MB and is not committed (see .gitignore), so this downloads
it on first run. It previously assumed the file was already unpacked on disk,
which meant the documented build failed on a clean clone.

Usage:
    python src/build_boundaries.py
"""

import io
import os
import urllib.request
import zipfile

import geopandas as gpd

TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

SHAPEFILE_PATH = os.path.join(DATA_DIR, "tl_2020_06_tract", "tl_2020_06_tract.shp")
OUTPUT_PATH = os.path.join(DATA_DIR, "tracts_06073.geojson")

SAN_DIEGO_COUNTY_FIPS = "073"


def fetch_shapefile():
    if os.path.exists(SHAPEFILE_PATH):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Shapefile not found. Downloading from {TIGER_URL} (~80 MB) ...")
    with urllib.request.urlopen(TIGER_URL) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        z.extractall(os.path.join(DATA_DIR, "tl_2020_06_tract"))
    print(f"  unpacked to {os.path.dirname(SHAPEFILE_PATH)}")


def main():
    fetch_shapefile()
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
