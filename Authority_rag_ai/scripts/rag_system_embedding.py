import time
import tempfile
import shutil
from pathlib import Path

from app.services.pdf_renderer import PDFRenderer
from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor
from app.services.chunk_service import ChunkService
from app.services.chunk_validator import ChunkValidator
from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService


# Folder containing PDFs
data_folder = Path("data/scanned")

pdf_files = sorted(data_folder.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found.")
    exit()


renderer = PDFRenderer()
ocr = OCRService()
parser = OCRParser()
builder = CanonicalDocumentBuilder()
metadata = MetadataExtractor()
chunker = ChunkService()
validator = ChunkValidator()
embedder = EmbeddingService()
db = PostgreSQLService()


print("=" * 70)
print("BATCH PDF INGESTION")
print("=" * 70)
print(f"Found {len(pdf_files)} PDF(s).\n")


successful = 0
failed = 0

# Start total execution timer
batch_start_time = time.time()

for index, pdf in enumerate(pdf_files, start=1):

    print("=" * 70)
    print(f"[{index}/{len(pdf_files)}] Processing : {pdf.name}")
    print("=" * 70)

    # Dictionary to store step execution times
    metrics = {}
    doc_start_time = time.time()

    try:
        # Create a temporary directory that safely auto-deletes when the scope closes
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_output_dir = Path(temp_dir_str)

            # -------------------------------------------------
            # STEP 1 : PDF Rendering
            # -------------------------------------------------
            print("\nSTEP 1 : PDF Rendering")
            
            start = time.time()
            rendered_pages = renderer.render(
                pdf_path=pdf,
                output_dir=temp_output_dir
            )
            metrics["Step 1: Rendering"] = time.time() - start

            print(f"Rendered {len(rendered_pages)} pages (saved to temp storage).")


            # -------------------------------------------------
            # STEP 2 : OCR + Parsing
            # -------------------------------------------------
            print("\nSTEP 2 : OCR + Parsing")

            start = time.time()
            parsed_pages = []

            for page_number, page_image in enumerate(rendered_pages, start=1):
                print(f"   ↳ Parsing page {page_number}/{len(rendered_pages)}...")
                raw = ocr.extract_text(page_image)
                parsed = parser.parse(raw, page_number=page_number)
                parsed_pages.extend(parsed["pages"])
                
            metrics["Step 2: OCR/Parse"] = time.time() - start

            print(f"Parsed {len(parsed_pages)} pages.")


            # -------------------------------------------------
            # STEP 3 : Canonical Document
            # -------------------------------------------------
            print("\nSTEP 3 : Canonical Document")

            start = time.time()
            document = builder.build(
                parsed_pages=parsed_pages,
                document_path=pdf,
            )
            document["folder_path"] = str(pdf.parent)
            metrics["Step 3: Doc Build"] = time.time() - start

            print("Canonical document created.")


            # -------------------------------------------------
            # STEP 4 : Metadata
            # -------------------------------------------------
            print("\nSTEP 4 : Metadata")

            start = time.time()
            document["metadata"] = metadata.extract(
                document=document,
                document_path=pdf,
            )
            metrics["Step 4: Metadata"] = time.time() - start

            print("Metadata extracted.")


            # -------------------------------------------------
            # STEP 5 : Chunking
            # -------------------------------------------------
            print("\nSTEP 5 : Chunking")

            start = time.time()
            chunks = chunker.create_chunks(document)
            metrics["Step 5: Chunking"] = time.time() - start

            print(f"Chunks created : {len(chunks)}")


            # -------------------------------------------------
            # STEP 6 : Validation
            # -------------------------------------------------
            print("\nSTEP 6 : Chunk Validation")

            start = time.time()
            valid_chunks, report = validator.validate(chunks)
            metrics["Step 6: Validation"] = time.time() - start

            print(report)


            # -------------------------------------------------
            # STEP 7 : Embedding
            # -------------------------------------------------
            print("\nSTEP 7 : Embedding")

            start = time.time()
            embedded_chunks = embedder.embed_chunks(valid_chunks)
            metrics["Step 7: Embedding"] = time.time() - start

            print(f"Embedded chunks : {len(embedded_chunks)}")


            # -------------------------------------------------
            # STEP 8 : Save Document
            # -------------------------------------------------
            print("\nSTEP 8 : Save Document")

            start = time.time()
            db.save_document(document)
            metrics["Step 8: Save Doc"] = time.time() - start


            # -------------------------------------------------
            # STEP 9 : Save Chunks
            # -------------------------------------------------
            print("\nSTEP 9 : Save Chunks")

            start = time.time()
            db.save_chunks(embedded_chunks)
            metrics["Step 9: Save Chunks"] = time.time() - start


            successful += 1
            print(f"\nFinished : {pdf.name}")
            
            # Temporary PNG images are automatically wiped out here as we leave the block

        # Display performance dashboard for the processed document
        total_doc_time = time.time() - doc_start_time
        print("\n" + "-" * 40)
        print(f"⏱️ PERFORMANCE METRICS : {pdf.name}")
        print("-" * 40)
        for step, duration in metrics.items():
            print(f"🔹 {step.ljust(20)}: {duration:.2f}s")
        print(f"⏱️ Total Doc Time     : {total_doc_time:.2f}s")
        print("-" * 40 + "\n")

    except Exception as e:

        failed += 1
        print(f"\nFailed : {pdf.name}")
        print(e)


db.close()

total_batch_time = time.time() - batch_start_time

print("\n" + "=" * 70)
print("BATCH INGESTION COMPLETED")
print("=" * 70)

print(f"Total PDFs       : {len(pdf_files)}")
print(f"Successful       : {successful}")
print(f"Failed           : {failed}")
print(f"Total Batch Time : {total_batch_time:.2f}s")
print("=" * 70)
print("Done.")
