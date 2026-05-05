import asyncio
import json
from pathlib import Path

from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os
from langchain.agents import create_agent
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from app.common.logger import logger

load_dotenv()

# 重要：gRPC/HTTP 的 Get/Clear 等非流式接口不应因为外部模型配置缺失而启动失败。
# 因此把 model/agent 的初始化改为延迟执行（仅在 StreamChat 时才初始化）。
_agent = None
_tavily = None

# 初始化 checkpointer：路径相对项目根目录，不依赖当前工作目录
_db_path = Path(__file__).resolve().parents[2] / "db" / "private_chef.db"
_db_path.parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(str(_db_path), check_same_thread=False)
checkpointer= SqliteSaver(connection)
checkpointer.setup()

def _get_tavily() -> TavilySearch:
    global _tavily
    if _tavily is None:
        _tavily = TavilySearch(
            max_results=5,
            topic="general",
        )
    return _tavily

@tool
def web_search(query: str):
    """根据关键词搜索互联网"""
    return _get_tavily().invoke(query)

system_prompt="""
你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：
1.识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量，整理出一份 “当前可用食材清单”。
2.智能食谱检索：优先调用 web_search 工具，以 “可用食材清单” 为核心关键词，查找可行菜谱。
3.多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分排序，制作简单且营养丰富的排名靠前。
4.结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，要包含食谱信息、得分、推荐理由、食谱的参考图片，帮助用户快速做出决策。

请严格按照流程，优先调用 web_search 工具搜索食谱，搜索不到的情况下才能自己发挥。
"""
def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    model = init_chat_model(
        model="qwen3.5-plus",
        model_provider="openai",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        streaming=True,
    )

    _agent = create_agent(
        model=model,
        tools=[web_search],
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
    return _agent

async def sse_chars(query: str):
    """按字符模拟 SSE 流式输出，与前端 fetch-event-source 解析的 data: JSON 一致。"""
    for ch in query:
        line = json.dumps(ch, ensure_ascii=False)
        yield f"data: {line}\n\n".encode("utf-8")
        await asyncio.sleep(1)
    yield b'data: {"done": true}\n\n'


async def search_recipes(prompt: str, image: str, thread_id: str):
    logger.info(f"[用户]: {prompt}, image: {image}, thread_id: {thread_id}")
    try:
        agent = _get_agent()
        # 判断是否有图片
        if not image or image.strip() == "":
            logger.info(f"没有图片，直接调用agent")
            message = HumanMessage(content=prompt)
        else:
            logger.info(f"有图片，调用agent")
            message=HumanMessage(content=[
                {"type": "image", "url": image},
                {"type": "text", "text": prompt}
            ])
        # 流式调用 agent
        for chunk, metadata in agent.stream(
            {"messages": [message]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages"
        ):
            logger.info(f"chunk.content: {chunk.content}, metadata: {metadata}")
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content
        # async for chunk in sse_chars(prompt):
        #     yield chunk
    except Exception as e:
        logger.error(f"\n[错误]: {str(e)}")
        err = json.dumps(
            {"error": "信息检索失败, 试试着手动输入食物列表"},
            ensure_ascii=False,
        )
        yield f"data: {err}\n\n".encode("utf-8")
        yield b'data: {"done": true}\n\n'


def clear_messages(thread_id: str):
    logger.info(f"清空历史消息, thread_id: {thread_id}")
    checkpointer.delete_thread(thread_id)

def get_messages(thread_id: str) -> list[dict[str, str]]:
    """获取会话历史"""
    """根据thread_id查询checkpoint"""
    cp = checkpointer.get({"configurable": {"thread_id": thread_id}})
    if not cp:
        return []
    """安全获取messages"""
    channel_values = cp.get("channel_values")
    if not channel_values:
        return []
    messages = channel_values.get("messages", [])
    if not messages:
        return []
    
    # 转换消息格式
    result = []
    for msg in messages:
        if not msg.content:
            continue
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
    return result;
