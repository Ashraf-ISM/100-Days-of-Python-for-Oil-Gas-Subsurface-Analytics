import sys
from PyQt5 import QtWidgets, QtCore, QtGui

class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.spin = QtWidgets.QSpinBox()
        layout.addWidget(self.spin)
        
        self.btn = QtWidgets.QPushButton("Focus")
        self.btn.clicked.connect(self.check_focus)
        layout.addWidget(self.btn)
        
        # action
        self.act = QtWidgets.QAction("Copy", self)
        self.act.setShortcut(QtGui.QKeySequence.Copy)
        self.act.triggered.connect(self.do_copy)
        self.addAction(self.act)

    def check_focus(self):
        self.spin.setFocus()
        focus = QtWidgets.QApplication.focusWidget()
        print("Focus is:", type(focus))
        print("Has copy?", hasattr(focus, "copy"))

    def do_copy(self):
        focus = QtWidgets.QApplication.focusWidget()
        print("Ctrl+C pressed. Focus is:", type(focus))
        print("Has copy?", hasattr(focus, "copy"))

app = QtWidgets.QApplication(sys.argv)
w = Window()
w.show()
w.check_focus()
QtCore.QTimer.singleShot(1000, app.quit)
app.exec_()
