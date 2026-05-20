"""供 private_chef_server 调用的 gRPC：PingUser 按 question 走 RAG 流式返回。"""

import ast
import logging
import os
import threading
from concurrent import futures

import grpc

from app.agents.rag import RagService
from app.common.logger import setup_logging
from app.grpc_generated import agent_user_pb2, agent_user_pb2_grpc
from app.agents.knowledge_base import KnowledgeBase
from app.common.reader import basename_from_filepath, read_filepath_bytes_sync
from app.agents.pg_history_helper import get_role, load_rows
from langchain_core.messages import messages_from_dict

logger = logging.getLogger("personal_chief.grpc_agent_user")

class AgentUserServicer(agent_user_pb2_grpc.ChatServiceServicer):
    def LoadChatHistory(self, request, context):
        session_id = request.session_id
        logger.info("-----Received LoadChatHistory request with session_id: %s", session_id)
        if not session_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id 不能为空")
        rows = load_rows(session_id)
        proto_messages = []
        messages = messages_from_dict([r.payload for r in rows])

        for row, msg in zip(rows, messages):
            # created_ms = 1000
            if row.created_at is not None:
                created_ms = int(row.created_at.timestamp() * 1000)
            proto_messages.append(
                agent_user_pb2.ChatHistoryMessage(
                    role=get_role(msg),
                    content=msg.content,
                    id=row.id,
                    created_at_ms=created_ms,
                )
            )
            # created_at_ms = row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else ""
            
            # print("for loop msg: ", type(msg), msg.content, label)
            # with st.chat_message(get_role(msg)):
            #     if label:
            #         st.caption(f"id={row.id} · {label}")
            #     st.markdown(msg.content)

        # print("debug l2: ", type(l2), l2)
        # for row in rows:
        #     print("debug row: ", type(row.payload))
        #     msgs = messages_from_dict([row.payload])
        #     # # 一行 DB 记录 = 一条对话消息
        #     # msg = messages_from_dict([row.payload])[0]
        #     # content = msg.content or ""
        #     # if not content:
        #     #     continue
        #     # created_ms = 0
        #     # if row.created_at is not None:
        #     #     created_ms = int(row.created_at.timestamp() * 1000)
        #     # proto_messages.append(
        #     #     agent_user_pb2.ChatHistoryMessage(
        #     #         role=get_role(msg),       # human→user, ai→assistant
        #     #         content=content,
        #     #         id=row.id,
        #     #         created_at_ms=created_ms,
        #     #     )
        #     # )
        return agent_user_pb2.LoadChatHistoryResp(messages=proto_messages)

    def UpdateKnowledge(self, request, context):
        filepath = request.filepath
        logger.info("-----Received UpdateKnowledge request with filepath: %s", filepath)
        if not filepath:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "filepath 不能为空")

        try:
            raw = read_filepath_bytes_sync(filepath)
            logger.info(
                "UpdateKnowledge Read %d bytes from filepath, preview: %r",
                len(raw),
                raw[:100],
            )
            # content_bytes = ast.literal_eval(raw)
            # decoded_content = content_bytes.decode('utf-8')
            # logger.info("UpdateKnowledge complete content: %s", decoded_content)
            text = raw.decode("utf-8", errors="replace")
            filename = basename_from_filepath(filepath)
            msg = KnowledgeBase().upload_by_str(text, filename=filename)
            logger.info("UpdateKnowledge result: %s", msg)
            return agent_user_pb2.UpdateKnowledgeResp(message=msg or "更新知识成功")
        except (OSError, ValueError) as e:
            logger.warning("UpdateKnowledge invalid filepath: %s", e)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception:
            logger.exception("Failed to update knowledge from filepath: %s", filepath)
            context.abort(grpc.StatusCode.INTERNAL, "更新知识库失败")
            
    def Consult(self, request, context):
        uid = int(request.user_id)
        question = (request.question or "").strip()
        session_id = (request.session_id or "").strip()
        if not question:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "question 不能为空")
        if not session_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "session_id 不能为空")

        session_config = {"configurable": {"session_id": session_id}}
        logger.info(
            "-----Received Consult request user_id=%s session_id=%s question=%s",
            uid,
            session_id,
            question,
        )
        try:
            chain = RagService().chain
            it = chain.stream({"input": question}, session_config)
            for chunk in it:
                if not context.is_active():
                    return
                text = chunk if isinstance(chunk, str) else str(chunk)
                yield agent_user_pb2.ConsultResp(chunk=text, done=False)
            yield agent_user_pb2.ConsultResp(chunk="", done=True)
        except grpc.RpcError:
            raise
        except Exception as e:
            logger.exception("consult RAG 流失败")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

def _build_agent_user_server() -> tuple[grpc.Server, str]:
    port = os.environ.get("PRIVATE_CHEF_AGENT_USER_GRPC_PORT", "50052")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    # _add_agent_user_servicer(AgentUserServicer(), server)
    agent_user_pb2_grpc.add_ChatServiceServicer_to_server(AgentUserServicer(), server)
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    return server, listen_addr


def start_agent_user_grpc_in_thread() -> grpc.Server:
    """在同进程内启动 gRPC；在后台线程里 wait_for_termination，主线程立即返回供 uvicorn lifespan yield。"""
    server, listen_addr = _build_agent_user_server()
    server.start()
    logger.info("AgentUserService gRPC listening on %s", listen_addr)
    threading.Thread(
        target=server.wait_for_termination,
        name="grpc-AgentUser",
        daemon=True,
    ).start()
    return server


def serve() -> None:
    setup_logging()
    server, listen_addr = _build_agent_user_server()
    server.start()
    logger.info("AgentUserService gRPC listening on %s", listen_addr)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
