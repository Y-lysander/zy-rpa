"""内容页基础组件：自绘标题/副标题、可注入的内容面板、统一样式辅助，
以及跨页面复用的滚动区（丝滑滚动）与结果区段卡片。"""
from PySide6.QtCore import Qt, QAbstractAnimation, QEasingCurve, QPropertyAnimation, QRectF
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..core import theme
from .dark import is_dark

PAD = 30          # 左右留白
TOP = 28          # 标题顶部起点
PANEL_TOP = 72    # 面板相对标题的顶部偏移


class BasePage(QWidget):
    """内容页基类：绘制标题/副标题与页面底色，内容以 set_content 注入。"""

    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self._content = None

    def header_geometry(self):
        return False, PAD, TOP, self.width() - PAD * 2

    def set_content(self, widget):
        self._content = widget
        widget.setParent(self)
        self._layout_content()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dark = is_dark(self)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.st("content_bg", dark))
        p.drawRect(self.rect())
        _, left, top, w = self.header_geometry()

        tf = QFont(self.font()); tf.setPointSize(18); tf.setBold(True)
        p.setFont(tf)
        p.setPen(theme.st("title_text", dark))
        p.drawText(QRectF(left, top, w, 30), Qt.AlignVCenter | Qt.AlignLeft, self.title)

        sf = QFont(self.font()); sf.setPointSize(10)
        p.setFont(sf)
        p.setPen(theme.st("sub_text", dark))
        p.drawText(QRectF(left, top + 34, w, 22), Qt.AlignVCenter | Qt.AlignLeft, self.subtitle)
        p.end()

    def resizeEvent(self, e):
        self._layout_content()
        super().resizeEvent(e)

    def _layout_content(self):
        if self._content is None:
            return
        _, left, top, w = self.header_geometry()
        self._content.setGeometry(left, top + PANEL_TOP, w,
                                  max(120, self.height() - (top + PANEL_TOP + 16)))


def section_label(text, parent, bold=True):
    """生成分区标题 QLabel。"""
    lab = QLabel(text, parent)
    if bold:
        f = QFont(lab.font()); f.setBold(True); lab.setFont(f)
    col = theme.st("section_text", is_dark(parent)).name()
    lab.setStyleSheet(f"color: {col}; background: transparent;")
    return lab


def style_panel(widget, dark=None):
    """给承载表单控件的内容面板设置一套跟随主题的 QSS，返回实际暗/明模式。"""
    dark = is_dark(widget) if dark is None else dark
    text = theme.st("title_text", dark).name()
    sub = theme.st("sub_text", dark).name()
    accent = theme.st("accent", dark).name()
    border = theme.st("panel_border", dark).name()
    bg = theme.st("panel_bg", dark).name()
    fg = theme.st("nav_text_act", dark).name()
    hover = theme.st("nav_hover", dark).name()
    widget.setStyleSheet(
        f"QLabel {{ color: {text}; background: transparent; }}"
        f"QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{"
        f" background: {bg}; color: {fg}; border: 1px solid {border};"
        f" border-radius: 6px; padding: 5px 9px;"
        f" selection-background-color: {accent}; selection-color: white; }}"
        f"QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover {{"
        f" border: 1px solid {accent}; }}"
        f"QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{"
        f" border: 1px solid {accent}; }}"

        f"QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,"
        f" QSpinBox:disabled {{ color: #9aa0ab; background: {hover}; }}"

        # 下拉框本体 + 三角箭头 + 弹出项列表
        f"QComboBox {{ background: {bg}; color: {fg}; border: 1px solid {border};"
        f" border-radius: 6px; padding: 5px 26px 5px 9px; }}"
        f"QComboBox:hover, QComboBox:focus {{ border-color: {accent}; }}"
        f"QComboBox:disabled {{ color: #9aa0ab; }}"
        f"QComboBox::drop-down {{ subcontrol-origin: padding;"
        f" subcontrol-position: top right; width: 24px; border: none;"
        f" border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}"
        f"QComboBox::down-arrow {{ image: none; width: 0; height: 0;"
        f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
        f" border-top: 5px solid {fg}; margin-top: -2px; }}"
        f"QComboBox QAbstractItemView {{ background: {bg}; color: {fg};"
        f" border: 1px solid {border}; border-radius: 7px;"
        f" outline: 0; padding: 4px; }}"
        f"QComboBox QAbstractItemView::item {{ min-height: 24px;"
        f" padding: 5px 10px; border-radius: 5px; }}"
        f"QComboBox QAbstractItemView::item:hover {{ background: {hover}; }}"
        f"QComboBox QAbstractItemView::item:selected {{ background: {accent};"
        f" color: white; }}"
        f"QComboBox QScrollBar:vertical {{ background: transparent; width: 8px;"
        f" margin: 2px; }}"
        f"QComboBox QScrollBar::handle:vertical {{ background: {hover};"
        f" border-radius: 3px; min-height: 20px; }}"
        f"QComboBox QScrollBar::add-line:vertical,"
        f" QComboBox QScrollBar::sub-line:vertical {{ height: 0; }}"

        f"QPushButton {{ background: {accent}; color: white; border: none;"
        f" border-radius: 6px; padding: 6px 16px; }}"
        f"QPushButton:disabled {{ background: #9aa0ab; }}"
        f"QPushButton#Ghost {{ background: transparent; color: {fg};"
        f" border: 1px solid {border}; }}"
        f"QPushButton#Ghost:hover {{ background: {hover}; }}"
        f"QPushButton#Danger {{ background: #d64545; }}"
        f"QCheckBox, QRadioButton {{ color: {text}; background: transparent; }}"
        f"QProgressBar {{ background: {bg}; border: 1px solid {border};"
        f" border-radius: 6px; text-align: center; color: {fg}; }}"
        f"QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}"
    )
    return dark


