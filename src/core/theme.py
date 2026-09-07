"""界面主题/风格的设置实现逻辑。

集中管理界面风格的注册表、当前状态与切换规则，并提供配色访问器。
UI 层（设置页与各控件）仅按需读取，避免把风格配置逻辑散落在界面代码里。
"""
from PySide6.QtGui import QColor


def _mk(q):
    return q if isinstance(q, QColor) else QColor(q)


# ---- 界面风格注册表：macOS / Win11 ----
STYLES = {
    "macos": {
        "label": "macOS 风格",
        "sidebar_bg":  (_mk("#ececef"), _mk("#191b1f")),
        "content_bg":  (_mk("#f6f6f7"), _mk("#222428")),
        "titlebar_bg": (_mk("#ececef"), _mk("#191b1f")),
        "panel_bg":    (_mk("#f0f0f1"), _mk("#202226")),
        "title_text":  (_mk("#1d1f26"), _mk("#ffffff")),
        "sub_text":    (_mk("#84888f"), _mk("#a0a0a0")),
        "placeholder": (_mk("#a5a9b0"), _mk("#6a6e76")),
        "nav_text":    (_mk("#3a3d45"), _mk("#9c9ca4")),
        "nav_text_act":(_mk("#1d1f26"), _mk("#ffffff")),
        "section_text":(_mk("#8a8e97"), _mk("#6f7480")),
        "nav_pill":    (QColor(64, 68, 78, 22), QColor(255, 255, 255, 26)),
        "nav_hover":   (QColor(120, 130, 150, 18), QColor(120, 130, 150, 20)),
        "icon":        (QColor(120, 130, 150), QColor(164, 174, 194)),
        "accent":      (QColor(88, 118, 255), QColor(120, 150, 255)),
        "bubble_bg":   (QColor(231, 232, 238), QColor(43, 47, 55)),
        "panel_border":(QColor(0, 0, 0, 16), QColor(255, 255, 255, 14)),
        "field_bg":    (_mk("#fbfbfc"), _mk("#2a2e33")),
        "field_border":(QColor(18, 26, 40, 22), QColor(255, 255, 255, 20)),
        "pill_radius": 11,
        "panel_radius": 12,
        "traffic": "mac",
    },
    # Win11 与 macOS 配色基本一致——风格差异收敛在顶栏
    "win11": {
        "label": "Win11 系统风格",
        "sidebar_bg":  (_mk("#ececef"), _mk("#191b1f")),
        "content_bg":  (_mk("#f6f6f7"), _mk("#222428")),
        "titlebar_bg": (_mk("#e9e9ec"), _mk("#1e2024")),
        "panel_bg":    (_mk("#f0f0f1"), _mk("#202226")),
        "title_text":  (_mk("#1d1f26"), _mk("#ffffff")),
        "sub_text":    (_mk("#84888f"), _mk("#a0a0a0")),
        "placeholder": (_mk("#a5a9b0"), _mk("#6a6e76")),
        "nav_text":    (_mk("#3a3d45"), _mk("#9c9ca4")),
        "nav_text_act":(_mk("#1d1f26"), _mk("#ffffff")),
        "section_text":(_mk("#8a8e97"), _mk("#6f7480")),
        "nav_pill":    (QColor(64, 68, 78, 22), QColor(255, 255, 255, 26)),
        "nav_hover":   (QColor(120, 130, 150, 18), QColor(120, 130, 150, 20)),
        "icon":        (QColor(120, 130, 150), QColor(164, 174, 194)),
        "accent":      (QColor(88, 118, 255), QColor(120, 150, 255)),
        "bubble_bg":   (QColor(231, 232, 238), QColor(43, 47, 55)),
        "panel_border":(QColor(0, 0, 0, 16), QColor(255, 255, 255, 14)),
        "field_bg":    (_mk("#fbfbfc"), _mk("#2a2e33")),
        "field_border":(QColor(18, 26, 40, 22), QColor(255, 255, 255, 20)),
        "pill_radius": 12,
        "panel_radius": 12,
        "traffic": "win",
    },
}

CURRENT_STYLE = "macos"

# 设置页展示用元数据（独立于配色，仅供 UI 读取）
STYLE_KEYS = ("macos", "win11")
STYLE_LABEL = {"macos": "macOS 风格", "win11": "Win11 系统风格"}
STYLE_SUBTITLE = {
    "macos": "左上红绿灯 · 彩色圆形按钮",
    "win11": "右上控制键 · 扁平符号按钮",
}


# 设置页展示用元数据（独立于配色，仅供 UI 读取）
THEMES = ("system", "light", "dark")
THEME_LABEL = {"system": "跟随系统", "light": "浅色", "dark": "深色"}
THEME_SUBTITLE = {
    "system": "跟随操作系统的深浅色",
    "light": "始终使用浅色外观",
    "dark": "始终使用深色外观",
}

CURRENT_THEME = "system"


def style_name() -> str:
    """返回当前启用的风格 key"""
    return CURRENT_STYLE


def theme_mode_name() -> str:
    """返回当前深浅色模式 key"""
    return CURRENT_THEME


def set_theme(key: str) -> bool:
    """切换深浅色模式；成功返回 True，未知模式返回 False。"""
    global CURRENT_THEME
    if key not in THEMES:
        return False
    CURRENT_THEME = key
    return True


def dark_override():
    """返回当前深浅色模式的强制值；None 表示跟随系统。

    UI 层据此决定明暗：'dark' -> True，'light' -> False，
    'system' -> None（交由系统调色板判定）。
    """
    if CURRENT_THEME == "dark":
        return True
    if CURRENT_THEME == "light":
        return False
    return None


def is_win() -> bool:
    """当前是否为 Win11 风格（语义化判断，替代各处魔法字符串比较）"""
    return CURRENT_STYLE == "win11"


def is_mac() -> bool:
    """当前是否为 macOS 风格"""
    return CURRENT_STYLE == "macos"


def set_style(key: str) -> bool:
    """切换当前界面风格；成功返回 True，未知风格返回 False。"""
    global CURRENT_STYLE
    if key not in STYLES:
        return False
    CURRENT_STYLE = key
    return True


def st(key, dark: bool):
    """按当前风格取配色：值为 (light, dark) 返回对应 QColor，标量为值本身"""
    v = STYLES[CURRENT_STYLE][key]
    if isinstance(v, tuple):
        return v[1] if dark else v[0]
    return v