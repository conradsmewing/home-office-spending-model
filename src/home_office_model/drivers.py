"""Driver-based projections for each Home Office programme area.

Each ``project_*_real`` function returns a Series indexed by financial year,
in real £ million at the model base year (2025-26) prices. The orchestrator
in ``projections.py`` converts to nominal where needed.
"""
from __future__ import annotations

import pandas as pd

from .config import BASE_YEAR, PROJECTION_YEARS, SR25_YEARS
from .scenarios import Scenario

DAYS_PER_YEAR = 365.25


def _years_from_base(years: list[str]) -> list[int]:
    """Integer offset from the base year for each projection year."""
    base = int(BASE_YEAR[:4])
    return [int(y[:4]) - base for y in years]


def _appeal_capacity_share(a, on_appeal: float) -> float:
    """Reallocation rule: divert caseworker capacity toward appeals when the
    appeal pool exceeds `appeal_target_months` of baseline appeal flow.
    Linearly ramps from baseline to max share as the overshoot grows.
    """
    baseline_flow = a.total_decisions_capacity * a.baseline_appeal_share
    if baseline_flow <= 0:
        return a.baseline_appeal_share
    current_months = on_appeal * 12.0 / baseline_flow
    if current_months <= a.appeal_target_months:
        return a.baseline_appeal_share
    overshoot = min(1.0, (current_months - a.appeal_target_months) / a.appeal_target_months)
    return a.baseline_appeal_share + overshoot * (a.max_appeal_share - a.baseline_appeal_share)


def _step_asylum(a, awaiting: float, on_appeal: float) -> dict:
    """Advance the two pools one year. Order: arrivals → withdrawals → capacity
    allocation → initial decisions → appeal decisions. Returns realised flows
    plus updated stocks so the caller can trace or cost them."""
    arrivals = a.new_arrivals_per_year
    awaiting_after_arr = awaiting + arrivals

    # Withdrawals leak from the awaiting pool (applied to start-of-year stock).
    withdrawals = awaiting * a.withdrawal_rate
    awaiting_post_wd = max(0.0, awaiting_after_arr - withdrawals)

    # Capacity split is decided from the pool at start of year.
    appeal_share = _appeal_capacity_share(a, on_appeal)
    appeal_capacity = a.total_decisions_capacity * appeal_share
    initial_capacity = a.total_decisions_capacity * (1 - appeal_share)

    # Initial decisions cannot exceed available awaiting stock.
    initial_decisions = min(initial_capacity, awaiting_post_wd)
    initial_granted = initial_decisions * a.initial_grant_rate
    initial_refused = initial_decisions * (1 - a.initial_grant_rate)
    new_awaiting = max(0.0, awaiting_post_wd - initial_decisions)

    # Appeals decided from pool + new refusals entering this year.
    appeals_decided = min(appeal_capacity, on_appeal + initial_refused)
    appeals_granted = appeals_decided * a.appeal_success_rate
    appeals_refused = appeals_decided * (1 - a.appeal_success_rate)
    new_on_appeal = max(0.0, on_appeal + initial_refused - appeals_decided)

    return {
        "arrivals": arrivals,
        "withdrawals": withdrawals,
        "appeal_share": appeal_share,
        "initial_capacity": initial_capacity,
        "appeal_capacity": appeal_capacity,
        "initial_decisions": initial_decisions,
        "initial_granted": initial_granted,
        "initial_refused": initial_refused,
        "appeals_decided": appeals_decided,
        "appeals_granted": appeals_granted,
        "appeals_refused": appeals_refused,
        "awaiting_end": new_awaiting,
        "on_appeal_end": new_on_appeal,
    }


