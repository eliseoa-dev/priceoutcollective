"""Aggregation pipeline: canonical household rows -> per-geography affordability metrics.

Usage:
    python src/aggregate.py [config/sd_hlb_2024.yaml]

Rows in the source data are intentional population clones from weighted
resampling (many synthetic households can share identical values) —
never drop_duplicates() on this data.
"""

import os
import sys

import pandas as pd

from adapter import load_config, load_source, to_canonical
from schema import AGGREGATE_COLUMNS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "sd_hlb_2024.yaml")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "output", "geo_metrics.csv")


def aggregate(canonical_df):
    """Group canonical household rows by geo_id and compute affordability metrics."""
    gap = canonical_df["need_measure"] - canonical_df["income_measure"]
    coverage = canonical_df["income_measure"] / canonical_df["need_measure"]

    working = canonical_df.assign(_gap=gap, _coverage=coverage)

    grouped = working.groupby("geo_id", as_index=False).agg(
        geo_name=("geo_name", "first"),
        geo_type=("geo_type", "first"),
        sample_size=("geo_id", "size"),
        vulnerability_rate=("vulnerable_flag", lambda s: 100 * s.mean()),
        median_gap=("_gap", "median"),
        coverage_pct=("_coverage", lambda s: 100 * s.median()),
    )

    return grouped[AGGREGATE_COLUMNS]


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    config = load_config(config_path)

    # source_csv is resolved relative to the config file's own directory, so
    # a new dataset only ever needs a new config file, never a code change.
    csv_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(config_path)), config["source_csv"]))

    raw = load_source(csv_path, config)
    canonical = to_canonical(raw, config)

    metrics = aggregate(canonical)

    total_tracts = len(metrics)
    min_sample_size = config["min_sample_size"]
    filtered = metrics[metrics["sample_size"] < min_sample_size]
    kept = metrics[metrics["sample_size"] >= min_sample_size].copy()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    kept.to_csv(OUTPUT_PATH, index=False)

    print(f"Total tracts processed: {total_tracts}")
    print(f"Tracts filtered out for low sample size (< {min_sample_size}): {len(filtered)}")
    if len(filtered) > 0:
        print(filtered[["geo_id", "sample_size"]].sort_values("sample_size").to_string(index=False))

    print(f"\nWrote {len(kept)} tracts to {OUTPUT_PATH}\n")

    ranked = kept.sort_values("coverage_pct")
    print("5 lowest coverage_pct tracts:")
    print(ranked.head(5)[["geo_id", "sample_size", "coverage_pct", "vulnerability_rate", "median_gap"]].to_string(index=False))

    print("\n5 highest coverage_pct tracts:")
    print(ranked.tail(5)[["geo_id", "sample_size", "coverage_pct", "vulnerability_rate", "median_gap"]].to_string(index=False))


if __name__ == "__main__":
    main()
