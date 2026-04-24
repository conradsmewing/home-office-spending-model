# Home Office spending model — plain English explanation

This document describes what the model does, where its numbers come from, and how the projection logic works. It is written for a reader who wants to understand the model without reading the code.

---

## 1. What the model is for

The model produces a year-by-year picture of Home Office departmental spending — both the Resource budget (RDEL: day-to-day running costs) and the Capital budget (CDEL: investment) — split into seven programme areas. It covers:

- A **historic** period from 2020-21 to 2024-25, using published outturn data.
- A **SR25 projection period** from 2025-26 to 2028-29, reflecting the June 2025 Spending Review envelope.
- A **SR27 projection period** from 2029-30 to 2030-31, which is fully driver-projected because no SR27 envelope yet exists.

All real-terms figures are expressed in **2025-26 prices** using the HMT GDP deflator.

---

## 2. The seven programme areas

The model splits the Home Office into seven areas, chosen because each has a distinct driver story:

| Area | What it covers |
|---|---|
| Asylum & Protection | Asylum accommodation (hotels and dispersal), subsistence, processing, legal |
| Borders & Migration | Border Force operations, UKVI gross costs less visa fee income |
| Border Security Command | New SR25 initiative tackling small-boats people-smuggling |
| Police | Core police grant, counter-terrorism policing, NCA contribution |
| Homeland Security | Counter-terrorism, intelligence, HMG security functions |
| Crime, Fire & Drugs | Crime reduction, drug strategy, fire resilience |
| Corporate & Admin | Back-office, HR, digital, admin trajectory set by SR25 |

---

## 3. Where the numbers come from

There are two main data inputs:

1. **PESA 2025 Chapter 1 (HMT)** — gives the total Home Office RDEL and CDEL envelope year-by-year from 2020-21 to 2029-30, on a consistent basis. The model extracts the "Home Office" row from four tables: resource DEL excl depreciation (historic and SR25 forward), and capital DEL (historic and forward).

2. **HMT GDP deflator (March 2026 QNA release)** — gives the implicit price deflator for every financial year from 1955-56 to 2024-25 (ONS outturn) and forecasts to 2030-31 (OBR Spring Statement 2026). The model rebases this so that 2025-26 = 100 and uses it for every real/nominal conversion.

PESA only tells us the total Home Office envelope, not the split between the seven programme areas. To produce a programme-level historic series the model applies a **share vector** (roughly: 19% asylum, 10% borders, 0.5% Border Security Command, 61% police, 4% homeland security, 3.5% crime/fire/drugs, 2.3% admin — shares sum to exactly 1.0). These shares are editable in `parse_sources.py` and should be replaced with authoritative figures once the HO Annual Report & Accounts PDF is parsed.

---

## 4. How the projection works

For the historic period the model uses PESA directly. For the projection period it does something different: it builds each area up from a small set of drivers, lets you vary those drivers, and reports back the total.

### 4.1 Asylum & Protection

The driver is:

> supported population × (hotel share × hotel unit cost + dispersal share × dispersal unit cost) × 365 days + processing cost per case × cases processed per year

The default baseline uses ~106,000 people in support, 30% in hotels at £140/night, 70% in dispersal accommodation at £22/night, and processing at ~£13,500 per case. Population can grow or shrink year-on-year through a parameter.

### 4.2 Police

> workforce (FTE) × average pay per FTE × on-costs multiplier + non-pay RDEL

The on-costs multiplier captures pensions, NICs and overheads (default 1.25). Workforce and real pay awards can grow year-on-year. Non-pay RDEL is a single bucket for counter-terrorism, NCA, technology and grants.

### 4.3 Borders & Migration

> Border Force pay bill + Border Force non-pay (scaled by passenger volume) + (UKVI gross cost − visa fee income)

UKVI is substantially fee-funded, so the model represents it as a net figure: gross cost less fee income. Fee income can grow in real terms through a parameter.

### 4.4 Border Security Command

SR25 announced a phased uplift of £280m additional RDEL per year by 2028-29. The model takes a 2025-26 baseline, interpolates linearly to the 2028-29 peak, and holds flat in real terms through the SR27 period. The profile can be switched to "backloaded".

