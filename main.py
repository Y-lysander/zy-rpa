"""智能中药开方系统 —— 图形界面入口。

在项目根目录（含 main.py 与 src/）下运行：
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from src.core.config import Config
from src.ui.window import AppWindow, apply_style


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(Config.APP_NAME)
    app.setStyleSheet(apply_style())
    win = AppWindow()
    win.show()
    win.center_on_screen()          # 初始窗口放在屏幕中心
    sys.exit(app.exec())


if __name__ == "__main__":
    main()