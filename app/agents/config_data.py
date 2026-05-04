collection_name = "clothing"

chunk_size = 1000
chunk_overlap = 100

md5_path = "./md5.txt"
persist_directory = "./chroma_db"

separators=["\n\n", "\n", "!", ".", "?", "。", "！", "？", " ", ""]

similarity_threshold = 2

# DashScope 嵌入与对话（与 knowledge_base / private_chef 保持一致）
embedding_model = "text-embedding-v4"
chat_model_name = "qwen3.5-plus"