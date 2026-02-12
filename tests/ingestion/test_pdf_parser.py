from pathlib import Path
from backend.ingestion.pdf_parser import extract_text_from_pdf

def test_pdf_text_extraction(tmp_path):
    # Create a dummy PDF
    pdf_path = tmp_path / "test.pdf"

    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "This is a test PDF.")
    c.save()

    result = extract_text_from_pdf(pdf_path)

    assert "file_name" in result
    assert result["file_name"] == "test.pdf"
    assert len(result["pages"]) > 0
    assert "text" in result["pages"][0]
