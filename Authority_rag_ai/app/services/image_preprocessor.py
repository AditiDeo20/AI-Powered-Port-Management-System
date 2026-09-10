from pathlib import Path
import cv2
import numpy as np


class ImagePreprocessor:

    def process(self, image_path: Path, output_dir: Path) -> Path:

        output_dir.mkdir(parents=True, exist_ok=True)

        image = cv2.imread(str(image_path))

        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        # -----------------------
        # 1. Convert to grayscale
        # -----------------------
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # -----------------------
        # 2. Denoise
        # -----------------------
        denoised = cv2.fastNlMeansDenoising(gray)

        # -----------------------
        # 3. Contrast Enhancement
        # -----------------------
        contrast = cv2.equalizeHist(denoised)

        # -----------------------
        # 4. Sharpen
        # -----------------------
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        sharpened = cv2.filter2D(contrast, -1, kernel)

        output_path = output_dir / image_path.name

        cv2.imwrite(str(output_path), sharpened)

        return output_path