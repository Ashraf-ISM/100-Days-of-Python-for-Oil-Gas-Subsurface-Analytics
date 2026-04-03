from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "mainwindow.ui"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from controllers.main_controller import MainController  # noqa: E402


class PetroVisionMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = UI_DIR / UI_FILE
        uic.loadUi(str(ui_path), self)
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is not None:
            self.setCentralWidget(tab_widget)
        self._connect_tab_switches()
        self.controller = MainController(self)

    def _connect_tab_switches(self) -> None:
        """Wire toolbar/menu actions and dashboard buttons to tab indices."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None:
            return

        def connect_action(action_name: str, idx: int) -> None:
            action = getattr(self, action_name, None)
            if action is None:
                return
            action.triggered.connect(
                lambda checked=False, tab_idx=idx: tab_widget.setCurrentIndex(tab_idx)
            )

        def connect_button(button_name: str, idx: int) -> None:
            button = getattr(self, button_name, None)
            if button is None:
                return
            button.clicked.connect(
                lambda checked=False, tab_idx=idx: tab_widget.setCurrentIndex(tab_idx)
            )

        # Toolbar / menu actions -> main tabs
        connect_action("actionNewLogPlot", 1)
        connect_action("actiondatainfo", 2)
        connect_action("actionNewCrossplot", 3)
        connect_action("actionNewHistogram", 4)
        connect_action("actionNewRoseDiagram", 5)
        connect_action("actionShaleVolume", 6)
        connect_action("actionPorosityCalc", 7)
        connect_action("actionWaterSaturation", 8)
        connect_action("actionPermeability", 9)
        connect_action("actionNetPay", 10)
        connect_action("actionWellCorrelation", 11)
        connect_action("actionMultimineralAnalysis", 12)
        connect_action("actionFMIAnalysis", 13)
        connect_action("actionWellboreStability", 14)
        connect_action("actionPorePressure", 15)

        # Geomechanics menu items -> Geomechanics Suite tab
        for name in (
            "actionStressAnalysis",
            "actionWellboreStability",
            "actionFractureAnalysis",
            "actionPorePressure",
            "actionUCS",
            "actionYoungsModulus",
            "actionPoissonRatio",
            "actionBrittlenessIndex",
            "actionMudWeightWindow",
        ):
            connect_action(name, 16)

        # Dashboard quick-launch buttons
        connect_button("btnDashLogView", 1)
        connect_button("btnDashXplot", 3)
        connect_button("btnDashVsh", 6)
        connect_button("btnDashSw", 8)
        connect_button("btnDashGeo", 16)
        connect_button("btnDashCorr", 11)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PetroVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
