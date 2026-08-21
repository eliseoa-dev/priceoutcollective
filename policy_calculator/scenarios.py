"""
"What Would Help" policy calculator — core scenario math.

Runway model (must match the map's definition — see data/README.md):
Rent burden b(t), t months from now, given today's burden b0 and annualized
rent/income growth rates g_rent, g_income:

    b(t) = b0 * ((1 + g_rent) / (1 + g_income)) ** (t / 12)

Runway is the smallest t where b(t) = 0.50 (already-burdened ZIPs get
runway = 0; ZIPs where income grows at least as fast as rent never cross
50% and get runway = None, i.e. "no crossing").

Each policy scenario adjusts b0, g_rent, and/or g_income before the runway
is recomputed, so "before vs. after" is just the same formula run twice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

AFFORDABLE_BURDEN = 0.30  # HUD's standard "cost-burdened" threshold
CRISIS_BURDEN = 0.50      # the runway target used by the map


def runway_months(burden_pct: float, rent_growth: float, income_growth: float) -> float | None:
    """Months until burden_pct crosses CRISIS_BURDEN. None = never, given current trends."""
    if burden_pct >= CRISIS_BURDEN:
        return 0.0
    ratio = (1 + rent_growth) / (1 + income_growth)
    if ratio <= 1.0:
        return None
    return 12 * math.log(CRISIS_BURDEN / burden_pct) / math.log(ratio)


@dataclass
class Scenario:
    name: str
    description: str

    def apply(self, row: dict) -> dict:
        """Return adjusted (burden_pct, rent_growth, income_growth) for this row."""
        raise NotImplementedError


class MinimumWageIncrease(Scenario):
    """One-time bump to household income (e.g. +8% from a minimum wage hike),
    growth trends unchanged afterward."""

    def __init__(self, pct_increase: float):
        self.pct_increase = pct_increase
        super().__init__(
            name=f"Minimum wage +{pct_increase:.0%}",
            description=f"One-time {pct_increase:.0%} income bump, growth trends unchanged.",
        )

    def apply(self, row: dict) -> dict:
        new_burden = row["rent_burden_pct"] / (1 + self.pct_increase)
        return {
            "burden_pct": new_burden,
            "rent_growth": row["rent_growth_rate"],
            "income_growth": row["income_growth_rate"],
        }


class RentStabilization(Scenario):
    """Caps annual rent growth at a policy ceiling (only helps if current
    growth is already above the cap)."""

    def __init__(self, cap: float):
        self.cap = cap
        super().__init__(
            name=f"Rent stabilization ({cap:.0%}/yr cap)",
            description=f"Caps rent growth at {cap:.0%}/yr instead of the current trend.",
        )

    def apply(self, row: dict) -> dict:
        return {
            "burden_pct": row["rent_burden_pct"],
            "rent_growth": min(row["rent_growth_rate"], self.cap),
            "income_growth": row["income_growth_rate"],
        }


class HousingVoucher(Scenario):
    """Covers pct_of_gap of the gap between current burden and the 30%
    "affordable" threshold, effectively lowering today's burden."""

    def __init__(self, pct_of_gap: float):
        self.pct_of_gap = pct_of_gap
        super().__init__(
            name=f"Housing voucher ({pct_of_gap:.0%} of gap)",
            description=f"Covers {pct_of_gap:.0%} of the gap between current burden and the 30% affordability line.",
        )

    def apply(self, row: dict) -> dict:
        gap = max(row["rent_burden_pct"] - AFFORDABLE_BURDEN, 0.0)
        new_burden = row["rent_burden_pct"] - self.pct_of_gap * gap
        return {
            "burden_pct": new_burden,
            "rent_growth": row["rent_growth_rate"],
            "income_growth": row["income_growth_rate"],
        }


class AllThree(Scenario):
    """All three levers at once — the 'what would it actually take' close."""

    def __init__(self, pct_increase: float, cap: float, pct_of_gap: float):
        self.wage = MinimumWageIncrease(pct_increase)
        self.cap = RentStabilization(cap)
        self.voucher = HousingVoucher(pct_of_gap)
        super().__init__(
            name="All three combined",
            description="Wage bump, rent cap, and voucher applied together.",
        )

    def apply(self, row: dict) -> dict:
        # Voucher lowers the burden first, then the wage bump divides what's left;
        # the cap bends the growth trend independently.
        after_voucher = self.voucher.apply(row)["burden_pct"]
        return {
            "burden_pct": after_voucher / (1 + self.wage.pct_increase),
            "rent_growth": min(row["rent_growth_rate"], self.cap.cap),
            "income_growth": row["income_growth_rate"],
        }


DEFAULT_SCENARIOS = [
    MinimumWageIncrease(0.08),
    RentStabilization(0.03),
    HousingVoucher(0.50),
    AllThree(0.08, 0.03, 0.50),
]


def evaluate(row: dict, scenario: Scenario) -> float | None:
    adjusted = scenario.apply(row)
    return runway_months(adjusted["burden_pct"], adjusted["rent_growth"], adjusted["income_growth"])
