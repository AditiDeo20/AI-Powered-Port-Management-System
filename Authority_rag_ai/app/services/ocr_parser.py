from typing import Any


class OCRParser:
    """
    Converts PaddleOCR output into our own standard format.
    """

    def parse(self, ocr_result: Any, page_number: int) -> dict:

        document = {
            "pages": []
        }

        # PaddleOCR returns one result per image/page
        for page in ocr_result:

            page_data = {
                "page_number": page_number,
                "lines": []
            }

            # OCR results
            rec_texts = page.get("rec_texts", [])
            rec_scores = page.get("rec_scores", [])
            rec_boxes = page.get("rec_boxes", [])

            for text, score, box in zip(rec_texts, rec_scores, rec_boxes):

                page_data["lines"].append(
                    {
                        "text": text,
                        "confidence": float(score),
                        "bbox": box.tolist() if hasattr(box, "tolist") else box,
                    }
                )

            document["pages"].append(page_data)

        return document