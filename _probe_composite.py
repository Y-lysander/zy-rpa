"""临时探针：复合串输入（人参 renshen rs）填充验证。"""
import sys
sys.path.insert(0, r"E:\items\zy_rpa")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from src.ui.recognize_page import RecognizePage
from src.data.herbs import search

print("search('人参 renshen rs'):", search("人参 renshen rs"), flush=True)
print("search('gui zhi'):", search("gui zhi"), flush=True)
print("search('gz'):", search("gz")[:3], flush=True)

app = QApplication(sys.argv)
page = RecognizePage()
page.resize(900, 640)
page.show()
app.processEvents()

edit = page._rows[0].name_edit
popup = edit._popup
edit.setFocus()
app.processEvents()

def type_sim(s):
    """逐字模拟输入（setText + 手动触发 textEdited）。"""
    for i in range(1, len(s) + 1):
        prefix = s[:i]
        edit.setText(prefix)
        edit.textEdited.emit(prefix)
        app.processEvents()
        print(f"  typed {prefix!r:20} popup={popup.isVisible()} rows={edit._list.count()}", flush=True)

print("== 逐字输入 '人参 renshen rs'", flush=True)
type_sim("人参 renshen rs")
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL1:", repr(edit.text()), flush=True)

print("== 粘贴 '人参 renshen rs'", flush=True)
edit.setText("")
app.clipboard().setText("人参 renshen rs")
edit.paste()
app.processEvents()
print(f"  pasted popup={popup.isVisible()} rows={edit._list.count()}", flush=True)
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL2:", repr(edit.text()), flush=True)

print("== 拼音 'gui zhi'", flush=True)
edit.setText("")
type_sim("gui zhi")
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL3:", repr(edit.text()), flush=True)

print("== 输入后按上下再回车", flush=True)
edit.setText("")
type_sim("人参 renshen rs")
QTest.keyClick(edit, Qt.Key_Down)
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL4:", repr(edit.text()), flush=True)

print("== 框内已有复合串、无弹窗直接回车", flush=True)
edit.setText("人参 renshen rs")
edit.hide_popup()   # 模拟无弹窗状态
app.processEvents()
print(f"  before: {edit.text()!r} popup={popup.isVisible()}", flush=True)
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL5:", repr(edit.text()), flush=True)

print("== 框内是合法药名无多余内容", flush=True)
edit.setText("人参")
edit.hide_popup()
QTest.keyClick(edit, Qt.Key_Return)
app.processEvents()
print("FILL6:", repr(edit.text()), flush=True)

print("DONE", flush=True)
