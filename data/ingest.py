"""
Import a source dataset into the project's shared schema (data/zips.csv).

The organizers' Affordability dataset lives in a Google Drive folder. Drop the
file(s) into data/raw/ and run this — it maps whatever column names the source
uses onto ours, derives the fields we need, and writes data/zips.csv.

    python ingest.py --inspect data/raw/whatever.csv   # show me its columns
    python ingest.py data/raw/whatever.csv             # import it
    python ingest.py data/raw/whatever.csv --zip-col ZCTA --income-col HHI

Supported inputs: .csv, .tsv, .xlsx.

Why this exists: everything downstream (the map, the policy calculator) reads
data/zips.csv and nothing else. Keeping the raw file in data/raw/ and the
conversion in one script means we can re-run the import when the source is
updated, and anyone can see exactly how a source column became one of ours.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT_PATH = HERE / "zips.csv"
RAW_DIR = HERE / "raw"

CRISIS = 0.50          # runway target: rent burden crosses half of income
DEFAULT_RENT_GROWTH = 0.055
DEFAULT_INCOME_GROWTH = 0.030

# Candidate source column names, in priority order, for each of our fields.
# Matching is case-insensitive and ignores spaces/underscores, so "Median Rent",
# "median_rent" and "MEDIANRENT" all hit the same entry.
ALIASES = {
    "zip": ["zip", "zipcode", "zcta", "zcta5", "postalcode", "geoid", "zip_code"],
    "area": ["area", "areaname", "neighborhood", "neighborhoodname", "neighbourhood",
             "community", "communityname", "place", "placename", "label", "name"],
    "median_income": ["medianincome", "median_household_income", "medianhouseholdincome",
                      "hhincome", "income", "medhhinc", "medianhhincome"],
    "median_rent": ["medianrent", "median_gross_rent", "mediangrossrent", "grossrent",
                    "rent", "medgrossrent", "medianmonthlyrent"],
    "rent_burden_pct": ["rentburdenpct", "rentburden", "burden", "rent_burden",
                        "costburden", "grossrentpctincome"],
    "rent_growth_rate": ["rentgrowthrate", "rentgrowth", "rentcagr", "rent_yoy", "rentyoy"],
    "income_growth_rate": ["incomegrowthrate", "incomegrowth", "incomecagr",
                           "income_yoy", "incomeyoy", "wagegrowth"],
    "featured": ["featured", "highlight", "flagged", "atrisk", "is_featured"],
}

TRUTHY = {"true", "1", "yes", "y", "t"}


def norm(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


TABULAR_SUFFIXES = (".csv", ".tsv", ".xlsx", ".xlsm")


def load_one(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return pd.read_excel(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path)


def zip_column_of(df: pd.DataFrame) -> str | None:
    lookup = {norm(c): c for c in df.columns}
    for alias in ALIASES["zip"]:
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None


def load_any(path: Path) -> pd.DataFrame:
    """Load one file, or merge every tabular file in a directory on its ZIP column.

    The organizers ship the dataset as several files (one per metric or per
    source table). Pointing this at data/raw/ joins them into one frame so the
    rest of the import doesn't care how many files there were.
    """
    if not path.exists():
        sys.exit(
            f"error: {path} not found.\n"
            f"       Put the source file(s) in {RAW_DIR}/ first — see data/raw/README.md."
        )

    if path.is_file():
        return load_one(path)

    files = sorted(p for p in path.iterdir() if p.suffix.lower() in TABULAR_SUFFIXES)
    if not files:
        sys.exit(
            f"error: no .csv/.tsv/.xlsx files in {path}/.\n"
            f"       Download the dataset into that folder — see data/raw/README.md."
        )

    merged: pd.DataFrame | None = None
    for f in files:
        part = load_one(f)
        zcol = zip_column_of(part)
        if zcol is None:
            print(f"warning: {f.name} has no recognizable ZIP column — skipping it.")
            print(f"         Columns: {', '.join(map(str, part.columns))}")
            continue

        # Normalize the join key so 92113, '92113' and '92113-1234' all match.
        part = part.copy()
        part["_zip"] = part[zcol].astype(str).str.extract(r"(\d{5})", expand=False)
        part = part.dropna(subset=["_zip"]).drop_duplicates(subset="_zip", keep="first")
        part = part.drop(columns=[zcol])

        print(f"  read {f.name:<40} {len(part):>5} rows, {len(part.columns) - 1} columns")

        if merged is None:
            merged = part
        else:
            overlap = (set(part.columns) & set(merged.columns)) - {"_zip"}
            if overlap:
                # Keep the first file's version; suffix the newcomer so nothing
                # is silently overwritten and you can see the collision.
                part = part.rename(columns={c: f"{c}__{f.stem}" for c in overlap})
            merged = merged.merge(part, on="_zip", how="outer")

    if merged is None:
        sys.exit("error: none of the files had a usable ZIP column.")

    merged = merged.rename(columns={"_zip": "zip"})
    print(f"  merged {len(files)} file(s) -> {len(merged)} ZIPs, {len(merged.columns)} columns\n")
    return merged


def find_column(df: pd.DataFrame, field: str, override: str | None) -> str | None:
    if override:
        if override not in df.columns:
            sys.exit(f"error: --{field.replace('_', '-')} column {override!r} is not in the file.\n"
                     f"       Columns present: {', '.join(map(str, df.columns))}")
        return override

    lookup = {norm(c): c for c in df.columns}
    for alias in ALIASES.get(field, []):
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None


def as_number(series: pd.Series) -> pd.Series:
    """Strip $ , % and whitespace, then coerce to float."""
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def as_rate(series: pd.Series) -> pd.Series:
    """Accept either 0.055 or 5.5 and return a fraction."""
    values = as_number(series)
    # If the column looks like whole percents (median well above 1), scale it down.
    if values.dropna().abs().median() > 1:
        values = values / 100.0
    return values


def runway_months(burden: float, rent_g: float, income_g: float) -> float:
    if not all(map(lambda v: isinstance(v, float) and not math.isnan(v),
                   [burden, rent_g, income_g])):
        return float("nan")
    if burden >= CRISIS:
        return 0.0
    ratio = (1 + rent_g) / (1 + income_g)
    if ratio <= 1:
        return float("inf")
    return 12 * math.log(CRISIS / burden) / math.log(ratio)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, nargs="?", default=RAW_DIR,
                   help="source file, or a directory whose tabular files are merged "
                        f"on their ZIP column (default: {RAW_DIR.name}/)")
    p.add_argument("--inspect", action="store_true",
                   help="print the source's columns and a preview, then exit")
    for field in ALIASES:
        p.add_argument(f"--{field.replace('_', '-')}-col", dest=f"{field}_col", default=None,
                       help=f"source column to use for {field}")
    p.add_argument("--feature-top", type=int, default=8,
                   help="if the source has no 'featured' column, flag the N ZIPs "
                        "with the least runway (default 8)")
    args = p.parse_args()

    df = load_any(args.source)

    if args.inspect:
        print(f"{args.source}  —  {len(df)} rows, {len(df.columns)} columns\n")
        for c in df.columns:
            guess = next((f for f in ALIASES if norm(c) in {norm(a) for a in ALIASES[f]}), None)
            tag = f"  -> maps to {guess}" if guess else "  -> (unmapped)"
            print(f"  {str(c):<34}{tag}")
        print("\nFirst rows:")
        print(df.head(5).to_string(index=False))
        print("\nFor anything unmapped, pass e.g. --income-col 'Your Column Name'")
        return

    resolved = {f: find_column(df, f, getattr(args, f"{f}_col")) for f in ALIASES}

    missing = [f for f in ("zip", "median_income", "median_rent") if not resolved[f]]
    if missing:
        sys.exit(
            "error: could not find required column(s): " + ", ".join(missing) + "\n"
            "       Columns present: " + ", ".join(map(str, df.columns)) + "\n"
            "       Map them explicitly, e.g. --income-col 'Median HH Income',\n"
            "       or run with --inspect to see what's there."
        )

    out = pd.DataFrame()
    out["zip"] = df[resolved["zip"]].astype(str).str.extract(r"(\d{5})", expand=False)
    out["area"] = df[resolved["area"]].astype(str).str.strip() if resolved["area"] else out["zip"]
    out["median_income"] = as_number(df[resolved["median_income"]])
    out["median_rent"] = as_number(df[resolved["median_rent"]])

    if resolved["rent_burden_pct"]:
        out["rent_burden_pct"] = as_rate(df[resolved["rent_burden_pct"]])
    else:
        out["rent_burden_pct"] = (out["median_rent"] * 12) / out["median_income"]
        print("note: no rent-burden column found — derived it as (rent x 12) / income")

    for field, default in (("rent_growth_rate", DEFAULT_RENT_GROWTH),
                           ("income_growth_rate", DEFAULT_INCOME_GROWTH)):
        if resolved[field]:
            out[field] = as_rate(df[resolved[field]])
        else:
            out[field] = default
            print(f"warning: no {field} in the source — filled with {default:.1%} for every ZIP.")
            print(f"         Every runway figure depends on this. Replace it before presenting.")

    before = len(out)
    out = out.dropna(subset=["zip", "median_income", "median_rent"])
    out = out[(out["median_income"] > 0) & (out["median_rent"] > 0)]
    if len(out) < before:
        print(f"note: dropped {before - len(out)} row(s) with a missing/zero zip, income or rent")

    out = out.drop_duplicates(subset="zip", keep="first").reset_index(drop=True)

    out["runway_months"] = [
        runway_months(b, r, i)
        for b, r, i in zip(out["rent_burden_pct"], out["rent_growth_rate"], out["income_growth_rate"])
    ]

    if resolved["featured"]:
        out["featured"] = df[resolved["featured"]].astype(str).str.lower().isin(TRUTHY)
    else:
        cutoff = out["runway_months"].replace([float("inf")], 1e9).nsmallest(args.feature_top)
        threshold = cutoff.max() if len(cutoff) else 0
        out["featured"] = out["runway_months"].replace([float("inf")], 1e9) <= threshold
        print(f"note: no 'featured' column — flagged the {args.feature_top} ZIPs with least runway")

    out = out.sort_values("runway_months").reset_index(drop=True)
    out["rent_burden_pct"] = out["rent_burden_pct"].round(4)
    out["rent_growth_rate"] = out["rent_growth_rate"].round(4)
    out["income_growth_rate"] = out["income_growth_rate"].round(4)
    out["runway_months"] = out["runway_months"].round(1)
    out["median_income"] = out["median_income"].round(0).astype("Int64")
    out["median_rent"] = out["median_rent"].round(0).astype("Int64")

    out.to_csv(OUT_PATH, index=False)

    print(f"\nWrote {OUT_PATH}  —  {len(out)} ZIPs, {int(out['featured'].sum())} featured")
    print(f"  already past 50% burden: {int((out['runway_months'] == 0).sum())}")
    print(f"  under 24 months runway:  {int((out['runway_months'] < 24).sum())}")
    print("\nNext:  cd ../policy_calculator && python sync_data.py --real")


if __name__ == "__main__":
    main()
