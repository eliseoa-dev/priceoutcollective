# data/zips.csv — shared schema

One row per San Diego ZIP code. This is the single shared input for both
the map and the policy calculator — don't change column names without
updating this file and pinging the team.

| column               | type  | meaning                                                                 |
|----------------------|-------|--------------------------------------------------------------------------|
| `zip`                | str   | 5-digit ZIP code                                                        |
| `area`               | str   | neighborhood name, for chart labels (optional — falls back to `zip`)    |
| `median_income`      | float | median annual household income ($)                                     |
| `median_rent`        | float | median monthly rent ($)                                                |
| `rent_burden_pct`    | float | current rent burden, as a fraction (e.g. `0.34` = 34%), = 12*rent/income |
| `rent_growth_rate`   | float | annualized rent growth rate, as a fraction (e.g. `0.06` = 6%/yr)        |
| `income_growth_rate` | float | annualized income growth rate, as a fraction                            |
| `runway_months`      | float | months until rent burden crosses 50% of income, given current trends   |
| `featured`           | bool  | true for the 5-10 ZIPs called out on the map                           |

## ⚠️ Current contents are placeholder data

`data/zips.csv` currently contains **illustrative stand-in rows, not measured
figures.** They are plausible for San Diego and internally consistent, but they
have not been pulled from ACS or any other source. They exist so the calculator
runs end-to-end today.

Swap in the real export whenever it's ready — same column names — and
everything downstream updates with no other change. **Do not present these
numbers to judges as real.** Both the Python output and the HTML prototype
label them as placeholder; keep that labeling until the real data lands.
