from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AsylumParams:
    # --- Supported population: two stocks (awaiting initial decision + on appeal) ---
    # Failed-appeal cases are assumed deported fast enough to leave support immediately.
    awaiting_determination_start: float = 90_000   # Stock at start of projection (2025-26)
    on_appeal_start: float = 16_000                # ~Total 106k matches HO stats end-2024

    # Inflow to awaiting_determination. Calibrated with total_decisions_capacity
    # = 140,000, initial_grant_rate = 0.45, withdrawal_rate = 0.12, and
    # dispersal_capacity = 75,000, so that the hotel population just reaches
    # zero in FY 2028-29.
    new_arrivals_per_year: float = 85_000

    # --- Decision throughput: single caseworker pool split between initial and appeal work ---
    # Reallocation rule: if the appeal pool exceeds `appeal_target_months` of baseline appeal
    # flow, caseworker capacity shifts from initial toward appeals, up to `max_appeal_share`.
    total_decisions_capacity: float = 140_000      # total initial + appeal decisions per year
    baseline_appeal_share: float = 0.29            # baseline allocation to appeals (~45k of 155k)
    max_appeal_share: float = 0.50                 # ceiling when diverting capacity
    appeal_target_months: float = 12.0             # target months of appeal backlog before diverting

    initial_grant_rate: float = 0.45               # share granted on initial decision (recent avg ~40-47%)
    # Refusals (= initial decisions × (1 - initial_grant_rate)) flow into on_appeal.
    appeal_success_rate: float = 0.45              # share granted on appeal at First-tier Tribunal

    # Withdrawals: share of the awaiting-determination pool who withdraw each year
    # (return home, abscond, regularise status) — leave support without a decision.
    withdrawal_rate: float = 0.12

    # --- Accommodation: dispersal capacity used first, hotels soak up the residual ---
    dispersal_capacity: float = 75_000             # persons housed in dispersal/initial accommodation
    hotel_cost_per_night: float = 140.0            # £/person; 24-25 avg ~140 (158→119 trajectory)
    dispersal_cost_per_night: float = 22.0         # £/person; dispersal/initial accommodation

    # --- Non-accommodation RDEL: processing, legal, subsistence, transport, third-country ---
    processing_cost_per_case: float = 13_500.0     # £/case — applied to initial + appeal decisions
    cost_real_growth: float = 0.0                  # on top of GDP deflator


@dataclass
class PoliceParams:
    """Gross police spending for England & Wales (all funding sources).

    The projection covers the full police funding settlement, not just the HO's
    share. Funding is split between the HO Core Grant (residual), the police
    precept raised via council tax by PCCs, and other local income (specific
    grants, fees, reserves drawdown).
    """
    # Workforce & pay (whole force)
    workforce_fte: float = 148_000                 # England & Wales officer FTE
    avg_pay_per_fte: float = 48_000                # £, indicative
    on_costs_multiplier: float = 1.25              # pensions, NICs, overheads
    # Staff & PCSO pay bucket — gross across all funders, all on-costs included.
    # Sized so that gross + precept + other reconciles to historic 2024-25 HO outturn.
    staff_pay_gross: float = 2_600.0               # £m
    staff_pay_real_growth: float = 0.0
    # Non-pay — gross across all funders (tech, estates, transport, CT, NCA grants etc.)
    non_pay_gross: float = 6_500.0                 # £m
    non_pay_real_growth: float = 0.0
    # Funding sources (2025-26 £m real)
    precept_income: float = 5_400.0                # raised via council tax precept
    precept_nominal_growth: float = 0.05           # nominal growth p.a. (council tax cap + base)
    other_income: float = 1_100.0                  # specific grants, fees, reserves
    other_income_real_growth: float = 0.0
    # Year-on-year assumptions
    workforce_growth_per_year: float = 0.0
    # Optional phase-in cap: if set (e.g. "2028-29"), workforce growth applies
    # through that financial year and then plateaus. Use this for "+N% over K
    # years then hold" policy scenarios. None = grow forever.
    workforce_growth_end_year: str | None = None
    real_pay_award_per_year: float = 0.01    # 1% real pay award p.a. (baseline)


