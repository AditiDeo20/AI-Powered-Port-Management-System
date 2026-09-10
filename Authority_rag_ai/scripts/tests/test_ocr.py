from pathlib import Path

from app.services.ocr_service import OCRService

ocr = OCRService()

result = ocr.extract_text(
    Path("data/rendered/page_1.png")
)

print(result)