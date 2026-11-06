import pandas as pd

SCHEDULED_TYPES = {"Daily Check", "Weekly Check", "Line Check", "A-Check", "C-Check"}


def calculate_kpis(df: pd.DataFrame) -> dict:
    orders = df["work_order_id"].nunique()
    repeat_count = int(df.loc[df["repeat_defect"].astype(str).str.lower().eq("yes"), "work_order_id"].nunique())
    aog_mask = (df["maintenance_type"].astype(str).str.upper().eq("AOG") |
                df["priority"].astype(str).str.upper().eq("AOG"))
    return {
        "orders": orders,
        "cost": float(df["total_cost_usd"].sum()),
        "downtime": float(df["aircraft_downtime_h"].sum()),
        "avg_downtime": float(df["aircraft_downtime_h"].mean()) if len(df) else 0,
        "delay": int(df["flight_delay_min"].sum()),
        "repeat_rate": (repeat_count / orders * 100) if orders else 0,
        "aog": int(df.loc[aog_mask, "work_order_id"].nunique()),
        "open": int(df.loc[df["status"].astype(str).str.lower().eq("open"), "work_order_id"].nunique()),
        "parts": float(df["parts_cost_usd"].sum()),
        "labor": float(df["labor_cost_usd"].sum()),
    }


def add_maintenance_group(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["maintenance_group"] = out["maintenance_type"].apply(
        lambda x: "Programmée" if x in SCHEDULED_TYPES else "Non programmée / autre"
    )
    return out
