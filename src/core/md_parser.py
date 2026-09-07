"""轻量 Markdown 解析器：把真实 AI 按约定格式返回的文本转换为 GUI 可用的数据。

覆盖三类输出：
- parse_prescription：开方结果 → dict
- parse_recognize：识别结果 → dict
- md_to_html：对话回复的 `##/###`、`**加粗**：`、`|表|`、`- 列表` → QTextEdit HTML

健壮性：逐行状态机扫描，任一行异常只跳过该行，绝不抛异常；缺字段置空，
由上层按 `if val:` 决定是否渲染该段。
"""
from __future__ import annotations

import html
import re

# ---- 开方：加粗标签 → key ----
PRESCRIBE_LABELS = {
    "方名": "prescription_name",
    "立法思路": "principle",
    "剂数": "dosage_count",
    "煎服法": "decoction",
    "禁忌": "contraindications",
    "加减说明": "modifications",
    "备注": "warnings",
}

# ---- 识别：块内 `- 标签` → key；段级加粗标签 → key ----
RECOGNIZE_LABELS = {
    "性味": "nature_flavor",
    "归经": "meridian",
    "功效": "effects",
    "注意": "notes",
}
RECOGNIZE_SECTIONS = {
    "配伍解析": "interaction",
    "煎服确认": "decoction",
    "备注": "warnings",
}

_BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*\s*[:：]\s*(.*)$")
_HEADING = re.compile(r"^#{2,3}\s+(.*)$")
_HERB_HEADING = re.compile(r"^###\s+(.*)$")
# 药名 剂量 单位（单位可缺）
_HERB_TITLE = re.compile(r"^(.*?)\s*([\d.]+)\s*(克|g|G|kg|毫克|毫升|ml|枚|片|包|剂|钱)?$")
_TABLE_HEADER = re.compile(r"^\|\s*药材名称\s*\|\s*剂量\s*\|\s*单位\s*\|$")
_TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
_DASH_LINE = re.compile(r"^-\s*(.+?)\s*[:：]\s*(.*)$")
_UNIT_WORDS = ("克", "g", "kg", "毫克", "毫升", "ml", "枚", "片", "包", "剂", "钱")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


# ---------------------------------------------------------------------------
# 通用逐行扫描骨架
# ---------------------------------------------------------------------------
def _lines(text):
    return (text or "").splitlines()


def parse_prescription(text: str) -> dict:
    """开方 Markdown → dict：prescription_name/principle/herbs[]/dosage_count/
    decoction/contraindications/modifications/warnings（缺失置空）。"""
    result = {
        "prescription_name": "", "principle": "", "dosage_count": "",
        "decoction": "", "contraindications": "", "modifications": "",
        "warnings": "", "model": "",
    }
    herbs: list[dict] = []
    try:
        cur_key = None          # 正在多行折叠的字段
        cur_val: list[str] = []
        in_table = False

        def commit():
            nonlocal cur_key, cur_val
            if cur_key:
                if cur_val:
                    result[cur_key] = "\n".join(cur_val).strip()
                cur_key = None
                cur_val = []

        for raw in _lines(text):
            line = raw.rstrip()
            s = line.strip()
            if not s:
                continue

            # 分隔行（表格数据续行前）
            if _TABLE_SEP.match(s) and in_table:
                continue

            # 药材表
            if s.startswith("|"):
                if _TABLE_HEADER.match(s):
                    commit()
                    in_table = True
                    continue
                if in_table:
                    cells = _cells(s)
                    if len(cells) >= 3:
                        herbs.append({
                            "name": cells[0], "dose": cells[1], "unit": cells[2],
                        })
                    else:
                        herbs.append({"name": cells[0] if cells else "",
                                      "dose": cells[1] if len(cells) > 1 else "",
                                      "unit": ""})
                    continue
                # 表外的 | 行忽略

            m = _BOLD_LINE.match(s)
            if m:
                label, inline = m.group(1).strip(), m.group(2).strip()
                key = PRESCRIBE_LABELS.get(label)
                if key:
                    commit()
                    cur_key = key
                    if inline:
                        cur_val = [inline]
                continue

            # 标题/其他标记：中断折叠
            if _HEADING.match(s):
                commit()
                continue
            if _DASH_LINE.match(s):
                commit()
                continue

            # 普通行：折叠进当前字段
            if cur_key is not None:
                cur_val.append(s)
        commit()
        result["herbs"] = herbs
    except Exception:                                   # noqa: BLE001
        result["herbs"] = result.get("herbs") or herbs
    return result


