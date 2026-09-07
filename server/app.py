"""虚拟 AI 服务 —— FastAPI 入口（本地模拟，不接真实云端模型）。

接口：
    GET  /health            健康探活（GUI 用于检测服务是否已启动）
    POST /api/prescribe     药方开方（单次对话，直接给出药方，不询问）
    POST /api/recognize     药方识别（逐味分析药效，附配伍与煎服建议）
    POST /api/chat          AI 助手对话（携带完整历史消息，返回一条回复）

启动：
    python -m server.run
或：
    python -m uvicorn server.app:app --port 8123
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from . import mock_ai
except ImportError:            # 以脚本方式直接运行时，无父包则回退绝对导入
    import mock_ai

app = FastAPI(title="虚拟中药AI服务", version="1.0.0")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8123


class PrescribeRequest(BaseModel):
    symptoms: str = ""        # 患者主诉/症状（必填）
    history: str = ""         # 现病史
    current_meds: str = ""    # 当前用药
    age_gender: str = ""      # 年龄/性别
    constitution: str = ""    # 体质
    allergies: str = ""       # 过敏史
    tongue_pulse: str = ""    # 舌象脉象
    menstruation: str = ""    # 经带情况
    lifestyle: str = ""       # 生活习惯
    decoct: bool = False      # 是否代煎


class PrescribeResponse(BaseModel):
    prescription_name: str
    principle: str
    herbs: list[dict]
    dosage_count: str
    decoction: str
    contraindications: str
    modifications: str
    warnings: str
    model: str


class RecognizeRequest(BaseModel):
    herbs: list[dict] = []      # [{"name", "dose", "unit"}]
    full_text: str = ""         # 整方文本（可选）


class RecognizeResponse(BaseModel):
    herbs: list[dict]
    interaction: str
    decoction: str
    warnings: str
    model: str


class ChatMessage(BaseModel):
    role: str = "user"        # user | assistant
    content: str = ""


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = []   # 完整对话历史（不含系统提示词）


class ChatResponse(BaseModel):
    reply: str
    model: str


@app.get("/health")
def health():
    return {"status": "ok", "model": mock_ai.MODEL_NAME}


@app.post("/api/prescribe", response_model=PrescribeResponse)
def prescribe(req: PrescribeRequest):
    """虚拟开方：单次对话，每次独立，直接给出药方。"""
    data = req.model_dump()
    return mock_ai.mock_complete(data)


@app.post("/api/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest):
    """虚拟识别：逐味分析药效，附配伍解析与煎服建议。"""
    data = req.model_dump()
    return mock_ai.mock_recognize(data)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """AI 助手对话：携带完整历史消息，返回一条助手回复。"""
    return mock_ai.mock_chat([m.model_dump() for m in req.messages])