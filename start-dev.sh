#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 与 scripts/2.sh 默认地址一致：供 server / grpcurl 调用的 AgentUser gRPC
uv run python -m app.grpc_agent_user_server &
GRPC_PID=$!
trap 'kill "${GRPC_PID}" 2>/dev/null || true' EXIT INT TERM
sleep 0.4
if ! kill -0 "${GRPC_PID}" 2>/dev/null; then
  echo "警告: AgentUser gRPC 子进程已退出（常见原因: 50052 已被占用）。scripts/2.sh 仍会失败，请检查: lsof -nP -iTCP:50052 -sTCP:LISTEN" >&2
fi

# 开发启动（自动热重载）
uv run --env-file .env.dev uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8001