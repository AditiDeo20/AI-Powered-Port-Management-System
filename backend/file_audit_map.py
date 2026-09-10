import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def generate_file_audit_map():
    print("=" * 85)
    print("           AI-PMS FILE RELATIONSHIP & SAFE-DELETION AUDIT MAP           ")
    print("=" * 85 + "\n")

    # Define Category Mappings
    core_critical = [
        # Frontend Entry points & Routes
        "port-lease-mms/src/routes/ai-chat.tsx (AI Assistant Hub & Agenda Drafting UI)",
        "port-lease-mms/src/routes/__root.tsx (App Navigation & Layout Shell)",
        "port-lease-mms/src/routes/index.tsx (Tenant Portal Dashboard)",
        
        # Backend API Services & Routers
        "backend/main.py (Tenant & Admin Portal FastAPI Entrypoint - Port 8000)",
        "backend/tenant.py (Tenant Auth, Land Lease Details, Calculations REST Router)",
        "backend/admin.py (Port Authority Officer Authentication & Portal Router)",
        "backend/agenda_workflow.py (DO -> NO -> HOD Agenda Review & Approval Engine)",
        "backend/database.py (PostgreSQL Connection Manager for Tenant & Admin DB)",

        # RAG AI Assistant Backend & Services
        "Authority_rag_ai/app/api_server.py (RAG AI Assistant FastAPI Entrypoint - Port 5000)",
        "Authority_rag_ai/app/services/agent_coordinator.py (Multi-Agent RAG Orchestrator)",
        "Authority_rag_ai/app/services/router_service.py (Query Intent Classifier & Router)",
        "Authority_rag_ai/app/services/postgres_service.py (PostgreSQL Vector Storage Service)",
        "Authority_rag_ai/app/services/embedding_service.py (BGE-M3 1024-dim Vector Generator)",
        "Authority_rag_ai/app/services/llm_service.py (Ollama Qwen2.5 Dynamic Generator)",
        "Authority_rag_ai/app/services/database_agent.py (PostgreSQL SQL Query & Schema Agent)",
        "Authority_rag_ai/app/services/ingestion_service.py (PDF Chunking & Vector Ingestion)",
        "Authority_rag_ai/app/services/history_service.py (Multi-Session Chat Persistence Service)"
    ]

    data_backups = [
        "Authority_rag_ai/data/pms_vector.dump (83 MB PostgreSQL pgvector Custom Archive - 11,851 chunks)",
        "Authority_rag_ai/schema_embeddings_export.sql (7.6 MB SQL Dump - 579 DB Table Embeddings)",
        "database/database_dump.sql (Structured Database Schema & Plot/Pmemo Data Dump)"
    ]

    safe_to_delete = [
        "backend/temp_uploads/ (Temporary uploaded PDF/TXT staging directory)",
        "backend/scratch_setup_db.py (Legacy initial database setup scratch file)",
        "backend/scratch_get_schema.py (Legacy schema extraction scratch file)",
        "Authority_rag_ai/scratch_get_schema.py (Duplicate schema extraction script)",
        "Authority_rag_ai/scratch_setup_db.py (Duplicate DB setup script)",
        "backend/__pycache__/ (Python byte-code cache files)",
        "Authority_rag_ai/app/__pycache__/ (Python byte-code cache files)",
        "port-lease-mms/node_modules/.cache/ (Frontend build cache files)"
    ]

    print("-------------------------------------------------------------------------------------")
    print("1. [CORE CRITICAL]: Active Production Code & Database Dependencies")
    print("-------------------------------------------------------------------------------------")
    for item in core_critical:
        print(f"  [+] {item}")
    print()

    print("-------------------------------------------------------------------------------------")
    print("2. [DATA BACKUPS]: Vector Storage Dumps & Schema Seed Exports")
    print("-------------------------------------------------------------------------------------")
    for item in data_backups:
        print(f"  [DB] {item}")
    print()

    print("-------------------------------------------------------------------------------------")
    print("3. [SAFE TO DELETE]: Duplicate Test Scripts, Temp Uploads & Caches")
    print("-------------------------------------------------------------------------------------")
    for item in safe_to_delete:
        print(f"  [-] {item}")
    print("-------------------------------------------------------------------------------------\n")

if __name__ == "__main__":
    generate_file_audit_map()
