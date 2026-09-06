"""药方开方页：完整可选表单 → 调用虚拟 AI 服务 → 分卡片展示药方 → 导出 PDF。

深浅色热切换：**所有**颜色均取自 theme token 并在 refresh_style() 重建，
确保切换后自动适配。
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.ai_client import AIClientError, VirtualAIClient
from ..core.config import Config
from ..core.pdf_export import export_prescription_pdf
from .dark import is_dark
from .pagekit import BasePage, section_label, style_panel

_FORM_W = 370


# ---- 异步开方线程 ----
class PrescribeWorker(QThread):
    done = Signal(object)
    err = Signal(str)

    def __init__(self, client, data, parent=None):
        super().__init__(parent)
        self._client = client
        self._data = data

    def run(self):
        try:
            self._client.ensure_running()
            result = self._client.prescribe(self._data)
            self.done.emit(result)
        except AIClientError as e:
            self.err.emit(str(e))
        except Exception as e:                      # noqa: BLE001
            self.err.emit(f"开方失败：{e}")


# ---- 结果卡片 ----
class SectionCard(QWidget):
    """单页药方区段卡片：标题 + 若干行内容，支持一键主题刷新。"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._title = title
        self._rows = []                      # (widget, role)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 14)
        v.setSpacing(5)
        self.title_lab = QLabel(title)
        self.title_lab.setWordWrap(True)
        f = QFont(self.title_lab.font()); f.setPointSize(11); f.setBold(True)
        self.title_lab.setFont(f)
        v.addWidget(self.title_lab)
        self._lay = v
        self.refresh()

    def add_text(self, text, role="body"):
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lay.addWidget(lab)
        self._rows.append((lab, role))
        self.refresh_row(lab, role)

    def add_herb_row(self, name, dose, unit):
        row = QWidget(self)
        rh = QHBoxLayout(row)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(10)
        n = QLabel(name); n.setWordWrap(False)
        d = QLabel(f"{dose} {unit}"); d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._rows.append((n, "herb")); self._rows.append((d, "sub"))
        rh.addWidget(n, 1); rh.addWidget(d)
        self._lay.addWidget(row)
        self.refresh_row(n, "herb"); self.refresh_row(d, "sub")

    def refresh_row(self, lab, role):
        dark = is_dark(self)
        if role == "accent":
            color = theme.st("accent", dark)
        elif role == "sub":
            color = theme.st("sub_text", dark)
        else:
            color = theme.st("title_text", dark)
        if role == "herb":
            f = QFont(lab.font()); f.setPointSize(11)
            lab.setFont(f)
        lab.setStyleSheet(f"color: {color.name()}; background: transparent;")

    def refresh(self):
        dark = is_dark(self)
        bg = theme.st("panel_bg", dark).name()
        border = theme.st("panel_border", dark).name()
        self.setStyleSheet(
            f"SectionCard {{ background: {bg}; border: 1px solid {border};"
            f" border-radius: 10px; }}")
        self.title_lab.setStyleSheet(
            f"color: {theme.st('accent', dark).name()}; background: transparent;")
        for lab, role in self._rows:
            self.refresh_row(lab, role)
        self.update()


