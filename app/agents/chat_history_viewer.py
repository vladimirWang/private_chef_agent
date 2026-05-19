"""
从本地 ./chat_history 读取会话并用 Streamlit 展示。

运行：cd private_chef_agent && ./run-chat-history-viewer.sh
"""

import json
from pathlib import Path

import streamlit as st
from langchain_core.messages import messages_from_dict

# private_chef_agent/chat_history（与 file_history_store 默认路径一致）
CHAT_DIR = Path(__file__).resolve().parents[2] / "chat_history"


print("debug CHAT_DIR: ", CHAT_DIR, type(CHAT_DIR))
def list_sessions() -> list[str]:
    if not CHAT_DIR.is_dir():
        return []
    l1 = [p.name for p in CHAT_DIR.iterdir() if p.is_file()]
    # return sorted(l1)
    return l1


def load_raw(session_id: str) -> list[dict]:
    path = CHAT_DIR / session_id
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _role(msg) -> str:
    if msg.type == "human":
        return "user"
    if msg.type == "ai":
        return "assistant"
    return "assistant"


st.set_page_config(page_title="Chat History", layout="wide")
st.title("本地 chat_history 查看")

st.caption(f"目录：`{CHAT_DIR}`")

sessions = list_sessions()

print("debug sessions: ", type(sessions), len(sessions))
if not sessions:
    st.warning("暂无会话文件。先通过 RAG 等写入 chat_history 后再查看。")
    st.stop()

session_id = st.selectbox("会话 ID", sessions)
raw = load_raw(session_id)

with st.expander("原始 JSON", expanded=False):
    st.json(raw)

messages = messages_from_dict(raw)
if not messages:
    st.info("该会话尚无消息。")
    st.stop()

for msg in messages:
    with st.chat_message(_role(msg)):
        st.markdown(msg.content)
