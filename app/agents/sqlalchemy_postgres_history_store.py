"""
极简 Demo：SQLAlchemy + PostgreSQL 存对话 + ChatTongyi
（表结构由 ruoyi-backend Alembic 管理，此处仅映射 agent_chat_message）

前置：PG_DSN、DASHSCOPE_API_KEY 写在 private_chef_agent/.env.dev
运行：cd private_chef_agent && ./run-sqlalchemy-postgres-chat-demo.sh
"""

import os
from datetime import datetime

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from sqlalchemy import BigInteger, DateTime, Integer, Text, create_engine, delete, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)

SESSION_ID = "demo_session_1"
DEMO_USER_ID = 1
MODEL_NAME = "qwen3-max"


# def _pg_url() -> str:
#     dsn = (
#         os.getenv("PG_DSN", "postgresql://root:123456@127.0.0.1:5432/assistant")
#         or ""
#     ).strip()
#     if dsn.startswith("postgresql://"):
#         return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
#     return dsn

PG_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

engine = create_engine(PG_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class AgentChatMessage(Base):
    __tablename__ = "agent_chat_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def init_db() -> None:
    Base.metadata.create_all(engine)


class SqlAlchemyPostgresChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def messages(self) -> list[BaseMessage]:
        with Session(engine) as db:
            rows = db.scalars(
                select(AgentChatMessage)
                .where(AgentChatMessage.session_id == self.session_id)
                .order_by(AgentChatMessage.id)
            ).all()
        return messages_from_dict([row.payload for row in rows])

    def add_messages(self, messages: list[BaseMessage]) -> None:
        with Session(engine) as db:
            for m in messages:
                db.add(
                    AgentChatMessage(
                        user_id=DEMO_USER_ID,
                        session_id=self.session_id,
                        payload=message_to_dict(m),
                    )
                )
            db.commit()

    def clear(self) -> None:
        with Session(engine) as db:
            db.execute(
                delete(AgentChatMessage).where(
                    AgentChatMessage.session_id == self.session_id
                )
            )
            db.commit()


def get_history(session_id: str) -> SqlAlchemyPostgresChatMessageHistory:
    return SqlAlchemyPostgresChatMessageHistory(session_id)


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
    # 表由 ruoyi-backend Alembic 创建；demo 需先存在 chat_session 与 user 记录
    chain = build_chain()
    cfg = {"configurable": {"session_id": SESSION_ID}}

    r1 = chain.invoke({"input": "你好，记住我叫小明"}, cfg)
    print("Q1:", r1.content)

    r2 = chain.invoke({"input": "我叫什么？"}, cfg)
    print("Q2:", r2.content)
