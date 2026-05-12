"""供 private_chef_server 调用的 gRPC：请求仅含 user_id，响应 message 为 ok。"""

import logging
import os
from concurrent import futures

import grpc

from app.common.logger import setup_logging
from app.grpc_generated import agent_user_pb2, agent_user_pb2_grpc

logger = logging.getLogger("personal_chief.grpc_agent_user")


class AgentUserServicer(agent_user_pb2_grpc.AgentUserServiceServicer):
    def PingUser(self, request, context):
        _ = request.user_id
        return agent_user_pb2.PingUserResponse(message="ok")


def _add_agent_user_servicer(servicer: AgentUserServicer, server: grpc.Server) -> None:
    """仅注册 generic handler；生成代码里的 add_registered_method_handlers 会导致部分客户端路由失败。"""
    rpc_method_handlers = {
        "PingUser": grpc.unary_unary_rpc_method_handler(
            servicer.PingUser,
            request_deserializer=agent_user_pb2.PingUserRequest.FromString,
            response_serializer=agent_user_pb2.PingUserResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "privatechef.agent.AgentUserService", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


def serve() -> None:
    setup_logging()
    port = os.environ.get("PRIVATE_CHEF_AGENT_USER_GRPC_PORT", "50052")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    _add_agent_user_servicer(AgentUserServicer(), server)
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info("AgentUserService gRPC listening on %s", listen_addr)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
