"""
Unified PDF Parser for Epi Meta Extractor.

Orchestrates multiple PDF parsing backends with automatic fallback:
    1. Marker (preferred) — high-quality markdown extraction
    2. GROBID — structured scientific article parsing
    3. PyPDF — simple text extraction (ultimate fallback)

Configuration via environment variables:
    PDF_PARSER_PRIMARY=marker|grobid|pypdf   (default: marker)
    PDF_PARSER_FALLBACK_CHAIN=marker,grobid,pypdf  (default)
    MARKER_ENABLED=true|false                 (default: true)
    GROBID_ENABLED=true|false                 (default: true)

Usage:
    from backend.ingestion.unified_pdf_parser import UnifiedPDFParser
    parser = UnifiedPDFParser()
    doc = await parser.parse("/path/to/article.pdf")
    print(doc.to_plain_text())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.config import settings


class ParserBackend(str, Enum):
    """Supported PDF parser backends."""
    MARKER = "marker"
    GROBID = "grobid"
    PYPDF = "pypdf"


@dataclass
class ParseResult:
    """Result of a PDF parse operation with metadata about which backend was used."""
    document: Any  # MarkerExtractedDocument | GrobidExtractedDocument
    backend_used: ParserBackend
    fallback_used: bool = False
    processing_time: Optional[float] = None
    error_log: List[str] = field(default_factory=list)

    def to_plain_text(self) -> str:
        """Delegate to the underlying document."""
        return self.document.to_plain_text()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict including backend metadata."""
        return {
            "backend_used": self.backend_used.value,
            "fallback_used": self.fallback_used,
            "processing_time": self.processing_time,
            "error_log": self.error_log,
            "document": self.document.to_dict(),
        }


