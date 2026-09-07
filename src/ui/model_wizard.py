"""AI 模型配置向导：引导用户填写并校验 API Key（适配当前应用主题）。

从 TokenPeek 项目的首次运行向导复制并精简而来：
- 仅配置「第一个模型」环节（当前仅支持 DeepSeek 单供应商）；
- 去除「是否添加第二模型」相关页面；
- 沿用本应用的主题配色（theme.st + is_dark）与 AnimatedButton。
校验通过后写入用户级 UserConfig（~/zy_rpa/config.json）。
"""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRect, Qt, QThread, Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QStackedWidget,
    QVBoxLayout, QWidget, QApplication,
)

from ..core import theme
from ..core.config import Config
from ..core.deepseek_client import DeepSeekClient
from ..core.user_config import UserConfig
from .dark import is_dark
from .pagekit import AnimatedButton


def _is_dark():
    return is_dark(QApplication.activeWindow() or QApplication.instance()
                   .activeModalWidget())


def _label_color():
    """根据当前主题返回标签文字颜色。"""
    return theme.st("title_text", _is_dark()).name()


def _primary_stylesheet():
    a = theme.st("accent", False)
    hover = a.darker(112).name()
    pressed = a.darker(124).name()
    disabled = a.lighter(165).name()
    return f"""
        QPushButton {{ font-size: 13px; font-weight: bold; color: white;
            background-color: {a.name()}; border: none; border-radius: 8px; }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:pressed {{ background-color: {pressed}; }}
        QPushButton:disabled {{ background-color: {disabled}; }}
    """


def _ghost_stylesheet():
    dark = _is_dark()
    border = theme.st("panel_border", dark).name()
    hover = theme.st("nav_hover", dark).name()
    accent = theme.st("accent", False).name()
    text = theme.st("nav_text_act", dark).name()
    return f"""
        QPushButton {{ font-size: 12px; color: {text}; background: transparent;
            border: 1px solid {border}; border-radius: 6px; }}
        QPushButton:hover {{ border: 1px solid {accent}; color: {accent};
            background: {hover}; }}
    """


def _alpha_name(color, alpha):
    c = QColor(color)
    c.setAlpha(alpha)
    return c.name(QColor.HexArgb)


class _VerifyThread(QThread):
    """API Key 校验线程（DeepSeek）。"""

    success_signal = Signal(bool, str)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        try:
            ok, err = DeepSeekClient(self.api_key.strip()).verify_api_key()
        except Exception as e:                     # noqa: BLE001
            ok, err = False, str(e)
        self.success_signal.emit(ok, err or "")


