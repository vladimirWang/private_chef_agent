import alibabacloud_oss_v2 as oss
from fastapi import APIRouter, HTTPException
from datetime import timedelta
import os
# 加载环境变量
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

# OSS 域名配置
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
OSS_BUCKET = os.getenv("OSS_BUCKET")

_client: oss.Client | None = None


def _get_oss_client() -> oss.Client:
    """
    延迟初始化 OSS Client，避免因生产环境缺少凭证导致应用启动失败。
    """
    global _client
    if _client is not None:
        return _client

    # 从环境变量中加载凭证信息，用于身份验证
    try:
        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OSS 凭证未配置或无效：{e}",
        )

    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider
    cfg.region = os.getenv("OSS_REGION", "cn-beijing")

    _client = oss.Client(cfg)
    return _client


@router.get("/oss/presign")
def chat_endpoint(filename: str):
    if not OSS_BUCKET:
        raise HTTPException(status_code=500, detail="OSS_BUCKET 未配置")

    # 根据文件扩展名判断 Content-Type
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    content_type = content_type_map.get(ext, "application/octet-stream")

    client = _get_oss_client()
    pre_result = client.presign(oss.PutObjectRequest(
        bucket=OSS_BUCKET,
        key=filename,
        content_type=content_type,
    ), expires=timedelta(seconds=3600))

    # 返回上传 URL 和可访问的图片路径
    return {
        "uploadUrl": pre_result.url.strip('"'),
        "contentType": content_type,
        "accessUrl": f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{filename}"
    }
