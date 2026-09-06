import sys

from PySide6.QtCore import (
    Qt, QRectF, QRect, Signal, QPointF, QEasingCurve, QVariantAnimation,
    QAbstractAnimation, QTimer, QEvent,
)
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QPen, QPalette, QGuiApplication, QLinearGradient,
    QCursor,
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QGraphicsOpacityEffect, QSpacerItem,
)

from ..core import theme
from ..core.config import Config
from ..core.user_config import UserConfig
from .dark import is_dark
from .placeholder_page import PlaceholderPage
from .prescribe_page import PrescribePage
from .settings_page import SettingsPage
from .about_page import AboutPage

ZOOM_MS = 240
TITLE_BAR_H = 40       # macOS 顶栏高度（交通灯行）
_TITLE_BAR_WIN = 34    # Win11 顶栏高度
_DEF_MIN_W, _DEF_MIN_H = 900, 600


def bar_h() -> int:
    return _TITLE_BAR_WIN if theme.is_win() else TITLE_BAR_H


# 「导航」分栏上下留白
_SIDE_TOP_MAC, _SIDE_TOP_WIN = 4, 16
_SIDE_BOT_MAC, _SIDE_BOT_WIN = 6, 8


# ---- Windows 原生窗口 API ----
_WIN32 = sys.platform == "win32"
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_DONOTROUND = 1
_DWMWCP_ROUND = 2


