# 智能中药开方系统

智能化的中药/药方 **开方** 与 **识别** 系统（图形界面版）。

本地 GUI 接入云端 AI 大模型，根据患者的症状、病史、当前用药情况自动生成中药方；
识别药方中各味药材的药效；并提供 AI 对话助手辅助调整与改进药方。

> 方向依据：见 `PRD.md`（含「待澄清细节」，后续逐条确认）。

## 快速开始

```bash
pip install PySide6 reportlab
python main.py
```

首次使用前，需先在「设置 → AI 模型配置」中添加模型并填写 DeepSeek API Key
（保存前自动校验有效性与网络连通性）。

> 当前接入 DeepSeek 云端模型（`deepseek-v4-flash`），API Key 仅保存在本地配置中。

## 界面构成（左侧导航）

| 页面 | 说明 |
|---|---|
| **药方开方** | ✅ 已实现：完整表单 → AI 生成药方 → 分卡片展示、可导出 PDF |
| **药方识别** | 逐项输入药材名称/计量 → AI 分析药效并展示、可导出 PDF（待实现） |
| **AI助手** | 对话改进/调整药方；可实时查看药方状态（药材/计量/煎服方式等） |
| **设置** | 深浅色与系统风格切换；AI 模型添加/更换/删除与 API Key 配置 |
| **关于** | 简介与免责声明 |

> 开方/识别/助手均接入云端 DeepSeek 模型。

## 项目结构

```
zy_rpa/
  main.py             # GUI 唯一入口（python main.py）
  PRD.md              # 产品需求文档（含待澄清细节）
  src/
    core/             # 应用配置(Config)、主题/风格(theme)、用户偏好持久化(user_config)、
                      # AI 客户端(ai_client)、DeepSeek 客户端(deepseek_client)、PDF 导出(pdf_export)
    ui/               # 主窗口(window)、页面(settings/about/prescribe/recognize/assistant)、
                      # 配置向导(model_wizard)、共享组件(pagekit/dark)
  Data/               # 动态数据目录（AI 生成/导出产物，不入版本库）
```

## 数据与隐私

- 用户偏好（界面风格/深浅色）持久化于 `用户主目录/zy_rpa/config.json`。
- AI 生成/导出产物统一放根目录 `Data/`。
- AI 交互涉及患者症状/病史上传云端模型，实际使用请注意隐私与合规。