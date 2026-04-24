# Dashboard user guide

The interactive Streamlit dashboard is the fastest way to explore the Home Office spending model. This guide walks through each tab, explains what the controls do, and points out what to look for.

For the underlying model logic, see [`model_explanation.md`](model_explanation.md).

## Running the dashboard

**Online (deployed):** a public version is hosted on Streamlit Community Cloud and auto-updates whenever `main` is pushed to GitHub.

**Locally:**
```bash
cd "Home Office"
streamlit run dashboard/app.py
```
The app opens at <http://localhost:8501>.

---

## Global controls (sidebar)

| Control | What it does |
|---|---|
| **Preset** | Resets all parameters to one of four bundled scenarios: `baseline`, `high asylum`, `low asylum`, `police growth`. Switching preset overwrites every control in every tab. |
| **Units** | Toggles between **real 2025-26 £m** and **nominal £m** for all charts and tables that respect it. Real is best for comparisons across years; nominal is what appears in published documents. |

All parameter changes in the tabs are applied live — each slider/input triggers a re-run of the projection.

---

## Tab 0 — Overview

The headline view: HO total spending (RDEL + CDEL) vs the budget envelope.

### Key controls
- **SR27 real growth slider** — sets the real growth rate applied to the 2028-29 envelope to extrapolate 2029-30 and 2030-31. The default matches the implied SR25 CAGR on total DEL (shown in the caption above the slider, currently around −0.24% p.a.).

### What to look at
- **KPI row**: Total DEL for 2025-26, 2028-29 (end of SR25) and 2030-31 (end of SR27), with the gap-vs-envelope shown as the delta. Red = model spend exceeds envelope.
- **Cumulative gap** across the projection horizon (one number showing the total headroom or overspend).
- **Forecast vs envelope chart**: four lines (RDEL envelope solid, RDEL model dashed; same for CDEL), with the SR27 extrapolation band shaded grey.
- **Gap bar chart**: year-by-year overspend (red) or headroom (green) for RDEL and CDEL.
- **Continuity check table**: percentage step-change in each area from 2024-25 outturn to 2025-26 model forecast. Cells with |Δ| > 5% are highlighted red. Use this to spot calibration drift.
- **RDEL by programme area**: stacked area chart showing the full year-by-year RDEL across historic + projection, split by area.

### Things to try
- Move the SR27 slider and watch the gap bars for 2029-30 and 2030-31.
- Switch preset to **high asylum** and see how the RDEL line drifts above the envelope.

---

## Tab 1 — Asylum & Protection

Two-stock supported population model plus capacity-constrained accommodation.

### Key controls (grouped)
- **Starting stocks & inflows**: `awaiting determination start`, `on appeal start`, `new arrivals per year`, `withdrawal rate` (fraction of awaiting pool who leave without a decision each year).
- **Decision capacity & reallocation rule**: `total decisions capacity`, `baseline appeal share`, `max appeal share` (the ceiling when backlog forces reallocation), `appeal backlog target` in months.
- **Outcome rates**: `initial grant rate`, `appeal success rate`.
- **Accommodation & unit costs**: `dispersal capacity`, `hotel £/night`, `dispersal £/night`, `£/case processing`.

### What to look at
- **Stock chart**: end-of-year supported population by pool (awaiting + on appeal), with a total line.
- **Outflows chart**: annual departures from support — granted (initial and appeal), refused-on-appeal (deported), and withdrawals.
- **Capacity reallocation chart**: shows the appeal share of decisions capacity drifting up when the appeal pool exceeds the target months. This is the visible signature of the reallocation rule.
- **Accommodation mix**: dispersal population (stacked) vs hotel population (residual) by year, with a dashed line at `dispersal_capacity`.
- **Asylum RDEL** area chart underneath.
- **Historic outturn + forecast chart**: the supported population line and the initial-decisions / granted / enforced-returns bars shown continuously across outturn and forecast years.

### Things to try
- Drop `dispersal_capacity` to 60,000 and see hotels stay in the picture longer.
- Raise `new arrivals per year` to 110k and watch the appeal pool grow, triggering the reallocation rule.
- Lower `initial grant rate` and see more population flow into the appeal pool.

---

## Tab 2 — Police (HO Core Grant)

The police line on HO RDEL is the residual once precept + other income are netted off gross E&W spending.

### Key levers (featured at top)
- **Police numbers** (officer FTE) and **workforce growth p.a.**.
- **Precept income growth p.a. (nominal)** — default 5% p.a., reflecting council-tax cap policy.

