from typing import List
from backend.config import settings

class EmbeddingService:
    """Embedding service supporting multiple providers: OpenAI, Gemini."""

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.enabled = False
        self.client = None
        self.model = None

        if self.provider == "gemini":
            self._init_gemini()
        else:
            self._init_openai()

    def _init_openai(self):
        """Initialize OpenAI embedding client."""
        self.enabled = bool(settings.OPENAI_API_KEY)
        if self.enabled:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.EMBEDDING_MODEL
        else:
            print("[EmbeddingService] OpenAI API key not set. Using mock embeddings.")

    def _init_gemini(self):
        """Initialize Gemini embedding client."""
        self.enabled = bool(settings.GEMINI_API_KEY)
        if self.enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.client = genai
                self.model = settings.GEMINI_EMBEDDING_MODEL
                print(f"[EmbeddingService] Gemini embeddings initialized with model: {self.model}")
            except ImportError:
                print("[EmbeddingService] google-generativeai not installed. Run: pip install google-generativeai")
                self.enabled = False
        else:
            print("[EmbeddingService] Gemini API key not set. Using mock embeddings.")

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        if not self.enabled:
            return self._get_mock_embedding(text)

        try:
            if self.provider == "gemini":
                return self._get_gemini_embedding(text)
            else:
                return self._get_openai_embedding(text)
        except Exception as e:
            print(f"[EmbeddingService] Error getting embedding: {e}")
            return self._get_mock_embedding(text)

    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding via OpenAI API."""
        response = self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding

    def _get_gemini_embedding(self, text: str) -> List[float]:
        """Get embedding via Gemini API."""
        result = self.client.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.enabled:
            return [self._get_mock_embedding(text) for text in texts]

        try:
            if self.provider == "gemini":
                # Gemini doesn't support batch in the same way; fallback to sequential
                return [self._get_gemini_embedding(text) for text in texts]
            else:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model
                )
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_data]
        except Exception as e:
            print(f"[EmbeddingService] Error getting batch embeddings: {e}")
            return [self._get_mock_embedding(text) for text in texts]

    def embed_study_text(self, study_content: str) -> List[float]:
        """Embed study content for RAG."""
        text_to_embed = study_content[:2000]
        return self.get_embedding(text_to_embed)

    def _get_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding for testing without API key."""
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()
        embedding = []
        hash_len = len(hash_val)

        for i in range(settings.EMBEDDING_DIMENSION):
            start_idx = (i * 2) % hash_len
            end_idx = (start_idx + 2) % hash_len if start_idx + 2 <= hash_len else hash_len
            hash_part = hash_val[start_idx:end_idx]
            if not hash_part:
                hash_part = hash_val[0]
            try:
                val = int(hash_part, 16) / 255.0 - 0.5
            except ValueError:
                val = 0.0
            embedding.append(val)

        return embedding

# Global instance
embedding_service = EmbeddingService()
