from openai import OpenAI
from typing import List
from backend.config import settings

class EmbeddingService:
    def __init__(self):
        # Embeddings are optional for testing with DeepSeek
        self.enabled = bool(settings.OPENAI_API_KEY)
        if self.enabled:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.EMBEDDING_MODEL
        else:
            self.client = None
            self.model = None
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        if not self.enabled:
            # Return mock embedding for testing without OpenAI
            return self._get_mock_embedding(text)
        
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return self._get_mock_embedding(text)
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        if not self.enabled:
            # Return mock embeddings for testing without OpenAI
            return [self._get_mock_embedding(text) for text in texts]
        
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            return [self._get_mock_embedding(text) for text in texts]
    
    def embed_study_text(self, study_content: str) -> List[float]:
        """Embed study content for RAG"""
        # Take first 2000 chars for embedding (OpenAI limit is 8191 tokens)
        text_to_embed = study_content[:2000]
        return self.get_embedding(text_to_embed)
    
    def _get_mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding for testing without API key"""
        # Simple hash-based embedding for testing
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to list of floats (1536 dimensions like text-embedding-3-small)
        embedding = []
        hash_len = len(hash_val)
        
        for i in range(settings.EMBEDDING_DIMENSION):
            # Use different parts of hash to create pseudo-random values
            start_idx = (i * 2) % hash_len
            end_idx = (start_idx + 2) % hash_len if start_idx + 2 <= hash_len else hash_len
            
            hash_part = hash_val[start_idx:end_idx]
            
            # Handle case where we get empty string or single char
            if not hash_part:
                hash_part = hash_val[0]
            
            try:
                val = int(hash_part, 16) / 255.0 - 0.5  # Normalize to [-0.5, 0.5]
            except ValueError:
                val = 0.0  # Fallback to 0 if conversion fails
            
            embedding.append(val)
        
        return embedding

# Global instance
embedding_service = EmbeddingService()
