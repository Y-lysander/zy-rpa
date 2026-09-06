"""虚拟 AI 服务启动入口（模拟远程 AI 模型，本地运行）。

两种启动方式均可：
    python -m server.run_server
    python server/run_server.py
支持 --host / --port 参数，默认 127.0.0.1:8123。
"""
from __future__ import annotations

import argparse

import uvicorn

try:
    from .app import DEFAULT_HOST, DEFAULT_PORT, app
except ImportError:            # 直接以脚本方式运行时的回退导入
    from app import DEFAULT_HOST, DEFAULT_PORT, app


def main() -> None:
    parser = argparse.ArgumentParser(description="启动虚拟 AI 服务（模拟远程 AI 模型）")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", reload=False)


if __name__ == "__main__":
    main()