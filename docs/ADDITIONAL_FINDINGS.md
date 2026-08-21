# Additional Findings

Supplementary work from Kyaw Soe Lwin, written up here rather than folded into
[`FINDINGS.md`](FINDINGS.md). It sits outside the product's three demo tabs
(calculator, map, wage distance) and outside
[`CLAIMS_LEDGER.md`](CLAIMS_LEDGER.md)'s formal claim classes — nothing on this
page ships in the interface. Read it as exploratory analysis, not a product
surface.

---

## Part 1 — The predictive risk model

### The false start

First attempt: an XGBoost classifier predicting `economically_vulnerable`
directly from the household's own cost columns (housing, food, childcare,
transport, healthcare, broadband). It scored 99.6% accuracy, 0.9999 AUC.

The score was fake. `economically_vulnerable` is defined as
`hh_income < hlb_year`, and `hlb_year` **is** those same cost columns — summed,
multiplied by 12, and taxed. The model wasn't predicting risk; it was
reconstructing arithmetic it had already been handed as input. A four-line
formula reproduces the label at 100% with no learning involved. This is the
exact failure mode [`CLAIMS_LEDGER.md`](CLAIMS_LEDGER.md) bans language for
("AI predicts poverty with N% accuracy") — caught here before it shipped.

**Fix:** the classifier was dropped from that pipeline step entirely, replaced
with an exact-formula recompute. No ML where none is needed.

### The real model: leakage-free, intake-only

A second model was built to predict risk using only signals an outreach
program would actually have at intake — before ever seeing a household's
budget: income, household composition, and PUMA location. Every column that
feeds into `hlb_year` is excluded by construction, which is what makes this
leakage-free rather than a restatement of the label formula.

An ablation confirms each signal's incremental value:

| signals included | accuracy | AUC |
|---|---|---|
| income alone | 86% | 0.94 |
| + household composition | 95.7% | 0.994 |
| + PUMA location | 97.3% | 0.998 |

F1 0.969 with the full intake feature set. Household size is the dominant
driver — the framing that matters for a screening program: what it actually
has at intake is income, family size, and neighborhood, not a household's
budget worksheet.

*(Note: the email backing this write-up cites `predictive_risk_metrics.csv`
as the artifact these numbers reproduce from. That file was not found in the
repository at the time of writing — confirm it's committed, or regenerate it
from `policy_calculator/predictive_risk_model.py`, before citing F1 0.969
anywhere the way `wage_distance.json` backs the wage-distance numbers.)*

### What happened to this model next

This is the same model, evaluated further by a teammate later the same day
and retired from the product. See
[`FINDINGS.md` — "The model we removed"](FINDINGS.md#the-model-we-removed)
for the full writeup; in short:

- a **four-line median lookup beats it on every seed** under group-aware
  validation — there is nothing here a formula doesn't already do better;
- it sits **0.17pp below the provable Bayes ceiling** for its own feature set;
- on the **contested 15.6% of households actually near the line** — where a
  screener's judgment would matter — accuracy drops to **81.9%**;
- its **false-negative rate varies 12.9× across PUMAs**, in a model keyed on
  geography, with no protected characteristics in the data to test disparate
  impact against.

The leakage fix documented above is genuine and the reported numbers
reproduce exactly. The decision to keep it out of the product was made on
different grounds — a working, honest model that a simpler method beats, with
an unresolved fairness question a hackathon timeline couldn't answer. Both
things are true at once.

---

## Part 2 — The fourth lever: guaranteed income

**What it is.** A flat monthly cash transfer per household, targeted by
income eligibility. Two designs share one toggle:

- **Hard cutoff** at 50% of county median income (**$53,099**): a household
  either receives the full transfer or nothing.
- **Taper to $0** at the county median (**$106,198**): the transfer phases
  out linearly as income rises, reaching zero exactly at the median.

At $500/month:

| design | households moved above their budget line | annual public cost | share under $50,000 |
|---|---|---|---|
| hard cutoff at 50% AMI | 7,413 | $1.72B | 62.9% |
| taper to 0 at the median | 26,058 | $2.64B | 17.9% |

**The targeting-vs-reach tradeoff.** The cutoff concentrates the entire
transfer on the deepest shortfalls — nearly two-thirds of who it reaches earn
under $50,000. The taper reaches 3.5× more households at a lower cost per
household lifted, but most of that reach lands above $50,000, since a wider
income band qualifies for at least a partial transfer.

**Why this lever exists at all.** It is the only modeled lever that reaches
under-$50,000 households in meaningful numbers. Every cost-side lever in the
calculator — childcare, healthcare, transit, rent — moves under 5% of
under-$50k households above their line, because those households are short by
more than any single cost category can cover. This is the same conclusion the
project's own primary finding reaches from the other direction: a 100%
childcare subsidy lifts **zero** households earning under $50,000 (see
[`FINDINGS.md` — Primary finding](FINDINGS.md#primary-finding)). Guaranteed
income is the one lever shaped to reach the population every other lever
misses.

**Scope, if asked.** Transfer amounts $250–$1,000/month were modeled, each
evaluated exactly on all 1,171,123 households (not sampled), and
cross-validated against a fresh computation — the same "two independent code
paths must agree" bar the rest of this project holds a number to before it
ships.

---

— Kyaw Soe Lwin
