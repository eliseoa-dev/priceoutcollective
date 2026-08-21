# policy_calculator/

"What would actually help" — three policy levers, recomputed across all
1,171,123 San Diego households.

## The demo

Open **`prototype.html`** in a browser. No build step, no server, no
dependencies. Everything it needs is embedded.

Three levers:

1. **Wage floor** — raises every household's income by a set percentage.
2. **Rent ceiling** — a housing voucher: the household pays at most this share
   of income toward rent, `min(FMR, cap × income)`.
3. **Childcare subsidy** — covers this share of childcare cost.

## The point to make on stage

At +25% wages, a 30%-of-income rent cap, and a 50% childcare subsidy,
**193,555 households are lifted above their living budget** — 44.4% down to
27.9%. The unit chart shows that mass moving.

The sharper point is the childcare callout. Countywide, a 50% childcare
subsidy moves vulnerability by 0.8 points and looks like a rounding error.
Among the 21.7% of households with children under 12 — who start at 58%
vulnerable rather than 40.7% — it moves 3.9 points.

**A lever can look like nothing countywide and still be the right policy,
because the average hides who it reaches.** That is the close.

## How it stays honest

Nothing is estimated at display time. `data/build_dataset.py` evaluates every
one of the 315 lever combinations against all 1.17M households and writes exact
rates to `data/grid.json`; the sliders step through those precomputed settings.

The baseline count shown (520,257) is the organizers' own published figure, not
one re-derived from a rounded rate.

## Rebuilding

```bash
cd ../data && python build_dataset.py --validate
cd ../policy_calculator && python sync_data.py
```

`sync_data.py` regenerates the page's embedded copy of `grid.json`. CI runs
`python sync_data.py --check` and fails the build if the page and the pipeline
have drifted — so a stale demo cannot reach `main`.

## Standalone analysis scripts

Two scripts from `feature/ml-vulnerability-simulator`, both reading the shared
gzip directly. They need `pip install -r requirements.txt` (pandas, matplotlib,
scikit-learn, xgboost); `prototype.html` needs none of it.

**`ml_vulnerability_simulator.py`** — recomputes the HLB formula per household
under four policy scenarios. Independent of `data/build_dataset.py`, and the two
agree: both reproduce the shipped `economically_vulnerable` flag to 99.9999%
(one household in 1,171,123), and both put a 50% childcare subsidy at 43.58%.
Two implementations converging is worth more than either alone.

**`predictive_risk_model.py`** — predicts vulnerability from income, household
composition, and PUMA only, deliberately excluding the itemized cost columns
that define the label. 97.3% accuracy, 0.998 AUC.

Worth stating carefully when presenting it: this is not forecasting an
uncertain outcome. `economically_vulnerable` is a deterministic function of
costs, and costs are largely determined by household composition (food,
childcare, bedroom count) and geography (FMR, transport). So the model is
recovering a known formula from proxies, and the residual 2.7% is mostly PUMA
being coarser than tract. That makes it a legitimate finding — **who you are
and where you live nearly determine your need threshold** — rather than
evidence of predictive power over something genuinely unknown. Useful for
outreach screening, where a program has income and household size but not an
itemized budget.
