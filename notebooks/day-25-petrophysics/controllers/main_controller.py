"""Main UI controller wiring actions to services."""
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
        self.plots = PlotService(ui, self.data)
        self.interp = InterpretationService(ui, self.data)
        self.qc = QCService(ui)
        self._wire_actions()

    def _wire_actions(self):
        # Project
        self._connect_action("actionNewProject", self.projects.new_project)
        self._connect_action("actionSaveProject", self.projects.save_project)

        # Import (single smart loader)
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
        # Plotting (plots tab buttons)
        self._connect_widget("btnPlotMultiTrack", "clicked", self.plots.new_log_plot)
        self._connect_widget("btnPlotTripleCombo", "clicked", self.plots.new_triple_combo)
        self._connect_widget("btnPlotCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("btnPlotHistogram", "clicked", self.plots.new_histogram)
        # Log viewer tab buttons
        self._connect_widget("plottriplecomboplot", "clicked", self.plots.new_triple_combo)
        self._connect_widget("plotmutlitrack", "clicked", self.plots.new_log_plot)

        # Calculations (buttons in tab)
        self._connect_widget("btnCalcVsh", "clicked", self.interp.compute_vsh)
        self._connect_widget("btnCalcPhi", "clicked", self.interp.compute_phi)
        self._connect_widget("btnCalcSw", "clicked", self.interp.compute_sw)
        self._connect_widget("btnCalcPerm", "clicked", self.interp.compute_perm)
        self._connect_widget("btnCalcNetPay", "clicked", self.interp.compute_net_pay)

        # Data actions
        self._connect_widget("btnLoadData", "clicked", self.data.load_data_view)
        self._connect_widget("btnApplyRename", "clicked", self.data.apply_rename)
        self._connect_widget("btnResetRename", "clicked", self.data.reset_rename)
        self._connect_widget("btnUndoRename", "clicked", self.data.undo_rename)
        self._connect_widget("btnCalcStats", "clicked", self.data.compute_stats)
        self._connect_widget("tabData", "currentChanged", self.data.on_data_tab_changed)
        self._connect_widget("comboDTWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboCurveWell", "currentTextChanged", self.data.on_curve_well_changed)
        self._connect_widget("comboLVWell", "currentTextChanged", self.data.set_current_well)

        # QC
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
