"""In-memory vector store for on-the-fly study text indexing.

Used by RAG chains to index a single study's text and retrieve
relevant chunks during extraction.
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from backend.services.embeddings import embedding_service
from backend.services.rag.document_loader import StudyTextSplitter


class InMemoryStudyVectorStore:
    """Simple in-memory vector store for a single study's text.

    Indexes study text chunks and provides similarity search.
    This is lighter than Qdrant for temporary per-study RAG.
    """

    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings: List[List[float]] = []

    async def index_study_text(self, text: str) -> None:
        """Split and index study text."""
        splitter = StudyTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(text)

        self.documents = [
            Document(page_content=chunk, metadata={"chunk_index": i})
            for i, chunk in enumerate(chunks)
        ]

        # Get embeddings for all chunks
        texts = [doc.page_content for doc in self.documents]
        self.embeddings = embedding_service.get_embeddings_batch(texts)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """Search for relevant chunks using cosine similarity."""
        if not self.documents or not self.embeddings:
            return []

        # Get query embedding
        query_embedding = embedding_service.get_embedding(query)

        # Compute cosine similarities
        import numpy as np
        query_vec = np.array(query_embedding)
        doc_vecs = np.array(self.embeddings)

        # Normalize vectors
        query_vec = query_vec / np.linalg.norm(query_vec)
        doc_vecs = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)

        # Compute similarities
        similarities = np.dot(doc_vecs, query_vec)

        # Get top-k indices
        top_k = min(k, len(self.documents))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Filter by threshold
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score_threshold and score < score_threshold:
                continue
            doc = Document(
                page_content=self.documents[idx].page_content,
                metadata={**self.documents[idx].metadata, "score": score}
            )
            results.append(doc)

        return results
