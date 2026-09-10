from __future__ import annotations

import os
import sqlite3
import re
from pathlib import Path as FilePath
from contextlib import contextmanager
from typing import Generator, Any

from dotenv import load_dotenv

# Load .env file from the backend directory
_env_path = FilePath(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

DATABASE_CONFIG: dict[str, str | int] = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "postgres"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root"),
}

SQLITE_DB_PATH = FilePath(__file__).resolve().parent / "pms_app_fallback.db"


class DictRow(dict):
    """Dict subclass supporting attribute/dict access and case-insensitive key lookup for RealDictCursor compatibility."""
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        if key in self:
            return super().__getitem__(key)
        if isinstance(key, str):
            lower_k = key.lower()
            for k, v in self.items():
                if k.lower() == lower_k:
                    return v
            if lower_k == "count":
                for k, v in self.items():
                    if "count" in k.lower():
                        return v
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self[key]
        except (KeyError, IndexError):
            return default


class SQLiteFallbackCursor:
    """Wrapper around sqlite3.Cursor providing psycopg2 RealDictCursor compatibility."""
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._cur = conn.cursor()

    def execute(self, query: str, params: tuple = ()) -> Any:
        # Convert PostgreSQL syntax to SQLite compatible syntax
        clean_query = query.replace("%s", "?")
        # Replace postgres-specific typecasts like ::date, ::text, ::integer
        clean_query = re.sub(r'::\w+', '', clean_query)
        # Replace SPLIT_PART(a, b, c) with substr/instr logic if simple
        clean_query = re.sub(r"SPLIT_PART\(([^,]+),\s*'([^']+)',\s*1\)", r"\1", clean_query, flags=re.IGNORECASE)
        # Remove PostgreSQL schema prefixes in table names (e.g. pms_chat.agendas -> agendas)
        clean_query = clean_query.replace("pms_chat.", "").replace("public.", "").replace("pms_app.", "")

        try:
            res = self._cur.execute(clean_query, params)
            return res
        except Exception as ex:
            try:
                clean_query2 = clean_query.replace("ILIKE", "LIKE")
                return self._cur.execute(clean_query2, params)
            except Exception:
                raise ex

    def fetchone(self) -> dict | None:
        row = self._cur.fetchone()
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return DictRow({k: row[k] for k in row.keys()})
        return row

    def fetchall(self) -> list[dict]:
        rows = self._cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, sqlite3.Row):
                result.append(DictRow({k: r[k] for k in r.keys()}))
            else:
                result.append(r)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cur, name)


