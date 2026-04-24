# Data files to download

The model ships with seed CSVs containing approximate values. For production analysis, download the canonical sources below into this folder (`data/raw/`) and re-run the loaders.

## 1. PESA 2025 — consistent historic RDEL/CDEL time series

- Landing page: https://www.gov.uk/government/statistics/public-expenditure-statistical-analyses-2025
- PDF: https://assets.publishing.service.gov.uk/media/6874fa6f92691289bdb7d393/Public_Expenditure_Statistical_Analyses_2025.pdf
- Expected file: `pesa_2025_chapter_1.xlsx` or similar (departmental budgets tables)
- Coverage: typically 2020-21 to 2025-26. For earlier years, use archived PESA 2020/2019 releases linked from the same landing page.

## 2. Home Office Annual Report & Accounts 2024-25

- Landing page: https://www.gov.uk/government/publications/home-office-annual-report-and-accounts-2024-to-2025
- PDF: https://assets.publishing.service.gov.uk/media/688c9785a34b939141463e37/HO_ARA_2024-25_Book_WEB_Final_v3+CorrSlip.pdf
- Provides: programme-level RDEL/CDEL outturn and Estimate comparison for 2024-25

## 3. GDP deflator (HMT, latest)

- Landing page: https://www.gov.uk/government/statistics/gdp-deflators-at-market-prices-and-money-gdp-march-2026-quarterly-national-accounts
- Direct XLSX: https://assets.publishing.service.gov.uk/media/69cbaf242d120d9d5ec0f2fd/GDP_Deflators_Qtrly_National_Accounts_March_2026_update.xlsx
- Save as: `gdp_deflator.xlsx`
- Coverage: historic to 2024-25 from ONS; forecast 2025-26 to 2030-31 from OBR Spring Statement 2026

## 4. SR25 Home Office settlement

- Document: https://www.gov.uk/government/publications/spending-review-2025-document/spending-review-2025-html
- Provides: DEL envelope by department 2025-26 to 2028-29, including the HO admin trajectory and £280m BSC uplift

## 5. Home Office Main Estimates Memorandum 2025-26

- Landing page: https://www.gov.uk/government/publications/home-office-main-estimates-memorandum-2024-to-2025 (check for 2025-26 version)
- Provides: detailed programme-level breakdown (asylum, UKVI, Border Force, police, homeland security, corporate) with driver commentary

## 6. Driver data (optional — replaces seed values in scenarios.py)

- **Asylum supported population**: Home Office "Immigration system statistics" quarterly release
- **Police workforce**: Home Office "Police workforce, England and Wales" release
- **Passenger volumes**: CAA / Port of Dover stats
- **Visa volumes and fee income**: HO visa statistics + UKVI accounts
