import time
import tempfile
import traceback
from pathlib import Path

import fitz  # PyMuPDF

from app.services.pdf_renderer import PDFRenderer
from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor
from app.services.chunk_service import ChunkService
from app.services.chunk_validator import ChunkValidator


# Minimum non-space characters on the first page to classify as textual
MIN_FIRST_PAGE_CHARS = 50


class IngestionService:
    """
    Smart auto-detecting ingestion pipeline for user-uploaded PDFs.
    Detects text vs scanned by checking the first page only,
    then routes to the appropriate pipeline.
    """

    def __init__(self, embedder, db):
        self.embedder = embedder
        self.db = db

        # Reuse existing services
        self.builder = CanonicalDocumentBuilder()
        self.metadata_extractor = MetadataExtractor()
        self.chunker = ChunkService()
        self.validator = ChunkValidator()

        # OCR services are lazy-loaded only if a scanned PDF is detected
        self._renderer = None
        self._ocr = None
        self._ocr_parser = None

        print("[IngestionService] Initialized (OCR loaded on demand).")

    def _ensure_ocr_services(self):
        """Lazy-load heavy OCR services only when needed."""
        if self._renderer is None:
            print("[IngestionService] Loading OCR services (PaddleOCR + Renderer)...")
            self._renderer = PDFRenderer()
            self._ocr = OCRService()
            self._ocr_parser = OCRParser()
            print("[IngestionService] OCR services loaded.")

    def _detect_pdf_type(self, pdf_path: Path) -> str:
        """
        Check only the first page with PyMuPDF.
        If < MIN_FIRST_PAGE_CHARS non-space characters → 'scanned', else → 'textual'.
        """
        try:
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                doc.close()
                return "scanned"

            first_page_text = doc[0].get_text("text")
            doc.close()

            non_space = "".join(ch for ch in first_page_text if not ch.isspace())

            if len(non_space) < MIN_FIRST_PAGE_CHARS:
                return "scanned"

            return "textual"

        except Exception as e:
            print(f"[IngestionService] PDF type detection error: {e}")
            return "scanned"

    def ingest(self, pdf_path: Path, user_id: str, status_dict: dict):
        """
        Run the full ingestion pipeline for a user-uploaded PDF.
        Updates status_dict in-place for frontend polling.
        """
        filename = pdf_path.name
        pipeline_start = time.time()

        print("\n" + "=" * 70)
        print(f"[IngestionService] STARTING INGESTION PIPELINE FOR: {filename}")
        print(f"[IngestionService] Target User: {user_id} | Path: {pdf_path}")
        print("=" * 70)

        try:
            # ---- Step 1: Detect PDF type ----
            print(f"[IngestionService] [STEP 1/7] Detecting PDF type for '{filename}'...")
            status_dict.update({
                "status": "processing",
                "step": "Detecting PDF type...",
                "pdf_type": None,
                "progress": 10,
            })

            pdf_type = self._detect_pdf_type(pdf_path)
            status_dict["pdf_type"] = pdf_type

            print(f"[IngestionService] [STEP 1/7 SUCCESS] '{filename}' detected as: [{pdf_type.upper()}]")

            # ---- Step 2: Build document ----
            print(f"[IngestionService] [STEP 2/7] Extracting content ({pdf_type} pipeline)...")
            if pdf_type == "textual":
                status_dict.update({
                    "step": "Extracting text (fast path)...",
                    "progress": 20,
                })

                document = self.builder.build_from_text_pdf(
                    document_path=pdf_path,
                )
                print(f"[IngestionService] [STEP 2/7 SUCCESS] Text extracted ({document.get('page_count', 0)} pages).")

            else:
                # Scanned path — load OCR services and process
                status_dict.update({
                    "step": "Scanned PDF detected — OCR in progress. This may take a few minutes...",
                    "progress": 15,
                })

                self._ensure_ocr_services()

                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_output_dir = Path(temp_dir_str)

                    # Render pages to images
                    status_dict["step"] = "Rendering PDF pages..."
                    print(f"[IngestionService] [STEP 2/7] Rendering PDF pages to images...")
                    rendered_pages = self._renderer.render(
                        pdf_path=pdf_path,
                        output_dir=temp_output_dir,
                    )

                    # OCR each page
                    parsed_pages = []
                    total_pages = len(rendered_pages)
                    print(f"[IngestionService] [STEP 2/7] Running OCR across {total_pages} rendered page images...")

                    for page_number, page_image in enumerate(rendered_pages, start=1):
                        status_dict.update({
                            "step": f"OCR processing page {page_number}/{total_pages}...",
                            "progress": 15 + int(35 * page_number / total_pages),
                        })
                        print(f"[IngestionService] [STEP 2/7] OCR processing page {page_number}/{total_pages}...")

                        raw = self._ocr.extract_text(page_image)
                        parsed = self._ocr_parser.parse(raw, page_number=page_number)
                        parsed_pages.extend(parsed["pages"])

                    # Build document from OCR output
                    document = self.builder.build(
                        parsed_pages=parsed_pages,
                        document_path=pdf_path,
                    )
                print(f"[IngestionService] [STEP 2/7 SUCCESS] OCR processing completed ({total_pages} pages).")

            document["folder_path"] = str(pdf_path.parent)

            # ---- Step 3: Metadata ----
            print(f"[IngestionService] [STEP 3/7] Extracting metadata for '{filename}'...")
            status_dict.update({
                "step": "Extracting metadata...",
                "progress": 55,
            })

            document["metadata"] = self.metadata_extractor.extract(
                document=document,
                document_path=pdf_path,
            )
            print(f"[IngestionService] [STEP 3/7 SUCCESS] Metadata extracted: title='{document['metadata'].get('title')}', pages={document.get('page_count')}.")

            # ---- Step 4: Chunking ----
            print(f"[IngestionService] [STEP 4/7] Creating chunks for '{filename}'...")
            status_dict.update({
                "step": "Chunking document...",
                "progress": 60,
            })

            chunks = self.chunker.create_chunks(document)
            print(f"[IngestionService] [STEP 4/7 SUCCESS] Created {len(chunks)} chunks.")

            # ---- Step 5: Validation ----
            print(f"[IngestionService] [STEP 5/7] Validating chunks for '{filename}'...")
            status_dict.update({
                "step": "Validating chunks...",
                "progress": 65,
            })

            valid_chunks, report = self.validator.validate(chunks)
            print(f"[IngestionService] [STEP 5/7 SUCCESS] Validation Report: {report}")

            if not valid_chunks:
                print(f"[IngestionService] [ERROR] Validation produced 0 valid chunks for '{filename}'. Aborting.")
                status_dict.update({
                    "status": "failed",
                    "step": "No valid chunks extracted from document.",
                    "progress": 100,
                })
                return

            # ---- Step 6: Embedding ----
            print(f"[IngestionService] [STEP 6/7] Generating BGE-M3 embeddings for {len(valid_chunks)} valid chunks...")
            status_dict.update({
                "step": "Embedding chunks (BGE-M3)...",
                "progress": 70,
            })

            embedded_chunks = self.embedder.embed_chunks(valid_chunks, batch_size=16, status_dict=status_dict)
            print(f"[IngestionService] [STEP 6/7 SUCCESS] Generated vector embeddings for all {len(embedded_chunks)} chunks.")

            # ---- Step 7: Save to user_chunks ----
            print(f"[IngestionService] [STEP 7/7] Storing {len(embedded_chunks)} embedded chunks into PostgreSQL pgvector database...")
            status_dict.update({
                "step": "Saving to database...",
                "progress": 90,
            })

            self.db.save_user_chunks(user_id, embedded_chunks)
            print(f"[IngestionService] [STEP 7/7 SUCCESS] Saved {len(embedded_chunks)} chunks to user_chunks table.")

            total_time = time.time() - pipeline_start

            status_dict.update({
                "status": "completed",
                "step": "Document indexed successfully!",
                "progress": 100,
                "total_time": f"{total_time:.1f}s",
                "chunks_count": len(embedded_chunks),
            })

            print("=" * 70)
            print(f"[IngestionService] [FINISHED] Ingested '{filename}' in {total_time:.1f}s "
                  f"({len(embedded_chunks)} chunks, type={pdf_type}).")
            print("=" * 70 + "\n")

        except Exception as e:
            print("!" * 70)
            print(f"[IngestionService] [CRITICAL ERROR] Failed ingesting '{filename}': {e}")
            traceback.print_exc()
            print("!" * 70 + "\n")
            status_dict.update({
                "status": "failed",
                "step": f"Ingestion failed: {str(e)}",
                "progress": 100,
            })
