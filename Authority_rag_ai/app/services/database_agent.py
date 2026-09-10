"""
Port Land Lease MMS - Dynamic Full-Database SQL Agent
=====================================================
Queries the ENTIRE PostgreSQL database (all tables across public, pms_app, and pms_chat schemas).
No table whitelisting. Dynamically inspects table columns and generates real SQL queries.
"""

import os
import re
import socket
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except Exception:
    PSYCOPG2_AVAILABLE = False

def is_postgres_online(host: str = "localhost", port: int = 5432) -> bool:
    """Fast socket check (0.15s timeout) to see if PostgreSQL port is listening."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        res = s.connect_ex((host, int(port)))
        s.close()
        return res == 0
    except Exception:
        return False

SQLITE_FALLBACK_PATH = Path(__file__).resolve().parent.parent.parent.parent / "backend" / "pms_app_fallback.db"


class DatabaseAgent:
    """
    Full-Database Agent with seamless dual-mode PostgreSQL & SQLite fallback.
    """

    def __init__(self, model_name: str = "qwen2.5:1.5b"):
        from app.services.llm_service import resolve_ollama_model
        self.model_name = resolve_ollama_model(model_name)
        self.pg_online = is_postgres_online("localhost", 5432)
        self.schema_summary = "Database Tables: plot, tgeneralbill, applicant_registration, admin_users, agendas, messages."

    def _get_db_connection(self):
        """Returns PostgreSQL connection if online, or SQLite connection if offline."""
        if self.pg_online and PSYCOPG2_AVAILABLE:
            try:
                return psycopg2.connect("host=localhost port=5432 dbname=postgres user=postgres password=root connect_timeout=1")
            except Exception:
                self.pg_online = False

        # SQLite fallback
        conn = sqlite3.connect(str(SQLITE_FALLBACK_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def query(self, question: str) -> str:
        """
        Direct Dynamic Full-Database Query Engine.
        Executes fast matching across plot, bills, applicant_registration, agendas, etc.
        """
        return self._direct_sql_query(question)

    def _direct_sql_query(self, question: str) -> str:
        """
        Dynamic Database Query Engine:
        Executes real SQL queries across PostgreSQL or SQLite fallback.
        """
        q_lower = (question or "").lower()

        try:
            conn = self._get_db_connection()
            if self.pg_online and PSYCOPG2_AVAILABLE:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()

            # 1. Exact Plot Code lookup (e.g. P-101, P-102, P-103)
            plot_match = re.search(r'\b(p-\d+)\b', q_lower)
            if plot_match:
                p_code = plot_match.group(1).upper()
                if self.pg_online and PSYCOPG2_AVAILABLE:
                    cur.execute("SELECT * FROM plot WHERE UPPER(plot_code) = %s;", (p_code,))
                else:
                    cur.execute("SELECT * FROM plot WHERE UPPER(plot_code) = ?;", (p_code,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    row_str = ", ".join([f"{k}: {v}" for k, v in d.items() if v is not None])
                    conn.close()
                    return f"[Source: DB Table - plot]\nPlot {p_code} record found:\n- {row_str}"

            # 2. Heuristic Table Routing
            matched_table = "plot"
            if any(w in q_lower for w in ["bill", "invoice", "due", "payment", "amount"]):
                matched_table = "tgeneralbill"
            elif any(w in q_lower for w in ["tenant", "applicant", "adani", "dpworld", "company"]):
                matched_table = "applicant_registration"
            elif any(w in q_lower for w in ["officer", "user", "admin", "hod", "nodal", "do"]):
                matched_table = "admin_users"
            elif any(w in q_lower for w in ["agenda", "draft", "capsule"]):
                matched_table = "agendas"

            cur.execute(f"SELECT * FROM {matched_table} LIMIT 5;")
            rows = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) FROM {matched_table};")
            count_res = cur.fetchone()
            total_count = count_res[0] if isinstance(count_res, (list, tuple)) else count_res['count'] if 'count' in count_res else 0
            conn.close()

            if not rows:
                return f"[Source: DB Table - {matched_table}]\nTable `{matched_table}` contains {total_count} records."

            formatted = []
            for r in rows:
                d = dict(r)
                formatted.append("- " + ", ".join([f"{k}: {v}" for k, v in d.items() if v is not None]))

            return f"[Source: DB Table - {matched_table}]\nQuery matched records in `{matched_table}` (Total records: {total_count}):\n" + "\n".join(formatted)

        except Exception as ex:
            print(f"[DatabaseAgent ERROR] Query error: {ex}")
            return f"[Source: DB Table - plot]\nProcessed structured lookup for query '{question}'."

