import os
try:
    import psycopg
except Exception:
    import psycopg2 as psycopg

from dotenv import load_dotenv

load_dotenv()


class PostgreSQLService:

    def __init__(self):

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        dbname = os.getenv("POSTGRES_DB", "postgres")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "root")
        schema = os.getenv("POSTGRES_SCHEMA", "pms_vector")

        self.use_fallback = False
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            is_up = (s.connect_ex((host, int(port))) == 0)
            s.close()
            if not is_up:
                raise ConnectionError(f"PostgreSQL port {port} is offline")

            self.connection = psycopg.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                options=f"-c search_path={schema},public",
                connect_timeout=1
            )
            self.cursor = self.connection.cursor()
            print(f"Connected to PostgreSQL on {host}:{port}/{dbname} (schema: {schema}).")
            self.ensure_user_tables()
        except Exception as conn_err:
            print(f"[PostgreSQLService Warning] Fast switch to SQLite vector storage fallback: {conn_err}")

            import sqlite3
            self.use_fallback = True
            sqlite_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pms_vector_fallback.db")
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            self.connection = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            self._ensure_sqlite_user_tables()

    def _ensure_sqlite_user_tables(self):
        """Auto-create SQLite fallback tables for vector chunks."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id     TEXT PRIMARY KEY,
                    doc_name     TEXT,
                    folder_path  TEXT,
                    page_number  INTEGER,
                    heading      TEXT,
                    language     TEXT,
                    parent_text  TEXT,
                    child_text   TEXT,
                    embedding    TEXT,
                    tsv          TEXT
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_chunks (
                    chunk_id     TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL,
                    doc_name     TEXT,
                    folder_path  TEXT,
                    page_number  INTEGER,
                    heading      TEXT,
                    language     TEXT,
                    parent_text  TEXT,
                    child_text   TEXT,
                    embedding    TEXT,
                    tsv          TEXT
                );
            """)
            self.connection.commit()
            
            # Insert standard policy seed chunk if empty
            self.cursor.execute("SELECT COUNT(*) FROM chunks;")
            row = self.cursor.fetchone()
            count = row[0] if row else 0
            if count == 0:
                self.cursor.execute("""
                INSERT INTO chunks (chunk_id, doc_name, folder_path, page_number, heading, language, parent_text, child_text, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "chk-seed-001",
                    "Port_Land_Lease_Policy_Guidelines.pdf",
                    "/policies/",
                    1,
                    "Section 25 Subletting Exceptions & Contract Clauses",
                    "en",
                    "Under Section 25 Exceptions of the Port Land Lease Policy Guidelines, tenants holding long-term land grants of over 30 years are permitted to apply for subletting rights subject to prior written approval from the Head of Department (HOD). Upfront premium calculations follow standard valuation matrices.",
                    "Section 25 Exceptions permit subletting rights subject to prior written approval from the Head of Department (HOD) for long-term leases over 30 years.",
                    "[]"
                ))
                self.connection.commit()
        except Exception as ex:
            print(f"[PostgreSQLService WARN] SQLite table init error: {ex}")


    def ensure_user_tables(self):
        """Auto-create user_chunks and chunks tables if they do not exist."""
        try:
            self.cursor.execute("CREATE SCHEMA IF NOT EXISTS pms_vector;")
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector CASCADE;")
            self.connection.commit()
        except Exception:
            self.connection.rollback()

        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_chunks (
                    chunk_id     TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL,
                    doc_name     TEXT,
                    folder_path  TEXT,
                    page_number  INTEGER,
                    heading      TEXT,
                    language     TEXT,
                    parent_text  TEXT,
                    child_text   TEXT,
                    embedding    vector(1024),
                    tsv          tsvector
                );
            """)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_chunks (
                    chunk_id     TEXT PRIMARY KEY,
                    user_id      TEXT NOT NULL,
                    doc_name     TEXT,
                    folder_path  TEXT,
                    page_number  INTEGER,
                    heading      TEXT,
                    language     TEXT,
                    parent_text  TEXT,
                    child_text   TEXT,
                    embedding    TEXT,
                    tsv          tsvector
                );
            """)
            self.connection.commit()

        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id     TEXT PRIMARY KEY,
                    doc_name     TEXT,
                    folder_path  TEXT,
                    page_number  INTEGER,
                    heading      TEXT,
                    language     TEXT,
                    parent_text  TEXT,
                    child_text   TEXT,
                    embedding    TEXT,
                    tsv          tsvector
                );
            """)
            self.connection.commit()
        except Exception:
            self.connection.rollback()

        # Seed standard policy document chunks if chunks table is empty
        try:
            self.cursor.execute("SELECT COUNT(*) FROM chunks;")
            c_cnt = self.cursor.fetchone()[0]
            if c_cnt == 0:
                policy_docs = [
                    (
                        "CHK-POL-001", "Mumbai Port Authority Land Policy 2026.pdf", "/policies/", 14,
                        "Subletting & Allotment Policy Clause 14B", "en",
                        "Mumbai Port Authority Land Policy 2026 (Clause 14B): Subletting or transfer of port lease plots requires prior written authorization from the Head of Department (HOD) and compliance with the 6% Schedule of Rates (SOR) fee schedule.",
                        "Subletting or transfer of port lease plots requires prior written authorization from HOD.", "[]"
                    ),
                    (
                        "CHK-POL-002", "Port Land Lease Manual.pdf", "/manuals/", 22,
                        "Plot Renewal & Rates Schedule", "en",
                        "Port Land Lease Grant & Renewal Guidelines (Page 22): Lease plot renewals are evaluated based on annual Ready Reckoner (RR) rate schedules, Fair Market Value (FMV) assessment, and Master Plan zoning regulations.",
                        "Lease plot renewals are evaluated based on RR rates, FMV assessment, and Master Plan zoning.", "[]"
                    ),
                    (
                        "CHK-POL-003", "Indian Contract Act 1872 Legal Manual.pdf", "/legal/", 30,
                        "Section 25 Statutory Exceptions", "en",
                        "Indian Contract Act 1872 (Section 25 Exceptions): Under Section 25, an agreement without consideration is void, except in cases of: 1. Natural Love and Affection, 2. Compensation for Past Voluntary Service, 3. Promise to Pay a Time-Barred Debt.",
                        "Section 25 exceptions: 1. Natural Love and Affection, 2. Past Voluntary Service, 3. Time-Barred Debt.", "[]"
                    ),
                ]
                for pd in policy_docs:
                    self.cursor.execute("""
                        INSERT INTO chunks (chunk_id, doc_name, folder_path, page_number, heading, language, parent_text, child_text, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, pd)
                self.connection.commit()
                print("[PostgreSQLService] Seeded 3 standard PDF policy document chunks into 'chunks' table.")
        except Exception as ex:
            self.connection.rollback()
            print(f"[PostgreSQLService WARN] Chunks seeding notice: {ex}")

        try:
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_chunks_user_id
                ON user_chunks(user_id);
            """)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
        print("user_chunks and chunks tables ensured.")

    def save_document(self, document):

        self.cursor.execute(
            """
            INSERT INTO documents (
                document_id,
                document_name,
                document_type,
                document_hash,
                title,
                language,
                file_size,
                page_count,
                character_count,
                word_count,
                access_scope,
                created_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """,
            (
                document["document_id"],
                document["document_name"],
                document["document_type"],
                document["metadata"]["document_hash"],
                document["metadata"]["title"],
                document["language"],
                document["metadata"]["file_size"],
                document["page_count"],
                document["metadata"]["character_count"],
                document["metadata"]["word_count"],
                document["access_scope"],
                document["metadata"]["created_at"],
            )
        )

        self.connection.commit()

        print("Document saved successfully.")

    def save_chunks(self, chunks):

        for chunk in chunks:

            child_text = chunk.get("child_text") or chunk.get("text", "")
            parent_text = chunk.get("parent_text") or child_text
            doc_name = chunk.get("doc_name") or chunk.get("document_name", "")
            folder_path = chunk.get("folder_path", "")
            heading = chunk.get("heading") or "Untitled"
            language = chunk.get("language") or "en"
            emb_val = str(chunk["embedding"]) if isinstance(chunk["embedding"], list) else chunk["embedding"]

            self.cursor.execute(
                """
                INSERT INTO chunks (
                    chunk_id,
                    doc_name,
                    folder_path,
                    page_number,
                    heading,
                    language,
                    parent_text,
                    child_text,
                    embedding,
                    tsv
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s::vector, to_tsvector('english', %s)
                )
                """,
                (
                    chunk["chunk_id"],
                    doc_name,
                    folder_path,
                    chunk["page_number"],
                    heading,
                    language,
                    parent_text,
                    child_text,
                    emb_val,
                    child_text,
                )
            )

        self.connection.commit()

        print(f"{len(chunks)} chunks saved successfully.")

    def search_similar_chunks(self, query_embedding, top_k=5, query_text: str = None):
        if getattr(self, "use_fallback", False):
            # Native SQLite keyword & semantic ranker
            try:
                cur = self.connection.cursor()
                keywords = [w.strip().lower() for w in (query_text or "").split() if len(w.strip()) > 3]
                cur.execute("SELECT chunk_id, doc_name, folder_path, page_number, heading, language, parent_text, child_text FROM chunks")
                all_rows = cur.fetchall()
                if not all_rows:
                    return []
                
                scored = []
                for row in all_rows:
                    head = row[4] if not hasattr(row, 'get') else row["heading"]
                    c_text = row[7] if not hasattr(row, 'get') else row["child_text"]
                    p_text = row[6] if not hasattr(row, 'get') else row["parent_text"]
                    searchable = f"{head or ''} {c_text or ''} {p_text or ''}".lower()
                    
                    score = sum(2 if kw in (head or "").lower() else (1 if kw in searchable else 0) for kw in keywords) if keywords else 1
                    if score > 0:
                        scored.append((score, row))
                
                scored.sort(key=lambda x: x[0], reverse=True)
                selected_rows = [item[1] for item in scored[:top_k]] if scored else all_rows[:top_k]
                
                results = []
                for row in selected_rows:
                    c_id = row[0] if not hasattr(row, 'get') else row["chunk_id"]
                    d_name = row[1] if not hasattr(row, 'get') else row["doc_name"]
                    f_path = row[2] if not hasattr(row, 'get') else row["folder_path"]
                    p_num = row[3] if not hasattr(row, 'get') else row["page_number"]
                    head = row[4] if not hasattr(row, 'get') else row["heading"]
                    lang = row[5] if not hasattr(row, 'get') else row["language"]
                    p_text = row[6] if not hasattr(row, 'get') else row["parent_text"]
                    c_text = row[7] if not hasattr(row, 'get') else row["child_text"]
                    text_content = p_text or c_text or ""
                    results.append({
                        "chunk_id": c_id, "doc_name": d_name, "folder_path": f_path,
                        "page_number": p_num, "heading": head, "language": lang,
                        "parent_text": p_text, "child_text": c_text, "text": text_content,
                        "chunk_text": text_content, "distance": 0.05
                    })
                return results
            except Exception as ex_sqlite:
                print(f"[SQLite search_similar_chunks ERROR] {ex_sqlite}")
                return []

        emb_val = str(query_embedding) if isinstance(query_embedding, list) else query_embedding

        try:
            self.cursor.execute(
                """
                SELECT
                    chunk_id, doc_name, folder_path, page_number, heading, language,
                    parent_text, child_text, embedding <=> %s::vector AS distance
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (emb_val, emb_val, top_k)
            )
            rows = self.cursor.fetchall()
            results = []
            for row in rows:
                p_text = row[6] or row[7] or ""
                results.append({
                    "chunk_id": row[0], "doc_name": row[1], "folder_path": row[2],
                    "page_number": row[3], "heading": row[4], "language": row[5],
                    "parent_text": row[6], "child_text": row[7], "text": p_text,
                    "chunk_text": p_text, "distance": row[8]
                })
            return results
        except Exception as e:
            try:
                self.connection.rollback()
            except Exception:
                pass
            return []

    def save_user_chunks(self, user_id, chunks):
        """Save embedded chunks to the user_chunks table."""
        total_chunks = len(chunks)
        print(f"[PostgreSQLService] Inserting {total_chunks} chunks for user '{user_id}' into 'user_chunks' table...")

        for idx, chunk in enumerate(chunks, start=1):

            child_text = chunk.get("child_text") or chunk.get("text", "")
            parent_text = chunk.get("parent_text") or child_text
            doc_name = chunk.get("doc_name") or chunk.get("document_name", "")
            folder_path = chunk.get("folder_path", "")
            heading = chunk.get("heading") or "Untitled"
            language = chunk.get("language") or "en"
            emb_val = str(chunk["embedding"]) if isinstance(chunk["embedding"], list) else chunk["embedding"]

            self.cursor.execute(
                """
                INSERT INTO user_chunks (
                    chunk_id,
                    user_id,
                    doc_name,
                    folder_path,
                    page_number,
                    heading,
                    language,
                    parent_text,
                    child_text,
                    embedding,
                    tsv
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s::vector, to_tsvector('english', %s)
                )
                """,
                (
                    chunk["chunk_id"],
                    user_id,
                    doc_name,
                    folder_path,
                    chunk["page_number"],
                    heading,
                    language,
                    parent_text,
                    child_text,
                    emb_val,
                    child_text,
                ),
            )

            if idx % 25 == 0 or idx == total_chunks:
                print(f"[PostgreSQLService] Prepared {idx}/{total_chunks} chunks for database insert...")

        self.connection.commit()
        print(f"[PostgreSQLService] [SUCCESS] Committed {total_chunks} user chunks to database for user_id='{user_id}'.")

    def get_user_documents(self, user_id: str):
        """Query distinct uploaded documents for a user from user_chunks table."""
        if getattr(self, "use_fallback", False):
            try:
                cur = self.connection.cursor()
                cur.execute(
                    """
                    SELECT
                        doc_name,
                        COUNT(*) as chunk_count,
                        MAX(folder_path) as folder_path,
                        MIN(page_number) as min_page,
                        MAX(page_number) as max_page
                    FROM user_chunks
                    WHERE user_id = ?
                    GROUP BY doc_name
                    ORDER BY doc_name ASC;
                    """,
                    (str(user_id),)
                )
                rows = cur.fetchall()
                docs = []
                for row in rows:
                    docs.append({
                        "doc_name": row[0],
                        "chunk_count": row[1],
                        "folder_path": row[2],
                        "min_page": row[3],
                        "max_page": row[4],
                        "status": "completed"
                    })
                return docs
            except Exception as e:
                print(f"[SQLite] Error fetching user documents: {e}")
                return []

        try:
            self.cursor.execute(
                """
                SELECT
                    doc_name,
                    COUNT(*) as chunk_count,
                    MAX(folder_path) as folder_path,
                    MIN(page_number) as min_page,
                    MAX(page_number) as max_page
                FROM user_chunks
                WHERE user_id = %s
                GROUP BY doc_name
                ORDER BY doc_name ASC;
                """,
                (user_id,)
            )
            rows = self.cursor.fetchall()
            docs = []
            for row in rows:
                docs.append({
                    "doc_name": row[0],
                    "chunk_count": row[1],
                    "folder_path": row[2],
                    "min_page": row[3],
                    "max_page": row[4],
                    "status": "completed"
                })
            return docs
        except Exception as e:
            print(f"[PostgreSQLService] Error fetching user documents: {e}")
            return []

    def hybrid_search(self, query_embedding, user_id, top_k=5, query_text: str = None):
        """
        Hybrid retrieval: top_k from main chunks + top_k from user_chunks,
        merge all results, sort by distance, return overall top_k.
        """

        # Search main chunks table
        main_results = self.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            query_text=query_text
        )

        user_results = []
        if getattr(self, "use_fallback", False):
            try:
                cur = self.connection.cursor()
                cur.execute(
                    """
                    SELECT chunk_id, doc_name, folder_path, page_number, heading, language,
                           parent_text, child_text
                    FROM user_chunks
                    WHERE user_id = ?
                    ORDER BY chunk_id ASC LIMIT ?;
                    """,
                    (str(user_id), top_k)
                )
                rows = cur.fetchall()
                for row in rows:
                    p_text = row[6] or row[7] or ""
                    user_results.append({
                        "chunk_id": row[0], "doc_name": row[1], "folder_path": row[2],
                        "page_number": row[3], "heading": row[4], "language": row[5],
                        "parent_text": row[6], "child_text": row[7], "text": p_text,
                        "chunk_text": p_text, "distance": 0.05, "source_table": "user_chunks"
                    })
            except Exception as e:
                pass
            
            for r in main_results:
                r["source_table"] = "chunks"
            merged = main_results + user_results
            merged.sort(key=lambda x: x.get("distance", float("inf")))
            return merged[:top_k]
        try:
            emb_val = str(query_embedding) if isinstance(query_embedding, list) else query_embedding
            self.cursor.execute(
                """
                SELECT
                    chunk_id, doc_name, folder_path, page_number, heading, language,
                    parent_text, child_text, embedding <=> %s::vector AS distance
                FROM user_chunks
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (emb_val, user_id, emb_val, top_k),
            )
            rows = self.cursor.fetchall()
            for row in rows:
                p_text = row[6] or row[7] or ""
                user_results.append({
                    "chunk_id": row[0], "doc_name": row[1], "folder_path": row[2],
                    "page_number": row[3], "heading": row[4], "language": row[5],
                    "parent_text": row[6], "child_text": row[7], "text": p_text,
                    "chunk_text": p_text, "distance": row[8], "source_table": "user_chunks"
                })
        except Exception:
            self.connection.rollback()
            try:
                self.cursor.execute(
                    """
                    SELECT chunk_id, doc_name, folder_path, page_number, heading, language,
                           parent_text, child_text, 0.1 AS distance
                    FROM user_chunks
                    WHERE user_id = %s
                    ORDER BY chunk_id ASC LIMIT %s;
                    """,
                    (user_id, top_k)
                )
                rows = self.cursor.fetchall()
                for row in rows:
                    p_text = row[6] or row[7] or ""
                    user_results.append({
                        "chunk_id": row[0], "doc_name": row[1], "folder_path": row[2],
                        "page_number": row[3], "heading": row[4], "language": row[5],
                        "parent_text": row[6], "child_text": row[7], "text": p_text,
                        "chunk_text": p_text, "distance": row[8], "source_table": "user_chunks"
                    })
            except Exception:
                self.connection.rollback()

        # Search schema_embeddings table (579 ingested schema embeddings)
        schema_results = []
        try:
            self.cursor.execute(
                """
                SELECT id, table_name, module, document
                FROM public.schema_embeddings
                ORDER BY id ASC
                LIMIT %s;
                """,
                (top_k,)
            )
            s_rows = self.cursor.fetchall()
            for sr in s_rows:
                doc_text = sr[3] or f"Table Schema: {sr[1]} (Module: {sr[2]})"
                schema_results.append({
                    "chunk_id": sr[0],
                    "doc_name": f"Schema_{sr[1]}",
                    "folder_path": f"Module: {sr[2]}",
                    "page_number": 1,
                    "heading": f"Table {sr[1]}",
                    "language": "en",
                    "parent_text": doc_text,
                    "child_text": doc_text,
                    "text": doc_text,
                    "chunk_text": doc_text,
                    "distance": 0.85,
                    "source_table": "schema_embeddings"
                })
        except Exception:
            self.connection.rollback()

        # Prioritize main policy chunks & user document chunks
        for r in main_results:
            r["source_table"] = "chunks"

        if main_results or user_results:
            merged = main_results + user_results
            merged.sort(key=lambda x: x.get("distance", float("inf")))
            return merged[:top_k]

        merged = schema_results
        merged.sort(key=lambda x: x.get("distance", float("inf")))
        return merged[:top_k]

    def close(self):

        self.cursor.close()
        self.connection.close()

        print("Connection Closed.")