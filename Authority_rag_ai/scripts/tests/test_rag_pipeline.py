from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService
from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService


embedder = EmbeddingService()
db = PostgreSQLService()
prompt_builder = PromptBuilder()
llm = LLMService()

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

    print("\n" + "=" * 70)
    print("STEP 1 : EMBEDDING QUERY")
    print("=" * 70)

    query_embedding = embedder.embed_text(question)

    print("Embedding Generated")

    print("\n" + "=" * 70)
    print("STEP 2 : RETRIEVAL")
    print("=" * 70)

    retrieved_chunks = db.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=3
    )

    print(f"Retrieved {len(retrieved_chunks)} chunks.")

    print("\n" + "=" * 70)
    print("STEP 3 : BUILD PROMPT")
    print("=" * 70)

    prompt = prompt_builder.build(
        question=question,
        retrieved_chunks=retrieved_chunks
    )

    print("Prompt Created")

    print("\n" + "=" * 70)
    print("STEP 4 : LLM GENERATION")
    print("=" * 70)

    print("\nAnswer:\n")

    llm.generate(prompt)

print("\nClosing connection...")

db.close()

print("Done.")