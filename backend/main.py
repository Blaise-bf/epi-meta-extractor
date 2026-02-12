from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil

from backend.schemas.loader import load_schema
from backend.ingestion.pdf_parser import extract_text_from_pdf
from fastapi import UploadFile, File
app = FastAPI(title="Epi Meta Extractor")

DATA_DIR = Path("data/raw_pdfs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/schema")
def get_schema():
    return load_schema()




@app.post("/upload-pdf")
def upload_pdf(file: UploadFile = File(...)):
    contents = file.file.read()

    tmp_path = Path("tmp") / file.filename
    tmp_path.parent.mkdir(exist_ok=True)

    with open(tmp_path, "wb") as f:
        f.write(contents)

    result = extract_text_from_pdf(tmp_path)

    return {
        "file_name": file.filename,
        "num_pages": result["num_pages"],
        "pages_extracted": len(result["pages"]),
    }
