"""Select a small set of "featured" tracts from output/geo_metrics.csv for
map annotation:
  - priced_out       : 2-3 lowest coverage_pct
  - on_edge           : 2-3 tracts with coverage_pct < 100, closest to 100
  - stable_baseline  : 1-2 highest coverage_pct

Usage:
    python src/select_featured.py
"""

import os

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(PROJECT_ROOT, "output", "geo_metrics.csv")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output", "featured_tracts.csv")

N_PRICED_OUT = 3
N_ON_EDGE = 3
N_STABLE_BASELINE = 2


def main():
    metrics = pd.read_csv(METRICS_PATH, dtype={"geo_id": str})

    priced_out = metrics.nsmallest(N_PRICED_OUT, "coverage_pct").assign(category="priced_out")

    below_100 = metrics[metrics["coverage_pct"] < 100].copy()
    below_100["_dist_to_100"] = 100 - below_100["coverage_pct"]
    on_edge = below_100.nsmallest(N_ON_EDGE, "_dist_to_100").drop(columns="_dist_to_100").assign(category="on_edge")

    stable_baseline = metrics.nlargest(N_STABLE_BASELINE, "coverage_pct").assign(category="stable_baseline")

    featured = pd.concat([priced_out, on_edge, stable_baseline], ignore_index=True)
    featured = featured.drop_duplicates(subset="geo_id", keep="first")

    featured.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(featured)} featured tracts to {OUTPUT_PATH}")
    print(featured[["geo_id", "category", "coverage_pct", "vulnerability_rate", "median_gap", "sample_size"]].to_string(index=False))


if __name__ == "__main__":
    main()
