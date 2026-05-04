from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.agents import config_data as config

class VectorStoreService(object):
    def __init__(self, embedding):
        self.embedding = embedding
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        return self.chroma.as_retriever(search_kwargs={"k": config.similarity_threshold})

if __name__ == "__main__":
    vector_store = VectorStore(DashScopeEmbeddings(model="text-embedding-v4"))
    retriever = vector_store.get_retriever()
    print(retriever.invoke("hello world"))