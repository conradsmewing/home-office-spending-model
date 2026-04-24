"""Streamlit dashboard for the Home Office spending model.

Run from the repo root:

    streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from home_office_model.config import (
    AREA_LABELS,
    HISTORIC_YEARS,
    PROJECTION_YEARS,
    SR25_YEARS,
)
from home_office_model.deflator import nominal_from_real, real_from_nominal
from home_office_model.drivers import project_asylum_population, project_police_funding
from home_office_model.projections import compare_scenarios, run_projection
from home_office_model.scenarios import (
    Scenario,
    high_asylum_grant_rate_scenario,
    high_asylum_inflows_scenario,
    police_plus_10pct_scenario,
)

st.set_page_config(
    page_title="Home Office spending model",
    page_icon="📊",
    layout="wide",
)

W = "stretch"  # replaces deprecated use_container_width=True


def pct_slider(label: str, lo: float, hi: float, value: float,
               step: float = 0.0025, key: str | None = None,
               help: str | None = None, decimals: int = 2) -> float:
    """Slider that stores decimal fractions (e.g. 0.05) but displays as % (5.00%)."""
    fmt = f"%.{decimals}f%%"
    v = st.slider(
        label,
        lo * 100.0, hi * 100.0, float(value) * 100.0, step * 100.0,
        format=fmt, key=key, help=help,
    )
    return v / 100.0


# ----------------------------------------------------------------------------
# Global controls
# ----------------------------------------------------------------------------
st.sidebar.title("Global settings")
preset = st.sidebar.selectbox(
    "Start from preset",
    ["baseline", "high asylum inflows", "high asylum grant rate", "police +10% over 3 years"],
    help="Resets all driver assumptions to the preset's defaults.",
)
preset_map = {
    "baseline": Scenario(name="baseline"),
    "high asylum inflows": high_asylum_inflows_scenario(),
    "high asylum grant rate": high_asylum_grant_rate_scenario(),
    "police +10% over 3 years": police_plus_10pct_scenario(),
}

# Rebuild scenario whenever the preset changes
if st.session_state.get("_preset") != preset:
    st.session_state["_preset"] = preset
    st.session_state["scen"] = preset_map[preset]

scen: Scenario = st.session_state["scen"]

real_or_nominal = st.sidebar.radio("Show values in", ["Real (2025-26 prices)", "Nominal"])
use_real = real_or_nominal.startswith("Real")
unit = "£m, 2025-26 prices" if use_real else "£m nominal"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def area_chart(series_or_df, title: str, yaxis: str):
    fig = px.line(series_or_df, markers=True)
    fig.update_layout(title=title, yaxis_title=yaxis, height=380,
                      hovermode="x unified", legend_title=None)
    fig.add_vline(x=len(HISTORIC_YEARS) - 0.5, line_dash="dash", line_color="grey")
    fig.add_vline(x=len(HISTORIC_YEARS) + len(SR25_YEARS) - 0.5,
                  line_dash="dot", line_color="grey")
    return fig


def run_current():
    result = run_projection(scen)
    rdel = result.rdel_real if use_real else result.rdel_nominal
    cdel = result.cdel_real if use_real else result.cdel_nominal
    totals = result.totals_real() if use_real else result.totals_nominal()
    totals["Total DEL"] = totals.sum(axis=1)
    return result, rdel.rename(columns=AREA_LABELS), cdel.rename(columns=AREA_LABELS), totals


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("Home Office spending model")
st.caption(
    "Driver-based projection of Home Office RDEL + CDEL across the SR25 period "
    "(to 2028-29) and SR27 period (to 2030-31). Real-terms figures in 2025-26 prices. "
    "Use each tab to explore the drivers of a specific programme area."
)


tabs = st.tabs([
    "🏠 Overview",
    "🛟 Asylum",
    "👮 Police",
    "🛂 Borders & Migration",
    "🛡️ Border Security Command",
    "🔐 Homeland Security",
    "🚒 Crime, Fire & Drugs",
    "🏢 Corporate & Admin",
    "🏗️ CDEL (capital)",
    "🔀 Compare scenarios",
    "⬇️ Export",
])


# ----------------------------------------------------------------------------
# 0 · Overview
# ----------------------------------------------------------------------------
with tabs[0]:
    result, rdel, cdel, totals = run_current()

    # ------- Envelope builder: SR25 published + SR27 extrapolation ------------
    env_nom_published = (result.sr25_envelope_nominal.copy()
                         if result.sr25_envelope_nominal is not None
                         else pd.DataFrame(columns=["RDEL", "CDEL"]))
    env_real_published = real_from_nominal(env_nom_published, result.deflator).reindex(
        columns=["RDEL", "CDEL"]
    )

    # Default SR27 real growth = observed SR25 CAGR on total envelope (2025-26 → 2028-29).
    if {"2025-26", "2028-29"}.issubset(env_real_published.index):
        total_start = env_real_published.loc["2025-26"].sum()
        total_end = env_real_published.loc["2028-29"].sum()
        n_years = int("2028-29"[:4]) - int("2025-26"[:4])  # 3
        sr25_cagr = (total_end / total_start) ** (1 / n_years) - 1
    else:
        sr25_cagr = 0.0
    default_sr27 = round(sr25_cagr / 0.0025) * 0.0025  # snap to slider step

    st.markdown(
        "**Budget envelope — SR25 years published; SR27 years extrapolated.** "
        f"SR25 implied real growth on total DEL was **{sr25_cagr * 100:+.2f}% p.a.** "
        "(used as the default below)."
    )
    sr27_real_growth = pct_slider(
        "SR27 real growth on overall budget p.a. (applied to both RDEL and CDEL from 2028-29)",
        -0.03, 0.04, float(default_sr27), 0.0025, key="o_sr27g",
    )

    env_real = env_real_published.copy()
    if "2028-29" in env_real.index:
        anchor = env_real.loc["2028-29"]
        for i, yr in enumerate(["2029-30", "2030-31"], start=1):
            env_real.loc[yr] = anchor * (1 + sr27_real_growth) ** i
    env_real = env_real.loc[PROJECTION_YEARS]
    env_nom = nominal_from_real(env_real, result.deflator)
    env = env_real if use_real else env_nom
    env["Total DEL"] = env["RDEL"] + env["CDEL"]

    # Forecast totals over projection years
    fc = totals.loc[PROJECTION_YEARS, ["RDEL", "CDEL", "Total DEL"]]
    gap = fc - env

    # ------- Headline KPIs: forecast vs envelope ------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "2025-26 Total DEL (model)",
        f"£{fc.loc['2025-26', 'Total DEL']:,.0f}m",
        delta=f"£{gap.loc['2025-26', 'Total DEL']:+,.0f}m vs envelope",
        delta_color="inverse",
    )
    c2.metric(
        "2028-29 (end SR25)",
        f"£{fc.loc['2028-29', 'Total DEL']:,.0f}m",
        delta=f"£{gap.loc['2028-29', 'Total DEL']:+,.0f}m vs envelope",
        delta_color="inverse",
    )
    c3.metric(
        "2030-31 (end SR27)",
        f"£{fc.loc['2030-31', 'Total DEL']:,.0f}m",
        delta=f"£{gap.loc['2030-31', 'Total DEL']:+,.0f}m vs envelope",
        delta_color="inverse",
    )
    c4.metric(
        "Cumulative gap 2025-26 → 2030-31",
        f"£{gap['Total DEL'].sum():+,.0f}m",
        help="Positive = model spend exceeds envelope.",
    )

    # ------- Forecast vs envelope chart ---------------------------------------
    st.subheader(f"Model forecast vs HO budget envelope ({unit})")

    fig_env = go.Figure()
    # RDEL: envelope solid, forecast dashed
    fig_env.add_trace(go.Scatter(
        x=env.index, y=env["RDEL"], name="RDEL — envelope",
        mode="lines+markers", line=dict(width=3, color="#1f77b4"),
    ))
    fig_env.add_trace(go.Scatter(
        x=fc.index, y=fc["RDEL"], name="RDEL — model",
        mode="lines+markers", line=dict(width=3, color="#1f77b4", dash="dash"),
    ))
    # CDEL: envelope solid, forecast dashed
    fig_env.add_trace(go.Scatter(
        x=env.index, y=env["CDEL"], name="CDEL — envelope",
        mode="lines+markers", line=dict(width=3, color="#e76f51"),
    ))
    fig_env.add_trace(go.Scatter(
        x=fc.index, y=fc["CDEL"], name="CDEL — model",
        mode="lines+markers", line=dict(width=3, color="#e76f51", dash="dash"),
    ))
    fig_env.add_vrect(
        x0="2028-29", x1="2030-31",
        fillcolor="#888", opacity=0.07, line_width=0,
        annotation_text="SR27 (extrapolated)", annotation_position="top right",
    )
    fig_env.update_layout(
        height=420, hovermode="x unified",
        yaxis_title=unit, legend_title=None,
        title="Envelope (solid) vs model (dashed). Positive gap = model exceeds envelope.",
    )
    st.plotly_chart(fig_env, width=W)

    # ------- Gap bar chart ----------------------------------------------------
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(
        x=gap.index, y=gap["RDEL"], name="RDEL gap",
        marker_color=["#e76f51" if v > 0 else "#2a9d8f" for v in gap["RDEL"]],
    ))
    fig_gap.add_trace(go.Bar(
        x=gap.index, y=gap["CDEL"], name="CDEL gap",
        marker_color=["#f4a261" if v > 0 else "#8dbfa5" for v in gap["CDEL"]],
    ))
    fig_gap.add_hline(y=0, line_color="black", line_width=1)
    fig_gap.update_layout(
        barmode="relative", height=300, hovermode="x unified",
        yaxis_title=f"Gap ({unit})", legend_title=None,
        title="Model − envelope gap by year (red = overspend, green = headroom)",
    )
    st.plotly_chart(fig_gap, width=W)

    # ------- Summary table ----------------------------------------------------
    summary = pd.DataFrame({
        "Envelope RDEL": env["RDEL"],
        "Model RDEL": fc["RDEL"],
        "Gap RDEL": gap["RDEL"],
        "Envelope CDEL": env["CDEL"],
        "Model CDEL": fc["CDEL"],
        "Gap CDEL": gap["CDEL"],
        "Gap Total": gap["Total DEL"],
    })
    st.dataframe(summary.style.format("{:,.0f}"), width=W)

    # ------- Continuity diagnostic --------------------------------------------
    st.subheader("Historic → projection continuity check")
    hist_year, proj_year = "2024-25", "2025-26"
    step_rdel = (rdel.loc[proj_year] / rdel.loc[hist_year].replace(0, pd.NA) - 1) * 100
    step_cdel = (cdel.loc[proj_year] / cdel.loc[hist_year].replace(0, pd.NA) - 1) * 100
    cont = pd.DataFrame({
        f"RDEL {hist_year}": rdel.loc[hist_year],
        f"RDEL {proj_year}": rdel.loc[proj_year],
        "RDEL Δ%": step_rdel,
        f"CDEL {hist_year}": cdel.loc[hist_year],
        f"CDEL {proj_year}": cdel.loc[proj_year],
        "CDEL Δ%": step_cdel,
    })
    THRESHOLD = 5.0

    def flag_style(v):
        try:
            if abs(float(v)) > THRESHOLD:
                return "background-color: #fde7e1"
        except (TypeError, ValueError):
            pass
        return ""

    styled = (
        cont.style
        .format({
            f"RDEL {hist_year}": "{:,.0f}", f"RDEL {proj_year}": "{:,.0f}",
            f"CDEL {hist_year}": "{:,.0f}", f"CDEL {proj_year}": "{:,.0f}",
            "RDEL Δ%": "{:+.1f}%", "CDEL Δ%": "{:+.1f}%",
        })
        .map(flag_style, subset=["RDEL Δ%", "CDEL Δ%"])
    )
    st.caption(
        f"Step change from {hist_year} outturn to {proj_year} model forecast. "
        f"Cells highlighted red when |Δ| > {THRESHOLD:.0f}%."
    )
    st.dataframe(styled, width=W)

    # ------- Existing RDEL by programme area ----------------------------------
    st.subheader(f"RDEL by programme area ({unit})")
    fig = px.area(rdel, x=rdel.index, y=rdel.columns,
                  labels={"x": "Year", "value": unit, "variable": "Area"})
    fig.add_vline(x=len(HISTORIC_YEARS) - 0.5, line_dash="dash", line_color="black",
                  annotation_text="historic → projection", annotation_position="top")
    fig.add_vline(x=len(HISTORIC_YEARS) + len(SR25_YEARS) - 0.5,
                  line_dash="dot", line_color="black",
                  annotation_text="SR25 → SR27", annotation_position="top")
    fig.update_layout(height=480, hovermode="x unified", legend_title=None)
    st.plotly_chart(fig, width=W)

    with st.expander("Full RDEL table"):
        st.dataframe(rdel.style.format("{:,.0f}"), width=W)
    with st.expander("Full CDEL table"):
        st.dataframe(cdel.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 1 · Asylum
# ----------------------------------------------------------------------------
with tabs[1]:
    st.header("Asylum & Protection")
    st.markdown(
        """
