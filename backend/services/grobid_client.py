"""
GROBID client for structured PDF parsing of scientific articles.

GROBID (GeneRation Of BIbliographic Data) is a machine learning library
for extracting, parsing, and re-structuring raw documents such as PDFs.
It extracts metadata, bibliographic references, and structured full text.

Service endpoints:
- /api/processFulltextDocument  → Full text with structure (TEI XML)
- /api/processHeaderDocument    → Header/metadata only (TEI XML)
- /api/processReferences        → References only (TEI XML)

Docker image: grobid/grobid:0.8.0 (or latest)
"""

import asyncio
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

import httpx
from backend.config import settings


# ---------------------------------------------------------------------------
# Data classes for structured GROBID output
# ---------------------------------------------------------------------------

@dataclass
class GrobidAuthor:
    """Structured author information from GROBID"""
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    surname: Optional[str] = None
    raw_name: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None


@dataclass
class GrobidReference:
    """A bibliographic reference extracted by GROBID"""
    raw_text: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None


@dataclass
class GrobidSection:
    """A structured section from the article body"""
    heading: Optional[str] = None
    text: str = ""
    figures: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GrobidFigure:
    """A figure from the article"""
    id: Optional[str] = None
    head: Optional[str] = None
    label: Optional[str] = None
    desc: Optional[str] = None
    fig_desc: Optional[str] = None


@dataclass
class GrobidTable:
    """A table from the article"""
    id: Optional[str] = None
    head: Optional[str] = None
    label: Optional[str] = None
    raw_text: Optional[str] = None
    rows: List[List[str]] = field(default_factory=list)


