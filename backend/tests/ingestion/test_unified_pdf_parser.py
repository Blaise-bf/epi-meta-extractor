"""
Tests for the unified PDF parser.

These tests verify the UnifiedPDFParser with mocked backends.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from backend.ingestion.unified_pdf_parser import (
    UnifiedPDFParser,
    ParseResult,
    ParserBackend,
    parse_pdf_unified,
)
from backend.services.marker_client import MarkerExtractedDocument, MarkerSection


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------

class TestUnifiedParserConfig:
    """Tests for parser configuration."""

    def test_default_chain(self):
        """Test that default chain is marker → grobid → pypdf."""
        parser = UnifiedPDFParser()
        assert parser.chain[0] == ParserBackend.MARKER
        assert parser.chain[1] == ParserBackend.GROBID
        assert parser.chain[2] == ParserBackend.PYPDF

    def test_custom_primary(self):
        """Test setting a custom primary backend."""
        parser = UnifiedPDFParser(primary_backend=ParserBackend.GROBID)
        assert parser.primary == ParserBackend.GROBID
        assert parser.chain[0] == ParserBackend.GROBID

    def test_custom_chain(self):
        """Test setting a custom fallback chain (primary still prepended)."""
        parser = UnifiedPDFParser(
            fallback_chain=[ParserBackend.PYPDF, ParserBackend.MARKER],
        )
        # Primary (marker from config) is always prepended first
        assert parser.chain[0] == ParserBackend.MARKER
        assert ParserBackend.PYPDF in parser.chain
        assert ParserBackend.GROBID not in parser.chain

    def test_primary_prepended_to_chain(self):
        """Test that primary is always first in chain."""
        parser = UnifiedPDFParser(
            primary_backend=ParserBackend.GROBID,
            fallback_chain=[ParserBackend.PYPDF, ParserBackend.GROBID],
        )
        assert parser.chain[0] == ParserBackend.GROBID
        assert ParserBackend.GROBID not in parser.chain[1:]


# ---------------------------------------------------------------------------
# ParseResult tests
# ---------------------------------------------------------------------------

class TestParseResult:
    """Tests for the ParseResult dataclass."""

    def test_parse_result_creation(self):
        """Test creating a ParseResult."""
        doc = MarkerExtractedDocument(title="Test")
        result = ParseResult(
            document=doc,
            backend_used=ParserBackend.MARKER,
            fallback_used=False,
        )
        assert result.backend_used == ParserBackend.MARKER
        assert result.fallback_used is False
        assert result.processing_time is None

    def test_parse_result_to_plain_text(self):
        """Test to_plain_text delegation."""
        doc = MarkerExtractedDocument(title="Test", body_text="Body")
        result = ParseResult(document=doc, backend_used=ParserBackend.MARKER)
        text = result.to_plain_text()
        assert "Title: Test" in text
        assert "Body" in text

    def test_parse_result_to_dict(self):
        """Test serialization to dict."""
        doc = MarkerExtractedDocument(title="Test")
        result = ParseResult(
            document=doc,
            backend_used=ParserBackend.MARKER,
            fallback_used=True,
            processing_time=1.5,
            error_log=["GROBID failed"],
        )
        d = result.to_dict()
        assert d["backend_used"] == "marker"
        assert d["fallback_used"] is True
        assert d["processing_time"] == 1.5
        assert d["error_log"] == ["GROBID failed"]


# ---------------------------------------------------------------------------
# Backend availability tests
# ---------------------------------------------------------------------------

class TestBackendAvailability:
    """Tests for checking backend availability."""

    def test_marker_not_installed(self):
        """Test that missing marker is handled gracefully."""
        parser = UnifiedPDFParser(fallback_chain=[ParserBackend.MARKER])
        with patch.object(
            parser,
            "_try_marker",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Should return None when marker is not available
            import asyncio
            result = asyncio.run(parser._try_marker(Path("test.pdf")))
            assert result is None

    def test_grobid_disabled(self):
        """Test that disabled GROBID is skipped."""
        parser = UnifiedPDFParser(fallback_chain=[ParserBackend.GROBID])
        with patch("backend.config.settings.GROBID_ENABLED", False):
            import asyncio
            result = asyncio.run(parser._try_grobid(Path("test.pdf")))
            assert result is None

    def test_pypdf_fallback(self, tmp_path):
        """Test PyPDF fallback creates a valid document."""
        parser = UnifiedPDFParser(fallback_chain=[ParserBackend.PYPDF])

        # Create a real PDF
        pdf_path = tmp_path / "test.pdf"
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "Test content")
        c.save()

        doc = parser._try_pypdf(pdf_path)
        assert doc is not None
        assert "Test content" in doc.body_text


# ---------------------------------------------------------------------------
# Main parse flow tests
# ---------------------------------------------------------------------------

class TestParseFlow:
    """Tests for the main parse() method."""

    @pytest.mark.asyncio
    async def test_marker_success(self, tmp_path):
        """Test successful parse with Marker."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_doc = MarkerExtractedDocument(title="Success")
        parser = UnifiedPDFParser(fallback_chain=[ParserBackend.MARKER])

        with patch.object(
            parser,
            "_try_marker",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ):
            result = await parser.parse(pdf_path)
            assert result.backend_used == ParserBackend.MARKER
            assert result.fallback_used is False
            assert result.document.title == "Success"

    @pytest.mark.asyncio
    async def test_marker_fails_grobid_succeeds(self, tmp_path):
        """Test fallback from Marker to GROBID."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_doc = MarkerExtractedDocument(title="GROBID Success")
        parser = UnifiedPDFParser(
            fallback_chain=[ParserBackend.MARKER, ParserBackend.GROBID],
        )

        with patch.object(
            parser,
            "_try_marker",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                parser,
                "_try_grobid",
                new_callable=AsyncMock,
                return_value=mock_doc,
            ):
                result = await parser.parse(pdf_path)
                assert result.backend_used == ParserBackend.GROBID
                assert result.fallback_used is True
                assert result.document.title == "GROBID Success"

    @pytest.mark.asyncio
    async def test_all_backends_fail(self, tmp_path):
        """Test that error is raised when all backends fail."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        parser = UnifiedPDFParser(
            fallback_chain=[ParserBackend.MARKER, ParserBackend.GROBID],
        )

        with patch.object(
            parser,
            "_try_marker",
            new_callable=AsyncMock,
            side_effect=Exception("Marker error"),
        ):
            with patch.object(
                parser,
                "_try_grobid",
                new_callable=AsyncMock,
                side_effect=Exception("GROBID error"),
            ):
                with pytest.raises(RuntimeError, match="All PDF parsers failed"):
                    await parser.parse(pdf_path)

    @pytest.mark.asyncio
    async def test_pypdf_ultimate_fallback(self, tmp_path):
        """Test that PyPDF works as ultimate fallback."""
        pdf_path = tmp_path / "test.pdf"

        # Create a real PDF
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "PyPDF content")
        c.save()

        parser = UnifiedPDFParser(
            fallback_chain=[
                ParserBackend.MARKER,
                ParserBackend.GROBID,
                ParserBackend.PYPDF,
            ],
        )

        with patch.object(
            parser,
            "_try_marker",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                parser,
                "_try_grobid",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await parser.parse(pdf_path)
                assert result.backend_used == ParserBackend.PYPDF
                assert result.fallback_used is True
                assert "PyPDF content" in result.document.body_text


# ---------------------------------------------------------------------------
# parse_pdf_unified convenience function tests
# ---------------------------------------------------------------------------

class TestParsePdfUnified:
    """Tests for the parse_pdf_unified convenience function."""

    @pytest.mark.asyncio
    async def test_with_string_arguments(self, tmp_path):
        """Test using string arguments for backend selection."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_doc = MarkerExtractedDocument(title="Test")

        with patch(
            "backend.ingestion.unified_pdf_parser.UnifiedPDFParser.parse",
            new_callable=AsyncMock,
            return_value=ParseResult(
                document=mock_doc,
                backend_used=ParserBackend.MARKER,
            ),
        ):
            result = await parse_pdf_unified(
                pdf_path,
                primary="marker",
                fallback_chain="marker,pypdf",
            )
            assert result.backend_used == ParserBackend.MARKER


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_pdf(self, tmp_path):
        """Test handling of empty/minimal PDF."""
        pdf_path = tmp_path / "empty.pdf"

        # Create a minimal PDF
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.save()

        parser = UnifiedPDFParser(fallback_chain=[ParserBackend.PYPDF])
        result = await parser.parse(pdf_path)
        assert result.backend_used == ParserBackend.PYPDF
        assert result.document is not None

    def test_invalid_backend_string(self):
        """Test handling of invalid backend string in config."""
        with patch("backend.config.settings.PDF_PARSER_PRIMARY", "invalid"):
            parser = UnifiedPDFParser()
            # Should default to marker
            assert parser.primary == ParserBackend.MARKER

    def test_empty_fallback_chain(self):
        """Test handling of empty fallback chain."""
        with patch("backend.config.settings.PDF_PARSER_FALLBACK_CHAIN", ""):
            parser = UnifiedPDFParser()
            # Should use default chain
            assert len(parser.chain) >= 1
