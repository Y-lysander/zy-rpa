"""设置页：应用外观 + AI 供应商/API Key 配置（AI 部分为占位，待实现确认）。"""
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.config import Config
from .pagekit import BasePage, section_label, style_panel


class SettingsPage(BasePage):

    def __init__(self, window=None, parent=None):
        super().__init__("设置", "应用外观 · AI 供应商与密钥")
        self.window = window
        self._syncing = False      # 同步期间屏蔽 currentIndexChanged 触发套用/保存
        self._build()

    def _build(self):
        self.panel = panel = QWidget(self)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(28, 16, 28, 16)
        lay.setSpacing(12)

        lay.addWidget(section_label("应用外观", panel))
        row = QHBoxLayout(); row.setSpacing(12)
        row.addWidget(QLabel("界面风格", panel))
        self.style_cb = QComboBox(panel)
        for k in theme.STYLE_KEYS:
            self.style_cb.addItem(theme.STYLE_LABEL[k], k)
        row.addWidget(self.style_cb)
        row.addSpacing(18)
        row.addWidget(QLabel("深浅色", panel))
        self.theme_cb = QComboBox(panel)
        for k in theme.THEMES:
            self.theme_cb.addItem(theme.THEME_LABEL[k], k)
        row.addWidget(self.theme_cb)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addWidget(section_label("AI 模型配置", panel))
        hint = QLabel("供应商接入、模型选择与 API Key 将在后续版本提供，敬请期待。", panel)
        hint.setWordWrap(True)
        lay.addWidget(hint)
        pay = QHBoxLayout(); pay.setSpacing(12)
        pay.addWidget(QLabel("供应商", panel))
        self.provider_cb = QComboBox(panel)   # 占位：具体供应商清单待确认
        self.provider_cb.addItem("（待接入）")
        pay.addWidget(self.provider_cb)
        pay.addSpacing(18)
        pay.addWidget(QLabel("API Key", panel))
        self.api_key_edit = QLineEdit(panel)
        self.api_key_edit.setPlaceholderText("API Key（待接入）")
        self.api_key_edit.setEnabled(False)
        pay.addWidget(self.api_key_edit, 1)
        lay.addLayout(pay)

        lay.addStretch(1)
        style_panel(panel)
        self.set_content(panel)
        # 套用持久化的外观偏好（显示当前值）
        self.style_cb.setCurrentIndex(self.style_cb.findData(theme.style_name()))
        self.theme_cb.setCurrentIndex(self.theme_cb.findData(theme.theme_mode_name()))
        self.style_cb.currentIndexChanged.connect(self._apply_appearance)
        self.theme_cb.currentIndexChanged.connect(self._apply_appearance)

    def refresh_style(self):
        style_panel(self.panel)
        self.update()

    def sync_from_config(self):
        """读取当前主题配置并同步下拉框选中项（仅更新显示，不触发套用/保存）。"""
        self._syncing = True
        try:
            self.style_cb.setCurrentIndex(self.style_cb.findData(theme.style_name()))
            self.theme_cb.setCurrentIndex(self.theme_cb.findData(theme.theme_mode_name()))
        finally:
            self._syncing = False

    def _apply_appearance(self):
        if self.window is None or self._syncing:
            return
        style = self.style_cb.currentData()
        theme_ = self.theme_cb.currentData()
        if style:
            self.window.set_style(style)
        if theme_:
            self.window.set_theme(theme_)