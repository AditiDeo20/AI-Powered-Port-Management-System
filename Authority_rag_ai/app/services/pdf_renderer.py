from pathlib import Path
import fitz  # PyMuPDF


class PDFRenderer:
    """
    Renders every page of a PDF into high-resolution PNG images.
    """

    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.zoom = dpi / 72  # PDF default resolution is 72 DPI

    def render(self, pdf_path: Path, output_dir: Path):

        if not pdf_path.exists():
            raise FileNotFoundError(f"{pdf_path} not found")

        output_dir.mkdir(parents=True, exist_ok=True)

        document = fitz.open(pdf_path)

        rendered_pages = []

        matrix = fitz.Matrix(self.zoom, self.zoom)

        for page_number, page in enumerate(document):

            pix = page.get_pixmap(matrix=matrix)

            image_path = output_dir / f"page_{page_number + 1}.png"

            pix.save(image_path)

            rendered_pages.append(image_path)

        document.close()

        return rendered_pages