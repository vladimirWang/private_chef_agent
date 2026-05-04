from gc import collect
import hashlib
import os
from app.agents import config_data as config
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from datetime import datetime

load_dotenv()
def get_string_md5(txt: str) -> str:
    md5_obj = hashlib.md5()
    md5_obj.update(txt.encode())
    hash_code = md5_obj.hexdigest()
    return hash_code

def check_md5(md5_value: str) -> bool:
    if not os.path.exists(config.md5_path):
        open(config.md5_path, "w").close()
        return False
    for line in open(config.md5_path, "r", encoding="utf-8").readlines():
        if line.strip() == md5_value:
            return True
    return False

def save_md5(md5_value: str):
    with open(config.md5_path, "a", encoding="utf-8") as f:
        f.write(md5_value + "\n")

class KnowledgeBase(object):
    def __init__(self):
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            separators=config.separators,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
        )

    def upload_by_str(self, text: str, filename: str) -> str:
        md5_value = get_string_md5(text)
        if check_md5(md5_value):
            return "[跳过]内容已存在"
        knowledge_chunks = []
        if len(text) > config.chunk_size:
            knowledge_chunks = self.splitter.split_text(text)
        else:
            knowledge_chunks = [text]
            
        metadata = {
            "operator": "user",
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": filename
        }
        metadata_list = [metadata] * len(knowledge_chunks)
        print(type(metadata_list))
        for i in metadata_list:
            print(i)

        self.chroma.add_texts(
            texts=knowledge_chunks,
            metadatas=[metadata for _ in range(len(knowledge_chunks))],
        )        
        save_md5(text)
        return "[成功]内容已保存"
if __name__ == "__main__":
    kb = KnowledgeBase()
    kb.upload_by_str("hello world", "test.txt")