"""
Build map/output/gap_map_data.json: for every one of the 727 reliable tracts,
the same mean-monthly cost-component balance sheet data/build_dataset.py
computes county-wide (data/grid.json's "budget" block), computed per tract
instead -- so clicking a tract on gap_map.html answers "where does the gap
come from here," not just "how big is it here."

Same scope as data/build_dataset.py: households in the red only, means (not
medians) so the balance sheet adds up on screen, same seven cost components
in the same order. Tracts are the reliable 727 already selected in
data/tracts.csv (>=100 households); this script does not re-derive that cut.

Reads the boundary geometry map/src/build_boundaries.py produces
(map/data/tracts_06073.geojson, gitignored -- run that script first) and
simplifies/rounds it for embedding: county-level detail does not need
survey-grade vertices, and untouched TIGER geometry would make gap_map.html
several times larger than the data actually shown.

    python build_gap_map_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "data" / "raw" / "san_diego_ca_hlb_hackathon_2024.csv.gz"
TRACTS_CSV = HERE / ".." / "data" / "tracts.csv"
PUMA_NAMES_CSV = HERE / ".." / "data" / "puma_names.csv"
GEOJSON_PATH = HERE / "data" / "tracts_06073.geojson"
FEATURED_CSV = HERE / "output" / "featured_tracts_named.csv"
OUTPUT_PATH = HERE / "output" / "gap_map_data.json"

# Same order and column mapping as data/build_dataset.py's countywide budget
# block, so a tract's balance sheet and the county's are directly comparable.
COMPONENTS = [
    ("Housing", "housing_cost_month"),
    ("Transportation", "transp_cost_month"),
    ("Healthcare", "healthcare_cost_month"),
    ("Food", "food_cost_month"),
    ("Other essentials", "other_cost_month"),
    ("Childcare", "childcare_cost_month"),
    ("Broadband", "broadband_cost_month"),
]
COLS = ["geoid", "hh_income", "hlb_year", "hlb_taxes_year", "economically_vulnerable"] + [
    c for _, c in COMPONENTS
]

# A tract-level mean is one thing on 1,180 households and another on 12.
# Below this count, the balance sheet still displays but is flagged.
MIN_VULNERABLE_FOR_FULL_CONFIDENCE = 30

SIMPLIFY_TOLERANCE_DEG = 0.0001   # ~11m at this latitude; county-map scale, not parcel scale
COORD_DECIMALS = 5                # ~1.1m precision


def build_balance_sheet(vuln: pd.DataFrame) -> dict:
    comp_vals = [(n, round(float(vuln[c].mean()))) for n, c in COMPONENTS]
    cost_total = sum(v for _, v in comp_vals)
    tax_month = round(float(vuln.hlb_taxes_year.mean()) / 12)
    income_month = round(float(vuln.hh_income.mean()) / 12)
    required_month = cost_total + tax_month
    return {
        "n": int(len(vuln)),
        "incomeMonth": income_month,
        "costMonth": cost_total,
        "taxMonth": tax_month,
        "requiredMonth": required_month,
        "meanShortfallMonth": required_month - income_month,
        "medianShortfallMonth": round(float((vuln.hlb_year - vuln.hh_income).median()) / 12),
        "components": [{"name": n, "amount": v} for n, v in comp_vals],
    }


def load_county_balance_sheet(df: pd.DataFrame) -> dict:
    return build_balance_sheet(df[df.economically_vulnerable == 1])


def _cross_check_against_grid(county: dict) -> None:
    """This script's county-wide balance sheet, computed independently from
    the raw microdata, must match data/grid.json's own -- the same
    independent-code-paths bar wage_distance_analysis.py holds itself to."""
    grid_path = HERE / ".." / "data" / "grid.json"
    if not grid_path.exists():
        print(f"  (skipping cross-check: {grid_path} not found)")
        return
    grid_budget = json.loads(grid_path.read_text())["budget"]
    fields = ["incomeMonth", "costMonth", "taxMonth", "requiredMonth",
              "meanShortfallMonth", "medianShortfallMonth"]
    mismatches = [f for f in fields if county[f] != grid_budget[f]]
    if mismatches:
        sys.exit(f"error: county balance sheet disagrees with data/grid.json's budget "
                  f"on {mismatches} -- the two independent computations should match exactly")
    for c, g in zip(county["components"], grid_budget["components"]):
        if c["amount"] != g["amount"]:
            sys.exit(f"error: county component '{c['name']}' disagrees with data/grid.json's budget")
    print("  county balance sheet matches data/grid.json's budget exactly.")


def load_geometry(geoids: set[str]) -> dict[str, dict]:
    if not GEOJSON_PATH.exists():
        sys.exit(
            f"error: {GEOJSON_PATH} not found.\n"
            "       Build it first: python src/build_boundaries.py"
        )
    gdf = gpd.read_file(GEOJSON_PATH)
    gdf["geoid"] = gdf["geoid"].astype(str)
    gdf = gdf[gdf.geoid.isin(geoids)].copy()
    missing = geoids - set(gdf.geoid)
    if missing:
        sys.exit(f"error: {len(missing)} tract(s) in data/tracts.csv have no boundary geometry: "
                  f"{sorted(missing)[:5]}...")
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)

    def round_coords(obj):
        if isinstance(obj, list):
            if obj and isinstance(obj[0], (int, float)):
                return [round(x, COORD_DECIMALS) for x in obj]
            return [round_coords(o) for o in obj]
        return obj

    out = {}
    raw = json.loads(gdf[["geoid", "geometry"]].to_json())
    for feat in raw["features"]:
        geom = feat["geometry"]
        geom["coordinates"] = round_coords(geom["coordinates"])
        out[feat["properties"]["geoid"]] = geom
    return out


def main() -> None:
    if not TRACTS_CSV.exists():
        sys.exit(f"error: {TRACTS_CSV} not found. Build it first: cd ../data && python build_dataset.py")

    tracts = pd.read_csv(TRACTS_CSV, dtype={"geoid": str, "puma": str})
    puma_names = pd.read_csv(PUMA_NAMES_CSV, dtype={"puma": str}) if PUMA_NAMES_CSV.exists() else None
    featured = pd.read_csv(FEATURED_CSV, dtype={"geoid": str}) if FEATURED_CSV.exists() else None

    print(f"Loading household records from {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH, usecols=COLS, dtype={"geoid": str})
    print(f"Loaded {len(df):,} records.")

    county = load_county_balance_sheet(df)
    _cross_check_against_grid(county)
    geometry = load_geometry(set(tracts.geoid))

    puma_name_map = {}
    if puma_names is not None:
        puma_name_map = dict(zip(puma_names.puma, puma_names["puma_short"]))

    featured_map = {}
    if featured is not None:
        featured_map = {
            row.geoid: {"neighborhoodName": row.neighborhood_name, "category": row.category}
            for row in featured.itertuples()
        }

    by_tract = dict(tuple(df[df.economically_vulnerable == 1].groupby("geoid")))

    tract_features = []
    low_confidence_count = 0
    for row in tracts.itertuples():
        geoid = row.geoid
        vuln = by_tract.get(geoid)
        sheet = build_balance_sheet(vuln) if vuln is not None and len(vuln) else {
            "n": 0, "incomeMonth": None, "costMonth": None, "taxMonth": None,
            "requiredMonth": None, "meanShortfallMonth": None, "medianShortfallMonth": None,
            "components": [{"name": n, "amount": None} for n, _ in COMPONENTS],
        }
        low_confidence = sheet["n"] < MIN_VULNERABLE_FOR_FULL_CONFIDENCE
        low_confidence_count += low_confidence

        feat = featured_map.get(geoid, {})
        tract_features.append({
            "geoid": geoid,
            "puma": row.puma,
            "pumaName": puma_name_map.get(row.puma, row.puma),
            "neighborhoodName": feat.get("neighborhoodName"),
            "category": feat.get("category"),
            "households": int(row.households),
            "medianIncome": int(row.median_income) if pd.notna(row.median_income) else None,
            "vulnerableRate": round(float(row.vulnerable_rate), 4),
            "vulnerableHouseholds": int(row.vulnerable_households),
            "bahProfile": bool(row.bah_profile),
            "lowConfidence": low_confidence,
            "balanceSheet": sheet,
            "geometry": geometry[geoid],
        })

    out = {
        "note": "Mean monthly balance sheet among households below their budget, per tract. "
                "Same seven cost components and method as the county-wide figure, computed "
                "per tract instead. Never a claim about any one household -- every row is "
                f"synthetic. Tracts with fewer than {MIN_VULNERABLE_FOR_FULL_CONFIDENCE} "
                "households below budget are flagged lowConfidence.",
        "county": county,
        "minVulnerableForFullConfidence": MIN_VULNERABLE_FOR_FULL_CONFIDENCE,
        "tracts": tract_features,
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUTPUT_PATH} ({size_kb:.0f} KB, {len(tract_features)} tracts, "
          f"{low_confidence_count} flagged low-confidence)")


if __name__ == "__main__":
    main()
