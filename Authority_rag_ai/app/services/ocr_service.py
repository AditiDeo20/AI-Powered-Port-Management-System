from pathlib import Path

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception:
    PADDLE_AVAILABLE = False


class OCRService:

    def __init__(self):
        self.available = PADDLE_AVAILABLE
        if PADDLE_AVAILABLE:
            try:
                self.ocr = PaddleOCR(
                    use_doc_orientation_classify=True,
                    use_doc_unwarping=True,
                    use_textline_orientation=True,
                    lang="en"
                )
            except Exception:
                self.available = False
        else:
            print("[WARN] PaddleOCR unavailable. Using PyMuPDF text extractor fallback.")

    def extract_text(self, image_path: Path):
        if not self.available:
            return []
        result = self.ocr.predict(str(image_path))
        return result