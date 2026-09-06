"""PDF 导出（reportlab）：把结构化药方渲染成 PDF 输出到 Data/。"""
from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

_TITLE = ParagraphStyle("title", fontName="STSong-Light", fontSize=17,
                        leading=24, alignment=1, spaceAfter=2)
_SUB = ParagraphStyle("sub", fontName="STSong-Light", fontSize=10,
                      leading=16, alignment=1, textColor=colors.HexColor("#5a5a5a"),
                      spaceAfter=10)
_H = ParagraphStyle("h", fontName="STSong-Light", fontSize=11, leading=18,
                    textColor=colors.HexColor("#4a62d6"), spaceBefore=8,
                    spaceAfter=3)
_BODY = ParagraphStyle("body", fontName="STSong-Light", fontSize=10.5,
                       leading=19, spaceAfter=4)
_MUTED = ParagraphStyle("muted", fontName="STSong-Light", fontSize=9.5,
                        leading=15, textColor=colors.HexColor("#888888"))


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def export_prescription_pdf(data: dict, path: str) -> str:
    """生成中药开方 PDF，返回文件路径。"""
    story = []
    story.append(Paragraph(_esc(data.get("prescription_name") or "中药方"), _TITLE))
    story.append(Paragraph(_esc(data.get("principle") or ""), _SUB))
    story.append(Paragraph("一、组成", _H))
    rows = [["药名", "剂量", "单位"]]
    for h in data.get("herbs") or []:
        rows.append([_esc(h.get("name") or ""), _esc(h.get("dose") or ""),
                     _esc(h.get("unit") or "")])
    tbl = Table(rows, colWidths=[60 * mm, 30 * mm, 20 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTNAME", (0, 0), (-1, 0), "STSong-Light"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0fb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4))
    for label in ("剂量", "煎服法"):
        key = "dosage_count" if label == "剂量" else "decoction"
        story.append(Paragraph(f"{label}：{_esc(data.get(key) or '')}", _BODY))
    story.append(Paragraph("二、煎服与禁忌", _H))
    story.append(Paragraph(f"煎服法：{_esc(data.get('decoction') or '')}", _BODY))
    story.append(Paragraph(f"禁忌：{_esc(data.get('contraindications') or '')}", _BODY))
    story.append(Paragraph("三、加减", _H))
    story.append(Paragraph(_esc(data.get("modifications") or ""), _BODY))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"模型：{_esc(data.get('model') or '')} · 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        _MUTED))
    if data.get("warnings"):
        story.append(Paragraph(_esc(data["warnings"]), _MUTED))

    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            title="中药方")
    doc.build(story)
    return path


def export_recognize_pdf(data: dict, path: str) -> str:
    """生成药方识别 PDF（逐味药效 + 配伍解析 + 煎服确认），返回文件路径。"""
    story = []
    story.append(Paragraph("药方识别", _TITLE))
    story.append(Paragraph(_esc(data.get("model") or ""), _SUB))
    story.append(Paragraph("一、药物明细", _H))
    rows = [["药名", "剂量", "性味", "归经", "功效", "注意"]]
    for h in data.get("herbs") or []:
        dose = f"{h.get('dose') or ''}{h.get('unit') or ''}".strip()
        rows.append([_esc(h.get("name") or ""), _esc(dose),
                     _esc(h.get("nature_flavor") or ""), _esc(h.get("meridian") or ""),
                     _esc(h.get("effects") or ""), _esc(h.get("notes") or "")])
    tbl = Table(rows, colWidths=[28 * mm, 18 * mm, 24 * mm, 24 * mm, 55 * mm, 55 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0fb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"共 {len(data.get('herbs') or [])} 味。", _MUTED))
    story.append(Paragraph("二、配伍解析", _H))
    story.append(Paragraph(_esc(data.get("interaction") or ""), _BODY))
    story.append(Paragraph("三、煎服确认", _H))
    story.append(Paragraph(_esc(data.get("decoction") or ""), _BODY))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M}", _MUTED))
    if data.get("warnings"):
        story.append(Paragraph(_esc(data["warnings"]), _MUTED))

    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=22 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            title="药方识别")
    doc.build(story)
    return path