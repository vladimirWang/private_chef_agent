#!/bin/bash

set -euo pipefail

# 生产启动（无热重载，对外监听）
uv run uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --env-file .env.prod