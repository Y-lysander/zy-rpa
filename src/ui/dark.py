"""深浅色判定辅助：供 window 与各页面共享，避免循环导入。"""
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from ..core import theme


def is_dark(widget=None):
    """当前是否为深色主题：设置强制值优先，否则用控件/应用调色板判定。"""
    ov = theme.dark_override()
    if ov is not None:
        return ov
    src = widget if widget is not None else QApplication.instance()
    return src.palette().color(QPalette.ColorRole.Window).lightness() < 128