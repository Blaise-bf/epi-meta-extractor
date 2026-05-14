"""LangChain-compatible document loaders for epidemiologic study texts.

Follows the pattern from RealPython's RAG tutorial:
https://realpython.com/build-llm-rag-chatbot-with-langchain/
"""

from typing import List, Optional, Iterator
from pathlib import Path
from langchain_core.documents import Document


class StudyDocumentLoader:
    """Load study texts as LangChain Document objects.

    Mirrors the CSVLoader pattern from the tutorial but adapted for
    raw study text strings or PDF-extracted text.
    """

    def __init__(self, text: Optional[str] = None, source: Optional[str] = None):
        self.text = text or ""
        self.source = source or "unknown"

    def load(self) -> List[Document]:
        """Load the study text as a single Document."""
        if not self.text:
            return []
        return [Document(
            page_content=self.text,
            metadata={"source": self.source, "type": "study_text"}
        )]

    @classmethod
    def from_text(cls, text: str, source: str = "study") -> List[Document]:
        """Factory: create Documents from raw text."""
        loader = cls(text=text, source=source)
        return loader.load()

    @classmethod
    def from_pdf_path(cls, pdf_path: str) -> List[Document]:
        """Factory: load text from a PDF file path."""
        from backend.ingestion.pdf_parser import extract_text_from_pdf
        text = extract_text_from_pdf(Path(pdf_path))
        return cls.from_text(text, source=pdf_path)


class StudyTextSplitter:
    """Split study documents into semantically meaningful chunks.

    Uses RecursiveCharacterTextSplitter with section-aware separators.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or [
                "\n\n## ",
                "\n\n### ",
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        return self.splitter.split_documents(documents)

    def split_text(self, text: str) -> List[str]:
        """Split raw text into chunks."""
        return self.splitter.split_text(text)
