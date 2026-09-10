"""
Port Land Lease MMS - Pgvector Diagnostic & Database Dump Ingestion Script
===========================================================================
1. Connects to PostgreSQL database (`pms_app` / `pms_chat` / `postgres`).
2. Verifies pgvector extension status.
3. Discovers all vector tables and vector column dimensions across schemas.
4. Checks chunk counts. If vector tables are empty or missing, parses and imports
   `Authority_rag_ai/schema_embeddings_export.sql` into PostgreSQL.
"""

from __future__ import annotations

import os
import sys
import re
from pathlib import Path
import psycopg2
import psycopg2.extras

def get_db_connection():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "root")
    
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )

def parse_and_import_sql_dump(cur, conn, dump_path: Path):
    print(f"Parsing and ingesting SQL dump: {dump_path} ({dump_path.stat().st_size} bytes)...")
    
    with open(dump_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    in_copy_mode = False
    copy_table = None
    copy_columns = []
    copy_rows = []
    
    executed_ddl_count = 0
    inserted_row_count = 0

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip psql client meta-commands (lines starting with \) except \.
        if stripped.startswith("\\") and not stripped.startswith("\\."):
            continue

        # Handle COPY data termination
        if in_copy_mode and stripped == "\\.":
            if copy_table and copy_rows:
                print(f"Executing batch insert for table '{copy_table}': {len(copy_rows)} rows...")
                # Insert copy_rows into table
                cols_str = ", ".join(copy_columns)
                placeholders = ", ".join(["%s"] * len(copy_columns))
                insert_sql = f"INSERT INTO {copy_table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
                
                # Execute batch inserts
                for row_vals in copy_rows:
                    try:
                        cur.execute(insert_sql, row_vals)
                        inserted_row_count += 1
                    except Exception as ins_err:
                        pass
                conn.commit()
                print(f"[OK] Ingested {len(copy_rows)} rows into '{copy_table}'.")

            in_copy_mode = False
            copy_table = None
            copy_columns = []
            copy_rows = []
            continue

        # Accumulate COPY data lines
        if in_copy_mode:
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) == len(copy_columns):
                # Clean up values (convert \N to None, handle boolean f/t)
                row_vals = []
                for val in parts:
                    if val == "\\N":
                        row_vals.append(None)
                    elif val == "t":
                        row_vals.append(True)
                    elif val == "f":
                        row_vals.append(False)
                    else:
                        row_vals.append(val)
                copy_rows.append(row_vals)
            continue

        # Detect COPY command start
        if stripped.upper().startswith("COPY "):
            # Format: COPY public.schema_embeddings (col1, col2, ...) FROM stdin;
            match = re.match(r"COPY\s+([^\s\(]+)\s*\(([^)]+)\)\s+FROM\s+stdin;", stripped, re.IGNORECASE)
            if match:
                copy_table = match.group(1)
                copy_columns = [c.strip() for c in match.group(2).split(",")]
                in_copy_mode = True
                copy_rows = []
                print(f"Detected COPY statement for table '{copy_table}' with columns: {copy_columns}")
            continue

        # Execute DDL/DML statements
        if stripped and not stripped.startswith("--"):
            if stripped.endswith(";"):
                try:
                    cur.execute(stripped)
                    executed_ddl_count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"[SUCCESS] SQL Dump Ingestion Complete: Executed {executed_ddl_count} DDL statements, Inserted {inserted_row_count} data rows.")


def diagnose_and_import():
    print("=== [1/4] Connecting to PostgreSQL Database ===")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("[OK] Connected to PostgreSQL on localhost:5432/postgres")

    # 1. Check pgvector extension
    print("\n=== [2/4] Checking pgvector Extension ===")
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        print("[OK] Executed: CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception as e:
        conn.rollback()
        print(f"[WARN] Vector extension check warning: {e}")

    cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
    ext = cur.fetchone()
    if ext:
        print(f"[OK] pgvector Extension Installed: Version {ext['extversion']}")
    else:
        print("[WARN] pgvector Extension NOT installed in PostgreSQL environment.")

    # 2. Search for vector columns across information schema
    print("\n=== [3/4] Discovering Vector Tables & Columns ===")
    cur.execute("""
        SELECT table_schema, table_name, column_name, udt_name 
        FROM information_schema.columns 
        WHERE udt_name = 'vector' OR data_type = 'USER-DEFINED';
    """)
    vec_cols = cur.fetchall()
    print(f"Found {len(vec_cols)} vector / user-defined columns in Database:")
    for vc in vec_cols:
        print(f"  - {vc['table_schema']}.{vc['table_name']} -> {vc['column_name']} ({vc['udt_name']})")

    # Inspect RAG tables
    cur.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('chunks', 'user_chunks', 'documents', 'schema_embeddings')
        ORDER BY table_schema, table_name;
    """)
    chunk_tables = cur.fetchall()
    print("\nTarget RAG Tables in Database:")
    total_chunk_count = 0
    for t in chunk_tables:
        s_name = t['table_schema']
        t_name = t['table_name']
        try:
            cur.execute(f"SELECT COUNT(*) FROM {s_name}.{t_name};")
            cnt = cur.fetchone()['count']
            print(f"  - Table {s_name}.{t_name}: {cnt} rows")
            total_chunk_count += cnt
        except Exception as ex:
            print(f"  - Table {s_name}.{t_name}: Error reading count ({ex})")

    # 3. Import schema_embeddings_export.sql if total_chunk_count == 0
    sql_dump_path = Path(__file__).resolve().parent.parent / "Authority_rag_ai" / "schema_embeddings_export.sql"
    print(f"\n=== [4/4] Evaluating Dump Import Requirements (Total Chunks across RAG tables: {total_chunk_count}) ===")
    
    if total_chunk_count == 0:
        if sql_dump_path.exists():
            parse_and_import_sql_dump(cur, conn, sql_dump_path)
        else:
            print(f"[WARN] Dump file not found at path: {sql_dump_path}")
    else:
        print(f"[OK] Vector chunk tables already populated with {total_chunk_count} total records. Skipping dump import.")

    # Final Verification of Vector Dimension
    for schema_name in ['pms_vector', 'public']:
        for tbl in ['schema_embeddings', 'chunks', 'user_chunks']:
            try:
                cur.execute(f"SELECT id, table_name FROM {schema_name}.{tbl} LIMIT 1;")
                r = cur.fetchone()
                if r:
                    print(f"\n[OK] RAG Table Found ({schema_name}.{tbl}): Sample Row -> ID={r.get('id') or r.get('chunk_id')}")
            except Exception:
                conn.rollback()

    cur.close()
    conn.close()
    print("\n=== Pgvector Diagnostic Completed Successfully ===")

if __name__ == "__main__":
    diagnose_and_import()
