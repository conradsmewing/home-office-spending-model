from pathlib import Path

import pandas as pd

from .config import BASE_YEAR, DATA_RAW


def load_deflator(path: Path | None = None) -> pd.Series:
    """Load the GDP deflator as a Series indexed by financial year (e.g. '2025-26').

    Looks for data/raw/gdp_deflator.csv first (user-provided), falling back to
    the seed CSV bundled with the repo.
    """
    if path is None:
        candidate = DATA_RAW / "gdp_deflator.csv"
        path = candidate if candidate.exists() else DATA_RAW / "gdp_deflator_seed.csv"
    df = pd.read_csv(path)
    df["year"] = df["year"].astype(str)
    return df.set_index("year")["deflator_index"].astype(float)


def rebase(series: pd.Series, base_year: str = BASE_YEAR) -> pd.Series:
    """Return a deflator series rebased so base_year = 100."""
    if base_year not in series.index:
        raise KeyError(f"Base year {base_year} not in deflator series")
    return series / series.loc[base_year] * 100.0


def real_from_nominal(
    nominal: pd.Series | pd.DataFrame,
    deflator: pd.Series,
    base_year: str = BASE_YEAR,
) -> pd.Series | pd.DataFrame:
    """Convert nominal £ to real £ at base_year prices.

    Expects the object to be indexed by financial year strings.
    """
    rebased = rebase(deflator, base_year)
    factor = 100.0 / rebased
    if isinstance(nominal, pd.DataFrame):
        return nominal.mul(factor.reindex(nominal.index), axis=0)
    return nominal.mul(factor.reindex(nominal.index))


def nominal_from_real(
    real: pd.Series | pd.DataFrame,
    deflator: pd.Series,
    base_year: str = BASE_YEAR,
) -> pd.Series | pd.DataFrame:
    """Convert real £ at base_year prices to nominal £."""
    rebased = rebase(deflator, base_year)
    factor = rebased / 100.0
    if isinstance(real, pd.DataFrame):
        return real.mul(factor.reindex(real.index), axis=0)
    return real.mul(factor.reindex(real.index))
