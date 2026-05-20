"""
从 PostgreSQL agent_chat_messages 表读取会话并用 Streamlit 展示。

运行：cd private_chef_agent && ./run-pg-chat-history-viewer.sh
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from langchain_core.messages import messages_from_dict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.sqlalchemy_history_store import AgentChatMessage, engine
from app.agents.pg_history_helper import list_sessions, load_rows, get_role


st.set_page_config(page_title="PG Chat History", layout="wide")
st.title("PostgreSQL 对话历史")

if not engine.url.database:
    st.error("未配置 SQLALCHEMY_DATABASE_URL，请在 .env.dev 中设置。")
    st.stop()

st.caption(f"数据库：`{engine.url.render_as_string(hide_password=True)}` · 表：`agent_chat_messages`")

try:
    sessions = list_sessions()
except Exception as e:
    st.error(f"连接数据库失败：{e}")
    st.stop()

if not sessions:
    st.warning("表中暂无会话。先运行 postgres / sqlalchemy 对话 demo 写入数据。")
    st.stop()

session_id = st.selectbox("会话 ID", sessions)
rows = load_rows(session_id)

with st.expander("原始 payload（按行）", expanded=False):
    st.json([{"id": r.id, "created_at": str(r.created_at), "payload": r.payload} for r in rows])

messages = messages_from_dict([r.payload for r in rows])
if not messages:
    st.info("该会话尚无消息。")
    st.stop()

for row, msg in zip(rows, messages):
    label = row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else ""
    print("for loop msg: ", type(msg), msg.content, label)
    with st.chat_message(get_role(msg)):
        if label:
            st.caption(f"id={row.id} · {label}")
        st.markdown(msg.content)
