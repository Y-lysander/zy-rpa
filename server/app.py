"""虚拟 AI 服务 —— FastAPI 入口（本地模拟，不接真实云端模型）。

接口：
    GET  /health            健康探活（GUI 用于检测服务是否已启动）
    POST /api/prescribe     药方开方（单次对话，直接给出药方，不询问）

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


@app.get("/health")
def health():
    return {"status": "ok", "model": mock_ai.MODEL_NAME}


@app.post("/api/prescribe", response_model=PrescribeResponse)
def prescribe(req: PrescribeRequest):
    """虚拟开方：单次对话，每次独立，直接给出药方。"""
    data = req.model_dump()
    return mock_ai.mock_complete(data)