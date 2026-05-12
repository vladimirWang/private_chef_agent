#!/usr/bin/env bash
# 本机 agent 根目录（与截图中路径一致）；换机器时请改这一行。
# 若端口无监听：默认自动后台起 gRPC，测完退出脚本时会关掉该进程（除非已设置 NO_AUTO_GRPC=1）。
set -euo pipefail

ROOT="/Users/wangfernando/fullstack_workspace/private_chef/private_chef_agent"
PROTO_DIR="${ROOT}/proto"
ADDR="127.0.0.1:50052"
USER_ID="${1:-4}"

_host="${ADDR%:*}"
_port="${ADDR##*:}"

port_open() {
  python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('${_host}', int('${_port}'))); s.close()" 2>/dev/null
}

cleanup_grpc() {
  if [[ -n "${_GRPC_BG_PID:-}" ]] && kill -0 "${_GRPC_BG_PID}" 2>/dev/null; then
    kill "${_GRPC_BG_PID}" 2>/dev/null || true
    wait "${_GRPC_BG_PID}" 2>/dev/null || true
  fi
}

if ! command -v grpcurl >/dev/null 2>&1; then
  echo "未找到 grpcurl，请先: brew install grpcurl" >&2
  exit 1
fi

if [[ ! -f "${PROTO_DIR}/agent_user.proto" ]]; then
  echo "找不到 proto: ${PROTO_DIR}/agent_user.proto ，请检查 ROOT 是否写对。" >&2
  exit 1
fi

_GRPC_BG_PID=""
if ! port_open; then
  if [[ "${NO_AUTO_GRPC:-}" == "1" ]]; then
    echo "" >&2
    echo "错误: ${_host}:${_port} 没有服务在监听。" >&2
    echo "请执行: cd ${ROOT} && uv run python -m app.grpc_agent_user_server" >&2
    echo "或去掉 NO_AUTO_GRPC=1 后重试本脚本（将自动拉起 gRPC）。" >&2
    exit 1
  fi
  echo "端口 ${_port} 无监听，正在后台启动 gRPC（退出本脚本时会结束该进程）..." >&2
  pushd "${ROOT}" >/dev/null
  uv run python -m app.grpc_agent_user_server &
  _GRPC_BG_PID=$!
  popd >/dev/null
  trap cleanup_grpc EXIT INT TERM
  _ok=0
  for _ in {1..30}; do
    if port_open; then
      _ok=1
      break
    fi
    if ! kill -0 "${_GRPC_BG_PID}" 2>/dev/null; then
      echo "错误: gRPC 子进程已退出（常见原因: 端口被占用）。请检查: lsof -nP -iTCP:${_port} -sTCP:LISTEN" >&2
      exit 1
    fi
    sleep 0.2
  done
  if [[ "${_ok}" != "1" ]]; then
    echo "错误: 等待 gRPC 监听 ${_host}:${_port} 超时。" >&2
    exit 1
  fi
fi

echo "调用 ${ADDR} PingUser user_id=${USER_ID}"
grpcurl -plaintext -import-path "${PROTO_DIR}" -proto agent_user.proto \
  -max-time 15 \
  -d '{"user_id":'"${USER_ID}"'}' \
  ${ADDR} \
  privatechef.agent.AgentUserService/PingUser

echo "grpcurl 调用成功。"
