import alibabacloud_oss_v2 as oss
from fastapi import APIRouter, HTTPException
from datetime import timedelta
import os
# 加载环境变量
from dotenv import load_dotenv
from app.models.schemas import ClothingUploadRequest

load_dotenv()
router = APIRouter()

@router.post("/clothing/upload")
async def upload_clothing(request: ClothingUploadRequest):
    return {"message": "success"}