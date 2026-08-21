# Findings

Every figure here was recomputed from `data/raw/san_diego_ca_hlb_hackathon_2024.csv.gz`
by at least two independent code paths. Claim classes are defined in
[`CLAIMS_LEDGER.md`](CLAIMS_LEDGER.md); method and limits in
[`METHODOLOGY.md`](METHODOLOGY.md); external sources in [`SOURCES.md`](SOURCES.md).

---

## The spine

> **Where you live and who you live with set the bar — to the cent.
> What you earn decides whether you clear it.**

`hlb_year` is a **deterministic lookup** on (tract × household composition). All
**62,032** cells hold exactly one value; maximum within-cell standard deviation is
**$0.000000**; R² = **1.000000**. A pure lookup on that table reproduces the
organizers' `economically_vulnerable` flag for **1,171,123 of 1,171,123** households.

The threshold side of the inequality carries no uncertainty at all. Only income varies.
That single fact organises the whole project — and it is why the repository no longer
presents a machine-learning model (see *The model we removed*, below).
`[DERIVED RESULT]`

---

## Primary finding

### A 100% childcare subsidy lifts zero households earning under $50,000.

| | households |
|---|---|
| below their budget, baseline | 520,257 |
| below their budget, childcare fully covered | 498,503 |
| **lifted** | **21,755** |
| …of those, earning $50,000+ | **21,755 (100.0%)** |
| …of those, earning $100,000+ | 18,586 (85.4%) |
| …of those, earning under $50,000 | **0** |
| vulnerable child-households under $50k | 45,385 |
| …lifted by a 100% subsidy | **0** |

Families below $50,000 are short far more than their entire childcare bill, so the
lever cannot reach them. The money lands almost entirely on six-figure households.
This complicates the project's own policy close rather than flattering it, which is
why it leads. `[POLICY SIMULATION]`

---

## Supporting findings

**1. 61.5% of households below their budget contain no children at all** — 320,034 of
520,257. One-person households alone are 28.2% of everyone in the red, 4.9× the entire
single-parent population. This is not primarily a families story. `[DATASET RESULT]`

**2. The two lenses disagree about 100,892 households, in both directions.**
On the same 1,171,123 households:

|  | passes 30% rent test | fails 30% rent test |
|---|---|---|
| **covers basic needs** | 556,230 | 94,636 |
| **below basic needs** | **6,256** | 514,001 |

The conventional housing-only test flags *more* households (608,637) than the full
basic-needs test (520,257). 94,636 look rent-burdened but are solvent; 6,256 look fine
on rent and cannot afford a basic life. Neither test is a superset of the other.
`[DERIVED RESULT]`

**3. The median job in San Diego does not cover the median one-person budget.**
BLS OEWS all-occupations median **$58,690** against a median `hlb_year` of **$59,625**
for one adult, no children. Holds nominal and CPI-deflated. City minimum wage full-time
full-year is **$35,048 — 58.8%** of that budget, clearing in **0 of 727** tracts; the
cheapest tract in the county requires $40,497.
`[EXTERNAL MARKET CONTEXT × DATASET RESULT — see METHODOLOGY §5]`

**4. Geography sets the bar but does not explain who misses it.** Income alone explains
R² = 0.605 of vulnerability; adding household size → 0.872; adding tract adds only
**0.054** and lowers out-of-sample R². Flattening housing costs across tracts makes the
map *more* unequal (rate sd 15.1 → 16.3pp), because expensive tracts are rich tracts
(Spearman housing-level vs vulnerability = **−0.403**). `[DERIVED RESULT]`

**5. Means-testing the rent subsidy costs 38% less and delivers 32% of the effect.**

| rent subsidy at 30% of income | lifted | cost/yr | per $1B |
|---|---|---|---|
| offered to everyone | 72,742 | $10.04B | 7,243 |
| income ≤ 80% of county median ($84,958) | 52,389 | $8.44B | 6,207 |
| income ≤ 50% of county median ($53,099) | 23,202 | $6.27B | 3,700 |

The universal version is the *most* cost-effective per household lifted — because the
households nearest the line are cheapest to lift, and many of them are not poor. That
is an uncomfortable result and it is left standing. `[POLICY SIMULATION]`

**6. Singles without children are the majority of households below budget, but need the largest raise to clear it.** For each household below its budget, holding housing and childcare costs fixed — the same assumption the calculator's wage slider makes on its own — there is an exact minimum raise that would close that household's own gap: `wage_lift_pct_needed = (hlb_year / hh_income − 1) × 100`. Its distribution, by composition:

