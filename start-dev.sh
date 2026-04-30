#!/bin/bash

set -euo pipefail

# # 开发启动（自动热重载）
# uv run uvicorn app.main:app \
#   --reload \
#   --host 127.0.0.1 \
#   --port 8001 \
#   --env-file .env.dev
# 开发启动（自动热重载）
uv run --env-file .env.dev uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8001