class _Results(QWidget):
    """结果区：动作条 + 可滚动卡片列表。"""

    def __init__(self, parent=None, on_export=None):
        super().__init__(parent)
        self.on_export = on_export
        self.cards = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        bar = QHBoxLayout(); bar.setSpacing(10)
        self.status = QLabel("等待输入并开方…")
        self.status.setObjectName("StatusLabel")
        self.export_btn = QPushButton("导出 PDF")
        self.export_btn.setObjectName("Ghost")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        bar.addWidget(self.status, 1)
        bar.addWidget(self.export_btn)
        root.addLayout(bar)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cw = QWidget()
        self.vlay = QVBoxLayout(self.cw)
        self.vlay.setContentsMargins(2, 2, 2, 4)
        self.vlay.setSpacing(12)
        self.vlay.addStretch(1)
        self.scroll.setWidget(self.cw)
        root.addWidget(self.scroll, 1)
        self.style_scroll()

        self.last_result = None
        self.show_placeholder()

    def show_placeholder(self):
        self.clear()
        p = QLabel(
            "输入症状等信息后点击「开方」。\n虚拟 AI 将生成结构化药方卡片。\n\n"
            "（当前为本地虚拟模型，仅用于功能演示，不构成医疗建议）")
        p.setWordWrap(True)
        p.setAlignment(Qt.AlignCenter)
        p.setMinimumHeight(200)
        self.vlay.insertWidget(self.vlay.count() - 1, p)
        self._fit_content()

    def _fit_content(self):
        """同步内容高度到滚动区，确保内容超高时出现滚动而非被压缩。"""
        self.cw.setMinimumHeight(self.vlay.sizeHint().height())

    def clear(self):
        self.cards = []
        while self.vlay.count() > 1:
            item = self.vlay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def render(self, data):
        self.clear()
        self.last_result = data
        self.status.setText("开方完成 ✅  ·  模型：" + data.get("model", ""))
        self.export_btn.setEnabled(True)

        name = data.get("prescription_name", "")
        principle = data.get("principle", "")

        head = SectionCard(name, self.cw)
        head.add_text(principle, role="body")
        self._append(head)

        herbs = data.get("herbs") or []
        c = SectionCard("药物组成", self.cw)
        for h in herbs:
            c.add_herb_row(h.get("name", ""), h.get("dose", ""), h.get("unit", ""))
        c.add_text(f"共 {len(herbs)} 味 · 剂数：{data.get('dosage_count', '')}", role="sub")
        self._append(c)

        for title, key in (("煎服法", "decoction"), ("禁忌", "contraindications"),
                           ("加减说明", "modifications")):
            val = data.get(key)
            if val:
                c = SectionCard(title, self.cw)
                c.add_text(val, role="body")
                self._append(c)

        c = SectionCard("备注", self.cw)
        c.add_text(data.get("warnings", ""), role="sub")
        self._append(c)
        self._fit_content()

    def _append(self, card):
        self._roles = []
        self.vlay.insertWidget(self.vlay.count() - 1, card)
        self.cards.append(card)

    def set_status(self, text):
        self.status.setText(text)

    def style_scroll(self):
        dark = is_dark(self)
        hover = theme.st("nav_hover", dark).name()
        self.scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {hover};"
            f" border-radius: 3px; min-height: 24px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        self.scroll.viewport().setAutoFillBackground(False)
        self.cw.setAutoFillBackground(False)

    def _style_roles(self):
        dark = is_dark(self)
        self.status.setStyleSheet(
            f"color: {theme.st('sub_text', dark).name()}; background: transparent;")

    def _export(self):
        if self.last_result and self.on_export:
            self.on_export(self.last_result)


