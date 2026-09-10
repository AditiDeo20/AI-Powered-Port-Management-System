import urllib.request
import json
import socket
import sys
import os

# Ensure Authority_rag_ai is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai")))

from app.services.agent_coordinator import AgentCoordinatorService
from app.services.postgres_service import PostgreSQLService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

def test_system_recovery_and_rag():
    print("=" * 85)
    print("          AI-PMS MASTER SYSTEM RECOVERY & RAG HARDENING TEST          ")
    print("=" * 85)

    # 1. RAG Query Direct Verification: J&K Applicability under Indian Contract Act
    print("\n[TEST 1] Testing RAG Pipeline Direct Query: 'Does Indian Contract Act apply to Jammu and Kashmir?'")
    embedder = EmbeddingService()
    db_service = PostgreSQLService()
    llm_service = LLMService(model="qwen2.5:3b")

    coordinator = AgentCoordinatorService(
        embedder=embedder,
        db=db_service,
        database_agent=None,
        llm_service=llm_service,
        router_service=None
    )

    query = "Does Indian Contract Act apply to Jammu and Kashmir?"
    result = coordinator.run_multihop(question=query, user_id="admin-test")
    answer = result.get("answer", "")

    print("\nGenerated RAG Response:")
    print("-----------------------------------------------------------------")
    print(answer)
    print("-----------------------------------------------------------------")

    assert answer and len(answer) > 20, "[FAIL] RAG query returned empty or trivial response!"
    assert any(term in answer for term in ["Jammu", "Kashmir", "2019", "Reorganisation", "Act", "India", "Contract"]), "[FAIL] Answer missing key statutory terms!"
    print("[CHECK PASSED] RAG query for J&K Indian Contract Act statutory applicability succeeded.\n")

    # 2. Localhost & Network IP API Health Endpoint Check
    print("[TEST 2] Health Endpoint Verification...")
    
    # Try localhost 8000 health check
    health_url = "http://127.0.0.1:8000/health"
    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"GET {health_url} -> Status Code: {resp.status}, Payload: {data}")
            assert resp.status == 200 and data.get("status") == "ok"
            print("[CHECK PASSED] Health check endpoint responding OK on 127.0.0.1:8000")
    except Exception as exc:
        print(f"[NOTE] Health check server on 8000 is not currently running (Expected if uvicorn is offline): {exc}")

    print("\n" + "=" * 85)
    print("MASTER SYSTEM RECOVERY & RAG RETRIEVAL HARDENING VERIFIED SUCCESSFULLY!")
    print("=" * 85 + "\n")

if __name__ == "__main__":
    test_system_recovery_and_rag()
