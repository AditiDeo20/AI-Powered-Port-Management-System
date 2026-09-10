import sys
import os
import time
sys.stdout.reconfigure(encoding='utf-8')

# Add the project root to sys.path so 'app' can be imported when running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService
from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService
from app.services.guardrail_service import GuardrailService
from app.services.database_agent import DatabaseAgent
from app.services.router_service import RouterService
embedder = EmbeddingService()
db = PostgreSQLService()
prompt_builder = PromptBuilder()
llm = LLMService()
guardrail = GuardrailService()
database_agent = DatabaseAgent()
router = RouterService()

print("=" * 70)
print("Enterprise RAG Pipeline")
print("Type 'exit' to quit")
print("=" * 70)

while True:

    question = input("\nEnter your question: ").strip()

    if question.lower() == "exit":
        break

    if not question:
        continue

    # Start overall pipeline timer
    pipeline_start = time.time()

    # Step 0: Input Guardrail Check done by "sujix-vs" on 5th aug 2026.
    guard_result = guardrail.validate_input(question)
    if not guard_result.is_safe:
        print("\n" + "!" * 70)
        print("⚠️ INPUT GUARDRAIL REJECTION")
        print("!" * 70)
        print(f"Message: {guard_result.reason}")
        print(f"Filtered: {guard_result.censored_text}")
        print("Query aborted to uphold content safety guidelines.")
        print("!" * 70)
        continue

    print("\n" + "=" * 70)
    print("ROUTING QUERY")
    print("=" * 70)
    
    route_start = time.time()
    route = router.route_query(question)
    route_time = time.time() - route_start
    print(f"Query routed to: {route} Expert (in {route_time:.2f}s)")

    if route == "DATABASE":
        print("\n" + "=" * 70)
        print("DATABASE RAG GENERATION")
        print("=" * 70)
        
        start_time = time.time()
        answer = database_agent.query(question)
        db_rag_time = time.time() - start_time
        
        print("\nAnswer:\n")
        print(answer)
        
        total_pipeline_time = time.time() - pipeline_start
        print("\n" + "-" * 70)
        print("PERFORMANCE METRICS")
        print("-" * 70)
        print(f"• Routing:    {route_time:.2f}s")
        print(f"• DB RAG:     {db_rag_time:.2f}s")
        print(f"• Total Time: {total_pipeline_time:.2f}s")
        print("-" * 70)
        continue

    print("\n" + "=" * 70)
    print("STEP 1 : EMBEDDING QUERY")
    print("=" * 70)

    start_time = time.time()
    query_embedding = embedder.embed_text(question)
    embed_time = time.time() - start_time

    print(f"Embedding Generated in {embed_time:.2f}s")

    print("\n" + "=" * 70)
    print("STEP 2 : RETRIEVAL")
    print("=" * 70)

    start_time = time.time()
    retrieved_chunks = db.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=3
    )
    retrieve_time = time.time() - start_time

    print(f"Retrieved {len(retrieved_chunks)} chunks in {retrieve_time:.2f}s")

    print("\n" + "=" * 70)
    print("STEP 3 : BUILD PROMPT")
    print("=" * 70)

    start_time = time.time()
    prompt = prompt_builder.build(
        question=question,
        retrieved_chunks=retrieved_chunks
    )
    prompt_time = time.time() - start_time

    print(f"Prompt Created in {prompt_time:.4f}s")

    print("\n" + "=" * 70)
    print("STEP 4 : LLM GENERATION")
    print("=" * 70)

    print("\nAnswer:\n")

    start_time = time.time()
    llm.generate(prompt)
    llm_time = time.time() - start_time

    # Calculate final pipeline duration
    total_pipeline_time = time.time() - pipeline_start

    print("\n" + "-" * 70)
    print("PERFORMANCE METRICS")
    print("-" * 70)
    print(f"• Embedding:  {embed_time:.2f}s")
    print(f"• Retrieval:  {retrieve_time:.2f}s")
    print(f"• Prompt:     {prompt_time:.4f}s")
    print(f"• Generation: {llm_time:.2f}s")
    print(f"• Total RAG:  {total_pipeline_time:.2f}s")
    print("-" * 70)

print("\nClosing connection...")

db.close()

print("Done.")