**What's in this area.** Supporting asylum seekers while cases are decided: hotel and
dispersal accommodation, subsistence, casework, legal, and third-country costs.

**How it's modelled — two-stock population.** Supported population = people
*awaiting an initial determination* plus people *on appeal* after an initial
refusal. Failed-appeal cases are assumed deported quickly enough to leave
support within the year.

- **Awaiting determination**: + new arrivals, − withdrawals, − initial decisions.
- **On appeal**: + initial refusals, − appeal decisions (both wins and losses
  leave support; losses are deported fast).
- **Withdrawals**: each year a share of the awaiting pool drops out (return
  home, abscond, regularise status) and leaves support without a decision.

**Decision capacity with reallocation.** One caseworker pool of
`total_decisions_capacity` is split between initial and appeal work. The
baseline split is `baseline_appeal_share`; when the appeal pool exceeds
`appeal_target_months` of baseline appeal flow, capacity shifts toward
appeals, up to `max_appeal_share`.

**Accommodation cost — capacity-constrained.** Dispersed accommodation is
filled up to `dispersal_capacity`; any residual population sits in hotels.
Marginal changes in the stock are therefore priced at the hotel £/night until
hotel use reaches zero.
        """
    )

    a = scen.asylum
    st.markdown("**Starting stocks & inflows**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        a.awaiting_determination_start = st.number_input(
            "Start — awaiting determination", 0, 400_000,
            int(a.awaiting_determination_start), 1_000, key="a_awd",
        )
    with c2:
        a.on_appeal_start = st.number_input(
            "Start — on appeal", 0, 200_000,
            int(a.on_appeal_start), 1_000, key="a_app",
        )
    with c3:
        a.new_arrivals_per_year = st.number_input(
            "New arrivals per year", 0, 200_000,
            int(a.new_arrivals_per_year), 1_000, key="a_arr",
        )
    with c4:
        a.withdrawal_rate = pct_slider(
            "Withdrawal rate (of awaiting pool / yr)", 0.0, 0.4,
            float(a.withdrawal_rate), 0.01, key="a_wr",
        )

    st.markdown("**Decision capacity & reallocation rule**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        a.total_decisions_capacity = st.number_input(
            "Total decisions capacity / yr", 0, 400_000,
            int(a.total_decisions_capacity), 5_000, key="a_cap",
        )
    with c2:
        a.baseline_appeal_share = pct_slider(
            "Baseline appeal share", 0.0, 0.8,
            float(a.baseline_appeal_share), 0.01, key="a_bas",
        )
    with c3:
        a.max_appeal_share = pct_slider(
            "Max appeal share (under divert)", 0.0, 0.9,
            float(a.max_appeal_share), 0.01, key="a_mas",
        )
    with c4:
        a.appeal_target_months = st.slider(
            "Appeal backlog target (months)", 3.0, 36.0,
            float(a.appeal_target_months), 1.0, key="a_tgt",
        )

    st.markdown("**Outcome rates**")
    c1, c2 = st.columns(2)
    with c1:
        a.initial_grant_rate = pct_slider(
            "Initial grant rate", 0.0, 1.0,
            float(a.initial_grant_rate), 0.01, key="a_igr",
        )
    with c2:
        a.appeal_success_rate = pct_slider(
            "Appeal success rate", 0.0, 1.0,
            float(a.appeal_success_rate), 0.01, key="a_asr",
        )

    st.markdown("**Accommodation & unit costs**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        a.dispersal_capacity = st.number_input(
            "Dispersal capacity (persons)", 0, 400_000,
            int(a.dispersal_capacity), 1_000, key="a_dcap",
        )
    with c2:
        a.hotel_cost_per_night = st.number_input(
            "Hotel £/night", 50.0, 300.0, float(a.hotel_cost_per_night), 5.0, key="a_hc"
        )
    with c3:
        a.dispersal_cost_per_night = st.number_input(
            "Dispersal £/night", 5.0, 80.0,
            float(a.dispersal_cost_per_night), 1.0, key="a_dc",
        )
    with c4:
        a.processing_cost_per_case = st.number_input(
            "£/case processing", 0.0, 40_000.0,
            float(a.processing_cost_per_case), 500.0, key="a_pc",
        )

    flow = project_asylum_population(scen)
    leavers = (
        flow["withdrawals"]
        + flow["initial_granted"]
        + flow["appeals_granted"]
        + flow["appeals_refused"]
    )
    net = flow["arrivals"] - leavers

    st.subheader("Supported population: stock & flows")
    cA, cB = st.columns([3, 2])
    with cA:
        fig_pop = go.Figure()
        fig_pop.add_trace(go.Bar(x=flow.index, y=flow["awaiting_end"],
                                 name="Awaiting determination",
                                 marker_color="#2a9d8f"))
        fig_pop.add_trace(go.Bar(x=flow.index, y=flow["on_appeal_end"],
                                 name="On appeal",
                                 marker_color="#f4a261"))
        fig_pop.add_trace(go.Scatter(x=flow.index, y=flow["pop_end"],
                                     mode="lines+markers",
                                     name="Total supported pop",
                                     line=dict(width=3, color="#264653")))
        fig_pop.update_layout(barmode="stack", height=420,
                              yaxis_title="People", hovermode="x unified",
                              legend_title=None,
                              title="End-of-year stock by pool")
        st.plotly_chart(fig_pop, width=W)
    with cB:
        fig_split = go.Figure()
        fig_split.add_trace(go.Bar(x=flow.index, y=flow["initial_granted"],
                                   name="Granted (initial)", marker_color="#264653"))
        fig_split.add_trace(go.Bar(x=flow.index, y=flow["appeals_granted"],
                                   name="Granted (appeal)", marker_color="#2a9d8f"))
        fig_split.add_trace(go.Bar(x=flow.index, y=flow["appeals_refused"],
                                   name="Appeal refused — deported",
                                   marker_color="#e76f51"))
        fig_split.add_trace(go.Bar(x=flow.index, y=flow["withdrawals"],
                                   name="Withdrawals", marker_color="#f4a261"))
        fig_split.update_layout(barmode="stack", height=420,
                                yaxis_title="People",
                                title="Annual outflows from support")
        st.plotly_chart(fig_split, width=W)

    st.subheader("Capacity reallocation to appeals")
    cap_df = pd.DataFrame({
        "Appeal share of capacity": flow["appeal_share"],
        "Target (baseline)": [a.baseline_appeal_share] * len(flow),
        "Ceiling": [a.max_appeal_share] * len(flow),
    })
    fig_share = go.Figure()
    fig_share.add_trace(go.Scatter(x=flow.index, y=flow["appeal_share"],
                                   mode="lines+markers", name="Appeal share",
                                   line=dict(width=3, color="#264653")))
    fig_share.add_hline(y=a.baseline_appeal_share, line_dash="dot",
                        annotation_text="Baseline", annotation_position="bottom left")
    fig_share.add_hline(y=a.max_appeal_share, line_dash="dash",
                        annotation_text="Max", annotation_position="top left")
    fig_share.update_layout(height=300, yaxis_title="Share of decisions capacity",
                            yaxis_tickformat=".0%",
                            title="Diversion toward appeals under the reallocation rule")
    st.plotly_chart(fig_share, width=W)

    st.subheader("Accommodation: hotel vs dispersal")
    fig_acc = go.Figure()
    fig_acc.add_trace(go.Bar(x=flow.index, y=flow["dispersal_pop"],
                             name="Dispersal", marker_color="#2a9d8f"))
    fig_acc.add_trace(go.Bar(x=flow.index, y=flow["hotel_pop"],
                             name="Hotel (residual)", marker_color="#e76f51"))
    fig_acc.add_hline(y=a.dispersal_capacity, line_dash="dash",
                      annotation_text="Dispersal capacity",
                      annotation_position="top left")
    fig_acc.update_layout(barmode="stack", height=360,
                          yaxis_title="People (mean across year)",
                          title="Accommodation mix at mean supported population")
    st.plotly_chart(fig_acc, width=W)

    st.dataframe(
        flow.assign(net_change=net).style.format("{:,.0f}"),
        width=W,
    )

    st.subheader(f"Asylum & Protection RDEL ({unit})")
    _, rdel, _, _ = run_current()
    s = rdel["Asylum & Protection"]
    st.plotly_chart(area_chart(s, f"Asylum & Protection RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)

    st.subheader("Historic outturn and model forecast")
    st.caption(
        "Outturn 2020–2024 (calendar years): indicative figures from Home Office "
        "*Immigration Statistics* (asylum support Asy_D11, initial decisions Asy_D02, "
        "returns Ret_D02). Forecast 2025-26 onwards: model output — *Enforced returns* "
        "uses failed-appeal cases (assumed deported within the year)."
    )
    historic_asylum = pd.DataFrame(
        {
            "Supported population (end of year)": [60_000, 78_000, 104_000, 112_000, 106_000],
            "Cases processed (initial decisions)": [14_000, 14_000, 19_000, 112_000, 110_000],
            "Granted asylum (initial decisions)":  [ 8_000,  9_000, 14_000,  76_000,  55_000],
            "Enforced returns of refused asylum seekers": [2_000, 2_000, 3_000, 4_000, 5_000],
        },
        index=["2020", "2021", "2022", "2023", "2024"],
    )
    historic_asylum.index.name = "Year"

    # Map FY "YYYY-YY+1" → CY "YYYY" — financial year-end (March) approximates
    # calendar year-end so forecast sits on the same axis as outturn.
    fy_to_cy = [yr[:4] for yr in flow.index]
    forecast_asylum = pd.DataFrame({
        "Supported population (end of year)": flow["pop_end"].values,
        "Cases processed (initial decisions)": flow["initial_decisions"].values,
        "Granted asylum (initial decisions)":  flow["initial_granted"].values,
        "Enforced returns of refused asylum seekers": flow["appeals_refused"].values,
    }, index=fy_to_cy)
    forecast_asylum.index.name = "Year"

    combined = pd.concat([historic_asylum, forecast_asylum])
    n_hist = len(historic_asylum)
    n_fc = len(forecast_asylum)
    is_forecast = [False] * n_hist + [True] * n_fc

    bar_specs = [
        ("Cases processed (initial decisions)",       "#9ecae1", "#d6eaf3"),
        ("Granted asylum (initial decisions)",        "#264653", "#8aa3a8"),
        ("Enforced returns of refused asylum seekers","#e76f51", "#f4bfad"),
    ]

    fig_hist = go.Figure()

    # Population as a single line; open marker for forecast points.
    fig_hist.add_trace(go.Scatter(
        x=combined.index,
        y=combined["Supported population (end of year)"],
        name="Supported population",
        mode="lines+markers",
        line=dict(width=3, color="#1f77b4"),
        marker=dict(
            size=9,
            color=["#1f77b4" if not f else "white" for f in is_forecast],
            line=dict(width=2, color="#1f77b4"),
            symbol=["circle" if not f else "diamond" for f in is_forecast],
        ),
    ))

    # One bar trace per metric, colours vary per-year (outturn vs forecast).
    for col, c_hist, c_fc in bar_specs:
        colours = [c_hist if not f else c_fc for f in is_forecast]
        fig_hist.add_trace(go.Bar(
            x=combined.index,
            y=combined[col],
            name=col.split(" (")[0],
            marker_color=colours,
        ))

    # Shaded forecast region (works with a categorical x-axis).
    fig_hist.add_vrect(
        x0=forecast_asylum.index[0], x1=forecast_asylum.index[-1],
        fillcolor="#888", opacity=0.06, line_width=0,
        annotation_text="Forecast", annotation_position="top right",
    )

    fig_hist.update_layout(
        barmode="group", height=460, hovermode="x unified",
        yaxis_title="People", legend_title=None,
        title=(
            f"Outturn {historic_asylum.index[0]}–{historic_asylum.index[-1]} "
            f"and model forecast {forecast_asylum.index[0]}–{forecast_asylum.index[-1]} "
            "(FY-end used as CY-end proxy)"
        ),
    )
    st.plotly_chart(fig_hist, width=W)
    st.caption("Paler bars and open diamond markers = model forecast; solid = outturn.")
    st.dataframe(combined.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 2 · Police
# ----------------------------------------------------------------------------
with tabs[2]:
    st.header("Police — HO Core Grant")
    st.markdown(
        """