| composition | households below budget | median raise needed to clear the line |
|---|---|---|
| Two or more adults, no children under 12 | 216,917 | 60.6% |
| Two or more adults, with children under 12 | 126,855 | 82.7% |
| **One adult, no children under 12** | **155,852** | **111.6%** (more than double) |
| One adult, with children under 12 | 20,398 | 172.7% (nearly triple) |

15,913 households (3.1%) report zero income; no percentage raise of any size ever reaches
them. Across all 520,257: a raise of 10% or less would clear 9.5% of them; more than half
need over 81.8% (their income would need to nearly double); even the calculator's own
maximum wage-slider setting, +50%, reaches only 35.8%. By income band the direction is
intuitive but the size is not — under $15,000 needs a median 770% raise (nearly 9×
income); $150,000–199,999 needs 12%.

The single-adult, no-children group is both the largest bloc below budget (finding 1) and,
per household, the one furthest from clearing it on wages alone — the two findings sit
side by side without contradicting each other, because "most common" and "furthest from
the line" are different rankings of the same population. `[DERIVED RESULT]` — cross-validated
against the calculator's own precomputed grid at all nine wage steps: recomputed
remaining-vulnerable counts match the shipped grid to within 5 households at every step
(the project's own documented cent-rounding tolerance), exactly at six of nine. See
`policy_calculator/wage_distance_analysis.py`.

---

## External cross-check

Four independent measures, four methodologies, one county:

| source | measure | value |
|---|---|---|
| United For ALICE | below ALICE threshold, 2024 | 44.8% |
| HUD CHAS | cost-burdened households | 44.6% |
| **this project** | **below Household Living Budget** | **44.4%** |
| ACS 2024 | paid housing cost burden ≥30% | 43.6% |

The ACS figure uses **no imputed rent at all**, which is the empirical answer to the
tenure objection below. San Diego County HHSA's own self-sufficiency budget for a
family of four ($8,155/mo) agrees with this model's $8,700 to within 7%.
`[EXTERNAL MARKET CONTEXT]`

The headline is therefore a **replication**, not a discovery. Its value is that it
arrives with a working policy engine attached.

---

## The model we removed

An XGBoost classifier reporting 97.3% accuracy / 0.998 ROC-AUC was demoted from the
product. The reported numbers are honest and reproduce exactly; the earlier data-leakage
fix was genuine. It was removed anyway, because:

- the label is a **deterministic formula**, so there is nothing to predict;
- a **four-line median lookup beats it on every seed** under group-aware validation;
- it sits **0.17pp below the provable Bayes ceiling** for its own feature set;
- 84.4% of households are trivially classified at 99.97% — on the contested 15.6% near
  the line, accuracy is **81.9%**;
- false-negative rate varies **12.9×** across PUMAs, in a screener keyed on geography,
  with no protected characteristics in the data to test disparate impact against.

`policy_calculator/predictive_risk_model.py` remains in the repository with a
`--group-aware` split and a printed warning. It is not in the interface, and
"AI predicts poverty" framings are banned in [`CLAIMS_LEDGER.md`](CLAIMS_LEDGER.md).

---

## What remains uncertain

- **Tenure.** `housing_cost_month` is required rent, not rent paid, and there is no
  tenure field. An owner with a paid-off mortgage is charged market rent. 45.4% of the
  count is sensitive to this. The ACS 43.6% cross-check is the best available bound.
- **Two tracts excluded from the flagship set.** `06073009510` and `06073009511` are the
  only two of 727 with a majority of households holding children under 12 (99.7th
  percentile), uniformly maxed bedroom counts and low recorded income — the signature of
  military family housing, where BAH is excluded from ACS money income. Flagged in
  `tracts.csv` as `bah_profile`, kept in every aggregate, not featured.
- **Rents are ~8% stale.** The dataset prices FY2024 SAFMR, itself trended from a
  November 2021 local rent survey. Re-priced to FY2026 the county median moves
  $2,590 → $2,816 (+7.97%).
- **Effective sample size.** 55,218 donors, not 1.17M independent households. Standard
  errors computed at n = 1.17M are ~4.6× too small. County rate CI is ±0.41pp.
- **Child-household counts carry ±18%** against ACS — the organizers' own weakest
  validated dimension. Every child-related figure inherits that band.
