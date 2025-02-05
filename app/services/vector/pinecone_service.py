
# services/pinecone_service.py
from pinecone import Pinecone, ServerlessSpec
from logzero import logger
from typing import List, Dict
from app.config import settings

class PineconeService:
    def __init__(self):
        self._init_pinecone()

    def _init_pinecone(self):
        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Check if index exists
            if settings.PINECONE_INDEX not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=settings.PINECONE_INDEX,
                    dimension=int(settings.EMBEDDING_DIMENSION),
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            
            self.index = self.pc.Index(settings.PINECONE_INDEX)
            logger.info("Pinecone initialized successfully")
            
        except Exception as e:
            logger.error(f"Pinecone initialization failed: {str(e)}")
            raise

    async def upsert_embeddings(self, vectors: List[Dict]):
        try:
            self.index.upsert(vectors=vectors)
            logger.info(f"Upserted {len(vectors)} vectors")
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {str(e)}")
            raise

    async def hybrid_search(self, query_embedding: List[float], k: int = 3):
        try:
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True
            )
            return results
        except Exception as e:
            logger.error(f"Pinecone query failed: {str(e)}")
            raise