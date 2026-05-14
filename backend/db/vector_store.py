from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any, Optional
from backend.config import settings
import uuid

class QdrantVectorStore:
    client: QdrantClient = None
    collection_name: str = settings.QDRANT_COLLECTION_NAME
    vector_size: int = settings.EMBEDDING_DIMENSION

    @classmethod
    async def init(cls):
        """Initialize Qdrant client"""
        try:
            # Try to connect to Qdrant
            cls.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )

            # Check if collection exists
            try:
                cls.client.get_collection(cls.collection_name)
            except Exception:
                # Create collection if it doesn't exist
                cls.client.create_collection(
                    collection_name=cls.collection_name,
                    vectors_config=VectorParams(
                        size=cls.vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"✓ Created Qdrant collection: {cls.collection_name}")

            print(f"✓ Connected to Qdrant at {settings.QDRANT_URL}")
        except Exception as e:
            print(f"⚠ Could not connect to Qdrant: {e}")
            print("  Vector store operations will be disabled")

    @classmethod
    async def add_vector(
        cls,
        study_id: str,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Add a vector to the store"""
        try:
            if not cls.client:
                return False

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "study_id": study_id,
                    "text": text[:1000],  # Limit payload size
                    **metadata
                }
            )

            cls.client.upsert(
                collection_name=cls.collection_name,
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Error adding vector: {e}")
            return False

    @classmethod
    async def search(
        cls,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        try:
            if not cls.client:
                return []

            results = cls.client.search(
                collection_name=cls.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                {
                    "study_id": result.payload.get("study_id"),
                    "text": result.payload.get("text"),
                    "score": result.score,
                    "metadata": {k: v for k, v in result.payload.items()
                                if k not in ["study_id", "text"]}
                }
                for result in results
            ]
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []

    @classmethod
    async def delete_vector(cls, study_id: str) -> bool:
        """Delete vectors for a study"""
        try:
            if not cls.client:
                return False

            cls.client.delete(
                collection_name=cls.collection_name,
                points_selector={
                    "filter": {
                        "has_id": [
                            {
                                "key": "study_id",
                                "match": {"value": study_id}
                            }
                        ]
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error deleting vector: {e}")
            return False

    @classmethod
    async def clear_collection(cls) -> bool:
        """Clear the collection (use with caution)"""
        try:
            if not cls.client:
                return False

            cls.client.delete_collection(cls.collection_name)
            cls.client.create_collection(
                collection_name=cls.collection_name,
                vectors_config=VectorParams(
                    size=cls.vector_size,
                    distance=Distance.COSINE
                )
            )
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

# Global instance
vector_store = QdrantVectorStore()
