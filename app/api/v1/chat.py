from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.private_chef import get_messages, clear_messages, search_recipes
from app.models.schemas import ChatRequest

router = APIRouter()


@router.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        search_recipes(request.message, request.image_url, request.thread_id),
        media_type="text/event-stream"
    )


@router.get("/chat/messages")
async def get_chat_messages(thread_id: str):
    # """获取历史消息（mock）"""
    # if not thread_id:
    #     raise HTTPException(status_code=400, detail="thread_id 不能为空")

    # messages = await get_messages(thread_id)

    # return JSONResponse(content={"messages": messages})
    messages = get_messages(thread_id)
    return {"messages": messages}


@router.delete("/chat/messages")
async def clear_chat_messages(thread_id: str):
    # """清空历史消息（mock）"""
    # if not thread_id:
    #     raise HTTPException(status_code=400, detail="thread_id 不能为空")

    # await clear_messages(thread_id)

    # return JSONResponse(content={"ok": True})
    # 清空历史消息
    clear_messages(thread_id)
    return {"success": True}