"""Main UI controller wiring actions to services."""
from __future__ import annotations

from PyQt5 import QtWidgets

from app.calculation_window import CalculationWindow
from services.project_service import ProjectService
from services.data_service import DataService
from services.plot_service import PlotService
from services.interpretation_service import InterpretationService
from services.formation_evaluation_service import FormationEvaluationService
from services.qc_service import QCService


class MainController:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self.projects = ProjectService(ui)
        self.data = DataService(ui)
        self.plots = PlotService(ui, self.data)
        self.interp = InterpretationService(ui, self.data)
        self.fe = FormationEvaluationService(ui, self.data)
        self.qc = QCService(ui, self.data)
        self.calculation_window: CalculationWindow | None = None
        
        # Store references for cross-service access
        self.ui._data_service = self.data
        self.ui._project_service = self.projects
        
        self._wire_actions()
        self._initialize_ui()

    def _wire_actions(self):
        # Project actions
        self._connect_action("actionNewProject", self.projects.new_project)
        self._connect_action("actionOpenProject", self.projects.open_project)
        self._connect_action("actionSaveProject", self.projects.save_project)
        self._connect_action("actionSaveProjectAs", self.projects.save_project_as)
        
        # Dashboard project buttons
        self._connect_widget("btnLoadProject", "clicked", self.projects.open_project)
        self._connect_widget("btnSaveProject", "clicked", self._save_and_track)
        self._connect_widget("btnDashRecent1", "clicked", 
                           lambda: self.projects.load_recent_project(self._get_recent_path(0)))
        self._connect_widget("btnDashRecent2", "clicked", 
                           lambda: self.projects.load_recent_project(self._get_recent_path(1)))
        self._connect_widget("btnDashRecent3", "clicked", 
                           lambda: self.projects.load_recent_project(self._get_recent_path(2)))

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
            self._connect_action(name, self._import_and_track)

        # Plotting
        self._connect_action("actionNewLogPlot", self.plots.new_log_plot)
        self._connect_action("actionNewCrossplot", self.plots.new_crossplot)
        self._connect_action("actionNewHistogram", self.plots.new_histogram)
        self._connect_action("actionBasicArithmetic", self.open_calculation_window)
        # Plotting (plots tab buttons)
        self._connect_widget("btnPlotMultiTrack", "clicked", self.plots.new_log_plot)
        self._connect_widget("btnPlotTripleCombo", "clicked", self.plots.new_triple_combo)
        self._connect_widget("btnPlotCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("btnPlotHistogram", "clicked", self.plots.new_histogram)
        self._connect_widget("btnLVPlotCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("btnLVPlotHistogram", "clicked", self.plots.new_histogram)
        self._connect_widget("btnLVPlotPairplot", "clicked", self.plots.new_pairplot)
        self._connect_widget("btnLVPlotViolin", "clicked", self.plots.new_violinplot)
        # Log viewer tab buttons
        self._connect_widget("plottriplecomboplot", "clicked", self.plots.new_triple_combo)
        self._connect_widget("plotmutlitrack", "clicked", self.plots.new_log_plot)

        # Dashboard module launch buttons
        self._connect_widget("btnDashLoadLogs", "clicked", self.data.import_data)
        self._connect_widget("btnDashQualityAssess", "clicked", self._go_to_qc_tab)
        self._connect_widget("btnDashViewEditLogs", "clicked", self._go_to_logviewer_tab)
        self._connect_widget("btnDashAnalyzeCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("btnDashNetPay", "clicked", self._go_to_netpay_tab)
        self._connect_widget("btnDashCalcVsh", "clicked", self.interp.compute_vsh)
        self._connect_widget("btnDashCalcPorosity", "clicked", self.interp.compute_phi)
        self._connect_widget("btnDashCalcPorosity2", "clicked", self.interp.compute_phi)
        self._connect_widget("btnDashCalcSaturation", "clicked", self.interp.compute_sw)
        self._connect_widget("btnDashNetPayEval", "clicked", self.interp.compute_net_pay)

        # Calculations (buttons in tab)
        self._connect_widget("btnCalcVsh", "clicked", self.interp.compute_vsh)
        self._connect_widget("btnCalcPhi", "clicked", self.interp.compute_phi)
        self._connect_widget("btnCalcSw", "clicked", self.interp.compute_sw)
        self._connect_widget("btnCalcPerm", "clicked", self.interp.compute_perm)
        self._connect_widget("btnCalcNetPay", "clicked", self.interp.compute_net_pay)
        self._connect_widget("btnResetNetPay", "clicked", self.interp.reset_net_pay)

        # Data actions
        self._connect_widget("btnLoadData", "clicked", self.data.load_data_view)
        self._connect_widget("btnApplyRename", "clicked", self.data.apply_rename)
        self._connect_widget("btnResetRename", "clicked", self.data.reset_rename)
        self._connect_widget("btnUndoRename", "clicked", self.data.undo_rename)
        self._connect_widget("btnCalcStats", "clicked", self.data.compute_stats)
        self._connect_widget("btnDISExport", "clicked", self.data.export_report)
        self._connect_widget("tabData", "currentChanged", self.data.on_data_tab_changed)
        self._connect_widget("comboDTWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboDISWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboQCWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboFeWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboVclWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboPhiWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboSwWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboPermWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboNetPayWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboCurveWell", "currentTextChanged", self.data.on_curve_well_changed)
        self._connect_widget("comboLVWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("btnDISRefresh", "clicked", self.data.load_data_view)

        # Formation evaluation
        self._connect_widget("btnRunFE", "clicked", self.fe.run_evaluation)
        self._connect_widget("btnFERender", "clicked", self.fe.run_evaluation)
        self._connect_widget("btnResetFE", "clicked", self.fe.reset_evaluation)
        

        # QC
        self._connect_widget("btnRunQC", "clicked", self.qc.run_qc)
        self._connect_widget("btnResetQC", "clicked", self.qc.reset_qc)
        self._connect_widget("btnExportQC", "clicked", self.qc.export_qc)
        self._connect_widget("comboQCCurve", "currentTextChanged", self.qc.run_qc)
        self._connect_widget("comboQCMethod", "currentTextChanged", self.qc.run_qc)
        self._connect_widget("comboQCSmoothing", "currentTextChanged", self.qc.run_qc)
        self._connect_widget("spinQCThreshold", "valueChanged", self.qc.run_qc)
        self._connect_widget("spinQCWindow", "valueChanged", self.qc.run_qc)
        self._connect_widget("spinQCFrom", "valueChanged", self.qc.run_qc)
        self._connect_widget("spinQCTo", "valueChanged", self.qc.run_qc)
        self._connect_widget("checkQCMissing", "toggled", self.qc.run_qc)
        self._connect_widget("checkQCOutliers", "toggled", self.qc.run_qc)
        self._connect_widget("checkQCSpikes", "toggled", self.qc.run_qc)
        self._connect_widget("checkQCNegative", "toggled", self.qc.run_qc)
        self._connect_widget("btnLVRunQC", "clicked", self.qc.run_qc)
        self._connect_widget("btnLVResetQC", "clicked", self.qc.reset_qc)
        self._connect_widget("btnLVExportQC", "clicked", self.qc.export_qc)

    def _initialize_ui(self) -> None:
        """Initialize UI state."""
        self.projects.refresh_recent_projects()

    def _connect_action(self, name: str, handler):
        action = getattr(self.ui, name, None)
        if action is not None:
            action.triggered.connect(handler)

    def _connect_widget(self, name: str, signal: str, handler):
        widget = getattr(self.ui, name, None)
        if widget is None:
            return
        getattr(widget, signal).connect(handler)

    def _import_and_track(self) -> None:
        """Import data and mark project as modified."""
        self.data.import_data()
        self.projects.mark_modified()

    def _save_and_track(self) -> None:
        """Save project."""
        self.projects.save_project()

    def _get_recent_path(self, index: int) -> str:
        """Get path for recent project button.
        
        Args:
            index: Button index (0-2)
        
        Returns:
            Project path or empty string
        """
        from core.project_manager import get_recent_projects
        recent = get_recent_projects()
        return recent[index] if index < len(recent) else ""

    def _go_to_qc_tab(self) -> None:
        """Switch to QC tab."""
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        if tab_widget is not None:
            qc_tab = getattr(self.ui, "tabQualitycontrol", None)
            if qc_tab is not None:
                idx = tab_widget.indexOf(qc_tab)
                if idx >= 0:
                    tab_widget.setCurrentIndex(idx)

    def _go_to_logviewer_tab(self) -> None:
        """Switch to log viewer tab."""
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        if tab_widget is not None:
            lv_tab = getattr(self.ui, "tabLogViewer", None)
            if lv_tab is not None:
                idx = tab_widget.indexOf(lv_tab)
                if idx >= 0:
                    tab_widget.setCurrentIndex(idx)

    def _go_to_netpay_tab(self) -> None:
        """Switch to net pay tab."""
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        if tab_widget is not None:
            np_tab = getattr(self.ui, "tabNetPay", None)
            if np_tab is not None:
                idx = tab_widget.indexOf(np_tab)
                if idx >= 0:
                    tab_widget.setCurrentIndex(idx)

    def open_calculation_window(self):
        if self.calculation_window is None:
            self.calculation_window = CalculationWindow(self.ui)

        curves: list[str] = []
        well = self.data._get_current_well()
        if well is not None:
            df = getattr(well, "data", None)
            if df is not None:
                curves = [str(column) for column in df.columns]

        self.calculation_window.set_available_curves(curves)
        self.calculation_window.show()
        self.calculation_window.raise_()
        self.calculation_window.activateWindow()
