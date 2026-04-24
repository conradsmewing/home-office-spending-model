# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Home Office spending model
#
# Driver-based model of UK Home Office RDEL and CDEL covering a historic outturn series
# (2015-16 to 2024-25) and projections over the SR25 period (to 2028-29) and SR27 period
# (to 2030-31). All real-terms figures are in **2025-26 prices** using the HMT GDP deflator.
#
# **NB:** the repo ships with seed CSVs containing approximate published figures so the model
# runs out of the box. For production analysis, replace `data/raw/gdp_deflator_seed.csv` and
# `data/raw/historic_seed.csv` with the canonical files listed in `data/raw/DOWNLOADS.md`.

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Make the package importable when running this notebook from the notebooks/ folder
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

from home_office_model.config import AREA_LABELS, HISTORIC_YEARS, PROJECTION_YEARS, SR25_YEARS, SR27_YEARS
from home_office_model.projections import run_projection, compare_scenarios
from home_office_model.scenarios import (
    Scenario,
    high_asylum_scenario,
    low_asylum_scenario,
    police_growth_scenario,
)

pd.set_option("display.float_format", "{:,.0f}".format)

# %% [markdown]
# ## Baseline projection

# %%
baseline = run_projection(Scenario(name="baseline"))

# %%
totals = baseline.totals_real()
totals["Total DEL (real)"] = totals.sum(axis=1)
totals

# %% [markdown]
# ## RDEL breakdown by area (real, £m, 2025-26 prices)

# %%
rdel = baseline.rdel_real.rename(columns=AREA_LABELS)
rdel

# %% [markdown]
# ### Stacked area chart: RDEL over time

# %%
fig, ax = plt.subplots(figsize=(11, 6))
rdel.plot.area(ax=ax, alpha=0.85)
ax.axvline(x=rdel.index.get_loc("2024-25") + 0.5, color="black", linestyle="--", linewidth=0.8)
ax.axvline(x=rdel.index.get_loc("2028-29") + 0.5, color="black", linestyle=":", linewidth=0.8)
ax.set_ylabel("£m, 2025-26 prices")
ax.set_title("Home Office RDEL by programme area (baseline scenario)")
ax.legend(loc="upper left", fontsize=9)
ax.margins(x=0)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Share of RDEL by area

# %%
shares = rdel.div(rdel.sum(axis=1), axis=0) * 100
shares.round(1)

# %% [markdown]
# ## Scenario comparison
#
# - **baseline** — SR25 as announced + flat driver assumptions
# - **high_asylum** — +20% supported population growing 3% p.a., slower hotel exit
# - **low_asylum** — -20% supported population, hotel share drops to 20%
# - **police_growth** — +1% workforce p.a., +1% real pay award

# %%
scenarios = [
    Scenario(name="baseline"),
    high_asylum_scenario(),
    low_asylum_scenario(),
    police_growth_scenario(),
]
comparison = compare_scenarios(scenarios)
pivot = comparison.pivot_table(
    index="year", columns="scenario", values="total_real", aggfunc="first"
)
pivot

# %%
fig, ax = plt.subplots(figsize=(11, 6))
pivot.plot(ax=ax, marker="o")
ax.set_ylabel("Total DEL, £m, 2025-26 prices")
ax.set_title("Home Office total DEL: scenario comparison")
ax.axvline(
    x=list(pivot.index).index("2024-25") + 0.5,
    color="grey",
    linestyle="--",
    linewidth=0.8,
    label="_historic / projection",
)
ax.axvline(
    x=list(pivot.index).index("2028-29") + 0.5,
    color="grey",
    linestyle=":",
    linewidth=0.8,
    label="_SR25 / SR27",
)
ax.legend(loc="upper left", fontsize=9)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Drilling into asylum drivers
#
# The biggest growth area in recent years. Supported population is modelled as two stocks
# (awaiting determination + on appeal). Dispersal capacity absorbs population first; the
# residual sits in hotels at £140/night vs £22/night dispersal. Try varying the capacity.

# %%
asylum_sensitivity = {}
for capacity in [60_000, 75_000, 90_000, 110_000]:
    s = Scenario(name=f"dispersal_cap_{capacity}")
    s.asylum.dispersal_capacity = capacity
    r = run_projection(s)
    asylum_sensitivity[f"{capacity // 1000}k dispersal capacity"] = r.rdel_real["asylum_support"]
pd.DataFrame(asylum_sensitivity).loc[PROJECTION_YEARS]

# %% [markdown]
# ## Export results

# %%
out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
baseline.long.to_csv(out_dir / "baseline_long.csv", index=False)
baseline.rdel_real.to_csv(out_dir / "baseline_rdel_real.csv")
baseline.cdel_real.to_csv(out_dir / "baseline_cdel_real.csv")
comparison.to_csv(out_dir / "scenario_comparison.csv", index=False)
print(f"Wrote outputs to {out_dir}")