**What's in this area.** The **HO Core Grant** for police in England & Wales —
the residual the Home Office has to fund once precept and other local income
are netted off gross force spending. This is the line that hits HO RDEL; the
gross pay bill and non-pay are modelled for context.

**Two key levers.** Police officer **numbers** (workforce FTE) and the nominal
**growth rate of precept income**. Everything else sits under *Advanced*.

**How gross spending is built up.** `Gross = Pay bill + Non-pay`, where the pay
bill = FTE × average pay × on-costs multiplier.

**Funding identity.** `Gross = HO Core Grant + Police Precept + Other income`.
Precept grows at a **nominal** rate (council-tax cap + base), converted back
to real using the GDP deflator. **HO Core Grant is the residual** — if gross
rises faster than precept + other, the HO grant has to grow to keep the force
whole (and vice versa). That HO residual is what feeds into the overview RDEL
total.
        """
    )
    p = scen.police
    st.markdown("**Key levers**")
    c1, c2 = st.columns(2)
    with c1:
        p.workforce_fte = st.number_input(
            "Police numbers (E&W officer FTE, 2025-26)", 100_000, 200_000,
            int(p.workforce_fte), 500, key="p_fte",
        )
        p.workforce_growth_per_year = pct_slider(
            "Workforce growth p.a.", -0.03, 0.03,
            float(p.workforce_growth_per_year), 0.0025, key="p_wg",
        )
    with c2:
        p.precept_nominal_growth = pct_slider(
            "Precept income growth p.a. (nominal)", -0.02, 0.10,
            float(p.precept_nominal_growth), 0.005, key="p_prg",
        )
        p.precept_income = st.number_input(
            "Precept income £m (2025-26)", 0.0, 15_000.0,
            float(p.precept_income), 50.0, key="p_pri",
        )

    with st.expander("Advanced — pay, non-pay, other income"):
        c1, c2, c3 = st.columns(3)
        with c1:
            p.avg_pay_per_fte = st.number_input(
                "Avg pay £/FTE", 30_000.0, 80_000.0,
                float(p.avg_pay_per_fte), 500.0, key="p_pay",
            )
            p.real_pay_award_per_year = pct_slider(
                "Real pay award p.a.", -0.02, 0.05,
                float(p.real_pay_award_per_year), 0.0025, key="p_pa",
            )
        with c2:
            p.on_costs_multiplier = st.slider(
                "On-costs multiplier", 1.0, 1.6,
                float(p.on_costs_multiplier), 0.01, key="p_oc",
            )
            p.staff_pay_gross = st.number_input(
                "Staff & PCSO pay £m (gross)", 0.0, 10_000.0,
                float(p.staff_pay_gross), 100.0, key="p_sp",
                help="Non-officer workforce pay (PCSOs, police staff). On-costs included.",
            )
            p.staff_pay_real_growth = pct_slider(
                "Staff pay real growth p.a.", -0.03, 0.05,
                float(p.staff_pay_real_growth), 0.005, key="p_spg",
            )
            p.non_pay_gross = st.number_input(
                "Non-pay gross £m (all funders)", 0.0, 20_000.0,
                float(p.non_pay_gross), 100.0, key="p_np",
            )
        with c3:
            p.non_pay_real_growth = pct_slider(
                "Non-pay real growth p.a.", -0.03, 0.05,
                float(p.non_pay_real_growth), 0.005, key="p_npg",
            )
            p.other_income = st.number_input(
                "Other income £m", 0.0, 5_000.0,
                float(p.other_income), 50.0, key="p_oi",
            )
            p.other_income_real_growth = pct_slider(
                "Other income real growth p.a.", -0.05, 0.05,
                float(p.other_income_real_growth), 0.005, key="p_oig",
            )

    result, rdel, _, _ = run_current()
    funding = project_police_funding(scen, deflator=result.deflator)

    # ------- Headline: HO Core Grant KPIs --------------------------------------
    # CAGR is measured in REAL terms (SR25 horizon); headline figures respect the unit toggle.
    hcg_real = funding["ho_core_grant"]
    hcg_25_real = hcg_real.loc["2025-26"]
    hcg_28_real = hcg_real.loc["2028-29"]
    real_cagr = (hcg_28_real / hcg_25_real) ** (1 / 3) - 1 if hcg_25_real > 0 else 0.0

    hcg_display = hcg_real if use_real else nominal_from_real(hcg_real, result.deflator)
    hcg_25_disp = hcg_display.loc["2025-26"]
    hcg_28_disp = hcg_display.loc["2028-29"]
    total_change_disp = hcg_28_disp - hcg_25_disp

    st.subheader(f"HO Core Grant — the key input to overall HO spending ({unit})")
    k1, k2, k3 = st.columns(3)
    k1.metric("2025-26 HO Core Grant", f"£{hcg_25_disp:,.0f}m")
    k2.metric(
        "2028-29 (end of SR25)", f"£{hcg_28_disp:,.0f}m",
        delta=f"£{total_change_disp:+,.0f}m vs 2025-26",
    )
    k3.metric("Implied real growth p.a.", f"{real_cagr * 100:+.1f}%")

    # ------- HO Core Grant trajectory: outturn + forecast ----------------------
    # Indicative HO Police Core Grant nominal £m (successive settlements + top-ups).
    hcg_hist_nominal = pd.Series(
        {
            "2020-21":  8_600.0,
            "2021-22":  9_100.0,
            "2022-23":  9_500.0,
            "2023-24": 10_100.0,
            "2024-25": 10_700.0,
        }
    )
    precept_hist_nominal = pd.Series(
        {
            "2020-21": 4_100.0,
            "2021-22": 4_400.0,
            "2022-23": 4_700.0,
            "2023-24": 5_000.0,
            "2024-25": 5_250.0,
        }
    )
    if use_real:
        hcg_hist = real_from_nominal(hcg_hist_nominal, result.deflator).rename(
            index=lambda y: y[:4])
        precept_hist = real_from_nominal(precept_hist_nominal, result.deflator).rename(
            index=lambda y: y[:4])
    else:
        hcg_hist = hcg_hist_nominal.rename(index=lambda y: y[:4])
        precept_hist = precept_hist_nominal.rename(index=lambda y: y[:4])

    if use_real:
        hcg_forecast = funding["ho_core_grant"]
        precept_forecast = funding["precept"]
    else:
        hcg_forecast = nominal_from_real(funding["ho_core_grant"], result.deflator)
        precept_forecast = nominal_from_real(funding["precept"], result.deflator)
    hcg_forecast = hcg_forecast.rename(index=lambda y: y[:4])
    precept_forecast = precept_forecast.rename(index=lambda y: y[:4])

    hcg_all = pd.concat([hcg_hist, hcg_forecast])
    prec_all = pd.concat([precept_hist, precept_forecast])
    n_hist = len(hcg_hist)
    is_fc_hcg = [False] * n_hist + [True] * len(hcg_forecast)

    fig_hcg = go.Figure()
    fig_hcg.add_trace(go.Scatter(
        x=hcg_all.index, y=hcg_all.values,
        mode="lines+markers", name="HO Core Grant",
        line=dict(width=3, color="#264653"),
        marker=dict(
            size=10,
            color=["#264653" if not f else "white" for f in is_fc_hcg],
            line=dict(width=2, color="#264653"),
            symbol=["circle" if not f else "diamond" for f in is_fc_hcg],
        ),
    ))
    fig_hcg.add_trace(go.Scatter(
        x=prec_all.index, y=prec_all.values,
        mode="lines+markers", name="Police precept",
        line=dict(width=2, color="#2a9d8f", dash="dot"),
        marker=dict(size=8,
                    color=["#2a9d8f" if not f else "white" for f in is_fc_hcg],
                    line=dict(width=2, color="#2a9d8f"),
                    symbol=["circle" if not f else "diamond" for f in is_fc_hcg]),
    ))
    fig_hcg.add_vrect(
        x0=hcg_forecast.index[0], x1=hcg_forecast.index[-1],
        fillcolor="#888", opacity=0.06, line_width=0,
        annotation_text="Forecast", annotation_position="top right",
    )
    fig_hcg.update_layout(
        height=420, yaxis_title=f"£m ({unit.replace('£m ', '')})",
        hovermode="x unified", legend_title=None,
        title=(
            f"HO Core Grant — outturn {hcg_hist.index[0]}–{hcg_hist.index[-1]} "
            f"and model forecast {hcg_forecast.index[0]}–{hcg_forecast.index[-1]}"
        ),
    )
    st.plotly_chart(fig_hcg, width=W)
    st.caption(
        "Solid circles = outturn (indicative HO Police Main/Core Grant + precept from "
        "the annual Police Funding Settlements). Open diamonds = model forecast. "
        "The HO Core Grant is the residual: Gross spend − Precept − Other income."
    )

    # ------- Funding stack: retained for context ------------------------------
    st.subheader(f"Full funding stack ({unit.replace('£m', '£m real')})")
    fig_f = go.Figure()
    fig_f.add_trace(go.Bar(x=funding.index, y=funding["ho_core_grant"],
                           name="HO Core Grant (residual)", marker_color="#264653"))
    fig_f.add_trace(go.Bar(x=funding.index, y=funding["precept"],
                           name="Police precept", marker_color="#2a9d8f"))
    fig_f.add_trace(go.Bar(x=funding.index, y=funding["other_income"],
                           name="Other income", marker_color="#f4a261"))
    fig_f.add_trace(go.Scatter(x=funding.index, y=funding["gross"],
                               mode="lines+markers", name="Gross spend",
                               line=dict(width=3, color="black")))
    fig_f.update_layout(barmode="stack", height=380, yaxis_title="£m (2025-26 prices)",
                        hovermode="x unified", legend_title=None,
                        title="Funding sources stack up to gross spending")
    st.plotly_chart(fig_f, width=W)
    st.dataframe(funding.style.format("{:,.0f}"), width=W)

    st.subheader("Police officer numbers — outturn and forecast")
    st.caption(
        "Outturn 2020–2024 (calendar years): indicative E&W police officer FTE at "
        "end-March of the following year. Forecast: workforce_fte × (1 + growth)^t. "
        "FY start-year used as calendar-year label."
    )
    # Indicative outturn (E&W officer FTE, near end-March of that FY / early next CY).
    police_hist = pd.Series(
        {
            "2020": 129_000,
            "2021": 136_000,
            "2022": 141_500,
            "2023": 147_400,
            "2024": 147_700,
        },
        name="Police FTE",
    )
    fte_forecast = pd.Series(
        {yr[:4]: p.workforce_fte * (1 + p.workforce_growth_per_year) ** t
         for yr, t in zip(PROJECTION_YEARS, range(len(PROJECTION_YEARS)))},
        name="Police FTE",
    )
    police_combined = pd.concat([police_hist, fte_forecast])
    n_hist = len(police_hist)
    is_forecast = [False] * n_hist + [True] * len(fte_forecast)

    fig_fte = go.Figure()
    fig_fte.add_trace(go.Scatter(
        x=police_combined.index, y=police_combined.values,
        mode="lines+markers",
        name="Police officer FTE",
        line=dict(width=3, color="#1f77b4"),
        marker=dict(
            size=10,
            color=["#1f77b4" if not f else "white" for f in is_forecast],
            line=dict(width=2, color="#1f77b4"),
            symbol=["circle" if not f else "diamond" for f in is_forecast],
        ),
    ))
    fig_fte.add_vrect(
        x0=fte_forecast.index[0], x1=fte_forecast.index[-1],
        fillcolor="#888", opacity=0.06, line_width=0,
        annotation_text="Forecast", annotation_position="top right",
    )
    fig_fte.update_layout(
        height=360, yaxis_title="Officer FTE",
        hovermode="x unified", legend_title=None,
        title=(
            f"Outturn {police_hist.index[0]}–{police_hist.index[-1]} "
            f"and forecast {fte_forecast.index[0]}–{fte_forecast.index[-1]}"
        ),
    )
    st.plotly_chart(fig_fte, width=W)
    st.caption("Open diamonds = model forecast; solid circles = outturn.")

    s = rdel["Police (core + CT grant)"]
    st.plotly_chart(area_chart(s, f"Police line on HO RDEL — HO Core Grant ({unit})", unit), width=W)


# ----------------------------------------------------------------------------
# 3 · Borders & Migration
# ----------------------------------------------------------------------------
with tabs[3]:
    st.header("Borders & Migration")
    st.markdown(
        """