def project_asylum_real(scenario: Scenario, years: list[str] = PROJECTION_YEARS) -> pd.Series:
    """Two-stock projection (awaiting determination + on appeal), then cost from the total.

    Each year:
        awaiting:  + arrivals, − withdrawals, − initial decisions
        on_appeal: + initial refusals, − appeal decisions  (both wins and losses leave)

    Caseworker capacity is a single pool split between initial and appeal work; the
    split shifts toward appeals when the appeal backlog exceeds a target in months
    of baseline flow. Accommodation: dispersal capacity is filled first, residual
    population sits in hotels (so marginal cost = hotel £/night until hotels empty).
    """
    a = scenario.asylum
    offsets = _years_from_base(years)
    out = {}
    awaiting = float(a.awaiting_determination_start)
    on_appeal = float(a.on_appeal_start)
    for yr, t in zip(years, offsets):
        pop_start = awaiting + on_appeal
        step = _step_asylum(a, awaiting, on_appeal)
        awaiting, on_appeal = step["awaiting_end"], step["on_appeal_end"]
        pop_end = awaiting + on_appeal
        mean_pop = 0.5 * (pop_start + pop_end)
        disp_pop = min(mean_pop, a.dispersal_capacity)
        hotel_pop = max(0.0, mean_pop - a.dispersal_capacity)
        unit_hotel = a.hotel_cost_per_night * (1 + a.cost_real_growth) ** t
        unit_disp = a.dispersal_cost_per_night * (1 + a.cost_real_growth) ** t
        accom = (hotel_pop * unit_hotel + disp_pop * unit_disp) * DAYS_PER_YEAR / 1e6
        cases = step["initial_decisions"] + step["appeals_decided"]
        proc = a.processing_cost_per_case * cases * (1 + a.cost_real_growth) ** t / 1e6
        out[yr] = accom + proc
    return pd.Series(out, name="asylum_support")


def project_asylum_population(
    scenario: Scenario, years: list[str] = PROJECTION_YEARS
) -> pd.DataFrame:
    """Year-by-year trace of the two-stock supported population.

    Columns: awaiting_start, on_appeal_start, pop_start, arrivals, withdrawals,
    appeal_share, initial_decisions, initial_granted, initial_refused,
    appeals_decided, appeals_granted, appeals_refused, awaiting_end,
    on_appeal_end, pop_end, dispersal_pop, hotel_pop.
    """
    a = scenario.asylum
    rows = []
    awaiting = float(a.awaiting_determination_start)
    on_appeal = float(a.on_appeal_start)
    for yr in years:
        aw_start, ap_start = awaiting, on_appeal
        pop_start = aw_start + ap_start
        step = _step_asylum(a, aw_start, ap_start)
        awaiting, on_appeal = step["awaiting_end"], step["on_appeal_end"]
        pop_end = awaiting + on_appeal
        mean_pop = 0.5 * (pop_start + pop_end)
        disp_pop = min(mean_pop, a.dispersal_capacity)
        hotel_pop = max(0.0, mean_pop - a.dispersal_capacity)
        rows.append({
            "year": yr,
            "awaiting_start": aw_start,
            "on_appeal_start": ap_start,
            "pop_start": pop_start,
            "arrivals": step["arrivals"],
            "withdrawals": step["withdrawals"],
            "appeal_share": step["appeal_share"],
            "initial_decisions": step["initial_decisions"],
            "initial_granted": step["initial_granted"],
            "initial_refused": step["initial_refused"],
            "appeals_decided": step["appeals_decided"],
            "appeals_granted": step["appeals_granted"],
            "appeals_refused": step["appeals_refused"],
            "awaiting_end": awaiting,
            "on_appeal_end": on_appeal,
            "pop_end": pop_end,
            "dispersal_pop": disp_pop,
            "hotel_pop": hotel_pop,
        })
    return pd.DataFrame(rows).set_index("year")


def project_police_real(
    scenario: Scenario,
    deflator: pd.Series | None = None,
    years: list[str] = PROJECTION_YEARS,
) -> pd.Series:
    """HO Core Grant for police (= the HO contribution to the funding settlement).

    Gross E&W spending (pay bill + non-pay) is funded by HO Core Grant +
    precept + other local income. This projection returns the HO residual —
    i.e. what the Home Office actually has to pay each year — since that is
    what hits the departmental RDEL budget.

    Use ``project_police_funding`` for the full decomposition including the
    precept and non-pay sides.
    """
    funding = project_police_funding(scenario, deflator=deflator, years=years)
    return funding["ho_core_grant"].rename("police")


