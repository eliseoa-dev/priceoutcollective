"""Config-driven adapter: reads a dataset config and renames a source
dataset's raw columns onto the canonical schema defined in schema.py.

To support a new dataset, write a new config/*.yaml file — no code here
should need to change.
"""

import pandas as pd
import yaml

from schema import CANONICAL_ROW_COLUMNS


def load_config(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    required = ["source_csv", "geo_key", "geo_type", "income_col", "need_col", "vulnerable_col", "min_sample_size"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"{config_path} is missing required keys: {missing}")

    return config


def load_source(csv_path, config):
    """Load only the columns the config declares, to bound memory on large files."""
    usecols = config.get("usecols")
    return pd.read_csv(csv_path, usecols=usecols, dtype={config["geo_key"]: str})


def to_canonical(df, config):
    """Rename raw source columns into the canonical row-level schema."""
    rename_map = {
        config["geo_key"]: "geo_id",
        config["income_col"]: "income_measure",
        config["need_col"]: "need_measure",
        config["vulnerable_col"]: "vulnerable_flag",
    }
    canonical = df.rename(columns=rename_map)

    # This dataset has no separate geography-name column; fall back to geo_id.
    if "geo_name" not in canonical.columns:
        canonical["geo_name"] = canonical["geo_id"]
    canonical["geo_type"] = config["geo_type"]

    return canonical[CANONICAL_ROW_COLUMNS]
