"""AI 助手页：对话式聊天界面。

上方为消息列表（用户右侧主题色气泡 / AI 左侧面板色气泡），下方为输入区；
完整对话历史随每次请求发送给服务端（服务端注入中药系统提示词）。

深浅色热切换：所有颜色均取自 theme token 并在 refresh_style() 重建。
"""
from __future__ import annotations

from PySide6.QtCore import (
    Qt, QAbstractAnimation, QEasingCurve, QPropertyAnimation, QThread,
    QTimer, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QTextOption
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QScrollArea, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget,
)

from ..core import theme
from ..core.ai_client import AIClient, AIClientError
from ..core.md_parser import md_to_html
from .dark import is_dark
from .pagekit import (
    AnimatedButton, AutoGrowTextEdit, BasePage, SmoothScrollArea, style_panel,
)


# ---- 异步对话线程 ----
class ChatWorker(QThread):
    done = Signal(object)
    err = Signal(str)

    def __init__(self, client, messages, parent=None):
        super().__init__(parent)
        self._client = client
        self._messages = messages

    def run(self):
        try:
            raw = self._client.fetch_chat(list(self._messages))
            reply = raw.get("reply", "") if isinstance(raw, dict) else raw
            self.done.emit(reply)
        except AIClientError as e:
            self.err.emit(str(e))
        except Exception as e:                      # noqa: BLE001
            self.err.emit(f"对话失败：{e}")