**What's in this area.** Border Force (ports & airports) plus UK Visas & Immigration
(gross spend offset by visa fee income).

**How it's modelled.** Border Force pay bill = FTE × pay × on-costs. FTE and pay
each escalate at their own real growth rate. BF non-pay (equipment, contracts)
grows at its own real rate and scales linearly with a passenger-volume index.
UKVI gross RDEL escalates at its own real rate and is netted off by fee
income, which also grows in real terms at the fee-growth rate.
        """
    )
    b = scen.borders
    st.markdown("**Border Force workforce & pay**")
    c1, c2, c3 = st.columns(3)
    with c1:
        b.border_force_fte = st.number_input(
            "Border Force FTE", 5_000, 20_000, int(b.border_force_fte), 100, key="b_fte"
        )
    with c2:
        b.border_force_workforce_growth = pct_slider(
            "BF workforce growth p.a.", -0.03, 0.03,
            float(b.border_force_workforce_growth), 0.0025, key="b_wg",
        )
    with c3:
        b.border_force_pay_per_fte = st.number_input(
            "BF pay £/FTE", 30_000.0, 70_000.0,
            float(b.border_force_pay_per_fte), 500.0, key="b_pay",
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        b.border_force_pay_real_growth = pct_slider(
            "BF real pay growth p.a.", -0.02, 0.04,
            float(b.border_force_pay_real_growth), 0.0025, key="b_pg",
        )
    with c2:
        b.border_force_non_pay = st.number_input(
            "BF non-pay RDEL £m", 0.0, 3_000.0,
            float(b.border_force_non_pay), 25.0, key="b_np",
        )
    with c3:
        b.border_force_non_pay_real_growth = pct_slider(
            "BF non-pay real growth p.a.", -0.03, 0.05,
            float(b.border_force_non_pay_real_growth), 0.005, key="b_npg",
        )

    c1, c2 = st.columns(2)
    with c1:
        b.passenger_volume_index = st.slider(
            "Passenger volume index", 0.7, 1.5,
            float(b.passenger_volume_index), 0.05, key="b_pi",
        )

    st.markdown("**UKVI gross RDEL net of fees**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b.ukvi_gross_rdel = st.number_input(
            "UKVI gross RDEL £m", 500.0, 5_000.0,
            float(b.ukvi_gross_rdel), 50.0, key="b_ug",
        )
    with c2:
        b.ukvi_gross_real_growth = pct_slider(
            "UKVI gross real growth p.a.", -0.03, 0.05,
            float(b.ukvi_gross_real_growth), 0.005, key="b_ugg",
        )
    with c3:
        b.ukvi_fee_income = st.number_input(
            "UKVI fee income £m", 0.0, 5_000.0,
            float(b.ukvi_fee_income), 50.0, key="b_fi",
        )
    with c4:
        b.fee_real_growth = pct_slider(
            "Fee income real growth p.a.", -0.05, 0.10,
            float(b.fee_real_growth), 0.005, key="b_fg",
        )

    _, rdel, _, _ = run_current()
    s = rdel["Borders & Migration"]
    st.plotly_chart(area_chart(s, f"Borders & Migration RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 4 · Border Security Command
# ----------------------------------------------------------------------------
with tabs[4]:
    st.header("Border Security Command")
    st.markdown(
        """
