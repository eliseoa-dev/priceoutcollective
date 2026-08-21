# One Raise Away

Story-first dashboard for the Affordability track: housed is not the same as safe.

Open `index.html` (static — no build, no server; any static host works, or `python3 -m http.server` in this folder).

- **Story** — the headline numbers and the mechanism: fixed income, subsidy set at move-in, rent rises, nobody watching.
- **The cliff** — working model. Slide rent 0–50%; every one of the 1,171,123 households is re-tested against its own living budget, per tract, for four lenses (all / living alone / with kids / retiree on Social Security).
- **Early signal** — storage lien-auction listings in San Diego County by ZIP (storagetreasures.com, 2026-06-12 → 2026-07-02) over the same map, plus the Downtown San Diego Partnership unsheltered count 2017–2025.
- **The ask** — four actionable proposals with evidence, and the full sources / methods / limits.
- **Snap the notice** — photograph a rent-increase letter; EyePop.ai text recognition pulls the new rent into the model (paste a Pop ID + API key in-app; the typed-text path works without one).

Model: a household is under its budget after a raise of r% when `hh_income < hlb_year + 12 · housing_cost_month · r · 1.2 · (1 + hlb_taxes_year / hlb_no_tax_year)`. Precomputed per tract at nine raise levels; `data.js` holds the aggregates (no household-level rows).
