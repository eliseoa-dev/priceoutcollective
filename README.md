# Priceout Collective

**Building for Good Hackathon — Affordability track**
Data Science Alliance @ UC San Diego (Halicioglu School of Data Science and Computing)

## The pitch

San Diego renters are being priced out. We're building a two-part story:

1. **The map** (`map/`) — a ZIP-code level view of San Diego showing which
   areas are most "at risk," using a **runway** metric: months until rent
   burden crosses 50% of income, based on current rent vs. income growth
   trends. This answers *"who's at risk?"*
2. **The policy calculator** (`policy_calculator/`) — takes the same
   per-ZIP data and recomputes runway under a few policy levers (minimum
   wage increase, rent stabilization, housing vouchers) to answer the
   judges' natural follow-up: *"okay, so what would actually fix it?"*

Both pieces read from one shared file: `data/zips.csv`. See
`data/README.md` for the schema. Nobody needs to touch anyone else's code —
build against the CSV.

## Repo layout

```
data/                shared input data (zips.csv) + schema docs
map/                 the risk map (runway-by-ZIP)
policy_calculator/   "what would help" scenario calculator
outputs/             generated charts/tables (gitignored except .gitkeep)
```

## Team workflow

We're working as a group in this repo — everyone forks or branches, opens
a PR, and we merge into `main`. See `CONTRIBUTING.md` for the exact steps.

- **Team leads / registration:** Shereen Shirazi, Dr. Adir, Ryan Lopez
- **Challenge track:** Affordability
- Lock in scope early — each sub-piece should be self-contained enough to
  demo independently, then we slot them together for the joint rehearsal.

## Demo flow (tentative)

1. Map: which ZIPs are running out of runway, and how fast.
2. Calculator: here's what buys that runway back (bar chart / table,
   before vs. after, per policy lever).
3. Close: recommended next steps / ask.

Aim for ~1-2 min per section so the joint walkthrough stays tight.
