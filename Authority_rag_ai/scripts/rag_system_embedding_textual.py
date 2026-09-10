import time
from pathlib import Path

from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor
from app.services.chunk_service import ChunkService
from app.services.chunk_validator import ChunkValidator
from app.services.embedding_service import EmbeddingService
from app.services.postgres_service import PostgreSQLService


# ============================================================
# Folder containing textual PDFs
# ============================================================

data_folder = Path("data/textual")

pdf_files = sorted(data_folder.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found.")
    exit()


builder = CanonicalDocumentBuilder()
metadata = MetadataExtractor()
chunker = ChunkService()
validator = ChunkValidator()
embedder = EmbeddingService()
db = PostgreSQLService()


print("=" * 70)
print("BATCH TEXTUAL PDF INGESTION")
print("=" * 70)
print(f"Found {len(pdf_files)} PDF(s).\n")


successful = 0
failed = 0

batch_start_time = time.time()


for index, pdf in enumerate(pdf_files, start=1):

    print("=" * 70)
    print(f"[{index}/{len(pdf_files)}] Processing : {pdf.name}")
    print("=" * 70)

    metrics = {}
    doc_start_time = time.time()

    try:

        # -------------------------------------------------
        # STEP 1 : Build Canonical Document
        # -------------------------------------------------
        print("\nSTEP 1 : Reading Textual PDF")

        start = time.time()

        document = builder.build_from_text_pdf(
        document_path=pdf
        )
        document["folder_path"] = str(pdf.parent)

        metrics["Step 1: Read PDF"] = time.time() - start

        print("Canonical document created.")


        # -------------------------------------------------
        # STEP 2 : Metadata
        # -------------------------------------------------
        print("\nSTEP 2 : Metadata")

        start = time.time()

        document["metadata"] = metadata.extract(
            document=document,
            document_path=pdf
        )

        metrics["Step 2: Metadata"] = time.time() - start

        print("Metadata extracted.")


        # -------------------------------------------------
        # STEP 3 : Chunking
        # -------------------------------------------------
        print("\nSTEP 3 : Chunking")

        start = time.time()

        chunks = chunker.create_chunks(document)

        metrics["Step 3: Chunking"] = time.time() - start

        print(f"Chunks created : {len(chunks)}")


        # -------------------------------------------------
        # STEP 4 : Chunk Validation
        # -------------------------------------------------
        print("\nSTEP 4 : Chunk Validation")

        start = time.time()

        valid_chunks, report = validator.validate(chunks)

        metrics["Step 4: Validation"] = time.time() - start

        print(report)


        # -------------------------------------------------
        # STEP 5 : Embedding
        # -------------------------------------------------
        print("\nSTEP 5 : Embedding")

        start = time.time()

        embedded_chunks = embedder.embed_chunks(valid_chunks)

        metrics["Step 5: Embedding"] = time.time() - start

        print(f"Embedded chunks : {len(embedded_chunks)}")


        # -------------------------------------------------
        # STEP 6 : Save Document
        # -------------------------------------------------
        print("\nSTEP 6 : Save Document")

        start = time.time()

        db.save_document(document)

        metrics["Step 6: Save Doc"] = time.time() - start


        # -------------------------------------------------
        # STEP 7 : Save Chunks
        # -------------------------------------------------
        print("\nSTEP 7 : Save Chunks")

        start = time.time()

        db.save_chunks(embedded_chunks)

        metrics["Step 7: Save Chunks"] = time.time() - start


        successful += 1

        print(f"\nFinished : {pdf.name}")

        total_doc_time = time.time() - doc_start_time

        print("\n" + "-" * 45)
        print(f"PERFORMANCE METRICS : {pdf.name}")
        print("-" * 45)

        for step, duration in metrics.items():
            print(f"{step.ljust(22)} : {duration:.2f}s")

        print(f"Total Doc Time           : {total_doc_time:.2f}s")
        print("-" * 45 + "\n")

    except Exception as e:

        failed += 1
        print(f"\nFailed : {pdf.name}")
        print(e)


db.close()

total_batch_time = time.time() - batch_start_time

print("\n" + "=" * 70)
print("BATCH TEXTUAL INGESTION COMPLETED")
print("=" * 70)

print(f"Total PDFs       : {len(pdf_files)}")
print(f"Successful       : {successful}")
print(f"Failed           : {failed}")
print(f"Total Batch Time : {total_batch_time:.2f}s")
print("=" * 70)
print("Done.")