#!/usr/bin/env python3
"""
Curate documents from data/ into:

    data/scanned/
    data/textual/

The script classifies documents as either:

- textual: contains extractable text
- scanned: image-only, OCR-needed, or no extractable text found

By default, files are copied so the original input files remain in place.
Use --move to move files instead.

Examples:

    python scripts/curate_documents.py
    python scripts/curate_documents.py --move
    python scripts/curate_documents.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import filecmp
import hashlib
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SCANNED_DIR = DATA_DIR / "scanned"
TEXTUAL_DIR = DATA_DIR / "textual"

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".log",
}

SCANNED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
}

SKIP_DIRS = {
    SCANNED_DIR.resolve(),
    TEXTUAL_DIR.resolve(),
}

SKIP_FILE_NAMES = {
    ".gitkeep",
    "curation_report.csv",
}


def has_meaningful_text(text: str, min_chars: int) -> bool:
    """Return True when extracted text is large enough to treat as textual."""
    compact = "".join(ch for ch in text if not ch.isspace())
    return len(compact) >= min_chars


def extract_pdf_text_with_pymupdf(path: Path, max_pages: int) -> str | None:
    """Extract PDF text with PyMuPDF when available."""
    try:
        import fitz  # type: ignore
    except ImportError:
        return None

    parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc[:max_pages]:
            parts.append(page.get_text("text"))
    return "\n".join(parts)


def extract_pdf_text_with_pypdf(path: Path, max_pages: int) -> str | None:
    """Extract PDF text with pypdf when available."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return None

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages[:max_pages]:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def extract_pdf_text_with_pdftotext(path: Path, max_pages: int) -> str | None:
    """Extract PDF text with the system pdftotext command when available."""
    if shutil.which("pdftotext") is None:
        return None

    result = subprocess.run(
        [
            "pdftotext",
            "-f",
            "1",
            "-l",
            str(max_pages),
            str(path),
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    return result.stdout


def classify_pdf(path: Path, min_chars: int, max_pages: int) -> str:
    """Classify a PDF as textual or scanned."""
    text = extract_pdf_text_with_pymupdf(path, max_pages)
    if text is None:
        text = extract_pdf_text_with_pypdf(path, max_pages)
    if text is None:
        text = extract_pdf_text_with_pdftotext(path, max_pages)

    if text is not None:
        return "textual" if has_meaningful_text(text, min_chars) else "scanned"

    # Safe fallback: low-level PDF markers are not enough to prove a document
    # is textual. Scanned PDFs often contain fonts, metadata, or hidden objects.
    # If no real extractor is available, treat the PDF as scanned so it goes
    # through OCR instead of being incorrectly accepted as text-ready.
    return "scanned"


def classify_file(path: Path, min_chars: int, max_pages: int) -> str | None:
    """Return textual, scanned, or None for unsupported files."""
    suffix = path.suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        return "textual"

    if suffix in SCANNED_EXTENSIONS:
        return "scanned"

    if suffix == ".pdf":
        return classify_pdf(path, min_chars=min_chars, max_pages=max_pages)

    if suffix in DOCUMENT_EXTENSIONS:
        # Office files are generally born-digital or contain extractable text.
        # Detailed classification can be improved later with python-docx/openpyxl.
        return "textual"

    return None


def unique_destination(destination_dir: Path, source: Path) -> Path:
    """Avoid overwriting files with the same name."""
    candidate = destination_dir / source.name
    if not candidate.exists():
        return candidate

    if filecmp.cmp(source, candidate, shallow=False):
        return candidate

    digest = hashlib.sha1(str(source.resolve()).encode("utf-8")).hexdigest()[:8]
    return destination_dir / f"{source.stem}_{digest}{source.suffix}"


def iter_input_files(data_dir: Path) -> list[Path]:
    """Find files under data/, excluding curation output directories."""
    files: list[Path] = []
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.name in SKIP_FILE_NAMES:
            continue

        resolved_parent_paths = {parent.resolve() for parent in path.parents}
        if resolved_parent_paths & SKIP_DIRS:
            continue

        files.append(path)

    return sorted(files)


def curate_documents(copy_mode: bool, dry_run: bool, min_chars: int, max_pages: int) -> list[dict[str, str]]:
    """Classify and copy/move documents into target directories."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory does not exist: {DATA_DIR}")

    if not dry_run:
        SCANNED_DIR.mkdir(parents=True, exist_ok=True)
        TEXTUAL_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []

    for source in iter_input_files(DATA_DIR):
        category = classify_file(source, min_chars=min_chars, max_pages=max_pages)
        if category is None:
            results.append(
                {
                    "source": str(source.relative_to(PROJECT_ROOT)),
                    "category": "unsupported",
                    "destination": "",
                    "action": "skipped",
                }
            )
            continue

        destination_dir = TEXTUAL_DIR if category == "textual" else SCANNED_DIR
        destination = unique_destination(destination_dir, source)
        action = "copy" if copy_mode else "move"

        if not dry_run:
            if copy_mode:
                shutil.copy2(source, destination)
            else:
                shutil.move(str(source), str(destination))

        results.append(
            {
                "source": str(source.relative_to(PROJECT_ROOT)),
                "category": category,
                "destination": str(destination.relative_to(PROJECT_ROOT)),
                "action": "dry-run" if dry_run else action,
            }
        )

    return results


def write_report(results: list[dict[str, str]], report_path: Path) -> None:
    """Write a CSV curation report."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["source", "category", "destination", "action"])
        writer.writeheader()
        writer.writerows(results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify documents in data/ into data/scanned/ and data/textual/."
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying them. Default is copy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without copying or moving files.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=40,
        help="Minimum extracted non-space characters required to treat a PDF as textual.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum PDF pages to inspect for text.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DATA_DIR / "curation_report.csv",
        help="Path to write the CSV curation report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = curate_documents(
        copy_mode=not args.move,
        dry_run=args.dry_run,
        min_chars=args.min_chars,
        max_pages=args.max_pages,
    )

    if not args.dry_run:
        write_report(results, args.report)

    counts = {"textual": 0, "scanned": 0, "unsupported": 0}
    for result in results:
        counts[result["category"]] = counts.get(result["category"], 0) + 1

    print("Curation complete")
    print(f"Textual: {counts.get('textual', 0)}")
    print(f"Scanned: {counts.get('scanned', 0)}")
    print(f"Unsupported: {counts.get('unsupported', 0)}")

    if args.dry_run:
        print("Dry run only. No files were copied or moved.")
    else:
        print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
