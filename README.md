# Home Office Spending Model

A driver-based Python model of UK Home Office departmental spending (RDEL + CDEL) covering a consistent historic series and projections over the SR25 period (to 2028-29) and SR27 period (to 2030-31). Real-terms analysis uses the HMT GDP deflator, rebased to **2025-26**.

An interactive Streamlit dashboard lets you explore the drivers, compare scenarios, and see gap-vs-envelope diagnostics.

## Documentation

- **[`docs/model_explanation.md`](docs/model_explanation.md)** — plain-English description of how the model works, driver by driver.
- **[`docs/dashboard_user_guide.md`](docs/dashboard_user_guide.md)** — tab-by-tab walkthrough of the interactive dashboard.

## Structure

```
Home Office/
├── dashboard/
│   └── app.py          # Streamlit dashboard (primary UI)
├── data/
│   ├── raw/            # source downloads (PESA, GDP deflator, HO ARA)
│   └── processed/      # parsed intermediate outputs
├── docs/
│   ├── model_explanation.md
│   └── dashboard_user_guide.md
├── src/home_office_model/
│   ├── config.py         # years, areas, paths
│   ├── deflator.py       # GDP deflator loader + real/nominal converters
│   ├── historic.py       # loads historic outturn time series
│   ├── scenarios.py      # dataclass scenario parameters
│   ├── drivers.py        # per-area driver projection functions
│   └── projections.py    # orchestrator: historic + SR25 + SR27 projection
├── notebooks/
│   └── home_office_model.py   # JupyText notebook (open in Jupyter/VS Code)
└── outputs/              # generated charts and CSVs
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the dashboard

```bash
streamlit run dashboard/app.py
```
Opens at <http://localhost:8501>.

### Run the projection from code

```python
from home_office_model.projections import run_projection
from home_office_model.scenarios import Scenario

result = run_projection(Scenario(name="baseline"))
print(result.totals_real())       # real £m totals by year
print(result.rdel_real)            # year × area RDEL matrix
print(result.envelope_gap())       # gap vs SR25 envelope
```

## Data

Raw files from gov.uk sit in `data/raw/`. Running `PYTHONPATH=src python -m home_office_model.parse_sources` parses them into tidy CSVs:

- `gdp_deflator.xlsx` → `gdp_deflator.csv` (1955-56 to 2030-31; ONS outturn + OBR forecast).
- `pesa_2025_ch1.xlsx` → `historic.csv` (HO RDEL/CDEL 2020-21 to 2024-25, distributed across areas by share vector) and `sr25_envelope.csv` (PESA plans 2025-26 onwards).

The model falls back to bundled `*_seed.csv` files if the parsed CSVs are missing, so it always runs.

## Areas

The model splits Home Office spending into seven programme areas:

| Area | Key drivers |
|---|---|
| Asylum & Protection | Two-stock population (awaiting + on appeal), capacity-constrained accommodation (dispersal first, hotels on the margin) |
| Borders & Migration | Border Force pay & non-pay + UKVI gross RDEL net of visa fee income |
| Border Security Command | SR25 envelope: £280m additional RDEL by 2028-29 |
| Police | **HO Core Grant (residual)** — gross E&W spending net of precept and other local income |
| Homeland Security | Real baseline × real growth rate |
| Crime, Fire & Drugs | Real baseline × real growth rate (fire & rescue transferred to MHCLG in 2022) |
| Corporate & Admin | SR25 nominal path then SR27 real-growth extrapolation |

## Scenarios

Four presets ship in the model:
- **baseline** — calibrated to continue from 2024-25 outturn with hotels exiting by 2028-29.
- **high asylum inflows** — arrivals surge to 130k/yr; appeal backlog builds, hotels stay in use.
- **high asylum grant rate** — initial grant rate raised to 70% (cohort-surge pattern); population drains fast, hotels empty early.
- **police +10% over 3 years** — police workforce phased up by 10% over three years, then plateaus.

Build your own by constructing a `Scenario()` and overriding parameters:

```python
from home_office_model.scenarios import Scenario
s = Scenario(name="my_test")
s.asylum.new_arrivals_per_year = 95_000
s.police.precept_nominal_growth = 0.04
```

See [`docs/model_explanation.md`](docs/model_explanation.md) for full driver logic.
