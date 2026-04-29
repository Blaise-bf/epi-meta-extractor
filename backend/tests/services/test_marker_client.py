"""
Tests for the Marker PDF client.

These tests verify the MarkerClient wrapper without requiring
marker-pdf to be installed (uses mocks).
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from backend.services.marker_client import (
    MarkerClient,
    MarkerExtractedDocument,
    MarkerSection,
    MarkerTable,
    MarkerFigure,
    parse_pdf_with_marker,
)


# ---------------------------------------------------------------------------
# MarkerClient availability tests
# ---------------------------------------------------------------------------

class TestMarkerClientAvailability:
    """Tests for checking if marker-pdf is available."""

    def test_is_available_when_installed(self):
        """Test that is_available returns True when marker is installed."""
        with patch.dict("sys.modules", {"marker": MagicMock()}):
            client = MarkerClient()
            assert client.is_available() is True

    def test_is_available_when_not_installed(self):
        """Test that is_available returns False when marker is not installed."""
        with patch.dict("sys.modules", {"marker": None}):
            # Force re-check by creating new client
            client = MarkerClient()
            client._marker_available = None
            assert client.is_available() is False

    def test_is_available_caches_result(self):
        """Test that availability result is cached."""
        client = MarkerClient()
        client._marker_available = True
        assert client.is_available() is True


# ---------------------------------------------------------------------------
# MarkerExtractedDocument tests
# ---------------------------------------------------------------------------

class TestMarkerExtractedDocument:
    """Tests for the MarkerExtractedDocument data class."""

    def test_empty_document(self):
        """Test creating an empty document."""
        doc = MarkerExtractedDocument()
        assert doc.title is None
        assert doc.abstract is None
        assert doc.body_text == ""
        assert doc.sections == []
        assert doc.figures == []
        assert doc.tables == []
        assert doc.references == []

    def test_to_plain_text_empty(self):
        """Test to_plain_text with empty document."""
        doc = MarkerExtractedDocument()
        assert doc.to_plain_text() == ""

    def test_to_plain_text_with_content(self):
        """Test to_plain_text with sections."""
        doc = MarkerExtractedDocument(
            title="Test Title",
            abstract="Test abstract",
        )
        doc.sections = [
            MarkerSection(heading="Introduction", text="Intro text"),
            MarkerSection(heading="Methods", text="Methods text"),
        ]
        text = doc.to_plain_text()
        assert "Title: Test Title" in text
        assert "Abstract: Test abstract" in text
        assert "Introduction" in text
        assert "Intro text" in text
        assert "Methods" in text
        assert "Methods text" in text

    def test_to_plain_text_no_title(self):
        """Test to_plain_text without title."""
        doc = MarkerExtractedDocument()
        doc.sections = [
            MarkerSection(heading="Section 1", text="Text 1"),
        ]
        text = doc.to_plain_text()
        assert "Title:" not in text
        assert "Section 1" in text

    def test_to_dict(self):
        """Test serialization to dict."""
        doc = MarkerExtractedDocument(
            title="Test",
            abstract="Abstract",
            doi="10.1234/test",
        )
        doc.sections = [
            MarkerSection(heading="H1", text="T1", level=1),
        ]
        d = doc.to_dict()
        assert d["title"] == "Test"
        assert d["abstract"] == "Abstract"
        assert d["doi"] == "10.1234/test"
        assert len(d["sections"]) == 1
        assert d["sections"][0]["heading"] == "H1"
        assert d["sections"][0]["level"] == 1


# ---------------------------------------------------------------------------
# Markdown parsing tests
# ---------------------------------------------------------------------------

class TestMarkdownParsing:
    """Tests for the markdown parser."""

    def test_parse_simple_markdown(self):
        """Test parsing simple markdown with headings."""
        client = MarkerClient()
        markdown = "# Title\n\nAbstract text here.\n\n## Methods\n\nMethods text."
        doc = client._parse_markdown(markdown)

        assert doc.title == "Title"
        assert doc.abstract == "Abstract text here."
        assert len(doc.sections) == 2
        assert doc.sections[0].heading == "Title"
        assert doc.sections[1].heading == "Methods"

    def test_parse_markdown_no_headings(self):
        """Test parsing markdown without headings."""
        client = MarkerClient()
        markdown = "Just some plain text without any headings."
        doc = client._parse_markdown(markdown)

        assert doc.title is None
        assert len(doc.sections) == 1
        assert doc.sections[0].text == "Just some plain text without any headings."

    def test_parse_markdown_multiple_levels(self):
        """Test parsing markdown with multiple heading levels."""
        client = MarkerClient()
        markdown = "# Main Title\n\n## Section 1\n\n### Subsection 1.1\n\nText here."
        doc = client._parse_markdown(markdown)

        assert doc.title == "Main Title"
        assert len(doc.sections) == 3
        assert doc.sections[0].level == 1
        assert doc.sections[1].level == 2
        assert doc.sections[2].level == 3

    def test_parse_empty_markdown(self):
        """Test parsing empty markdown."""
        client = MarkerClient()
        doc = client._parse_markdown("")
        assert doc.sections == []
        assert doc.body_text == ""

    def test_parse_markdown_with_tables(self):
        """Test that markdown with tables is preserved in text."""
        client = MarkerClient()
        markdown = "# Results\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        doc = client._parse_markdown(markdown)

        assert len(doc.sections) == 1
        assert "| A | B |" in doc.sections[0].text


# ---------------------------------------------------------------------------
# Async parse tests (mocked)
# ---------------------------------------------------------------------------

class TestParsePdfWithMarker:
    """Tests for the parse_pdf_with_marker function."""

    @pytest.mark.asyncio
    async def test_parse_with_marker_success(self, tmp_path):
        """Test successful parsing with Marker."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy pdf content")

        mock_doc = MarkerExtractedDocument(title="Test", body_text="Body")

        with patch.object(MarkerClient, "is_available", return_value=True):
            with patch.object(
                MarkerClient,
                "process_pdf",
                new_callable=AsyncMock,
                return_value=mock_doc,
            ):
                doc, used_marker = await parse_pdf_with_marker(pdf_path)
                assert used_marker is True
                assert doc.title == "Test"

    @pytest.mark.asyncio
    async def test_parse_with_marker_not_available(self, tmp_path):
        """Test fallback to PyPDF when Marker is not available."""
        pdf_path = tmp_path / "test.pdf"

        # Create a real PDF using reportlab
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "Fallback text")
        c.save()

        with patch.object(MarkerClient, "is_available", return_value=False):
            doc, used_marker = await parse_pdf_with_marker(pdf_path)
            assert used_marker is False
            assert "Fallback text" in doc.body_text

    @pytest.mark.asyncio
    async def test_parse_marker_failure_fallback(self, tmp_path):
        """Test fallback to PyPDF when Marker fails."""
        pdf_path = tmp_path / "test.pdf"

        # Create a real PDF
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "Fallback text")
        c.save()

        with patch.object(MarkerClient, "is_available", return_value=True):
            with patch.object(
                MarkerClient,
                "process_pdf",
                new_callable=AsyncMock,
                side_effect=Exception("Marker failed"),
            ):
                doc, used_marker = await parse_pdf_with_marker(pdf_path)
                assert used_marker is False
                assert "Fallback text" in doc.body_text

    @pytest.mark.asyncio
    async def test_parse_marker_failure_no_fallback(self, tmp_path):
        """Test that exception is raised when fallback is disabled."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        with patch.object(MarkerClient, "is_available", return_value=True):
            with patch.object(
                MarkerClient,
                "process_pdf",
                new_callable=AsyncMock,
                side_effect=Exception("Marker failed"),
            ):
                with pytest.raises(Exception, match="Marker failed"):
                    await parse_pdf_with_marker(pdf_path, fallback_to_pypdf=False)


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------

class TestMarkerIntegration:
    """Integration tests that verify the full flow."""

    def test_document_roundtrip(self):
        """Test that document can be created, converted to dict, and used."""
        doc = MarkerExtractedDocument(
            title="Epidemiological Study",
            abstract="A study about risk factors.",
            doi="10.1000/epi.2024.001",
        )
        doc.sections = [
            MarkerSection(heading="Background", text="Background text"),
            MarkerSection(heading="Results", text="OR = 2.5 (95% CI: 1.2-4.8)"),
        ]

        # Convert to plain text for LLM
        text = doc.to_plain_text()
        assert "Epidemiological Study" in text
        assert "OR = 2.5" in text

        # Convert to dict for storage
        d = doc.to_dict()
        assert d["doi"] == "10.1000/epi.2024.001"
        assert d["sections_count"] == len(d["sections"])

    def test_complex_markdown_structure(self):
        """Test parsing a complex markdown document."""
        client = MarkerClient()
        markdown = """# Systematic Review of Risk Factors

## Abstract

This review examines risk factors for disease X.

## Methods

### Search Strategy

We searched PubMed and Embase.

### Inclusion Criteria

- Cohort studies
- Case-control studies

## Results

| Study | OR | 95% CI |
|-------|-----|--------|
| Smith 2020 | 2.1 | 1.5-2.9 |
| Jones 2021 | 1.8 | 1.2-2.7 |

## Discussion

The results suggest a significant association.
"""
        doc = client._parse_markdown(markdown)

        assert doc.title == "Systematic Review of Risk Factors"
        assert doc.abstract == "This review examines risk factors for disease X."
        assert len(doc.sections) == 5  # Title, Methods, Search Strategy, Results, Discussion

        # Check that table is preserved
        results_section = [s for s in doc.sections if s.heading == "Results"][0]
        assert "| Study |" in results_section.text
