import sys
import os

# Add Authority_rag_ai to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Authority_rag_ai")))

from app.services.agent_coordinator import AgentCoordinatorService
from app.services.database_agent import DatabaseAgent
from app.services.postgres_service import PostgreSQLService
from app.services.embedding_service import EmbeddingService
from app.services.router_service import RouterService

def run_e2e_rag_verification():
    print("=" * 85)
    print("      AI-PMS REAL RAG PIPELINE & CITATION VERIFICATION SUITE      ")
    print("=" * 85 + "\n")

    pg_service = PostgreSQLService()
    embedder = EmbeddingService()
    
    coordinator = AgentCoordinatorService(
        embedder=embedder,
        db=pg_service,
        database_agent=None,
        llm_service=None,
        router_service=None
    )

    tests = [
        {
            "id": 1,
            "title": "PGLM 2015 Township Applicability & Exclusions",
            "query": "Which port township areas are explicitly excluded from the applicability of PGLM 2015?",
            "must_contain": ["Mumbai", "Kandla", "Kolkata", "Haldia Dock Complex"],
        },
        {
            "id": 2,
            "title": "Indian Contract Act 1872 Section 25 Exceptions",
            "query": "Section 25 contract act exceptions",
            "must_contain": ["Natural Love", "Voluntarily", "Debt"],
        }
    ]

    all_passed = True

    for t in tests:
        print(f"--- TEST CASE {t['id']}: {t['title']} ---")
        print(f"Query: \"{t['query']}\"")
        
        result = coordinator.run_multihop(question=t['query'], user_id="test-user")
        answer = result.get("answer", "")
        
        print("\nGenerated RAG Response Output:")
        print("-" * 65)
        print(answer)
        print("-" * 65 + "\n")

        # 1. Assert NO raw question echo
        assert t['query'] not in answer, f"[FAIL] Echo mock violation: Raw query string '{t['query']}' echoed in answer!"
        print("[CHECK PASSED] Zero raw question echo.")

        # 2. Assert must_contain strings
        for expected in t['must_contain']:
            assert expected.lower() in answer.lower(), f"[FAIL] Missing required factual context: '{expected}'"
            print(f"[CHECK PASSED] Verified factual text present: '{expected}'")

        # 3. Assert citation format
        assert "[Source: Doc -" in answer or "[Source: DB Table -" in answer, "[FAIL] Missing mandatory [Source: ...] citation!"
        print("[CHECK PASSED] Mandatory [Source: ...] citation verified.\n")

    print("=" * 85)
    print("ALL RAG VERIFICATION TESTS PASSED SUCCESSFULLY! ZERO ECHO MOCKS DETECTED.")
    print("=" * 85 + "\n")

if __name__ == "__main__":
    run_e2e_rag_verification()
