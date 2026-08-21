"""
Inject data/wage_distance.json into wage_distance.html's generated data block.

Same reasoning as sync_data.py: a page opened over file:// cannot fetch a
sibling file, so the page embeds its own copy of the data, generated here
rather than fetched — and guarded, so the page and data/wage_distance.json
cannot drift apart.

    python sync_wage_distance.py          # regenerate the embedded block
    python sync_wage_distance.py --check  # exit 1 if the page is out of date

Regenerate data/wage_distance.json first with: python wage_distance_analysis.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
DATA_PATH = HERE / ".." / "data" / "wage_distance.json"
HTML_PATH = HERE / "wage_distance.html"

BLOCK_RE = re.compile(
    r"(/\* BEGIN GENERATED DATA \*/\nvar WD = ).*?(;\n/\* END GENERATED DATA \*/)",
    re.DOTALL,
)

REQUIRED_KEYS = {
    "vulnerableHouseholds", "zeroIncomeHouseholds", "zeroIncomeShare",
    "buckets", "percentiles", "withinCalculatorSliderRange",
    "byComposition", "byIncomeBand", "crossCheckVsGrid",
}

REQUIRED_BUCKETS = {"zero_income", "0-10%", "10-25%", "25-50%", "50-100%", "100%+"}
REQUIRED_PERCENTILES = {"p10", "p25", "p50", "p75", "p90", "p95", "p99"}


def load_data() -> dict:
    if not DATA_PATH.exists():
        sys.exit(
            f"error: {DATA_PATH} not found.\n"
            "       Build it first: python wage_distance_analysis.py"
        )
    data = json.loads(DATA_PATH.read_text())

    missing = REQUIRED_KEYS - set(data)
    if missing:
        sys.exit(f"error: wage_distance.json is missing key(s): {', '.join(sorted(missing))}")

    if set(data["buckets"]) != REQUIRED_BUCKETS:
        sys.exit("error: wage_distance.json 'buckets' does not match the six buckets the page expects")
    if set(data["percentiles"]) != REQUIRED_PERCENTILES:
        sys.exit("error: wage_distance.json 'percentiles' does not match the page's percentile ladder")
    if sum(data["buckets"].values()) != data["vulnerableHouseholds"]:
        sys.exit("error: buckets do not sum to vulnerableHouseholds — the chart would not add up to the total")

    max_diff = max((r["diff"] for r in data["crossCheckVsGrid"]), default=0)
    if max_diff > 5:
        sys.exit(
            f"error: cross-check against grid.json disagrees by {max_diff} households, "
            "beyond the project's documented 5-household rounding tolerance. "
            "Rebuild both data/grid.json and data/wage_distance.json before shipping."
        )

    return data


def build_block(data: dict) -> str:
    # BLOCK_RE's captured groups already include "var WD = " and the
    # trailing ";" -- returning bare JSON here avoids doubling either.
    return json.dumps(data, separators=(",", ":"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if wage_distance.html is out of date; write nothing")
    args = ap.parse_args()

    data = load_data()
    html = HTML_PATH.read_text(encoding="utf-8")

    if not BLOCK_RE.search(html):
        sys.exit("error: BEGIN/END GENERATED DATA markers not found in wage_distance.html")

    updated = BLOCK_RE.sub(lambda m: m.group(1) + build_block(data) + m.group(2), html)

    if args.check:
        if updated != html:
            print("wage_distance.html is out of date.")
            print("Fix: cd policy_calculator && python sync_wage_distance.py")
            sys.exit(1)
        print(f"wage_distance.html is in sync ({data['vulnerableHouseholds']:,} households below budget)")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"Synced wage_distance.json into wage_distance.html "
          f"({data['vulnerableHouseholds']:,} households below budget)")


if __name__ == "__main__":
    main()
