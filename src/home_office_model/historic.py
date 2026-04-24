from pathlib import Path

import pandas as pd

from .config import AREAS, BUDGET_TYPES, DATA_RAW, HISTORIC_YEARS


def load_historic(path: Path | None = None) -> pd.DataFrame:
    """Load historic RDEL/CDEL outturn, returning a tidy long DataFrame.

    Columns: year, area, budget_type, value_gbp_m, source
    Values are in nominal £ million.
    """
    if path is None:
        candidate = DATA_RAW / "historic.csv"
        path = candidate if candidate.exists() else DATA_RAW / "historic_seed.csv"
    df = pd.read_csv(path)
    df["year"] = df["year"].astype(str)
    df["value_gbp_m"] = df["value_gbp_m"].astype(float)
    return df


def historic_wide(df: pd.DataFrame, budget_type: str = "RDEL") -> pd.DataFrame:
    """Pivot to year × area wide matrix for a given budget_type."""
    sub = df[df["budget_type"] == budget_type]
    wide = sub.pivot_table(index="year", columns="area", values="value_gbp_m", aggfunc="sum")
    wide = wide.reindex(index=HISTORIC_YEARS, columns=AREAS).fillna(0.0)
    return wide


def historic_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Return a year × budget_type total matrix."""
    return df.pivot_table(index="year", columns="budget_type", values="value_gbp_m", aggfunc="sum")


def load_sr25_envelope(path: Path | None = None) -> pd.DataFrame | None:
    """Load the published SR25 envelope (PESA plans for 2025-26 onwards), if available.

    Returns None if the file doesn't exist (model still runs with driver projections only).
    """
    path = path or DATA_RAW / "sr25_envelope.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["year"] = df["year"].astype(str)
    return df.pivot_table(index="year", columns="budget_type", values="value_gbp_m", aggfunc="sum")
