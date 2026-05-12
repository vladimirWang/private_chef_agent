#!/usr/bin/env bash
# 使用 grpcurl 验证 AgentUser gRPC（需先启动 agent 端服务）。
#
# 用法:
#   ./scripts/verify_agent_user_grpc.sh [user_id]
# 环境变量:
#   PRIVATE_CHEF_AGENT_USER_GRPC_ADDR  默认 127.0.0.1:50052
#
# 依赖: brew install grpcurl
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDR="${PRIVATE_CHEF_AGENT_USER_GRPC_ADDR:-127.0.0.1:50052}"
USER_ID="${1:-1}"

if ! command -v grpcurl >/dev/null 2>&1; then
  echo "未找到 grpcurl。macOS: brew install grpcurl" >&2
  exit 1
fi

# 常见踩坑：同一端口被多个旧 python 进程监听，连接可能落到未注册路由的实例，返回 UNIMPLEMENTED / Method not found
if [[ "${ADDR}" =~ ^[0-9.]+:([0-9]+)$ ]]; then
  _port="${BASH_REMATCH[1]}"
  _n="$(lsof -nP -iTCP:"${_port}" -sTCP:LISTEN 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')"
  if [[ "${_n}" =~ ^[0-9]+$ ]] && [[ "${_n}" -gt 1 ]]; then
    echo "警告: 端口 ${_port} 上存在 ${_n} 个监听进程，可能导致 Method not found。请检查: lsof -nP -iTCP:${_port} -sTCP:LISTEN" >&2
  fi
fi

echo "调用 ${ADDR} privatechef.agent.AgentUserService/PingUser user_id=${USER_ID}"
# 与 grpc_demo/test_grpc.sh 一致：-d 单引号 JSON；地址裸参数
grpcurl -plaintext -import-path "${ROOT}/proto" -proto agent_user.proto \
  -max-time 15 \
  -d '{"user_id":'"${USER_ID}"'}' \
  ${ADDR} \
  privatechef.agent.AgentUserService/PingUser

echo "grpcurl 调用成功。"
