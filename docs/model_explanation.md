# Home Office spending model — plain English explanation

This document describes what the model does, where its numbers come from, and how the projection logic works. It is written for a reader who wants to understand the model without reading the code. A companion document, [`dashboard_user_guide.md`](dashboard_user_guide.md), explains how to drive the interactive dashboard.

---

## 1. What the model is for

The model produces a year-by-year picture of Home Office departmental spending — both the Resource budget (RDEL: day-to-day running costs) and the Capital budget (CDEL: investment) — split into seven programme areas. It covers:

- A **historic** period from 2020-21 to 2024-25, using published outturn data.
- An **SR25 projection period** from 2025-26 to 2028-29, reflecting the June 2025 Spending Review envelope.
- An **SR27 projection period** from 2029-30 to 2030-31, which is fully driver-projected because no SR27 envelope yet exists.

All real-terms figures are expressed in **2025-26 prices** using the HMT GDP deflator.

The model's core claim is that departmental spending is the sum of a small set of causal drivers (asylum supported population, police workforce, visa fee income, etc.) and that changes in those drivers have traceable budget consequences.

---

## 2. The seven programme areas

| Area | What it covers |
|---|---|
| Asylum & Protection | Asylum accommodation (hotels + dispersal), subsistence, casework, legal |
| Borders & Migration | Border Force operations + UKVI gross costs net of visa fee income |
| Border Security Command | New SR25 initiative tackling small-boats people-smuggling |
| Police | **HO Core Grant** — the residual the HO funds after precept and other local income |
| Homeland Security | Counter-terrorism, intelligence, HMG security functions |
| Crime, Fire & Drugs | Crime reduction and drug strategy (fire & rescue was transferred to MHCLG in 2022) |
| Corporate & Admin | Back-office, HR, digital, admin trajectory set by SR25 |

---

## 3. Where the numbers come from

Two primary sources:

1. **PESA 2025 Chapter 1 (HMT)** — total Home Office RDEL and CDEL envelope from 2020-21 to 2029-30 on a consistent basis. The model reads four PESA tables (RDEL and CDEL, historic and SR25 plans) and extracts the Home Office row.
2. **HMT GDP deflator (March 2026 QNA release)** — implicit price deflator for every financial year from 1955-56 through to 2030-31 (combining ONS outturn and OBR forecast). The model rebases to 2025-26 = 100.

PESA provides totals, not the splits between programme areas. The historic area splits are produced by applying a fixed share vector to each year's total (roughly: police 32%, borders 22%, homeland 18%, admin 18%, asylum 4%, crime/fire/drugs 4%, BSC 2%). These shares are editable in `parse_sources.py`; for analytical rigour they should be replaced with values from the HO Annual Report & Accounts or the Main Estimates Memorandum.

The driver-level inputs (workforce sizes, pay rates, population stocks, unit costs) are indicative figures calibrated to match the historic 2024-25 outturn in each area, so the transition into the projection is continuous.

---

## 4. How the projection works

For the historic period the model uses PESA directly. For the projection period it builds each area up from drivers. All driver calculations happen in **real 2025-26 prices**; nominal figures are produced at the end by re-applying the deflator.

### 4.1 Asylum & Protection — two-stock population + capacity-constrained accommodation

The supported population is modelled as two stocks:

- **Awaiting determination**: people who have arrived and whose initial asylum decision is pending.
- **On appeal**: people who were refused at initial decision and have appealed.

Each year the stocks evolve as:

```
awaiting[t+1]  = awaiting[t] + arrivals − withdrawals − initial decisions
on_appeal[t+1] = on_appeal[t] + initial refusals − appeal decisions
```

Failed-appeal cases are assumed to be deported quickly enough to leave support within the year, so they do not accumulate anywhere. Withdrawals are modelled as a fraction of the awaiting pool each year (people returning home, regularising status, or going missing).

Decision throughput is a single caseworker pool of `total_decisions_capacity` (baseline 140k cases/year), split between initial and appeal work. The split defaults to `baseline_appeal_share` (29%) but **reallocates toward appeals** when the appeal pool exceeds `appeal_target_months` (default 12 months) of baseline appeal flow — ramping linearly up to `max_appeal_share` (50%). This captures the real behaviour whereby caseworker resource gets pulled into appeals when the backlog grows.

