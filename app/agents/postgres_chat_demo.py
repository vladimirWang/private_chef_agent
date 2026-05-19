"""
极简 Demo：PostgreSQL 存对话 + ChatTongyi

前置：本机 PG 可连；DASHSCOPE_API_KEY 写在 private_chef_agent/.env.dev
运行：cd private_chef_agent && ./run-postgres-chat-demo.sh
"""

import json

import psycopg
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

# ---------- 硬编码（按本机改）----------
PG_DSN = "postgresql://root:123456@127.0.0.1:5432/assistant"
SESSION_ID = "demo_session_1"
MODEL_NAME = "qwen3-max"

DDL = """
CREATE TABLE IF NOT EXISTS agent_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_chat_session ON agent_chat_messages(session_id);
"""


def init_db() -> None:
    with psycopg.connect(PG_DSN) as conn:
        conn.execute(DDL)
        conn.commit()


class PostgresChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> list[BaseMessage]:
        with psycopg.connect(PG_DSN) as conn:
            rows = conn.execute(
                "SELECT payload FROM agent_chat_messages WHERE session_id = %s ORDER BY id",
                (self.session_id,),
            ).fetchall()
        return messages_from_dict([row[0] for row in rows])

    def add_messages(self, messages: list[BaseMessage]) -> None:
        with psycopg.connect(PG_DSN) as conn:
            for m in messages:
                conn.execute(
                    "INSERT INTO agent_chat_messages (session_id, payload) VALUES (%s, %s)",
                    (self.session_id, json.dumps(message_to_dict(m))),
                )
            conn.commit()

    def clear(self) -> None:
        with psycopg.connect(PG_DSN) as conn:
            conn.execute(
                "DELETE FROM agent_chat_messages WHERE session_id = %s",
                (self.session_id,),
            )
            conn.commit()


def get_history(session_id: str) -> PostgresChatMessageHistory:
    return PostgresChatMessageHistory(session_id)


def build_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是简洁助手。"),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]
    )
    model = ChatTongyi(model=MODEL_NAME)
    return RunnableWithMessageHistory(
        prompt | model,
        get_history,
        input_messages_key="input",
        history_messages_key="history",
    )


if __name__ == "__main__":
    init_db()
    chain = build_chain()
    cfg = {"configurable": {"session_id": SESSION_ID}}

    r1 = chain.invoke({"input": "你好，记住我叫小明"}, cfg)
    print("Q1:", r1.content)

    r2 = chain.invoke({"input": "我叫什么？"}, cfg)
    print("Q2:", r2.content)