class PrescribePage(BasePage):

    def __init__(self, parent=None):
        super().__init__("药方开方", "根据症状/病史/用药情况，AI 自动生成中药方")
        self.client = VirtualAIClient()
        self._worker = None
        self._build()

    # ---- 构建 ----
    def _build(self):
        self.panel = panel = QWidget(self)
        root = QHBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # 左：表单放入独立滚动区，内容超高时内部滚动，绝不压缩重叠
        self.form_scroll = QScrollArea(panel)
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QScrollArea.NoFrame)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.form_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.form_scroll.setFixedWidth(_FORM_W + 20)
        self.form = self._build_form()
        self.form.setMinimumWidth(_FORM_W - 6)
        self.form_scroll.setWidget(self.form)
        self._style_left_scroll()
        root.addWidget(self.form_scroll)

        # 右：结果滚动区
        self.results = _Results(panel, on_export=self._do_export)
        root.addWidget(self.results, 1)

        style_panel(panel)
        self.set_content(panel)

    def _build_form(self):
        self.form = form = QWidget()
        v = QVBoxLayout(form)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        v.addWidget(section_label("患者信息（均可选）", form))
        v.addSpacing(6)

        # (标题, 控件, 占位, 多行?)
        self.sy = self._field(v, "主诉 / 症状 *", True, "如：反复上腹隐痛，嗳气，食欲不振")
        self.hist = self._field(v, "现病史", True, "如：半年前曾确诊慢性胃炎")
        self.meds = self._field(v, "当前用药", False, "如：奥美拉唑 20mg 每日一次")
        self.age = self._field(v, "年龄 / 性别", False, "如：32 岁 · 女")
        self.constitution = self._field(v, "体质", False, "如：痰湿质、气虚质")
        self.allergy = self._field(v, "过敏史", False, "如：对青霉素过敏")
        self.tongue = self._field(v, "舌象脉象", False, "如：舌淡苔白腻，脉细")
        self.menstruation = self._field(v, "经带情况", False, "如：经量偏少，色淡")
        self.lifestyle = self._field(v, "生活习惯", False, "如：熬夜多、久坐")

        row = QHBoxLayout(); row.setSpacing(10)
        row.addWidget(QLabel("是否代煎", form))
        self.decoct = QComboBox(form)
        self.decoct.addItems(["否", "是"])
        row.addWidget(self.decoct)
        row.addStretch(1)
        v.addLayout(row)

        v.addSpacing(6)
        self.go_btn = QPushButton("开方", form)
        self.go_btn.clicked.connect(self._on_prescribe)
        v.addWidget(self.go_btn)
        self.hint = QLabel("全部字段可选，仅「症状」必填。每次开方为独立新对话。")
        self.hint.setWordWrap(True)
        v.addWidget(self.hint)
        v.addStretch(1)
        return form

    def _field(self, layout, label, multiline, placeholder):
        lab = QLabel(label, self.panel)
        lab.setWordWrap(True)
        layout.addWidget(lab)
        if multiline:
            w = QPlainTextEdit(self.panel)
            w.setPlaceholderText(placeholder)
            w.setFixedHeight(66)
        else:
            w = QLineEdit(self.panel)
            w.setPlaceholderText(placeholder)
        layout.addWidget(w)
        return w

    def _style_left_scroll(self):
        dark = is_dark(self)
        hover = theme.st("nav_hover", dark).name()
        self.form_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {hover};"
            f" border-radius: 3px; min-height: 24px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        self.form_scroll.viewport().setAutoFillBackground(False)
        self.form.setAutoFillBackground(False)

    def _collect(self) -> dict:
        return {
            "symptoms": self.sy.toPlainText(),
            "history": self.hist.toPlainText(),
            "current_meds": self.meds.text(),
            "age_gender": self.age.text(),
            "constitution": self.constitution.text(),
            "allergies": self.allergy.text(),
            "tongue_pulse": self.tongue.text(),
            "menstruation": self.menstruation.text(),
            "lifestyle": self.lifestyle.text(),
            "decoct": self.decoct.currentIndex() == 1,
        }

    # ---- 开方 ----
    def _on_prescribe(self):
        if self._worker and self._worker.isRunning():
            return
        data = self._collect()
        if not data["symptoms"].strip():
            self.results.set_status("请先填写「症状」后再开方。")
            return
        self.go_btn.setEnabled(False)
        self.results.set_status("正在启动虚拟 AI 并开方…")
        self._worker = PrescribeWorker(self.client, data, self)
        self._worker.done.connect(self._on_done)
        self._worker.err.connect(self._on_err)
        self._worker.finished.connect(lambda: self.go_btn.setEnabled(True))
        self._worker.start()

    def _on_done(self, result):
        self.results.render(result)

    def _on_err(self, msg):
        self.results.set_status("开方失败：" + msg)
        self.results.show_placeholder()

    # ---- 导出 PDF ----
    def _do_export(self, data):
        try:
            Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            name = data.get("prescription_name", "药方")
            fname = f"药方_{name}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            path = str(Config.DATA_DIR / fname)
            export_prescription_pdf(data, path)
            self.results.set_status(f"已导出：Data/{fname} ✅")
        except Exception as e:                      # noqa: BLE001
            self.results.set_status(f"导出失败：{e}")

    # ---- 主题热切换 ----
    def refresh_style(self):
        style_panel(self.panel)
        self._style_form_labels()
        self._style_left_scroll()
        self.results.style_scroll()
        for c in self.results.cards:
            c.refresh()
        self.results._style_roles()
        self.update()

    def _style_form_labels(self):
        dark = is_dark(self)
        col = theme.st("sub_text", dark).name()
        self.hint.setStyleSheet(f"color: {col}; background: transparent;")