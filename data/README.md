# data/zips.csv — shared schema

One row per San Diego ZIP code. This is the single shared input for both
the map and the policy calculator — don't change column names without
updating this file and pinging the team.

| column               | type  | meaning                                                                 |
|----------------------|-------|--------------------------------------------------------------------------|
| `zip`                | str   | 5-digit ZIP code                                                        |
| `median_income`      | float | median annual household income ($)                                     |
| `median_rent`        | float | median monthly rent ($)                                                |
| `rent_burden_pct`    | float | current rent burden, as a fraction (e.g. `0.34` = 34%), = 12*rent/income |
| `rent_growth_rate`   | float | annualized rent growth rate, as a fraction (e.g. `0.06` = 6%/yr)        |
| `income_growth_rate` | float | annualized income growth rate, as a fraction                            |
| `runway_months`      | float | months until rent burden crosses 50% of income, given current trends   |
| `featured`           | bool  | true for the 5-10 ZIPs called out on the map                           |

`data/zips.csv` currently contains **dummy placeholder rows** so the
calculator is runnable end-to-end. Swap in the real export whenever it's
ready — same column names, and everything downstream should just work.