@dataclass
class BordersParams:
    # Border Force workforce & pay
    border_force_fte: float = 9_500
    border_force_pay_per_fte: float = 42_000
    border_force_on_costs: float = 1.25
    border_force_workforce_growth: float = 0.0     # FTE growth p.a.
    border_force_pay_real_growth: float = 0.01     # real pay award p.a.
    # Border Force non-pay (equipment, ops); scales with passenger volume
    border_force_non_pay: float = 700.0            # £m (2025-26 real)
    border_force_non_pay_real_growth: float = 0.0
    passenger_volume_index: float = 1.0            # 1.0 = baseline
    # UKVI — gross RDEL netted against fee income
    ukvi_gross_rdel: float = 1_600.0               # £m (2025-26 real)
    ukvi_gross_real_growth: float = 0.0            # real growth in gross UKVI RDEL
    ukvi_fee_income: float = 900.0                 # £m visa fees (offset; 2025-26 real)
    fee_real_growth: float = 0.0                   # real growth in fee income


@dataclass
class BorderSecurityCommandParams:
    baseline_rdel_2025_26: float = 100.0           # £m — indicative; replace with MEM
    plus_by_2028_29: float = 280.0                 # SR25: +£280m RDEL by 2028-29
    profile: str = "linear"                        # "linear" | "backloaded"


@dataclass
class OtherAreasParams:
    homeland_security_baseline: float = 800.0      # £m real 2025-26
    homeland_security_real_growth: float = 0.0
    crime_fire_drugs_baseline: float = 450.0       # £m real 2025-26 (excl. fire & rescue transferred to MHCLG in 2022)
    crime_fire_drugs_real_growth: float = -0.01
    # Admin trajectory from SR25 (nominal £m)
    corporate_admin_by_year: dict = field(
        default_factory=lambda: {
            "2025-26": 482.0,
            "2026-27": 474.0,
            "2027-28": 466.0,
            "2028-29": 458.0,
        }
    )
    # SR27 period: extrapolate admin at this real growth rate
    corporate_admin_real_growth_sr27: float = -0.02


@dataclass
class CDELParams:
    # Total CDEL is taken from the published SR25 envelope (nominal, deflated to
    # real) for years where it exists. For years beyond the envelope, CDEL grows
    # from the last envelope year at ``sr27_real_growth``.
    sr27_real_growth: float = 0.0
    # Area split (shares must sum to 1). Aligned with the historic PESA × default-
    # shares series so the 2024-25 → 2025-26 transition is continuous.
    split: dict = field(
        default_factory=lambda: {
            "asylum_support": 0.04,
            "borders_migration": 0.22,
            "border_security_command": 0.02,
            "police": 0.32,
            "homeland_security": 0.18,
            "crime_fire_drugs": 0.04,
            "corporate_admin": 0.18,
        }
    )
    # Fallback total if the SR25 envelope is not loaded (kept for robustness).
    total_cdel_2025_26_fallback: float = 1_543.0


@dataclass
class Scenario:
    name: str = "baseline"
    description: str = ""
    asylum: AsylumParams = field(default_factory=AsylumParams)
    police: PoliceParams = field(default_factory=PoliceParams)
    borders: BordersParams = field(default_factory=BordersParams)
    bsc: BorderSecurityCommandParams = field(default_factory=BorderSecurityCommandParams)
    other: OtherAreasParams = field(default_factory=OtherAreasParams)
    cdel: CDELParams = field(default_factory=CDELParams)


def high_asylum_inflows_scenario() -> Scenario:
    s = Scenario(
        name="high_asylum_inflows",
        description="Arrivals surge to 130k/yr; decision capacity, grant rate and other levers unchanged. Shows the pool backlog building under a demand shock.",
    )
    s.asylum.new_arrivals_per_year = 130_000
    return s


def high_asylum_grant_rate_scenario() -> Scenario:
    s = Scenario(
        name="high_asylum_grant_rate",
        description="Initial grant rate lifted to 70% (reflects a Syrian/Afghan-style grant cohort). Arrivals and capacity unchanged; fewer cases flow to appeal.",
    )
    s.asylum.initial_grant_rate = 0.70
    return s


def police_plus_10pct_scenario() -> Scenario:
    s = Scenario(
        name="police_plus_10pct",
        description="Police workforce +10% over 3 years then plateau (target ~162,800 FTE by end of 2028-29).",
    )
    # (1.10)^(1/3) − 1 ≈ 3.2280%, so 3 years of compounding delivers +10%.
    s.police.workforce_growth_per_year = 0.032280
    s.police.workforce_growth_end_year = "2028-29"
    return s
