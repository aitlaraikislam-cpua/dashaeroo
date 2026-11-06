from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "ait_laraik_islam.csv"
DATE_COLUMNS = ["open_datetime", "close_datetime"]
NUMERIC_COLUMNS = [
    "aircraft_age_years", "flight_hours_total", "flight_cycles_total",
    "ata_chapter", "labor_hours", "technicians", "parts_cost_usd",
    "labor_cost_usd", "total_cost_usd", "aircraft_downtime_h", "flight_delay_min"
]


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Keep source records; do not silently delete rows. Missing close dates can
    # represent work orders that are still in progress.
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].fillna("Non renseigné")
    return df


def quality_summary(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_work_orders": int(df["work_order_id"].duplicated().sum()),
        "missing_close_dates": int(df["close_datetime"].isna().sum()),
        "missing_values": int(df.isna().sum().sum()),
    }
