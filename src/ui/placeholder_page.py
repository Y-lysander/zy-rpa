"""占位页：PRD 功能实现前的过渡页。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton

from .pagekit import BasePage, style_panel
from .dark import is_dark
from ..core import theme


class PlaceholderPage(BasePage):
    """尚未实现的 PRD 功能占位页面。"""

    def __init__(self, title, subtitle, note="该功能仍在规划中，待细节确认后实现。",
                 parent=None):
        super().__init__(title, subtitle)
        self.note = note
        self.panel = panel = QWidget(self)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(28, 40, 28, 40)
        lay.setSpacing(12)
        lay.addStretch(1)
        self.note_lab = QLabel(self.note, panel)
        self.note_lab.setWordWrap(True)
        self.note_lab.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.note_lab)
        lay.addStretch(1)
        panel.setLayout(lay)
        style_panel(panel)
        self.set_content(panel)

    def refresh(self):
        pass

    def refresh_style(self):
        style_panel(self.panel)
        self.update()