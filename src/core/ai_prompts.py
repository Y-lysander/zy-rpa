"""发送给真实 AI 的提示词构建，与返回格式约束。

开方/识别/助手的提示词与返回格式解析都收敛在 GUI 端，保证模型严格按约定
Markdown 返回，GUI 才能稳定解析并显示到正确位置。
"""
from __future__ import annotations


# 开方：患者输入字段（标签, dict key）
_PRESCRIBE_FIELDS = [
    ("患者主诉/症状", "symptoms"),
    ("现病史", "history"),
    ("当前用药", "current_meds"),
    ("年龄/性别", "age_gender"),
    ("体质", "constitution"),
    ("过敏史", "allergies"),
    ("舌象脉象", "tongue_pulse"),
    ("经带情况", "menstruation"),
    ("生活习惯", "lifestyle"),
]

# 开方：模型需按这些标签返回（唯一，与 GUI 解析 key 对应）
_PRESCRIBE_OUT_LABELS = [
    "方名", "立法思路", "剂数", "煎服法", "禁忌", "加减说明", "备注",
]


def _fmt_quote(label: str, value: str) -> str:
    value = (value or "").strip()
    return f"{label}：{value}\n" if value else ""


def _prescription_format_rules() -> str:
    """开方输出格式硬约束（含示例），供提示词复用。"""
    labels = "、".join(f"**{lb}**" for lb in _PRESCRIBE_OUT_LABELS)
    return (
        "\n# 输出格式（必须严格遵守，这是解析契约）\n"
        f"只输出以下结构，不得输出 JSON、代码块或任何额外说明：\n"
        f"先用 `## 药方` 开头；"
        f"随后按顺序用加粗标签行 `**标签**：值` 输出，可用标签：{labels}；\n"
        f"药材清单必须用表格，表头固定为 `| 药材名称 | 剂量 | 单位 |`，"
        f"分隔行为 `|---|---|---|`，每行一味药；\n"
        f"某个字段没有信息时可省略对应标签，但不要编造；"
        f"**方名**/**立法思路** 必须给出。\n"
        f"示例：\n"
        f"## 药方\n\n"
        f"**方名**：桂枝汤\n"
        f"**立法思路**：解肌发表，调和营卫\n\n"
        f"| 药材名称 | 剂量 | 单位 |\n|---|---|---|\n"
        f"| 桂枝 | 9 | g |\n| 白芍 | 9 | g |\n\n"
        f"**剂数**：5\n"
        f"**煎服法**：水煎服，温覆取微汗\n"
        f"**禁忌**：忌生冷、油腻\n"
        f"**加减说明**：随证加减\n"
        f"**备注**：AI 生成，仅供参考\n"
    )


def build_prescription_prompt(data: dict) -> str:
    """患者信息 + 开方任务 + 返回格式约束。"""
    lines = ["# 任务：请对以下患者开出中药方",
             "# 要求：直接给出完整药方，不得反问提问。"]
    lines += [_fmt_quote(label, data.get(key)) for label, key in _PRESCRIBE_FIELDS]
    if data.get("decoct"):
        lines.append("煎服提示：患者需代煎。\n")
    return "".join(lines) + _prescription_format_rules()


def _recognize_format_rules() -> str:
    """识别输出格式硬约束（含示例）。"""
    return (
        "\n# 输出格式（必须严格遵守，这是解析契约）\n"
        "只输出以下结构，不得输出 JSON、代码块或任何额外说明：\n"
        "逐味药各用一个三级标题 `### 药名 剂量单位` 开头，块内用 `- ` 列表输出"
        "`- 性味：…`、`- 归经：…`、`- 功效：…`、`- 注意：…`（无信息可省略对应项）；\n"
        "最后用加粗标签行给出 `**配伍解析**：…`、`**煎服确认**：…`、`**备注**：…`；\n"
        "示例：\n"
        "## 识别结果\n\n"
        "### 桂枝 9g\n"
        "- 性味：辛、甘，温\n"
        "- 归经：心、肺、膀胱经\n"
        "- 功效：发汗解肌，温通经脉\n"
        "- 注意：温热病者忌用\n\n"
        "**配伍解析**：本方共 1 味药，以温通为主\n"
        "**煎服确认**：水煎服\n"
        "**备注**：AI 生成，仅供参考\n"
    )


def build_recognize_prompt(data: dict) -> str:
    """待识别药材 + 识别任务 + 返回格式约束。"""
    herbs = [h for h in (data.get("herbs") or [])
             if str(h.get("name") or "").strip()]
    lines = ["# 任务：请分析下列药材的性味归经、功效主治与配伍禁忌",
             "# 要求：逐味返回结构化结果，另附配伍解析与煎服建议。"]
    if herbs:
        rows = "；".join(f"{h.get('name')} {h.get('dose') or ''}{h.get('unit') or ''}"
                         for h in herbs)
        lines.append("药材清单：" + rows)
    if (data.get("full_text") or "").strip():
        lines.append("整方原文：\n" + data["full_text"].strip())
    return "\n".join(lines) + _recognize_format_rules()


# 对话助手系统提示词：角色/职责 + 返回格式约定（富文本渲染）
CHAT_SYSTEM_PROMPT = (
    "# 角色\n"
    "你是一位经验丰富的中医师，是「智能中药开方系统」的 AI 助手，"
    "精通中医基础理论、中药学、方剂学与辨证论治。\n"
    "# 职责\n"
    "1. 解答用户关于中药、方剂、症状调理、养生保健等中医相关问题；\n"
    "2. 解释开方/识别结果中的疑问，说明药性、配伍、煎服方法与注意事项；\n"
    "3. 涉及用药的建议须审慎，明确提示需由执业中医师辨证审核。\n"
    "# 要求\n"
    "- 回答精炼准确，先给结论再展开；\n"
    "- 涉及剂量与配伍时给出安全提示；\n"
    "- 不夸大疗效、不承诺治愈；\n"
    "- 无法判断或超出中医范围时如实说明。\n"
    "# 返回格式（便于界面渲染）\n"
    "- 用 `## 小节标题`（或 `###`）组织长回复；\n"
    "- 要点用加粗标签 `**标签**：值`；\n"
    "- 对照性内容可 用 `| 列1 | 列2 |` 式表格；\n"
    "- 步骤/条目用 `- ` 列表。\n"
)


def chat_messages_with_system(messages: list) -> list:
    """把系统提示词以 system 消息拼在会话最前，供真实模型调用。"""
    return [{"role": "system", "content": CHAT_SYSTEM_PROMPT}] + list(messages or [])