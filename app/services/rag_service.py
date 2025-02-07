# services/rag_service.py
from logzero import logger
from openai import AsyncOpenAI
from typing import List, Dict
from app.services.vector.embeddings import EmbeddingService
from app.services.vector.pinecone_service import PineconeService
from app.config import settings

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService(settings.OPENAI_API_KEY)
        self.pinecone_service = PineconeService()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _create_prompt(self, query: str, context: List[str]) -> List[Dict]:
        context_text = "\n\n".join(context)
        return [
            {"role": "system", "content": "You are a helpful assistant analyzing documents. Provide detailed answers based on the context provided."},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}\n\nProvide a detailed answer using specific information from the context."}
        ]

    async def process_query(self, query: str) -> Dict:
        try:
            query_embedding = await self.embedding_service.get_embeddings(query)
            logger.info("Generated query embeddings")
            
            search_results = await self.pinecone_service.hybrid_search(query_embedding, k=3)
            logger.info("Completed vector search")
            
            contexts = []
            sources = []
            for match in search_results.matches:
                if match.metadata and 'text' in match.metadata:
                    contexts.append(match.metadata['text'])
                    sources.append({
                        "page": int(match.metadata.get('page_num', 0)),
                        "score": float(match.score)
                    })

            if not contexts:
                return {
                    "answer": "No relevant information found in the document.",
                    "sources": [],
                    "confidence_score": 0.0
                }

            messages = self._create_prompt(query, contexts)
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # or "gpt-4" for better performance
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0
            
            return {
                "answer": response.choices[0].message.content.strip(),
                "sources": sources,
                "confidence_score": avg_score
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            raise