### 4.5 Homeland Security and Crime/Fire/Drugs

Each is a simple baseline (fixed at 2025-26 real prices) compounded year-on-year by a real growth rate. The defaults are 0% for homeland security and −1% for crime/fire/drugs.

### 4.6 Corporate & Admin

SR25 sets admin costs in nominal terms: £482m (25-26) → £474m → £466m → £458m (28-29). The model reads these nominal figures, deflates them to real prices, and then extrapolates the SR27 period at −2% real growth per year (reflecting continued admin pressure).

### 4.7 CDEL

CDEL is modelled as a single total, calibrated to match PESA 2025-26 plans (~£1.54bn real), and then distributed across areas using a fixed split (police ~32%, borders ~22%, admin ~18%, homeland security ~18%, with smaller shares elsewhere). A real growth parameter lets you grow or shrink the total year-on-year.

---

## 5. Real versus nominal terms

Every driver calculation happens in **real** 2025-26 prices. After the projection is assembled, the model multiplies each year by the rebased GDP deflator to produce a **nominal** figure. This means:

- Parameter changes (e.g. hotel cost per night) are always interpreted as real-terms assumptions. If you want to model a 2% real cost pressure on top of inflation, set the parameter accordingly.
- Comparing real vs nominal side-by-side shows how much of headline growth is inflation versus genuine volume or price change.

The deflator is rebased inside the model, so the HMT file does not need to be in 2025-26 base — the source file is in 2024-25 base and the model converts automatically.

---

## 6. Scenarios

Scenarios are just a bundle of parameter overrides. The repo ships with four:

- **baseline** — flat assumptions everywhere; calibrated so 2025-26 totals match PESA plans within ~£50m.
- **high asylum** — 130,000 supported population (+20%), growing 3% per year, hotel share 32%.
- **low asylum** — 85,000 supported population (−20%), falling 5% per year, hotel share down to 20%.
- **police growth** — workforce growing 1% per year, real pay award of 1% per year.

You can build your own by constructing a `Scenario()` and editing any of its sub-objects (asylum, police, borders, bsc, other, cdel).

---

## 7. The envelope comparison

A key output is the **envelope gap**: the difference between what the driver model projects and what the SR25 settlement actually allocates. A positive gap means the bottom-up drivers are implying more spending than the top-down settlement allows — i.e. something has to give. In the baseline scenario the gap is near zero in 2025-26 (£47m undershoot, because the seed parameters are calibrated there), widens to −£988m in 2026-27 (SR25 tightens but the model assumes flat activity), and swings to +£332m in 2028-29. These gaps are the most interesting output of the model: they quantify where the implied savings or cost pressures sit.

---

## 8. What the model does not do

- It does not attempt to model the Home Office's AME (annually managed expenditure) — things like provisions and impairments which sit outside DEL control.
- It does not capture the precept-funded portion of police spending; the police line only reflects HO-funded police DEL.
- The historic series starts at 2020-21 because that is the window PESA 2025 gives on a consistent basis. Pre-2020 data would require parsing archived PESA releases.
- The programme-level historic split is a proportional allocation, not direct outturn. This is a known limitation; the fix is to parse the HO Annual Report & Accounts for the Statement of Parliamentary Supply.
- The seed driver parameters (pay rates, workforce sizes, UKVI fees) are indicative figures from published sources. For analytical rigour they should be replaced with values from the Home Office Main Estimates Memorandum.

---

## 9. How to use the model

1. Open `notebooks/home_office_model.py` in Jupyter to interact with the baseline and scenarios.
2. Or run `PYTHONPATH=src python -m home_office_model.render` to regenerate the charts and CSVs in `outputs/`.
3. Edit `scenarios.py` to change driver assumptions, or build a new scenario in a notebook cell:

   ```python
   from home_office_model.projections import run_projection
   from home_office_model.scenarios import Scenario

   my_scenario = Scenario(name="my_test")
   my_scenario.asylum.dispersal_capacity = 80_000
   my_scenario.police.workforce_growth_per_year = 0.02
   result = run_projection(my_scenario)
   result.totals_real()
   ```

4. Compare against the SR25 envelope via `result.envelope_gap()`.
