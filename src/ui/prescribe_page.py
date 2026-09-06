"""药方开方页：两阶段交互。

第一阶段（表单页）：输入内容占满整页，填写病情信息；
点击「开方」后切换到第二阶段（结果页）：顶部固定列出已录入的病情信息
（一条条），下方展示 AI 返回的清华药方；支持导出 PDF（保存位置对话框）。

深浅色热切换：**所有**颜色均取自 theme token 并在 refresh_style() 重建，
确保切换后自动适配。
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import (
    Qt, QAbstractAnimation, QEasingCurve, QThread, QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QStackedLayout,
    QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.ai_client import AIClientError, VirtualAIClient
from ..core.config import Config
from ..core.pdf_export import export_prescription_pdf
from .dark import is_dark
from .pagekit import BasePage, SectionCard, SmoothScrollArea, section_label, style_panel


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


class PrescribePage(BasePage):

    def __init__(self, parent=None):
        super().__init__("药方开方", "填写病情信息，AI 自动生成中药方")
        self.client = VirtualAIClient()
        self._worker = None
        self._fade_anim = None
        self._build()

    # ---- 构建 ----
    def _build(self):
        self.panel = panel = QWidget(self)
        self.stack = QStackedLayout(panel)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.setSpacing(0)
        self.form_page = self._build_form_page(panel)
        self.result_page = self._build_result_page(panel)
        self.stack.addWidget(self.form_page)
        self.stack.addWidget(self.result_page)
        self.stack.setCurrentIndex(0)

        style_panel(panel)
        self.set_content(panel)

    # ---- 第一阶段：表单页 ----
    def _build_form_page(self, parent):
        self.form_scroll = scroll = SmoothScrollArea(parent)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        form = QWidget(scroll)
        v = QVBoxLayout(form)
        v.setContentsMargins(2, 2, 6, 12)
        v.setSpacing(10)

        v.addWidget(section_label("患者信息（仅症状必填）", form))
        v.addSpacing(2)

        # 症状（多行、必填）
        self.symptoms_label = section_label("主诉 / 症状 *", form, bold=False)
        v.addWidget(self.symptoms_label)
        self.sy = QPlainTextEdit(form)
        self.sy.setPlaceholderText("如：反复上腹隐痛，嗳气，食欲不振")
        self.sy.setFixedHeight(108)
        self.sy.textChanged.connect(self._on_symptoms_changed)
        v.addWidget(self.sy)

        v.addSpacing(2)
        v.addWidget(section_label("现病史", form, bold=False))
        self.hist = QPlainTextEdit(form)
        self.hist.setPlaceholderText("如：半年前曾确诊慢性胃炎")
        self.hist.setFixedHeight(84)
        v.addWidget(self.hist)

        v.addSpacing(4)

        # 紧凑字段：两列网格
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)
        self.field_labels = []

        self.age = QLineEdit(form); self.age.setPlaceholderText("如：32")
        self._cell_field(grid, 0, 0, "年龄", self.age)

        gender_cell = self._build_gender(form)
        grid.addWidget(gender_cell, 0, 1)

        self.meds = QLineEdit(form); self.meds.setPlaceholderText("如：奥美拉唑 20mg 每日一次")
        self._cell_field(grid, 1, 0, "当前用药", self.meds)
        self.constitution = QLineEdit(form); self.constitution.setPlaceholderText("如：痰湿质、气虚质")
        self._cell_field(grid, 1, 1, "体质", self.constitution)

        self.allergy = QLineEdit(form); self.allergy.setPlaceholderText("如：对青霉素过敏")
        self._cell_field(grid, 2, 0, "过敏史", self.allergy)
        self.tongue = QLineEdit(form); self.tongue.setPlaceholderText("如：舌淡苔白腻，脉细")
        self._cell_field(grid, 2, 1, "舌象脉象", self.tongue)

        self.lifestyle = QLineEdit(form); self.lifestyle.setPlaceholderText("如：熬夜多、久坐")
        self._cell_field(grid, 3, 0, "生活习惯", self.lifestyle)
        self.menstruation = QLineEdit(form); self.menstruation.setPlaceholderText("如：经量偏少，色淡")
        # 「经带情况」置于末格：男生隐藏后不留中间空位
        self.menstruation_cell = self._cell_field(grid, 3, 1, "经带情况", self.menstruation)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid)

        v.addSpacing(8)
        self.go_btn = QPushButton("开方", form)
        self.go_btn.setObjectName("CTA")
        self.go_btn.setCursor(Qt.PointingHandCursor)
        self.go_btn.clicked.connect(self._on_prescribe)
        v.addWidget(self.go_btn)

        self.hint = QLabel("仅「症状」必填，其余可选。", form)
        self.hint.setWordWrap(True)
        v.addWidget(self.hint)

        v.addStretch(1)
        scroll.setWidget(form)
        self._style_scroll(scroll)
        self._style_form(form)
        self._style_labels(form)
        return scroll

    def _build_gender(self, parent):
        cell = QWidget(parent)
        cv = QVBoxLayout(cell)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(5)
        lab = self._make_label("性别（可选）", cell)
        cv.addWidget(lab)

        row = QHBoxLayout(); row.setSpacing(8)
        self.gender_group = QButtonGroup(parent); self.gender_group.setExclusive(True)
        self.gender_btns = {}
        for text in ("男", "女"):
            b = QPushButton(text, cell)
            b.setObjectName("SegBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, t=text: self._on_gender(t))
            self.gender_group.addButton(b)
            self.gender_btns[text] = b
            row.addWidget(b, 1)
        cv.addLayout(row)
        return cell

    def _make_label(self, text, parent):
        lab = QLabel(text, parent)
        lab.setWordWrap(True)
        self.field_labels.append(lab)
        return lab

    def _cell_field(self, grid, r, c, label, field):
        cell = QWidget(self.form_scroll)
        cv = QVBoxLayout(cell)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(5)
        lab = self._make_label(label, cell)
        field.setParent(cell)
        cv.addWidget(lab)
        cv.addWidget(field)
        grid.addWidget(cell, r, c)
        return cell

    def _on_gender(self, text):
        # 男生无需填写「经带情况」
        self.menstruation_cell.setVisible(text != "男")

    def _on_symptoms_changed(self):
        self.hint.setText("仅「症状」必填，其余可选。")
        self._style_labels(warn=False)

    # ---- 第二阶段：结果页 ----
    def _build_result_page(self, parent):
        page = QWidget(parent)
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)

        bar = QHBoxLayout(); bar.setSpacing(10)
        self.status = QLabel("填写病情信息后点击「开方」")
        bar.addWidget(self.status, 1)
        self.export_btn = QPushButton("导出 PDF")
        self.export_btn.setObjectName("Ghost")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._do_export)
        bar.addWidget(self.export_btn)
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setObjectName("Ghost")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset)
        bar.addWidget(self.reset_btn)
        col.addLayout(bar)

        self.page_scroll = scroll = SmoothScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cw = QWidget()
        self.vlay = QVBoxLayout(self.cw)
        self.vlay.setContentsMargins(2, 2, 2, 8)
        self.vlay.setSpacing(12)
        self.vlay.addStretch(1)
        scroll.setWidget(self.cw)
        col.addWidget(scroll, 1)

        self.cards = []
        self._last_data = None
        self._last_result = None
        self._style_scroll(scroll)
        self._style_status()
        return page

    def _result_line(self, label, value):
        return f"{label}：{value}" if value else ""

    def _fade_to(self, index):
        """表单↔结果两层之间做淡出淡入过渡，避免切换时生硬闪现。"""
        # 中断上次尚未结束的过渡，清理悬挂的 GraphicsEffect
        anim = self._fade_anim
        self._fade_anim = None
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
            self._reset_fade_effects()

        cur = self.stack.currentWidget()
        if self.stack.indexOf(cur) == index:
            return

        out_eff = QGraphicsOpacityEffect(cur)
        cur.setGraphicsEffect(out_eff)
        fade_out = QVariantAnimation(cur)
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0); fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        fade_out.valueChanged.connect(out_eff.setOpacity)

        def _on_out():
            cur.setGraphicsEffect(None)
            self.stack.setCurrentIndex(index)
            nxt = self.stack.currentWidget()
            in_eff = QGraphicsOpacityEffect(nxt)
            nxt.setGraphicsEffect(in_eff)
            in_eff.setOpacity(0.0)
            fade_in = QVariantAnimation(nxt)
            fade_in.setDuration(180)
            fade_in.setStartValue(0.0); fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.OutCubic)
            fade_in.valueChanged.connect(in_eff.setOpacity)

            def _on_in():
                if self._fade_anim is fade_in:
                    self._fade_anim = None
                nxt.setGraphicsEffect(None)

            fade_in.finished.connect(_on_in)
            fade_in.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._fade_anim = fade_in

        fade_out.finished.connect(_on_out)
        fade_out.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = fade_out

    def _reset_fade_effects(self):
        for idx in range(self.stack.count()):
            w = self.stack.widget(idx)
            if w is not None:
                w.setGraphicsEffect(None)

    def _open_result(self, data):
        """切换结果页：顶部列出已录入信息 + 下方占位（等待开方）。"""
        self._last_data = data
        self._fade_to(1)
        self.cards = []
        while self.vlay.count() > 1:
            item = self.vlay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        info = SectionCard("已录入的病情与信息", self.cw)
        lines = self._info_lines(data)
        if lines:
            for line in lines:
                info.add_text(line, role="body")
        else:
            info.add_text("未录入其他信息。", role="sub")
        self._append_card(info)

        ph = QLabel("正在生成药方，请稍候…")
        ph.setAlignment(Qt.AlignCenter)
        ph.setMinimumHeight(160)
        self._append_card(ph, is_placeholder=True)

        self.status.setText("正在开方…")
        self.export_btn.setEnabled(False)
        self._fit_content()

    def _info_lines(self, data):
        fields = [
            ("主诉/症状", "symptoms"), ("现病史", "history"),
            ("年龄", "age"), ("性别", "gender"),
            ("当前用药", "current_meds"), ("体质", "constitution"),
            ("过敏史", "allergies"), ("舌象脉象", "tongue_pulse"),
            ("经带情况", "menstruation"), ("生活习惯", "lifestyle"),
        ]
        return [self._result_line(lb, data.get(k)) for lb, k in fields
                if str(data.get(k) or "").strip()]

    def _append_card(self, card, is_placeholder=False):
        self.vlay.insertWidget(self.vlay.count() - 1, card)
        if not is_placeholder:
            self.cards.append(card)

    def _clear_placeholder(self):
        self.cards = []                       # 重新挂载卡片列表
        for i in range(self.vlay.count()):
            item = self.vlay.itemAt(i)
            w = item.widget()
            if w is not None and isinstance(w, QLabel) and w.alignment() == Qt.AlignCenter:
                item = self.vlay.takeAt(i)
                w.deleteLater()
                break
        # 保留 info 卡片为第一张
        first = self.vlay.itemAt(0).widget()
        if isinstance(first, SectionCard):
            self.cards.append(first)

    def _render_result(self, result):
        self._last_result = result
        self._clear_placeholder()
        self.status.setText("开方完成 ✅" + ("  ·  模型：" + result.get("model", "") if result.get("model") else ""))
        self.export_btn.setEnabled(True)

        name = result.get("prescription_name", "")
        principle = result.get("principle", "")

        head = SectionCard(name, self.cw)
        if principle:
            head.add_text(principle, role="body")
        self._append_card(head)

        herbs = result.get("herbs") or []
        c = SectionCard("药物组成", self.cw)
        for h in herbs:
            c.add_herb_row(h.get("name", ""), h.get("dose", ""), h.get("unit", ""))
        c.add_text(f"共 {len(herbs)} 味 · 剂数：{result.get('dosage_count', '')}", role="sub")
        self._append_card(c)

        for title, key in (("煎服法", "decoction"), ("禁忌", "contraindications"),
                           ("加减说明", "modifications")):
            val = result.get(key)
            if val:
                c = SectionCard(title, self.cw)
                c.add_text(val, role="body")
                self._append_card(c)

        c = SectionCard("备注", self.cw)
        c.add_text(result.get("warnings", ""), role="sub")
        self._append_card(c)
        self._fit_content()

    def _show_error(self, msg):
        self._clear_placeholder()
        self.status.setText("开方失败")
        err = SectionCard("开方失败", self.cw)
        err.add_text(msg, role="body")
        self._append_card(err)
        self.export_btn.setEnabled(False)
        self._fit_content()

    def _fit_content(self):
        self.cw.setMinimumHeight(self.vlay.sizeHint().height())

    # ---- 开方 ----
    def _collect(self) -> dict:
        age = self.age.text().strip()
        gender = (self.gender_group.checkedButton().text() if
                  self.gender_group.checkedButton() else "")
        age_parts = []
        if age:
            age_parts.append(f"{age}岁")
        if gender:
            age_parts.append(gender)
        menstruation = self.menstruation.text() if gender != "男" else ""
        return {
            "symptoms": self.sy.toPlainText(),
            "history": self.hist.toPlainText(),
            "current_meds": self.meds.text(),
            "age": age,
            "gender": gender,
            "age_gender": " · ".join(p for p in age_parts if p),
            "constitution": self.constitution.text(),
            "allergies": self.allergy.text(),
            "tongue_pulse": self.tongue.text(),
            "menstruation": menstruation,
            "lifestyle": self.lifestyle.text(),
        }

    def _on_prescribe(self):
        if self._worker and self._worker.isRunning():
            return
        data = self._collect()
        if not data["symptoms"].strip():
            self.hint.setText("请先填写「症状」再开方。")
            self._style_labels(warn=True)
            return
        self.go_btn.setEnabled(False)
        self._open_result(data)
        self._worker = PrescribeWorker(self.client, data, self)
        self._worker.done.connect(self._render_result)
        self._worker.err.connect(self._show_error)
        self._worker.finished.connect(lambda: self.go_btn.setEnabled(True))
        self._worker.start()

    # ---- 重置 ----
    def _on_reset(self):
        """清空已填表单并回到输入界面。"""
        self.sy.clear()
        self.hist.clear()
        self.age.clear()
        self.meds.clear()
        self.constitution.clear()
        self.allergy.clear()
        self.tongue.clear()
        self.lifestyle.clear()
        self.menstruation.clear()
        checked = self.gender_group.checkedButton()
        if checked is not None:
            checked.setChecked(False)
        self.menstruation_cell.setVisible(True)
        self.hint.setText("仅「症状」必填，其余可选。")
        self._style_labels(warn=False)
        self.cards = []
        self._last_data = None
        self._last_result = None
        self.status.setText("填写病情信息后点击「开方」")
        self.export_btn.setEnabled(False)
        self._fade_to(0)

    # ---- 导出 PDF ----
    def _do_export(self):
        if not self._last_result:
            return
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        default = Config.DATA_DIR / f"药方_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF", str(default), "PDF 文件 (*.pdf)")
        if not path:
            return
        try:
            export_prescription_pdf(self._last_result, path)
            self.status.setText("已导出 ✅  " + path)
        except Exception as e:                      # noqa: BLE001
            self.status.setText(f"导出失败：{e}")

    # ---- 样式 ----
    def _style_scroll(self, scroll):
        dark = is_dark(self)
        # 滚动条把手：以次级文字色派生半透明色，默认淡悬停深，精致不突兀
        base = QColor(theme.st("sub_text", dark))
        h_idle = QColor(base); h_idle.setAlpha(64)
        h_hover = QColor(base); h_hover.setAlpha(130)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; }}"
            f"QScrollBar:vertical {{ background: transparent; width: 6px;"
            f" margin: 2px 2px 2px 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {h_idle.name()};"
            f" border-radius: 3px; min-height: 26px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {h_hover.name()}; }}"
            f"QScrollBar::handle:vertical:pressed {{ background: {h_hover.name()}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,"
            f" QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{"
            f" height: 0; width: 0; background: transparent; }}")
        scroll.viewport().setAutoFillBackground(False)

    def _style_labels(self, warn=False):
        dark = is_dark(self)
        sub = theme.st("sub_text", dark).name()
        accent = theme.st("accent", dark).name()
        for lab in self.field_labels:
            lab.setStyleSheet(f"color: {sub}; background: transparent;")
        # 必填的「症状」标签在缺省时以强调色提示
        self.symptoms_label.setStyleSheet(
            f"color: {accent if warn else sub}; background: transparent;")
        self.hint.setStyleSheet(
            f"color: {accent if warn else sub}; background: transparent;")

    def _style_form(self, form):
        dark = is_dark(self)
        fg = theme.st("nav_text_act", dark).name()
        border = theme.st("panel_border", dark).name()
        accent = theme.st("accent", dark)
        hover = theme.st("nav_hover", dark).name()
        form.setStyleSheet(
            f"QPushButton#SegBtn {{ background: transparent; color: {fg};"
            f" border: 1px solid {border}; border-radius: 8px;"
            f" padding: 5px 0; }}"
            f"QPushButton#SegBtn:hover {{ background: {hover}; }}"
            f"QPushButton#SegBtn:checked {{ background: {accent.name()}; color: white;"
            f" border-color: {accent.name()}; }}"
            f"QPushButton#CTA {{ background: {accent.name()}; color: white;"
            f" border: none; border-radius: 10px; height: 40px; }}"
            f"QPushButton#CTA:hover {{ background: {accent.darker(112).name()}; }}"
            f"QPushButton#CTA:disabled {{ background: #9aa0ab; }}")

    def _style_status(self):
        dark = is_dark(self)
        self.status.setStyleSheet(
            f"color: {theme.st('sub_text', dark).name()}; background: transparent;")

    # ---- 主题热切换 ----
    def refresh_style(self):
        style_panel(self.panel)
        self._style_form(self.form_page)
        self._style_scroll(self.form_scroll)
        self._style_scroll(self.page_scroll)
        self._style_status()
        self._style_labels()
        for c in self.cards:
            c.refresh()
        self.update()