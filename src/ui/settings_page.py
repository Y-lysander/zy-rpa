"""设置页：应用外观 + AI 供应商/API Key 配置（新增/管理中/删除，自动保存）。"""
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.user_config import UserConfig
from .pagekit import AnimatedButton, BasePage, section_label, style_panel
from .model_wizard import ModelWizard


class SettingsPage(BasePage):

    def __init__(self, window=None, parent=None):
        super().__init__("设置", "应用外观 · AI 供应商与密钥")
        self.window = window
        self._ucfg = UserConfig()
        self._syncing = False      # 同步期间屏蔽 currentIndexChanged 触发套用/保存
        self._build()

    # ---- 构建 ----
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
        # 该区域随是否已配置模型而切换：未配置 -> 添加按钮；已配置 -> 管理/删除
        self.ai_area = QWidget(panel)
        self.ai_lay = QVBoxLayout(self.ai_area)
        self.ai_lay.setContentsMargins(0, 0, 0, 0)
        self.ai_lay.setSpacing(10)
        self._build_ai_empty()
        lay.addWidget(self.ai_area)

        lay.addStretch(1)
        style_panel(panel)
        self.set_content(panel)
        # 套用持久化的外观偏好（显示当前值）
        self.style_cb.setCurrentIndex(self.style_cb.findData(theme.style_name()))
        self.theme_cb.setCurrentIndex(self.theme_cb.findData(theme.theme_mode_name()))
        self.style_cb.currentIndexChanged.connect(self._apply_appearance)
        self.theme_cb.currentIndexChanged.connect(self._apply_appearance)

    def _rebuild_ai_content(self):
        """重建 AI 配置区内容容器（整体替换，彻底清空嵌套布局与控件）。

        避免逐项删除时漏掉嵌套 QHBoxLayout 里的控件，导致重复/重叠。
        """
        old = getattr(self, "_ai_content", None)
        if old is not None:
            old.setParent(None)
            old.deleteLater()
        self._ai_content = QWidget(self.ai_area)
        self.ai_content_lay = QVBoxLayout(self._ai_content)
        self.ai_content_lay.setContentsMargins(0, 0, 0, 0)
        self.ai_content_lay.setSpacing(10)
        self.ai_lay.addWidget(self._ai_content)

    def _build_ai_empty(self):
        """未配置模型：显示「添加模型」按钮，点击弹出配置向导。"""
        self._rebuild_ai_content()
        lay = self.ai_content_lay
        tip = QLabel("尚未配置 AI 模型。点击下方按钮，通过向导接入首个模型供应商"
                     "（DeepSeek），即可使用 AI 开方 / 识别 / 助手功能。", self._ai_content)
        tip.setWordWrap(True)
        lay.addWidget(tip)
        btn = AnimatedButton("添加模型")
        btn.setObjectName("Ghost")
        btn.setFixedWidth(120)
        btn.clicked.connect(self._on_add_model)
        lay.addWidget(btn)
        lay.addSpacing(4)

    def _build_ai_managed(self, provider, model, api_key):
        """已配置模型：显示供应商/模型/密钥，并给出管理与删除入口。"""
        self._rebuild_ai_content()
        lay = self.ai_content_lay
        info = QLabel(f"供应商：{provider}    模型：{model}", self._ai_content)
        info.setWordWrap(True)
        lay.addWidget(info)
        key_row = QHBoxLayout(); key_row.setSpacing(12)
        key_row.addWidget(QLabel("API Key", self._ai_content))
        masked = api_key[:6] + "…" + api_key[-4:] if len(api_key) > 10 else "…" + api_key[-4:]
        self.key_edit = QLineEdit(masked, self._ai_content)
        self.key_edit.setReadOnly(True)
        key_row.addWidget(self.key_edit, 1)
        lay.addLayout(key_row)
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        manage_btn = QPushButton("更换模型", self._ai_content)
        manage_btn.setObjectName("Ghost")
        manage_btn.clicked.connect(self._on_manage)
        btn_row.addWidget(manage_btn)
        del_btn = QPushButton("删除配置", self._ai_content)
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

    # ---- 状态刷新 ----
    def refresh_ai_state(self):
        """根据 UserConfig 当前配置刷新 AI 配置区。"""
        self._ucfg.load()
        key = (self._ucfg.get("api_key") or "").strip()
        if not key:
            self._build_ai_empty()
        else:
            self._build_ai_managed(
                self._ucfg.get("ai_provider") or "deepseek",
                self._ucfg.get("ai_model") or "deepseek-v4-flash",
                key)
        style_panel(self.panel)
        self._ai_area_dark()

    def _ai_area_dark(self):
        # 让下拉折行等样式跟随主题（由 style_panel 统一处理即可）
        pass

    # ---- 事件 ----
    def _dlg_parent(self):
        """返回用于承载对话框的顶层窗口。"""
        if self.window is not None:
            return self.window.window()
        return None

    def _on_add_model(self):
        wiz = ModelWizard(self._dlg_parent())
        if wiz.exec() == ModelWizard.Accepted:
            self.refresh_ai_state()

    def _on_manage(self):
        wiz = ModelWizard(self._dlg_parent())
        if wiz.exec() == ModelWizard.Accepted:
            self.refresh_ai_state()

    def _on_delete(self):
        ret = QMessageBox.question(
            self._dlg_parent(), "删除模型配置",
            "确定要删除当前 AI 模型配置吗？删除后需重新添加才能使用 AI 功能。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        self._ucfg.save(ai_provider="deepseek", ai_model="deepseek-v4-flash",
                        api_key="")
        self.refresh_ai_state()

    def refresh_style(self):
        style_panel(self.panel)
        self.refresh_ai_state()

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