def project_police_funding(
    scenario: Scenario,
    deflator: pd.Series | None = None,
    years: list[str] = PROJECTION_YEARS,
) -> pd.DataFrame:
    """Decompose gross police spending into pay/non-pay and funding sources.

    All columns are in real £m at the model base year. Precept income grows at
    ``precept_nominal_growth`` in nominal terms and is deflated back to real
    using the GDP deflator. The HO Core Grant is the residual that balances
    the accounts.

    Columns: pay_bill, non_pay, gross, precept, other_income, ho_core_grant.
    """
    from .deflator import load_deflator, real_from_nominal

    if deflator is None:
        deflator = load_deflator()

    p = scenario.police
    offsets = _years_from_base(years)
    # Build nominal precept series first, then convert in one pass.
    precept_nominal = pd.Series(
        {yr: p.precept_income * (1 + p.precept_nominal_growth) ** t
         for yr, t in zip(years, offsets)}
    )
    precept_real = real_from_nominal(precept_nominal, deflator)

    rows = []
    for yr, t in zip(years, offsets):
        workforce = p.workforce_fte * (1 + p.workforce_growth_per_year) ** t
        pay = p.avg_pay_per_fte * (1 + p.real_pay_award_per_year) ** t
        officer_pay = workforce * pay * p.on_costs_multiplier / 1e6
        staff_pay = p.staff_pay_gross * (1 + p.staff_pay_real_growth) ** t
        pay_bill = officer_pay + staff_pay
        non_pay = p.non_pay_gross * (1 + p.non_pay_real_growth) ** t
        gross = pay_bill + non_pay
        precept = float(precept_real.loc[yr])
        other = p.other_income * (1 + p.other_income_real_growth) ** t
        ho_core = gross - precept - other
        rows.append({
            "year": yr, "officer_pay": officer_pay, "staff_pay": staff_pay,
            "pay_bill": pay_bill, "non_pay": non_pay, "gross": gross,
            "precept": precept, "other_income": other, "ho_core_grant": ho_core,
        })
    return pd.DataFrame(rows).set_index("year")


def project_borders_real(scenario: Scenario, years: list[str] = PROJECTION_YEARS) -> pd.Series:
    """Border Force pay + non-pay, plus UKVI gross RDEL net of fee income.

    All inputs are 2025-26 real £m; time-varying growth rates are applied from
    the base year.
    """
    b = scenario.borders
    offsets = _years_from_base(years)
    out = {}
    for yr, t in zip(years, offsets):
        workforce = b.border_force_fte * (1 + b.border_force_workforce_growth) ** t
        pay = b.border_force_pay_per_fte * (1 + b.border_force_pay_real_growth) ** t
        bf_pay = workforce * pay * b.border_force_on_costs / 1e6
        bf_non_pay = (
            b.border_force_non_pay
            * (1 + b.border_force_non_pay_real_growth) ** t
            * b.passenger_volume_index
        )
        ukvi_gross = b.ukvi_gross_rdel * (1 + b.ukvi_gross_real_growth) ** t
        ukvi_fees = b.ukvi_fee_income * (1 + b.fee_real_growth) ** t
        ukvi_net = ukvi_gross - ukvi_fees
        out[yr] = bf_pay + bf_non_pay + ukvi_net
    return pd.Series(out, name="borders_migration")


def project_bsc_real(scenario: Scenario, years: list[str] = PROJECTION_YEARS) -> pd.Series:
    """Border Security Command: interpolate from baseline to baseline+uplift by 2028-29,
    then hold real in SR27 period unless told otherwise.
    """
    bsc = scenario.bsc
    baseline = bsc.baseline_rdel_2025_26
    peak = baseline + bsc.plus_by_2028_29
    anchor_years = {"2025-26": baseline, "2028-29": peak}
    out = {}
    for yr in years:
        if yr in anchor_years:
            out[yr] = anchor_years[yr]
            continue
        yi = int(yr[:4])
        if 2026 <= yi <= 2027:
            # Interpolate between 2025-26 and 2028-29
            if bsc.profile == "backloaded":
                share = {2026: 0.2, 2027: 0.5}[yi]
            else:  # linear
                share = (yi - 2025) / 3
            out[yr] = baseline + share * bsc.plus_by_2028_29
        else:
            # SR27 period — hold at peak in real terms
            out[yr] = peak
    return pd.Series(out, name="border_security_command")


