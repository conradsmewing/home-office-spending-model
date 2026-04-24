# Home Office Spending Model

A driver-based Python model of UK Home Office departmental spending (RDEL + CDEL) covering a consistent historic series and projections over the SR25 period (to 2028-29) and SR27 period (to 2030-31). Real-terms analysis uses the HMT GDP deflator, rebased to **2025-26**.

## Structure

```
Home Office/
├── data/
│   ├── raw/         # original downloads (PESA, HO ARA, GDP deflator, ...)
│   └── processed/   # cleaned parquet/csv outputs
├── src/home_office_model/
│   ├── config.py         # years, areas, paths
│   ├── deflator.py       # GDP deflator loader + real/nominal converters
│   ├── historic.py       # loads historic outturn time series
│   ├── scenarios.py      # dataclass scenario parameters
│   ├── drivers.py        # per-area driver projection functions
│   └── projections.py    # orchestrator: historic + SR25 + SR27 projection
├── notebooks/
│   └── home_office_model.py   # JupyText notebook (open in Jupyter/VS Code)
└── outputs/         # generated charts and tables
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then either open `notebooks/home_office_model.py` in Jupyter (it'll render as a notebook via JupyText) or run the projection directly:

```python
from home_office_model.projections import run_projection
from home_office_model.scenarios import Scenario

result = run_projection(Scenario(name="baseline"))
print(result.head())
```

## Data

**Data pipeline**: raw files from gov.uk sit in `data/raw/`. Running `python -m home_office_model.parse_sources` (from within `src/`, or with `PYTHONPATH=src`) parses them into tidy CSVs:

- `gdp_deflator.xlsx` → `gdp_deflator.csv` (70+ financial years, 1955-56 to 2030-31 via OBR forecast)
- `pesa_2025_ch1.xlsx` → `historic.csv` (HO RDEL/CDEL 2020-21 to 2024-25, distributed across areas using published shares) + `sr25_envelope.csv` (PESA plans 2025-26 onwards)

The model falls back to bundled `*_seed.csv` files if the parsed CSVs are missing, so it always runs. For deeper programme-level outturn by sub-area you'd additionally parse the HO Annual Report & Accounts PDF (not yet automated — see `data/raw/DOWNLOADS.md`).

## Areas

The model splits Home Office spending into 7 programme areas, each with its own driver logic:

| Area | Key drivers |
|---|---|
| Asylum & Protection | supported population × hotel/dispersal mix × unit cost + processing |
| Borders & Migration | Border Force workforce + UKVI gross less fee income |
| Border Security Command | SR25 envelope (£280m additional RDEL by 2028-29) |
| Police | workforce × pay × on-costs + non-pay RDEL |
| Homeland Security | baseline × real growth |
| Crime, Fire & Drugs | baseline × real growth |
| Corporate & Admin | SR25 envelope (known, declining -10% real by 2028-29) |
