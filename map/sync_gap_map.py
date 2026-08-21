"""
Inject map/output/gap_map_data.json into gap_map.html's generated data block.

Same reasoning as policy_calculator/sync_data.py: a page opened over file://
cannot fetch a sibling file, so it embeds its own copy, generated here rather
than fetched -- and guarded, so the page and the data cannot drift apart.

    python sync_gap_map.py          # regenerate the embedded block
    python sync_gap_map.py --check  # exit 1 if the page is out of date

Regenerate map/output/gap_map_data.json first with:
    python src/build_boundaries.py   # only needed once, or if boundaries change
    python build_gap_map_data.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
DATA_PATH = HERE / "output" / "gap_map_data.json"
HTML_PATH = HERE / "gap_map.html"

BLOCK_RE = re.compile(
    r"(/\* BEGIN GENERATED DATA \*/\nvar GAP = ).*?(;\n/\* END GENERATED DATA \*/)",
    re.DOTALL,
)

REQUIRED_KEYS = {"note", "county", "minVulnerableForFullConfidence", "tracts"}
REQUIRED_TRACT_KEYS = {
    "geoid", "puma", "pumaName", "households", "medianIncome",
    "vulnerableRate", "vulnerableHouseholds", "bahProfile", "lowConfidence",
    "balanceSheet", "geometry",
}


def load_data() -> dict:
    if not DATA_PATH.exists():
        sys.exit(
            f"error: {DATA_PATH} not found.\n"
            "       Build it first: python src/build_boundaries.py && python build_gap_map_data.py"
        )
    data = json.loads(DATA_PATH.read_text())

    missing = REQUIRED_KEYS - set(data)
    if missing:
        sys.exit(f"error: gap_map_data.json is missing key(s): {', '.join(sorted(missing))}")
    if len(data["tracts"]) != 727:
        sys.exit(f"error: gap_map_data.json has {len(data['tracts'])} tracts, expected the 727 reliable tracts")

    for t in data["tracts"]:
        missing = REQUIRED_TRACT_KEYS - set(t)
        if missing:
            sys.exit(f"error: tract {t.get('geoid', '?')} is missing key(s): {', '.join(sorted(missing))}")
        if not t["geometry"] or not t["geometry"].get("coordinates"):
            sys.exit(f"error: tract {t['geoid']} has no boundary geometry")

    # The balance sheet must add up on screen, county-wide and per tract.
    def check_ledger(sheet: dict, label: str) -> None:
        if sheet.get("costMonth") is None:
            return
        comp_sum = sum(c["amount"] for c in sheet["components"])
        if comp_sum != sheet["costMonth"]:
            sys.exit(f"error: {label} balance sheet components do not sum to costMonth")
        if sheet["requiredMonth"] != sheet["costMonth"] + sheet["taxMonth"]:
            sys.exit(f"error: {label} requiredMonth does not equal costMonth + taxMonth")

    check_ledger(data["county"], "county")
    for t in data["tracts"]:
        check_ledger(t["balanceSheet"], f"tract {t['geoid']}")

    return data


def build_block(data: dict) -> str:
    # BLOCK_RE's captured groups already include "var GAP = " and the
    # trailing ";" -- returning bare JSON here avoids doubling either.
    return json.dumps(data, separators=(",", ":"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if gap_map.html is out of date; write nothing")
    args = ap.parse_args()

    data = load_data()
    html = HTML_PATH.read_text(encoding="utf-8")

    if not BLOCK_RE.search(html):
        sys.exit("error: BEGIN/END GENERATED DATA markers not found in gap_map.html")

    updated = BLOCK_RE.sub(lambda m: m.group(1) + build_block(data) + m.group(2), html)

    if args.check:
        if updated != html:
            print("gap_map.html is out of date.")
            print("Fix: cd map && python sync_gap_map.py")
            sys.exit(1)
        print(f"gap_map.html is in sync ({len(data['tracts'])} tracts)")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"Synced gap_map_data.json into gap_map.html ({len(data['tracts'])} tracts)")


if __name__ == "__main__":
    main()
