# from fastapi import APIRouter, UploadFile, File, HTTPException
# from logzero import logger
from app.services.pdf_processor import PDFProcessor
from app.services.vector.embeddings import EmbeddingService
from app.services.vector.pinecone_service import PineconeService
from app.services.rag_service import RAGService
from app.schemas.pdf_chat import QueryRequest, QueryResponse
from app.config import settings

# router = APIRouter()
# pdf_processor = PDFProcessor()
# embedding_service = EmbeddingService(settings.OPENAI_API_KEY)
# pinecone_service = PineconeService()
# rag_service = RAGService()

# @router.post("/upload")
# async def upload_pdf(file: UploadFile = File(...)):
#     try:
#         if not file.filename.endswith('.pdf'):
#             raise HTTPException(status_code=400, detail="Only PDF files are allowed")
            
#         content = await file.read()
#         chunks = pdf_processor.process_pdf(content)
        
#         vectors = []
#         for chunk in chunks:
#             embedding = await embedding_service.get_embeddings(chunk["text"])
#             vectors.append({
#                 "id": chunk["id"],
#                 "values": embedding,
#                 "metadata": {
#                     "text": chunk["text"],
#                     "page_num": chunk["metadata"]["page_num"]
#                 }
#             })
        
#         await pinecone_service.upsert_embeddings(vectors)
#         return {"message": "PDF processed and indexed successfully"}
        
#     except Exception as e:
#         logger.error(f"PDF upload failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/query", response_model=QueryResponse)
# async def query_pdf(request: QueryRequest):
#     try:
#         result = await rag_service.process_query(request.query)
#         return QueryResponse(**result)
        
#     except Exception as e:
#         logger.error(f"Query processing failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# routes/pdf_qa.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from logzero import logger
from typing import List

router = APIRouter()
pdf_processor = PDFProcessor()
embedding_service = EmbeddingService(settings.OPENAI_API_KEY)
pinecone_service = PineconeService()
rag_service = RAGService()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Process PDF
        chunks = pdf_processor.process_pdf(content)
        
        if not chunks:
            return JSONResponse(
                status_code=400,
                content={"message": "No content could be extracted from the PDF"}
            )
        
        # Create embeddings and store in Pinecone
        vectors = []
        for chunk in chunks:
            embedding = await embedding_service.get_embeddings(chunk["text"])
            vectors.append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "page_num": chunk["metadata"]["page_num"]
                }
            })
        
        await pinecone_service.upsert_embeddings(vectors)
        
        return JSONResponse(
            status_code=200,
            content={"message": f"PDF processed successfully. Extracted {len(chunks)} chunks."}
        )
        
    except Exception as e:
        logger.error(f"PDF upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/query", response_model=QueryResponse)
async def query_pdf(request: QueryRequest):
    try:
        result = await rag_service.process_query(request.query)
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )