#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

uv run python -m grpc_tools.protoc -I../private_chef_server/proto --python_out=./app/grpc_generated --grpc_python_out=./app/grpc_generated agent_user.proto

GRPC_STUB="${SCRIPT_DIR}/app/grpc_generated/agent_user_pb2_grpc.py"
if [[ -f "${GRPC_STUB}" ]] && grep -q '^import agent_user_pb2 as agent__user__pb2' "${GRPC_STUB}"; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  else
    sed -i 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  fi
fi
