# Methodology

## 1. The data

`data/raw/san_diego_ca_hlb_hackathon_2024.csv.gz` — the organizers' Household Living
Budget microdata for San Diego County. **1,171,123 synthetic households, 25 columns,
2024 dollars, 732 census tracts (2020 vintage), 22 PUMAs.**

Built by fitting ACS tract totals with iterative proportional fitting, then sampling
real PUMS households as donors. **55,218 distinct donors** produced the 1,171,123 rows —
roughly 21 copies each county-wide, a median of 1.6 reuses within any one tract.

Three consequences the pipeline enforces:

1. **Never deduplicate.** `drop_duplicates()` would delete most of the population.
2. **No row is a real household.** Valid for distributions and geographic patterns only.
3. **Group quarters are excluded** — military barracks, nursing homes, student housing,
   correctional facilities. A real omission in this county, not a technicality.

## 2. The threshold

`economically_vulnerable = 1` iff `hh_income < hlb_year`. Both sides are gross annual
2024 dollars, so it is like-for-like. This is the organizers' published measure.

`hlb_year = hlb_no_tax_year + hlb_taxes_year`, where `hlb_no_tax_year` is 12 × the sum
of seven monthly cost components. All four identities were verified across all
1,171,123 rows; residuals are cent-level rounding only, and
`economically_vulnerable == (hh_income < hlb_year)` has **zero violations**.

**Housing is required rent, not rent paid.** `housing_cost_month` is the HUD FY2024
Small Area Fair Market Rent for the tract at the bedroom count implied by household
size (`hh_size_recode` k → k−1 bedrooms; verified against HUD's published SAFMR table,
0-BR 970/3,090 and 4-BR 2,360/6,960 matching exactly). It is a normative standard and
is **not tenure-adjusted**: an owner with a paid-off mortgage is assigned a market rent.

**The two tax columns are different quantities.** `hlb_taxes_year` is tax on the
*budget* income — threshold construction only. `taxes_on_actual_income_year` is tax on
*actual* income. They are not interchangeable.

## 3. The three modelling corrections

The previous build carried two errors pointing in opposite directions. Correcting one
without the other is **worse than correcting neither**, so both are applied.

| | effect on the rent lever | direction |
|---|---|---|
| 'other essentials' recomputed from subsidised rent | +2.01pp | overstated |
| budget tax scaled by a fixed per-household ratio | −1.53pp | understated |
| **net, uncorrected** | **~3% on the headline** | |

**(a) 'Other essentials' is frozen at the cost of the unit.** The organizers define
`other_cost_month` as 20% of (food + housing), where housing is the FMR cost *of the
unit*. A rent subsidy changes who pays that rent, not what the unit costs. Recomputing
`other` from the subsidised rent handed the lever 1.2× leverage it had not earned.

**(b) Budget tax is interpolated, not scaled.** Within a composition type the budget tax
is a deterministic increasing function of the budget: among rows sharing (type, budget)
the observed spread is **$0.01**, i.e. cent rounding. Evaluating a *changed* budget
against that same observed curve is interpolation of a known function, not a fitted
model. It never extrapolates — queries outside a type's observed range clamp to its
endpoints. Correctness test: at baseline the changed budget equals the observed budget,
and the interpolator reproduces the shipped flag for **1,171,123 of 1,171,123** households.

**(c) The rent lever carries an income-eligibility dimension.** A universal subsidy is
not a policy anyone proposes. Eligibility is assessed on income *as it is in the
scenario* — i.e. after any wage lever — because that is what a program would observe.

## 4. The grid

9 wage × 7 cap × 5 childcare × 3 eligibility = **945 combinations**, each evaluated
exactly on all 1,171,123 households at build time and shipped as a lookup table. The
sliders index the step arrays directly, so **no interpolated — i.e. fabricated — value
can ever be displayed**. `sync_data.py` refuses to ship if a slider's `max` attribute
disagrees with its step list, or if the balance-sheet column does not add up.

Why a grid and not a browser-side sample: because rows are clones, a 24,000-row sample
carries far fewer independent households than its size implies, and the county rate
swung ±1.5pp on the random seed alone across five seeds.

## 5. External layers — how they are joined

