from langchain_core.messages import messages_from_dict
from sqlalchemy import delete, select
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
                .where(
                    AgentChatMessage.session_id == session_id,
                    AgentChatMessage.deleted_at.is_(None),
                )
                .order_by(AgentChatMessage.created_at, AgentChatMessage.id)
            ).all()
        )


def get_role(msg) -> str:
    if msg.type == "human":
        return "user"
    if msg.type == "ai":
        return "assistant"
    return "assistant"


def get_messages(session_id: str) -> list[dict[str, str]]:
    """HTTP 兼容：将会话历史转为 role/content 列表。"""
    rows = load_rows(session_id)
    result: list[dict[str, str]] = []
    for row in rows:
        msgs = messages_from_dict([row.payload])
        if not msgs:
            continue
        msg = msgs[0]
        content = msg.content or ""
        if not content:
            continue
        result.append({"role": get_role(msg), "content": content})
    return result


def clear_messages(session_id: str) -> None:
    with Session(engine) as db:
        db.execute(
            delete(AgentChatMessage).where(AgentChatMessage.session_id == session_id)
        )
        db.commit()