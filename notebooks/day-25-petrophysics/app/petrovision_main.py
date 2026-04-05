from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "mainwindow.ui"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from controllers.main_controller import MainController  # noqa: E402


class PetroVisionMainWindow(QtWidgets.QMainWindow):
    def __init__(self, project_path: str | None = None):
        super().__init__()
        ui_path = UI_DIR / UI_FILE
        uic.loadUi(str(ui_path), self)
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is not None:
            self.setCentralWidget(tab_widget)
        self._embed_data_analysis_tab()
        self._connect_tab_switches()
        self.controller = MainController(self)
        
        # Set window geometry
        self.setGeometry(100, 100, 1497, 893)
        
        # Load project if provided
        if project_path and Path(project_path).exists():
            QtCore.QTimer.singleShot(500, 
                lambda p=project_path: self.controller.projects.load_project_from_path(p))

    def _embed_data_analysis_tab(self) -> None:
        """Replace the Data Info & Stats tab with the Data & Analysis dock contents."""
        data_tab = getattr(self, "tabDataInfoStats", None)
        dock = getattr(self, "dockData", None)
        if data_tab is None or dock is None:
            return

        # If already embedded, skip.
        existing_tab = getattr(self, "tabData", None)
        if existing_tab is not None and existing_tab.parent() is data_tab:
            return

        dock_contents = dock.widget() or getattr(self, "dockDataContents", None)
        if dock_contents is None:
            return

        # Clear existing widgets in the tab (keep the layout to avoid warnings)
        existing_layout = data_tab.layout()
        if existing_layout is not None:
            while existing_layout.count():
                item = existing_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
        else:
            existing_layout = QtWidgets.QVBoxLayout(data_tab)
            existing_layout.setContentsMargins(0, 0, 0, 0)

        # Detach contents from dock and hide the dock
        if dock.widget() is dock_contents:
            dock.setWidget(None)
        dock.hide()

        dock_contents.setParent(data_tab)
        dock_contents.setVisible(True)
        dock_contents.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        existing_layout.setContentsMargins(0, 0, 0, 0)
        existing_layout.addWidget(dock_contents)

    def _connect_tab_switches(self) -> None:
        """Wire toolbar/menu actions and dashboard buttons to tab indices."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None:
            return

        def tab_index(tab_name: str, fallback: int | None = None) -> int | None:
            tab = getattr(self, tab_name, None)
            if tab is not None:
                idx = tab_widget.indexOf(tab)
                if idx >= 0:
                    return idx
            return fallback

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

        def connect_action_to_tab(action_name: str, tab_name: str, fallback_idx: int) -> None:
            idx = tab_index(tab_name, fallback_idx)
            if idx is not None:
                connect_action(action_name, idx)

        # Toolbar / menu actions -> main tabs
        connect_action_to_tab("actionNewLogPlot", "tabLogViewer", 1)
        connect_action_to_tab("actiondatainfo", "tabDataInfoStats", 2)
        connect_action_to_tab("actionNewCrossplot", "tabLogViewer", 1)
        connect_action_to_tab("actionNewHistogram", "tabLogViewer", 1)
        connect_action_to_tab("actionQualityControl", "tabQualitycontrol", 3)
        connect_action_to_tab("actionFormationTesting", "tabFormationevaluation", 4)
        connect_action_to_tab("actionNewRoseDiagram", "tabRoseDiagram", 5)
        connect_action_to_tab("actionShaleVolume", "tabShaleVolume", 6)
        connect_action_to_tab("actionPorosityCalc", "tabPorosity", 7)
        connect_action_to_tab("actionWaterSaturation", "tabWaterSaturation", 8)
        connect_action_to_tab("actionPermeability", "tabPermeability", 9)
        connect_action_to_tab("actionNetPay", "tabNetPay", 10)
        connect_action_to_tab("actionWellCorrelation", "tabWellCorrelation", 11)
        connect_action_to_tab("actionMultimineralAnalysis", "tabMultiMineral", 12)
    
    def closeEvent(self, event):
        """Handle application close - prompt to save if modified.
        
        Args:
            event: QCloseEvent
        """
        if self.controller.projects.is_project_modified():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Save Project?",
                "Project has unsaved changes. Save before closing?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
            )
            
            if reply == QtWidgets.QMessageBox.Save:
                self.controller.projects.save_project()
                event.accept()
            elif reply == QtWidgets.QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
        connect_action_to_tab("actionFMIAnalysis", "tabFMIAnalysis", 13)
        connect_action_to_tab("actionWellboreStability", "tabWellboreStability", 14)
        connect_action_to_tab("actionPorePressure", "tabPorePressure", 15)

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