Accommodation cost is **capacity-constrained**: dispersed accommodation is filled first up to `dispersal_capacity` (default 75,000 persons), and any residual population sits in hotels. Marginal changes in the supported stock are therefore priced at the hotel nightly rate (default £140/night) until hotel use reaches zero, after which marginal changes are at the dispersal rate (default £22/night).

Non-accommodation RDEL is a processing cost per case (default £13,500) applied to the total number of initial + appeal decisions.

Baseline parameters are calibrated so the hotel population just reaches zero by the end of 2028-29.

### 4.2 Police — HO Core Grant as the residual

The model computes gross England & Wales police spending as:

```
Gross = Officer pay + Staff/PCSO pay + Non-pay
```

where officer pay = `workforce_fte × avg_pay × on-costs_multiplier`, staff pay is a separate bucket for PCSOs and police staff (~£2.6bn default), and non-pay covers estates, technology, transport, CT and NCA contributions (~£6.5bn default).

This gross is then reconciled against funding sources:

```
Gross = HO Core Grant + Precept + Other income
```

**Precept income** (council-tax raised by Police & Crime Commissioners) grows at `precept_nominal_growth` in nominal terms (default 5% p.a., roughly the council-tax cap plus base), then deflated back to real using the GDP deflator. **Other income** is a small bucket for specific grants, fees and reserves.

The **HO Core Grant is the residual** — the amount the Home Office has to fund to keep the force whole. This is what feeds the Overview RDEL total, not gross police spending. When gross rises faster than precept + other, the HO grant has to grow; when precept growth outpaces gross, HO can give less.

### 4.3 Borders & Migration — Border Force + UKVI net

```
RDEL = Border Force pay bill
     + Border Force non-pay × passenger_volume_index
     + UKVI gross RDEL − visa fee income
```

Each component has its own real growth rate: Border Force workforce growth, BF real pay growth, BF non-pay real growth, UKVI gross real growth, and fee income real growth. UKVI is substantially fee-funded, so the model shows the net figure.

### 4.4 Border Security Command — phased SR25 uplift

SR25 announced a phased uplift of +£280m RDEL per year by 2028-29 on top of a small 2025-26 baseline. The model interpolates from baseline to peak across the SR25 period (linear or backloaded profile), then holds flat in real terms through SR27.

### 4.5 Homeland Security and Crime/Fire/Drugs — baselines × real growth

Each is a real 2025-26 baseline compounded at its own real growth rate. The Crime/Fire/Drugs baseline (£450m default) reflects the fact that fire & rescue funding transferred to MHCLG in 2022 and so is no longer part of the Home Office budget — this leaves a visible step-change at the historic → projection boundary, which the continuity diagnostic flags.

### 4.6 Corporate & Admin — SR25 nominal path + SR27 real growth

SR25 sets admin costs in nominal £m (482 → 474 → 466 → 458 over 2025-26 to 2028-29). The model reads these nominal figures, deflates them to real, then extrapolates the SR27 period at the scenario's `corporate_admin_real_growth_sr27` (default −2% real p.a., reflecting continued admin pressure).

### 4.7 CDEL — envelope anchored, SR27 growth-extrapolated

Total CDEL is taken directly from the **published SR25 envelope** (nominal £m, deflated to real) for years where it exists, which runs through 2029-30. Beyond the envelope, CDEL grows from the last known envelope year at `cdel.sr27_real_growth`. The total is then split across areas by fixed shares (defaults aligned with the historic PESA profile: police 32%, borders 22%, homeland 18%, admin 18%, asylum 4%, crime/fire/drugs 4%, BSC 2%).

This is an improvement on the earlier model, which used a single hardcoded total-CDEL number with 0% real growth and a different area split — that produced wild step changes at the boundary and a flat projection forever.

---

## 5. Real versus nominal terms

Every driver calculation happens in **real 2025-26 prices**. The model then multiplies each year by the rebased GDP deflator to produce nominal figures. Parameter changes (e.g. hotel cost per night, real pay award) are always interpreted as real-terms assumptions. The exception is `precept_nominal_growth`, which is expressed in nominal terms to match how council-tax cap policy is typically discussed; the model converts it to real internally.

The deflator is rebased inside the model, so the HMT source file does not need to be in 2025-26 base — it is in 2024-25 base and the model converts automatically.

---

