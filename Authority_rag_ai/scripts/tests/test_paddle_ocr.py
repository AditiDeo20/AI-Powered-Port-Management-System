from paddleocr import PaddleOCR

ocr = PaddleOCR(lang="en")

result = ocr.predict("data/rendered/page_1.png")

print(type(result))
print(result)