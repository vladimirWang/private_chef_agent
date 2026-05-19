#!/bin/bash
# 启动 chat_history Streamlit 查看器
# 浏览器访问 http://127.0.0.1:8501

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

uv run streamlit run app/agents/chat_history_viewer.py \
  --server.address 127.0.0.1 \
  --server.port 8501
