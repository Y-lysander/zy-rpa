"""药方识别页：两阶段交互。

第一阶段（表单页）：逐项录入药材（药名/剂量/单位，可动态增删行），
也可一次性粘贴整方文本；点击「识别」后切换到第二阶段（结果页）：
逐味展示性味归经、功效与注意，附配伍解析与煎服确认；支持导出 PDF。

深浅色热切换：所有颜色均取自 theme token 并在 refresh_style() 重建。
"""
from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtCore import (
    QAbstractNativeEventFilter, QObject, QRect, Qt, QAbstractAnimation,
    QEasingCurve, QEvent, QPoint, QThread, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton,
    QScrollArea, QStackedLayout, QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.ai_client import AIClientError, VirtualAIClient
from ..core.config import Config
from ..core.pdf_export import export_recognize_pdf
from ..data.herbs import HERB_NAMES, search
from .dark import is_dark
from .pagekit import (
    AnimatedButton, BasePage, SectionCard, SmoothScrollArea, section_label, style_panel,
)

# 剂量单位下拉候选（data 存规范化单位文本）
_UNITS = ["g", "kg", "毫克", "毫升", "枚", "片", "包", "剂", "钱"]


# ---- Windows 输入法键位拦截 ----
# 中文输入法在组合拼音时会把方向键/回车送给输入法候选窗，QLineEdit 因而收不到
# QEvent.KeyPress，导致联想弹窗的键盘选词失效。这里用原生消息过滤器在系统层
# 拦截这几个键，直接处理选词/填入/收起，避免被输入法吞掉。
_WIN32 = sys.platform == "win32"
_VK_UP, _VK_DOWN, _VK_RETURN, _VK_ESCAPE = 0x26, 0x28, 0x0D, 0x1B
_WM_KEYDOWN = 0x0100


class _HerbNativeKeyFilter(QAbstractNativeEventFilter):
    """(仅 Windows) 联想弹窗可见时拦截方向键/回车/ESC，避免被输入法吞掉。"""

    def nativeEventFilter(self, eventType, message):
        if not _WIN32 or eventType not in (b"windows_generic_MSG", "windows_generic_MSG"):
            return False, 0
        try:
            msg = _MSG.from_address(int(message))
            if msg.message != _WM_KEYDOWN:
                return False, 0
            edit = QApplication.focusWidget()
            if not isinstance(edit, HerbNameEdit) or not edit._popup.isVisible():
                return False, 0
            key = msg.wParam
            if key == _VK_UP:
                edit._nav(-1); return True, 0
            if key == _VK_DOWN:
                edit._nav(1); return True, 0
            if key == _VK_RETURN:
                edit._confirm(); return True, 0
            if key == _VK_ESCAPE:
                edit._close_popup(); return True, 0
        except Exception:
            pass
        return False, 0


if _WIN32:
    import ctypes

    class _MSG(ctypes.Structure):
        """64 位 Windows MSG 结构前 4 个字段（足够读取 message 与 wParam）。"""
        _fields_ = [
            ("hwnd", ctypes.c_void_p),      # 偏移 0
            ("message", ctypes.c_uint),     # 偏移 8
            ("_pad", ctypes.c_uint),        # 偏移 12
            ("wParam", ctypes.c_size_t),    # 偏移 16
        ]

    _herb_native_filter = _HerbNativeKeyFilter()
    _herb_native_installed = False
else:
    _herb_native_filter = None
    _herb_native_installed = True


def _install_native_filter():
    """应用级安装一次原生键位过滤器（Windows 专用）。"""
    global _herb_native_installed
    if _herb_native_installed:
        return
    _herb_native_installed = True
    app = QApplication.instance()
    if app is not None and _herb_native_filter is not None:
        app.installNativeEventFilter(_herb_native_filter)


# ---- 药名联想输入框 ----
class _PopupDismissFilter(QObject):
    """应用级点击过滤器：点击输入框/弹窗之外区域时收起候选弹窗。"""

    def __init__(self, edit):
        super().__init__(edit)
        self._edit = edit

    def eventFilter(self, obj, event):
        if event.type() != QEvent.MouseButtonPress:
            return False
        ed = self._edit
        try:
            popup = ed._popup
            if not popup.isVisible():
                return False
        except RuntimeError:
            return False
        gpos = event.globalPosition().toPoint()
        edit_rect = QRect(ed.mapToGlobal(QPoint(0, 0)), ed.size())
        if edit_rect.contains(gpos) or popup.geometry().contains(gpos):
            return False
        ed.hide_popup()
        return False


class HerbNameEdit(QLineEdit):
    """带本地药材库联想的药名输入框。

    输入中文/全拼/首字母做模糊匹配，输入框下方弹出候选列表；键盘上下键预选，
    回车或点击将候选项填入文本框。候选弹窗为自绘 Popup 列表，键盘焦点始终
    留在输入框内。不使用 QCompleter——其原生键盘导航在部分环境下不可用，
    且对弹窗 setCurrentIndex 会把文本框内容改写为复合串，行为不可靠。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        _install_native_filter()           # (Windows) 保证输入法不吞方向键/回车
        self.installEventFilter(self)          # 接管弹窗可见时的键盘交互
        QApplication.instance().installEventFilter(_PopupDismissFilter(self))
        self._popup_row = -1                   # 当前预选行（-1 表示未预选）
        self._popup = QFrame(None, Qt.Popup)
        self._popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self._popup.setFocusPolicy(Qt.NoFocus)
        lay = QVBoxLayout(self._popup)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(0)
        self._list = QListWidget(self._popup)
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setMouseTracking(True)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.itemClicked.connect(self._pick_item)
        lay.addWidget(self._list)
        self.textEdited.connect(self._on_text_edited)
        # 编辑结束（回车或焦点离开）时，把"药名 拼音 首字母"复合串归一化为药名
        self.editingFinished.connect(self._normalize_composite)
        self.apply_theme()

    # ---- 弹窗显隐 ----
    def _on_text_edited(self, text):
        self._show_popup(text)

    def _show_popup(self, query):
        names = search(query)
        if not names:
            self._close_popup()
            return
        self._list.clear()
        for name in names:
            self._list.addItem(name)
        n = self._list.count()
        row_h = self._list.sizeHintForRow(0)
        if row_h <= 0:
            row_h = 30
        self._list.setFixedSize(max(self.width(), 220), min(n * row_h + 6, 250))
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if pos.y() + self._list.height() > avail.bottom():
                top = self.mapToGlobal(QPoint(0, 0)).y()
                pos.setY(max(avail.top(), top - self._list.height() - 4))
            if pos.x() + self._list.width() > avail.right():
                pos.setX(max(avail.left(), avail.right() - self._list.width()))
        self._popup.move(pos)
        self._popup_row = -1
        self._list.setCurrentRow(-1)
        self._popup.show()
        self._popup.raise_()

    def hide_popup(self):
        self._close_popup()

    def _close_popup(self):
        try:
            self._popup.hide()
        except RuntimeError:      # 应用退出时 C++ 对象可能已被销毁
            pass
        self._popup_row = -1

    def _maybe_hide_popup(self):
        try:
            visible = self._popup.isVisible()
        except RuntimeError:
            return
        if not visible:
            return
        # 弹窗显示瞬间会产生伪 FocusOut（焦点仍在输入框内），此时不收起
        if QApplication.focusWidget() is self:
            return
        # 鼠标正悬停在候选弹窗上（点击选中中）时不收起
        if self._popup.geometry().contains(QCursor.pos()):
            return
        self._close_popup()

    # ---- 填入 ----
    def _pick_item(self, item):
        if item is None:
            return
        self.setText(item.text())
        self.setCursorPosition(len(item.text()))
        self._close_popup()

    def _nav(self, delta):
        """在候选列表里移动预选行（delta 为 +1/-1）；未预选时方向决定落点。"""
        n = self._list.count()
        if not n:
            return
        row = self._popup_row
        if row < 0:
            row = 0 if delta > 0 else n - 1
        else:
            row = (row + delta) % n
        self._popup_row = row
        self._list.setCurrentRow(row)

    def _confirm(self):
        """把当前预选行填入输入框并关闭弹窗。"""
        n = self._list.count()
        if not n:
            return
        row = self._popup_row if self._popup_row >= 0 else 0
        self._pick_item(self._list.item(row))
        # 取消输入法未决的组字：防止回车后 IME 又把"药名 拼音 首字母"
        # 复合串提交追加回输入框，覆盖刚填入的药名。
        QGuiApplication.inputMethod().reset()

    def _normalize_composite(self):
        """把"药名 拼音 首字母"复合串归一化为药名。

        如 "人参 renshen rs" -> "人参"；首段不是合法药名则不处理。
        空串或纯药名不变。编辑结束（回车/焦点离开）时调用；
        若控件已被销毁需防护。
        """
        try:
            text = self.text()
        except RuntimeError:          # 控件已被销毁
            return
        token = text.split(None, 1)[0] if text.strip() else ""
        if token and token in HERB_NAMES and text != token:
            self.setText(token)
            self.setCursorPosition(len(token))

    # ---- 键盘交互 ----
    def eventFilter(self, obj, event):
        if obj is self:
            et = event.type()
            if et == QEvent.KeyPress and self._popup.isVisible():
                key = event.key()
                # 非 Windows 平台（macOS 等）无输入法吞键问题，直接走事件过滤。
                # Windows 上由原生过滤器先行拦截，此处作为兜底。
                if key in (Qt.Key_Down, Qt.Key_Up):
                    self._nav(1 if key == Qt.Key_Down else -1)
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._confirm()
                    return True
                if key == Qt.Key_Escape:
                    self._close_popup()
                    return True
            elif et == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                # 弹窗未显示时回车：若内容为"药名 拼音 首字母"复合串，归一化为药名
                self._normalize_composite()
            elif et == QEvent.FocusOut:
                self._maybe_hide_popup()
            elif et == QEvent.Hide:
                self._close_popup()
        return super().eventFilter(obj, event)

    # ---- 样式 ----
    def apply_theme(self):
        dark = is_dark(self)
        panel = theme.st("panel_bg", dark).name()
        border = theme.st("panel_border", dark).name()
        fg = theme.st("title_text", dark).name()
        accent = theme.st("accent", dark).name()
        hover = theme.st("nav_hover", dark).name()
        self._popup.setStyleSheet(
            f"QFrame {{ background: {panel}; border: 1px solid {border};"
            f" border-radius: 8px; }}"
            f"QListWidget {{ background: transparent; border: none;"
            f" outline: none; color: {fg}; font-size: 13px; }}"
            f"QListWidget::item {{ padding: 6px 10px; border-radius: 5px; }}"
            f"QListWidget::item:selected {{ background: {accent}; color: white; }}"
            f"QListWidget::item:hover {{ background: {hover}; }}")


# ---- 异步识别线程 ----
class RecognizeWorker(QThread):
    done = Signal(object)
    err = Signal(str)

    def __init__(self, client, data, parent=None):
        super().__init__(parent)
        self._client = client
        self._data = data

    def run(self):
        try:
            self._client.ensure_running()
            result = self._client.recognize(self._data)
            self.done.emit(result)
        except AIClientError as e:
            self.err.emit(str(e))
        except Exception as e:                      # noqa: BLE001
            self.err.emit(f"识别失败：{e}")


# ---- 单行药材输入 ----
class HerbRow(QWidget):
    remove_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_remove = None
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.name_edit = HerbNameEdit(self)
        self.name_edit.setPlaceholderText("药名，如：桂枝")
        h.addWidget(self.name_edit, 3)
        self.dose_edit = QLineEdit(self)
        self.dose_edit.setPlaceholderText("剂量，如：9")
        self.dose_edit.setFixedWidth(90)
        h.addWidget(self.dose_edit)
        self.unit_cb = QComboBox(self)
        for u in _UNITS:
            self.unit_cb.addItem(u, u)
        self.unit_cb.setFixedWidth(74)
        h.addWidget(self.unit_cb)
        self.del_btn = AnimatedButton("删除", self)
        self.del_btn.setObjectName("Danger")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setFixedWidth(56)
        self.del_btn.clicked.connect(lambda: self.remove_clicked.emit(self))
        h.addWidget(self.del_btn)

    def data(self) -> dict:
        return {
            "name": self.name_edit.text(),
            "dose": self.dose_edit.text(),
            "unit": self.unit_cb.currentData(),
        }


class RecognizePage(BasePage):

    def __init__(self, parent=None):
        super().__init__("药方识别", "逐项录入药材或粘贴整方，AI 分析药效与配伍")
        self.client = VirtualAIClient()
        self._worker = None
        self._fade_anim = None
        self._rows = []
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
        # 滚动时联想弹窗跟随定位不可靠，直接收起
        scroll.verticalScrollBar().valueChanged.connect(self._hide_popups)
        self.form_scroll = scroll

        form = QWidget(scroll)
        v = QVBoxLayout(form)
        v.setContentsMargins(2, 2, 6, 12)
        v.setSpacing(10)

        v.addWidget(section_label("逐项录入（至少录入一味药材）", form))
        v.addSpacing(2)
        self.rows_box = QWidget(form)
        self.rows_lay = QVBoxLayout(self.rows_box)
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        self.rows_lay.setSpacing(6)
        v.addWidget(self.rows_box)

        self.add_btn = AnimatedButton("＋ 添加一味药材", form)
        self.add_btn.setObjectName("AddSub")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_row)
        v.addWidget(self.add_btn)

        v.addSpacing(12)
        v.addWidget(section_label("整方文本（可选）", form))
        self.full_text = QPlainTextEdit(form)
        self.full_text.setPlaceholderText(
            "也可整方一次粘贴，如：桂枝9g 白芍9g 生姜3片 大枣4枚 炙甘草6g")
        self.full_text.setFixedHeight(120)
        v.addWidget(self.full_text)
        self.hint = QLabel("逐项录入与整方文本可任选其一，也可同时提供。", form)
        self.hint.setWordWrap(True)
        v.addWidget(self.hint)

        v.addSpacing(8)
        self.go_btn = AnimatedButton("识别", form)
        self.go_btn.setObjectName("CTA")
        self.go_btn.setCursor(Qt.PointingHandCursor)
        self.go_btn.clicked.connect(self._on_recognize)
        v.addWidget(self.go_btn)

        v.addStretch(1)
        scroll.setWidget(form)
        self._style_scroll(scroll)
        self._style_form(form)
        self._style_hint(False)
        self._add_row()          # 默认提供一行
        return scroll

    def _hide_popups(self):
        for row in self._rows:
            row.name_edit.hide_popup()

    def _add_row(self):
        # 药名为空的行不能作为新药材添加：先补全已有药名
        empty = [i for i, row in enumerate(self._rows, 1)
                 if not row.data()["name"].strip()]
        if empty:
            nums = "、".join(str(i) for i in empty)
            self.hint.setText(f"第 {nums} 行尚未填写药名，请先补全后再添加新药材。")
            self._style_hint(True)
            return
        row = HerbRow(self.rows_box)
        row.remove_clicked.connect(self._remove_row)
        self._rows.append(row)
        self.rows_lay.addWidget(row)
        self.hint.setText("逐项录入与整方文本可任选其一，也可同时提供。")
        self._style_hint(False)

    def _remove_row(self, row):
        if row in self._rows:
            self._rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        if not self._rows:
            self._add_row()      # 至少保留一行

    # ---- 第二阶段：结果页 ----
    def _build_result_page(self, parent):
        page = QWidget(parent)
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)

        bar = QHBoxLayout(); bar.setSpacing(10)
        self.status = QLabel("录入药材后点击「识别」")
        bar.addWidget(self.status, 1)
        self.export_btn = AnimatedButton("导出 PDF")
        self.export_btn.setObjectName("Ghost")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._do_export)
        bar.addWidget(self.export_btn)
        self.reset_btn = AnimatedButton("重置")
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

    def _fade_to(self, index):
        """表单↔结果两层之间做淡出淡入过渡，避免切换时生硬闪现。"""
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
        """切换结果页：顶部列出已录入药材 + 下方占位（等待识别）。"""
        self._last_data = data
        self._fade_to(1)
        self.cards = []
        while self.vlay.count() > 1:
            item = self.vlay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        info = SectionCard("待识别的药材", self.cw)
        herbs = [h for h in data.get("herbs", []) if h.get("name", "").strip()]
        if herbs:
            for h in herbs:
                info.add_herb_row(h["name"], h.get("dose", ""), h.get("unit", ""))
        if (data.get("full_text") or "").strip():
            info.add_text("整方文本：", role="sub")
            info.add_text(data["full_text"].strip(), role="body")
        self._append_card(info)

        ph = QLabel("正在识别药效，请稍候…")
        ph.setAlignment(Qt.AlignCenter)
        ph.setMinimumHeight(160)
        self._append_card(ph, is_placeholder=True)

        self.status.setText("正在识别…")
        self.export_btn.setEnabled(False)
        self._fit_content()

    def _append_card(self, card, is_placeholder=False):
        self.vlay.insertWidget(self.vlay.count() - 1, card)
        if not is_placeholder:
            self.cards.append(card)

    def _clear_placeholder(self):
        self.cards = []
        for i in range(self.vlay.count()):
            item = self.vlay.itemAt(i)
            w = item.widget()
            if w is not None and isinstance(w, QLabel) and w.alignment() == Qt.AlignCenter:
                item = self.vlay.takeAt(i)
                w.deleteLater()
                break
        first = self.vlay.itemAt(0).widget()
        if isinstance(first, SectionCard):
            self.cards.append(first)

    def _render_result(self, result):
        self._last_result = result
        self._clear_placeholder()
        self.status.setText(
            "识别完成 ✅" + ("  ·  模型：" + result.get("model", "") if result.get("model") else ""))
        self.export_btn.setEnabled(True)

        for h in result.get("herbs") or []:
            name = h.get("name", "")
            dose = f"{h.get('dose', '')}{h.get('unit', '')}"
            title = f"{name}  {dose}".strip()
            c = SectionCard(title, self.cw)
            nf = h.get("nature_flavor", "")
            meridian = h.get("meridian", "")
            if nf:
                c.add_text(f"性味：{nf}", role="body")
            if meridian:
                c.add_text(f"归经：{meridian}", role="body")
            if h.get("effects"):
                c.add_text(h["effects"], role="body")
            if h.get("notes"):
                c.add_text(f"注意：{h['notes']}", role="sub")
            self._append_card(c)

        c = SectionCard("配伍解析", self.cw)
        c.add_text(result.get("interaction", ""), role="body")
        self._append_card(c)

        c = SectionCard("煎服确认", self.cw)
        c.add_text(result.get("decoction", ""), role="body")
        self._append_card(c)

        c = SectionCard("备注", self.cw)
        c.add_text(result.get("warnings", ""), role="sub")
        self._append_card(c)
        self._fit_content()

    def _show_error(self, msg):
        self._clear_placeholder()
        self.status.setText("识别失败")
        err = SectionCard("识别失败", self.cw)
        err.add_text(msg, role="body")
        self._append_card(err)
        self.export_btn.setEnabled(False)
        self._fit_content()

    def _fit_content(self):
        self.cw.setMinimumHeight(self.vlay.sizeHint().height())

    # ---- 识别 ----
    def _collect(self) -> dict:
        herbs = []
        for row in self._rows:
            d = row.data()
            name = d["name"].strip()
            if name:
                herbs.append({**d, "name": name})
        return {
            "herbs": herbs,
            "full_text": self.full_text.toPlainText(),
        }

    def _on_recognize(self):
        if self._worker and self._worker.isRunning():
            return
        # 药名为空的行不能作为药材：完全空行忽略，填了剂量但缺药名的行需补全
        partial = [i for i, row in enumerate(self._rows, 1)
                   if not row.data()["name"].strip()
                   and row.data()["dose"].strip()]
        if partial:
            nums = "、".join(str(i) for i in partial)
            self.hint.setText(f"第 {nums} 行缺少药名，请补全药名或删除该行。")
            self._style_hint(True)
            return
        data = self._collect()
        if not data["herbs"] and not data["full_text"].strip():
            self.hint.setText("请至少录入一味药材，或粘贴整方文本。")
            self._style_hint(True)
            return
        self.go_btn.setEnabled(False)
        self._open_result(data)
        self._worker = RecognizeWorker(self.client, data, self)
        self._worker.done.connect(self._render_result)
        self._worker.err.connect(self._show_error)
        self._worker.finished.connect(lambda: self.go_btn.setEnabled(True))
        self._worker.start()

    # ---- 重置 ----
    def _on_reset(self):
        """清空已填药材与整方文本，并回到输入界面。"""
        for row in list(self._rows):
            self._remove_row(row)
        self.full_text.clear()
        self._style_hint(False)
        self.cards = []
        self._last_data = None
        self._last_result = None
        self.status.setText("录入药材后点击「识别」")
        self.export_btn.setEnabled(False)
        self._fade_to(0)

    # ---- 导出 PDF ----
    def _do_export(self):
        if not self._last_result:
            return
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        default = Config.DATA_DIR / f"识别_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF", str(default), "PDF 文件 (*.pdf)")
        if not path:
            return
        try:
            export_recognize_pdf(self._last_result, path)
            self.status.setText("已导出 ✅  " + path)
        except Exception as e:                      # noqa: BLE001
            self.status.setText(f"导出失败：{e}")

    # ---- 样式 ----
    def _style_scroll(self, scroll):
        dark = is_dark(self)
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

    def _style_hint(self, warn=False):
        dark = is_dark(self)
        accent = theme.st("accent", dark).name()
        sub = theme.st("sub_text", dark).name()
        self.hint.setStyleSheet(f"color: {accent if warn else sub}; background: transparent;")

    def _style_form(self, form):
        dark = is_dark(self)
        accent = theme.st("accent", dark)
        border = theme.st("field_border", dark).name()
        fg = theme.st("nav_text_act", dark).name()
        # nav_pill / nav_hover 为半透明色，必须用 HexArgb 保留透明度，否则会变不透明导致文字看不清
        hover = theme.st("nav_hover", dark).name(QColor.HexArgb)
        # 「添加一味药材」：两种模式都用明显区别于页面底色的实心灰，确保一眼可辨
        if dark:
            add_fill = "#333a45"
            add_hover = "#3f4754"
        else:
            add_fill = "#dde1e7"
            add_hover = "#c3c8d0"
        form.setStyleSheet(
            # 「添加一味药材」：柔和实心填充按钮（md 风格，非透明描边）
            f"QPushButton#AddSub {{ background: {add_fill}; color: {fg}; border: none;"
            f" border-radius: 9px; padding: 9px 14px; }}"
            f"QPushButton#AddSub:hover {{ background: {add_hover}; }}"
            # 「删除」：实心危险按钮
            f"QPushButton#Danger {{ background: #d64545; color: white; border: none;"
            f" border-radius: 9px; padding: 4px 0; }}"
            f"QPushButton#Danger:hover {{ background: #c13a3a; }}"
            f"QPushButton#Danger:disabled {{ background: #9aa0ab; }}"
            f"QPushButton#Ghost {{ background: transparent; color: {fg};"
            f" border: 1px dashed {border}; border-radius: 9px;"
            f" padding: 8px 14px; }}"
            f"QPushButton#Ghost:hover {{ background: {hover};"
            f" border-color: {accent.name()}; }}"
            f"QPushButton#Ghost:disabled {{ color: #9aa0ab; }}"
            f"QPushButton#CTA {{ background: {accent.name()}; color: white;"
            f" border: none; border-radius: 9px; height: 40px;"
            f" font-size: 14px; font-weight: bold; }}"
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
        self._style_hint()
        for row in self._rows:
            row.name_edit.apply_theme()
        for c in self.cards:
            c.refresh()
        self.update()
