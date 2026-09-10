from app.services.embedding_service import EmbeddingService

embedding = EmbeddingService()

vector = embedding.embed_text(
    "The lease agreement shall remain valid for twenty years."
)

print(type(vector))
print(len(vector))

print(vector[:10])