class SlidingStackedWidget(QStackedWidget):
    """支持水平滑动切换的堆叠窗口（OutCubic，复制自 TokenPeek）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 300
        self._animating = False

    def slide_to(self, target, direction):
        if self._animating or self.currentWidget() is target:
            return
        self._animating = True
        width, height = self.width(), self.height()
        start_pos = width if direction == "left" else -width
        target.setGeometry(start_pos, 0, width, height)
        target.show()
        target.raise_()

        cur_end = -width if direction == "left" else width
        self._cur_anim = QPropertyAnimation(self.currentWidget(), b"geometry")
        self._cur_anim.setDuration(self._duration)
        self._cur_anim.setStartValue(self.currentWidget().geometry())
        self._cur_anim.setEndValue(QRect(cur_end, 0, width, height))

        self._tgt_anim = QPropertyAnimation(target, b"geometry")
        self._tgt_anim.setDuration(self._duration)
        self._tgt_anim.setStartValue(QRect(start_pos, 0, width, height))
        self._tgt_anim.setEndValue(QRect(0, 0, width, height))
        for a in (self._cur_anim, self._tgt_anim):
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._cur_anim.finished.connect(
            lambda: self._finish(target))
        self._cur_anim.start()
        self._tgt_anim.start()

    def _finish(self, target):
        self._animating = False
        self.setCurrentWidget(target)
        target.setGeometry(0, 0, self.width(), self.height())

    def slide_next(self, widget):
        self.slide_to(widget, "left")


class WelcomePage(QWidget):
    """欢迎页面。"""

    start_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 40, 30, 30)

        title = QLabel("配置 AI 模型")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold;"
                            f" color: {theme.st('accent', False).name()};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(20)

        desc = QLabel("为了使用 AI 智能开方、药材识别与中医助手，请先接入模型供应商。"
                      "当前支持 DeepSeek，填写你的 API Key 即可开始。")
        desc.setStyleSheet(f"font-size: 13px; color:"
                           f" {theme.st('sub_text', _is_dark()).name()};")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(25)

        for t in ("· API Key 仅保存在本地", "· 保存前自动校验有效性",
                  "· 随时随地可在设置中更换模型"):
            f = QLabel(t)
            f.setStyleSheet(f"font-size: 12px; color:"
                            f" {theme.st('sub_text', _is_dark()).name()};"
                            f" padding: 4px 0;")
            f.setAlignment(Qt.AlignCenter)
            layout.addWidget(f)

        layout.addStretch()
        start = AnimatedButton("开始配置")
        start.setFixedSize(160, 40)
        start.setStyleSheet(_primary_stylesheet())
        start.clicked.connect(self.start_clicked.emit)
        layout.addWidget(start, alignment=Qt.AlignCenter)


class ModelConfigPage(QWidget):
    """模型配置页面：选择模型 + 输入 API Key + 校验保存。"""

    next_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.verify_thread = None
        self.setup_ui()

    def _field_ss(self):
        dark = _is_dark()
        line = theme.st("sub_text", dark)
        idle = _alpha_name(line, 120)
        hover = _alpha_name(line, 200)
        accent = theme.st("accent", False).name()
        fg = theme.st("nav_text_act", dark).name()
        border = theme.st("panel_border", dark).name()
        panel_bg = theme.st("panel_bg", dark).name()
        nav_hover = theme.st("nav_hover", dark).name()
        return f"""
            QLineEdit, QComboBox {{ background: transparent; color: {fg};
                border: none; border-bottom: 1px solid {idle}; border-radius: 0;
                padding: 7px 2px 8px 2px; font-size: 13px; }}
            QLineEdit:hover, QComboBox:hover {{ border-bottom: 1px solid {hover}; }}
            QLineEdit:focus, QComboBox:focus {{ border-bottom: 2px solid {accent}; }}
            QComboBox::drop-down {{ subcontrol-origin: padding;
                subcontrol-position: top right; width: 24px; border: none; }}
            QComboBox::down-arrow {{ image: none; width: 0; height: 0;
                border-left: 4px solid transparent; border-right: 4px solid transparent;
                border-top: 5px solid {fg}; margin-top: -2px; }}
            QComboBox QAbstractItemView {{ background: {panel_bg}; color: {fg};
                border: 1px solid {border}; border-radius: 7px; outline: 0;
                padding: 4px; }}
            QComboBox QAbstractItemView::item {{ min-height: 26px;
                padding: 5px 10px; border-radius: 5px; }}
            QComboBox QAbstractItemView::item:hover {{ background: {nav_hover}; }}
            QComboBox QAbstractItemView::item:selected {{ background: {accent};
                color: white; }}
        """

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("模型配置")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold;"
                            f" color: {theme.st('accent', False).name()};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("请选择模型并输入 DeepSeek 的 API Key。Key 仅保存在本地，"
                      "保存前会自动校验有效性。")
        desc.setStyleSheet(f"font-size: 12px; color:"
                           f" {theme.st('sub_text', _is_dark()).name()};")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(20)

        model_label = QLabel("模型")
        model_label.setStyleSheet(f"font-size: 12px; color: {_label_color()};")
        layout.addWidget(model_label)

        self.model_combo = QComboBox(self)
        for p in Config.MODEL_PROVIDERS:
            for m in p["models"]:
                self.model_combo.addItem(m, m)
        layout.addWidget(self.model_combo)

        layout.addSpacing(10)
        key_label = QLabel("API Key")
        key_label.setStyleSheet(f"font-size: 12px; color: {_label_color()};")
        layout.addWidget(key_label)

        self.key_edit = QLineEdit(self)
        self.key_edit.setPlaceholderText("sk-…（DeepSeek API Key）")
        layout.addWidget(self.key_edit)

        self.status_label = QLabel(self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        layout.addStretch()

        button_widget = QWidget(self)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(15)
        self.next_button = AnimatedButton("校验并保存")
        self.next_button.setFixedSize(160, 40)
        self.next_button.setStyleSheet(_primary_stylesheet())
        self.next_button.clicked.connect(self.verify_and_continue)
        button_layout.addStretch()
        button_layout.addWidget(self.next_button)
        layout.addWidget(button_widget)
        layout.addSpacing(10)

        self._apply_field_style()

    def _apply_field_style(self):
        self.model_combo.setStyleSheet(self._field_ss())
        self.key_edit.setStyleSheet(self._field_ss())

    def verify_and_continue(self):
        key = self.key_edit.text().strip()
        if not key:
            self.show_status("请输入 API Key", is_error=True)
            return
        self.next_button.setText("校验中…")
        self.next_button.setEnabled(False)
        self.show_status("正在校验 API Key…", is_info=True)
        self.verify_thread = _VerifyThread(key, self)
        self.verify_thread.success_signal.connect(self._on_verify)
        self.verify_thread.start()

    def _on_verify(self, success, error):
        self.next_button.setText("校验并保存")
        self.next_button.setEnabled(True)
        if success:
            self.save_config()
            self.next_clicked.emit()
        else:
            self.show_status(f"校验失败：{error}", is_error=True)

    def save_config(self):
        """校验通过后把配置持久化到 UserConfig。"""
        UserConfig().save(
            ai_provider="deepseek",
            ai_model=self.model_combo.currentData() or Config.DEFAULT_MODEL,
            api_key=self.key_edit.text().strip())

    def show_status(self, message, is_error=False, is_info=False):
        self.status_label.setText(message)
        self.status_label.show()
        dark = _is_dark()
        if is_error:
            bg, text = _alpha_name("#c92a2a", 40 if dark else 26), \
                ("#ff9c9c" if dark else "#c92a2a")
        elif is_info:
            bg, text = _alpha_name("#1971c2", 40 if dark else 26), \
                ("#7cc0ff" if dark else "#1971c2")
        else:
            bg, text = _alpha_name("#2b8a3e", 40 if dark else 26), \
                ("#7fe0a0" if dark else "#2b8a3e")
        self.status_label.setStyleSheet(
            f"font-size: 11px; color: {text}; background-color: {bg};"
            f" padding: 5px; border-radius: 4px;")


class CompletePage(QWidget):
    """完成页面。"""

    finish_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 40, 30, 30)

        title = QLabel("配置完成")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold;"
                            f" color: {theme.st('accent', False).name()};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(15)

        desc = QLabel("已成功接入 DeepSeek 模型，现在可以开始使用 AI 智能开方、"
                      "药材识别与中医助手功能了。")
        desc.setStyleSheet(f"font-size: 14px; color:"
                           f" {theme.st('title_text', _is_dark()).name()};")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(30)

        hint = QLabel("可在「设置」中随时更换模型或删除配置")
        hint.setStyleSheet(f"font-size: 12px; color:"
                           f" {theme.st('sub_text', _is_dark()).name()};")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()

        finish = AnimatedButton("完成")
        finish.setFixedSize(160, 40)
        finish.setStyleSheet(_primary_stylesheet())
        finish.clicked.connect(self.finish_clicked.emit)
        layout.addWidget(finish, alignment=Qt.AlignCenter)
        layout.addSpacing(20)


class ModelWizard(QDialog):
    """AI 模型配置向导（单模型，DeepSeek）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置 AI 模型")
        self.setFixedSize(440, 420)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stacked = SlidingStackedWidget(self)
        self.welcome = WelcomePage()
        self.config = ModelConfigPage()
        self.complete = CompletePage()
        for page in (self.welcome, self.config, self.complete):
            self.stacked.addWidget(page)

        self.welcome.start_clicked.connect(self._go_config)
        self.config.next_clicked.connect(self._go_complete)
        self.complete.finish_clicked.connect(self.accept)
        layout.addWidget(self.stacked)

        dark = _is_dark()
        self.setStyleSheet(
            f"QDialog {{ background-color:"
            f" {theme.st('content_bg', dark).name()}; }}"
            f"QLabel {{ background: transparent; }}")

    def _go_config(self):
        self.config._apply_field_style()
        self.stacked.slide_next(self.config)

    def _go_complete(self):
        self.stacked.slide_next(self.complete)