"""关于页：简介、版本与免责声明。"""
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QTextBrowser

from ..core.config import Config
from .pagekit import BasePage, section_label, style_panel

ABOUT = """
<h2>{name}</h2>
<p>智能化的中药/药方<b>开方</b>与<b>识别</b>系统：本地图形界面接入云端 AI 模型，
根据症状/病史/用药情况自动生成中药方、识别药方药效，并提供 AI 对话助手辅助调整与改进。</p>
<p>所有生成内容基于云端大模型，给出方剂与药效解读，供中医师参考。</p>

<h3>免责声明</h3>
<p>本程序生成的药方与药效判断由 AI 模型产出，<b>不构成医疗建议</b>。
实际用药请务必由具备资质的中医师辨证审核，对 AI 输出存疑时应以专家意见为准。</p>
"""


class AboutPage(BasePage):

    def __init__(self, parent=None):
        super().__init__("关于", "智能中药开方系统 · 版本与说明")
        self.panel = panel = QWidget(self)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(4, 4, 4, 4)
        browser = QTextBrowser(panel)
        browser.setOpenExternalLinks(True)
        browser.setHtml(ABOUT.format(name=Config.APP_NAME))
        lay.addWidget(browser)
        panel.setLayout(lay)
        style_panel(panel)
        self.set_content(panel)

    def refresh_style(self):
        style_panel(self.panel)
        self.update()