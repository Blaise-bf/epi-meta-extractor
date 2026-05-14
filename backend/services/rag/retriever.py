"""LangChain-compatible retriever backed by Qdrant vector store.

Follows the RealPython pattern of wrapping a vector DB as a retriever
that can be plugged into LCEL chains.
"""

from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field

from backend.db.vector_store import QdrantVectorStore
from backend.services.embeddings import embedding_service


class StudyRetriever(BaseRetriever):
    """Retrieve relevant study chunks from Qdrant vector store.

    Implements LangChain's BaseRetriever so it can be used in LCEL chains
    with the pipe operator: retriever | prompt | llm
    """

    collection_name: str = Field(default="epi_studies")
    k: int = Field(default=5)
    score_threshold: float = Field(default=0.7)

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Synchronous retrieval — delegates to async internally."""
        import asyncio
        try:
            return asyncio.get_event_loop().run_until_complete(
                self._aget_relevant_documents(query, run_manager=run_manager)
            )
        except RuntimeError:
            # No event loop running — create a new one
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self._aget_relevant_documents(query, run_manager=run_manager)
                )
            finally:
                loop.close()

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Async retrieval from Qdrant."""
        # Get query embedding
        query_embedding = embedding_service.get_embedding(query)

        # Search vector store
        results = await QdrantVectorStore.search(
            query_embedding=query_embedding,
            limit=self.k,
            score_threshold=self.score_threshold,
        )

        # Convert to LangChain Documents
        documents = []
        for result in results:
            doc = Document(
                page_content=result.get("text", ""),
                metadata={
                    "study_id": result.get("study_id"),
                    "score": result.get("score"),
                    **result.get("metadata", {}),
                }
            )
            documents.append(doc)

        return documents

    @classmethod
    def from_study_id(cls, study_id: str, k: int = 5) -> "StudyRetriever":
        """Create a retriever scoped to a specific study."""
        # For now, return a standard retriever; filtering by study_id
        # would require Qdrant payload filtering which can be added later
        return cls(k=k)
