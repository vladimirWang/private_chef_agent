from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse

from app.agents.private_chef import clear_messages, get_messages, search_recipes
from app.agents.rag import RagService
from app.models.schemas import ChatRequest

router = APIRouter()


@router.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    chain = RagService().chain

    res = chain.stream({input: "我身高176，体重150斤，尺码推荐"})
    print("chain: ", res)
    return JSONResponse({"message": "ok"})
    # return StreamingResponse(
    #     search_recipes(request.message, request.image_url, request.thread_id),
    #     media_type="text/event-stream"
    # )


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


@router.post("/chat/fileupload")
async def fileUpload(thread_id: str):
    # """清空历史消息（mock）"""
    # if not thread_id:
    #     raise HTTPException(status_code=400, detail="thread_id 不能为空")

    # await clear_messages(thread_id)

    # return JSONResponse(content={"ok": True})
    # 清空历史消息
    clear_messages(thread_id)
    return {"success": True}
