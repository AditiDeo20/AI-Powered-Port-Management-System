from pathlib import Path
from pprint import pprint

from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor


image = Path("data/rendered/page_1.png")

ocr = OCRService()
parser = OCRParser()
builder = CanonicalDocumentBuilder()
metadata_extractor = MetadataExtractor()


raw = ocr.extract_text(image)

parsed = parser.parse(raw)

document = builder.build(
    parsed_pages=parsed["pages"],
    document_path=image,
)

document["metadata"] = metadata_extractor.extract(
    document=document,
    document_path=image,
)

pprint(document)