def project_homeland_security_real(
    scenario: Scenario, years: list[str] = PROJECTION_YEARS
) -> pd.Series:
    o = scenario.other
    offsets = _years_from_base(years)
    out = {
        yr: o.homeland_security_baseline * (1 + o.homeland_security_real_growth) ** t
        for yr, t in zip(years, offsets)
    }
    return pd.Series(out, name="homeland_security")


def project_crime_fire_drugs_real(
    scenario: Scenario, years: list[str] = PROJECTION_YEARS
) -> pd.Series:
    o = scenario.other
    offsets = _years_from_base(years)
    out = {
        yr: o.crime_fire_drugs_baseline * (1 + o.crime_fire_drugs_real_growth) ** t
        for yr, t in zip(years, offsets)
    }
    return pd.Series(out, name="crime_fire_drugs")


def project_corporate_admin_real(
    scenario: Scenario,
    deflator: pd.Series,
    years: list[str] = PROJECTION_YEARS,
) -> pd.Series:
    """SR25 sets admin in NOMINAL £m for 2025-26 to 2028-29. Convert those to real using
    the deflator, then extrapolate the SR27 period at the scenario's real growth rate.
    """
    from .deflator import real_from_nominal

    o = scenario.other
    nom_known = pd.Series(o.corporate_admin_by_year)
    real_known = real_from_nominal(nom_known, deflator)
    last_year = max(o.corporate_admin_by_year.keys())
    last_real = real_known.loc[last_year]

    out = {}
    for yr in years:
        if yr in real_known.index:
            out[yr] = real_known.loc[yr]
        else:
            steps = int(yr[:4]) - int(last_year[:4])
            out[yr] = last_real * (1 + o.corporate_admin_real_growth_sr27) ** steps
    return pd.Series(out, name="corporate_admin")


def project_cdel_real(
    scenario: Scenario,
    deflator: pd.Series | None = None,
    sr25_envelope_nominal: pd.DataFrame | None = None,
    years: list[str] = PROJECTION_YEARS,
) -> pd.DataFrame:
    """Project CDEL by area in real £m (base year prices).

    Strategy:
    - Take the published SR25 envelope (nominal £m) for years where it exists,
      deflate to real.
    - For years beyond the envelope, grow from the last known envelope year at
      ``sr27_real_growth``.
    - Fall back to the scenario's ``total_cdel_2025_26_fallback`` if no
      envelope is available.
    - Split each year's total across areas using ``scenario.cdel.split``.
    """
    from .deflator import load_deflator, real_from_nominal
    from .historic import load_sr25_envelope

    c = scenario.cdel
    if deflator is None:
        deflator = load_deflator()
    if sr25_envelope_nominal is None:
        sr25_envelope_nominal = load_sr25_envelope()

    env_cdel_real = pd.Series(dtype=float)
    if sr25_envelope_nominal is not None and "CDEL" in sr25_envelope_nominal.columns:
        env_cdel_nom = sr25_envelope_nominal["CDEL"].dropna()
        env_cdel_real = real_from_nominal(env_cdel_nom, deflator)

    totals: dict[str, float] = {}
    last_known_year = env_cdel_real.index.max() if len(env_cdel_real) else None
    for yr in years:
        if yr in env_cdel_real.index:
            totals[yr] = float(env_cdel_real.loc[yr])
        elif last_known_year is not None:
            steps = int(yr[:4]) - int(last_known_year[:4])
            totals[yr] = float(env_cdel_real.loc[last_known_year]) * (1 + c.sr27_real_growth) ** steps
        else:
            steps = int(yr[:4]) - int("2025-26"[:4])
            totals[yr] = c.total_cdel_2025_26_fallback * (1 + c.sr27_real_growth) ** steps

    df = pd.DataFrame(index=years, columns=list(c.split.keys()), dtype=float)
    for yr, total in totals.items():
        for area, share in c.split.items():
            df.loc[yr, area] = total * share
    return df