**What's in this area.** Standalone command set up to disrupt organised immigration
crime. Funded on top of Borders & Migration.

**How it's modelled.** SR25 announced *+£280m RDEL by 2028-29* on top of a 2025-26
baseline. The model interpolates between the two anchors and then holds real in the
SR27 period:

- **Linear profile**: equal +¼ of the uplift each year.
- **Backloaded profile**: 20% / 50% / 100% delivered by 2026-27 / 2027-28 / 2028-29.
        """
    )
    bsc = scen.bsc
    c1, c2, c3 = st.columns(3)
    with c1:
        bsc.baseline_rdel_2025_26 = st.number_input(
            "Baseline 2025-26 £m", 0.0, 1_000.0,
            float(bsc.baseline_rdel_2025_26), 10.0, key="bsc_base",
        )
    with c2:
        bsc.plus_by_2028_29 = st.number_input(
            "Uplift by 2028-29 £m", 0.0, 1_000.0,
            float(bsc.plus_by_2028_29), 10.0, key="bsc_up",
        )
    with c3:
        bsc.profile = st.selectbox(
            "Profile", ["linear", "backloaded"],
            index=0 if bsc.profile == "linear" else 1, key="bsc_prof",
        )

    _, rdel, _, _ = run_current()
    s = rdel["Border Security Command"]
    st.plotly_chart(area_chart(s, f"Border Security Command RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 5 · Homeland Security
# ----------------------------------------------------------------------------
with tabs[5]:
    st.header("Homeland Security")
    st.markdown(
        """
