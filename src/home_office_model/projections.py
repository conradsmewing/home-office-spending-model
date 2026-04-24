"""Projection orchestrator.

Combines a historic outturn series with a driver-based projection for SR25
(2025-26 to 2028-29) and SR27 (2029-30 to 2030-31) periods. Returns a tidy
long DataFrame with both nominal and real (2025-26 prices) figures.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import AREAS, BASE_YEAR, HISTORIC_YEARS, PROJECTION_YEARS
from .deflator import load_deflator, nominal_from_real, real_from_nominal
from .drivers import (
    project_asylum_real,
    project_borders_real,
    project_bsc_real,
    project_corporate_admin_real,
    project_crime_fire_drugs_real,
    project_homeland_security_real,
    project_police_real,
    project_cdel_real,
)
from .historic import historic_wide, load_historic, load_sr25_envelope
from .scenarios import Scenario


@dataclass
class ProjectionResult:
    long: pd.DataFrame            # tidy: year, area, budget_type, value_real, value_nominal, source
    rdel_real: pd.DataFrame       # year × area, real £m
    cdel_real: pd.DataFrame       # year × area, real £m
    rdel_nominal: pd.DataFrame
    cdel_nominal: pd.DataFrame
    deflator: pd.Series
    scenario: Scenario
    sr25_envelope_nominal: pd.DataFrame | None = None

    def totals_real(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"RDEL": self.rdel_real.sum(axis=1), "CDEL": self.cdel_real.sum(axis=1)}
        )

    def totals_nominal(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"RDEL": self.rdel_nominal.sum(axis=1), "CDEL": self.cdel_nominal.sum(axis=1)}
        )

    def envelope_gap(self) -> pd.DataFrame | None:
        """Driver projection vs published SR25 envelope, nominal £m.

        A positive gap means the driver model projects more spending than the SR25
        envelope — i.e. the scenario is inconsistent with the published settlement.
        """
        if self.sr25_envelope_nominal is None:
            return None
        model_tot = self.totals_nominal()
        env = self.sr25_envelope_nominal
        gap = (model_tot - env).dropna(how="all")
        gap["TOTAL"] = gap.sum(axis=1)
        return gap


def _driver_rdel_real(scenario: Scenario, deflator: pd.Series) -> pd.DataFrame:
    """Return a year × area DataFrame of projected RDEL in real £m (base year prices)."""
    series = [
        project_asylum_real(scenario),
        project_borders_real(scenario),
        project_bsc_real(scenario),
        project_police_real(scenario, deflator),
        project_homeland_security_real(scenario),
        project_crime_fire_drugs_real(scenario),
        project_corporate_admin_real(scenario, deflator),
    ]
    df = pd.concat(series, axis=1)
    df = df.reindex(columns=AREAS)
    return df


def run_projection(scenario: Scenario | None = None) -> ProjectionResult:
    scenario = scenario or Scenario()
    deflator = load_deflator()

    # --- Historic: nominal outturn from CSV ---
    hist = load_historic()
    rdel_hist_nom = historic_wide(hist, "RDEL")
    cdel_hist_nom = historic_wide(hist, "CDEL")
    rdel_hist_real = real_from_nominal(rdel_hist_nom, deflator)
    cdel_hist_real = real_from_nominal(cdel_hist_nom, deflator)

    # --- Projection: driver-based real-terms values ---
    envelope = load_sr25_envelope()
    rdel_proj_real = _driver_rdel_real(scenario, deflator)
    cdel_proj_real = project_cdel_real(
        scenario, deflator=deflator, sr25_envelope_nominal=envelope,
    ).reindex(columns=AREAS).fillna(0.0)

    rdel_proj_nom = nominal_from_real(rdel_proj_real, deflator)
    cdel_proj_nom = nominal_from_real(cdel_proj_real, deflator)

    # --- Stitch historic + projection ---
    rdel_real = pd.concat([rdel_hist_real, rdel_proj_real]).reindex(
        index=HISTORIC_YEARS + PROJECTION_YEARS, columns=AREAS
    ).fillna(0.0)
    cdel_real = pd.concat([cdel_hist_real, cdel_proj_real]).reindex(
        index=HISTORIC_YEARS + PROJECTION_YEARS, columns=AREAS
    ).fillna(0.0)
    rdel_nominal = pd.concat([rdel_hist_nom, rdel_proj_nom]).reindex(
        index=HISTORIC_YEARS + PROJECTION_YEARS, columns=AREAS
    ).fillna(0.0)
    cdel_nominal = pd.concat([cdel_hist_nom, cdel_proj_nom]).reindex(
        index=HISTORIC_YEARS + PROJECTION_YEARS, columns=AREAS
    ).fillna(0.0)

    # --- Long form ---
    records = []
    for budget_type, real_df, nom_df in [
        ("RDEL", rdel_real, rdel_nominal),
        ("CDEL", cdel_real, cdel_nominal),
    ]:
        for yr in real_df.index:
            source = "historic" if yr in HISTORIC_YEARS else "projection"
            for area in AREAS:
                records.append(
                    {
                        "year": yr,
                        "area": area,
                        "budget_type": budget_type,
                        "value_real_2025_26_gbp_m": real_df.loc[yr, area],
                        "value_nominal_gbp_m": nom_df.loc[yr, area],
                        "source": source,
                    }
                )
    long = pd.DataFrame.from_records(records)

    return ProjectionResult(
        long=long,
        rdel_real=rdel_real,
        cdel_real=cdel_real,
        rdel_nominal=rdel_nominal,
        cdel_nominal=cdel_nominal,
        deflator=deflator,
        scenario=scenario,
        sr25_envelope_nominal=envelope,
    )


def compare_scenarios(scenarios: list[Scenario]) -> pd.DataFrame:
    """Run multiple scenarios and return a comparison table of total real DEL by year."""
    frames = []
    for s in scenarios:
        result = run_projection(s)
        totals = result.totals_real()
        totals["total_real"] = totals.sum(axis=1)
        totals["scenario"] = s.name
        totals["year"] = totals.index
        frames.append(totals.reset_index(drop=True))
    return pd.concat(frames, ignore_index=True)
