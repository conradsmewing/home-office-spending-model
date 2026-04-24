"""Render static PNG charts and CSVs into the outputs/ folder.

Run as:
    PYTHONPATH=src python -m home_office_model.render
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from .config import AREA_LABELS, HISTORIC_YEARS, OUTPUTS, PROJECTION_YEARS, SR25_YEARS
from .projections import compare_scenarios, run_projection
from .scenarios import (
    Scenario,
    high_asylum_grant_rate_scenario,
    high_asylum_inflows_scenario,
    police_plus_10pct_scenario,
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

plt.rcParams.update(
    {
        "figure.dpi": 120,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "-",
        "legend.frameon": False,
    }
)

AREA_COLOURS = {
    "asylum_support": "#d62728",
    "borders_migration": "#ff7f0e",
    "border_security_command": "#8c564b",
    "police": "#1f77b4",
    "homeland_security": "#2ca02c",
    "crime_fire_drugs": "#9467bd",
    "corporate_admin": "#7f7f7f",
}


def _gbp_millions(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"£{v:,.0f}m"))


def _mark_period_boundaries(ax, index):
    idx = list(index)
    for yr, style in [("2024-25", "--"), ("2028-29", ":")]:
        if yr in idx:
            x = idx.index(yr) + 0.5
            ax.axvline(x=x, color="black", linestyle=style, linewidth=0.8, alpha=0.6)


# ---------------------------------------------------------------------------
# Individual charts
# ---------------------------------------------------------------------------


def chart_rdel_stacked(result, out_path):
    df = result.rdel_real.rename(columns=AREA_LABELS)
    cols = [AREA_LABELS[a] for a in AREA_COLOURS.keys()]
    df = df[cols]
    fig, ax = plt.subplots(figsize=(11, 6))
    df.plot.area(ax=ax, color=[AREA_COLOURS[a] for a in AREA_COLOURS.keys()], alpha=0.88)
    _gbp_millions(ax)
    _mark_period_boundaries(ax, df.index)
    ax.set_title("Home Office RDEL by programme area (baseline, real 2025-26 prices)")
    ax.set_xlabel("")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.margins(x=0)
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)


def chart_total_real_vs_nominal(result, out_path):
    real = result.totals_real().sum(axis=1)
    nominal = result.totals_nominal().sum(axis=1)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(real.index, real.values, marker="o", label="Real (2025-26 prices)", color="#1f77b4")
    ax.plot(nominal.index, nominal.values, marker="s", label="Nominal", color="#d62728")
    _gbp_millions(ax)
    _mark_period_boundaries(ax, real.index)
    ax.set_title("Home Office total DEL: real vs nominal (baseline)")
    ax.set_xlabel("")
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)


def chart_scenario_comparison(comparison, out_path):
    pivot = comparison.pivot_table(
        index="year", columns="scenario", values="total_real", aggfunc="first"
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = {"baseline": "#1f77b4", "high_asylum": "#d62728", "low_asylum": "#2ca02c", "police_growth": "#ff7f0e"}
    for col in pivot.columns:
        ax.plot(pivot.index, pivot[col], marker="o", label=col, color=colors.get(col))
    _gbp_millions(ax)
    _mark_period_boundaries(ax, pivot.index)
    ax.set_title("Home Office total DEL across scenarios (real 2025-26 prices)")
    ax.set_xlabel("")
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)


def chart_envelope_gap(result, out_path):
    gap = result.envelope_gap()
    if gap is None:
        return
    gap = gap.drop(columns=["TOTAL"], errors="ignore")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    gap.plot.bar(ax=ax, color={"RDEL": "#1f77b4", "CDEL": "#ff7f0e"})
    _gbp_millions(ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Driver projection vs published SR25 envelope (nominal £m)\npositive = driver model exceeds envelope")
    ax.set_xlabel("")
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)


def chart_asylum_sensitivity(out_path):
    rows = {}
    for capacity in [60_000, 75_000, 90_000, 110_000]:
        s = Scenario(name=f"cap_{capacity}")
        s.asylum.dispersal_capacity = capacity
        r = run_projection(s)
        rows[f"{capacity // 1000}k dispersal capacity"] = r.rdel_real["asylum_support"].loc[PROJECTION_YEARS]
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    df.plot(ax=ax, marker="o")
    _gbp_millions(ax)
    ax.set_title("Asylum RDEL sensitivity to dispersal capacity (real 2025-26 prices)")
    ax.set_xlabel("")
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)
    return df


def chart_rdel_share_stacked(result, out_path):
    df = result.rdel_real.rename(columns=AREA_LABELS)
    cols = [AREA_LABELS[a] for a in AREA_COLOURS.keys()]
    df = df[cols]
    shares = df.div(df.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(11, 6))
    shares.plot.area(ax=ax, color=[AREA_COLOURS[a] for a in AREA_COLOURS.keys()], alpha=0.88)
    _mark_period_boundaries(ax, shares.index)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_ylim(0, 100)
    ax.set_title("Home Office RDEL — share by programme area (baseline)")
    ax.set_xlabel("")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.margins(x=0)
    plt.xticks(rotation=45)
    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def table_summary(result) -> pd.DataFrame:
    """Human-readable summary: headline totals and growth rates."""
    real = result.totals_real().sum(axis=1)
    nominal = result.totals_nominal().sum(axis=1)
    df = pd.DataFrame({"Real £m (25-26 prices)": real.round(0), "Nominal £m": nominal.round(0)})
    df["Real YoY %"] = real.pct_change().mul(100).round(2)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render_all() -> None:
    OUTPUTS.mkdir(exist_ok=True)

    baseline = run_projection(Scenario(name="baseline"))
    scenarios = [
        Scenario(name="baseline"),
        high_asylum_inflows_scenario(),
        high_asylum_grant_rate_scenario(),
        police_plus_10pct_scenario(),
    ]
    comparison = compare_scenarios(scenarios)

    # --- Charts ---
    chart_rdel_stacked(baseline, OUTPUTS / "01_rdel_stacked_area.png")
    chart_rdel_share_stacked(baseline, OUTPUTS / "02_rdel_shares.png")
    chart_total_real_vs_nominal(baseline, OUTPUTS / "03_total_real_vs_nominal.png")
    chart_scenario_comparison(comparison, OUTPUTS / "04_scenario_comparison.png")
    chart_envelope_gap(baseline, OUTPUTS / "05_envelope_gap.png")
    asylum_sens = chart_asylum_sensitivity(OUTPUTS / "06_asylum_sensitivity.png")

    # --- CSVs ---
    baseline.long.to_csv(OUTPUTS / "baseline_long.csv", index=False)
    baseline.rdel_real.round(0).to_csv(OUTPUTS / "baseline_rdel_real.csv")
    baseline.cdel_real.round(0).to_csv(OUTPUTS / "baseline_cdel_real.csv")
    baseline.rdel_nominal.round(0).to_csv(OUTPUTS / "baseline_rdel_nominal.csv")
    baseline.cdel_nominal.round(0).to_csv(OUTPUTS / "baseline_cdel_nominal.csv")
    comparison.to_csv(OUTPUTS / "scenario_comparison.csv", index=False)
    if baseline.envelope_gap() is not None:
        baseline.envelope_gap().round(0).to_csv(OUTPUTS / "envelope_gap.csv")
    asylum_sens.round(0).to_csv(OUTPUTS / "asylum_sensitivity.csv")
    table_summary(baseline).to_csv(OUTPUTS / "baseline_summary.csv")

    print(f"Wrote charts and CSVs to {OUTPUTS}")
    for f in sorted(OUTPUTS.iterdir()):
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    render_all()
