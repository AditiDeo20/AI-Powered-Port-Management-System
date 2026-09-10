from pathlib import Path

from app.services.image_preprocessor import ImagePreprocessor

processor = ImagePreprocessor()

image = Path("data/rendered/page_1.png")

output = Path("data/processed")

result = processor.process(image, output)

print(result)