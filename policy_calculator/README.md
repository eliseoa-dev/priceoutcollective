# policy_calculator/

"What would help" — takes the shared per-ZIP data (`data/zips.csv`) and
recomputes the runway metric under a few policy levers, so we can show
before/after per ZIP.

## Scenarios (defaults, tweak in `scenarios.py`)

1. **Minimum wage +8%** — one-time income bump, growth trends unchanged.
2. **Rent stabilization (3%/yr cap)** — caps rent growth at the policy
   ceiling instead of the current trend.
3. **Housing voucher (50% of gap)** — covers half the gap between current
   rent burden and the 30% "affordable" line.

All three reuse the same runway formula the map uses — see the docstring
in `scenarios.py` for the exact math. **If the map's runway definition
differs from what's documented there, tell us — we'll line them up before
the joint rehearsal.**

## The demo piece: `prototype.html`

`prototype.html` is the thing to actually show. Open it in a browser — no
build step, no server, no dependencies. Three sliders (wage, rent cap,
voucher); every ZIP's runway recomputes live, before vs. after, with a
table view and a methodology section built in.

The data is embedded at the top of its `<script>` block in the same shape as
`data/zips.csv`. When the real export lands, paste the rows in there (and
into the CSV) and everything updates.

The Python path below produces the same numbers as a static chart + CSV, for
anyone who'd rather work in pandas.

## Run it

```bash
pip install -r requirements.txt
python run.py                 # all ZIPs
python run.py --featured-only # just the map's called-out ZIPs
```

Outputs land in `../outputs/`:
- `policy_runway_table.csv` — runway today vs. each scenario, per ZIP
- `policy_runway_chart.png` — grouped bar chart of the same

Ships with dummy data in `data/zips.csv` so this runs standalone right
now — swap in the real export whenever it's ready, same column names.

## Demo-ready sanity check

`runway_today` in the output table should roughly match the `runway_months`
column already in `data/zips.csv` (it's recomputed from `rent_burden_pct` /
growth rates independently, as a sanity check that the shared formula
lines up before we present).
