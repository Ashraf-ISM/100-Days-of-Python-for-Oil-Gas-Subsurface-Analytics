from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui, uic

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
        self._reorder_tabs()
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
        connect_action_to_tab("actionFMIAnalysis", "tabFMIAnalysis", 13)
        connect_action_to_tab("actionWellboreStability", "tabWellboreStability", 14)
        connect_action_to_tab("actionPorePressure", "tabPorePressure", 15)

        geo_idx = tab_index("tabGeomechanics", 16)
        if geo_idx is not None:
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
                connect_action(name, geo_idx)

            connect_button("btnDashGeo", geo_idx)
        else:
            connect_button("btnDashGeo", 16)

        # Dashboard quick-launch buttons
        connect_button("btnDashLogView", tab_index("tabLogViewer", 1) or 1)
        connect_button("btnDashXplot", tab_index("tabLogViewer", 1) or 1)
        connect_button("btnDashVsh", tab_index("tabShaleVolume", 6) or 6)
        connect_button("btnDashSw", tab_index("tabWaterSaturation", 8) or 8)
        connect_button("btnDashCorr", tab_index("tabWellCorrelation", 11) or 11)
    
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

    def _reorder_tabs(self) -> None:
        """Put the main analysis tabs in a stable, user-friendly order."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None:
            return

        desired_order = [
            "tabDashboard",
            "tabDataInfoStats",
            "tabLogViewer",
            "tabQualitycontrol",
            "tabFormationevaluation",
        ]

        current_tab = tab_widget.currentWidget()
        tab_state: list[tuple[QtWidgets.QWidget, str, QtGui.QIcon, str, str]] = []
        for index in range(tab_widget.count()):
            widget = tab_widget.widget(index)
            tab_state.append(
                (
                    widget,
                    tab_widget.tabText(index),
                    tab_widget.tabIcon(index),
                    tab_widget.tabToolTip(index),
                    tab_widget.tabWhatsThis(index),
                )
            )

        lookup = {
            widget: (text, icon, tooltip, whatsthis)
            for widget, text, icon, tooltip, whatsthis in tab_state
        }

        ordered_widgets: list[QtWidgets.QWidget] = []
        seen: set[QtWidgets.QWidget] = set()
        for tab_name in desired_order:
            widget = getattr(self, tab_name, None)
            if widget is None or widget in seen or tab_widget.indexOf(widget) < 0:
                continue
            ordered_widgets.append(widget)
            seen.add(widget)

        for widget, *_rest in tab_state:
            if widget not in seen:
                ordered_widgets.append(widget)
                seen.add(widget)

        if [widget for widget, *_rest in tab_state] == ordered_widgets:
            return

        for index in reversed(range(tab_widget.count())):
            tab_widget.removeTab(index)

        for widget in ordered_widgets:
            text, icon, tooltip, whatsthis = lookup[widget]
            new_index = tab_widget.addTab(widget, icon, text)
            if tooltip:
                tab_widget.setTabToolTip(new_index, tooltip)
            if whatsthis:
                tab_widget.setTabWhatsThis(new_index, whatsthis)

        dashboard = getattr(self, "tabDashboard", None)
        if dashboard is not None and tab_widget.indexOf(dashboard) >= 0:
            tab_widget.setCurrentWidget(dashboard)
        elif current_tab is not None:
            tab_widget.setCurrentWidget(current_tab)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PetroVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
