from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

import app.agents.config_data as config


class VectorStore(object):
    def __init__(self):
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        return self.chroma.as_retriever(search_kwargs={"k": config.search_kwargs})
