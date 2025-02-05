from langchain_openai import OpenAIEmbeddings

class EmbeddingService:
    def __init__(self, api_key: str):
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    async def get_embeddings(self, text: str):
        return await self.embeddings.aembed_query(text)