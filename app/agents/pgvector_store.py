import os
from functools import lru_cache

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import select

import app.agents.config_data as config
from app.common.reader import logical_filename_from_storage_name


def _pg_connection_url() -> str:
    url = (os.getenv("SQLALCHEMY_DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError("未配置 SQLALCHEMY_DATABASE_URL 或 PG_DSN")
    return url


def get_embeddings() -> DashScopeEmbeddings:
    return DashScopeEmbeddings(model=config.embedding_model)


@lru_cache(maxsize=1)
def get_pgvector_store() -> PGVector:
    """与 ruoyi-backend 共用 PostgreSQL 中的 PGVector（collection: ragPractice）。"""
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=config.collection_name,
        connection=_pg_connection_url(),
        use_jsonb=True,
        embedding_length=config.embedding_length,
        create_extension=True,
    )


def delete_by_logical_source(store: PGVector, logical_source: str) -> int:
    """删除同一逻辑文件的历史向量（含旧版带时间戳的 source）。"""
    ids_to_delete: list[str] = []
    with store._make_sync_session() as session:
        collection = store.get_collection(session)
        if not collection:
            return 0
        rows = session.execute(
            select(store.EmbeddingStore.id, store.EmbeddingStore.cmetadata).where(
                store.EmbeddingStore.collection_id == collection.uuid
            )
        ).all()
        for row_id, cmetadata in rows:
            src = (cmetadata or {}).get("source") or ""
            if logical_filename_from_storage_name(src) == logical_source:
                ids_to_delete.append(row_id)

    if ids_to_delete:
        store.delete(ids=ids_to_delete, collection_only=True)
    return len(ids_to_delete)