def set_native_round(window, round_on: bool):
    if not _WIN32:
        return
    import ctypes
    try:
        val = ctypes.c_int(_DWMWCP_ROUND if round_on else _DWMWCP_DONOTROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(window.winId()), _DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def _force_frame_recalc(window):
    if not _WIN32:
        return
    import ctypes
    try:
        SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x0004, 0x0010, 0x0020
        ctypes.windll.user32.SetWindowPos(int(window.winId()), 0, 0, 0, 0, 0,
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    except Exception:
        pass


_WM_NCCALCSIZE = 0x0083
_WM_NCHITTEST = 0x0084
HT_LEFT, HT_RIGHT, HT_TOP, HT_TOPLEFT, HT_TOPRIGHT, HT_BOTTOM = 10, 11, 12, 13, 14, 15
HT_BOTTOMLEFT, HT_BOTTOMRIGHT = 16, 17
_RESIZE_EDGE = 6


def _edge_hit_test(window, lparam):
    dpr = max(1.0, window.devicePixelRatioF())
    x = _low_word(lparam) / dpr
    y = _high_word(lparam) / dpr
    r = window.geometry()
    left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()
    el, et = x >= left and x < left + _RESIZE_EDGE, y >= top and y < top + _RESIZE_EDGE
    er = x > right - _RESIZE_EDGE and x <= right
    eb = y > bottom - _RESIZE_EDGE and y <= bottom
    if et and el: return HT_TOPLEFT
    if et and er: return HT_TOPRIGHT
    if eb and el: return HT_BOTTOMLEFT
    if eb and er: return HT_BOTTOMRIGHT
    if el: return HT_LEFT
    if er: return HT_RIGHT
    if et: return HT_TOP
    if eb: return HT_BOTTOM
    return 0


def _low_word(v): return ctypes_int16(v & 0xFFFF)


def _high_word(v): return ctypes_int16((v >> 16) & 0xFFFF)


def ctypes_int16(u):
    return (u - 65536) if u >= 32768 else u


class TrafficLightButton(QWidget):
    """macOS 红黄绿灯窗口按钮。"""
    clicked_signal = Signal(int)
    _COLORS = {
        'red':    (0xFF5F57, 0xE1443C),
        'yellow': (0xFEBE2E, 0xDB9D0E),
        'green':  (0x28C840, 0x15A92E),
    }

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.host = None
        self._hover = False
        self.setFixedSize(14, 14)
        self.setCursor(Qt.PointingHandCursor)

    def is_lit(self):
        return True if self.host is None else self.host.window_active or self.host.cluster_hover

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked_signal.emit({'red': 0, 'yellow': 1, 'green': 2}[self.kind])
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        dark = is_dark(self)
        if self.is_lit():
            top, bottom = self._COLORS[self.kind]
            if self._hover:
                top = QColor(top).lighter(112); bottom = QColor(bottom).lighter(112)
            outline = QColor(0, 0, 0, 55)
        else:
            top, bottom = (QColor(192, 195, 201), QColor(168, 172, 179)) if not dark \
                else (QColor(104, 108, 116), QColor(84, 88, 96))
            outline = QColor(0, 0, 0, 30)
        r = QRectF(self.rect()).adjusted(1.2, 1.2, -1.2, -1.2)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, QColor(top)); g.setColorAt(1.0, QColor(bottom))
        p.setPen(QPen(outline, 0.7)); p.setBrush(g); p.drawEllipse(r)
        hp = QPainterPath()
        hp.moveTo(r.center().x(), r.top() + r.height() * 0.18)
        hp.arcTo(QRectF(r.left() + 1, r.top() + 1, r.width() - 2, r.height() - 2), 180, 200)
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 70 if self.is_lit() else 26))
        p.drawPath(hp)
        if self._hover or (self.host is not None and self.host.cluster_hover):
            self._draw_symbol(p, r.center())
        p.end()

    def _draw_symbol(self, p, c: QPointF):
        p.setPen(QPen(QColor(60, 20, 15, 210), 1.1, Qt.SolidLine, Qt.RoundCap))
        d = 2.6
        if self.kind == 'red':
            p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
            p.drawLine(QPointF(c.x() - d, c.y() + d), QPointF(c.x() + d, c.y() - d))
        elif self.kind == 'yellow':
            p.drawLine(QPointF(c.x() - d, c.y()), QPointF(c.x() + d, c.y()))
        elif self.kind == 'green':
            a, b, k = c.x(), c.y(), 1.3
            pa = QPainterPath()
            pa.moveTo(a - k, b + k * 1.4); pa.lineTo(a + k * 1.4, b - k)
            pa.lineTo(a + k, b - k * 1.5); pa.lineTo(a + k * 1.5, b - k)
            pa.moveTo(a + k, b - k * 1.4); pa.lineTo(a - k * 1.4, b + k)
            pa.lineTo(a - k * 1.5, b + k)
            p.setPen(QPen(QColor(20, 60, 20, 210), 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(pa)


class TrafficHeader(QWidget):
    traffic_signal = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TITLE_BAR_H)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.window_active = True
        self.cluster_hover = False
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(40)
        self._hover_timer.timeout.connect(self._poll_light_hover)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 0, 0)
        lay.setSpacing(8)
        self.lights = []
        for kind in ('red', 'yellow', 'green'):
            b = TrafficLightButton(kind)
            b.host = self
            b.clicked_signal.connect(self.traffic_signal)
            self.lights.append(b)
            lay.addWidget(b)
        self.app_title = QLabel(Config.APP_NAME)
        self.app_title.setObjectName("TitleLabel")
        lay.addSpacing(4)
        lay.addWidget(self.app_title)
        lay.addStretch(1)
        self.apply_style()

    def apply_style(self):
        win = theme.is_win()
        for b in self.lights:
            b.setVisible(not win)
        if win:
            self.stop_polling()
        else:
            self.start_polling()

    def start_polling(self):
        self._hover_timer.start()

    def stop_polling(self):
        self._hover_timer.stop()
        self.cluster_hover = False
        for b in self.lights:
            b._hover = False; b.update()

    def _poll_light_hover(self):
        gpos = QCursor.pos()
        cluster = QRect()
        for b in self.lights:
            if b.isVisible():
                gr = QRect(b.mapToGlobal(b.rect().topLeft()), b.size())
                cluster = cluster.united(gr.adjusted(-3, -3, 3, 3))
        hover = cluster.contains(gpos)
        if hover != self.cluster_hover:
            self.cluster_hover = hover
            for b in self.lights:
                b.update()
        for b in self.lights:
            if not b.isVisible():
                continue
            gr = QRect(b.mapToGlobal(b.rect().topLeft()), b.size())
            b._hover = gr.adjusted(-1, -1, 1, 1).contains(gpos)
            b.update()

    def set_window_active(self, active):
        if active != self.window_active:
            self.window_active = active
            for b in self.lights:
                b.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = (e.globalPosition().toPoint()
                          - self.window().frameGeometry().topLeft())

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and hasattr(self, '_drag') \
                and not self.window().isMaximized():
            self.window().move(e.globalPosition().toPoint() - self._drag)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.traffic_signal.emit(2)


