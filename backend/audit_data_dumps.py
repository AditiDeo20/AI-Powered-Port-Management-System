import os
import sys
import subprocess
import json
import math

try:
    import psycopg2
except ImportError:
    try:
        import psycopg as psycopg2
    except ImportError:
        print("[ERROR] Neither psycopg2 nor psycopg is installed.")
        sys.exit(1)

PG_BIN_DIR = r"C:\Program Files\PostgreSQL\18\bin"
PSQL_EXE = os.path.join(PG_BIN_DIR, "psql.exe")
PG_RESTORE_EXE = os.path.join(PG_BIN_DIR, "pg_restore.exe")

HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = os.getenv("POSTGRES_PORT", "5432")
DBNAME = os.getenv("POSTGRES_DB", "postgres")
USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")

DUMP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai", "data", "pms_vector.dump"))
SQL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai", "schema_embeddings_export.sql"))

def get_db_connection():
    return psycopg2.connect(
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        user=USER,
        password=PASSWORD
    )

def parse_vector_string(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        cleaned = val.strip().strip("'\"[](){}")
        if not cleaned:
            return []
        try:
            return [float(x.strip()) for x in cleaned.split(",") if x.strip()]
        except Exception:
            return []
    return []

def restore_dumps_if_needed():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure DOMAIN public.vector AS text exists for compatibility
    try:
        cursor.execute("CREATE DOMAIN public.vector AS text;")
        conn.commit()
    except Exception:
        conn.rollback()

    # Ensure schema_embeddings table exists with exact dump columns
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.schema_embeddings (
                id text PRIMARY KEY,
                table_name text,
                module text,
                sub_module text,
                has_excel_mapping boolean,
                document text,
                embedding text
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()

    cursor.execute("SELECT COUNT(*) FROM public.schema_embeddings;")
    schema_emb_count = cursor.fetchone()[0]

    if schema_emb_count == 0 and os.path.exists(SQL_PATH):
        print(f"[INGESTION] Importing schema_embeddings_export.sql via python copy ({SQL_PATH})...")
        try:
            with open(SQL_PATH, 'r', encoding='utf-8') as f:
                content = f.read()

            start_idx = content.find("COPY public.schema_embeddings")
            if start_idx != -1:
                header_end = content.find("\n", start_idx)
                data_start = header_end + 1
                data_end = content.find("\n\\.\n", data_start)
                tsv_data = content[data_start:data_end]

                import io
                cursor.copy_expert("COPY public.schema_embeddings (id, table_name, module, sub_module, has_excel_mapping, document, embedding) FROM STDIN", io.StringIO(tsv_data))
                conn.commit()
                
                cursor.execute("SELECT COUNT(*) FROM public.schema_embeddings;")
                schema_emb_count = cursor.fetchone()[0]
                print(f"[SUCCESS] Imported {schema_emb_count} rows into public.schema_embeddings.")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Schema embeddings import failed: {e}")
    else:
        print(f"[OK] public.schema_embeddings already populated with {schema_emb_count} rows.")

    # 2. Check pms_vector.chunks & user_chunks
    total_chunk_rows = 0
    for sch, tbl in [("pms_vector", "chunks"), ("pms_vector", "user_chunks")]:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{sch}"."{tbl}";')
            total_chunk_rows += cursor.fetchone()[0]
        except Exception:
            conn.rollback()

    if total_chunk_rows < 60:
        print(f"[INGESTION] Restoring pms_vector.dump ({DUMP_PATH})...")
        env = os.environ.copy()
        env["PGPASSWORD"] = PASSWORD
        cmd = [PG_RESTORE_EXE, "-h", HOST, "-p", PORT, "-U", USER, "-d", DBNAME, "--data-only", DUMP_PATH]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        print(f"[INGESTION RESULT] pg_restore exit code {res.returncode}")
    else:
        print(f"[OK] PDF vector chunks already populated with {total_chunk_rows} rows.")

    conn.close()

def verify_audit():
    print("\n" + "=" * 80)
    print("      AI-PMS DUMP INGESTION & PGVECTOR VERIFICATION REPORT      ")
    print("=" * 80 + "\n")

    conn = get_db_connection()
    cursor = conn.cursor()

    tables_to_verify = [
        ("public", "schema_embeddings", "embedding", "table_name"),
        ("pms_vector", "chunks", "embedding", "child_text"),
        ("pms_vector", "user_chunks", "embedding", "child_text"),
        ("public", "user_chunks", "embedding", "child_text")
    ]

    summary = []

    for sch, tbl, vec_col, txt_col in tables_to_verify:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s);", (sch, tbl))
        exists = cursor.fetchone()[0]
        if not exists:
            summary.append({
                "table": f"{sch}.{tbl}",
                "rows": 0,
                "dims": "N/A",
                "status": "MISSING"
            })
            continue

        full_table = f'"{sch}"."{tbl}"'
        cursor.execute(f"SELECT COUNT(*) FROM {full_table};")
        row_count = cursor.fetchone()[0]

        dims = "N/A"
        if row_count > 0:
            cursor.execute(f"SELECT {vec_col} FROM {full_table} WHERE {vec_col} IS NOT NULL LIMIT 1;")
            sample = cursor.fetchone()
            if sample and sample[0]:
                vec = parse_vector_string(sample[0])
                if vec:
                    dims = f"{len(vec)}-dim"
                else:
                    dims = "Vector Col (Empty)"

        status = "OK" if row_count > 0 and "1024" in dims else ("EMPTY" if row_count == 0 else "POPULATED")

        summary.append({
            "table": f"{sch}.{tbl}",
            "rows": row_count,
            "dims": dims,
            "status": status
        })

    print("-" * 80)
    print(f"{'Table Name':<32} | {'Row Count':<10} | {'Vector Dims':<18} | {'Status':<15}")
    print("-" * 80)
    for s in summary:
        print(f"{s['table']:<32} | {s['rows']:<10} | {s['dims']:<18} | {s['status']:<15}")
    print("-" * 80 + "\n")

    conn.close()

if __name__ == "__main__":
    restore_dumps_if_needed()
    verify_audit()
