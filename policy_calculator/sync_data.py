"""
Regenerate the data block inside prototype.html from data/zips.csv.

The CSV is the single source of truth. The HTML embeds its own copy because a
page opened over file:// cannot fetch a sibling file (browsers block it), so
that copy has to be generated rather than fetched.

    python sync_data.py            # regenerate, keep the PLACEHOLDER banner
    python sync_data.py --real     # regenerate and mark the data as measured
    python sync_data.py --check    # exit 1 if the HTML is out of date

Use --real only once the numbers actually come from the project's dataset.
It flips the page's banner from a warning to a "live data" note, so it is the
one flag that changes what we are claiming to judges.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CSV_PATH = HERE / ".." / "data" / "zips.csv"
HTML_PATH = HERE / "prototype.html"

BLOCK_RE = re.compile(
    r"(/\* BEGIN GENERATED DATA \*/\n).*?(\n  /\* END GENERATED DATA \*/)",
    re.DOTALL,
)

TRUTHY = {"true", "1", "yes", "y", "t"}


def js_str(value: str) -> str:
    """Quote a string for embedding in JS source."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def js_rate(value: float) -> str:
    """Render a rate the way the hand-written block did: .055 rather than 0.055."""
    text = f"{value:.4f}".rstrip("0")
    return text[1:] if text.startswith("0.") else text


def load_rows() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"error: {CSV_PATH} has no data rows")

    required = {"zip", "median_income", "median_rent", "rent_growth_rate", "income_growth_rate"}
    missing = required - set(rows[0])
    if missing:
        sys.exit(f"error: {CSV_PATH} is missing required columns: {', '.join(sorted(missing))}")
    return rows


def build_block(rows: list[dict], placeholder: bool) -> str:
    # Pad the zip/area fields so the generated source stays scannable by eye.
    areas = [r.get("area") or r["zip"] for r in rows]
    area_w = max(len(js_str(a)) for a in areas) + 1

    lines = []
    for row, area in zip(rows, areas):
        featured = str(row.get("featured", "")).strip().lower() in TRUTHY
        lines.append(
            "    {{ zip:{zip}, area:{area:<{aw}} income:{inc:<8} rent:{rent:<6} "
            "rentG:{rg:<6} incG:{ig:<6} featured:{feat} }}".format(
                zip=js_str(row["zip"]),
                area=js_str(area) + ",",
                aw=area_w,
                inc=str(int(float(row["median_income"]))) + ",",
                rent=str(int(float(row["median_rent"]))) + ",",
                rg=js_rate(float(row["rent_growth_rate"])) + ",",
                ig=js_rate(float(row["income_growth_rate"])) + ",",
                feat="true" if featured else "false",
            )
        )

    return (
        "  var ZIPS = [\n"
        + ",\n".join(lines)
        + "\n  ];\n"
        + f"  var DATA_IS_PLACEHOLDER = {'true' if placeholder else 'false'};"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true",
                        help="mark the data as measured (flips the page's provenance banner)")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if prototype.html is out of date; write nothing")
    args = parser.parse_args()

    rows = load_rows()
    html = HTML_PATH.read_text(encoding="utf-8")

    if not BLOCK_RE.search(html):
        sys.exit("error: could not find the BEGIN/END GENERATED DATA markers in prototype.html")

    placeholder = not args.real
    if args.check:
        # Preserve whatever the file already claims, so --check tests the rows
        # rather than failing purely on the banner flag.
        placeholder = "var DATA_IS_PLACEHOLDER = true;" in html

    block = build_block(rows, placeholder)
    updated = BLOCK_RE.sub(lambda m: m.group(1) + block + m.group(2), html)

    if args.check:
        if updated != html:
            print("prototype.html is out of date — run: python sync_data.py")
            sys.exit(1)
        print(f"prototype.html is in sync with {len(rows)} rows from zips.csv")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    status = "PLACEHOLDER" if placeholder else "LIVE DATA"
    print(f"Synced {len(rows)} ZIPs into prototype.html  (banner: {status})")
    if not placeholder:
        print("Provenance banner now claims measured data — make sure that is true.")


if __name__ == "__main__":
    main()