# ---- 输入框：Enter 发送，Shift+Enter 换行，高度随内容自适应 ----
class ChatInputEdit(AutoGrowTextEdit):
    submit = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, max_rows=5)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) \
                and not (e.modifiers() & Qt.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(e)


# ---- 聊天气泡 ----
class ChatBubble(QTextEdit):
    """聊天气泡（只读 QTextEdit）。

    QLabel 的 wordWrap 在布局中的高度计算不可靠（文本会被裁剪），
    这里用 QTextEdit + 文档布局精确计算尺寸：宽度按内容自适应、长文封顶，
    高度由 documentLayout().documentSize() 确定，短消息窄、长消息宽。
    """

    PAD_W = 24          # QSS 左右 padding（12+12）
    PAD_H = 18          # QSS 上下 padding（8+8）+ 少量余量
    MARGIN = 6          # document().setDocumentMargin() 值（左右各 6px）
    HEADROOM = 8        # 额外余量，防“位置足够却触边多折行”

    def __init__(self, text, role, max_w, parent=None, markdown=False):
        super().__init__(parent)
        self.role = role
        self._markdown = markdown
        self.setReadOnly(True)
        self._has_table = markdown and "|" in text   # 用原始 Markdown 判断，勿用 toPlainText()
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.document().setDocumentMargin(self.MARGIN)
        # QTextEdit 视口默认用调色板 Base 自绘，会盖住 QSS 背景，需关掉
        self.viewport().setAutoFillBackground(False)
        f = self.font(); f.setPixelSize(13); self.setFont(f)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if markdown:
            self.setHtml(md_to_html(text))
        else:
            self.setPlainText(text)
        self.refresh()
        self.set_max_width(max_w)

    def set_max_width(self, max_w):
        """窗口缩放时重设封顶宽度，按新宽度重排。"""
        self._max_w = max_w
        self._apply_size()

    def _natural_width(self, doc):
        """取文档“不折行”时的真实宽度（按实际加载字体量取）。

        fontMetrics 用的是系统默认字体度量，可能与运行时中文字体不同导致
        宽度偏小、单行内容被多余折行；这里直接用文档排版自身的最大行宽，
        能自动适配用户系统的真实字体。
        """
        doc.setTextWidth(1 << 24)          # 超宽，避免折行
        best = 0
        block = doc.begin()
        while block.isValid():
            try:
                maxw = int(block.layout().maximumWidth())
            except (AttributeError, RuntimeError):
                maxw = 0
            if maxw > best:
                best = maxw
            block = block.next()
        return best

    def _apply_size(self):
        doc = self.document()
        if self._has_table:
            w = self._max_w
        else:
            natural = int(self._natural_width(doc))
            # 需同时容纳：文字本身宽度 + 文档左右 margin + QSS 左右 padding
            w = min(self._max_w, natural + self.PAD_W + 2 * self.MARGIN + self.HEADROOM)
        self.setFixedWidth(w)
        doc.setTextWidth(max(w - self.PAD_W, 1))
        h = int(doc.documentLayout().documentSize().height())
        self.setFixedHeight(max(h + self.PAD_H, 28))

    def refresh(self):
        dark = is_dark(self)
        if self.role == "user":
            bg = theme.st("accent", dark).name()
            fg = "#ffffff"
            radius = ("border-top-left-radius: 12px; border-top-right-radius: 12px;"
                      " border-bottom-left-radius: 12px; border-bottom-right-radius: 4px;")
        else:
            bg = theme.st("bubble_bg", dark).name()
            fg = theme.st("title_text", dark).name()
            radius = ("border-top-left-radius: 12px; border-top-right-radius: 12px;"
                      " border-bottom-left-radius: 4px; border-bottom-right-radius: 12px;")
        accent = theme.st("accent", dark).name()
        self.setStyleSheet(
            f"QTextEdit {{ background: {bg}; color: {fg}; border: none;"
            f" {radius} padding: 8px 12px; font-size: 13px;"
            f" selection-background-color: {accent}; selection-color: white; }}")


class AssistantPage(BasePage):

    def __init__(self, parent=None):
        super().__init__("AI助手", "与 AI 对话，解答中药、方剂与症状调理等问题")
        self.client = AIClient()
        self._worker = None
        self._messages = []        # 对话历史 [{"role", "content"}]
        self._bubbles = []         # 已挂载的气泡控件（不含占位）
        self._typing = None        # 「正在思考…」占位气泡
        self._scroll_anim = None   # 进行中的滚动动画（防止多动画竞争）
        self._build()
        self._append_ai(
            "你好，我是中药 AI 助手。可以为您解答药材功效、方剂配伍、症状调理等问题。")

    # ---- 构建 ----
    def _build(self):
        self.panel = QWidget(self)
        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(2, 2, 6, 4)
        lay.setSpacing(10)

        self.chat_scroll = scroll = SmoothScrollArea(self.panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_cw = QWidget()
        self.chat_lay = QVBoxLayout(self.chat_cw)
        self.chat_lay.setContentsMargins(4, 4, 4, 8)
        self.chat_lay.setSpacing(12)
        self.chat_lay.addStretch(1)
        scroll.setWidget(self.chat_cw)
        lay.addWidget(scroll, 1)

        input_box = QWidget(self.panel)
        irow = QHBoxLayout(input_box)
        irow.setContentsMargins(0, 0, 0, 0)
        irow.setSpacing(10)
        self.input_edit = ChatInputEdit(input_box)
        self.input_edit.setPlaceholderText("请输入您的问题，Enter 发送，Shift+Enter 换行")
        self.input_edit.textChanged.connect(self._update_send_state)
        self.input_edit.submit.connect(self._on_send)
        irow.addWidget(self.input_edit, 1)
        self.send_btn = AnimatedButton("发送", input_box)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setFixedWidth(88)
        self.send_btn.setFixedHeight(40)
        self.send_btn.clicked.connect(self._on_send)
        irow.addWidget(self.send_btn, 0, Qt.AlignBottom)
        lay.addWidget(input_box)

        style_panel(self.panel)
        self.set_content(self.panel)
        self._style_scroll(scroll)
        self._style_send_btn()
        self._update_send_state()

    # ---- 消息渲染 ----
    def _append_bubble(self, text, role):
        bubble = ChatBubble(text, role, self._max_bubble_w(), self.chat_cw,
                            markdown=(role == "ai"))
        align = Qt.AlignRight if role == "user" else Qt.AlignLeft
        self.chat_lay.insertWidget(self.chat_lay.count() - 1, bubble, 0, align)
        self._bubbles.append(bubble)
        self._fade_in(bubble)
        self._relayout_bubble_widths()
        self._scroll_to_bottom()
        return bubble

    def _append_user(self, text):
        return self._append_bubble(text, "user")

    def _append_ai(self, text):
        return self._append_bubble(text, "ai")

    def _fade_in(self, widget):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        eff.setOpacity(0.0)
        anim = QVariantAnimation(widget)
        anim.setDuration(180)
        anim.setStartValue(0.0); anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(eff.setOpacity)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _remove_typing(self):
        if self._typing is None:
            return
        w = self._typing
        self._typing = None
        self.chat_lay.removeWidget(w)
        if w in self._bubbles:
            self._bubbles.remove(w)
        w.setParent(None)
        w.deleteLater()

    def _scroll_to_bottom(self):
        QTimer.singleShot(0, self._do_scroll_bottom)

    def _stop_scroll_anim(self):
        a = self._scroll_anim
        self._scroll_anim = None
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

    def _on_scroll_finished(self, a):
        if self._scroll_anim is a:
            self._scroll_anim = None
        try:
            a.deleteLater()
        except RuntimeError:
            pass

    def _do_scroll_bottom(self, prev_max=-1, unchanged=0):
        # 先激活布局并刷新 widget 几何，让新增气泡的尺寸计入内容高度
        lay = self.chat_cw.layout()
        if lay is not None:
            lay.activate()
            lay.invalidate()
        self.chat_cw.adjustSize()

        bar = self.chat_scroll.verticalScrollBar()
        cur = bar.maximum()

        # 滚动范围还在随新气泡增长，等待其稳定（连续两轮不变）后再滚，
        # 避免新气泡尺寸未计入时把半途位置当成目标（若以 chat_cw 高度为准会偏差）。
        if cur != prev_max or unchanged < 2:
            QTimer.singleShot(
                0, lambda m=cur, u=unchanged + (0 if cur != prev_max else 1):
                self._do_scroll_bottom(m, u))
            return

        if cur <= 0 or cur <= bar.value():
            return
        # 停掉上一次未完成的滚动动画，避免多动画竞争导致停不到底
        self._stop_scroll_anim()
        anim = QPropertyAnimation(bar, b"value", self)
        anim.setDuration(260)
        anim.setStartValue(bar.value())
        anim.setEndValue(cur)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: self._on_scroll_finished(anim))
        self._scroll_anim = anim
        anim.start()

    def _max_bubble_w(self):
        vp = self.chat_scroll.viewport()
        if vp is None:
            return 480
        return max(200, int(vp.width() * 0.72))

    def _relayout_bubble_widths(self):
        max_w = self._max_bubble_w()
        for b in self._bubbles:
            b.set_max_width(max_w)

    # ---- 发送 ----
    def _on_send(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.input_edit.clear()
        self._ask(text, show_user_bubble=True)

    def _ask(self, text, show_user_bubble=True):
        """把一条用户消息发给服务端并显示回复气泡。

        show_user_bubble=False 时不渲染用户气泡（用于「询问AI助手」把方子
        自动注入提示词，只展示 AI 一次分析结果），但该消息仍计入对话历史，
        供后续追问保持上下文。
        """
        if self._worker and self._worker.isRunning():
            return
        if show_user_bubble:
            self._append_user(text)
        self._messages.append({"role": "user", "content": text})
        self._typing = self._append_ai("正在思考…")
        self._update_send_state()
        self._worker = ChatWorker(self.client, list(self._messages), self)
        self._worker.done.connect(self._on_reply)
        self._worker.err.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ---- 外部触发：带着方子内容新开一段对话 ----
    def start_prescription_chat(self, prescription_prompt: str):
        """清空旧对话，新开一段；把方子内容注入提示词顶部并自动询问一次。

        自动询问不显示用户气泡，直接展示 AI 返回的一次分析结果；
        方子作为消息计入历史，之后由用户继续自由追问。
        """
        self._new_conversation()
        prompt = (prescription_prompt or "").strip()
        if not prompt:
            return
        self._ask(prompt + "\n\n看看这个方子，帮我分析分析。", show_user_bubble=False)

    def _new_conversation(self):
        """清空当前对话气泡与历史，回到新对话状态。"""
        if self._worker and self._worker.isRunning():
            return
        while self.chat_lay.count() > 1:      # 保留末尾 stretch
            item = self.chat_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._messages = []
        self._bubbles = []
        self._typing = None
        self._append_ai(
            "你好，我是中药 AI 助手。可以为您解答药材功效、方剂配伍、症状调理等问题。")

    def _on_reply(self, reply):
        reply = (reply or "").strip()
        self._messages.append({"role": "assistant", "content": reply})
        self._remove_typing()
        self._append_ai(reply or "（AI 未返回内容）")

    def _on_error(self, msg):
        self._remove_typing()
        self._append_ai(f"请求失败：{msg}")

    def _on_worker_done(self):
        self._worker = None
        self._update_send_state()
        self.input_edit.setFocus()

    def _update_send_state(self):
        busy = self._worker is not None and self._worker.isRunning()
        empty = not self.input_edit.toPlainText().strip()
        self.send_btn.setEnabled(not busy and not empty)

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

    def _style_send_btn(self):
        dark = is_dark(self)
        accent = theme.st("accent", dark)
        self.send_btn.setStyleSheet(
            f"QPushButton {{ background: {accent.name()}; color: white; border: none;"
            f" border-radius: 9px; font-size: 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {accent.darker(112).name()}; }}"
            f"QPushButton:disabled {{ background: #9aa0ab; }}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout_bubble_widths()

    # ---- 主题热切换 ----
    def refresh_style(self):
        style_panel(self.panel)
        self._style_scroll(self.chat_scroll)
        self._style_send_btn()
        for b in self._bubbles:
            b.refresh()
        self.update()
