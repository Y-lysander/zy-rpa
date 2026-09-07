"""应用全局配置（模块级，沿用框架的 Config 模式）。"""

from pathlib import Path


class Config:
    """应用配置（模块级，沿用框架的 Config 模式）。"""

    APP_NAME = "RPA中药系统"      # 程序名称（顶栏/任务栏统一显示）

    # 项目根目录（src/core/config.py 向上三层）
    ROOT = Path(__file__).resolve().parents[2]

    # 动态数据目录（AI 生成/导出的内容产物统一放根目录 Data/）
    DATA_DIR = ROOT / "Data"

    # ---- 模型供应商 ----
    AI_PROVIDER = "deepseek"    # 当前供应商：deepseek

    # 供应商 API 端点
    DEEPSEEK_API_BASE = "https://api.deepseek.com"
    DEEPSEEK_BALANCE_API = "/user/balance"
    DEEPSEEK_CHAT_API = "/chat/completions"

    # 供应商默认模型
    DEFAULT_MODEL = "deepseek-v4-flash"

    # 模型下拉候选（当前仅 DeepSeek 单供应商）
    MODEL_PROVIDERS = [
        {"name": "DeepSeek", "provider": "deepseek",
         "models": ["deepseek-v4-flash"]},
    ]