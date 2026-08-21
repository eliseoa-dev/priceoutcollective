"""
Build the project's working datasets from the organizers' HLB microdata.

Input   data/raw/san_diego_ca_hlb_hackathon_2024.csv.gz   (1.17M synthetic households)
Outputs data/tracts.csv     one row per census tract (baseline figures, for the map)
        data/grid.json      exact vulnerability rates over the policy-lever grid

    python build_dataset.py             # build both
    python build_dataset.py --validate  # also verify against the shipped flag

Why a grid rather than a sample. The calculator has to answer "what happens to
vulnerability if we pull this lever" instantly. The obvious approach — ship a
sample of households and recompute in the browser — does not survive contact
with this dataset: rows are clones of 55,218 PUMS donors, so a 24,000-row
sample holds far fewer independent households than its size suggests, and the
county rate swings about +/-1.5pp depending on the random seed. That is too
loose for a headline number.

So instead every lever combination is evaluated here, on all 1.17M households,
and the exact rates are shipped as a lookup table. The sliders move in discrete
policy steps that match the grid. Nothing is estimated at display time.

Guardrails from the organizers' data dictionary, enforced here:
  - never deduplicate (rows are intentional clones)
  - drop tracts under MIN_TRACT_HH before ranking or mapping
  - housing_cost_month is REQUIRED rent (HUD FMR), not rent paid
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw" / "san_diego_ca_hlb_hackathon_2024.csv.gz"
TRACTS_OUT = HERE / "tracts.csv"
GRID_OUT = HERE / "grid.json"

MIN_TRACT_HH = 100          # the dictionary flags 5 tracts below this as unreliable
OTHER_RATE = 0.20           # other_cost_month is defined as 20% of (food + housing)
FIXED_COSTS = ["transp_cost_month", "broadband_cost_month", "healthcare_cost_month"]

# The lever grid. These are the values the sliders snap to.
WAGE_STEPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]          # % income increase
CAP_STEPS = [0, 50, 45, 40, 35, 30, 25]                  # % of income; 0 = no cap
CARE_STEPS = [0, 25, 50, 75, 100]                        # % of childcare covered

N_FEATURED = 10

# Households whose shipped flag we may fail to reproduce due to cent-level rounding
# in the published cost columns. See validate() for why this is not zero.
MAX_ROUNDING_DISAGREEMENTS = 5


def load() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(
            f"error: {RAW} not found.\n"
            "       See data/raw/README.md for where the source file comes from."
        )
    df = pd.read_csv(RAW, dtype={"geoid": str, "puma": str})
    df["fixed_cost_month"] = df[FIXED_COSTS].sum(axis=1)
    # Tax on the budget as a fraction of the budget, held constant per household
    # so a changed budget implies a changed tax without re-solving TAXSIM.
    df["tax_ratio"] = (df.hlb_taxes_year / df.hlb_no_tax_year.replace(0, np.nan)).fillna(0)
    df["kids_under_12"] = (
        df.no_schooler + df.no_preschooler + df.no_toddler + df.no_infant
    ) > 0
    return df


class Model:
    """Vectorized vulnerability model over the whole population."""

    def __init__(self, df: pd.DataFrame):
        self.income = df.hh_income.to_numpy(float)
        self.food = df.food_cost_month.to_numpy(float)
        self.childcare = df.childcare_cost_month.to_numpy(float)
        self.housing = df.housing_cost_month.to_numpy(float)
        self.fixed = df.fixed_cost_month.to_numpy(float)
        self.tax = df.tax_ratio.to_numpy(float)
        self.kids = df.kids_under_12.to_numpy(bool)

    def hit(self, wage_pct: float, cap_pct: float, care_pct: float) -> np.ndarray:
        """Boolean per household: income below the living budget under these levers."""
        income = self.income * (1 + wage_pct / 100.0)

        housing = self.housing
        if cap_pct:
            # A HUD-style voucher: the household pays at most cap% of income toward
            # rent and the subsidy covers the rest, up to the FMR standard.
            housing = np.minimum(housing, (cap_pct / 100.0) * income / 12.0)

        childcare = self.childcare * (1 - care_pct / 100.0)
        other = OTHER_RATE * (self.food + housing)
        pre_tax = 12.0 * (self.food + childcare + housing + other + self.fixed)
        return income < pre_tax * (1 + self.tax)


def build_tracts(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("geoid")
    out = pd.DataFrame({
        "geoid": g.size().index,
        "households": g.size().values,
        "puma": g.puma.first().values,
        "median_income": g.hh_income.median().values.round(0),
        "median_hlb": g.hlb_year.median().values.round(0),
        "median_housing_month": g.housing_cost_month.median().values.round(0),
        "median_childcare_month": g.childcare_cost_month.median().values.round(0),
        "vulnerable_rate": g.economically_vulnerable.mean().values.round(4),
        "kids_share": g.kids_under_12.mean().values.round(4),
    })
    out["median_gap"] = (out.median_hlb - out.median_income).round(0)

    small = out[out.households < MIN_TRACT_HH]
    if len(small):
        print(f"  dropped {len(small)} tract(s) under {MIN_TRACT_HH} households "
              f"(flagged unreliable by the data dictionary)")
    out = out[out.households >= MIN_TRACT_HH].copy()

    out = out.sort_values("vulnerable_rate", ascending=False).reset_index(drop=True)
    out["featured"] = False
    out.loc[out.head(N_FEATURED).index, "featured"] = True
    return out


def build_grid(df: pd.DataFrame, tracts: pd.DataFrame) -> dict:
    """Exact rates at every lever combination, county-wide and per featured tract."""
    model = Model(df)

    featured = tracts[tracts.featured].geoid.tolist()
    lookup = {g: i for i, g in enumerate(featured)}
    codes = df.geoid.map(lookup).to_numpy()
    in_featured = ~pd.isna(codes)
    codes = np.where(in_featured, codes, -1).astype(int)
    f_codes = codes[in_featured]
    f_counts = np.bincount(f_codes, minlength=len(featured)).astype(float)

    kids = model.kids
    n_kids = int(kids.sum())

    county, county_kids, per_tract = [], [], []
    total = len(WAGE_STEPS) * len(CAP_STEPS) * len(CARE_STEPS)
    done = 0

    for w in WAGE_STEPS:
        for c in CAP_STEPS:
            for k in CARE_STEPS:
                hit = model.hit(w, c, k)
                county.append(round(float(hit.mean()) * 1000000))
                county_kids.append(round(float(hit[kids].sum()) / n_kids * 1000000))
                sums = np.bincount(f_codes, weights=hit[in_featured].astype(float),
                                   minlength=len(featured))
                per_tract.append([round(v) for v in (sums / f_counts * 1000000)])
                done += 1
        print(f"    {done}/{total} combinations", end="\r")
    print(f"    {total}/{total} combinations   ")

    # Median monthly cost components, for the budget-composition view. Taken over
    # vulnerable households specifically: the county median household is solvent,
    # so a county-wide median would not describe the households in question.
    vuln = df[df.economically_vulnerable == 1]
    components = [
        ("Housing", "housing_cost_month"),
        ("Transportation", "transp_cost_month"),
        ("Healthcare", "healthcare_cost_month"),
        ("Food", "food_cost_month"),
        ("Other essentials", "other_cost_month"),
        ("Childcare", "childcare_cost_month"),
        ("Broadband", "broadband_cost_month"),
    ]

    return {
        "note": "Rates are per-million integers (444239 = 44.4239%). Exact, computed on "
                "all 1,171,123 households — not sampled.",
        "population": int(len(df)),
        "vulnerableCount": int(df.economically_vulnerable.sum()),
        "budget": {
            # Means, not medians: a median of each component would not sum to the
            # median total, so the stack would not reconcile with the bar it sits in.
            # Means do add up. The shortfall is computed per household and then
            # medianed, which is a legitimate median of a real quantity.
            "scope": "mean monthly amounts across the 520,257 vulnerable households",
            "incomeMonth": round(float(vuln.hh_income.mean()) / 12),
            "budgetMonth": round(float(vuln.hlb_year.mean()) / 12),
            "taxMonth": round(float(vuln.hlb_taxes_year.mean()) / 12),
            "medianShortfallMonth": round(float((vuln.hlb_year - vuln.hh_income).median()) / 12),
            "components": [
                {"name": n, "amount": round(float(vuln[c].mean()))}
                for n, c in components
            ],
        },
        "wageSteps": WAGE_STEPS,
        "capSteps": CAP_STEPS,
        "careSteps": CARE_STEPS,
        "county": county,
        "countyKids": county_kids,
        "kidsShare": round(float(kids.mean()), 4),
        "tracts": [
            {
                "geoid": r.geoid,
                # The release carries no neighborhood names — only tract and PUMA
                # codes. We show the PUMA rather than guessing at a place name.
                "puma": r.puma,
                "households": int(r.households),
                "medianIncome": int(r.median_income),
                "medianHlb": int(r.median_hlb),
                "medianHousing": int(r.median_housing_month),
                "kidsShare": float(r.kids_share),
            }
            for r in tracts[tracts.featured].itertuples()
        ],
        "tractRates": per_tract,
    }


def validate(df: pd.DataFrame, grid: dict) -> None:
    model = Model(df)
    mine = model.hit(0, 0, 0)
    official = df.economically_vulnerable.astype(bool).to_numpy()
    differing = int((mine != official).sum())

    print(f"\n  reconstruction vs shipped economically_vulnerable flag:")
    print(f"    ours     {mine.mean():.6%}")
    print(f"    official {official.mean():.6%}")
    print(f"    households classified differently: {differing} of {len(df):,}")

    # The published cost columns are each rounded to cents, but hlb_no_tax_year is
    # computed from unrounded values. So for a household sitting within a few cents
    # of its threshold, no arithmetic on the published columns can reproduce the
    # shipped flag. One household in this release is 9 cents from the line. That is
    # a rounding artifact in the source, not a modeling disagreement — but if this
    # count ever grows, something real has broken.
    if differing > MAX_ROUNDING_DISAGREEMENTS:
        raise SystemExit(
            f"error: {differing} households disagree with the shipped flag, "
            f"more than the {MAX_ROUNDING_DISAGREEMENTS} explainable by cent-level "
            "rounding. The model is wrong, not the rounding."
        )
    print(f"    within the {MAX_ROUNDING_DISAGREEMENTS}-household rounding tolerance.")

    idx = lambda w, c, k: ((WAGE_STEPS.index(w) * len(CAP_STEPS) + CAP_STEPS.index(c))
                           * len(CARE_STEPS) + CARE_STEPS.index(k))
    print("\n  spot checks (grid value vs freshly computed):")
    for w, c, k in [(0, 0, 0), (25, 0, 0), (0, 30, 0), (0, 0, 50), (25, 30, 50)]:
        stored = grid["county"][idx(w, c, k)] / 1000000
        fresh = float(model.hit(w, c, k).mean())
        flag = "ok" if abs(stored - fresh) < 1e-4 else "MISMATCH"
        print(f"    wage+{w:<3} cap{c:<3} care{k:<4} {stored:7.2%}  {fresh:7.2%}  {flag}")
        if flag == "MISMATCH":
            raise SystemExit("error: grid disagrees with a fresh computation")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    print(f"Reading {RAW.name} ...")
    df = load()
    print(f"  {len(df):,} households, {df.geoid.nunique()} tracts, {df.puma.nunique()} PUMAs")

    tracts = build_tracts(df)
    tracts.to_csv(TRACTS_OUT, index=False)
    print(f"  wrote {TRACTS_OUT.name}: {len(tracts)} tracts")

    print("  evaluating the policy grid on all households ...")
    grid = build_grid(df, tracts)
    GRID_OUT.write_text(json.dumps(grid, separators=(",", ":")))
    print(f"  wrote {GRID_OUT.name}: "
          f"{len(grid['county'])} combinations, {GRID_OUT.stat().st_size / 1000:.0f} KB")

    if args.validate:
        validate(df, grid)

    print(f"\nCounty-wide vulnerable: {df.economically_vulnerable.mean():.1%} "
          f"({df.economically_vulnerable.sum():,} of {len(df):,} households)")


if __name__ == "__main__":
    main()
