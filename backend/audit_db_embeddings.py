import sys
import os
import json
import math
import traceback

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    try:
        import psycopg as psycopg2
        from psycopg.rows import dict_row as RealDictCursor
    except ImportError:
        print("[ERROR] Neither psycopg2 nor psycopg is installed.")
        sys.exit(1)

def get_db_connection(dbname="postgres"):
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "root")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        options="-c search_path=pms_vector,public"
    )
    return conn

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

def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def audit_database():
    print("=" * 80)
    print("      AI-PMS POSTGRESQL & PGVECTOR COMPREHENSIVE STORAGE AUDIT REPORT      ")
    print("=" * 80 + "\n")

    dbname = "postgres"
    conn = get_db_connection(dbname)
    cursor = conn.cursor()

    # Ensure pgvector extension exists
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector CASCADE;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[WARN] Failed enabling vector extension: {e}")

    # Target tables to check
    target_tables = [
        ("public", "plot"),
        ("public", "plot_zone_details"),
        ("public", "plot_rr_land_value"),
        ("public", "pmemo"),
        ("public", "plot_fair_mkt_value"),
        ("public", "schema_embeddings"),
        ("public", "user_chunks"),
        ("pms_vector", "user_chunks"),
        ("pms_vector", "chunks")
    ]

    print(f"Connecting to Database: '{dbname}' on localhost:5432...\n")

    audit_results = []

    for schema, table in target_tables:
        row_count = 0
        vector_dims = "N/A (No Vector)"
        status = "EMPTY"
        
        # Check table existence
        cursor.execute("""
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s;
        """, (schema, table))
        if not cursor.fetchone():
            audit_results.append({
                "table_name": f"{schema}.{table}",
                "row_count": 0,
                "vector_dims": "N/A",
                "status": "MISSING / NOT CREATED"
            })
            continue

        full_table = f'"{schema}"."{table}"'
        
        # Check row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {full_table};")
            row_count = cursor.fetchone()[0]
        except Exception as e:
            conn.rollback()
            row_count = 0

        # Check for vector or embedding column
        cursor.execute("""
            SELECT column_name, udt_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s AND (column_name LIKE '%%embedding%%' OR udt_name = 'vector');
        """, (schema, table))
        vec_cols = cursor.fetchall()

        if vec_cols:
            vec_col_name = vec_cols[0][0]
            udt_name = vec_cols[0][1]
            if row_count > 0:
                try:
                    if udt_name == "vector":
                        cursor.execute(f"SELECT vector_dims({vec_col_name}) FROM {full_table} WHERE {vec_col_name} IS NOT NULL LIMIT 1;")
                        dim_res = cursor.fetchone()
                        if dim_res and dim_res[0]:
                            vector_dims = f"{dim_res[0]}-dim"
                    else:
                        cursor.execute(f"SELECT {vec_col_name} FROM {full_table} WHERE {vec_col_name} IS NOT NULL LIMIT 1;")
                        sample_emb = cursor.fetchone()
                        if sample_emb and sample_emb[0]:
                            parsed = parse_vector_string(sample_emb[0])
                            if parsed:
                                vector_dims = f"{len(parsed)}-dim (text-encoded)"
                            else:
                                vector_dims = "Text Vector (Empty)"
                        else:
                            vector_dims = "Vector Col (Nulls)"
                except Exception as e:
                    conn.rollback()
                    vector_dims = f"Vector Col ({vec_cols[0][2]})"
            else:
                vector_dims = f"Vector Col ({vec_cols[0][2]} 0 rows)"

        if row_count > 0:
            status = "OK"
        else:
            status = "EMPTY"

        audit_results.append({
            "table_name": f"{schema}.{table}",
            "row_count": row_count,
            "vector_dims": vector_dims,
            "status": status
        })

    # Print Summary Table
    print("-" * 80)
    print(f"{'Table Name':<32} | {'Row Count':<10} | {'Vector Dims':<24} | {'Status':<15}")
    print("-" * 80)
    for res in audit_results:
        print(f"{res['table_name']:<32} | {res['row_count']:<10} | {res['vector_dims']:<24} | {res['status']:<15}")
    print("-" * 80 + "\n")

    # ---------------------------------------------------------
    # 2. VECTOR SIMILARITY RETRIEVAL TEST
    # ---------------------------------------------------------
    query_text = "What is the maximum tenure for land allotted inside custom bond areas?"
    print("=" * 80)
    print(f"VECTOR SIMILARITY RETRIEVAL TEST FOR QUERY:")
    print(f'"{query_text}"')
    print("=" * 80 + "\n")

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai")))
    
    query_vector = None
    try:
        from app.services.embedding_service import EmbeddingService
        embedder = EmbeddingService()
        query_vector = embedder.embed_text(query_text)
        print(f"[SUCCESS] Generated {len(query_vector)}-dim BGE-M3 query vector.\n")
    except Exception as e:
        print(f"[WARN] EmbeddingService fallback: {e}")
        query_vector = [0.01] * 1024

    # Test retrieval against vector tables
    vector_target_tables = [
        ("pms_vector", "chunks", "embedding", "child_text"),
        ("pms_vector", "user_chunks", "embedding", "child_text"),
        ("public", "user_chunks", "embedding", "child_text"),
        ("public", "schema_embeddings", "embedding", "table_name")
    ]

    for sch, tbl, vec_col, txt_col in vector_target_tables:
        try:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s);", (sch, tbl))
            exists = cursor.fetchone()[0]
            if not exists:
                continue

            cursor.execute(f"SELECT COUNT(*) FROM \"{sch}\".\"{tbl}\";")
            count = cursor.fetchone()[0]
            if count == 0:
                print(f"[RETRIEVAL TEST] Table '{sch}.{tbl}' is EMPTY ({count} rows). Skipping search.")
                continue

            print(f"--- Top 5 Nearest Neighbors in '{sch}.{tbl}' (Cosine Similarity / Distance) ---")
            
            cursor.execute(f"SELECT {txt_col}, {vec_col} FROM \"{sch}\".\"{tbl}\" WHERE {vec_col} IS NOT NULL;")
            rows = cursor.fetchall()

            scored_rows = []
            for row in rows:
                content = row[0]
                emb_raw = row[1]
                emb_vec = parse_vector_string(emb_raw)
                if not emb_vec:
                    continue

                sim = cosine_similarity(query_vector, emb_vec)
                dist = 1.0 - sim
                scored_rows.append((content, sim, dist))

            scored_rows.sort(key=lambda x: x[1], reverse=True)

            if not scored_rows:
                print("  No rows with valid vector embeddings found.")
            else:
                for i, r in enumerate(scored_rows[:5], start=1):
                    content_snippet = str(r[0])[:120].replace('\n', ' ')
                    sim = r[1]
                    dist = r[2]
                    print(f"  {i}. [Cosine Dist: {dist:.4f} | Cosine Sim: {sim:.4f}] Content: {content_snippet}...")
            print()

        except Exception as e:
            conn.rollback()
            print(f"[RETRIEVAL TEST ERROR] Search on '{sch}.{tbl}' failed: {e}\n")

    conn.close()

if __name__ == "__main__":
    audit_database()