## 6. The envelope comparison

A key output is the **envelope gap**: the difference between what the driver model projects and the HO budget envelope. On the Overview tab the envelope is built from:

- **SR25 years (2025-26 to 2029-30)**: published SR25 envelope, deflated to real.
- **SR27 years (2030-31)**: extrapolated from 2028-29 at a user-set SR27 real growth rate, which defaults to the SR25 implied CAGR on total DEL (currently around −0.24% p.a.).

The model prints both the per-year gap and the cumulative gap across the projection horizon. A positive gap means the driver model projects more spending than the envelope allows — i.e. something has to give.

---

## 7. The continuity diagnostic

Every projection starts from historic 2024-25 outturn and extends forward. If the driver assumptions and the historic shares are out of alignment the first projection year jumps unnaturally. The Overview tab includes a diagnostic table that reports the percentage step change in each area from 2024-25 outturn to 2025-26 model forecast, and flags any step with absolute value > 5%. The diagnostic is the cheapest way to tell whether the driver baseline is well-calibrated.

Currently the flagged steps in the baseline are:
- Corporate Admin +11% (known SR25 nominal path forces this).
- Crime/Fire/Drugs −32% (genuine transfer of fire & rescue to MHCLG in 2022 — real discontinuity, not a bug).
- CDEL (all areas) −10% (real SR25 total CDEL is below 2024-25 outturn; same percentage across all areas because they share the envelope).

---

## 8. Scenarios

Scenarios are just a bundle of parameter overrides. The repo ships with four:

- **baseline** — arrivals 85k, decision capacity 140k, 45% initial grant / 45% appeal success, 12% withdrawals, dispersal capacity 75k, 1% real pay growth, 5% nominal precept growth. Calibrated so the hotel population just reaches zero by 2028-29.
- **high asylum inflows** — arrivals surge to 130k/yr; all other levers at baseline. The appeal pool backlog builds and hotel population climbs rather than exits — the classic demand-shock stress test.
- **high asylum grant rate** — initial grant rate lifted from 45% to 70% (Syrian/Afghan-style cohort surge), arrivals and capacity at baseline. Fewer cases flow to appeal, so the population drains faster and hotels empty within a year.
- **police +10% over 3 years** — workforce grows from 148,000 to 162,800 FTE by the end of 2028-29 (three years of ~3.23% compounding) and then plateaus. HO Core Grant rises by ~£700m real over SR25 before precept growth starts to catch up.

You can build your own by constructing a `Scenario()` and editing any of its sub-objects (asylum, police, borders, bsc, other, cdel). The phase-in cap on workforce growth uses `police.workforce_growth_end_year = "2028-29"` in combination with a positive `workforce_growth_per_year` — growth applies through that FY and then plateaus.

---

## 9. What the model does not do

- It does not attempt to model the Home Office's AME (annually managed expenditure) — things like provisions and impairments which sit outside DEL control.
- The historic series starts at 2020-21 because that is the window PESA 2025 gives on a consistent basis.
- The programme-level historic split is a proportional allocation of the PESA total, not direct outturn. The fix is to parse the HO Annual Report & Accounts for the Statement of Parliamentary Supply.
- Police staff/PCSO pay is modelled as a single £2.6bn bucket rather than having its own workforce × pay calculation; the dashboard exposes it as a tunable number.
- The seed driver parameters are indicative figures calibrated to 2024-25 outturn. They should be cross-checked against the Home Office Main Estimates Memorandum before use in analytical work.

---

## 10. How to use the model

The fastest way is the interactive dashboard — see [`dashboard_user_guide.md`](dashboard_user_guide.md).

From code:

```python
from home_office_model.projections import run_projection
from home_office_model.scenarios import Scenario

my_scenario = Scenario(name="my_test")
my_scenario.asylum.dispersal_capacity = 80_000
my_scenario.police.workforce_growth_per_year = 0.01
result = run_projection(my_scenario)

print(result.totals_real())        # total RDEL + CDEL by year, real £m
print(result.rdel_real)             # year × area RDEL matrix
print(result.envelope_gap())        # gap vs SR25 envelope, nominal £m
```

To regenerate the static charts in `outputs/`:

```bash
PYTHONPATH=src python -m home_office_model.render
```

To open the notebook view:

```bash
jupyter lab notebooks/home_office_model.py
```