### Advanced expander
- Average officer pay, on-costs multiplier, real pay award.
- Staff & PCSO pay bucket (default £2.6bn) — this is what reconciles the gross spend to 2024-25 historic outturn.
- Non-pay gross and real growth.
- Other income and its real growth.

### What to look at
- **Headline KPIs**: 2025-26 HO Core Grant, 2028-29 HO Core Grant (with £ delta vs 2025-26), and implied real growth p.a.
- **HO Core Grant line chart**: outturn 2020-21 to 2024-25 (indicative Police Funding Settlement figures) plus model forecast 2025-26 to 2030-31, with precept shown as a dotted companion line.
- **Full funding stack**: HO Core Grant + Precept + Other = Gross, shown as a stacked bar with the gross line overlaid.
- **Police numbers chart**: outturn FTE 2020–2024 plus model forecast 2025–2030.

### Things to try
- Nudge `precept_nominal_growth` from 5% to 3% and watch the HO Core Grant KPIs rise (HO has to fill the gap).
- Raise `workforce_fte` to 160k and see gross rise faster than precept, forcing more HO grant.
- Lower `staff_pay_gross` by £500m to see the HO Core Grant fall by the same amount (it's a direct pass-through).

---

## Tab 3 — Borders & Migration

Border Force pay bill + non-pay, plus UKVI gross net of fee income. All components have their own real growth rates.

### Key controls
- **Border Force workforce & pay**: FTE, workforce growth, pay per FTE, real pay growth, non-pay £m, non-pay real growth, passenger volume index.
- **UKVI gross net of fees**: gross £m, gross real growth, fee income £m, fee real growth.

### What to look at
- The Borders & Migration RDEL area chart should now drift over the projection horizon (before these drivers existed it was frozen flat).

### Things to try
- Set `fee_real_growth` to +5% p.a. (fees rising faster than inflation) and see UKVI net shrink.
- Raise `passenger_volume_index` to 1.2 (20% above baseline) to scale BF non-pay.

---

## Tab 4 — Border Security Command

A standalone SR25 programme funded on top of Borders & Migration.

### Controls
- **Baseline 2025-26 £m**, **Uplift by 2028-29 £m** (default +£280m per SR25), **profile** (linear or backloaded).

### What to look at
- The phased ramp from baseline to baseline + uplift over the SR25 period, then flat real in SR27.

---

## Tab 5 — Homeland Security

Single real baseline compounded at a real growth rate.

### Controls
- **Baseline 2025-26 £m**, **Real growth p.a.**.

---

## Tab 6 — Crime, Fire & Drugs

Same simple structure as Homeland Security, but with a reduced baseline (£450m default) reflecting the 2022 transfer of fire & rescue to MHCLG. The historic → projection transition shows a −32% step, which is correct — it's a real transfer event, not a calibration bug.

### Controls
- **Baseline 2025-26 £m**, **Real growth p.a.**.

---

## Tab 7 — Corporate & Admin

SR25 nominal path for 2025-26 to 2028-29, then real-growth extrapolation for SR27.

### Controls
- **Corporate admin nominal £m by year (SR25 years)** — four number inputs for 25-26, 26-27, 27-28, 28-29.
- **SR27 real growth p.a.** — extrapolation rate for 2029-30 and 2030-31.

---

## Tab 8 — CDEL (capital)

Total CDEL comes from the published SR25 envelope; SR27 years extrapolate at the CDEL real growth rate. Area splits are fixed shares.

### Controls
- **Fallback total CDEL £m** — used only if the envelope file is missing.
- **SR27 real growth p.a. (CDEL)**.
- **Area split** — seven number inputs (shares must sum to 1; a warning appears if they don't).

---

## Tab 9 — Compare scenarios

Runs the four bundled presets side-by-side and plots total DEL by year on a single chart. Useful for quickly seeing how, say, `high asylum` differs from `baseline`.

---

## Tab 10 — Export

Download options:
- **Tidy long CSV** of the full projection (year × area × budget_type × real + nominal values).
- **Current scenario parameters** as JSON (so you can reproduce the exact run later).

---

## Keyboard / workflow tips

- **Real/nominal toggle** is a single sidebar switch — flip it to see how much of headline growth is inflation.
- Every widget change re-runs the projection. For a large sweep (e.g. comparing 10 scenarios) use the Compare scenarios tab or scripted runs via `run_projection(Scenario())` — the dashboard is built for single-scenario inspection.
- **Preset switching** throws away all your tuning. If you have a customised scenario you want to keep, hit the Export tab first and save the JSON.
- The continuity diagnostic on the Overview tab is the first place to look after changing any baseline parameter — an unexpected >5% step-change usually indicates a miscalibrated driver.