External data is **never joined to a household row.** The dataset contains no
occupation, education, age, race, ethnicity, sex, tenure or employment status, and none
of these are imputed onto it.

The occupation comparison is a comparison of two independently sourced aggregates:

> A household of composition X in tract T needs $H per year `[DATASET RESULT]`.
> A worker in occupation Y earns $W at the median `[EXTERNAL MARKET CONTEXT, BLS OEWS]`.
> Therefore one full-time year-round Y wage, as a household's **only** income, does or
> does not clear that bar `[DERIVED RESULT]`.

Assumptions, all stated on the page: 2,080 hours; one earner; the household's own
composition drives its threshold; OEWS annual wages are hourly × 2,080 and therefore
full-time-equivalents, which makes the finding conservative for part-time-heavy
occupations. This comparison is legitimate at tract level specifically because
`hlb_year` has **zero within-tract variance** for a fixed composition — the threshold is
a lookup, not a sampled statistic, so "clears the bar in N of 727 tracts" is exact.

**Education was researched and dropped.** It answers the same question as occupation
with a less actionable label, and it is the strongest temptation to commit a fabricated
tract-level join.

## 6. Geography

727 of 732 tracts. Five hold under 100 households (smallest 9) and the dictionary
advises filtering before ranking or mapping; they are dropped from ranked output and
retained nowhere that implies precision.

Tracts are featured by **absolute number of households below their budget**, not by
rate. Ranking on rate alone had put tracts holding 2.9% of the county's affected
households at the top of the table, and the top-10-by-rate is not statistically
separable — the donor-adjusted CI is ±3.1pp and 60 tracts overlap the #10 threshold.

`median_shortfall_month` is the median of (`hlb_year` − `hh_income`) **among households
below their budget**, computed per household. It replaces a previous `median_gap` column
that was median(HLB) − median(income) — a difference of medians, which is not a quantity
any household possesses, and which disagreed in sign with the map's per-household
version in 74 of 727 tracts.

**Two tracts are flagged `bah_profile` and excluded from the featured set.**
`06073009510` and `06073009511` are the only two of 727 where a majority of households
hold children under 12 (99.7th percentile), with uniformly maxed bedroom counts and low
recorded income — the signature of military family housing, where the Basic Allowance
for Housing is excluded from ACS/PUMS money income while the model still charges full
market rent. Tenure and BAH cannot be confirmed from the release, so this is a
disclosure, not a correction: both tracts remain in every aggregate.

## 7. Known limitations, inherited

- **Tax law year is 2023 applied to 2024 dollars** (the organizers' TAXSIM
  implementation caps there). It slightly *overstates* tax and therefore vulnerability:
  shaving the threshold 0.5% moves the headline 44.42% → 44.19%.
- **Households-with-children counts carry ±18%** against independent ACS — the
  organizers' weakest validated dimension. Every child-related figure inherits it.
- **Household population runs 3.72% low** and average household size 3.24% low, because
  the model constrains how many households have 5+ members but not how many members they
  have. Affects per-person aggregation, not per-household budgets.
- **141,050 households across 84 tracts** carry an imputed broadband cost; 14 carry an
  imputed transportation cost.
- **Childcare ignores labour force participation** — charged whenever children under 12
  are present, including where no adult works.
- **Retirees cannot be identified.** Age bands stop at "19+", so tax modelling treats all
  budget income as wages for a 40-year-old and payroll tax is charged to every household.
- **`no_teenager` includes 18-year-olds**, unlike Census "under 18".
- **Negative incomes are floored to zero**, so true zeros and censored business losses
  are indistinguishable.
- **Effective sample size is 55,218, not 1,171,123.** Standard errors computed at the row
  count are ~4.6× too small. No p-value in this project is quoted at n = 1.17M.

## 8. Rebuilding

```bash
pip install -r data/requirements.txt
cd data && python build_dataset.py --validate    # ~3 min over 1.17M rows
cd ../policy_calculator && python sync_data.py
```

`--validate` reproduces the organizers' `economically_vulnerable` flag, spot-checks
eight grid cells against fresh computations, and fails loudly if the ledger does not
reconcile. Exactly one household disagrees with the shipped flag: it sits nine cents
from its threshold, where published cost columns are rounded to cents but the budget
total is not. If that count grows, the model is wrong, not the rounding.
