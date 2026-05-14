#!/bin/bash

uv run python -m grpc_tools.protoc -I../private_chef_server/proto --python_out=./app/grpc_generated --grpc_python_out=./app/grpc_generated agent_user.proto
