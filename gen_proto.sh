#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Docker 镜像里上一步已 uv sync，优先用 .venv 里的 Python，避免 RUN 阶段再经 uv run 可能长时间解析/锁等待
if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
  "${SCRIPT_DIR}/.venv/bin/python" -m grpc_tools.protoc -I../private_chef_server/proto --python_out=./app/grpc_generated --grpc_python_out=./app/grpc_generated agent_user.proto
else
  uv run python -m grpc_tools.protoc -I../private_chef_server/proto --python_out=./app/grpc_generated --grpc_python_out=./app/grpc_generated agent_user.proto
fi

GRPC_STUB="${SCRIPT_DIR}/app/grpc_generated/agent_user_pb2_grpc.py"
if [[ -f "${GRPC_STUB}" ]] && grep -q '^import agent_user_pb2 as agent__user__pb2' "${GRPC_STUB}"; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  else
    sed -i 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  fi
fi

# Bash 脚本执行完毕即退出；无 Node 的 process.exit。显式 exit 仅作语义说明。
exit 0
