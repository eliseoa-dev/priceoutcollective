# map/

The tract-level risk map: where San Diego households fall below their
Household Living Budget, shown on an interactive choropleth with eight
hand-picked tracts called out by name and category ("already priced out,"
"on the edge," "stable baseline"). Answers *who is at risk, and where*.

**Live demo:** https://priceout-collective.surge.sh

## Config-driven — the point of this piece

`config/sd_hlb_2024.yaml` maps this dataset's raw column names onto a
canonical schema (`geo_id`, `income_measure`, `need_measure`,
`vulnerable_flag`, ...). Everything downstream — `adapter.py`,
`aggregate.py`, `build_map.py` — reads only the canonical names, never the
raw dataset's own column names.

**To point this pipeline at a different dataset, write a new YAML config.
No code changes.** The config declares the source file path, which columns
to load (`usecols`, to bound memory on a 1.17M-row file), the geography key,
and the minimum sample size below which a tract gets dropped before ranking.

## How to run

```bash
cd map
pip install -r requirements.txt
python src/build_boundaries.py   # downloads Census TIGER tract boundaries -> data/tracts_06073.geojson (gitignored, ~1-2 min)
python src/aggregate.py          # data/raw/*.csv.gz -> output/geo_metrics.csv (727 tracts)
python src/select_featured.py    # geo_metrics.csv -> output/featured_tracts.csv (8 tracts, 3 categories)
python src/build_map.py          # -> output/sd_affordability_map.html (standalone, opens in any browser)
```

`aggregate.py` reads straight from the shared
`data/raw/san_diego_ca_hlb_hackathon_2024.csv.gz` — no private copy of the
raw data lives in this folder.

## What's committed vs. regenerated

| File | Committed? | Why |
|---|---|---|
| `output/geo_metrics.csv` | yes | small, and the map's actual data layer |
| `output/featured_tracts_named.csv` | yes | `select_featured.py`'s 8-tract pick, plus a `neighborhood_name` column added via a one-off lookup against SANDAG's community planning boundaries and Census TIGER place boundaries (not yet an automated step — see below) |
| `output/sd_affordability_map.html` | yes | the actual deliverable — fully standalone, no server needed |
| `output/featured_tracts.csv` | no | `select_featured.py`'s raw (unnamed) output; regenerate by running it |
| `data/tracts_06073.geojson`, `data/tl_2020_06_tract/` | no | large and trivially regenerable from `build_boundaries.py`; gitignored |

**Known gap:** if you re-run `select_featured.py` after changing the
featured-tract selection logic, `featured_tracts_named.csv` needs its
`neighborhood_name` column re-added by hand (point-in-polygon lookup against
SANDAG's `Community_Plan_SD.geojson` and Census TIGER `tl_2020_06_place`
boundaries) — that lookup isn't wired into the pipeline yet.

## Note on `data/tracts.csv`

`data/tracts.csv` (the shared aggregation, described in the root README and
`data/README.md`) computes a similar per-tract vulnerability rate
independently, and the numbers cross-check closely where tracts overlap
(e.g. `06073009510`: 87.4% both ways). Two independent pipelines converging
on the same number is good validation, but it's also duplicated work worth
reconciling — worth a team conversation on whether `map/` should read
`data/tracts.csv` directly instead of maintaining its own
`config/`-driven aggregation. Keeping the separate pipeline for now because
the config-driven adapter pattern is the reusable part of this
contribution — happy to fold it into `data/build_dataset.py` instead if the
team prefers one aggregation path.

## Caveats worth knowing before presenting this

- **"La Jolla" by ZIP (92037) includes UCSD student housing.** A few tracts
  in that ZIP show unusually low coverage — almost certainly grad/undergrad
  housing, not the wealthy neighborhood the name evokes colloquially.
- The featured "priced out" and border-area rural tracts were checked for
  thin-sample artifacts; all featured tracts have 700+ households.
- The standalone HTML embeds all data but still loads its basemap tiles
  (CartoDB Positron) from a CDN — it needs internet to render the street/
  coastline background, though the data layer itself would still render on
  a blank background offline.
