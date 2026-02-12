from pathlib import Path
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: Path) -> dict:
    reader = PdfReader(str(pdf_path))

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(
            {
                "page_number": i + 1,
                "text": text.strip()
            }
        )

    return {
        "file_name": pdf_path.name,
        "num_pages": len(pages),
        "pages": pages
    }
