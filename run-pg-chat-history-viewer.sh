#!/bin/bash
# Streamlit 查看 PostgreSQL agent_chat_messages
# 浏览器访问 http://127.0.0.1:8502

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"
export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

uv run --env-file .env.dev streamlit run app/agents/pg_chat_history_viewer.py \
  --server.address 127.0.0.1 \
  --server.port 8502