**What's in this area.** Counter-terrorism coordination, state threats, protective
security and Prevent — excluding CT policing (which sits under Police).

**How it's modelled.** A single baseline in 2025-26 prices, grown at a real rate:

$$\\text{RDEL}_t = \\text{baseline} \\cdot (1+g)^t$$
        """
    )
    o = scen.other
    c1, c2 = st.columns(2)
    with c1:
        o.homeland_security_baseline = st.number_input(
            "Baseline 2025-26 £m", 0.0, 5_000.0,
            float(o.homeland_security_baseline), 25.0, key="hs_b",
        )
    with c2:
        o.homeland_security_real_growth = pct_slider(
            "Real growth p.a.", -0.05, 0.10,
            float(o.homeland_security_real_growth), 0.005, key="hs_g",
        )

    _, rdel, _, _ = run_current()
    s = rdel["Homeland Security"]
    st.plotly_chart(area_chart(s, f"Homeland Security RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 6 · Crime, Fire & Drugs
# ----------------------------------------------------------------------------
with tabs[6]:
    st.header("Crime, Fire & Drugs")
    st.markdown(
        """
**What's in this area.** Fire & Rescue grants, drugs strategy, crime prevention
programmes, violence against women & girls funding.

**How it's modelled.** Same form as Homeland Security — baseline × real growth.
The baseline real-growth rate is negative (−1% p.a.) reflecting the SR25 trajectory
of declining non-core grants.
        """
    )
    o = scen.other
    c1, c2 = st.columns(2)
    with c1:
        o.crime_fire_drugs_baseline = st.number_input(
            "Baseline 2025-26 £m", 0.0, 5_000.0,
            float(o.crime_fire_drugs_baseline), 25.0, key="cfd_b",
        )
    with c2:
        o.crime_fire_drugs_real_growth = pct_slider(
            "Real growth p.a.", -0.05, 0.05,
            float(o.crime_fire_drugs_real_growth), 0.005, key="cfd_g",
        )

    _, rdel, _, _ = run_current()
    s = rdel["Crime, Fire & Drugs"]
    st.plotly_chart(area_chart(s, f"Crime, Fire & Drugs RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 7 · Corporate & Admin
# ----------------------------------------------------------------------------
with tabs[7]:
    st.header("Corporate & Admin")
    st.markdown(
        """
