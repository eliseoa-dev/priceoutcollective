# Priceout Collective

**Building for Good Hackathon — Affordability track**
Data Science Alliance @ UC San Diego (Halicioglu School of Data Science and Computing)

## The finding

**44.4% of San Diego households — 520,257 of 1,171,123 — earn less than their
basic-needs budget requires.** For the average household in that position, the
gap is about $3,383 every month, and housing is 42.5% of what they need.

This project asks the follow-up: *what would it actually take to change that?*

## The two halves

1. **The map** (`map/`) — where households fall below their living budget,
   by census tract. Answers *who is at risk*.
2. **The policy calculator** (`policy_calculator/`) — three policy levers,
   recomputed across all 1.17M households, showing how many are lifted above
   the line. Answers *what would help*.

Open **`policy_calculator/prototype.html`** in a browser. No build, no server,
no dependencies.

## ⚠️ Read this before building on the data

The dataset is **not** what the project was originally scoped against, and the
difference matters:

- **It is a single 2024 snapshot.** There are no growth rates and no time
  dimension. Any metric defined as "months until X crosses Y" — the original
  runway idea — **cannot be computed from this data.** That premise is retired.
- **Geography is census tracts, not ZIP codes** (`geoid`, 2020 vintage).
- **Rows are synthetic households**, cloned from 55,218 PUMS donors. Valid for
  distributions and geography; never for claims about individual households.
  Do not deduplicate — it would silently delete much of the population.
- **`housing_cost_month` is required rent, not rent paid.** It is the HUD
  FY2024 Small Area Fair Market Rent for the tract at the household's implied
  bedroom count, and it is not tenure-adjusted.

Full details in `data/README.md` and the organizers' dictionary in `data/raw/`.

## Repo layout

```
data/
  raw/                 organizers' source files, unmodified
  build_dataset.py     raw microdata -> tracts.csv + grid.json
  tracts.csv           727 census tracts, baseline figures
  grid.json            exact rates at all 315 lever combinations
policy_calculator/
  prototype.html       ← the demo
  sync_data.py         regenerates the page's embedded data from grid.json
map/                   the tract-level risk map
docs/                  team docs, incl. a plain-language git guide
```

## Rebuilding from source

```bash
pip install -r data/requirements.txt
cd data && python build_dataset.py --validate    # ~2 min over 1.17M rows
cd ../policy_calculator && python sync_data.py
```

`--validate` checks the model against the organizers' own
`economically_vulnerable` flag and fails loudly if it drifts.

New to git, or unsure how branches and PRs work here?
[`docs/git-for-teammates.md`](docs/git-for-teammates.md) — five minutes.
