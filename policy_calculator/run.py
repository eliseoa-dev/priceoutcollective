"""
Run the "what would help" policy calculator.

    python run.py [--csv ../data/zips.csv] [--featured-only] [--cap N]

Outputs (into ../outputs/):
    policy_runway_table.csv   before/after runway per ZIP per scenario
    policy_runway_chart.png   grouped bar chart, runway today vs. each scenario
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from scenarios import DEFAULT_SCENARIOS, evaluate, runway_months

HERE = Path(__file__).parent
DEFAULT_CSV = HERE / ".." / "data" / "zips.csv"
OUTPUT_DIR = HERE / ".." / "outputs"

# Runway "None" (never crosses 50%) is capped at this many months purely
# for charting/table display — doesn't affect the underlying math.
DISPLAY_CAP_MONTHS = 240


def display_runway(months: float | None) -> float:
    return DISPLAY_CAP_MONTHS if months is None else round(months, 1)


def build_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        today = runway_months(
            row_dict["rent_burden_pct"], row_dict["rent_growth_rate"], row_dict["income_growth_rate"]
        )
        record = {"zip": row_dict["zip"], "runway_today": display_runway(today)}
        for scenario in DEFAULT_SCENARIOS:
            record[scenario.name] = display_runway(evaluate(row_dict, scenario))
        rows.append(record)
    return pd.DataFrame(rows)


def plot_table(table: pd.DataFrame, out_path: Path) -> None:
    scenario_cols = [c for c in table.columns if c not in ("zip", "runway_today")]
    cols = ["runway_today"] + scenario_cols
    x = range(len(table))
    width = 0.8 / len(cols)

    fig, ax = plt.subplots(figsize=(max(8, len(table) * 1.2), 5))
    for i, col in enumerate(cols):
        offsets = [xi + i * width for xi in x]
        ax.bar(offsets, table[col], width=width, label=col)

    ax.set_xticks([xi + width * (len(cols) - 1) / 2 for xi in x])
    ax.set_xticklabels(table["zip"], rotation=0)
    ax.set_ylabel("Runway (months)")
    ax.set_title("Runway today vs. under each policy scenario, by ZIP")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--featured-only", action="store_true", help="only chart/table the featured ZIPs")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    if args.featured_only and "featured" in df.columns:
        df = df[df["featured"].astype(str).str.lower().isin(["true", "1", "yes"])]

    OUTPUT_DIR.mkdir(exist_ok=True)
    table = build_table(df)

    table_path = OUTPUT_DIR / "policy_runway_table.csv"
    chart_path = OUTPUT_DIR / "policy_runway_chart.png"
    table.to_csv(table_path, index=False)
    plot_table(table, chart_path)

    print(table.to_string(index=False))
    print(f"\nWrote {table_path}")
    print(f"Wrote {chart_path}")


if __name__ == "__main__":
    main()
