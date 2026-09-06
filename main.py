"""智能中药开方系统 —— 图形界面入口。

在项目根目录（含 main.py 与 src/）下运行：
    python main.py
"""
import os
import sys
import ctypes

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.core.config import Config
from src.ui.window import AppWindow, apply_style


def _icon_path():
    """程序图标路径（兼容 PyInstaller 打包与源码运行）。"""
    try:
        base = sys._MEIPASS          # PyInstaller 打包后的临时目录
    except AttributeError:
        base = str(Config.ROOT)
    return os.path.join(base, "icon.ico")


def _set_taskbar_icon(window, icon_path):
    """Windows 任务栏图标：向窗口发送 WM_SETICON（需在窗口显示后调用）。"""
    if sys.platform != "win32" or not os.path.exists(icon_path):
        return
    try:
        hwnd = int(window.winId())
        hicon = ctypes.windll.user32.LoadImageW(
            None, icon_path, 1,      # IMAGE_ICON
            0, 0, 0x10               # LR_LOADFROMFILE
        )
        if hicon:
            # WM_SETICON：0 小图标（标题栏/任务栏），1 大图标（Alt+Tab）
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 0, hicon)
            ctypes.windll.user32.SendMessageW(hwnd, 0x80, 1, hicon)
    except Exception:
        pass


def main():
    # 1. 设置 AppUserModelID（必须在 QApplication 创建之前），
    #    保证任务栏图标正确分组与显示，不退化回默认 Python 图标。
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ZhongYi.RPA.Medicine.1")

    app = QApplication(sys.argv)
    app.setApplicationName(Config.APP_NAME)

    # 2. 设置应用与窗口图标
    icon_path = _icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setStyleSheet(apply_style())
    win = AppWindow()
    if os.path.exists(icon_path):
        win.setWindowIcon(QIcon(icon_path))
    win.show()
    win.center_on_screen()          # 初始窗口放在屏幕中心

    # 3. Windows 任务栏图标（窗口显示后）
    _set_taskbar_icon(win, icon_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
