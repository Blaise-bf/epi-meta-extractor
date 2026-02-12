from fastapi.testclient import TestClient
from backend.main import app
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from pathlib import Path
from reportlab.pdfgen import canvas


client = TestClient(app)

def test_upload_pdf_endpoint(tmp_path):
    pdf_path = tmp_path / "upload_test.pdf"

    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "API upload with pypdf.")
    c.save()

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/upload-pdf",
            files={"file": ("upload_test.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200

    body = response.json()
    assert body["file_name"] == "upload_test.pdf"
    assert body["num_pages"] == 1
    assert body["pages_extracted"] == 1


