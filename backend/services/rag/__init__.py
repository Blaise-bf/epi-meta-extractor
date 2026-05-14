"""RAG (Retrieval-Augmented Generation) components for epidemiologic study extraction.

This package implements LangChain-based RAG following the RealPython tutorial:
https://realpython.com/build-llm-rag-chatbot-with-langchain/

Components:
- document_loader: Load and split study texts into LangChain Documents
- vector_store: In-memory vector store for per-study indexing
- retriever: LangChain-compatible retriever for study chunks
- chains: LCEL chains for metadata/methods/analysis extraction
- agent: Agent-based extraction with tool routing
"""

from backend.services.rag.document_loader import StudyDocumentLoader, StudyTextSplitter
from backend.services.rag.vector_store import InMemoryStudyVectorStore
from backend.services.rag.retriever import StudyRetriever
from backend.services.rag.chains import (
    build_metadata_rag_chain,
    build_methods_rag_chain,
    build_analysis_rag_chain,
    run_parallel_extraction,
)
from backend.services.rag.agent import build_extraction_agent, extract_with_agent

__all__ = [
    "StudyDocumentLoader",
    "StudyTextSplitter",
    "InMemoryStudyVectorStore",
    "StudyRetriever",
    "build_metadata_rag_chain",
    "build_methods_rag_chain",
    "build_analysis_rag_chain",
    "run_parallel_extraction",
    "build_extraction_agent",
    "extract_with_agent",
]