def parse_recognize(text: str) -> dict:
    """识别 Markdown → dict：herbs[]（name/dose/unit/nature_flavor/meridian/
    effects/notes）+ interaction/decoction/warnings（缺失置空）。"""
    result = {"herbs": [], "interaction": "", "decoction": "",
              "warnings": "", "model": ""}
    try:
        herb: dict | None = None
        herb_last_field = None          # 用于 `- ` 值的续行折叠
        sec_key = None                  # 段级字段折叠
        sec_val: list[str] = []

        def commit_sec():
            nonlocal sec_key, sec_val
            if sec_key:
                if sec_val:
                    result[sec_key] = "\n".join(sec_val).strip()
                sec_key = None
                sec_val = []

        def commit_herb():
            nonlocal herb, herb_last_field
            if herb:
                result["herbs"].append(herb)
                herb = None
                herb_last_field = None

        for raw in _lines(text):
            line = raw.rstrip()
            s = line.strip()
            if not s:
                continue

            hm = _HERB_HEADING.match(s)
            if hm:
                commit_herb()
                commit_sec()
                title = hm.group(1).strip()
                herb = {"name": "", "dose": "", "unit": "",
                        "nature_flavor": "", "meridian": "", "effects": "", "notes": ""}
                tm = _HERB_TITLE.match(title)
                if tm:
                    herb["name"] = tm.group(1).strip()
                    herb["dose"] = tm.group(2) or ""
                    herb["unit"] = (tm.group(3) or "").strip()
                herb_last_field = None
                continue

            bm = _BOLD_LINE.match(s)
            if bm:
                label, inline = bm.group(1).strip(), bm.group(2).strip()
                key = RECOGNIZE_SECTIONS.get(label)
                if key:
                    commit_herb()
                    commit_sec()
                    sec_key = key
                    sec_val = [inline] if inline else []
                continue

            dm = _DASH_LINE.match(s)
            if dm:
                if sec_key:
                    commit_sec()
                if herb is not None:
                    label, val = dm.group(1).strip(), dm.group(2).strip()
                    key = RECOGNIZE_LABELS.get(label)
                    if key:
                        herb[key] = val
                        herb_last_field = key
                    else:
                        herb_last_field = None   # 未识别标签不作为续行接收器
                continue

            if sec_key is not None:
                sec_val.append(s)
            elif herb is not None and herb_last_field:
                prev = herb.get(herb_last_field) or ""
                herb[herb_last_field] = (prev + "\n" + s) if prev else s
            # 其余忽略

        commit_sec()
        commit_herb()
    except Exception:                                   # noqa: BLE001
        pass
    return result


# ---------------------------------------------------------------------------
# 对话回复：Markdown → HTML（供 ChatBubble 富文本显示）
# ---------------------------------------------------------------------------
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline_bold(s: str) -> str:
    return _BOLD_RE.sub(r"<b>\1</b>", s)


def _table_html(rows: list[str]) -> str:
    """把已收集的表格行（含表头/分隔/数据）转成 <table>。"""
    hdr = []
    body = []
    for i, row in enumerate(rows):
        if _TABLE_SEP.match(row.strip()):
            continue
        cells = _cells(row)
        if i == 0 and cells:
            hdr = cells
        elif cells:
            body.append(cells)
    thead = "<thead><tr>" + "".join(f"<th>{_inline_bold(c)}</th>" for c in hdr) + "</tr></thead>" \
        if hdr else ""
    tbody = "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{_inline_bold(c)}</td>" for c in row) + "</tr>"
        for row in body) + "</tbody>"
    return f"<table>{thead}{tbody}</table>"


def md_to_html(text: str) -> str:
    """把 `##/###`、`**加粗**：`、`|表|`、`- 列表` 渲染成 QTextEdit 可用 HTML。

    颜色交由气泡 QSS 继承，这里只输出语义标签；无这些标记时退化为简单段落。
    """
    text = (text or "").strip()
    if not text:
        return "<p></p>"
    lines = html.escape(text).splitlines()
    out: list[str] = []
    in_ul = False
    i = 0

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    while i < len(lines):
        raw = lines[i].rstrip()
        s = raw.strip()
        if not s:
            close_ul()
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j].strip())
                j += 1
            close_ul()
            out.append(_table_html(rows))
            i = j
            continue
        hm = re.match(r"^(#{2,3})\s+(.*)$", s)
        if hm and hm.group(2):
            close_ul()
            lvl = 2 if len(hm.group(1)) == 2 else 3
            out.append(f"<h{lvl}>{_inline_bold(hm.group(2))}</h{lvl}>")
            i += 1
            continue
        if s.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_bold(s[2:])}</li>")
            i += 1
            continue
        close_ul()
        out.append(f"<p>{_inline_bold(s)}</p>")
        i += 1
    close_ul()
    return "<div>" + "".join(out) + "</div>"


# 占位：与 server 响应模型一致，供外部引用
PRESCRIPTION_FIELD_MAP = list(PRESCRIBE_LABELS.values())
RECOGNIZE_FIELD_MAP = list(RECOGNIZE_SECTIONS.values())