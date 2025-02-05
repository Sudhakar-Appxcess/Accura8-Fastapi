
# services/chat_service.py
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalQA
from langchain.memory import ConversationBufferMemory
from app.services.pdf_processor import PDFProcessor
import pinecone
from typing import Dict, List
import uuid

class ChatService:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.conversations = {}

    def _get_retriever(self, namespace: str):
        vectorstore = Pinecone.from_existing_index(
            index_name=self.pdf_processor.index_name,
            embedding=self.pdf_processor.embeddings,
            namespace=namespace
        )
        return vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.7
            }
        )

    async def process_query(self, query: str, conversation_id: Optional[str] = None) -> Dict:
        if not conversation_id or conversation_id not in self.conversations:
            conversation_id = str(uuid.uuid4())
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            self.conversations[conversation_id] = {
                "memory": memory,
                "namespace": self.conversations.get(conversation_id, {}).get("namespace")
            }

        conversation = self.conversations[conversation_id]
        retriever = self._get_retriever(conversation["namespace"])

        qa_chain = ConversationalRetrievalQA.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=conversation["memory"],
            return_source_documents=True
        )

        response = await qa_chain.arun({"question": query})
        
        sources = [doc.metadata.get("source", "") for doc in response["source_documents"]]
        
        return {
            "answer": response["answer"],
            "sources": sources,
            "conversation_id": conversation_id
        }