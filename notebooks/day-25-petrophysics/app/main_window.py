from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow
from app.controller import Controller
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        ui_path = os.path.join("app", "ui", "petrophysicsWorkstaton.ui")
        uic.loadUi(ui_path, self)

        self.controller = Controller(self)

        if hasattr(self, "loadButton"):
            self.loadButton.clicked.connect(self.controller.load_las)

        if hasattr(self, "computeButton"):
            self.computeButton.clicked.connect(self.controller.run_petrophysics)
