#!/bin/bash
# 启动 postgres_chat_demo，环境变量来自 .env.dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

uv run --env-file .env.dev python -m app.agents.postgres_history_store
