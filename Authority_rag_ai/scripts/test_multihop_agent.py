import sys
import os
import json

# Force UTF-8 encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService
from app.services.llm_service import LLMService
from app.services.router_service import RouterService
from app.services.database_agent import DatabaseAgent
from app.services.agent_coordinator import AgentCoordinatorService

def test_multihop():
    print("=" * 70)
    print("Testing Multi-Hop Agent Coordinator...")
    print("=" * 70)

    embedder = EmbeddingService()
    db = PostgreSQLService()
    llm = LLMService()
    router = RouterService(model_name="qwen2.5:7b")
    database_agent = DatabaseAgent(model_name="qwen2.5:7b")

    coordinator = AgentCoordinatorService(
        embedder=embedder,
        db=db,
        database_agent=database_agent,
        llm_service=llm,
        router_service=router
    )

    test_queries = [
        "How many distinct plot_ids are in plot_zone_details?",
        "What is MBPT and what is the MPA Act of 2021?",
        "Find plot records in plot_zone_details and explain what policy applies to them."
    ]

    for q in test_queries:
        print(f"\n[QUERY]: {q}")
        print("-" * 50)
        
        for raw_event in coordinator.run_multihop_stream(question=q):
            lines = raw_event.strip().split("\n")
            for line in lines:
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    event_type = payload.get("type")
                    if event_type == "route":
                        print(f"  --> Route: {payload.get('route')} (Table: {payload.get('table')})")
                    elif event_type == "hop":
                        print(f"  --> [HOP {payload.get('step')}]: {payload.get('action')} - {payload.get('details')}")
                    elif event_type == "metadata":
                        print(f"  --> Source Citation: {payload.get('source')}")
                    elif event_type == "token":
                        print(payload.get("content"), end="", flush=True)
                    elif event_type == "done":
                        print(f"\n  --> Metrics: {payload.get('metrics')}")

if __name__ == "__main__":
    test_multihop()
