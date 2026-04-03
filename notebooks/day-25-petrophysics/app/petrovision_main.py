from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from controllers.main_controller import MainController  # noqa: E402


class PetroVisionMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = ROOT_DIR / "ui" / "PetroVisionPro.ui"
        uic.loadUi(str(ui_path), self)
        self.controller = MainController(self)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PetroVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
