from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

BASE_YEAR = "2025-26"

HISTORIC_START = "2020-21"     # PESA 2025 covers 2020-21 onwards
HISTORIC_END = "2024-25"
SR25_YEARS = ["2025-26", "2026-27", "2027-28", "2028-29"]
SR27_YEARS = ["2029-30", "2030-31"]


def fy_range(start: str, end: str) -> list[str]:
    s = int(start[:4])
    e = int(end[:4])
    return [f"{y}-{str(y + 1)[-2:]}" for y in range(s, e + 1)]


HISTORIC_YEARS = fy_range(HISTORIC_START, HISTORIC_END)
PROJECTION_YEARS = SR25_YEARS + SR27_YEARS
ALL_YEARS = HISTORIC_YEARS + PROJECTION_YEARS

AREAS = [
    "asylum_support",
    "borders_migration",
    "border_security_command",
    "police",
    "homeland_security",
    "crime_fire_drugs",
    "corporate_admin",
]

AREA_LABELS = {
    "asylum_support": "Asylum & Protection",
    "borders_migration": "Borders & Migration",
    "border_security_command": "Border Security Command",
    "police": "Police (core + CT grant)",
    "homeland_security": "Homeland Security",
    "crime_fire_drugs": "Crime, Fire & Drugs",
    "corporate_admin": "Corporate & Admin",
}

BUDGET_TYPES = ["RDEL", "CDEL"]
