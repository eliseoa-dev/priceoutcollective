# Handoff — audited policy calculator

**Branch:** `claude/cost-case-handoff`

This branch adds a judge-ready cost case without replacing the corrected model already
on `main`. The calculator evaluates all 945 combinations of wage, rent cap, childcare,
and rent-subsidy eligibility on all 1,171,123 synthetic households.

## What changed

- Exact scenario household counts remove rate-rounding errors from the interface.
- `publicCostM` combines annual rent-subsidy and childcare outlays.
- `wageCostM` reports additional wages separately because they are employer-borne.
- `remainingMedianIncome` describes the baseline income of households still short.
- The calculator uses the same eight named reference tracts as the map.
- A simple targeted package card shows both the result and who remains behind.

The grid order is wage → rent cap → childcare → eligibility. In JavaScript use
`idx(wageIndex, capIndex, careIndex, eligibilityIndex)`.

## Verified package case

The displayed package is a 25% income lift, rent payments capped at 30% of income
for households below 50% of county median income, and 50% childcare coverage.

- 139,773 households move above their living-budget line (26.9% of those initially short).
- Annual public outlay is $7.106 billion, or about $50,839 per household lifted.
- Additional annual wages are $41.407 billion and are not counted as public outlay.
- 380,484 households remain short; their median baseline income is $38,173.
- A universal 30%-of-income rent cap alone moves 72,741 households, 14.0% of the baseline group.

These are modeled counterfactuals, not forecasts or funding recommendations. No housing
supply, rent-price response, take-up, administrative cost, or behavioral response is modeled.

## Required checks

```bash
python data/build_dataset.py --validate
python policy_calculator/sync_data.py
python policy_calculator/sync_data.py --check
```

The baseline reconstruction differs from the organizer-provided flag for 1 of 1,171,123
households, within the documented five-household tolerance caused by cent-rounded inputs.
Budget tax is interpolated from each household-composition group's observed tax curve; it
is not scaled by a fixed effective-tax ratio and is not re-solved through TAXSIM.