def _init_sqlite_fallback_db(sqlite_path: FilePath) -> None:
    """Initialize SQLite database with required tables and seed data when PostgreSQL is offline."""
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Admin Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        admin_id TEXT PRIMARY KEY,
        name TEXT,
        user_name TEXT,
        plain_password TEXT,
        passwd TEXT
    );
    """)
    cur.execute("SELECT COUNT(*) FROM admin_users;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO admin_users (admin_id, name, user_name, plain_password, passwd)
        VALUES (?, ?, ?, ?, ?);
        """, [
            ("567", "SMT.AMRUTA HARSHAD VYAPARI", "test_admin", "admin1234", "$2b$12$e..."),
            ("101", "ROHIT SHARMA", "rsharma", "admin1234", "$2b$12$e..."),
            ("102", "POOJA DESHMUKH", "pdeshmukh", "admin1234", "$2b$12$e..."),
            ("103", "VIKRAM RAO", "vrao", "admin1234", "$2b$12$e...")
        ])

    # 2. Admin Roles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_roles (
        admin_id TEXT PRIMARY KEY,
        role_id TEXT
    );
    """)
    cur.execute("SELECT COUNT(*) FROM admin_roles;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO admin_roles (admin_id, role_id) VALUES (?, ?);
        """, [
            ("567", "HO"),
            ("101", "DO"),
            ("102", "NO"),
            ("103", "HO")
        ])

    # 3. Applicant Registration / Tenants
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applicant_registration (
        applicant_id INTEGER PRIMARY KEY,
        ind_org_name TEXT,
        authorised_person_name TEXT,
        username TEXT,
        password TEXT,
        login_password TEXT,
        pan_number TEXT,
        gst_number TEXT,
        status TEXT
    );
    """)
    cur.execute("SELECT COUNT(*) FROM applicant_registration;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO applicant_registration (applicant_id, ind_org_name, authorised_person_name, username, password, login_password, pan_number, gst_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            (123, "Adani Ports & SEZ Ltd", "Rakesh Sharma", "test_tenant", "admin1234", "admin1234", "AAACA1234A", "27AAACA1234A1Z5", "APPROVED"),
            (124, "DP World Logistics", "Pooja Deshmukh", "dpworld", "admin1234", "admin1234", "AAACD5678B", "27AAACD5678B1Z2", "APPROVED")
        ])

    # 4. Plots
    cur.execute("""
    CREATE TABLE IF NOT EXISTS plot (
        plot_code TEXT PRIMARY KEY,
        owner_name TEXT,
        location TEXT,
        area REAL,
        from_date TEXT,
        to_date TEXT,
        status TEXT
    );
    """)
    cur.execute("SELECT COUNT(*) FROM plot;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO plot (plot_code, owner_name, location, area, from_date, to_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, [
            ("P-101", "Adani Ports & SEZ Ltd", "Zone A - Embarkation HQ", 12500.0, "2020-01-01", "2035-12-31", "OCCUPIED"),
            ("P-102", "DP World Logistics", "Zone B - Sewree Timber Pond", 8400.0, "2021-06-01", "2036-05-31", "OCCUPIED"),
            ("P-103", "Jindal Steel & Power Ltd", "Zone C - Titwala TDR", 6200.0, "2022-03-15", "2037-03-14", "PENDING")
        ])

    # 5. Bills
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tgeneralbill (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customerCode TEXT,
        bill_amount REAL,
        status INTEGER
    );
    """)
    cur.execute("SELECT COUNT(*) FROM tgeneralbill;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO tgeneralbill (customerCode, bill_amount, status) VALUES (?, ?, ?);
        """, [
            ("P-101", 45000.0, 1),
            ("P-102", 28000.0, 1)
        ])

    # 6. Workflow Cases
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workflow_cases (
        case_id TEXT PRIMARY KEY,
        tenancy_id TEXT,
        title TEXT,
        workflow_state TEXT,
        current_owner TEXT,
        created_by TEXT,
        created_at TEXT
    );
    """)

    # 7. Workflow Messages & Agendas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agendas (
        agenda_id TEXT PRIMARY KEY,
        title TEXT,
        tenancy_id TEXT,
        created_by TEXT,
        assigned_do TEXT,
        assigned_no TEXT,
        assigned_hod TEXT,
        current_owner TEXT,
        current_state TEXT,
        editing_version INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        agenda_id TEXT,
        thread_type TEXT,
        sender_id TEXT,
        sender_name TEXT,
        sender_role TEXT,
        recipient_name TEXT,
        recipient_role TEXT,
        content TEXT,
        is_ai_response BOOLEAN DEFAULT 0,
        ai_triggered_by TEXT,
        created_at TEXT
    );
    """)

    # Auto-migrate missing columns in existing SQLite messages table
    existing_cols = [c[1] for c in cur.execute("PRAGMA table_info(messages)").fetchall()]
    for col_name, col_type in [
        ("recipient_name", "TEXT"),
        ("recipient_role", "TEXT"),
        ("is_ai_response", "BOOLEAN DEFAULT 0"),
        ("ai_triggered_by", "TEXT"),
    ]:
        if col_name not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass

    conn.commit()
    conn.close()


def is_postgres_online(host: str = "localhost", port: int = 5432) -> bool:
    """Fast socket check (0.1s timeout) to see if PostgreSQL port is listening."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        res = s.connect_ex((host, int(port)))
        s.close()
        return res == 0
    except Exception:
        return False


@contextmanager
def get_cursor() -> Generator[Any, None, None]:
    """Yield a dict-cursor (PostgreSQL primary, SQLite fallback if offline)."""
    import psycopg2
    import psycopg2.extras

    conn = None

    # Check if PostgreSQL port is listening
    host_str = str(DATABASE_CONFIG["host"])
    port_int = int(DATABASE_CONFIG["port"])
    if is_postgres_online(host_str, port_int):
        for db_name in [DATABASE_CONFIG["dbname"], "postgres", "port_lease_mms"]:
            for pwd in [DATABASE_CONFIG["password"], "root", "postgres"]:
                try:
                    cfg = dict(DATABASE_CONFIG)
                    cfg["dbname"] = db_name
                    cfg["password"] = pwd
                    conn = psycopg2.connect(**cfg)
                    break
                except Exception:
                    pass
            if conn:
                break

    if conn:
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
                conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    else:
        # Fast fallback to SQLite
        if not SQLITE_DB_PATH.exists():
            _init_sqlite_fallback_db(SQLITE_DB_PATH)

        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        fallback_cur = SQLiteFallbackCursor(sqlite_conn)
        try:
            yield fallback_cur
            sqlite_conn.commit()
        except Exception:
            sqlite_conn.rollback()
            raise
        finally:
            sqlite_conn.close()


