"""Canonical schema shared by every dataset adapter in this pipeline.

Downstream aggregation code must only ever reference these column names —
never a raw source dataset's own column names.
"""

# Row-level canonical columns produced by an adapter.
# (sample_size is a derived aggregate, not a per-row field, so it is not
# populated until aggregation groups rows by geo_id.)
CANONICAL_ROW_COLUMNS = [
    "geo_id",
    "geo_name",
    "geo_type",
    "income_measure",
    "need_measure",
    "vulnerable_flag",
]

# Columns produced by the aggregation step, one row per geo_id.
AGGREGATE_COLUMNS = [
    "geo_id",
    "geo_name",
    "geo_type",
    "sample_size",
    "vulnerability_rate",
    "median_gap",
    "coverage_pct",
]