**What's in this area.** Departmental HQ, finance, HR, digital corporate services,
estates — the admin envelope controlled under SR25's efficiency targets.

**How it's modelled.** SR25 specifies *nominal* admin budgets year-by-year from
2025-26 to 2028-29 (declining ~10% in real terms). The model converts those
figures to real using the GDP deflator, then extrapolates the SR27 period at a
configurable real growth rate.
        """
    )
    o = scen.other
    st.markdown("**SR25 nominal envelope (£m):**")
    cols = st.columns(len(o.corporate_admin_by_year))
    for col, (yr, val) in zip(cols, sorted(o.corporate_admin_by_year.items())):
        with col:
            o.corporate_admin_by_year[yr] = st.number_input(
                yr, 0.0, 2_000.0, float(val), 5.0, key=f"ca_{yr}"
            )
    o.corporate_admin_real_growth_sr27 = pct_slider(
        "SR27 real growth p.a.", -0.05, 0.03,
        float(o.corporate_admin_real_growth_sr27), 0.005, key="ca_g",
    )

    _, rdel, _, _ = run_current()
    s = rdel["Corporate & Admin"]
    st.plotly_chart(area_chart(s, f"Corporate & Admin RDEL ({unit})", unit), width=W)
    st.dataframe(s.to_frame().T.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 8 · CDEL
# ----------------------------------------------------------------------------
with tabs[8]:
    st.header("CDEL (capital)")
    st.markdown(
        """
