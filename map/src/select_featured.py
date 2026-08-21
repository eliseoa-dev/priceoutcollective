"""Select a small set of "featured" tracts from output/geo_metrics.csv for map
annotation, and attach official place names.

  - most_affected : highest NUMBER of households below their budget
  - at_the_line   : tracts closest to the county-wide rate
  - least_affected: lowest share below their budget

Selection is by the number of households affected, not the share. Ranking on
share alone put tracts holding 2.9% of the county's affected households at the
top of the map, and the top ten by share are not statistically separable — the
donor-adjusted interval is +/-3.1 points and sixty tracts overlap the tenth.

Tracts flagged `bah_profile` in data/tracts.csv are excluded from the featured
set and kept in every total. They are the only two of 727 where most households
hold children under 12, with uniformly maxed bedroom counts and low recorded
income: the signature of military family housing, where the housing allowance is
excluded from recorded income while the model still charges full market rent.

Place names come from the official 2020 Census PUMA names in data/puma_names.csv
(TIGER/Line 2023, NAMELSAD20). Nothing here is hand-written.

Usage:
    python src/select_featured.py
"""

import os

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
METRICS_PATH = os.path.join(PROJECT_ROOT, "output", "geo_metrics.csv")
TRACTS_PATH = os.path.join(REPO_ROOT, "data", "tracts.csv")
PUMA_NAMES_PATH = os.path.join(REPO_ROOT, "data", "puma_names.csv")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output", "featured_tracts_named.csv")

N_MOST_AFFECTED = 3
N_AT_THE_LINE = 3
N_LEAST_AFFECTED = 2


def main():
    metrics = pd.read_csv(METRICS_PATH, dtype={"geo_id": str})
    tracts = pd.read_csv(TRACTS_PATH, dtype={"geoid": str, "puma": str})
    pumas = pd.read_csv(PUMA_NAMES_PATH, dtype=str)

    df = metrics.merge(
        tracts[["geoid", "puma", "households", "vulnerable_households",
                "median_shortfall_month", "bah_profile"]],
        left_on="geo_id", right_on="geoid", how="inner",
    ).merge(pumas[["puma", "puma_label"]], on="puma", how="left")

    if df.puma_label.isna().any():
        raise SystemExit("error: a featured tract has no official PUMA name")

    county_rate = 100 * df.vulnerable_households.sum() / df.households.sum()
    eligible = df[~df.bah_profile].copy()

    most = eligible.nlargest(N_MOST_AFFECTED, "vulnerable_households").assign(
        category="most_affected")

    rest = eligible[~eligible.geo_id.isin(most.geo_id)].copy()
    rest["_dist"] = (rest.vulnerability_rate - county_rate).abs()
    line = rest.nsmallest(N_AT_THE_LINE, "_dist").drop(columns="_dist").assign(
        category="at_the_line")

    least = eligible.nsmallest(N_LEAST_AFFECTED, "vulnerability_rate").assign(
        category="least_affected")

    featured = pd.concat([most, line, least], ignore_index=True)
    featured = featured.drop_duplicates(subset="geo_id", keep="first")
    featured = featured.rename(columns={"puma_label": "neighborhood_name"})
    featured.to_csv(OUTPUT_PATH, index=False)

    print(f"County-wide rate: {county_rate:.1f}%")
    print(f"Excluded {int(df.bah_profile.sum())} BAH-profile tract(s) from the featured set.")
    print(f"Wrote {len(featured)} featured tracts to {OUTPUT_PATH}")
    print(featured[["geo_id", "neighborhood_name", "category", "vulnerability_rate",
                    "vulnerable_households", "households"]].to_string(index=False))


if __name__ == "__main__":
    main()
