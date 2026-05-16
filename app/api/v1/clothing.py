import asyncio
import json
import random
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.knowledge_base import KnowledgeBase, get_string_md5
from app.agents.rag import RagService
from app.models.schemas import ClothingConsultRequest, ClothingUploadRequest

load_dotenv()
router = APIRouter()


def basename_from_filepath(filepath: str) -> str:
    """从 URL 或本地路径得到文件名（含扩展名）。"""
    if filepath.startswith(("http://", "https://")):
        tail = urlparse(filepath).path.rstrip("/")
        name = tail.rsplit("/", 1)[-1] if tail else ""
    else:
        name = Path(filepath).name
    if not name:
        raise HTTPException(status_code=400, detail="无法从 filepath 解析文件名")
    return name


async def read_filepath_bytes(filepath: str) -> bytes:
    """支持 http(s) URL 或本地文件路径。"""
    if filepath.startswith(("http://", "https://")):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(filepath)
                r.raise_for_status()
                return r.content
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"拉取远程文件失败: {e}") from e
    path = Path(filepath)
    if not path.is_file():
        raise HTTPException(status_code=400, detail="本地文件不存在或不是文件")
    return path.read_bytes()


@router.post("/clothing/upload")
async def upload_clothing(request: ClothingUploadRequest):
    filepath = request.filepath
    filename = basename_from_filepath(filepath)
    raw = await read_filepath_bytes(filepath)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    # md5_value = get_string_md5(text)
    kb = KnowledgeBase()
    result = kb.upload_by_str(text, filename=filename)
    print("更新知识库结果: ", result)
    return JSONResponse({"message": "文件上传成功", "data": {"filename": filename}})


_STREAM_END = object()


async def _clothing_consult_sse(query: str, session_config: dict):
    """流式输出咨询结果；块与块之间随机等待 1～5 秒再推送，避免阻塞事件循环。"""
    chain = RagService().chain
    it = chain.stream({"input": query}, session_config)
    first = True
    while True:
        chunk = await asyncio.to_thread(next, it, _STREAM_END)
        if chunk is _STREAM_END:
            break
        text = chunk if isinstance(chunk, str) else str(chunk)
        if not first:
            await asyncio.sleep(random.uniform(1.0, 5.0))
        first = False
        line = json.dumps(text, ensure_ascii=False)
        yield f"data: {line}\n\n".encode("utf-8")
    yield b'data: {"done": true}\n\n'


@router.post("/clothing/consult")
async def search_clothing(request: ClothingConsultRequest):
    query = request.question
    session_config = {"configurable": {"session_id": "user01"}}
    return StreamingResponse(
        _clothing_consult_sse(query, session_config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