**What's in this area.** Capital spending across all programme areas — mostly
digital systems, borders/immigration infrastructure, police tech grants, and
the HO estate.

**How it's modelled.** Total CDEL is taken from the published SR25 envelope
for SR25 years (deflated to real). Beyond the envelope, the total grows at
the SR27 real growth rate below. The total is then split across areas by
fixed shares (default shares match the historic PESA profile).
        """
    )
    c = scen.cdel
    c1, c2 = st.columns(2)
    with c1:
        c.total_cdel_2025_26_fallback = st.number_input(
            "Fallback total CDEL £m (used only if envelope missing)",
            500.0, 5_000.0,
            float(c.total_cdel_2025_26_fallback), 25.0, key="cdel_t",
        )
    with c2:
        c.sr27_real_growth = pct_slider(
            "SR27 real growth p.a. (CDEL)",
            -0.05, 0.10, float(c.sr27_real_growth), 0.005, key="cdel_g",
        )

    st.markdown("**CDEL split across areas (shares should sum to 1):**")
    cols = st.columns(len(c.split))
    new_split = {}
    for col, (area, share) in zip(cols, c.split.items()):
        with col:
            new_split[area] = st.number_input(
                AREA_LABELS.get(area, area), 0.0, 1.0, float(share), 0.01, key=f"cdel_sp_{area}"
            )
    c.split = new_split
    share_total = sum(new_split.values())
    if abs(share_total - 1.0) > 0.01:
        st.warning(f"Shares sum to {share_total:.2f}, not 1.00 — results will scale accordingly.")

    _, _, cdel, _ = run_current()
    st.plotly_chart(
        area_chart(cdel, f"CDEL by area ({unit})", unit), width=W
    )
    st.dataframe(cdel.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 9 · Scenario comparison
# ----------------------------------------------------------------------------
with tabs[9]:
    st.header("Preset scenario comparison")
    st.caption(
        "Runs the four built-in presets side-by-side (using their default parameters) "
        "for total DEL in real 2025-26 prices."
    )
    comp = compare_scenarios([
        Scenario(name="baseline"),
        high_asylum_inflows_scenario(),
        high_asylum_grant_rate_scenario(),
        police_plus_10pct_scenario(),
    ])
    pivot = comp.pivot_table(index="year", columns="scenario",
                             values="total_real", aggfunc="first")
    fig = px.line(pivot, markers=True,
                  labels={"value": "Total DEL, £m (2025-26 prices)", "year": "Year"})
    fig.update_layout(height=450, hovermode="x unified", legend_title=None)
    st.plotly_chart(fig, width=W)
    st.dataframe(pivot.style.format("{:,.0f}"), width=W)


# ----------------------------------------------------------------------------
# 10 · Export
# ----------------------------------------------------------------------------
with tabs[10]:
    st.header("Download results")
    result, rdel, cdel, totals = run_current()

    # Assumptions dump (cast everything to str to avoid Arrow mixed-type errors)
    rows = []
    for group, params in asdict(scen).items():
        if group in {"name", "description"}:
            continue
        if isinstance(params, dict):
            for k, v in params.items():
                rows.append({"Group": group, "Parameter": k, "Value": str(v)})
    assumptions_df = pd.DataFrame(rows)
    st.subheader("Current assumptions")
    st.dataframe(assumptions_df, width=W, hide_index=True)

    name = scen.name.replace(" ", "_")

    # ---------- Excel workbook: one-click snapshot of the whole scenario -------
    def build_excel_bytes() -> bytes:
        """Assemble a multi-sheet xlsx with assumptions, totals, per-area matrices,
        long-format results, and the asylum + police driver detail."""
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            assumptions_df.to_excel(xw, sheet_name="Assumptions", index=False)
            result.totals_real().round(1).to_excel(xw, sheet_name="Totals (real)")
            result.totals_nominal().round(1).to_excel(xw, sheet_name="Totals (nominal)")
            (result.rdel_real.rename(columns=AREA_LABELS).round(1)
                .to_excel(xw, sheet_name="RDEL by area (real)"))
            (result.rdel_nominal.rename(columns=AREA_LABELS).round(1)
                .to_excel(xw, sheet_name="RDEL by area (nominal)"))
            (result.cdel_real.rename(columns=AREA_LABELS).round(1)
                .to_excel(xw, sheet_name="CDEL by area (real)"))
            (result.cdel_nominal.rename(columns=AREA_LABELS).round(1)
                .to_excel(xw, sheet_name="CDEL by area (nominal)"))
            result.long.to_excel(xw, sheet_name="Long format", index=False)
            if result.sr25_envelope_nominal is not None:
                result.sr25_envelope_nominal.to_excel(xw, sheet_name="SR25 envelope (nominal)")
            try:
                asylum_trace = project_asylum_population(scen).round(1)
                asylum_trace.to_excel(xw, sheet_name="Asylum population")
            except Exception:
                pass
            try:
                police_trace = project_police_funding(scen, deflator=result.deflator).round(1)
                police_trace.to_excel(xw, sheet_name="Police funding")
            except Exception:
                pass
        return buf.getvalue()

    st.download_button(
        "📥 Full Excel workbook (all sheets)",
        data=build_excel_bytes(),
        file_name=f"home_office_{name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    st.markdown("**Individual CSVs**")
    st.download_button("Assumptions CSV",
                       assumptions_df.to_csv(index=False).encode("utf-8"),
                       f"home_office_{name}_assumptions.csv", "text/csv")
    st.download_button("Long-format results CSV",
                       result.long.to_csv(index=False).encode("utf-8"),
                       f"home_office_{name}_long.csv", "text/csv")
    st.download_button(f"RDEL ({unit}) CSV",
                       rdel.to_csv().encode("utf-8"),
                       f"home_office_{name}_rdel.csv", "text/csv")
    st.download_button(f"CDEL ({unit}) CSV",
                       cdel.to_csv().encode("utf-8"),
                       f"home_office_{name}_cdel.csv", "text/csv")
    st.download_button(f"Totals ({unit}) CSV",
                       totals.to_csv().encode("utf-8"),
                       f"home_office_{name}_totals.csv", "text/csv")
