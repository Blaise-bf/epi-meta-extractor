"""
Marker PDF client for high-quality PDF-to-markdown extraction.

Marker (https://github.com/VikParuchuri/marker) converts PDFs to
markdown/JSON/HTML with excellent table, equation, and inline math support.
It is a strong alternative to GROBID for LLM-ready document extraction.

Installation:
    pip install marker-pdf

Usage:
    from backend.services.marker_client import MarkerClient, parse_pdf_with_marker
    doc = await parse_pdf_with_marker("/path/to/article.pdf")
    print(doc.to_plain_text())
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings

# ---------------------------------------------------------------------------
# Structured output data classes (mirror GrobidExtractedDocument shape)
# ---------------------------------------------------------------------------


@dataclass
class MarkerSection:
    """A structured section from the article body"""
    heading: Optional[str] = None
    text: str = ""
    level: int = 1  # Markdown heading level (#=1, ##=2, ...)


@dataclass
class MarkerTable:
    """A table extracted by Marker"""
    id: Optional[str] = None
    caption: Optional[str] = None
    markdown: Optional[str] = None  # Markdown representation
    html: Optional[str] = None      # HTML representation
    rows: List[List[str]] = field(default_factory=list)


@dataclass
class MarkerFigure:
    """A figure extracted by Marker"""
    id: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None


@dataclass
class MarkerExtractedDocument:
    """
    Complete structured document extracted by Marker.
    Designed to be a drop-in replacement for GrobidExtractedDocument.
    """
    # Document metadata
    title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    authors: List[Dict[str, Optional[str]]] = field(default_factory=list)
    submission_date: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None

    # Full text structure
    sections: List[MarkerSection] = field(default_factory=list)
    body_text: str = ""  # Concatenated plain body text

    # Figures and tables
    figures: List[MarkerFigure] = field(default_factory=list)
    tables: List[MarkerTable] = field(default_factory=list)

    # References
    references: List[Dict[str, Any]] = field(default_factory=list)

    # Raw output (for debugging or advanced use)
    raw_markdown: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None

    # Processing metadata
    marker_version: Optional[str] = None
    processing_time: Optional[float] = None

    def to_plain_text(self) -> str:
        """Convert structured document to plain text for LLM extraction"""
        parts = []

        if self.title:
            parts.append(f"Title: {self.title}")

        if self.abstract:
            parts.append(f"Abstract: {self.abstract}")

        for section in self.sections:
            if section.heading:
                parts.append(f"\n{section.heading}")
            if section.text:
                parts.append(section.text)

        # Fallback: include body_text if no sections were added
        if not self.sections and self.body_text:
            parts.append(self.body_text)

        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict for JSON storage"""
        return {
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "authors": self.authors,
            "publication_date": self.publication_date,
            "journal": self.journal,
            "doi": self.doi,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "body_text": self.body_text,
            "sections": [
                {
                    "heading": s.heading,
                    "text": s.text,
                    "level": s.level,
                }
                for s in self.sections
            ],
            "figures_count": len(self.figures),
            "tables_count": len(self.tables),
            "references_count": len(self.references),
            "marker_version": self.marker_version,
        }


# ---------------------------------------------------------------------------
# Marker Client
# ---------------------------------------------------------------------------

class MarkerClient:
    """
    Async wrapper for the Marker PDF-to-markdown converter.

    Usage:
        client = MarkerClient()
        doc = await client.process_pdf("/path/to/article.pdf")
        print(doc.to_plain_text())
    """

    def __init__(
        self,
        timeout: float = 300.0,
        max_pages: Optional[int] = None,
        languages: Optional[List[str]] = None,
        use_llm: bool = False,
    ):
        self.timeout = timeout
        self.max_pages = max_pages
        self.languages = languages or ["en"]
        self.use_llm = use_llm
        self._marker_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if marker-pdf is installed and importable."""
        if self._marker_available is not None:
            return self._marker_available
        try:
            import marker  # noqa: F401
            self._marker_available = True
            return True
        except ImportError:
            self._marker_available = False
            return False

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------

    async def process_pdf(
        self,
        pdf_path: Path,
        output_format: str = "markdown",
    ) -> MarkerExtractedDocument:
        """
        Process a PDF through Marker and return a structured document.

        Args:
            pdf_path: Path to the PDF file.
            output_format: "markdown" | "json" | "html"

        Returns:
            MarkerExtractedDocument with structured content.
        """
        if not self.is_available():
            raise RuntimeError(
                "marker-pdf is not installed. "
                "Install it with: pip install marker-pdf"
            )

        # Marker is synchronous, so run in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._process_pdf_sync,
            pdf_path,
            output_format,
        )

    def _process_pdf_sync(
        self,
        pdf_path: Path,
        output_format: str,
    ) -> MarkerExtractedDocument:
        """Synchronous Marker processing (runs in thread pool)."""
        import time

        start_time = time.time()

        # Lazy import to avoid heavy import at module load time
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered

        # Create converter with optional LLM enhancement
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

        # Convert PDF
        rendered = converter(str(pdf_path))

        # Extract text based on output format
        if output_format == "markdown":
            text, _, images = text_from_rendered(rendered)
            raw_markdown = text
        elif output_format == "json":
            # Marker doesn't natively output JSON, but we can serialize
            raw_markdown = rendered.text if hasattr(rendered, "text") else str(rendered)
        else:
            raw_markdown = rendered.text if hasattr(rendered, "text") else str(rendered)

        processing_time = time.time() - start_time

        # Parse markdown into structured document
        doc = self._parse_markdown(raw_markdown)
        doc.raw_markdown = raw_markdown
        doc.processing_time = processing_time

        # Try to extract metadata from the rendered object if available
        if hasattr(rendered, "metadata"):
            meta = rendered.metadata
            doc.title = meta.get("title") or doc.title
            doc.authors = meta.get("authors", [])
            doc.doi = meta.get("doi")

        return doc

    # ------------------------------------------------------------------
    # Markdown parsing
    # ------------------------------------------------------------------

    def _parse_markdown(self, markdown: str) -> MarkerExtractedDocument:
        """Parse Marker markdown output into structured sections."""
        doc = MarkerExtractedDocument()

        if not markdown:
            return doc

        lines = markdown.split("\n")
        current_section: Optional[MarkerSection] = None
        current_lines: List[str] = []

        # Simple markdown heading parser
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Detect headings (# Heading, ## Heading, etc.)
            if stripped.startswith("#"):
                # Save previous section
                if current_section is not None:
                    current_section.text = "\n".join(current_lines).strip()
                    doc.sections.append(current_section)
                    current_lines = []

                # Determine heading level
                level = 0
                for char in stripped:
                    if char == "#":
                        level += 1
                    else:
                        break

                heading_text = stripped[level:].strip()
                current_section = MarkerSection(
                    heading=heading_text,
                    level=level,
                )

                # First level-1 heading is likely the title
                if level == 1 and not doc.title:
                    doc.title = heading_text

            else:
                current_lines.append(line)

        # Save last section
        if current_section is not None:
            current_section.text = "\n".join(current_lines).strip()
            doc.sections.append(current_section)
        elif current_lines:
            # No headings at all — treat everything as body text
            doc.body_text = "\n".join(current_lines).strip()
            doc.sections.append(MarkerSection(text=doc.body_text))

        # If no sections were created, create one with all text
        if not doc.sections and markdown.strip():
            doc.body_text = markdown.strip()
            doc.sections.append(MarkerSection(text=doc.body_text))

        # Build full body text from sections
        doc.body_text = "\n\n".join(
            s.text for s in doc.sections if s.text
        )

        # Try to extract abstract from first section or "Abstract" section
        if doc.sections and not doc.abstract:
            # Look for a section explicitly named "Abstract"
            for section in doc.sections:
                if section.heading and section.heading.lower() == "abstract":
                    if section.text and len(section.text) < 5000:
                        doc.abstract = section.text
                        break
            else:
                # Fallback: use first non-empty section text
                for section in doc.sections:
                    first_text = section.text
                    if first_text and len(first_text) < 2000:
                        doc.abstract = first_text
                        break

        return doc


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

async def parse_pdf_with_marker(
    pdf_path: Path,
    fallback_to_pypdf: bool = True,
) -> Tuple[MarkerExtractedDocument, bool]:
    """
    Parse a PDF with Marker, falling back to PyPDF if Marker fails.

    Args:
        pdf_path: Path to the PDF file.
        fallback_to_pypdf: Whether to fall back to PyPDF if Marker fails.

    Returns:
        (document, used_marker): The parsed document and a boolean flag
        indicating whether Marker was used (True) or PyPDF was used (False).
    """
    client = MarkerClient()

    if client.is_available():
        try:
            doc = await client.process_pdf(pdf_path)
            return doc, True
        except Exception as e:
            print(f"[Marker] Extraction failed: {e}")
            if not fallback_to_pypdf:
                raise

    # PyPDF fallback
    print("[Marker] Falling back to PyPDF...")
    from backend.ingestion.pdf_parser import extract_text_from_pdf

    pypdf_result = extract_text_from_pdf(pdf_path)
    full_text = "\n".join([page["text"] for page in pypdf_result["pages"]])

    doc = MarkerExtractedDocument(
        title=None,
        abstract=None,
        body_text=full_text,
    )
    doc.sections.append(MarkerSection(heading=None, text=full_text))

    return doc, False
