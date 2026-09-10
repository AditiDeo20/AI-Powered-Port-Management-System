from uuid import uuid4
from pathlib import Path
from typing import Any
import fitz  # PyMuPDF


class CanonicalDocumentBuilder:

    def build(self,parsed_pages: list[dict[str, Any]],document_path: Path,) -> dict[str, Any]:

        pages = []
        full_text = []

        for page in parsed_pages:

            page_text = "\n".join(
                line["text"] for line in page["lines"]
            )

            pages.append(
                {
                    "page_number": page["page_number"],
                    "text": page_text,
                }
            )

            full_text.append(page_text)

        document = {

            # -------- Identity --------
            "document_id": str(uuid4()),
            "document_name": document_path.name,
            "document_type": document_path.suffix.replace(".", ""),

            # -------- Source --------
            "source": "scanned_pdf",

            # -------- Security --------
            "tenant_id": None,
            "access_scope": None,

            # -------- Metadata --------
            "page_count": len(pages),
            "language": None,

            # -------- Content --------
            "pages": pages,
            "full_text": "\n\n".join(full_text),

            # -------- Placeholder --------
            "metadata": {}
        }

        return document

    def build_from_text_pdf(self,document_path: Path,) -> dict[str, Any]:

        pdf = fitz.open(document_path)

        pages = []
        full_text = []

        for page_number, page in enumerate(pdf, start=1):

            page_text = page.get_text("text").strip()

            pages.append(
                {
                    "page_number": page_number,
                    "text": page_text,
                }
            )

            full_text.append(page_text)

        pdf.close()

        document = {

            # -------- Identity --------
            "document_id": str(uuid4()),
            "document_name": document_path.name,
            "document_type": document_path.suffix.replace(".", ""),

            # -------- Source --------
            "source": "text_pdf",

            # -------- Security --------
            "tenant_id": None,
            "access_scope": None,

            # -------- Metadata --------
            "page_count": len(pages),
            "language": None,

            # -------- Content --------
            "pages": pages,
            "full_text": "\n\n".join(full_text),

            # -------- Placeholder --------
            "metadata": {}
        }

        return document