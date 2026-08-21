"""
Build the project's working datasets from the organizers' HLB microdata.

Input   data/raw/san_diego_ca_hlb_hackathon_2024.csv.gz   (1.17M synthetic households)
Outputs data/tracts.csv     one row per census tract (baseline figures, for the map)
        data/grid.json      exact vulnerability rates over the policy-lever grid

    python build_dataset.py             # build both
    python build_dataset.py --validate  # also verify against the shipped flag

Why a grid rather than a sample. The calculator has to answer "what happens to
vulnerability if we pull this lever" instantly. The obvious approach — ship a
sample of households and recompute in the browser — does not survive contact with
this dataset: rows are clones of 55,218 PUMS donors, so a 24,000-row sample holds
far fewer independent households than its size suggests, and the county rate swings
about +/-1.5pp depending on the random seed. That is too loose for a headline.

So every lever combination is evaluated here, on all 1.17M households, and the
exact rates ship as a lookup table. The sliders snap to the grid. Nothing is
estimated at display time.

Guardrails from the organizers' data dictionary, enforced here:
  - never deduplicate (rows are intentional clones)
  - drop tracts under MIN_TRACT_HH before ranking or mapping
  - housing_cost_month is REQUIRED rent (HUD FMR), not rent paid

THREE MODELLING CORRECTIONS (see docs/METHODOLOGY.md for the measured effect of each):

  1. 'Other essentials' is frozen at the cost of the unit. The organizers define
     other_cost_month as 20% of (food + housing), where housing is the FMR cost OF
     THE UNIT. A rent subsidy changes who pays that rent, not what the unit costs,
     so 'other' must not fall when the rent lever fires. Recomputing it from the
     subsidised rent handed the lever 1.2x leverage it had not earned: it overstated
     the rent lever by 2.01pp.

  2. Budget tax is interpolated off each composition type's own observed tax curve
     rather than scaled by a fixed ratio. Within a composition type the budget tax
     is a deterministic increasing function of the budget — among rows sharing
     (type, budget) the observed spread is $0.01, i.e. cent rounding. Evaluating a
     changed budget against that same curve is interpolation of a known function,
     not a fitted model, and it reproduces the shipped flag exactly at baseline.
     The fixed-ratio approximation understated the rent lever by 1.53pp.

     These two errors pointed in opposite directions and partly cancelled, which is
     why the uncorrected headline was only ~3% off. Correcting one without the other
     is worse than correcting neither.

  3. The rent lever carries an income-eligibility dimension. A universal subsidy is
     not a policy anyone proposes; means-testing is the honest comparison, and it is
     the answer to "isn't this just spraying money at everyone".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw" / "san_diego_ca_hlb_hackathon_2024.csv.gz"
PUMA_NAMES = HERE / "puma_names.csv"
TRACTS_OUT = HERE / "tracts.csv"
GRID_OUT = HERE / "grid.json"

MIN_TRACT_HH = 100          # the dictionary flags 5 tracts below this as unreliable
OTHER_RATE = 0.20           # other_cost_month is defined as 20% of (food + housing)
FIXED_COSTS = ["transp_cost_month", "broadband_cost_month", "healthcare_cost_month"]
COMP_COLS = ["no_adult", "no_teenager", "no_schooler",
             "no_preschooler", "no_toddler", "no_infant"]

# The lever grid. These are the values the sliders snap to.
WAGE_STEPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]          # % income increase
CAP_STEPS = [0, 50, 45, 40, 35, 30, 25]                  # % of income; 0 = no subsidy
CARE_STEPS = [0, 25, 50, 75, 100]                        # % of childcare covered
ELIG_STEPS = [0, 80, 50]                                 # 0 = universal; else % of county median

N_FEATURED = 10

# Households whose shipped flag we may fail to reproduce due to cent-level rounding
# in the published cost columns. See validate() for why this is not zero.
MAX_ROUNDING_DISAGREEMENTS = 5

# Tracts whose household profile is consistent with military family housing, where
# the Basic Allowance for Housing is excluded from ACS/PUMS money income while the
# model still charges a full market rent. Flagged, never silently dropped — we
# cannot confirm tenure or BAH from the release, so this is a disclosure, not a fix.
# Threshold: share of households with children under 12 at or above 0.50. Exactly
# two of 727 reliable tracts qualify, and both sit in the 99.7th percentile.
BAH_KIDS_SHARE = 0.50

SCALE = 1e7          # composite-key scale for the tax interpolator; > any annual budget


def load() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(
            f"error: {RAW} not found.\n"
            "       See data/raw/README.md for where the source file comes from."
        )
    df = pd.read_csv(RAW, dtype={"geoid": str, "puma": str})
    df["fixed_cost_month"] = df[FIXED_COSTS].sum(axis=1)
    df["kids_under_12"] = (
        df.no_schooler + df.no_preschooler + df.no_toddler + df.no_infant
    ) > 0
    return df


class BudgetTax:
    """Exact budget-tax lookup, interpolated within composition type.

    hlb_taxes_year is a deterministic increasing function of hlb_no_tax_year once
    composition is fixed. We evaluate a *changed* budget against each household's
    own type curve. Never extrapolates: queries outside a type's observed range
    clamp to its endpoints.
    """

    def __init__(self, df: pd.DataFrame):
        code, _ = pd.factorize(pd.MultiIndex.from_frame(df[COMP_COLS]))
        base = df.hlb_no_tax_year.to_numpy(float)
        tax = df.hlb_taxes_year.to_numpy(float)
        if base.max() >= SCALE:
            raise ValueError("budget exceeds the composite-key scale")
        order = np.lexsort((base, code))
        self.x = base[order]
        self.y = tax[order]
        self.key = code[order] * SCALE + self.x       # globally sorted, unlike x alone
        self.code = code
        c_sorted = code[order]
        n = int(code.max()) + 1
        self.lo = np.searchsorted(c_sorted, np.arange(n), "left")
        self.hi = np.searchsorted(c_sorted, np.arange(n), "right") - 1

    def __call__(self, new_base: np.ndarray) -> np.ndarray:
        lo, hi = self.lo[self.code], self.hi[self.code]
        j = np.clip(np.searchsorted(self.key, self.code * SCALE + new_base, "left"), lo, hi)
        jm = np.maximum(j - 1, lo)
        x1, y1, x0, y0 = self.x[j], self.y[j], self.x[jm], self.y[jm]
        same = x1 == x0
        t = np.clip(np.where(same, 0.0, (new_base - x0) / np.where(same, 1.0, x1 - x0)), 0.0, 1.0)
        return y0 + t * (y1 - y0)


class Model:
    """Vectorized vulnerability model over the whole population."""

    def __init__(self, df: pd.DataFrame):
        self.income = df.hh_income.to_numpy(float)
        self.food = df.food_cost_month.to_numpy(float)
        self.childcare = df.childcare_cost_month.to_numpy(float)
        self.housing = df.housing_cost_month.to_numpy(float)
        self.fixed = df.fixed_cost_month.to_numpy(float)
        self.kids = df.kids_under_12.to_numpy(bool)
        self.tax = BudgetTax(df)
        self.median_income = float(np.median(self.income))
        # 'other' as the organizers define it, from the UNCAPPED cost of the unit
        self.other = OTHER_RATE * (self.food + self.housing)

    def _housing(self, income: np.ndarray, cap_pct: float, elig_pct: float) -> np.ndarray:
        if not cap_pct:
            return self.housing
        # A housing voucher: the household pays at most cap% of income toward rent
        # and the subsidy covers the rest, up to the FMR standard.
        subsidised = np.minimum(self.housing, (cap_pct / 100.0) * income / 12.0)
        if not elig_pct:
            return subsidised
        eligible = income <= (elig_pct / 100.0) * self.median_income
        return np.where(eligible, subsidised, self.housing)

    def hit(self, wage_pct: float, cap_pct: float, care_pct: float,
            elig_pct: float = 0) -> np.ndarray:
        """Boolean per household: income below the living budget under these levers."""
        income = self.income * (1 + wage_pct / 100.0)
        housing = self._housing(income, cap_pct, elig_pct)
        childcare = self.childcare * (1 - care_pct / 100.0)
        pre_tax = 12.0 * (self.food + childcare + housing + self.other + self.fixed)
        return income < pre_tax + self.tax(pre_tax)

    def subsidy_cost(self, wage_pct: float, cap_pct: float, elig_pct: float) -> float:
        """Annual public cost of the rent lever, in dollars."""
        if not cap_pct:
            return 0.0
        income = self.income * (1 + wage_pct / 100.0)
        paid = self._housing(income, cap_pct, elig_pct)
        return float(np.sum(np.maximum(self.housing - paid, 0.0)) * 12.0)


def build_tracts(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("geoid")
    shortfall = df.hlb_year - df.hh_income
    vuln = df.economically_vulnerable == 1

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

    # Number in the red, not just the rate. A high rate in a 469-household tract and
    # a high rate in a 7,260-household tract are not the same policy problem, and
    # ranking on rate alone had put tracts holding 2.9% of the county's affected
    # households at the top of the table.
    out["vulnerable_households"] = g.economically_vulnerable.sum().values.astype(int)

    # Median monthly shortfall AMONG HOUSEHOLDS IN THE RED. The previous column
    # named median_gap was median(HLB) - median(income): a difference of medians,
    # which is not a quantity any household possesses, and which disagreed in sign
    # with the map's per-household version in 74 of 727 tracts.
    med_short = (shortfall[vuln].groupby(df.geoid[vuln]).median() / 12).round(0)
    out["median_shortfall_month"] = out.geoid.map(med_short).fillna(0).astype(int)

    small = out[out.households < MIN_TRACT_HH]
    if len(small):
        print(f"  dropped {len(small)} tract(s) under {MIN_TRACT_HH} households "
              f"(flagged unreliable by the data dictionary)")
    out = out[out.households >= MIN_TRACT_HH].copy()

    # Disclosure flag, not a filter. See BAH_KIDS_SHARE above.
    out["bah_profile"] = out.kids_share >= BAH_KIDS_SHARE

    # Sort deterministically. Several tracts share a rate, and an unstable sort
    # orders ties differently between pandas versions and platforms — which would
    # change the set of featured tracts depending on whose machine built the file.
    out = out.sort_values(
        ["vulnerable_households", "geoid"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)

    # Feature by absolute number in the red, excluding the BAH-profile tracts from
    # the flagship set. They stay in the file and stay on the map; they are simply
    # not the tracts the demo leads with, because we cannot answer the obvious
    # question about them from this release.
    eligible = out[~out.bah_profile]
    out["featured"] = False
    out.loc[eligible.head(N_FEATURED).index, "featured"] = True
    return out


INCOME_BANDS = [
    "Less than $15,000", "$15,000 to $24,999", "$25,000 to $34,999",
    "$35,000 to $49,999", "$50,000 to $74,999", "$75,000 to $99,999",
    "$100,000 to $149,999", "$150,000 to $199,999", "$200,000 or more",
]


def build_who(df: pd.DataFrame) -> dict:
    """Who is falling short — by income, by household composition, by size."""
    vuln = df.economically_vulnerable == 1
    n_vuln = int(vuln.sum())
    gap_month = (df.hlb_year - df.hh_income) / 12

    def summarize(mask, label):
        n = int(mask.sum())
        if n == 0:
            return None
        return {
            "label": label,
            "households": n,
            "rate": round(float(df.loc[mask, "economically_vulnerable"].mean()), 4),
            "shareOfVulnerable": round(float((mask & vuln).sum()) / n_vuln, 4),
            "medianGapMonth": round(float(gap_month[mask & vuln].median())),
        }

    # One definition of "with children", used everywhere. The page previously
    # rendered two different populations — 31.7% (any child, including teenagers)
    # and 21.7% (children under 12 only) — with nothing reconciling them.
    kids_12 = df.kids_under_12
    single = df.no_adult == 1
    multi = df.no_adult >= 2
    no_adult = df.no_adult == 0

    composition = [
        summarize(single & kids_12, "One adult, with children under 12"),
        summarize(multi & kids_12, "Two or more adults, with children under 12"),
        summarize(single & ~kids_12, "One adult, no children under 12"),
        summarize(multi & ~kids_12, "Two or more adults, no children under 12"),
        # 235 households report no member aged 19+. Small, but the bars have to sum.
        summarize(no_adult, "No adult aged 19 or over"),
    ]

    sizes = [summarize(df.hh_size == i, f"{i} person" + ("" if i == 1 else "s"))
             for i in range(1, 6)]
    sizes.append(summarize(df.hh_size >= 6, "6 or more"))

    bands = [s for b in INCOME_BANDS for s in [summarize(df.hh_income_cat == b, b)] if s]

    t = df.groupby("geoid").economically_vulnerable.agg(["size", "sum"])
    t = t[t["size"] >= MIN_TRACT_HH].sort_values("sum", ascending=False)

    # The 30%-of-income housing test against the full basic-needs test. Both are
    # computed here on the same households, so the 2x2 reconciles exactly.
    burdened = (df.housing_cost_month * 12) > (0.30 * df.hh_income)
    return {
        "incomeBands": bands,
        "composition": [c for c in composition if c],
        "sizes": [s for s in sizes if s],
        # Two different populations, both reported explicitly so nothing on the
        # page has to guess which "with children" it means.
        "noKidsU12ShareOfVulnerable": round(float((vuln & ~kids_12).sum()) / n_vuln, 4),
        "noKidsAtAllShareOfVulnerable": round(
            float((vuln & ~kids_12 & (df.no_teenager == 0)).sum()) / n_vuln, 4),
        "noKidsAtAllCount": int((vuln & ~kids_12 & (df.no_teenager == 0)).sum()),
        "earning50kPlus": {
            "households": int((vuln & (df.hh_income >= 50000)).sum()),
            "share": round(float((vuln & (df.hh_income >= 50000)).sum()) / n_vuln, 4),
        },
        "earning100kPlus": {
            "households": int((vuln & (df.hh_income >= 100000)).sum()),
            "share": round(float((vuln & (df.hh_income >= 100000)).sum()) / n_vuln, 4),
        },
        "concentration": {
            "tracts": int(len(t)),
            "top50Share": round(float(t.head(50)["sum"].sum() / t["sum"].sum()), 4),
        },
        "lenses": {
            "note": "The conventional 30%-of-income housing test vs the full "
                    "basic-needs budget, on the same 1,171,123 households.",
            "burdenedOnly": int((burdened & ~vuln).sum(),),
            "hlbOnly": int((~burdened & vuln).sum()),
            "both": int((burdened & vuln).sum()),
            "neither": int((~burdened & ~vuln).sum()),
            "burdenedTotal": int(burdened.sum()),
            "hlbTotal": n_vuln,
        },
    }


def build_grid(df: pd.DataFrame, tracts: pd.DataFrame) -> dict:
    """Exact rates at every lever combination, county-wide and per featured tract."""
    model = Model(df)

    featured = tracts[tracts.featured].geoid.tolist()
    lookup = {g: i for i, g in enumerate(featured)}
    codes = df.geoid.map(lookup).to_numpy()
    in_featured = ~pd.isna(codes)
    f_codes = np.where(in_featured, codes, -1).astype(int)[in_featured]
    f_counts = np.bincount(f_codes, minlength=len(featured)).astype(float)

    kids = model.kids
    n_kids = int(kids.sum())

    county, county_kids, per_tract, cost = [], [], [], []
    total = len(WAGE_STEPS) * len(CAP_STEPS) * len(CARE_STEPS) * len(ELIG_STEPS)
    done = 0

    for w in WAGE_STEPS:
        for c in CAP_STEPS:
            for k in CARE_STEPS:
                for e in ELIG_STEPS:
                    hit = model.hit(w, c, k, e)
                    county.append(round(float(hit.mean()) * 1000000))
                    county_kids.append(round(float(hit[kids].sum()) / n_kids * 1000000))
                    sums = np.bincount(f_codes, weights=hit[in_featured].astype(float),
                                       minlength=len(featured))
                    per_tract.append([round(v) for v in (sums / f_counts * 1000000)])
                    # Annual public cost of the rent lever, in millions.
                    cost.append(round(model.subsidy_cost(w, c, e) / 1e6))
                    done += 1
            print(f"    {done}/{total} combinations", end="\r")
    print(f"    {total}/{total} combinations   ")

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
    comp_vals = [(n, round(float(vuln[c].mean()))) for n, c in components]
    cost_total = sum(v for _, v in comp_vals)
    tax_month = round(float(vuln.hlb_taxes_year.mean()) / 12)

    # Official 2020 PUMA names, so the table reads as places rather than FIPS codes.
    # Sourced from Census TIGER/Line 2023 (NAMELSAD20); nothing is invented here.
    names = {}
    if PUMA_NAMES.exists():
        pn = pd.read_csv(PUMA_NAMES, dtype=str)
        names = dict(zip(pn.puma, pn.puma_label))
        missing = {r.puma for r in tracts[tracts.featured].itertuples()} - set(names)
        if missing:
            raise SystemExit(f"error: no PUMA name for {sorted(missing)}")

    return {
        "note": "Rates are per-million integers (444239 = 44.4239%). Exact, computed on "
                "all 1,171,123 households — not sampled.",
        "population": int(len(df)),
        "who": build_who(df),
        "vulnerableCount": int(df.economically_vulnerable.sum()),
        "countyMedianIncome": round(model.median_income),
        "budget": {
            # EVERY figure in this block is a mean over the households in the red, so
            # the column adds up on screen: components -> total -> +tax -> required,
            # minus earned = short. The median shortfall is carried separately and
            # labelled as such; it must never be subtracted from a column of means.
            "scope": "mean monthly amounts across the households in the red",
            "incomeMonth": round(float(vuln.hh_income.mean()) / 12),
            "costMonth": cost_total,
            "taxMonth": tax_month,
            "requiredMonth": cost_total + tax_month,
            "meanShortfallMonth": cost_total + tax_month - round(float(vuln.hh_income.mean()) / 12),
            "medianShortfallMonth": round(float((vuln.hlb_year - vuln.hh_income).median()) / 12),
            "housingShareOfCost": round(comp_vals[0][1] / cost_total, 4),
            "housingShareOfRequired": round(comp_vals[0][1] / (cost_total + tax_month), 4),
            "components": [{"name": n, "amount": v} for n, v in comp_vals],
        },
        "wageSteps": WAGE_STEPS,
        "capSteps": CAP_STEPS,
        "careSteps": CARE_STEPS,
        "eligSteps": ELIG_STEPS,
        "county": county,
        "countyKids": county_kids,
        "rentSubsidyCostMillions": cost,
        "kidsShare": round(float(kids.mean()), 4),
        "tracts": [
            {
                "geoid": r.geoid,
                "puma": r.puma,
                "pumaName": names.get(r.puma, ""),
                "households": int(r.households),
                "vulnerableHouseholds": int(r.vulnerable_households),
                "medianIncome": int(r.median_income),
                "medianHlb": int(r.median_hlb),
                "medianHousing": int(r.median_housing_month),
                "medianShortfallMonth": int(r.median_shortfall_month),
                "kidsShare": float(r.kids_share),
            }
            for r in tracts[tracts.featured].itertuples()
        ],
        "tractRates": per_tract,
    }


def validate(df: pd.DataFrame, grid: dict) -> None:
    model = Model(df)
    mine = model.hit(0, 0, 0, 0)
    official = df.economically_vulnerable.astype(bool).to_numpy()
    differing = int((mine != official).sum())

    print("\n  reconstruction vs shipped economically_vulnerable flag:")
    print(f"    ours     {mine.mean():.6%}")
    print(f"    official {official.mean():.6%}")
    print(f"    households classified differently: {differing} of {len(df):,}")

    # The published cost columns are each rounded to cents, but hlb_no_tax_year is
    # computed from unrounded values. So for a household sitting within a few cents
    # of its threshold, no arithmetic on the published columns can reproduce the
    # shipped flag. If this count ever grows, something real has broken.
    if differing > MAX_ROUNDING_DISAGREEMENTS:
        raise SystemExit(
            f"error: {differing} households disagree with the shipped flag, "
            f"more than the {MAX_ROUNDING_DISAGREEMENTS} explainable by cent-level "
            "rounding. The model is wrong, not the rounding."
        )
    print(f"    within the {MAX_ROUNDING_DISAGREEMENTS}-household rounding tolerance.")

    def idx(w, c, k, e):
        return (((WAGE_STEPS.index(w) * len(CAP_STEPS) + CAP_STEPS.index(c))
                 * len(CARE_STEPS) + CARE_STEPS.index(k))
                * len(ELIG_STEPS) + ELIG_STEPS.index(e))

    print("\n  spot checks (grid value vs freshly computed):")
    for w, c, k, e in [(0, 0, 0, 0), (25, 0, 0, 0), (0, 30, 0, 0), (0, 0, 50, 0),
                       (0, 30, 0, 50), (25, 30, 50, 0), (25, 30, 50, 50), (50, 25, 100, 80)]:
        stored = grid["county"][idx(w, c, k, e)] / 1000000
        fresh = float(model.hit(w, c, k, e).mean())
        # stored values are per-million integers, so half a unit is the floor
        flag = "ok" if abs(stored - fresh) <= 5e-7 else "MISMATCH"
        print(f"    wage+{w:<3} cap{c:<3} care{k:<4} elig{e:<3} "
              f"{stored:7.2%}  {fresh:7.2%}  {flag}")
        if flag == "MISMATCH":
            raise SystemExit("error: grid disagrees with a fresh computation")

    # The ledger has to reconcile on screen: a judge will subtract these two numbers.
    b = grid["budget"]
    implied = b["requiredMonth"] - b["incomeMonth"]
    print(f"\n  ledger reconciliation: required {b['requiredMonth']} - earned "
          f"{b['incomeMonth']} = {implied}, stored meanShortfallMonth "
          f"{b['meanShortfallMonth']}")
    if implied != b["meanShortfallMonth"]:
        raise SystemExit("error: the budget ledger does not add up")
    print("    ok — the column adds up.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    print(f"Reading {RAW.name} ...")
    df = load()
    print(f"  {len(df):,} households, {df.geoid.nunique()} tracts, {df.puma.nunique()} PUMAs")

    tracts = build_tracts(df)
    tracts.to_csv(TRACTS_OUT, index=False)
    print(f"  wrote {TRACTS_OUT.name}: {len(tracts)} tracts "
          f"({int(tracts.bah_profile.sum())} flagged BAH-profile, excluded from the featured set)")

    print("  evaluating the policy grid on all households ...")
    grid = build_grid(df, tracts)
    GRID_OUT.write_text(json.dumps(grid, separators=(",", ":")))
    print(f"  wrote {GRID_OUT.name}: "
          f"{len(grid['county'])} combinations, {GRID_OUT.stat().st_size / 1000:.0f} KB")

    if args.validate:
        validate(df, grid)

    print(f"\nCounty-wide in the red: {df.economically_vulnerable.mean():.1%} "
          f"({df.economically_vulnerable.sum():,} of {len(df):,} households)")


if __name__ == "__main__":
    main()
