# Priceout Collective

**Building for Good Hackathon — Affordability track**
Data Science Alliance @ UC San Diego (Halicioglu School of Data Science and Computing)

## The finding

**44.4% of San Diego households — 520,257 of 1,171,123 — earn less than their
basic-needs budget requires.** That number is a *replication*, not a discovery: ALICE
puts it at 44.8%, HUD CHAS at 44.6%, and ACS paid cost burden at 43.6%. Four
methodologies, one county, a one-point spread.

What we add is the part nobody else publishes — **what it would take to change it**, and
what that costs:

> **A 100% childcare subsidy lifts zero households earning under $50,000.**
> 21,755 households move above their line; every one of them earns $50,000 or more, and
> 85% earn six figures. Families below $50,000 are short more than their entire childcare
> bill, so the lever cannot reach them.

The organising insight underneath all of it:

> **Where you live and who you live with set the bar — to the cent.
> What you earn decides whether you clear it.**

`hlb_year` is a deterministic lookup on (tract × composition): 62,032 cells, every one
holding a single value, R² = 1.000000. The threshold carries no uncertainty. Only income
varies.

## The demo

Open **`index.html`** in a browser for the unified demo. One entry page switches between
the policy calculator, the tract-level county map, and the wage-distance view; each can
also open full screen. No build or application server is required.

The calculator includes three levers, an eligibility test on the rent subsidy, and a live
cost figure — all 945 combinations precomputed exactly on all 1.17M households, so nothing
is estimated in the browser. The wage-distance view answers a different question: not what
one stated policy does countywide, but how large a raise it would take to close each
below-budget household's own gap — a distribution, computed exactly, never a per-household
claim.

## Where to look

| | |
|---|---|
| [`docs/FINDINGS.md`](docs/FINDINGS.md) | every finding, with its claim class and its caveat |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | how the model works and what it cannot do |
| [`docs/SOURCES.md`](docs/SOURCES.md) | every external figure, with a primary source |
| [`docs/CLAIMS_LEDGER.md`](docs/CLAIMS_LEDGER.md) | the six claim classes, and the banned language |

## ⚠️ Read this before building on the data

- **It is a single 2024 snapshot.** No growth rates, no time dimension. Any metric of the
  form "months until X" — the original runway idea — **cannot be computed from this
  data.** That premise is retired. Do not reintroduce it.
- **Geography is census tracts, not ZIP codes** (`geoid`, 2020 vintage). There is no ZIP
  field, and a tract→ZIP crosswalk would not preserve the thresholds.
- **Rows are synthetic households**, cloned from 55,218 PUMS donors. Valid for
  distributions and geography; never for claims about individual households. Do not
  deduplicate — it would silently delete most of the population. Effective sample size is
  55,218, so standard errors at n=1.17M are ~4.6× too small.
- **`housing_cost_month` is required rent, not rent paid.** HUD FY2024 Small Area FMR for
  the tract, not tenure-adjusted: an owner with a paid-off mortgage is still charged
  market rent.
- **The dataset has no occupation, education, age, race, sex or tenure.** Never impute
  them, and never join external data to a household row.

Full detail in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) and the organizers'
dictionary in `data/raw/` — **read the Word document before doing analysis.**

## Repo layout

```
index.html               ← unified demo entry point
data/
  raw/                       organizers' source files, unmodified
  build_dataset.py           raw microdata -> tracts.csv + grid.json
  tracts.csv                 727 census tracts, baseline figures
  grid.json                  exact rates at all 945 lever combinations
  wage_distance.json         distribution of the raise each below-budget household needs
  puma_names.csv             official 2020 PUMA names (Census TIGER/Line 2023)
policy_calculator/
  prototype.html             ← the calculator
  sync_data.py                regenerates the calculator's embedded data from grid.json
  wage_distance.html         ← the wage-distance view
  wage_distance_analysis.py  raw microdata -> data/wage_distance.json
  sync_wage_distance.py       regenerates that page's embedded data
map/                         the tract-level map
docs/                        methodology, sources, findings, claims ledger
```

## Rebuilding from source

```bash
pip install -r data/requirements.txt
cd data && python build_dataset.py --validate    # ~3 min over 1.17M rows
cd ../policy_calculator && python sync_data.py
python wage_distance_analysis.py && python sync_wage_distance.py
```

`--validate` reproduces the organizers' own `economically_vulnerable` flag, spot-checks
eight grid cells against fresh computations, and **fails loudly** if the ledger stops
adding up or a slider's range stops matching the grid.

New to git, or unsure how branches and PRs work here?
[`docs/git-for-teammates.md`](docs/git-for-teammates.md) — five minutes.
