"""供 private_chef_server 调用的 gRPC：PingUser 按 question 走 RAG 流式返回。"""

import logging
import os
import threading
from concurrent import futures

import grpc

from app.agents.rag import RagService
from app.common.logger import setup_logging
from app.grpc_generated import agent_user_pb2, agent_user_pb2_grpc

logger = logging.getLogger("personal_chief.grpc_agent_user")


class AgentUserServicer(agent_user_pb2_grpc.AgentUserServiceServicer):
    def PingUser(self, request, context):
        uid = int(request.user_id)
        question = (request.question or "").strip()
        if not question:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "question 不能为空")

        session_config = {"configurable": {"session_id": f"user_{uid}"}}
        try:
            chain = RagService().chain
            it = chain.stream({"input": question}, session_config)
            for chunk in it:
                if not context.is_active():
                    return
                text = chunk if isinstance(chunk, str) else str(chunk)
                yield agent_user_pb2.PingUserChunk(chunk=text, done=False)
            yield agent_user_pb2.PingUserChunk(chunk="", done=True)
        except grpc.RpcError:
            raise
        except Exception as e:
            logger.exception("PingUser RAG 流失败")
            context.abort(grpc.StatusCode.INTERNAL, str(e))


def _add_agent_user_servicer(servicer: AgentUserServicer, server: grpc.Server) -> None:
    if not hasattr(agent_user_pb2, "PingUserChunk"):
        raise RuntimeError(
            "agent_user_pb2 缺少 PingUserChunk（proto 已改为流式）。"
            "请在 agent 根目录执行: ./scripts/gen_grpc_python.sh 后重启服务。"
        )
    rpc_method_handlers = {
        "PingUser": grpc.unary_stream_rpc_method_handler(
            servicer.PingUser,
            request_deserializer=agent_user_pb2.PingUserRequest.FromString,
            response_serializer=agent_user_pb2.PingUserChunk.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "privatechef.agent.AgentUserService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


def _build_agent_user_server() -> tuple[grpc.Server, str]:
    port = os.environ.get("PRIVATE_CHEF_AGENT_USER_GRPC_PORT", "50052")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    _add_agent_user_servicer(AgentUserServicer(), server)
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    return server, listen_addr


def start_agent_user_grpc_in_thread() -> grpc.Server:
    """在同进程内启动 gRPC；在后台线程中阻塞 wait_for_termination，返回 server 供 stop(grace)。"""
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
