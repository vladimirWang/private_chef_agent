import copy
import hashlib
import os
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

import app.agents.config_data as config
from app.agents.pgvector_store import delete_by_logical_source, get_pgvector_store
from app.common.reader import logical_filename_from_storage_name


class KnowledgeBase(object):
    def __init__(self):
        self.vector_store = get_pgvector_store()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_overlap=config.chunk_overlap,
            chunk_size=config.chunk_size,
            length_function=len,
            separators=config.separators,
        )

    def _delete_by_logical_source(self, logical_source: str) -> int:
        return delete_by_logical_source(self.vector_store, logical_source)

    def delete_by_filename(self, filename: str) -> int:
        logical_source = logical_filename_from_storage_name(filename)
        return self._delete_by_logical_source(logical_source)

    def upload_by_str(self, data: str, filename: str, operator: str = "system") -> str:
        logical_source = logical_filename_from_storage_name(filename)
        removed = self._delete_by_logical_source(logical_source)

        chunks = []
        if len(data) > config.chunk_overlap:
            chunks = self.splitter.split_text(data)
        else:
            chunks = [data]
        metadata = {
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": logical_source,
            "operator": operator,
        }
        self.vector_store.add_texts(
            chunks, metadatas=[copy.deepcopy(metadata) for _ in range(len(chunks))]
        )
        save_md5(get_string_md5(data))
        if removed:
            return f"[成功]已更新知识库（替换 {removed} 条旧记录）"
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
