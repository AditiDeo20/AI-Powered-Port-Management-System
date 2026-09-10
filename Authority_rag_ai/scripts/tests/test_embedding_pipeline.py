from pathlib import Path

from app.services.pdf_renderer import PDFRenderer
from app.services.ocr_service import OCRService
from app.services.ocr_parser import OCRParser
from app.services.document_builder import CanonicalDocumentBuilder
from app.services.metadata_extractor import MetadataExtractor
from app.services.chunk_service import ChunkService
from app.services.chunk_validator import ChunkValidator
from app.services.embedding_service import EmbeddingService


def main():

    # Input pdf
    pdf = Path("data/TR 93 of 75.pdf")

    # Initialize Services
    ocr = OCRService()
    parser = OCRParser()
    builder = CanonicalDocumentBuilder()
    metadata = MetadataExtractor()
    chunker = ChunkService()
    validator = ChunkValidator()
    embedder = EmbeddingService()
    renderer = PDFRenderer()


    #pdf rendering. 
    
    print("=" * 70)
    print("STEP 1 : PDF Rendering")
    print("=" * 70)

    rendered_pages = renderer.render(
        pdf_path=pdf,
        output_dir=Path("data/rendered")
    )

    print(f"Rendered {len(rendered_pages)} pages.")



    

    print("\n" + "=" * 70)
    print("STEP 2 : OCR + Parsing")
    print("=" * 70)

    parsed_pages = []

    for page_image in rendered_pages:

        print(f"\nProcessing : {page_image.name}")

        raw = ocr.extract_text(page_image)

        print("OCR Completed")

        parsed = parser.parse(raw)

        print("OCR Parsing Completed")

        parsed_pages.extend(parsed["pages"])

    print(f"\nProcessed {len(parsed_pages)} pages successfully.")

    

    print("\n" + "=" * 70)
    print("STEP 3 : Canonical Document")
    print("=" * 70)

    document = builder.build(
        parsed_pages=parsed_pages,
        document_path=pdf,
    )

    print("Canonical Document Created")



    print("\n" + "=" * 70)
    print("STEP 4 : Metadata Extraction")
    print("=" * 70)

    document["metadata"] = metadata.extract(
        document=document,
        document_path=pdf,
    )

    print("Metadata Extracted")

    print("\n" + "=" * 70)
    print("STEP 5 : Chunking")
    print("=" * 70)

    chunks = chunker.create_chunks(document)

    print(f"Chunks Created : {len(chunks)}")

    print("\n" + "=" * 70)
    print("STEP 6 : Chunk Validation")
    print("=" * 70)

    valid_chunks, report = validator.validate(chunks)

    print(report)

    print("\n" + "=" * 70)
    print("STEP 7 : Embedding")
    print("=" * 70)

    embedded_chunks = embedder.embed_chunks(valid_chunks)

    print(f"Embedded Chunks : {len(embedded_chunks)}")

    first_chunk = embedded_chunks[0]

    print("\nChunk Information")
    print("-" * 40)

    print("Chunk ID           :", first_chunk["chunk_id"])
    print("Document ID        :", first_chunk["document_id"])
    print("Document Name      :", first_chunk["document_name"])
    print("Page Number        :", first_chunk["page_number"])
    print("Word Count         :", first_chunk["word_count"])
    print("Character Count    :", first_chunk["character_count"])

    print("\nEmbedding Information")
    print("-" * 40)

    print("Embedding Dimension :", len(first_chunk["embedding"]))

    print("\nFirst 10 Values")
    print(first_chunk["embedding"][:10])

    print("\nPipeline Completed Successfully.")


if __name__ == "__main__":
    main()