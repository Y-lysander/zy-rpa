"""DeepSeek 官方 API 客户端（urllib 实现，不引入第三方依赖）。

提供两件事：
- verify_api_key：调用 /user/balance 校验 API Key 有效性（沿用 TokenPeek 的做法）。
- chat_completion：调用 /chat/completions 完成对话（OpenAI 兼容协议），返回正文文本。

网络/HTTP 错误统一抛 DeepSeekError，由上层转为 AIClientError。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

API_BASE = "https://api.deepseek.com"
BALANCE_PATH = "/user/balance"
CHAT_PATH = "/chat/completions"
DEFAULT_TIMEOUT = 120.0
VERIFY_TIMEOUT = 8.0


class DeepSeekError(Exception):
    """DeepSeek API 调用失败。"""


def _request(url: str, headers: dict, method: str, body: dict | None,
             timeout: float) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:                                   # noqa: BLE001
            pass
        if e.code == 401:
            raise DeepSeekError("API Key 无效（401）")
        if e.code == 402:
            raise DeepSeekError("余额不足或配额已用尽（402）")
        if e.code == 429:
            raise DeepSeekError("请求过于频繁，请稍后再试（429）")
        raise DeepSeekError(f"DeepSeek API 错误 HTTP {e.code}: {detail[:200]}")
    except urllib.error.URLError as e:
        raise DeepSeekError(f"无法连接 DeepSeek API：{e.reason}")
    except Exception as e:                                  # noqa: BLE001
        raise DeepSeekError(f"DeepSeek 请求异常：{e}")


class DeepSeekClient:
    """DeepSeek API 客户端。"""

    def __init__(self, api_key: str, base: str = API_BASE,
                 timeout: float = DEFAULT_TIMEOUT):
        self._key = api_key
        self._base = base.rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

    def verify_api_key(self, timeout: float = VERIFY_TIMEOUT) -> tuple[bool, str]:
        """校验 API Key：成功返回 (True, '')，失败返回 (False, 错误信息)。"""
        try:
            _request(f"{self._base}{BALANCE_PATH}", self._headers(),
                     "GET", None, timeout)
            return True, ""
        except DeepSeekError as e:
            return False, str(e)

    def chat_completion(self, messages: list, model: str,
                        timeout: float | None = None) -> str:
        """发送消息列表，返回模型正文（纯文本）。"""
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        data = _request(f"{self._base}{CHAT_PATH}", self._headers(),
                        "POST", body, timeout or self._timeout)
        try:
            content = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            content = ""
        if not content.strip():
            if data.get("choices"):
                finish = data["choices"][0].get("finish_reason")
                content = finish or "（模型未返回内容）"
            else:
                content = "（模型未返回内容）"
        return content.strip()