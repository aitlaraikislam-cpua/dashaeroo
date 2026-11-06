from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "aeronex.db"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.execute("""CREATE TABLE IF NOT EXISTS maintenance_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, aircraft_reg TEXT NOT NULL,
        task TEXT NOT NULL, due_date TEXT NOT NULL, priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Planned', assigned_to TEXT DEFAULT '', notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS parts_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, part_number TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0,
        min_quantity INTEGER NOT NULL DEFAULT 0, location TEXT DEFAULT '',
        unit_cost REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
        specialty TEXT DEFAULT '', station TEXT DEFAULT '', email TEXT DEFAULT '',
        availability TEXT DEFAULT 'Disponible', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    return con

def read_table(table):
    if table not in {"maintenance_plan","parts_inventory","technicians"}:
        raise ValueError("Table non autorisée")
    with connect() as con:
        return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id DESC", con)

def add_record(table, values):
    allowed = {
      "maintenance_plan":{"aircraft_reg","task","due_date","priority","status","assigned_to","notes"},
      "parts_inventory":{"part_number","description","quantity","min_quantity","location","unit_cost"},
      "technicians":{"full_name","specialty","station","email","availability"}
    }
    if table not in allowed or set(values) - allowed[table]:
        raise ValueError("Champs invalides")
    cols=list(values)
    with connect() as con:
        con.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                    [values[c] for c in cols])
        con.commit()

def delete_record(table, record_id):
    if table not in {"maintenance_plan","parts_inventory","technicians"}:
        raise ValueError("Table non autorisée")
    with connect() as con:
        con.execute(f"DELETE FROM {table} WHERE id=?", (int(record_id),))
        con.commit()