# ---------------------------------------------------------------------------
# 跨页面共享：丝滑滚动区 + 结果区段卡片
# ---------------------------------------------------------------------------
class SmoothScrollArea(QScrollArea):
    """滚轮驱动垂直滚动，内容向目标位置平滑过渡（OutCubic）。

    连续滚动时取消前一段动画并重定向到新目标，避免"一跳一跳"的生硬感。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = None

    def _stop(self):
        a = self._anim
        self._anim = None
        if a is None:
            return
        # 动画可能已因 finished 被 deleteLater 销毁，捕获该竞态
        try:
            a.stop()
        except RuntimeError:
            pass
        try:
            a.deleteLater()
        except RuntimeError:
            pass

    def _anim_finished(self, a):
        if self._anim is a:
            self._anim = None
        try:
            a.deleteLater()
        except RuntimeError:
            pass

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy == 0:
            return
        bar = self.verticalScrollBar()
        start = bar.value()
        target = start - dy
        target = max(bar.minimum(), min(bar.maximum(), target))
        if target == start:
            return
        self._stop()
        a = QPropertyAnimation(bar, b"value", self)
        a.setDuration(260)
        a.setStartValue(start)
        a.setEndValue(target)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.finished.connect(lambda: self._anim_finished(a))
        self._anim = a
        a.start()
        e.accept()


class SectionCard(QWidget):
    """结果区段：强调色标题 + 一条细横线作装饰 + 内容行，支持一键主题刷新。

    不使用圆角卡片盒子，避免"卡片套卡片"，仅以标题/细线/内容排版。
    """

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._rows = []                      # (widget, role)
        v = QVBoxLayout(self)
        v.setContentsMargins(2, 0, 2, 0)
        v.setSpacing(7)
        self.title_lab = QLabel(title)
        self.title_lab.setWordWrap(True)
        f = QFont(self.title_lab.font()); f.setPointSize(11); f.setBold(True)
        self.title_lab.setFont(f)
        v.addWidget(self.title_lab)
        self.line = QWidget(self)
        self.line.setFixedHeight(1)
        v.addWidget(self.line)
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
        self.title_lab.setStyleSheet(
            f"color: {theme.st('accent', dark).name()}; background: transparent;")
        self.line.setStyleSheet(
            f"background: {theme.st('panel_border', dark).name()}; border: none;")
        for lab, role in self._rows:
            self.refresh_row(lab, role)
        self.update()