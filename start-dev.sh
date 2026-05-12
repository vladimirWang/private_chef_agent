#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# gRPC 已由 app.main 在进程内启动（lifespan），此处只起 uvicorn
uv run --env-file .env.dev uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8001
