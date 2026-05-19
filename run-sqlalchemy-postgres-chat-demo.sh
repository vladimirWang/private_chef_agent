#!/bin/bash
# 启动 sqlalchemy_postgres_history_store，环境变量来自 .env.dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

uv run --env-file .env.dev python -m app.agents.sqlalchemy_postgres_history_store
