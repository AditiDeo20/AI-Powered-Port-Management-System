from pathlib import Path
from pprint import pprint

from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor
from app.services.chunk_service import ChunkService


image = Path("data/rendered/page_1.png")

ocr = OCRService()
parser = OCRParser()
builder = CanonicalDocumentBuilder()
metadata = MetadataExtractor()
chunker = ChunkService()


raw = ocr.extract_text(image)

parsed = parser.parse(raw)

document = builder.build(
    parsed_pages=parsed["pages"],
    document_path=image,
)

document["metadata"] = metadata.extract(
    document=document,
    document_path=image,
)

chunks = chunker.create_chunks(document)

print(f"\nTotal Chunks: {len(chunks)}\n")

for chunk in chunks:
    pprint(chunk)
    print("-" * 80)