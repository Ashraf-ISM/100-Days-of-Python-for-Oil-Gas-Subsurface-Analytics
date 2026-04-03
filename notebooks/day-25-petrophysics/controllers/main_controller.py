"""Main UI controller for PetroVisionPro."""
from __future__ import annotations

from PyQt5 import QtWidgets

from services.project_service import ProjectService
from services.data_service import DataService
from services.plot_service import PlotService
from services.interpretation_service import InterpretationService
from services.qc_service import QCService


class MainController:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self.projects = ProjectService(ui)
        self.data = DataService(ui)
        self.plots = PlotService(ui)
        self.interp = InterpretationService(ui)
        self.qc = QCService(ui)

        self._wire_actions()

    def _wire_actions(self):
        # Project
        self._connect_action("actionNewProject", self.projects.new_project)
        self._connect_action("actionSaveProject", self.projects.save_project)

        # Data import (single smart loader)
        for name in (
            "actionImportLAS",
            "actionImportDLIS",
            "actionImportLIS",
            "actionImportASCII",
            "actionImportCSV",
            "actionImportExcel",
            "actionImportWITSML",
            "actionImportSEGY",
            "actionImportXML",
            "actionImportODM",
        ):
            self._connect_action(name, self.data.import_data)

        # Plotting
        self._connect_action("actionNewLogPlot", self.plots.new_log_plot)
        self._connect_action("actionNewCrossplot", self.plots.new_crossplot)
        self._connect_action("actionNewHistogram", self.plots.new_histogram)

        # Interpretation
        self._connect_action("actionShaleVolume", self.interp.compute_vsh)
        self._connect_action("actionPorosityCalc", self.interp.compute_phi)
        self._connect_action("actionWaterSaturation", self.interp.compute_sw)
        self._connect_action("actionPermeability", self.interp.compute_perm)
        self._connect_action("actionNetPay", self.interp.compute_net_pay)

        # QC
        self._connect_action("actionQualityControl", self._show_qc_tab)
        self._connect_widget("btnRunQC", "clicked", self.qc.run_qc)
        self._connect_widget("btnExportQC", "clicked", self.qc.export_qc)

    def _connect_action(self, name: str, handler):
        action = getattr(self.ui, name, None)
        if action is not None:
            action.triggered.connect(handler)

    def _connect_widget(self, name: str, signal: str, handler):
        widget = getattr(self.ui, name, None)
        if widget is None:
            return
        getattr(widget, signal).connect(handler)

    def _show_qc_tab(self):
        tab_console = getattr(self.ui, "tabConsole", None)
        tab_qc = getattr(self.ui, "tabQC", None)
        if tab_console is not None and tab_qc is not None:
            tab_console.setCurrentWidget(tab_qc)
