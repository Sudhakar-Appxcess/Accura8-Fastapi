# services/pdf_processor.py
from PyPDF2 import PdfReader
from io import BytesIO
from typing import List, Dict
import uuid
from logzero import logger

class PDFProcessor:
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200

    def process_pdf(self, file_content: bytes) -> List[Dict]:
        try:
            # Convert bytes to BytesIO object
            pdf_file = BytesIO(file_content)
            reader = PdfReader(pdf_file)
            chunks = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():  # Only process non-empty pages
                    page_chunks = self._create_chunks(text, page_num)
                    chunks.extend(page_chunks)
                    
            return chunks
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise

    def _create_chunks(self, text: str, page_num: int) -> List[Dict]:
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            current_chunk.append(word)
            current_size += 1
            
            if current_size >= self.chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "metadata": {
                        "page_num": page_num,
                        "chunk_size": len(current_chunk)
                    }
                })
                # Maintain overlap
                current_chunk = current_chunk[-self.chunk_overlap:]
                current_size = len(current_chunk)
        
        # Add remaining text as final chunk
        if current_chunk:
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": " ".join(current_chunk),
                "metadata": {
                    "page_num": page_num,
                    "chunk_size": len(current_chunk)
                }
            })
            
        return chunks