class UnifiedPDFParser:
    """
    Unified PDF parser that tries multiple backends with automatic fallback.

    Usage:
        parser = UnifiedPDFParser()
        result = await parser.parse("/path/to/article.pdf")
        print(result.to_plain_text())
        print(f"Used backend: {result.backend_used}")
    """

    def __init__(
        self,
        primary_backend: Optional[ParserBackend] = None,
        fallback_chain: Optional[List[ParserBackend]] = None,
    ):
        """
        Initialize the unified parser.

        Args:
            primary_backend: The first parser to try. Defaults to config.
            fallback_chain: Ordered list of fallbacks. Defaults to config.
        """
        # Determine primary backend from config or argument
        self.primary = primary_backend or self._get_configured_primary()

        # Determine fallback chain from config or argument
        self.chain = fallback_chain or self._get_configured_chain()

        # Ensure primary is first in chain
        if self.chain and self.chain[0] != self.primary:
            # Remove primary from chain if present, then prepend
            self.chain = [b for b in self.chain if b != self.primary]
            self.chain.insert(0, self.primary)

        print(f"[UnifiedPDFParser] Chain: {' → '.join(b.value for b in self.chain)}")

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_configured_primary() -> ParserBackend:
        """Read primary backend from settings."""
        backend_str = getattr(settings, "PDF_PARSER_PRIMARY", "marker").lower()
        try:
            return ParserBackend(backend_str)
        except ValueError:
            print(f"[UnifiedPDFParser] Unknown primary '{backend_str}', defaulting to marker")
            return ParserBackend.MARKER

    @staticmethod
    def _get_configured_chain() -> List[ParserBackend]:
        """Read fallback chain from settings."""
        chain_str = getattr(
            settings,
            "PDF_PARSER_FALLBACK_CHAIN",
            "marker,grobid,pypdf",
        )
        backends = []
        for name in chain_str.split(","):
            name = name.strip().lower()
            try:
                backends.append(ParserBackend(name))
            except ValueError:
                print(f"[UnifiedPDFParser] Unknown backend '{name}', skipping")
        if not backends:
            backends = [ParserBackend.MARKER, ParserBackend.GROBID, ParserBackend.PYPDF]
        return backends

    # ------------------------------------------------------------------
    # Main parse method
    # ------------------------------------------------------------------

    async def parse(self, pdf_path: Path) -> ParseResult:
        """
        Parse a PDF using the configured backend chain.

        Tries each backend in order until one succeeds.
        """
        error_log: List[str] = []

        for i, backend in enumerate(self.chain):
            is_fallback = i > 0
            backend_name = backend.value.upper()

            try:
                doc = await self._try_backend(backend, pdf_path)
                if doc:
                    print(f"[UnifiedPDFParser] Success with {backend_name}")
                    return ParseResult(
                        document=doc,
                        backend_used=backend,
                        fallback_used=is_fallback,
                        error_log=error_log,
                    )
            except Exception as e:
                msg = f"{backend_name} failed: {e}"
                print(f"[UnifiedPDFParser] {msg}")
                error_log.append(msg)
                continue

        # All backends failed
        raise RuntimeError(
            f"All PDF parsers failed for {pdf_path.name}. "
            f"Errors: {'; '.join(error_log)}"
        )

    async def _try_backend(self, backend: ParserBackend, pdf_path: Path) -> Optional[Any]:
        """Try a specific backend."""
        if backend == ParserBackend.MARKER:
            return await self._try_marker(pdf_path)
        elif backend == ParserBackend.GROBID:
            return await self._try_grobid(pdf_path)
        elif backend == ParserBackend.PYPDF:
            return self._try_pypdf(pdf_path)
        return None

    # ------------------------------------------------------------------
    # Individual backend wrappers
    # ------------------------------------------------------------------

    async def _try_marker(self, pdf_path: Path) -> Optional[Any]:
        """Try Marker PDF parser."""
        if not getattr(settings, "MARKER_ENABLED", True):
            print("[UnifiedPDFParser] Marker disabled in config")
            return None

        try:
            from backend.services.marker_client import MarkerClient
            client = MarkerClient()
            if not client.is_available():
                print("[UnifiedPDFParser] Marker not installed")
                return None
            return await client.process_pdf(pdf_path)
        except ImportError:
            print("[UnifiedPDFParser] marker-pdf not installed")
            return None

    async def _try_grobid(self, pdf_path: Path) -> Optional[Any]:
        """Try GROBID parser."""
        if not getattr(settings, "GROBID_ENABLED", True):
            print("[UnifiedPDFParser] GROBID disabled in config")
            return None

        try:
            from backend.services.grobid_client import GrobidClient
            client = GrobidClient()
            if not await client.is_available():
                print("[UnifiedPDFParser] GROBID service not available")
                return None
            return await client.process_fulltext(pdf_path)
        except Exception as e:
            print(f"[UnifiedPDFParser] GROBID error: {e}")
            return None

    def _try_pypdf(self, pdf_path: Path) -> Optional[Any]:
        """Try PyPDF parser (synchronous)."""
        try:
            from backend.ingestion.pdf_parser import extract_text_from_pdf
            from backend.services.marker_client import MarkerExtractedDocument, MarkerSection

            result = extract_text_from_pdf(pdf_path)
            full_text = "\n".join([page["text"] for page in result["pages"]])

            doc = MarkerExtractedDocument(
                title=None,
                abstract=None,
                body_text=full_text,
            )
            doc.sections.append(MarkerSection(heading=None, text=full_text))
            return doc
        except Exception as e:
            print(f"[UnifiedPDFParser] PyPDF error: {e}")
            return None


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

async def parse_pdf_unified(
    pdf_path: Path,
    primary: Optional[str] = None,
    fallback_chain: Optional[List[str]] = None,
) -> ParseResult:
    """
    Parse a PDF with the unified parser.

    Args:
        pdf_path: Path to the PDF file.
        primary: Override primary backend ("marker", "grobid", "pypdf").
        fallback_chain: Override fallback chain as list of backend names.

    Returns:
        ParseResult with document and backend metadata.
    """
    primary_backend = ParserBackend(primary) if primary else None
    chain = [ParserBackend(b) for b in fallback_chain] if fallback_chain else None

    parser = UnifiedPDFParser(
        primary_backend=primary_backend,
        fallback_chain=chain,
    )
    return await parser.parse(pdf_path)
