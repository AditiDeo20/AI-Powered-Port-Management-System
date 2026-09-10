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


for index, pdf in enumerate(pdf_files, start=1):

    print("=" * 70)
    print(f"[{index}/{len(pdf_files)}] Processing : {pdf.name}")
    print("=" * 70)

    try:

        # -------------------------------------------------
        # STEP 1 : PDF Rendering
        # -------------------------------------------------

        print("\nSTEP 1 : PDF Rendering")

        rendered_pages = renderer.render(
            pdf_path=pdf,
            output_dir=Path("data/rendered")
        )

        print(f"Rendered {len(rendered_pages)} pages.")


        # -------------------------------------------------
        # STEP 2 : OCR + Parsing
        # -------------------------------------------------

        print("\nSTEP 2 : OCR + Parsing")

        parsed_pages = []

        for page_number, page_image in enumerate(rendered_pages, start=1):

            print(f"Processing {page_image.name}")

            raw = ocr.extract_text(page_image)

            parsed = parser.parse(
                raw,
                page_number=page_number
            )

            parsed_pages.extend(parsed["pages"])

        print(f"Parsed {len(parsed_pages)} pages.")


        # -------------------------------------------------
        # STEP 3 : Canonical Document
        # -------------------------------------------------

        print("\nSTEP 3 : Canonical Document")

        document = builder.build(
            parsed_pages=parsed_pages,
            document_path=pdf,
        )
        document["folder_path"] = str(pdf.parent)

        print("Canonical document created.")


        # -------------------------------------------------
        # STEP 4 : Metadata
        # -------------------------------------------------

        print("\nSTEP 4 : Metadata")

        document["metadata"] = metadata.extract(
            document=document,
            document_path=pdf,
        )

        print("Metadata extracted.")


        # -------------------------------------------------
        # STEP 5 : Chunking
        # -------------------------------------------------

        print("\nSTEP 5 : Chunking")

        chunks = chunker.create_chunks(document)

        print(f"Chunks created : {len(chunks)}")


        # -------------------------------------------------
        # STEP 6 : Validation
        # -------------------------------------------------

        print("\nSTEP 6 : Chunk Validation")

        valid_chunks, report = validator.validate(chunks)

        print(report)


        # -------------------------------------------------
        # STEP 7 : Embedding
        # -------------------------------------------------

        print("\nSTEP 7 : Embedding")

        embedded_chunks = embedder.embed_chunks(valid_chunks)

        print(f"Embedded chunks : {len(embedded_chunks)}")


        # -------------------------------------------------
        # STEP 8 : Save Document
        # -------------------------------------------------

        print("\nSTEP 8 : Save Document")

        db.save_document(document)


        # -------------------------------------------------
        # STEP 9 : Save Chunks
        # -------------------------------------------------

        print("\nSTEP 9 : Save Chunks")

        db.save_chunks(embedded_chunks)


        successful += 1

        print(f"\nFinished : {pdf.name}")

    except Exception as e:

        failed += 1

        print(f"\nFailed : {pdf.name}")

        print(e)


db.close()

print("\n" + "=" * 70)
print("BATCH INGESTION COMPLETED")
print("=" * 70)

print(f"Total PDFs : {len(pdf_files)}")
print(f"Successful : {successful}")
print(f"Failed     : {failed}")