@dataclass
class GrobidExtractedDocument:
    """
    Complete structured document extracted by GROBID.
    This is the primary output of the GROBID parser.
    """
    # Document metadata
    title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    authors: List[GrobidAuthor] = field(default_factory=list)
    submission_date: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None

    # Full text structure
    sections: List[GrobidSection] = field(default_factory=list)
    body_text: str = ""  # Concatenated plain body text

    # Figures and tables
    figures: List[GrobidFigure] = field(default_factory=list)
    tables: List[GrobidTable] = field(default_factory=list)

    # References
    references: List[GrobidReference] = field(default_factory=list)

    # Raw TEI XML (for debugging or advanced use)
    raw_tei_xml: Optional[str] = None

    # Processing metadata
    grobid_version: Optional[str] = None
    grobid_timestamp: Optional[str] = None

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

        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict for JSON storage"""
        return {
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "authors": [
                {
                    "first_name": a.first_name,
                    "middle_name": a.middle_name,
                    "surname": a.surname,
                    "raw_name": a.raw_name,
                    "affiliation": a.affiliation,
                    "email": a.email,
                }
                for a in self.authors
            ],
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
                }
                for s in self.sections
            ],
            "figures_count": len(self.figures),
            "tables_count": len(self.tables),
            "references_count": len(self.references),
            "grobid_version": self.grobid_version,
        }


# ---------------------------------------------------------------------------
# GROBID Client
# ---------------------------------------------------------------------------

class GrobidClient:
    """
    Async HTTP client for the GROBID REST API.

    Usage:
        client = GrobidClient()
        doc = await client.process_pdf("/path/to/article.pdf")
        print(doc.title)
        print(doc.to_plain_text())
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        self.base_url = (base_url or settings.GROBID_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ------------------------------------------------------------------
    # Health & status
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Check if the GROBID service is reachable."""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/isalive",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core extraction endpoints
    # ------------------------------------------------------------------

    async def process_fulltext(
        self,
        pdf_path: Path,
        consolidate_header: bool = True,
        consolidate_citations: bool = False,
        include_raw_citations: bool = False,
        include_raw_affiliations: bool = False,
        tei_coordinates: List[str] = None,
        segment_sentences: bool = False,
    ) -> GrobidExtractedDocument:
        """
        Process a PDF through GROBID's /api/processFulltextDocument endpoint.

        This is the main extraction method — it returns the full structured
        document including metadata, body sections, figures, tables, and refs.
        """
        tei_coordinates = tei_coordinates or []
        params = {
            "consolidateHeader": "1" if consolidate_header else "0",
            "consolidateCitations": "1" if consolidate_citations else "0",
            "includeRawCitations": "1" if include_raw_citations else "0",
            "includeRawAffiliations": "1" if include_raw_affiliations else "0",
            "segmentSentences": "1" if segment_sentences else "0",
            "teiCoordinates": ",".join(tei_coordinates) if tei_coordinates else "",
        }

        pdf_bytes = pdf_path.read_bytes()
        files = {"input": (pdf_path.name, io.BytesIO(pdf_bytes), "application/pdf")}

        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                client = await self._get_client()
                response = await client.post(
                    f"{self.base_url}/api/processFulltextDocument",
                    data=params,
                    files=files,
                )
                response.raise_for_status()
                tei_xml = response.text
                return self._parse_tei(tei_xml)
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 503 and attempt < self.max_retries:
                    # GROBID may be busy — back off and retry
                    wait = 2 ** attempt
                    print(f"[GROBID] Service busy (503), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"[GROBID] Error ({e}), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise

        raise last_exception or RuntimeError("GROBID processing failed")

    async def process_header(
        self,
        pdf_path: Path,
        consolidate_header: bool = True,
    ) -> GrobidExtractedDocument:
        """
        Extract only the header/metadata via /api/processHeaderDocument.
        Faster than fulltext when only metadata is needed.
        """
        params = {
            "consolidateHeader": "1" if consolidate_header else "0",
        }
        pdf_bytes = pdf_path.read_bytes()
        files = {"input": (pdf_path.name, io.BytesIO(pdf_bytes), "application/pdf")}

        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/api/processHeaderDocument",
            data=params,
            files=files,
        )
        response.raise_for_status()
        tei_xml = response.text
        return self._parse_tei(tei_xml)

    # ------------------------------------------------------------------
    # TEI XML Parsing
    # ------------------------------------------------------------------

    def _parse_tei(self, tei_xml: str) -> GrobidExtractedDocument:
        """Parse GROBID TEI XML output into a structured document."""
        doc = GrobidExtractedDocument(raw_tei_xml=tei_xml)

        try:
            root = ET.fromstring(tei_xml.encode("utf-8"))
        except ET.ParseError as e:
            print(f"[GROBID] Failed to parse TEI XML: {e}")
            return doc

        # TEI namespace
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}

        # --- Metadata from <teiHeader> ---
        tei_header = root.find(".//tei:teiHeader", ns)
        if tei_header is not None:
            self._parse_tei_header(tei_header, doc, ns)

        # --- Body text from <text><body> ---
        body = root.find(".//tei:text/tei:body", ns)
        if body is not None:
            self._parse_tei_body(body, doc, ns)

        # --- Figures ---
        for figure_elem in root.findall(".//tei:figure", ns):
            doc.figures.append(self._parse_figure(figure_elem, ns))

        # --- Tables ---
        for table_elem in root.findall(".//tei:table", ns):
            doc.tables.append(self._parse_table(table_elem, ns))

        # --- References ---
        list_bibl = root.find(".//tei:listBibl", ns)
        if list_bibl is not None:
            for bibl in list_bibl.findall("tei:biblStruct", ns):
                doc.references.append(self._parse_reference(bibl, ns))

        # --- GROBID version / timestamp ---
        app_info = root.find(".//tei:application", ns)
        if app_info is not None:
            doc.grobid_version = app_info.get("version")
            doc.grobid_timestamp = app_info.get("when")

        return doc

    # ------------------------------------------------------------------
    # Sub-parsers
    # ------------------------------------------------------------------

    def _parse_tei_header(
        self,
        tei_header: ET.Element,
        doc: GrobidExtractedDocument,
        ns: Dict[str, str],
    ) -> None:
        """Parse <teiHeader> for metadata."""
        file_desc = tei_header.find("tei:fileDesc", ns)
        if file_desc is None:
            return

        # Title
        title_stmt = file_desc.find("tei:titleStmt", ns)
        if title_stmt is not None:
            title_elem = title_stmt.find("tei:title[@type='main']", ns)
            if title_elem is None:
                title_elem = title_stmt.find("tei:title", ns)
            if title_elem is not None and title_elem.text:
                doc.title = self._clean_text(title_elem.text)

        # Authors
        source_desc = file_desc.find("tei:sourceDesc", ns)
        if source_desc is not None:
            bibl_full = source_desc.find("tei:biblStruct", ns)
            if bibl_full is not None:
                analytic = bibl_full.find("tei:analytic", ns)
                if analytic is not None:
                    for author in analytic.findall("tei:author", ns):
                        doc.authors.append(self._parse_author(author, ns))

                # Journal / monograph info
                monogr = bibl_full.find("tei:monogr", ns)
                if monogr is not None:
                    title_elem = monogr.find("tei:title", ns)
                    if title_elem is not None and title_elem.text:
                        doc.journal = self._clean_text(title_elem.text)

                    imprint = monogr.find("tei:imprint", ns)
                    if imprint is not None:
                        date_elem = imprint.find("tei:date[@type='published']", ns)
                        if date_elem is None:
                            date_elem = imprint.find("tei:date", ns)
                        if date_elem is not None:
                            doc.publication_date = date_elem.get("when") or date_elem.text

                    # DOI / PMID / PMCID
                    for idno in monogr.findall("tei:idno", ns):
                        id_type = idno.get("type", "").lower()
                        if id_type == "doi":
                            doc.doi = idno.text
                        elif id_type == "pmid":
                            doc.pmid = idno.text
                        elif id_type == "pmcid":
                            doc.pmcid = idno.text

        # Abstract
        profile_desc = tei_header.find("tei:profileDesc", ns)
        if profile_desc is not None:
            abstract = profile_desc.find("tei:abstract", ns)
            if abstract is not None:
                doc.abstract = self._extract_text_recursive(abstract, ns)

            # Keywords
            keywords = profile_desc.find("tei:textClass/tei:keywords", ns)
            if keywords is not None:
                for term in keywords.findall("tei:term", ns):
                    if term.text:
                        doc.keywords.append(term.text.strip())

    def _parse_tei_body(
        self,
        body: ET.Element,
        doc: GrobidExtractedDocument,
        ns: Dict[str, str],
    ) -> None:
        """Parse <body> into structured sections."""
        body_parts: List[str] = []

        for child in body:
            tag = self._strip_ns(child.tag)

            if tag == "div":
                section = self._parse_section(child, ns)
                if section.text or section.heading:
                    doc.sections.append(section)
                    if section.text:
                        body_parts.append(section.text)
            elif tag == "p":
                para_text = self._extract_text_recursive(child, ns)
                if para_text:
                    body_parts.append(para_text)

        doc.body_text = "\n\n".join(body_parts)

    def _parse_section(self, div: ET.Element, ns: Dict[str, str]) -> GrobidSection:
        """Parse a <div> into a GrobidSection."""
        section = GrobidSection()

        # Heading
        head = div.find("tei:head", ns)
        if head is not None:
            section.heading = self._clean_text(self._extract_text_recursive(head, ns))

        # Paragraphs and nested divs
        parts: List[str] = []
        for child in div:
            tag = self._strip_ns(child.tag)
            if tag == "p":
                para_text = self._extract_text_recursive(child, ns)
                if para_text:
                    parts.append(para_text)
            elif tag == "div":
                # Nested section — flatten for now
                nested = self._parse_section(child, ns)
                if nested.heading:
                    parts.append(f"{nested.heading}")
                if nested.text:
                    parts.append(nested.text)
            elif tag == "figure":
                section.figures.append(self._parse_figure(child, ns))
            elif tag == "table":
                section.tables.append(self._parse_table(child, ns))

        section.text = "\n\n".join(parts)
        return section

    def _parse_author(self, author_elem: ET.Element, ns: Dict[str, str]) -> GrobidAuthor:
        """Parse a <author> element."""
        author = GrobidAuthor()

        pers_name = author_elem.find("tei:persName", ns)
        if pers_name is not None:
            forename = pers_name.find("tei:forename", ns)
            if forename is not None and forename.text:
                author.first_name = forename.text.strip()

            surname = pers_name.find("tei:surname", ns)
            if surname is not None and surname.text:
                author.surname = surname.text.strip()

            # Build raw name
            parts = []
            if author.first_name:
                parts.append(author.first_name)
            if author.surname:
                parts.append(author.surname)
            author.raw_name = " ".join(parts) if parts else None
        else:
            # Fallback: raw text
            raw = self._extract_text_recursive(author_elem, ns)
            if raw:
                author.raw_name = raw.strip()

        # Affiliation
        affiliation = author_elem.find("tei:affiliation", ns)
        if affiliation is not None:
            org = affiliation.find("tei:orgName", ns)
            if org is not None and org.text:
                author.affiliation = org.text.strip()
            else:
                author.affiliation = self._extract_text_recursive(affiliation, ns)

        # Email
        email = author_elem.find("tei:email", ns)
        if email is not None and email.text:
            author.email = email.text.strip()

        return author

    def _parse_figure(self, figure_elem: ET.Element, ns: Dict[str, str]) -> GrobidFigure:
        """Parse a <figure> element."""
        fig = GrobidFigure(id=figure_elem.get("xml:id"))

        head = figure_elem.find("tei:head", ns)
        if head is not None:
            fig.head = self._extract_text_recursive(head, ns)

        label = figure_elem.find("tei:label", ns)
        if label is not None:
            fig.label = label.text

        desc = figure_elem.find("tei:figDesc", ns)
        if desc is not None:
            fig.fig_desc = self._extract_text_recursive(desc, ns)

        return fig

    def _parse_table(self, table_elem: ET.Element, ns: Dict[str, str]) -> GrobidTable:
        """Parse a <table> element."""
        tbl = GrobidTable(id=table_elem.get("xml:id"))

        head = table_elem.find("tei:head", ns)
        if head is not None:
            tbl.head = self._extract_text_recursive(head, ns)

        label = table_elem.find("tei:label", ns)
        if label is not None:
            tbl.label = label.text

        # Extract rows
        rows: List[List[str]] = []
        for row in table_elem.findall("tei:row", ns):
            cells = []
            for cell in row.findall("tei:cell", ns):
                cell_text = self._extract_text_recursive(cell, ns)
                cells.append(cell_text)
            if cells:
                rows.append(cells)
        tbl.rows = rows

        # Raw text fallback
        tbl.raw_text = self._extract_text_recursive(table_elem, ns)

        return tbl

    def _parse_reference(
        self,
        bibl_struct: ET.Element,
        ns: Dict[str, str],
    ) -> GrobidReference:
        """Parse a <biblStruct> reference."""
        ref = GrobidReference()

        # Raw text (analytic + monogr combined)
        ref.raw_text = self._extract_text_recursive(bibl_struct, ns)

        analytic = bibl_struct.find("tei:analytic", ns)
        if analytic is not None:
            title = analytic.find("tei:title", ns)
            if title is not None and title.text:
                ref.title = title.text.strip()

            for author in analytic.findall("tei:author", ns):
                a = self._parse_author(author, ns)
                if a.raw_name:
                    ref.authors.append(a.raw_name)

        monogr = bibl_struct.find("tei:monogr", ns)
        if monogr is not None:
            title = monogr.find("tei:title", ns)
            if title is not None and title.text:
                ref.journal = title.text.strip()

            imprint = monogr.find("tei:imprint", ns)
            if imprint is not None:
                date = imprint.find("tei:date", ns)
                if date is not None:
                    year_str = date.get("when") or date.text
                    if year_str:
                        try:
                            ref.year = int(year_str[:4])
                        except ValueError:
                            pass

            for idno in monogr.findall("tei:idno", ns):
                if idno.get("type", "").lower() == "doi":
                    ref.doi = idno.text

        return ref

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_ns(tag: str) -> str:
        """Remove XML namespace from tag."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @staticmethod
    def _clean_text(text: Optional[str]) -> Optional[str]:
        """Clean extracted text: normalize whitespace."""
        if not text:
            return None
        return " ".join(text.split())

    def _extract_text_recursive(
        self,
        elem: ET.Element,
        ns: Dict[str, str],
    ) -> str:
        """Recursively extract all text from an element and its children."""
        parts = []
        if elem.text and elem.text.strip():
            parts.append(elem.text.strip())
        for child in elem:
            child_text = self._extract_text_recursive(child, ns)
            if child_text:
                parts.append(child_text)
            if child.tail and child.tail.strip():
                parts.append(child.tail.strip())
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Convenience functions (module-level)
# ---------------------------------------------------------------------------

async def parse_pdf_with_grobid(
    pdf_path: Path,
    fallback_to_pypdf: bool = True,
) -> Tuple[GrobidExtractedDocument, bool]:
    """
    Parse a PDF with GROBID, optionally falling back to PyPDF.

    Returns:
        (document, used_grobid): The parsed document and a flag indicating
        whether GROBID was used (True) or PyPDF fallback was used (False).
    """
    client = GrobidClient()

    # Check if GROBID is available
    if await client.is_available():
        try:
            doc = await client.process_fulltext(pdf_path)
            await client.close()
            return doc, True
        except Exception as e:
            print(f"[GROBID] Fulltext extraction failed: {e}")
            if not fallback_to_pypdf:
                raise
    else:
        print("[GROBID] Service not available.")
        if not fallback_to_pypdf:
            raise RuntimeError("GROBID is not available and fallback is disabled")

    await client.close()

    # Fallback to PyPDF
    print("[GROBID] Falling back to PyPDF...")
    from backend.ingestion.pdf_parser import extract_text_from_pdf

    pypdf_result = extract_text_from_pdf(pdf_path)
    full_text = "\n".join([page["text"] for page in pypdf_result["pages"]])

    doc = GrobidExtractedDocument(
        title=None,
        abstract=None,
        body_text=full_text,
    )
    # Create a single section for the whole text
    doc.sections.append(GrobidSection(heading=None, text=full_text))

    return doc, False


# Global singleton for reuse
grobid_client = GrobidClient()