class TopDragBar(QWidget):
    traffic_signal = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(bar_h())
        self.setAttribute(Qt.WA_TranslucentBackground)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = (e.globalPosition().toPoint()
                          - self.window().frameGeometry().topLeft())

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and hasattr(self, '_drag') \
                and not self.window().isMaximized():
            self.window().move(e.globalPosition().toPoint() - self._drag)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.traffic_signal.emit(2)


class NavButton(QWidget):
    """自绘侧边导航项。"""
    clicked_signal = Signal(str)

    def __init__(self, key, label, icon_path=None, parent=None):
        super().__init__(parent)
        self.key = key
        self.label = label
        self.active = False
        self._hover = False
        self.icon_path = icon_path
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active):
        if self.active != active:
            self.active = active; self.update()

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked_signal.emit(self.key)
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        dark = is_dark(self)
        r = theme.st("pill_radius", dark)
        pill = QRectF(self.rect()).adjusted(8, 3, -8, -3)
        if self.active:
            p.setBrush(theme.st("nav_pill", dark)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(pill, r, r)
        elif self._hover:
            p.setBrush(theme.st("nav_hover", dark)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(pill, r, r)
        self._draw_icon(p, dark)
        f = QFont(self.font()); f.setPointSize(10)
        col = theme.st("nav_text_act", dark) if self.active else theme.st("nav_text", dark)
        if self.active:
            f.setBold(True)
        p.setFont(f); p.setPen(col)
        p.drawText(QRectF(46.0, 0, self.width() - 58, self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.label)
        p.end()

    def _draw_icon(self, p, dark):
        col = theme.st("icon", dark)
        p.setPen(QPen(col, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        cw, x0, y0 = 9.0, 19.0, (self.height() - 9) / 2
        paths = {
            'grid': lambda: (
                p.drawRect(QRectF(x0, y0, cw, cw)),
                p.drawLine(QPointF(x0 + cw / 2, y0), QPointF(x0 + cw / 2, y0 + cw)),
                p.drawLine(QPointF(x0, y0 + cw / 2), QPointF(x0 + cw, y0 + cw / 2)),
            ),
            'doc': lambda: p.drawPath(self._doc_path(cw, x0, y0)),
            'gear': lambda: (
                p.drawEllipse(QPointF(x0 + cw / 2, y0 + cw / 2), 3.0, 3.0),
                p.drawEllipse(QPointF(x0 + cw / 2, y0 + cw / 2), 5.7, 5.7),
            ),
            'pill': lambda: p.drawRoundedRect(
                QRectF(x0 + 1, y0 + 1, cw - 2, cw - 2), (cw - 2) / 2, (cw - 2) / 2),
            'chat': lambda: self._chat_icon(p, cw, x0, y0),
            'info': lambda: self._info_icon(p, cw, x0, y0),
        }
        paths.get(self.icon_path or 'doc', paths['doc'])()

    def _info_icon(self, p, cw, x0, y0):
        """关于图标：圆环 + 内部「i」，与其他闭合轮廓图标保持一致。"""
        cx, cy = x0 + cw / 2, y0 + cw / 2
        p.drawEllipse(QPointF(cx, cy), 4.6, 4.6)
        p.drawLine(QPointF(cx, cy - 0.8), QPointF(cx, cy + 2.4))
        p.drawEllipse(QPointF(cx, cy - 2.6), 1.0, 1.0)

    def _chat_icon(self, p, cw, x0, y0):
        p.drawRoundedRect(QRectF(x0, y0, cw, cw - 3), 2.2, 2.2)
        dots = (x0 + cw / 2, y0 + (cw - 3) / 2 + 0.5)
        p.drawEllipse(QPointF(dots[0] - 2.0, dots[1]), 0.9, 0.9)
        p.drawEllipse(QPointF(dots[0], dots[1]), 0.9, 0.9)
        p.drawEllipse(QPointF(dots[0] + 2.0, dots[1]), 0.9, 0.9)
        p.drawLine(QPointF(x0 - 1, y0 + cw - 1), QPointF(x0 + cw - 2, y0 + cw - 3.5))

    @staticmethod
    def _doc_path(cw, x0, y0):
        path = QPainterPath()
        path.moveTo(x0, y0 + cw)
        path.lineTo(x0, y0 + 3)
        path.lineTo(x0 + cw * 0.5, y0 + 3)
        path.lineTo(x0 + cw * 0.7, y0 + cw * 0.35)
        path.lineTo(x0 + cw, y0 + cw * 0.35)
        path.lineTo(x0 + cw, y0 + cw)
        path.closeSubpath()
        return path


class Sidebar(QWidget):
    traffic_signal = Signal(int)
    navigate_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 14)
        lay.setSpacing(2)
        self.header = TrafficHeader()
        self.header.traffic_signal.connect(self.traffic_signal)
        lay.addWidget(self.header)
        self._sec_top = QSpacerItem(1, _SIDE_TOP_MAC)
        lay.addItem(self._sec_top)
        section = QLabel("导航")
        section.setObjectName("SectionLabel")
        section.setContentsMargins(19, 0, 0, 0)
        lay.addWidget(section)
        self._sec_bot = QSpacerItem(1, _SIDE_BOT_MAC)
        lay.addItem(self._sec_bot)
        self.nav_items = []
        for key, label, ip in [("prescribe", "药方开方", "pill"),
                               ("recognize", "药方识别", "doc"),
                               ("assistant", "AI助手", "chat"),
                               ("settings", "设置", "gear"),
                               ("about", "关于", "info")]:
            nb = NavButton(key, label, ip)
            nb.clicked_signal.connect(self.navigate_signal)
            self.nav_items.append(nb)
            lay.addWidget(nb)
        lay.addStretch(1)
        self.nav_items[0].set_active(True)

    def apply_style(self):
        win = theme.is_win()
        self.header.setVisible(not win)
        self._sec_top.changeSize(1, _SIDE_TOP_WIN if win else _SIDE_TOP_MAC)
        self._sec_bot.changeSize(1, _SIDE_BOT_WIN if win else _SIDE_BOT_MAC)
        self.layout().activate(); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        dark = is_dark(self)
        p.setPen(Qt.NoPen); p.setBrush(theme.st("sidebar_bg", dark))
        p.drawRect(self.rect()); p.end()


class PageStack(QStackedWidget):
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen); p.setBrush(theme.st("content_bg", is_dark(self)))
        p.drawRect(self.rect()); p.end()
        super().paintEvent(e)


class AppWindow(QWidget):
    """主窗口：左侧导航 + 页面堆栈 + 原生窗口外壳。"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(_DEF_MIN_W, _DEF_MIN_H)
        self.setWindowTitle(Config.APP_NAME)
        self.user_cfg = UserConfig()     # 用户偏好（风格/深浅色），启动时套用
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.traffic_signal.connect(self._on_traffic)
        self.sidebar.navigate_signal.connect(self.switch_page)
        root.addWidget(self.sidebar)

        self.stack = PageStack()
        self.pages = {}
        root.addWidget(self.stack, 1)

        self.pages["prescribe"] = PrescribePage()
        self.pages["recognize"] = PlaceholderPage("药方识别", "逐项输入药材与用量，AI 分析药效并展示")
        self.pages["assistant"] = PlaceholderPage("AI助手", "与 AI 对话，改进与调整药方，实时查看药方状态")
        self.pages["settings"] = SettingsPage(window=self)
        self.pages["about"] = AboutPage()
        for key, page in self.pages.items():
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.pages["prescribe"])

        self._topdrag = TopDragBar(self)
        self._topdrag.traffic_signal.connect(self._on_traffic)
        self._topdrag.setVisible(theme.is_mac())
        self._topdrag.raise_()

        self._opened = False
        self._zoomed = False
        self._normal_geom = None
        self._zoom_anim = None
        self._switch_anim = None
        self._switch_widgets = None

        # 恢复用户上次保存的界面风格与深浅色
        style = self.user_cfg.get("ui_style")
        theme_ = self.user_cfg.get("theme_mode")
        if style:
            self.set_style(style)
        if theme_:
            self.set_theme(theme_)

    def center_on_screen(self):
        """将窗口移动到所在屏幕可用区的中心（在 show() 之后调用）。"""
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        av = screen.availableGeometry()
        w = self.width(); h = self.height()
        if w < 10 or h < 10:                       # 尺寸未确定时按最小尺寸估算
            w = self.minimumWidth(); h = self.minimumHeight()
        x = av.center().x() - w // 2
        y = av.center().y() - h // 2
        # 不超过屏幕范围（多屏/小屏时避免移出可视区）
        x = max(av.left(), min(x, av.right() - w + 1))
        y = max(av.top(), min(y, av.bottom() - h + 1))
        self.move(x, y)

    def _recenter_after_layout(self):
        """风格切换后尺寸/边框已重新计算完成，重新把窗口放回屏幕中心。"""
        self.center_on_screen()

    # ---- 公开接口 ----
    def switch_page(self, key: str):
        """切换到指定页面（带滑入滑出动画）。"""
        for item in self.sidebar.nav_items:
            item.set_active(item.key == key)
        if key not in self.pages or self.stack.currentWidget() is self.pages[key]:
            return
        if self._switch_anim is not None:
            self._switch_anim.stop(); self._switch_anim = None
            self._reset_switch_widgets()
        old = self.stack.currentWidget()
        new = self.pages[key]
        self._switch_widgets = [old, new]
        SHIFT, MS = 30, 200
        old_eff = QGraphicsOpacityEffect(old)
        old.setGraphicsEffect(old_eff)
        a1 = QVariantAnimation(old); a1.setDuration(MS)
        a1.setStartValue(0.0); a1.setEndValue(1.0)
        a1.setEasingCurve(QEasingCurve.OutCubic)
        a1.valueChanged.connect(lambda t: (old.move(-int(SHIFT * t), 0),
                                           old_eff.setOpacity(1.0 - t)))

        def _play_in():
            new_eff = QGraphicsOpacityEffect(new)
            new.setGraphicsEffect(new_eff)
            new.move(SHIFT, 0); new_eff.setOpacity(0.0)
            self.stack.setCurrentWidget(new)
            a2 = QVariantAnimation(new); a2.setDuration(MS)
            a2.setStartValue(0.0); a2.setEndValue(1.0)
            a2.setEasingCurve(QEasingCurve.OutCubic)
            a2.valueChanged.connect(lambda t: (new.move(int(SHIFT * (1 - t)), 0),
                                               new_eff.setOpacity(t)))
            a2.finished.connect(self._finish_switch)
            a2.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._switch_anim = a2

        a1.finished.connect(lambda: (old.setGraphicsEffect(None), old.move(0, 0), _play_in()))
        a1.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._switch_anim = a1

    def _finish_switch(self):
        if self._switch_anim is not None:
            self._switch_anim = None
        self._reset_switch_widgets()

    def _reset_switch_widgets(self):
        for w in (self._switch_widgets or ()):
            if w is not None:
                w.setGraphicsEffect(None); w.move(0, 0)
        self._switch_widgets = None

    def notify_config_changed(self):
        """设置被保存后刷新所有页面。"""
        self._refresh_all()

    def _refresh_all(self):
        for p in self.pages.values():
            p.update()
            rf = getattr(p, "refresh_style", None)
            if rf:
                rf()

    # ---- 外观切换 ----
    def set_style(self, key: str):
        if not theme.set_style(key):
            return
        self.user_cfg.save(ui_style=key)     # 持久化用户界面风格
        QApplication.instance().setStyleSheet(apply_style())
        self._topdrag.setVisible(theme.is_mac())
        self.sidebar.apply_style(); self.sidebar.header.apply_style()
        self._relayout_overlays()
        _force_frame_recalc(self)
        QTimer.singleShot(0, self._adapt_min_size)
        # 风格切换会改变窗口尺寸/边框，重新定向到屏幕中心
        QTimer.singleShot(0, self._recenter_after_layout)
        self._refresh_all()

    def set_theme(self, key: str):
        if not theme.set_theme(key):
            return
        self.user_cfg.save(theme_mode=key)   # 持久化用户深浅色偏好
        QApplication.instance().setStyleSheet(apply_style())
        self._refresh_all()

    # ---- 窗口事件 ----
    def showEvent(self, e):
        super().showEvent(e)
        if not self._opened:
            self._opened = True
            QTimer.singleShot(0, lambda: set_native_round(self, True))
        handle = self.windowHandle()
        if handle is not None and not getattr(self, '_active_connected', False):
            handle.activeChanged.connect(self._on_window_active_changed)
            self._active_connected = True

    def _on_window_active_changed(self):
        if self.windowHandle() is not None:
            self.sidebar.header.set_window_active(self.windowHandle().isActive())

    def nativeEvent(self, eventType, message):
        if not _WIN32 or theme.is_win():
            return super().nativeEvent(eventType, message)
        try:
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            m = msg.message
            if m == _WM_NCCALCSIZE:
                return True, 0
            if m == _WM_NCHITTEST and not self.isMaximized():
                ht = _edge_hit_test(self, msg.lParam)
                if ht:
                    return True, ht
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def changeEvent(self, e):
        if e.type() == QEvent.WindowDeactivate:
            self.sidebar.header.set_window_active(False)
        elif e.type() == QEvent.WindowActivate:
            self.sidebar.header.set_window_active(True)
        elif e.type() == QEvent.WindowStateChange:
            self._sync_light_poll()
        super().changeEvent(e)

    def _sync_light_poll(self):
        if theme.is_win():
            return
        header = self.sidebar.header
        if self.isMinimized():
            header.stop_polling()
        else:
            header.start_polling()

    def _on_traffic(self, idx: int):
        if idx == 0:
            self.close()
        elif idx == 1:
            if self._zoom_anim:
                self._zoom_anim.stop()
            self.showMinimized()
        else:
            self._toggle_zoom()

    def _toggle_zoom(self):
        if _WIN32:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()
            return
        if self._zoomed:
            target = QRect(self._normal_geom) if self._normal_geom else self._fallback_rect()
            self._run_zoom(target, end_zoomed=False)
        else:
            self._normal_geom = self.frameGeometry()
            screen = QGuiApplication.screenAt(self._normal_geom.center()) or self.screen()
            self._run_zoom(screen.availableGeometry(), end_zoomed=True)

    def _fallback_rect(self):
        screen = self.screen()
        sg = screen.availableGeometry()
        w, h = min(1000, sg.width() - 60), min(680, sg.height() - 60)
        return QRect(sg.center().x() - w // 2, sg.center().y() - h // 2, w, h)

    def _run_zoom(self, target, end_zoomed):
        if self._zoom_anim:
            self._zoom_anim.stop()
        set_native_round(self, not end_zoomed)
        anim = QVariantAnimation(self); anim.setDuration(ZOOM_MS)
        anim.setStartValue(self.geometry()); anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(self.setGeometry)
        anim.finished.connect(lambda: self._finish_zoom(anim, end_zoomed, target))
        anim.start(); self._zoom_anim = anim

    def _finish_zoom(self, anim, end_zoomed, target):
        if anim is not self._zoom_anim:
            return
        self.setGeometry(target)
        self._zoomed = end_zoomed
        QTimer.singleShot(0, lambda: set_native_round(self, not self._zoomed))

    def resizeEvent(self, e):
        self._relayout_overlays(); super().resizeEvent(e)

    def _relayout_overlays(self):
        if theme.is_mac():
            self._topdrag.setGeometry(self.sidebar.width(), 0,
                                      self.width() - self.sidebar.width(), bar_h())
            self._topdrag.raise_()

    def _adapt_min_size(self):
        if theme.is_win():
            g = self.normalGeometry() if self.isMaximized() else self.geometry()
            self.setMinimumSize(max(1, g.width()), max(1, g.height()))
        else:
            self.setMinimumSize(_DEF_MIN_W, _DEF_MIN_H)


def apply_style(dark: bool = None):
    if dark is None:
        ov = theme.dark_override()
        if ov is not None:
            dark = ov
        else:
            app = QApplication.instance()
            dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    title_col = theme.st("title_text", dark).name()
    sub_col = theme.st("sub_text", dark).name()
    section_col = theme.st("section_text", dark).name()
    return f"""
    QWidget {{ font-family: "Microsoft YaHei UI"; color: {title_col}; }}
    #TitleLabel {{ font-size: 12px; color: {sub_col}; background: transparent; border: none; }}
    #SectionLabel {{ font-size: 10px; color: {section_col}; background: transparent; }}
    """