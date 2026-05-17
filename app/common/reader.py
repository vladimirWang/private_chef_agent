import asyncio
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException


def basename_from_filepath(filepath: str) -> str:
    """从 URL 或本地路径得到文件名（含扩展名）。"""
    if filepath.startswith(("http://", "https://")):
        tail = urlparse(filepath).path.rstrip("/")
        name = tail.rsplit("/", 1)[-1] if tail else ""
    else:
        name = Path(filepath).name
    if not name:
        raise ValueError("无法从 filepath 解析文件名")
    return name


def read_filepath_bytes_sync(filepath: str) -> bytes:
    """支持 http(s) URL 或本地文件路径（同步，供 gRPC 等非 async 上下文使用）。"""
    if filepath.startswith(("http://", "https://")):
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(filepath)
                r.raise_for_status()
                return r.content
        except httpx.HTTPError as e:
            raise OSError(f"拉取远程文件失败: {e}") from e
    path = Path(filepath)
    if not path.is_file():
        raise ValueError("本地文件不存在或不是文件")
    return path.read_bytes()


async def read_filepath_bytes(filepath: str) -> bytes:
    try:
        return await asyncio.to_thread(read_filepath_bytes_sync, filepath)
    except OSError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e