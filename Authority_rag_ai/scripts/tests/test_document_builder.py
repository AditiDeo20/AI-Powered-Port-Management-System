from pathlib import Path
from pprint import pprint

from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder


ocr = OCRService()
parser = OCRParser()
builder = CanonicalDocumentBuilder()

image = Path("data/rendered/page_1.png")

raw = ocr.extract_text(image)

parsed = parser.parse(raw)

document = builder.build(
    parsed_pages=parsed["pages"],
    document_path=image,
)

pprint(document)