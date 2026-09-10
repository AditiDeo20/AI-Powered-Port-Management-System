import os
import time
import sys
import json
import shutil
import threading
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

# Force stdout to UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

app = FastAPI(title="Port Land Lease RAG AI Assistant API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_origin_regex=r"http://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Test user ID (hardcoded for now — replace with real auth later)
TEST_USER_ID = "user-test-0001"

# Global services references
embedder = None
db = None
prompt_builder = None
llm = None
guardrail = None
ingestion_service = None
router = None
database_agent = None
agent_coordinator = None
services_ready = False
services_loading = False
init_error = None

# Track upload/ingestion status per filename
upload_status = {}

def load_services_bg():
    global embedder, db, prompt_builder, llm, guardrail, ingestion_service, router, database_agent, agent_coordinator, services_ready, services_loading, init_error
    if services_ready or services_loading:
        return
    services_loading = True
    try:
        print("=" * 70)
        print("Initializing Real Enterprise RAG Pipeline Services in background...")
        print("=" * 70)

        from app.services.embedding_service import EmbeddingService
        from app.services.postgres_service import PostgreSQLService
        from app.services.prompt_builder import PromptBuilder
        from app.services.llm_service import LLMService
        from app.services.guardrail_service import GuardrailService
        from app.services.ingestion_service import IngestionService
        from app.services.router_service import RouterService
        from app.services.database_agent import DatabaseAgent
        from app.services.agent_coordinator import AgentCoordinatorService

        embedder = EmbeddingService()
        db = PostgreSQLService()
        prompt_builder = PromptBuilder()
        llm = LLMService()
        guardrail = GuardrailService()
        ingestion_service = IngestionService(embedder=embedder, db=db)
        router = RouterService(model_name="qwen2.5:7b")
        database_agent = DatabaseAgent(model_name="qwen2.5:7b")
        agent_coordinator = AgentCoordinatorService(
            embedder=embedder,
            db=db,
            database_agent=database_agent,
            llm_service=llm,
            router_service=router
        )
        
        services_ready = True
        init_error = None
        print("=" * 70)
        print("[SUCCESS] All RAG Services (BGE-M3, PostgreSQL, Ollama Qwen2.5, Guardrails) Loaded!")
        print("=" * 70)
    except Exception as e:
        services_ready = False
        init_error = str(e)
        print("!" * 70)
        print(f"[ERROR] Error during RAG service initialization: {e}")
        print("!" * 70)
    finally:
        services_loading = False

class ChatRequest(BaseModel):
    question: str
    context: Optional[str] = "Board Note"
    top_k: Optional[int] = 3

class ChatResponse(BaseModel):
    success: bool
    answer: str
    is_safe: bool = True
    safety_message: Optional[str] = None
    source: Optional[str] = None
    page: Optional[str] = None
    retrieved_chunks: List[dict] = []
    metrics: dict = {}
    error_details: Optional[str] = None

@app.on_event("startup")
def startup_event():
    # Start non-blocking background initialization thread
    thread = threading.Thread(target=load_services_bg, daemon=True)
    thread.start()

@app.get("/api/health")
def health_check():
    return {
        "status": "online" if services_ready else ("loading" if services_loading else "error"),
        "service": "Port Land RAG Chatbot API",
        "rag_services_ready": services_ready,
        "init_error": init_error
    }

@app.post("/api/chat/stream")
def process_chat_stream(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not services_ready:
        def err_gen():
            payload = json.dumps({
                "type": "error",
                "message": "Backend connection failed. RAG services (PostgreSQL/Ollama) are not ready."
            })
            yield f"data: {payload}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    def event_generator():
        # Input Guardrail Check
        try:
            guard_result = guardrail.validate_input(question)
            if not guard_result.is_safe:
                payload = json.dumps({
                    "type": "error",
                    "message": guard_result.reason
                })
                yield f"data: {payload}\n\n"
                return
        except Exception as ge:
            print(f"Guardrail error: {ge}")

        if agent_coordinator:
            for event in agent_coordinator.run_multihop_stream(
                question=question,
                user_id=TEST_USER_ID,
                context_filter=req.context,
                top_k=req.top_k or 3
            ):
                yield event
        else:
            err_payload = json.dumps({
                "type": "error",
                "message": "Agent Coordinator is not ready."
            })
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/chat", response_model=ChatResponse)
def process_chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not services_ready:
        return ChatResponse(
            success=False,
            answer="Backend connection failed.",
            error_details=init_error or "RAG services (PostgreSQL/Ollama) are initializing or not reachable."
        )

    pipeline_start = time.time()

    try:
        guard_result = guardrail.validate_input(question)
        if not guard_result.is_safe:
            return ChatResponse(
                success=False,
                answer=guard_result.reason or "Guardrail rejection: The assistant declines and states its scope is restricted to Port Estate & Land Management.",
                is_safe=False,
                safety_message=guard_result.reason,
                error_details=f"Block Type: {guard_result.block_type}"
            )
    except Exception as ge:
        print(f"Guardrail error: {ge}")

    try:
        is_database = False
        if router:
            route_info = router.route_query(question)
            is_database = (route_info.get("route") == "DATABASE")

        if is_database and database_agent:
            # DATABASE ROUTE: Generate and execute SQL using DatabaseAgent
            s_db = time.time()
            answer = database_agent.query(question)
            db_time = time.time() - s_db

            table_name = route_info.get("table") or "Database Tables"
            source_name = f"Table: {table_name}"
            
            total_time = time.time() - pipeline_start

            return ChatResponse(
                success=True,
                answer=answer,
                is_safe=True,
                source=source_name,
                page=None,
                retrieved_chunks=[],
                metrics={
                    "routing_time": f"{time.time() - s_db:.2f}s",
                    "generation_time": f"{db_time:.2f}s",
                    "total_time": f"{total_time:.2f}s"
                }
            )

        # DOCUMENT ROUTE: Embed and Search
        s1 = time.time()
        query_embedding = embedder.embed_text(question)
        embed_time = time.time() - s1

        s2 = time.time()
        retrieved_chunks = db.hybrid_search(
            query_embedding=query_embedding,
            user_id=TEST_USER_ID,
            top_k=req.top_k or 3
        )
        retrieve_time = time.time() - s2

        if req.context and req.context != "All":
            filtered = [
                c for c in retrieved_chunks 
                if req.context.lower() in (c.get("heading", "") + c.get("doc_name", "") + c.get("folder_path", "")).lower()
            ]
            if filtered:
                retrieved_chunks = filtered

        s3 = time.time()
        prompt = prompt_builder.build(question=question, retrieved_chunks=retrieved_chunks)
        prompt_time = time.time() - s3

        s4 = time.time()
        answer = llm.generate(prompt)
        llm_time = time.time() - s4

        source_name = None
        page_str = None

        if retrieved_chunks:
            top_chunk = retrieved_chunks[0]
            source_name = top_chunk.get("doc_name") or top_chunk.get("heading") or "Port Document"
            if top_chunk.get("page_number"):
                page_str = f"Pg {top_chunk.get('page_number')}"

        total_time = time.time() - pipeline_start

        return ChatResponse(
            success=True,
            answer=answer,
            is_safe=True,
            source=source_name,
            page=page_str,
            retrieved_chunks=retrieved_chunks,
            metrics={
                "embedding_time": f"{embed_time:.2f}s",
                "retrieval_time": f"{retrieve_time:.2f}s",
                "prompt_time": f"{prompt_time:.4f}s",
                "generation_time": f"{llm_time:.2f}s",
                "total_time": f"{total_time:.2f}s"
            }
        )

    except Exception as err:
        print(f"[ERROR] RAG Pipeline execution error (V.S): {err}")
        return ChatResponse(
            success=False,
            answer="Backend connection failed.",
            error_details=str(err)
        )

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), context: str = Form("Board Note")):
    try:
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)

        print(f"\n[Upload API] Received upload request for file: '{file.filename}' (Context: '{context}')")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size_kb = os.path.getsize(file_path) / 1024.0
        print(f"[Upload API] Saved '{file.filename}' ({file_size_kb:.1f} KB) to '{file_path}'")

        # Initialize upload status and trigger background ingestion
        upload_status[file.filename] = {
            "status": "pending",
            "step": "File uploaded, starting ingestion...",
            "pdf_type": None,
            "progress": 5,
        }

        if services_ready and ingestion_service:
            print(f"[Upload API] Spawning background thread for IngestionService.ingest('{file.filename}')...")
            def run_ingestion():
                ingestion_service.ingest(
                    pdf_path=Path(file_path),
                    user_id=TEST_USER_ID,
                    status_dict=upload_status[file.filename],
                )

            thread = threading.Thread(target=run_ingestion, daemon=True)
            thread.start()
        else:
            print(f"[Upload API] [WARN] Cannot start ingestion for '{file.filename}': RAG services not ready.")
            upload_status[file.filename].update({
                "status": "failed",
                "step": "RAG services not ready. Please try again later.",
                "progress": 100,
            })

        return {
            "success": True,
            "filename": file.filename,
            "context": context,
            "message": f"File '{file.filename}' uploaded. Ingestion started in background."
        }
    except Exception as e:
        print(f"[Upload API] [ERROR] Upload failed for '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


from urllib.parse import unquote

@app.get("/api/upload/status/{filename}")
def get_upload_status(filename: str):
    """Poll ingestion progress for a specific uploaded file."""
    decoded_name = unquote(filename)
    if decoded_name in upload_status:
        return {"success": True, **upload_status[decoded_name]}
    if filename in upload_status:
        return {"success": True, **upload_status[filename]}
    
    clean_decoded = decoded_name.strip().lower()
    clean_filename = filename.strip().lower()
    for key, val in upload_status.items():
        clean_key = key.strip().lower()
        if clean_key == clean_decoded or clean_key == clean_filename:
            return {"success": True, **val}

    return {"success": False, "status": "unknown", "step": "No ingestion record found."}


@app.get("/api/documents")
def get_user_documents():
    """Retrieve all user-uploaded documents and active ingestion statuses."""
    db_docs = []
    if db and services_ready:
        db_docs = db.get_user_documents(TEST_USER_ID)
    
    indexed_names = {d["doc_name"] for d in db_docs}
    
    active_docs = []
    for fname, info in upload_status.items():
        if fname not in indexed_names:
            active_docs.append({
                "doc_name": fname,
                "chunk_count": info.get("chunks_count", 0),
                "folder_path": None,
                "min_page": None,
                "max_page": None,
                "status": info.get("status", "pending"),
                "step": info.get("step", ""),
                "progress": info.get("progress", 0)
            })
            
    return {
        "success": True,
        "documents": active_docs + db_docs
    }

from app.services.chat_history_service import ChatHistoryService
history_service = ChatHistoryService()


@app.get("/api/sessions")
def get_chat_sessions():
    try:
        sessions = history_service.get_all_sessions()
        return {"success": True, "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sessions: {str(e)}")

class SaveSessionsRequest(BaseModel):
    sessions: List[dict]

@app.post("/api/sessions")
def save_chat_sessions(req: SaveSessionsRequest):
    try:
        success = history_service.save_sessions(req.sessions)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save sessions: {str(e)}")

@app.delete("/api/sessions/{session_id}")
def delete_chat_session(session_id: str):
    try:
        success = history_service.delete_session(session_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend index.html not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api_server:app", host="0.0.0.0", port=8000, reload=True)
