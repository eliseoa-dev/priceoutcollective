# data/

## The source

`raw/san_diego_ca_hlb_hackathon_2024.csv.gz` — the organizers' Household Living
Budget microdata for San Diego County. 1,171,123 rows, 25 columns, 2024 dollars.
Gzipped at 16.7 MB; 175 MB decompressed. Read it directly, no need to unpack:

```python
df = pd.read_csv("raw/san_diego_ca_hlb_hackathon_2024.csv.gz", dtype={"geoid": str, "puma": str})
```

Keep `geoid` and `puma` as strings — leading zeros matter.

The organizers' own dictionaries are in `raw/` (a CSV summary and the full Word
document). **Read the Word one before doing analysis**; the notes below are the
parts that most affect this project, not a replacement for it.

## What a row is

A **synthetic** household, built by fitting ACS tract totals with iterative
proportional fitting and sampling real PUMS households as donors.

Three consequences, straight from the dictionary:

1. **Rows are clones.** 55,218 distinct donors produced 1,171,123 rows.
   `drop_duplicates()` would silently delete most of the population. Never
   deduplicate.
2. **No row is a real household.** Valid for distributions and geographic
   patterns. Never for claims about individual households.
3. **Group quarters are excluded** — military barracks, nursing homes, student
   housing, correctional facilities. In this county that is a real omission.

## The columns that drive this project

| column | meaning |
|---|---|
| `geoid` | 11-digit census tract, 2020 vintage. The join key for tract shapefiles. |
| `puma` | 5-digit PUMA. Coarser, useful when tract noise bites. |
| `hh_income` | Annual household income, 2024 dollars. Negatives floored to zero. |
| `housing_cost_month` | **Required** rent — HUD FY2024 Small Area FMR for the tract at the bedroom count the household's size implies. Not rent paid, not tenure-adjusted: an owner with a paid-off mortgage still gets an imputed market rent. |
| `childcare_cost_month` | Charged whenever children under 12 are present, regardless of whether any adult works. |
| `hlb_year` | Gross annual income required to afford the budget. |
| `hlb_taxes_year` | Tax on the *budget* income. **Threshold construction only** — not a household's tax bill. |
| `taxes_on_actual_income_year` | Tax on *actual* income. Use this for anything household-specific. |
| `economically_vulnerable` | 1 if `hh_income < hlb_year`. Gross vs gross, like-for-like. |

The two tax columns are different quantities and are **not** interchangeable.
`hlb_taxes_year` exceeds actual income entirely for 6.4% of households.

## What this data cannot do

**There is no time dimension.** No rent growth, no income growth, no trend.
Any "months until X" metric is not computable here. The project's original
runway metric was retired for exactly this reason.

## Derived files

`build_dataset.py` produces both, and neither should be hand-edited:

- **`tracts.csv`** — 727 tracts (5 dropped for holding under 100 households,
  as the dictionary advises before ranking or mapping), with baseline
  vulnerability and cost medians.
- **`grid.json`** — vulnerability rates at all 315 policy-lever combinations,
  computed exactly on all 1.17M households. Rates are per-million integers.

```bash
python build_dataset.py --validate
```

`--validate` reproduces the shipped `economically_vulnerable` flag and fails if
more than 5 households disagree. Currently exactly 1 does: it sits nine cents
from its threshold, where the published cost columns are rounded to cents but
the budget total is not. If that count ever grows, the model is wrong.

## Why a grid instead of a household sample

Shipping a sample to the browser and recomputing live was the first design and
it failed. Because rows are clones, a 24,000-row sample carries far fewer
independent households than its size implies, and the county rate swung about
±1.5pp on the random seed alone — measured across five seeds. Precomputing
every combination exactly removes the question entirely.
