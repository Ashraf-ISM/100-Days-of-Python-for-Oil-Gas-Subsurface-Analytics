"""
missing_log_window.py
Main controller for the Missing Log Prediction module.
Wires all UI buttons to separate service scripts.
"""
from __future__ import annotations

from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import pandas as pd

from .prediction_engine          import MissingLogEngine
from .correlation_viewer         import CorrelationMatrixDialog
from .missing_intervals_viewer   import MissingIntervalsDialog
from .training_controller        import TrainingController
from .model_manager              import ModelManager
from .export_controller          import ExportController
from .actual_vs_predicted_viewer import ActualVsPredictedDialog
 

class MissingLogPredictionWindow(QtWidgets.QWidget):
    """
    Main window controller for the Missing Log Prediction AI modules.

    Responsibilities:
        - Data sourcing  (project wells or external LAS)
        - Well / log selection
        - Dynamic feature checkbox list
        - Live statistics display
        - Button wiring to separate service objects 
    """

    def __init__(self, ui_dir: Path, parent=None):
        super().__init__(parent)
        self.ui_dir = ui_dir
        uic.loadUi(str(ui_dir / "MissingLogPrediction.ui"), self)

        self.setWindowTitle("PetroARX AI Analytics — Missing Log Prediction ")

        # ── state ──────────────────────────────────────────────────────────────
        self._data_service      = None
        self._df: pd.DataFrame | None = None
        self._engine: MissingLogEngine | None = None
        self._feature_checkboxes: list[QtWidgets.QCheckBox] = []
        self._all_wells: dict[str, object] = {}   # name → well object

        # ── service objects (separate scripts) ─────────────────────────────────
        self._trainer  = TrainingController(self)
        self._model_mgr = ModelManager()
        self._exporter  = ExportController()

        self._setup_connections()
        self._init_ui_state()

    # ─────────────────────────────────────────────────────────────────────────
    # Bootstrap
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_connections(self):
        """Connect every named button to its handlers."""

        # Header — data source
        _wire(self, "btnLoadFromProject",   self.load_from_active_well)
        _wire(self, "btnImportExternalLAS", self.import_external_las)

        # Header — help
        _wire(self, "btnDocumentation", self._show_help)
        _wire(self, "btnHowItWorks",    self._show_help)
        _wire(self, "btnVideoTutorial", self._show_help)

        # Section 1 — target log
        _wire(self, "btnViewIntervals", self._open_missing_intervals)
        if hasattr(self, "cboTargetLog"):
            self.cboTargetLog.currentTextChanged.connect(self._on_target_log_changed)

        # Well selector (if present)
        if hasattr(self, "cboWellSelector"):
            self.cboWellSelector.currentTextChanged.connect(self._on_well_selected)

        # Section 2 — features
        _wire(self, "btnAutoSel",  self._auto_select_features)
        _wire(self, "btnFeatEng",  self._show_feature_engineering)
        # Feature Correlation Matrix (user-named button in Qt Designer)
        _wire(self, "feature_correlation_matrixpushButton", self._open_correlation_matrix)

        # Section 3 — model config
        _wire(self, "sliderTestSize", lambda v: setattr(
            getattr(self, "lblTestSizeVal", None), "text", f"{v}"
        ), signal="valueChanged")

        # Section 4 — training
        _wire(self, "btnViewTrainingLog", self._view_training_log)

        # Section 5 — performance
        _wire(self, "btnDetailedMetrics", self._show_detailed_metrics)

        # Bottom bar
        _wire(self, "btnBack",    self.close)
        _wire(self, "btnReset",   self._reset_all)
        _wire(self, "btnPreview", self._preview_prediction)
        _wire(self, "btnApply",   self._train_and_apply)
        _wire(self, "btnExport",  self._export_results)

        # Section 6 — Actual vs Predicted Log viewer 
        # Try several possible button names used in Qt Designer
        for _btn_avp in (
            "btnActualVsPredicted",
            "btnWellLogTrack",
            "btnCustomPlot",
            "btnMatplotlibCanvas",
            "btnViewActualVsPred",
        ):
            _wire(self, _btn_avp, self._open_actual_vs_predicted)

        # Section 9 — feature importance 
        _wire(self, "btnExplainAI", self._explain_at_depth)
        _wire(self, "btnCompare",   self._compare_models)

        # Section 10-14 — bottom panels 
        _wire(self, "btnEditPipeline", self._edit_pipeline)
        _wire(self, "btnOptimize",     self._run_hyperopt)
        _wire(self, "btnViewResults",  self._view_optim_results)
        _wire(self, "btnViewDrift",    self._view_drift)
        _wire(self, "btnSaveModel",    self._save_model)
        _wire(self, "btnLoadModel",    self._load_model)
        _wire(self, "btnBatch",        self._batch_prediction)
        _wire(self, "btnExportPkg",    self._export_package)
        _wire(self, "btnDeploy",       self._deploy_model)

    def _init_ui_state(self):
        """Set initial placeholder text on stat labels ."""
        for name in ("lblDataPtsVal", "lblMissingVal", "lblDepthVal"):
            if hasattr(self, name):
                getattr(self, name).setText("—")
        if hasattr(self, "lblUnit"):
            self.lblUnit.setText("Unit: —")
        if hasattr(self, "btnViewIntervals"):
            self.btnViewIntervals.setText("No data loaded ")

    # ─────────────────────────────────────────────────────────────────────────
    # Data ingestion
    # ─────────────────────────────────────────────────────────────────────────

    def set_data_service(self, data_service):
        """Inject the PetroARX DataService and populate the well selector."""
        self._data_service = data_service
        self._populate_well_selector()
        self.load_from_active_well()

    def _populate_well_selector(self):
        """Fill the well-selection combo with ALL loaded project wells."""
        if self._data_service is None:
            return
        self._all_wells = dict(getattr(self._data_service, "_wells", {}))
        if hasattr(self, "cboWellSelector"):
            self.cboWellSelector.blockSignals(True)
            self.cboWellSelector.clear()
            self.cboWellSelector.addItems(sorted(self._all_wells.keys()))
            # pre-select active well
            cur = getattr(self._data_service, "_current_well", None)
            if cur:
                idx = self.cboWellSelector.findText(cur)
                if idx >= 0:
                    self.cboWellSelector.setCurrentIndex(idx)
            self.cboWellSelector.blockSignals(False)

    def _on_well_selected(self, well_name: str):
        """User picked a different well from the selector."""
        well = self._all_wells.get(well_name)
        if well is None:
            return
        self._df = well.data.copy()
        self._engine = MissingLogEngine(self._df)
        self._populate_curve_lists()

    def load_from_active_well(self):
        """Load data from the currently active well in PetroARX."""
        if self._data_service is None:
            return
        well = self._data_service._get_current_well()
        if well is None:
            QtWidgets.QMessageBox.warning(self, "Data Loading",
                                          "No active well found in the project. .")
            return
        self._df = well.data.copy()
        self._engine = MissingLogEngine(self._df)
        self._populate_curve_lists()

    def import_external_las(self):
        """Allow user to upload a LAS file independently."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import LAS Data", "",
            "LAS Files (*.las *.laz);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            from core.well_data_loader import load_well
            well, _msg = load_well(file_path, replace_nulls=True)
            self._df = well.data
            self._engine = MissingLogEngine(self._df)
            self._populate_curve_lists()
            QtWidgets.QMessageBox.information(
                self, "Import Success",
                f"✔  Loaded: {Path(file_path).name}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Import Error", f"Failed to load LAS file:\n{exc}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Curve / log population
    # ─────────────────────────────────────────────────────────────────────────

    def _populate_curve_lists(self):
        """Populate target-log dropdown and dynamic feature checkboxes."""
        if self._df is None:
            return
        curves = list(self._df.columns)

        # Target log combo
        if hasattr(self, "cboTargetLog"):
            self.cboTargetLog.blockSignals(True)
            self.cboTargetLog.clear()
            self.cboTargetLog.addItems(curves)
            self.cboTargetLog.blockSignals(False)

        # Dynamic feature checkboxes
        layout = getattr(self, "lytFeatures", None)
        if layout is not None:
            # Clear old
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self._feature_checkboxes = []
            for curve in curves:
                chk = QtWidgets.QCheckBox(curve)
                chk.setChecked(True)   # default: all selected
                layout.addWidget(chk)
                self._feature_checkboxes.append(chk)
            layout.addStretch()

        # Trigger initial stats
        self._update_data_display()
        # Disable current target in features list
        self._on_target_log_changed(self.cboTargetLog.currentText()
                                    if hasattr(self, "cboTargetLog") else "")

    def get_selected_features(self) -> list[str]:
        """Return names of all checked feature logs."""
        return [c.text() for c in self._feature_checkboxes if c.isChecked()]

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics display
    # ─────────────────────────────────────────────────────────────────────────

    def _on_target_log_changed(self, log_name: str):
        """Called when the user picks a different target log."""
        self._update_data_display()
        # Disable target log in feature list (prevent predicting from self)
        for chk in self._feature_checkboxes:
            if chk.text() == log_name:
                chk.setChecked(False)
                chk.setEnabled(False)
            else:
                chk.setEnabled(True)

    def _update_data_display(self):
        """Refresh Data Points, Missing, Depth Range, Missing Intervals."""
        if self._df is None or self._df.empty or self._engine is None:
            return
        cur = getattr(self, "cboTargetLog", None)
        log_name = cur.currentText() if cur else ""
        if not log_name:
            return

        stats = self._engine.get_log_statistics(log_name)
        if stats:
            _lbl_set(self, "lblDataPtsVal",
                     f"{stats['total']:,}")
            _lbl_set(self, "lblMissingVal",
                     f"{stats['missing']:,} ({stats['missing_pct']:.1f}%)")
            _lbl_set(self, "badgeRed",
                     f"{stats['missing']:,} ({stats['missing_pct']:.1f}%)")

        # Depth range
        depth_col = next(
            (c for c in self._df.columns if c.upper() in {"DEPTH","DEPT","MD"}), None
        )
        if depth_col:
            d_min = self._df[depth_col].min()
            d_max = self._df[depth_col].max()
            _lbl_set(self, "lblDepthVal", f"{d_min:.1f} – {d_max:.1f} m")

        # Missing intervals count
        intervals = self._engine.count_missing_intervals(log_name)
        if hasattr(self, "btnViewIntervals"):
            plural = "interval" if intervals == 1 else "intervals"
            self.btnViewIntervals.setText(f"{intervals} {plural} detected  →")

        # Unit (best effort)
        _lbl_set(self, "lblUnit", f"Unit: {self._engine.guess_unit(log_name)}")

    # ─────────────────────────────────────────────────────────────────────────
    # Button handlers — Section 1 (Target Log)
    # ─────────────────────────────────────────────────────────────────────────

    def _open_missing_intervals(self):
        if self._df is None:
            QtWidgets.QMessageBox.information(self, "Missing Intervals",
                                              "Load well data first.")
            return
        target = self.cboTargetLog.currentText()
        dlg = MissingIntervalsDialog(self._df, target, parent=self)
        dlg.exec_()

    # ─────────────────────────────────────────────────────────────────────────
    # Button handlers — Section 2 (Input Features)
    # ─────────────────────────────────────────────────────────────────────────

    def _open_correlation_matrix(self):
        """Show the correlation heatmap + ranked chart."""
        if self._df is None:
            QtWidgets.QMessageBox.information(self, "Correlation Matrix",
                                              "Load well data first.")
            return
        target = self.cboTargetLog.currentText() if hasattr(self, "cboTargetLog") else ""
        dlg = CorrelationMatrixDialog(self._df, target, parent=self)
        dlg.exec_()

    def _auto_select_features(self):
        """Check top 5 correlated features automatically."""
        if self._engine is None or not hasattr(self, "cboTargetLog"):
            return
        target    = self.cboTargetLog.currentText()
        suggested = self._engine.suggest_features(target)
        for chk in self._feature_checkboxes:
            chk.setChecked(chk.text() in suggested and chk.text() != target)

    def _show_feature_engineering(self):
        QtWidgets.QMessageBox.information(
            self, "Feature Engineering",
            "Feature Engineering pipeline (derivatives, normalization, PCA) "
            "will be available in the next release."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Button handlers — Training / Prediction
    # ─────────────────────────────────────────────────────────────────────────

    def _train_and_apply(self):
        """Main 'Apply Prediction & Save to Well' button."""
        # After the worker finishes it will call _on_training_finished via signal.
        # Connect once (guard against double-connect with a flag).
        if not getattr(self, "_avp_signal_connected", False):
            self._trainer._worker_finished_signal_proxy = self._on_training_finished
            self._avp_signal_connected = False  # reset so flag works below
        self._trainer.start_training()
        # The TrainingController connects finished → _on_finished internally;
        # we additionally hook into it after start:
        if self._trainer._worker is not None and not getattr(self, "_avp_signal_connected", False):
            self._trainer._worker.finished.connect(self._on_training_finished)
            self._avp_signal_connected = True

    def _on_training_finished(self, result: dict):
        """Called automatically after training completes — opens the viewer."""
        self._open_actual_vs_predicted()

    def _preview_prediction(self):
        """Preview prediction without saving — opens the Actual vs Predicted viewer."""
        self._open_actual_vs_predicted()

    def _open_actual_vs_predicted(self):
        """Open the professional Actual vs Predicted Log viewer dialog."""
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(
                self, "Actual vs Predicted Log",
                "Please train the model first (click 'Apply Prediction & Save to Well')."
            )
            return
        if self._df is None:
            QtWidgets.QMessageBox.information(
                self, "Actual vs Predicted Log", "Load well data first."
            )
            return
        target   = self.cboTargetLog.currentText() if hasattr(self, "cboTargetLog") else ""
        features = self.get_selected_features()
        dlg = ActualVsPredictedDialog(
            df       = self._df,
            target   = target,
            features = features,
            result   = result,
            parent   = self,
        )
        dlg.exec_()

    def _export_results(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Export",
                                              "Train the model first.")
            return
        self._exporter.export_results(
            self._df,
            self.cboTargetLog.currentText(),
            self.get_selected_features(),
            result,
            parent_widget=self
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Button handlers — Model Management
    # ─────────────────────────────────────────────────────────────────────────

    def _save_model(self):
        result = self._trainer.last_result
        if result is None or result.get("model") is None:
            QtWidgets.QMessageBox.information(self, "Save Model",
                                              "Train a model first.")
            return
        meta = {
            "algorithm": result["algorithm"],
            "target":    self.cboTargetLog.currentText(),
            "features":  self.get_selected_features(),
            "r2":        result["r2"],
            "rmse":      result["rmse"],
        }
        self._model_mgr.save_model(result["model"], meta, parent_widget=self)

    def _load_model(self):
        model, meta = self._model_mgr.load_model(parent_widget=self)
        if model is not None:
            # Restore feature selection if possible
            if meta and "features" in meta:
                for chk in self._feature_checkboxes:
                    chk.setChecked(chk.text() in meta["features"])

    def _batch_prediction(self):
        QtWidgets.QMessageBox.information(
            self, "Batch Prediction",
            "Batch prediction across multiple wells will be "
            "available in the next release."
        )

    def _deploy_model(self):
        QtWidgets.QMessageBox.information(
            self, "Deploy Model",
            "Model deployment / API export will be available in the next release."
        )

    def _export_package(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Export Package",
                                              "Train a model first.")
            return
        self._export_results()

    # ─────────────────────────────────────────────────────────────────────────
    # Other button handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _view_training_log(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Training Log",
                                              "No training has been run yet.")
            return
        msg = (
            f"Algorithm : {result['algorithm']}\n"
            f"Samples   : {result['n_train']:,} train / {result['n_test']:,} test\n"
            f"Features  : {result['n_features']}\n"
            f"Duration  : {result['duration']}\n\n"
            f"CV R² scores : {[round(s,4) for s in result['cv_scores']]}\n"
            f"CV mean R²   : {result['cv_mean']:.4f} ± {result['cv_std']:.4f}"
        )
        QtWidgets.QMessageBox.information(self, "Training Log", msg)

    def _show_detailed_metrics(self):
        self._view_training_log()

    def _explain_at_depth(self):
        QtWidgets.QMessageBox.information(
            self, "Explain at Depth",
            "SHAP depth-level explanation will be available in the next release."
        )

    def _compare_models(self):
        QtWidgets.QMessageBox.information(
            self, "Compare Models",
            "Model leaderboard comparison will be available in the next release."
        )

    def _edit_pipeline(self):
        QtWidgets.QMessageBox.information(
            self, "Feature Engineering Pipeline",
            "Interactive pipeline editor will be available in the next release."
        )

    def _run_hyperopt(self):
        QtWidgets.QMessageBox.information(
            self, "Hyperparameter Optimization",
            "Bayesian optimization will be available in the next release."
        )

    def _view_optim_results(self):
        QtWidgets.QMessageBox.information(
            self, "Optimization Results",
            "No optimization has been run yet."
        )

    def _view_drift(self):
        QtWidgets.QMessageBox.information(
            self, "Data Drift Detection",
            "Data drift analysis will be available in the next release."
        )

    def _reset_all(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Reset All",
            "Reset all settings and clear loaded data?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self._df = None
        self._engine = None
        self._feature_checkboxes = []
        layout = getattr(self, "lytFeatures", None)
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        if hasattr(self, "cboTargetLog"):
            self.cboTargetLog.clear()
        self._init_ui_state()

    def _show_help(self):
        QtWidgets.QMessageBox.information(
            self, "Documentation",
            "Missing Log Prediction\n\n"
            "1. Load a well from the project or upload a LAS file.\n"
            "2. Choose a Target Log (the curve to be predicted).\n"
            "3. Select Input Features (correlated curves).\n"
            "4. Configure the ML algorithm and cross-validation.\n"
            "5. Click 'Apply Prediction & Save to Well' to train.\n"
            "6. Export results or save the model for later use."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _wire(window, widget_name: str, handler, signal: str = "clicked"):
    """Safely connect a widget's signal to a handler."""
    w = getattr(window, widget_name, None)
    if w is None:
        return
    try:
        getattr(w, signal).connect(handler)
    except Exception:
        pass


def _lbl_set(window, name: str, text: str):
    """Safely set text on a QLabel by name."""
    lbl = getattr(window, name, None)
    if lbl is not None:
        lbl.setText(text)
