#!/usr/bin/env bash
# 根据 proto/*.proto 重新生成 app/grpc_generated/ 下的 Python 与 gRPC 桩代码。
# 用法（在任意目录）:
#   ./scripts/gen_grpc_python.sh
# 或:
#   bash private_chef_agent/scripts/gen_grpc_python.sh
set -euo pipefail

AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${AGENT_ROOT}"

if ! command -v uv >/dev/null 2>&1; then
  echo "需要 uv。安装: https://github.com/astral-sh/uv" >&2
  exit 1
fi

PROTO_DIR="${AGENT_ROOT}/proto"
OUT_DIR="${AGENT_ROOT}/app/grpc_generated"

mkdir -p "${OUT_DIR}"

echo "==> grpc_tools.protoc (python + grpc_python)"
echo "    -I ${PROTO_DIR}"
echo "    --python_out / --grpc_python_out -> ${OUT_DIR}"
# 等价命令（无 uv 时可在 venv 里直接执行下一行）:
# python -m grpc_tools.protoc -I proto --python_out=app/grpc_generated --grpc_python_out=app/grpc_generated proto/agent_user.proto
uv run python -m grpc_tools.protoc \
  -I "${PROTO_DIR}" \
  --python_out="${OUT_DIR}" \
  --grpc_python_out="${OUT_DIR}" \
  "${PROTO_DIR}/agent_user.proto"

GRPC_STUB="${OUT_DIR}/agent_user_pb2_grpc.py"
if [[ -f "${GRPC_STUB}" ]] && grep -q '^import agent_user_pb2 as agent__user__pb2' "${GRPC_STUB}"; then
  echo "==> 修正包内 import（生成器默认写成顶层 import，在 app.grpc_generated 包内会失败）"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  else
    sed -i 's/^import agent_user_pb2 as agent__user__pb2$/from . import agent_user_pb2 as agent__user__pb2/' "${GRPC_STUB}"
  fi
fi

echo "完成。输出: ${OUT_DIR}/agent_user_pb2.py ${OUT_DIR}/agent_user_pb2_grpc.py"
