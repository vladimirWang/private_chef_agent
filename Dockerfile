FROM python:3.13-slim

# 构建阶段避免 uv 等待交互；Python 无缓冲便于日志
ENV CI=1 \
    PYTHONUNBUFFERED=1

# 与根目录 docker-compose 的 volume ./private_chef_agent:/app 一致
WORKDIR /app

# gen_proto.sh 使用 -I../private_chef_server/proto（相对本目录的上级目录）
# build context 仅为 agent 目录时，proto 由 Compose 的 additional_contexts: server_proto 注入
COPY --from=server_proto / /private_chef_server/proto

# 使用 uv + uv.lock 做可复现安装
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . ./

RUN bash ./gen_proto.sh

CMD ["echo", "-----------------gen_proto.sh done-----------------"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8001

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
