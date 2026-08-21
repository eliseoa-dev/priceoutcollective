# data/raw/ — source files, unmodified

Put the organizers' original dataset files here, exactly as downloaded. Don't
edit them. `data/ingest.py` reads from here and writes `data/zips.csv`, which
is what the map and the policy calculator actually consume.

Keeping the raw file committed means anyone can re-run the import, and we can
show a judge exactly how a source column became one of ours.

## Getting the Affordability dataset in here

The dataset lives in a Google Drive folder shared by the organizers
(`Affordability`, owned by adir@datasciencealliance.org).

**Heads up on a permissions gotcha:** the folder is shared, but the files
*inside* it were shared only by inheriting the folder — which means automated
tools that connect to Drive see the folder as empty. If you're scripting
against Drive and getting nothing back, that's why. Download through the
browser instead, or ask the organizers to share the files directly.

Steps:

1. Open the folder in your browser and download the file(s).
2. Drop them in this directory.
3. Look at what you got:
   ```bash
   cd data
   python ingest.py --inspect raw/<the-file>.csv
   ```
   It prints every column and which of our fields it maps to.
4. Import it:
   ```bash
   python ingest.py raw/<the-file>.csv
   ```
   For anything it couldn't map automatically, pass it explicitly:
   ```bash
   python ingest.py raw/<the-file>.csv --income-col 'Median HH Income' --area-col 'Community'
   ```
5. Regenerate the prototype's embedded copy and flip its banner to live data:
   ```bash
   cd ../policy_calculator
   python sync_data.py --real
   ```
6. Commit the raw file, `data/zips.csv`, and `prototype.html` together, so the
   source and the derived data never drift apart.

## What the importer handles for you

- `$1,900` and `5.5%` style formatting
- rates given either as `0.055` or as `5.5`
- ZIP columns named `ZCTA`, `ZCTA5`, `GEOID`, `zip_code`, …
- deriving `rent_burden_pct` as `(rent × 12) / income` when the source lacks it
- deriving `runway_months` from burden and the two growth rates
- picking the featured ZIPs (the N with least runway) when the source has no
  `featured` flag

## What it will warn you about

If the source has **no rent-growth or income-growth columns**, the importer
fills in a flat default for every ZIP and prints a warning. Every runway number
depends on those two rates, so a flat default makes the output a demonstration
of the method, not a finding. Find the real growth figures before presenting,
or say plainly that the rates are assumed.
