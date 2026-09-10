from pathlib import Path
from hashlib import sha256
from datetime import datetime


class MetadataExtractor:

    def extract(
        self,
        document: dict,
        document_path: Path,
    ) -> dict:

        text = document["full_text"]

        words = text.split()

        title = "Untitled"

        for line in text.splitlines():

            line = line.strip()

            if line:
                title = line
                break

        metadata = {

            "title": title,

            "document_name": document_path.name,

            "document_type": document_path.suffix.replace(".", ""),

            "file_size": document_path.stat().st_size,

            "page_count": document["page_count"],

            "word_count": len(words),

            "character_count": len(text),

            "created_at": datetime.utcnow().isoformat(),

            "document_hash": sha256(
                document_path.read_bytes()
            ).hexdigest(),

            "language": None,
        }

        return metadata