from pathlib import Path

from app.services.pdf_renderer import PDFRenderer


renderer = PDFRenderer(dpi=300)

folder_path = Path("data")

# Find all files in the folder (ignoring hidden files)
files = [f for f in folder_path.glob("*") if f.is_file() and not f.name.startswith(".")]

if not files:
    print("Error: No files found in the 'data' folder.")
else:
    # Select the first file automatically
    pdf = files[0]
    
    print(f"Loading first file found: {pdf.name}")

output = Path("data/rendered")

pages = renderer.render(pdf, output)

print("\nRendered Pages:\n")

for page in pages:
    print(page)