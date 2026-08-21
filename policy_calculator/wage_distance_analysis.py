"""
Wage Distance Analysis
How large a raise would it take to close each household's own gap?

The published grid (data/grid.json) evaluates a uniform wage lever at nine
discrete steps (0-50%) and reports the countywide rate that remains
vulnerable. That answers "did this policy work" for one stated policy. It
cannot answer the personal question: for a household already below its
budget, how big a raise -- applied to that household alone, nothing else
changing -- would put it exactly at the line?

That number falls straight out of the organizers' own formula. Holding the
budget side fixed (no rent cap, no childcare subsidy: exactly what the wage
lever alone does in data/build_dataset.py's Model.hit), a household needs

    wage_lift_pct_needed = (hlb_year / hh_income - 1) * 100

percent more income to clear its own line. This script computes it exactly
for every one of the 520,257 households below their budget, then reports the
distribution -- not any individual value, consistent with the claims ledger's
ban on statements about individual (synthetic) households.

It also cross-checks itself against data/grid.json: summing, for each of the
grid's own wage steps, how many currently-vulnerable households have
wage_lift_pct_needed <= that step reproduces the grid's own shipped household
counts (cap=0, care=0, elig=0) to within its documented 5-household
cent-rounding tolerance. Two independent code paths agreeing is the
project's standing bar for a number that ships.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "data" / "raw" / "san_diego_ca_hlb_hackathon_2024.csv.gz"
GRID_PATH = HERE / ".." / "data" / "grid.json"
# Committed alongside grid.json, not written to outputs/: wage_distance.html
# embeds a copy of this file the same way prototype.html embeds grid.json, so
# it has to be a tracked source of truth, not a gitignored scratch artifact.
OUTPUT_JSON = HERE / ".." / "data" / "wage_distance.json"

COLS = [
    "hh_income", "hlb_year", "economically_vulnerable",
    "no_adult", "no_schooler", "no_preschooler", "no_toddler", "no_infant",
]

# Same wage steps the shipped grid uses (data/build_dataset.py: WAGE_STEPS),
# so the cross-check below lines up index-for-index.
WAGE_STEPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]

BUCKETS = [
    ("zero_income", None, None),   # handled separately: no raise ever reaches $0
    ("0-10%", 0, 10),
    ("10-25%", 10, 25),
    ("25-50%", 25, 50),
    ("50-100%", 50, 100),
    ("100%+", 100, np.inf),
]


def load():
    print(f"Loading household records from {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH, usecols=COLS)
    print(f"Loaded {len(df):,} records.")
    return df


def composition_label(df: pd.DataFrame) -> pd.Series:
    """Same five categories as data/build_dataset.py:build_who, so results
    line up with the published 'who.composition' breakdown in grid.json."""
    kids_12 = (df.no_schooler + df.no_preschooler + df.no_toddler + df.no_infant) > 0
    single = df.no_adult == 1
    multi = df.no_adult >= 2
    no_adult = df.no_adult == 0

    label = pd.Series("No adult aged 19 or over", index=df.index)
    label[single & kids_12] = "One adult, with children under 12"
    label[multi & kids_12] = "Two or more adults, with children under 12"
    label[single & ~kids_12] = "One adult, no children under 12"
    label[multi & ~kids_12] = "Two or more adults, no children under 12"
    label[no_adult] = "No adult aged 19 or over"
    return label


def income_band_label(income: pd.Series) -> pd.Series:
    bins = [-1, 15000, 25000, 35000, 50000, 75000, 100000, 150000, 200000, np.inf]
    labels = [
        "Less than $15,000", "$15,000 to $24,999", "$25,000 to $34,999",
        "$35,000 to $49,999", "$50,000 to $74,999", "$75,000 to $99,999",
        "$100,000 to $149,999", "$150,000 to $199,999", "$200,000 or more",
    ]
    return pd.cut(income, bins=bins, labels=labels)


def cross_check_against_grid(df: pd.DataFrame, vuln: pd.DataFrame, pct_needed: pd.Series):
    """Independent-path validation: reconstruct the grid's own wage-only
    (cap=0, care=0, elig=0) rates from pct_needed and diff against grid.json."""
    print("\n--- Cross-check against data/grid.json (wage lever alone) ---")
    if not GRID_PATH.exists():
        print(f"  SKIPPED: {GRID_PATH} not found.")
        return

    grid = json.loads(GRID_PATH.read_text())
    wage_steps = grid["wageSteps"]
    cap_steps, care_steps, elig_steps = grid["capSteps"], grid["careSteps"], grid["eligSteps"]
    assert wage_steps == WAGE_STEPS, "wage steps in grid.json no longer match this script"

    def idx(w, c, k, e):
        return (((wage_steps.index(w) * len(cap_steps) + cap_steps.index(c))
                 * len(care_steps) + care_steps.index(k))
                * len(elig_steps) + elig_steps.index(e))

    # data/build_dataset.py's own spot-checks tolerate up to this many
    # households disagreeing, explained by cent-rounded cost columns vs. an
    # unrounded budget total (see data/README.md). This script uses the
    # shipped hlb_year directly rather than build_dataset.py's BudgetTax
    # interpolator, so it inherits the same tolerance rather than improving on it.
    ROUNDING_TOLERANCE = 5

    baseline_vulnerable = int(vuln.sum())
    max_disagreement = 0
    rows = []
    for w in wage_steps:
        lifted = int((pct_needed <= w).sum())
        remaining = baseline_vulnerable - lifted
        shipped_count = grid["countyCounts"][idx(w, 0, 0, 0)]
        diff = abs(remaining - shipped_count)
        max_disagreement = max(max_disagreement, diff)
        rows.append((w, remaining, shipped_count, diff))
        print(f"  wage +{w:>2}%: recomputed remaining-vulnerable {remaining:>7,} "
              f"vs shipped {shipped_count:>7,}  (diff {diff})")

    if max_disagreement == 0:
        print("  MATCH: exact, all nine steps -- two independent code paths agree.")
    elif max_disagreement <= ROUNDING_TOLERANCE:
        print(f"  MATCH within tolerance: max disagreement {max_disagreement} households, "
              f"inside the project's own {ROUNDING_TOLERANCE}-household cent-rounding bar.")
    else:
        print(f"  WARNING: max disagreement {max_disagreement} households, exceeds the "
              f"{ROUNDING_TOLERANCE}-household tolerance -- investigate before shipping.")
    return rows


def summarize(df: pd.DataFrame) -> dict:
    vuln = df.economically_vulnerable == 1
    n_vuln = int(vuln.sum())
    sub = df.loc[vuln].copy()

    zero_income = sub.hh_income == 0
    n_zero = int(zero_income.sum())

    reachable = sub.loc[~zero_income]
    pct_needed = (reachable.hlb_year / reachable.hh_income - 1) * 100

    # Full-population series (aligned to df's index) for the cross-check, so
    # zero-income households count as "never reachable" (pct_needed = inf).
    pct_needed_full = pd.Series(np.inf, index=sub.index)
    pct_needed_full.loc[reachable.index] = pct_needed
    cross_check_rows = cross_check_against_grid(df, vuln, pct_needed_full)

    bucket_counts = {}
    bucket_counts["zero_income"] = n_zero
    for name, lo, hi in BUCKETS[1:]:
        mask = (pct_needed > lo) & (pct_needed <= hi)
        bucket_counts[name] = int(mask.sum())
    assert sum(bucket_counts.values()) == n_vuln, "buckets must partition all vulnerable households"

    percentiles = [10, 25, 50, 75, 90, 95, 99]
    pct_values = {f"p{p}": round(float(np.percentile(pct_needed, p)), 1) for p in percentiles}

    within_slider_range = int((pct_needed <= 50).sum())  # calculator's own max wage step

    comp = composition_label(df.loc[vuln])
    by_composition = []
    for label in comp.unique():
        m = comp == label
        sub_pct = pct_needed_full.loc[m.index[m]]
        finite = sub_pct[np.isfinite(sub_pct)]
        by_composition.append({
            "label": label,
            "households": int(m.sum()),
            "zeroIncomeShare": round(float((sub_pct == np.inf).mean()), 4),
            "medianPctNeeded": round(float(finite.median()), 1) if len(finite) else None,
        })

    band = income_band_label(sub.hh_income)
    by_income_band = []
    for label in pd.Categorical(band).categories:
        m = band == label
        if not m.any():
            continue
        sub_pct = pct_needed_full.loc[sub.index[m]]
        finite = sub_pct[np.isfinite(sub_pct)]
        by_income_band.append({
            "label": label,
            "households": int(m.sum()),
            "zeroIncomeShare": round(float((sub_pct == np.inf).mean()), 4),
            "medianPctNeeded": round(float(finite.median()), 1) if len(finite) else None,
        })

    return {
        "note": "Distribution of the minimum uniform wage lift that would put each "
                "currently-below-budget household exactly at its own line, holding "
                "housing and childcare costs fixed -- the same assumption the wage "
                "slider alone uses. Never a per-household figure; every row is synthetic.",
        "vulnerableHouseholds": n_vuln,
        "zeroIncomeHouseholds": n_zero,
        "zeroIncomeShare": round(n_zero / n_vuln, 4),
        "buckets": bucket_counts,
        "percentiles": pct_values,
        "withinCalculatorSliderRange": {
            "maxWageStepModeled": 50,
            "householdsReachable": within_slider_range,
            "shareOfVulnerable": round(within_slider_range / n_vuln, 4),
        },
        "byComposition": by_composition,
        "byIncomeBand": by_income_band,
        "crossCheckVsGrid": [
            {"wagePct": w, "recomputedRemaining": remaining, "shippedRemaining": shipped, "diff": d}
            for w, remaining, shipped, d in (cross_check_rows or [])
        ],
    }


def main():
    df = load()
    result = summarize(df)

    OUTPUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {OUTPUT_JSON}")

    print("\n--- Summary ---")
    print(f"Vulnerable households: {result['vulnerableHouseholds']:,}")
    print(f"  of which zero recorded income (no raise ever reaches them): "
          f"{result['zeroIncomeHouseholds']:,} ({result['zeroIncomeShare']:.1%})")
    print("Distance-to-line buckets (share of vulnerable households):")
    for name, _, _ in BUCKETS:
        count = result["buckets"][name]
        print(f"  {name:>12}: {count:>7,}  ({count / result['vulnerableHouseholds']:.1%})")
    print("Percentiles of wage lift needed (excludes zero-income households):")
    for p, v in result["percentiles"].items():
        print(f"  {p}: {v}%")
    r = result["withinCalculatorSliderRange"]
    print(f"Reachable within the calculator's own +50% max slider: "
          f"{r['householdsReachable']:,} ({r['shareOfVulnerable']:.1%})")


if __name__ == "__main__":
    main()
