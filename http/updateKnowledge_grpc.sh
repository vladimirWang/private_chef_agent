#!/usr/bin/env bash
# 测试 KnowledgeBaseService/UpdateKnowledge（需 agent 已启动且 gRPC 在 50052 监听）
set -euo pipefail

FILEPATH="${1:-https://example.com/example.txt}"

# if ! command -v grpcurl >/dev/null 2>&1; then
#   echo "未找到 grpcurl。macOS: brew install grpcurl" >&2
#   exit 1
# fi

grpcurl -plaintext \
  -import-path "../proto" \
  -proto agent_user.proto \
  -d "{\"filepath\": \"${FILEPATH}\"}" \
  127.0.0.1:50052 \
  agent.KnowledgeBaseService/UpdateKnowledge
