"""内容页基础组件：自绘标题/副标题、可注入的内容面板，以及统一样式辅助。"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget

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