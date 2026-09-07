"""AI 客户端：直连 DeepSeek 云端模型。

已移除本地 server/ 链路。GUI 各页面通过 fetch_prescribe / fetch_recognize /
fetch_chat 获取模型输出的**原始 Markdown 文本**，再由 worker 用 md_parser 归一
成结构化 dict 或富文本显示。

配置（供应商/模型/API Key）来自用户级 UserConfig（~/zy_rpa/config.json），
未配置时会抛 AIClientError 提示先在设置中添加模型。
"""
from __future__ import annotations

from .ai_prompts import (
    build_prescription_prompt,
    build_recognize_prompt,
    chat_messages_with_system,
)
from .config import Config
from .deepseek_client import DeepSeekClient, DeepSeekError
from .user_config import UserConfig


class AIClientError(Exception):
    """AI 调用失败（未配置/网络/模型报错）。"""


class AIClient:
    """对接 DeepSeek 模型的统一客户端。"""

    def __init__(self, user_cfg: UserConfig = None):
        # 每次调用时 load()，确保设置页新保存的 key/模型能被读取
        self._ucfg = user_cfg or UserConfig()

    # ---- 凭据 ----
    def _credentials(self) -> tuple[str, str]:
        self._ucfg.load()
        api_key = (self._ucfg.get("api_key") or "").strip()
        model = (self._ucfg.get("ai_model") or Config.DEFAULT_MODEL
                 or "deepseek-v4-flash").strip()
        if not api_key:
            raise AIClientError("尚未配置 AI 模型，请在「设置」中添加模型并填写 API Key")
        return model, api_key

    def _chat_text(self, messages: list, timeout: float) -> str:
        model, api_key = self._credentials()
        try:
            return DeepSeekClient(api_key).chat_completion(messages, model, timeout)
        except DeepSeekError as e:
            raise AIClientError(str(e))
        except Exception as e:                          # noqa: BLE001
            raise AIClientError(f"AI 调用失败：{e}")

    # ---- 开方/识别/对话（统一文本层入口）----
    def fetch_prescribe(self, data: dict, timeout: float = 180.0) -> str:
        """组装开方提示词并发给模型，返回原始 Markdown 文本。"""
        return self._chat_text(
            [{"role": "user", "content": build_prescription_prompt(data)}], timeout)

    def fetch_recognize(self, data: dict, timeout: float = 180.0) -> str:
        """组装识别提示词并发给模型，返回原始 Markdown 文本。"""
        return self._chat_text(
            [{"role": "user", "content": build_recognize_prompt(data)}], timeout)

    def fetch_chat(self, messages: list, timeout: float = 180.0) -> str:
        """把系统提示词拼到最前并发送完整对话历史，返回原始 Markdown 文本。"""
        return self._chat_text(chat_messages_with_system(messages), timeout)

    # ---- 供设置页/向导校验 API Key ----
    def verify(self, api_key: str) -> tuple[bool, str]:
        """校验给定 API Key：成功 (True, '')，失败 (False, 错误信息)。"""
        try:
            return DeepSeekClient(api_key.strip()).verify_api_key()
        except Exception as e:                          # noqa: BLE001
            return False, str(e)