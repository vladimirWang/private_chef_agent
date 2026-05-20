from pathlib import Path

from langchain_core.messages import messages_from_dict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.sqlalchemy_history_store import AgentChatMessage, engine

def list_sessions() -> list[str]:
    with Session(engine) as db:
        return list(
            db.scalars(
                select(AgentChatMessage.session_id)
                .distinct()
                .order_by(AgentChatMessage.session_id)
            ).all()
        )


def load_rows(session_id: str) -> list[AgentChatMessage]:
    with Session(engine) as db:
        return list(
            db.scalars(
                select(AgentChatMessage)
                .where(AgentChatMessage.session_id == session_id)
                .order_by(AgentChatMessage.created_at, AgentChatMessage.id)
            ).all()
        )


def get_role(msg) -> str:
    if msg.type == "human":
        return "user"
    if msg.type == "ai":
        return "assistant"
    return "assistant"