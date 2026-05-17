#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

PROTO_DIR="${SCRIPT_DIR}/proto"
OUT_DIR="${SCRIPT_DIR}/app/grpc_generated"

mkdir -p "${OUT_DIR}"

proto_files=("${PROTO_DIR}"/*.proto)
if [[ ! -e "${proto_files[0]}" ]]; then
  echo "未找到 proto 文件: ${PROTO_DIR}/*.proto" >&2
  exit 1
fi

# Docker 镜像里上一步已 uv sync，优先用 .venv 里的 Python，避免 RUN 阶段再经 uv run 可能长时间解析/锁等待
if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
  "${SCRIPT_DIR}/.venv/bin/python" -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    "${proto_files[@]}"
else
  uv run python -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    "${proto_files[@]}"
fi

for grpc_stub in "${OUT_DIR}"/*_pb2_grpc.py; do
  [[ -f "${grpc_stub}" ]] || continue
  if grep -qE '^import [a-zA-Z0-9_]+_pb2 as ' "${grpc_stub}"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
      sed -i '' -E 's/^import ([a-zA-Z0-9_]+_pb2 as .+)$/from . import \1/' "${grpc_stub}"
    else
      sed -i -E 's/^import ([a-zA-Z0-9_]+_pb2 as .+)$/from . import \1/' "${grpc_stub}"
    fi
  fi
done

echo "-----------------gen_proto.sh done-----------------"
exit 0
