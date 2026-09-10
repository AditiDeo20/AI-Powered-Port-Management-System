from pathlib import Path
from pprint import pprint

from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser


ocr = OCRService()
parser = OCRParser()

image = Path("data/rendered/page_2.png")

raw_result = ocr.extract_text(image)

parsed = parser.parse(raw_result,1)

pprint(parsed)