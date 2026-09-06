"""虚拟 AI 服务客户端与自动拉起。

GUI 经 HTTP 调用本地虚拟服务（server/）。未接入真实云端模型，
接口层保持简单：health 探活 + prescribe 开方 + recognize 识别。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

from .config import Config


class AIClientError(Exception):
    """虚拟 AI 服务调用失败。"""


class VirtualAIClient:
    """虚拟 AI 服务 HTTP 客户端。"""

    def __init__(self, host: str = Config.AI_HOST, port: int = Config.AI_PORT):
        self.base = f"http://{host}:{port}"

    # ---- 探活 ----
    def health(self, timeout: float = 2.0):
        try:
            with urllib.request.urlopen(f"{self.base}/health", timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    # ---- 开方 ----
    def prescribe(self, data: dict, timeout: float = 120.0) -> dict:
        return self._post("/api/prescribe", data, timeout)

    # ---- 识别 ----
    def recognize(self, data: dict, timeout: float = 120.0) -> dict:
        return self._post("/api/recognize", data, timeout)

    def _post(self, path: str, data: dict, timeout: float) -> dict:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise AIClientError(f"服务返回错误 HTTP {e.code}: {e.read().decode('utf-8')}")
        except Exception as e:
            raise AIClientError(f"无法连接服务：{e}")

    # ---- 自动拉起服务 ----
    def ensure_running(self, timeout: float = 20.0) -> bool:
        """确保本地服务可连接；未就绪则后台拉起 server/run_server.py 并等待。"""
        if self.health():
            return True
        server_py = str(Config.ROOT / "server" / "run_server.py")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            subprocess.Popen(
                [sys.executable, server_py],
                cwd=str(Config.ROOT),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=flags, close_fds=True,
            )
        except Exception:
            pass
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.health(timeout=1.0):
                return True
            time.sleep(0.4)
        return False