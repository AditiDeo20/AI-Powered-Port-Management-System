from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService


embedder = EmbeddingService()
db = PostgreSQLService()

print("=" * 70)
print("Semantic Retrieval Test")
print("Type 'exit' to quit")
print("=" * 70)

while True:

    query = input("\nEnter your question: ").strip()

    if query.lower() == "exit":
        break

    if not query:
        continue

    print("\n" + "=" * 70)
    print("USER QUESTION")
    print("=" * 70)
    print(query)

    print("\n" + "=" * 70)
    print("STEP 1 : EMBEDDING QUERY")
    print("=" * 70)

    query_embedding = embedder.embed_text(query)

    print("Embedding Generated")
    print("Dimension:", len(query_embedding))

    print("\n" + "=" * 70)
    print("STEP 2 : VECTOR SEARCH")
    print("=" * 70)

    results = db.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=3
    )

    print(f"Retrieved {len(results)} chunks.\n")

    for index, chunk in enumerate(results, start=1):

        print(f"Result {index}")
        print("-" * 40)

        print("Chunk ID      :", chunk["chunk_id"])
        print("Doc Name      :", chunk.get("doc_name"))
        print("Folder Path   :", chunk.get("folder_path"))
        print("Page Number   :", chunk.get("page_number"))
        print("Heading       :", chunk.get("heading"))
        print("Language      :", chunk.get("language"))
        print("Distance      :", round(chunk["distance"], 4))

        print("\nChild Text Preview:")
        print((chunk.get("child_text") or chunk.get("text", ""))[:250])
        print("\nParent Text Preview:")
        print((chunk.get("parent_text") or "")[:250])

        print("\n")

print("\nClosing connection...")

db.close()

print("Done.")