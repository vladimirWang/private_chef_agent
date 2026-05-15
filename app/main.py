import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import chat
from app.api.v1 import oss
from app.common.logger import setup_logging
from app.api.v1 import clothing
from app.grpc_agent_user_server import serve

# 初始化日志配置
setup_logging()

_log = logging.getLogger("personal_chief")


def _agent_user_grpc_disabled() -> bool:
    v = os.environ.get("DISABLE_AGENT_USER_GRPC", "").strip().lower()
    return v in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = None
    if not _agent_user_grpc_disabled():
        try:
            from app.grpc_agent_user_server import start_agent_user_grpc_in_thread

            grpc_server = start_agent_user_grpc_in_thread()
        except Exception:
            _log.exception(
                "AgentUser gRPC 启动失败（常见原因: 端口被占用）。"
                "可设环境变量 DISABLE_AGENT_USER_GRPC=1 仅起 HTTP，或单独运行 python -m app.grpc_agent_user_server"
            )
            raise
    yield
    if grpc_server is not None:
        grpc_server.stop(grace=5)


app = FastAPI(
    title="Personal Chief API",
    description="私厨",
    version="0.1.0",
    lifespan=lifespan,
)

# 健康检查（供 docker healthcheck / 负载均衡探活）
@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}

# 1. 配置跨域资源共享 (CORS)
# 插件开发中，由于请求来自浏览器扩展环境，必须正确配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定插件的 ID 或具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2.挂载路由
app.include_router(chat.router, prefix="/api/v1", tags=["对话"])
app.include_router(oss.router, prefix="/api/v1", tags=["申请上传签名url"])
app.include_router(clothing.router, prefix="/api/v1", tags=["衣物上传"])

# 3.挂载前端资源
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# 前端 fallback 路由 - 只处理非 API 请求
@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    # 排除 API 路径
    if path.startswith("api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not Found"}, status_code=404)
    # 如果请求的是静态文件，直接返回
    file_path = os.path.join(static_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # 否则返回 index.html（SPA fallback）
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "你的独家私厨上线了~", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    serve()
    # 启动命令：python -m app.main
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
