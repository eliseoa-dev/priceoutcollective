# Claims ledger

Every number this project shows belongs to exactly one class. A judge should be able to
point at any figure and get an immediate answer to "where did that come from?"

| class | means | example |
|---|---|---|
| **DATASET RESULT** | computed directly from the organizers' HLB microdata | 520,257 households below their budget |
| **DERIVED RESULT** | computed by us from that microdata, with a stated definition | the 30%-rule × basic-needs 2×2 |
| **EXTERNAL POLICY DEFINITION** | a rule or limit published by a government body | HUD cost burden = >30% of income |
| **EXTERNAL MARKET CONTEXT** | an observed statistic from an outside source | BLS OEWS median wage $58,690 |
| **MODEL ESTIMATE** | output of a fitted model | *(none ship in this product)* |
| **POLICY SIMULATION** | our model's arithmetic under stated lever assumptions | 21,755 lifted by full childcare coverage |

`MODEL ESTIMATE` is deliberately empty. The classifier was removed; see
[`FINDINGS.md`](FINDINGS.md#the-model-we-removed).

---

## Headline figures

| figure | value | class | where it comes from |
|---|---|---|---|
| households in the county | 1,171,123 | DATASET RESULT | row count |
| below their budget | 520,257 (44.42%) | DATASET RESULT | `economically_vulnerable` |
| mean monthly shortfall | $4,009 | DATASET RESULT | mean(`hlb_year`−`hh_income`)/12 over the red |
| median monthly shortfall | $3,383 | DATASET RESULT | median of the same quantity |
| required income, mean | $8,701/mo | DATASET RESULT | mean(`hlb_year`)/12 over the red |
| housing share of the cost basket | 42.5% | DERIVED RESULT | $2,954 ÷ $6,943 |
| housing share of required income | 34.0% | DERIVED RESULT | $2,954 ÷ $8,701 |
| reliable tracts | 727 of 732 | DATASET RESULT | ≥100 households |
| county median household income | $106,198 | DATASET RESULT | median(`hh_income`) |

**Mean and median are never mixed in one column.** The balance sheet is all means so it
adds up on screen; the median is carried beside it and labelled. `build_dataset.py` and
`sync_data.py` both refuse to ship a grid where `required − earned ≠ short`.

---

## Banned language

Do not write, say, or put on a slide:

- ❌ "AI predicts poverty with 97% accuracy" — or any variant. The label is a published
  deterministic formula over public inputs; a four-line lookup gets 100.000000%.
- ❌ "Not metaphorically" / "actually in the red" — the budget is a **normative
  standard**, not observed spending. Nothing here is observed.
- ❌ "months until priced out", "runway", "on the current path", any rent or income
  trajectory — **the data has no time dimension.** It is a 2024 snapshot.
- ❌ "ZIP code" anything — geography is census tracts. There is no ZIP field.
- ❌ "would lift N households out of poverty" — say "under the model's assumptions,
  N households move above their budget line."
- ❌ any statement about an individual household — every row is synthetic.
- ❌ "this neighbourhood causes…" — a tract is where a household is, not why.
- ❌ quoting a tract rate to three digits — the donor-adjusted CI is ±3.1pp.
- ❌ describing the rent lever as "a housing voucher" without the caveat below.

## Required caveats

**On the rent lever.** It is voucher-*shaped*, not San Diego's voucher. It uses gross
rather than adjusted income; it is offered to every eligible household; and in the City
of San Diego the actual tenant contribution is not 30% — SDHC is a Moving to Work
agency, and under "Path to Success" work-able households pay the greater of 40% of
adjusted income or a minimum family contribution. Both county waiting lists are closed;
SDHC's closed with 82,848 applicants and nobody selected since August 2022, and it
assists roughly 1.3% of county households. Say "what a subsidy of this shape would do",
never "what vouchers would do".

**On the 45% housing+transportation benchmark.** It is not law. There is no official
combined threshold. Attribute to CNT (a nonprofit); HUD's Location Affordability Index
contains no threshold of any kind.

**On AMI.** Never compute tiers arithmetically. San Diego's published "50%" limit is
66.8% of AMI, and its "80%" limit exceeds the 4-person AMI. Use HUD's published table.

**On anything involving children.** Carry the organizers' ±18%.

**On tenure.** Say that housing cost is required rent, not rent paid, and that owners
receive an imputed market rent — before someone asks.
