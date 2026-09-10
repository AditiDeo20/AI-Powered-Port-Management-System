from uuid import uuid4


class ChunkService:

    def __init__(
        self,
        chunk_size: int = 250,
        overlap: int = 40,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(self, document: dict):

        chunks = []

        chunk_index = 0

        for page in document["pages"]:

            words = page["text"].split()

            start = 0

            while start < len(words):

                end = min(start + self.chunk_size, len(words))

                chunk_words = words[start:end]

                chunk_text = " ".join(chunk_words)

                doc_metadata = document.get("metadata", {})
                heading = doc_metadata.get("title") or "Untitled"
                language = document.get("language") or doc_metadata.get("language") or "en"
                folder_path = document.get("folder_path", "")

                chunks.append(
                    {
                        "chunk_id": str(uuid4()),
                        "doc_name": document["document_name"],
                        "folder_path": folder_path,
                        "page_number": page["page_number"],
                        "heading": heading,
                        "language": language,
                        "parent_text": page["text"],
                        "child_text": chunk_text,

                        # Backwards compatibility & pipeline metrics
                        "chunk_index": chunk_index,
                        "document_id": document["document_id"],
                        "document_name": document["document_name"],
                        "text": chunk_text,
                        "word_count": len(chunk_words),
                        "character_count": len(chunk_text),
                        "metadata": doc_metadata,
                    }
                )

                chunk_index += 1

                start += self.chunk_size - self.overlap

        return chunks