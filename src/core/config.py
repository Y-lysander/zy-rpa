"""应用全局配置（模块级，沿用框架的 Config 模式）。"""

from pathlib import Path


class Config:
    """应用配置（模块级，沿用框架的 Config 模式）。"""

    APP_NAME = "RPA中药系统"      # 程序名称（顶栏/任务栏统一显示）

    # 项目根目录（src/core/config.py 向上三层）
    ROOT = Path(__file__).resolve().parents[2]

    # 动态数据目录（AI 生成/导出的内容产物统一放根目录 Data/）
    DATA_DIR = ROOT / "Data"

    # 虚拟 AI 服务（本地模拟，不接真实云端模型）
    AI_HOST = "127.0.0.1"
    AI_PORT = 8123
    AI_BASE = f"http://{AI_HOST}:{AI_PORT}"
    AI_PROVIDER = "virtual"   # 当前供应商：virtual（本地模拟）