from pathlib import Path
from docling.document_converter import DocumentConverter

# Define the folder path
folder_path = Path("data")

# Find all files in the folder (ignoring hidden files)
files = [f for f in folder_path.glob("*") if f.is_file() and not f.name.startswith(".")]

if not files:
    print("Error: No files found in the 'data' folder.")
else:
    # Select the first file automatically
    first_file_path = files[0]
    
    print(f"Loading first file found: {first_file_path.name}")
    
    # Create converter and process the file
    converter = DocumentConverter()
    result = converter.convert(first_file_path)
    
    print("===================================")
    print("DOCUMENT LOADED SUCCESSFULLY")
    print("===================================")
    
    # Print the extracted text as Markdown
    print(result.document.export_to_markdown())
