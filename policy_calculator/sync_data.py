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
    "population", "wageSteps", "capSteps", "careSteps", "eligSteps",
    "county", "countyKids", "tracts", "tractRates", "budget",
    "rentSubsidyCostMillions",
}

# The sliders index the step arrays directly, so each input's max attribute must be
# len(steps) - 1. These are hand-written in the HTML; if a step list changes and the
# max does not, the page silently indexes past the end of the grid and shows nothing.
SLIDER_MAX_RE = {
    "wage": (re.compile(r'id="wage"[^>]*?max="(\d+)"'), "wageSteps"),
    "cap": (re.compile(r'id="cap"[^>]*?max="(\d+)"'), "capSteps"),
    "care": (re.compile(r'id="care"[^>]*?max="(\d+)"'), "careSteps"),
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

    expected = (len(grid["wageSteps"]) * len(grid["capSteps"])
                * len(grid["careSteps"]) * len(grid["eligSteps"]))
    for key in ("county", "countyKids", "tractRates", "rentSubsidyCostMillions"):
        if len(grid[key]) != expected:
            sys.exit(
                f"error: grid.json '{key}' has {len(grid[key])} entries, "
                f"expected {expected} (one per lever combination)."
            )
    for row in grid["tractRates"]:
        if len(row) != len(grid["tracts"]):
            sys.exit("error: a tractRates row does not match the number of tracts")

    # The balance sheet is rendered as a column a judge can add up. Refuse to ship
    # a grid whose ledger does not reconcile.
    b = grid["budget"]
    if b["requiredMonth"] - b["incomeMonth"] != b["meanShortfallMonth"]:
        sys.exit("error: grid.json budget ledger does not add up "
                 f"({b['requiredMonth']} - {b['incomeMonth']} != {b['meanShortfallMonth']})")
    if sum(c["amount"] for c in b["components"]) != b["costMonth"]:
        sys.exit("error: grid.json budget components do not sum to costMonth")

    return grid


def check_sliders(html: str, grid: dict) -> None:
    for name, (pattern, key) in SLIDER_MAX_RE.items():
        m = pattern.search(html)
        if not m:
            sys.exit(f"error: could not find the {name} slider's max attribute")
        want = len(grid[key]) - 1
        if int(m.group(1)) != want:
            sys.exit(f"error: slider '{name}' has max={m.group(1)} but {key} has "
                     f"{len(grid[key])} steps (max should be {want}). "
                     "The page would index past the end of the grid.")


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

    check_sliders(html, grid)

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
