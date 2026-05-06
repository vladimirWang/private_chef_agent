import copy
import hashlib
import os
from datetime import datetime

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import app.agents.config_data as config


class KnowledgeBase(object):
    def __init__(self):
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_overlap=config.chunk_overlap,
            chunk_size=config.chunk_size,
            length_function=len,
            separators=config.separators,
        )

    def upload_by_str(self, data: str, filename: str) -> str:
        md5_value = get_string_md5(data)
        if check_md5(md5_value):
            return "[跳过]已存在于知识库中"
        chunks = []
        if len(data) > config.chunk_overlap:
            chunks = self.splitter.split_text(data)
        else:
            chunks = [data]
        metadata = {
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": filename,
            "operator": "user01",
        }
        self.chroma.add_texts(
            chunks, metadatas=[copy.deepcopy(metadata) for _ in range(len(chunks))]
        )
        save_md5(md5_value)
        return "[成功]已保存至知识库中"


def save_md5(md5_value: str):
    with open(config.md5_path, "a", encoding="utf-8") as f:
        f.write(md5_value + "\n")


def check_md5(md5_value: str) -> bool:
    if not os.path.exists(config.md5_path):
        open(config.md5_path, "w", encoding="utf-8").close()
        return False
    for line in open(config.md5_path, "r", encoding="utf-8").readlines():
        if line.strip() == md5_value:
            return True
    return False


def get_string_md5(data: str, encoding="utf-8"):
    md5_obj = hashlib.md5()
    md5_obj.update(data.encode(encoding))
    return md5_obj.hexdigest()
