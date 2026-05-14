"""Main UI controller wiring actions to services."""
from __future__ import annotations

from PyQt5 import QtWidgets

from app.calculation_window import CalculationWindow
from services.project_service import ProjectService
from services.data_service import DataService
from services.plot_service import PlotService
from services.interpretation_service import InterpretationService
from services.geomechanics_service import GeomechanicsService
from services.formation_evaluation_service import FormationEvaluationService
from services.qc_service import QCService


class MainController:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self.projects = ProjectService(ui)
        self.data = DataService(ui)
        self.plots = PlotService(ui, self.data)
        self.interp = InterpretationService(ui, self.data)
        self.geo = GeomechanicsService(ui, self.data)
        self.fe = FormationEvaluationService(ui, self.data)
        self.qc = QCService(ui, self.data)
        self.calculation_window: CalculationWindow | None = None
        
        # Store references for cross-service access
        self.ui._data_service = self.data
        self.ui._project_service = self.projects
        self.ui._interp_service = self.interp

        # Post-load callback — called by ProjectService after a project is
        # successfully opened so that all interpretation workspaces are
        # re-rendered from the loaded DataFrame + restored AppState values.
        self.ui.on_project_loaded = self._on_project_loaded

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
        self._connect_action("actionDeleteWell", self._delete_well_and_track)

        # ── Well menu ─────────────────────────────────────────────────────────
        self._connect_action("actionAddWell", self._import_and_track)          # Add New Well
        self._connect_action("actionWellProperties", self._show_well_properties)
        self._connect_action("actionSetActiveWell", self._show_set_active_well)
        self._connect_action("actionWellTops", self._show_well_tops_info)
        self._connect_action("actionWellTrajectory", self._go_to_3d_well_tab)
        self._connect_action("actionCasingCompletion", self._show_casing_info)
        self._connect_action("actionCoreData", self._show_core_data_info)
        self._connect_action("actionDSTData", self._show_dst_data_info)
        self._connect_action("actionFluidAnalysis", self._show_fluid_analysis_info)
        self._connect_action("actionMudLog", self._show_mud_log_info)
        # Project Browser sidebar '+ Well' and 'Import' buttons
        self._connect_widget("btnBrowseAddWell", "clicked", self._import_and_track)
        self._connect_widget("btnBrowseImport", "clicked", self._import_and_track)

        # Plotting
        self._connect_action("actionNewLogPlot", self.plots.new_log_plot)
        self._connect_action("actionNewCrossplot", self.plots.new_crossplot)
        self._connect_action("actionNewHistogram", self.plots.new_histogram)
        self._connect_action("actionBasicArithmetic", self.open_calculation_window)
        self._connect_action("actionAbout", self._show_about_dialog)
        self._connect_action("actionDocumentation", self._show_help_dialog)
        self._connect_action("actionTutorials", self._show_help_dialog)
        # Plotting (plots tab buttons)
        self._connect_widget("btnPlotMultiTrack", "clicked", self.plots.new_log_plot)
        self._connect_widget("btnPlotTripleCombo", "clicked", self.plots.new_triple_combo)
        self._connect_widget("btnPlotCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("btnPlotHistogram", "clicked", self.plots.new_histogram)
        self._connect_widget("btnLVPlotCrossplot", "clicked", self.plots.new_crossplot)
        self._connect_widget("advance_cross_plot", "clicked", self.plots.open_advanced_crossplot)
        self._connect_widget("btnLVPlotHistogram", "clicked", self.plots.new_histogram)
        self._connect_widget("btnLVPlotPairplot", "clicked", self.plots.new_pairplot)
        self._connect_widget("btnLVPlotViolin", "clicked", self.plots.new_violinplot)
        # Log viewer tab buttons
        self._connect_widget("plottriplecomboplot", "clicked", self.plots.new_triple_combo)
        self._connect_widget("plotmutlitrack", "clicked", self.plots.new_log_plot)

        # Dashboard module launch buttons
        self._connect_widget("btnDashImportLAS", "clicked", self.data.import_data)
        self._connect_widget("btnDashImportCSV", "clicked", self.data.import_data)
        self._connect_widget("btnDashImportSEGY", "clicked", self.data.import_data)
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
        self._connect_widget("btnDashGeo", "clicked", self._go_to_geomechanics_tab)

        # Calculations (buttons in tab)
        self._connect_widget("btnCalcVsh", "clicked", self.interp.compute_vsh)
        self._connect_widget("btnVshModelComparison", "clicked", self.interp.show_vsh_model_comparison_dialog)
        self._connect_widget("btnResetVsh", "clicked", self.interp.reset_vsh_panel)
        self._connect_widget("btnCalcPhi", "clicked", self.interp.compute_phi)
        self._connect_widget("btnResetPhi", "clicked", self.interp.reset_phi_panel)
        self._connect_widget("btnCalcSw", "clicked", self.interp.compute_sw)
        self._connect_widget("btnCalcPerm", "clicked", self.interp.compute_perm)
        self._connect_widget("btnCalcNetPay", "clicked", self.interp.compute_net_pay)
        self._connect_widget("btnResetNetPay", "clicked", self.interp.reset_net_pay)

        # Data actions
        self._connect_widget("btnLoadData", "clicked", self.data.load_data_view)
        self._connect_widget("btnApplyRename", "clicked", self.data.apply_rename)
        self._connect_widget("btnResetRename", "clicked", self.data.reset_rename)
        self._connect_widget("btnUndoRename", "clicked", self.data.undo_rename)
        self._connect_widget("btnDISRenameColumns", "clicked", self.data.show_rename_dialog)
        self._connect_widget("btnDISUndoRename", "clicked", self.data.undo_rename)
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
        self._connect_widget("comboGeoWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("comboCurveWell", "currentTextChanged", self.data.on_curve_well_changed)
        self._connect_widget("comboLVWell", "currentTextChanged", self.data.set_current_well)
        self._connect_widget("btnDISRefresh", "clicked", self.data.load_data_view)

        # Formation evaluation
        self._connect_widget("btnRunFE", "clicked", self.fe.run_evaluation)
        self._connect_widget("btnFERender", "clicked", self.fe.run_evaluation)
        self._connect_widget("btnResetFE", "clicked", self.fe.reset_evaluation)
        

        # QC — existing controls
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
        # QC — new spike engine controls (safe fallback: silently ignored if absent)
        self._connect_widget("comboQCSpikeMode", "currentTextChanged", self.qc.run_qc)
        self._connect_widget("spinQCConfidence",  "valueChanged",       self.qc.run_qc)
        self._connect_widget("checkQCCrossLog",   "toggled",            self.qc.run_qc)
        self._connect_widget("comboQCCorrection", "currentTextChanged", self.qc.run_qc)

    def _initialize_ui(self) -> None:
        """Initialize UI state."""
        self.projects.refresh_recent_projects()

    def _on_project_loaded(self) -> None:
        """Re-render all interpretation workspaces after a project is opened.

        The well DataFrames (including previously computed VSH, PHIT, SW, PERM,
        NET_PAY curves) are already in memory at this point.  AppState has also
        been restored to the UI widgets.  We just need to tell each workspace
        to repaint itself and, where a dedicated re-render function exists, call it.
        """
        well = self.data._get_current_well()
        if well is None:
            return

        df = getattr(well, "data", None)
        if df is None:
            return

        cols_upper = {str(c).upper() for c in df.columns}

        # ── Vsh / Shale Volume ────────────────────────────────────────────────
        # run_vsh_workflow re-reads the restored GR-curve / GR-min / GR-max
        # widgets and replots the track; the VSH column already in the
        # DataFrame will be overwritten with the same values.
        if "VSH" in cols_upper or "VSH_LINEAR" in cols_upper:
            try:
                self.interp.run_vsh_workflow()
            except Exception as exc:
                print(f"[PostLoad] Vsh refresh skipped: {exc}")

        # ── Porosity ──────────────────────────────────────────────────────────
        if any(c in cols_upper for c in ("PHIT", "PHIE")):
            try:
                self.interp.refresh_porosity_workspace()
            except Exception as exc:
                print(f"[PostLoad] Porosity refresh skipped: {exc}")

        # ── Water Saturation ──────────────────────────────────────────────────
        if "SW" in cols_upper:
            try:
                self.interp.refresh_sw_workspace()
            except Exception as exc:
                print(f"[PostLoad] Sw refresh skipped: {exc}")

        # ── Net Pay ───────────────────────────────────────────────────────────
        if "NET_PAY" in cols_upper or "PAYFLAG" in cols_upper:
            try:
                self.interp.compute_net_pay()
            except Exception as exc:
                print(f"[PostLoad] Net Pay refresh skipped: {exc}")

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
        imported = self.data.import_data()
        if imported:
            self.projects.mark_modified()

    def _delete_well_and_track(self) -> None:
        """Delete the active well and mark project as modified."""
        before = len(getattr(self.data, "_wells", {}))
        self.data.remove_current_well()
        after = len(getattr(self.data, "_wells", {}))
        if after < before:
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

    def _go_to_geomechanics_tab(self) -> None:
        """Switch to geomechanics tab."""
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        if tab_widget is not None:
            geo_tab = getattr(self.ui, "tabGeomechanics", None)
            if geo_tab is not None:
                idx = tab_widget.indexOf(geo_tab)
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

    def _show_about_dialog(self) -> None:
        """Open About dialog from Help menu."""
        handler = getattr(self.ui, "show_about_dialog", None)
        if callable(handler):
            handler()

    def _show_help_dialog(self) -> None:
        """Open documentation/help summary from Help menu."""
        handler = getattr(self.ui, "show_help_dialog", None)
        if callable(handler):
            handler()

    # ── Well menu handlers ────────────────────────────────────────────────────

    def _show_well_properties(self) -> None:
        """Display properties of the currently active well. """
        well = self.data._get_current_well()
        if well is None:
            QtWidgets.QMessageBox.information(
                self.ui, "Well Properties", "No well is currently loaded.\nUse Well ▸ Add New Well to import a LAS file. "
            )
            return
        df = getattr(well, "data", None)
        name = getattr(well, "name", "Unknown")
        log_info = getattr(well, "log_info", {}) or {}
        header_info = getattr(well, "header_info", {}) or {}

        # Build a readable summary
        lines = [f"Well: {name}"]
        if df is not None:
            curves = list(df.columns)
            depth_col = next((c for c in curves if str(c).upper() in {"DEPTH", "DEPT", "MD"}), None)
            if depth_col:
                import pandas as pd
                depths = pd.to_numeric(df[depth_col], errors="coerce").dropna()
                if not depths.empty:
                    lines.append(f"Depth range: {depths.min():.1f} – {depths.max():.1f} m")
            lines.append(f"Number of curves: {len(curves)}")
            lines.append(f"Total samples: {len(df):,}")
        for key in ("company", "field", "country", "well", "uwi"):
            val = header_info.get(key, "") or header_info.get(key.upper(), "")
            if val:
                lines.append(f"{key.capitalize()}: {val}")

        QtWidgets.QMessageBox.information(self.ui, "Well Properties", "\n".join(lines))

    def _show_set_active_well(self) -> None:
        """Show a dialog to pick which loaded well should be the active well. """
        wells = sorted(getattr(self.data, "_wells", {}).keys())
        if not wells:
            QtWidgets.QMessageBox.information(
                self.ui, "Set Active Well", "No wells are loaded.\nUse Well ▸ Add New Well to import a well."
            )
            return

        current = self.data._current_well or wells[0]
        item, ok = QtWidgets.QInputDialog.getItem(
            self.ui, "Set Active Well", "Select the well to make active:", wells,
            wells.index(current) if current in wells else 0, False
        )
        if ok and item:
            self.data.set_current_well(item)

    def _show_well_tops_info(self) -> None:
        """Placeholder – opens the Well Tops information panel."""
        well = self.data._get_current_well()
        name = getattr(well, "name", "N/A") if well else "N/A"
        QtWidgets.QMessageBox.information(
            self.ui, "Well Tops",
            f"Well Tops for: {name}\n\nWell tops import / editing will be"
            " available in a future release.\nYou can currently load LAS files"
            " that include formation marker columns."
        ) 

    def _go_to_3d_well_tab(self) -> None:
        """Switch to the 3D Well Viewer tab."""
        tab_widget = getattr(self.ui, "centralTabWidget", None)
        if tab_widget is None:
            return
        tab = getattr(self.ui, "tab3DWell", None)
        if tab is not None:
            idx = tab_widget.indexOf(tab)
            if idx >= 0:
                tab_widget.setCurrentIndex(idx)
                return
        # Fallback: try common indices
        tab_widget.setCurrentIndex(3)

    def _show_casing_info(self) -> None:
        """Placeholder for Casing & Completion data."""
        QtWidgets.QMessageBox.information(
            self.ui, "Casing & Completion",
            "Casing & Completion data management will be available in a future release."
        )

    def _show_core_data_info(self) -> None:
        """Placeholder for Core Data viewer.""" 
        QtWidgets.QMessageBox.information(
            self.ui, "Core Data",
            "Core data import and display will be available in a future release.\n "
            "CSV-format core plug data can currently be loaded via File ▸ Import Data ▸ Import CSV."
        )

    def _show_dst_data_info(self) -> None:
        """Placeholder for DST Data viewer."""
        QtWidgets.QMessageBox.information(
            self.ui, "DST Data",
            "Drill Stem Test data management will be available in a future release."
        )

    def _show_fluid_analysis_info(self) -> None:
        """Placeholder for Fluid Analysis."""
        QtWidgets.QMessageBox.information(
            self.ui, "Fluid Analysis",
            "Fluid analysis / PVT data tools will be available in a future release."
        )

    def _show_mud_log_info(self) -> None:
        """Placeholder for Mud Log viewer."""
        QtWidgets.QMessageBox.information(
            self.ui, "Mud Log",
            "Mud log import and viewer will be available in a future release."
        )
