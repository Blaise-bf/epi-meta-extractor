"""
PDF Parser module for Epi Meta Extractor.

Uses a unified parser with automatic backend fallback:
    1. Marker (preferred) — high-quality markdown extraction
    2. GROBID — structured scientific article parsing
    3. PyPDF — simple text extraction (ultimate fallback)

Configuration via environment variables (see backend/config.py):
    PDF_PARSER_PRIMARY=marker|grobid|pypdf
    PDF_PARSER_FALLBACK_CHAIN=marker,grobid,pypdf
"""

from pathlib import Path
from typing import Dict, Any, Tuple

from pypdf import PdfReader

from backend.config import settings

# Keep GROBID imports for backward compatibility
from backend.services.grobid_client import (
    GrobidClient,
    GrobidExtractedDocument,
    GrobidSection,
    parse_pdf_with_grobid,
)

# Unified parser
from backend.ingestion.unified_pdf_parser import (
    UnifiedPDFParser,
    ParseResult,
    ParserBackend,
)


def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract text from a PDF using PyPDF (legacy fallback).

    Returns a dict with page-by-page text.  Kept for backward compatibility
    with callers that expect the old shape.
    """
    reader = PdfReader(str(pdf_path))

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(
            {
                "page_number": i + 1,
                "text": text.strip(),
            }
        )

    return {
        "file_name": pdf_path.name,
        "num_pages": len(pages),
        "pages": pages,
    }


async def parse_pdf(
    pdf_path: Path,
    use_grobid: bool = True,
    fallback_to_pypdf: bool = True,
) -> Tuple[GrobidExtractedDocument, bool]:
    """
    Parse a PDF and return a structured document.

    DEPRECATED: This function is kept for backward compatibility.
    Use `parse_pdf_unified()` or `UnifiedPDFParser.parse()` for new code.

    Args:
        pdf_path: Path to the PDF file.
        use_grobid: Whether to try GROBID first (default: True).
        fallback_to_pypdf: Whether to fall back to PyPDF if GROBID fails
                           or is unavailable (default: True).

    Returns:
        (document, used_grobid): The parsed document and a boolean flag
        indicating whether GROBID was used (True) or PyPDF was used (False).
    """
    # Build a fallback chain based on legacy arguments
    chain = []
    if use_grobid and settings.GROBID_ENABLED:
        chain.append(ParserBackend.GROBID)
    chain.append(ParserBackend.PYPDF)

    parser = UnifiedPDFParser(fallback_chain=chain)
    result = await parser.parse(pdf_path)

    # Convert Marker document to Grobid document for backward compatibility
    doc = result.document
    if hasattr(doc, "to_dict"):
        # It's a Marker or Grobid document
        if isinstance(doc, GrobidExtractedDocument):
            return doc, result.backend_used == ParserBackend.GROBID

    # Wrap in GrobidExtractedDocument for backward compatibility
    grobid_doc = GrobidExtractedDocument(
        title=getattr(doc, "title", None),
        abstract=getattr(doc, "abstract", None),
        body_text=getattr(doc, "body_text", ""),
    )
    for section in getattr(doc, "sections", []):
        grobid_doc.sections.append(
            GrobidSection(
                heading=getattr(section, "heading", None),
                text=getattr(section, "text", ""),
            )
        )

    used_grobid = result.backend_used == ParserBackend.GROBID
    return grobid_doc, used_grobid


async def parse_pdf_unified(
    pdf_path: Path,
    primary: str = "marker",
    fallback_chain: str = "marker,grobid,pypdf",
) -> ParseResult:
    """
    Parse a PDF with the unified parser (recommended for new code).

    Args:
        pdf_path: Path to the PDF file.
        primary: Primary backend ("marker", "grobid", "pypdf").
        fallback_chain: Comma-separated fallback chain.

    Returns:
        ParseResult with document and backend metadata.
    """
    chain = [ParserBackend(b.strip()) for b in fallback_chain.split(",")]
    parser = UnifiedPDFParser(
        primary_backend=ParserBackend(primary),
        fallback_chain=chain,
    )
    return await parser.parse(pdf_path)
