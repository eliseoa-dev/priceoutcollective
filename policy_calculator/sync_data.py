"""
Inject data/grid.json into prototype.html's generated data block.

data/grid.json is the single source of truth. The page embeds its own copy
because a page opened over file:// cannot fetch a sibling file, so that copy
has to be generated rather than fetched — and then guarded, or the two drift
and the demo shows numbers that no longer match the pipeline.

    python sync_data.py          # regenerate the embedded block
    python sync_data.py --check  # exit 1 if the page is out of date (CI runs this)

Regenerate grid.json first with:  cd ../data && python build_dataset.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
GRID_PATH = HERE / ".." / "data" / "grid.json"
HTML_PATH = HERE / "prototype.html"

BLOCK_RE = re.compile(
    r"(/\* BEGIN GENERATED DATA \*/\n).*?(\n/\* END GENERATED DATA \*/)",
    re.DOTALL,
)

REQUIRED_KEYS = {
    "population", "wageSteps", "capSteps", "careSteps",
    "county", "countyKids", "tracts", "tractRates", "budget",
}


def load_grid() -> dict:
    if not GRID_PATH.exists():
        sys.exit(
            f"error: {GRID_PATH} not found.\n"
            "       Build it first: cd ../data && python build_dataset.py"
        )
    grid = json.loads(GRID_PATH.read_text())

    missing = REQUIRED_KEYS - set(grid)
    if missing:
        sys.exit(f"error: grid.json is missing key(s): {', '.join(sorted(missing))}")

    expected = len(grid["wageSteps"]) * len(grid["capSteps"]) * len(grid["careSteps"])
    for key in ("county", "countyKids", "tractRates"):
        if len(grid[key]) != expected:
            sys.exit(
                f"error: grid.json '{key}' has {len(grid[key])} entries, "
                f"expected {expected} (one per lever combination)."
            )
    for row in grid["tractRates"]:
        if len(row) != len(grid["tracts"]):
            sys.exit("error: a tractRates row does not match the number of tracts")

    return grid


def build_block(grid: dict) -> str:
    return "var GRID = " + json.dumps(grid, separators=(",", ":")) + ";"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if prototype.html is out of date; write nothing")
    args = ap.parse_args()

    grid = load_grid()
    html = HTML_PATH.read_text(encoding="utf-8")

    if not BLOCK_RE.search(html):
        sys.exit("error: BEGIN/END GENERATED DATA markers not found in prototype.html")

    updated = BLOCK_RE.sub(lambda m: m.group(1) + build_block(grid) + m.group(2), html)

    combos = len(grid["county"])
    if args.check:
        if updated != html:
            print("prototype.html is out of date.")
            print("Fix: cd policy_calculator && python sync_data.py")
            sys.exit(1)
        print(f"prototype.html is in sync ({combos} lever combinations, "
              f"{len(grid['tracts'])} tracts, {grid['population']:,} households)")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"Synced grid into prototype.html: {combos} lever combinations, "
          f"{len(grid['tracts'])} tracts, {grid['population']:,} households")


if __name__ == "__main__":
    main()
