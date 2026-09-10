import sys
import os

# Add Authority_rag_ai to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai")))

from app.services.llm_service import LLMService, resolve_ollama_model, OLLAMA_HOST
from app.services.agent_coordinator import AgentCoordinatorService
from app.services.postgres_service import PostgreSQLService
from app.services.embedding_service import EmbeddingService

def test_direct_ollama_and_rag():
    print("=" * 85)
    print("      OLLAMA CONNECTION & DIRECT RAG GENERATION VERIFICATION      ")
    print("=" * 85)
    print(f"Target Ollama IPv4 Endpoint: {OLLAMA_HOST}\n")

    # 1. Test Model Resolution & Normalization
    resolved = resolve_ollama_model("qwen2.5")
    print(f"[TEST 1] Model Normalization: 'qwen2.5' -> '{resolved}'")
    assert resolved == "qwen2.5:3b", f"Expected 'qwen2.5:3b', got '{resolved}'"

    # 2. Direct LLM Service Generation
    print("\n[TEST 2] Executing Direct LLM Generation via LLMService...")
    llm_service = LLMService(model="qwen2.5:3b")
    prompt = "In 2 sentences, explain the primary purpose of land management policy for major ports in India."
    
    response = llm_service.generate(prompt)
    print("-" * 65)
    print(response)
    print("-" * 65)
    
    assert response and len(response) > 10, "[FAIL] Direct LLM generation returned empty response!"
    assert "[RAG System Error]" not in response, "[FAIL] Masked error string found in response!"
    print("[CHECK PASSED] Direct Ollama LLM generation successful.\n")

    # 3. Full Multi-Hop RAG Query Execution
    print("[TEST 3] Executing Full Multi-Hop RAG Pipeline via AgentCoordinatorService...")
    pg_service = PostgreSQLService()
    embedder = EmbeddingService()
    
    coordinator = AgentCoordinatorService(
        embedder=embedder,
        db=pg_service,
        database_agent=None,
        llm_service=llm_service,
        router_service=None
    )

    query = "Which port township areas are explicitly excluded from PGLM 2015?"
    print(f"Query: \"{query}\"")
    
    rag_result = coordinator.run_multihop(question=query, user_id="test-user")
    answer = rag_result.get("answer", "")

    print("\nGenerated Full RAG Response:")
    print("=" * 65)
    print(answer)
    print("=" * 65)

    assert answer and len(answer) > 10, "[FAIL] RAG execution returned empty response!"
    assert "[RAG System Error]" not in answer, "[FAIL] Masked error string found in RAG answer!"
    assert "[Source: Doc -" in answer or "[Source: DB Table -" in answer, "[FAIL] Missing mandatory citation format!"
    print("\n" + "=" * 85)
    print("ALL OLLAMA CONNECTION & DIRECT RAG VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 85 + "\n")

if __name__ == "__main__":
    test_direct_ollama_and_rag()
