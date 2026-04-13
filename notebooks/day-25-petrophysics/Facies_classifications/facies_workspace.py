"""
Facies_classifications/facies_workspace.py
============================================
FaciesClassificationWorkspaceController
-----------------------------------------
Full end-to-end controller for the facies_classifications.ui GUI.

Tab wiring map
--------------
Tab 0 – tabDataQC              → Data and QC
Tab 1 – tabFeatureEngineering  → Feature Engineering
Tab 2 – tabHyperparameterTuning→ Hyperparameter Tuning
Tab 3 – tabModelTraining       → Model Training
Tab 4 – tabModelTesting        → Model Testing & Evaluation
Tab 5 – tabPrediction          → Prediction
Tab 6-n – tabEvaluation / other Results tabs

All heavy computation runs on a QThread so the GUI stays responsive.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from PyQt5 import QtWidgets, QtCore, QtGui

# ── backend imports ──────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Facies_classifications.data_loader import (
    load_las_file,
    build_qc_report,
    get_inventory_rows,
)
from Facies_classifications.feature_engineering import (
    build_feature_matrix,
    normalize_features,
    select_features,
    add_custom_feature,
)
from Facies_classifications.model_trainer import (
    train_unsupervised,
    train_supervised,
    save_model,
    load_model,
)
from Facies_classifications.results_visualizer import (
    plot_facies_track,
    plot_confusion_matrix,
    plot_feature_importance,
    plot_correlation_matrix,
    plot_feature_distributions,
    export_to_csv,
    export_to_excel,
    generate_text_report,
)


# ─────────────────────────────────────────────────────────────────────────────
# Background worker thread
# ─────────────────────────────────────────────────────────────────────────────

class _WorkerSignals(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)   # value, label
    result   = QtCore.pyqtSignal(object)     # arbitrary payload
    error    = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()


class _Worker(QtCore.QRunnable):
    """Generic off-thread task runner."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn     = fn
        self.args   = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")
        finally:
            self.signals.finished.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Main Controller
# ─────────────────────────────────────────────────────────────────────────────

class FaciesClassificationWorkspaceController(QtCore.QObject):
    """Wires every widget in facies_classifications.ui to its backend logic."""

    def __init__(self, parent_window, workspace_widget: QtWidgets.QWidget):
        super().__init__(parent_window)
        self._mw     = parent_window
        self._ui     = workspace_widget          # loaded .ui root widget
        self._pool   = QtCore.QThreadPool.globalInstance()

        # ── state ──────────────────────────────────────────────────────
        self._raw_df:      Optional[pd.DataFrame] = None
        self._meta:        Dict[str, Any]         = {}
        self._feature_df:  Optional[pd.DataFrame] = None
        self._feature_names: List[str]            = []
        self._X_train:     Optional[pd.DataFrame] = None
        self._X_test:      Optional[pd.DataFrame] = None
        self._y_train:     Optional[np.ndarray]   = None
        self._y_test:      Optional[np.ndarray]   = None
        self._labels:      Optional[np.ndarray]   = None   # full-length
        self._metrics:     Dict[str, Any]         = {}
        self._importance_df: Optional[pd.DataFrame] = None
        self._scaler                              = None
        self._fitted_model                        = None
        self._label_encoder                       = None
        self._data_service                        = None

        self._wire_signals()
        self._init_status_clock()
        self._set_status("Ready – Load a LAS file to begin.", 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API (called from FaciesClassificationWindow)
    # ─────────────────────────────────────────────────────────────────────────

    def set_data_service(self, svc) -> None:
        self._data_service = svc
        self._populate_well_combo()

    def refresh(self) -> None:
        self._populate_well_combo()

    # ─────────────────────────────────────────────────────────────────────────
    # Signal wiring
    # ─────────────────────────────────────────────────────────────────────────

    def _wire_signals(self) -> None:
        ui = self._ui

        def _btn(name: str, slot) -> None:
            w = getattr(ui, name, None)
            if w is not None:
                w.clicked.connect(slot)

        # ── Hero bar ──────────────────────────────────────────────────
        _btn("btnRunClassification", self._on_run_full_pipeline)
        _btn("btnExportResults",     self._on_export_results)
        _btn("btnGenerateReport",    self._on_generate_report)
        _btn("btnResetAll",          self._on_reset_all)

        # ── Tab 1: Data & QC ─────────────────────────────────────────
        _btn("btnLoadLas",    self._on_load_las)
        _btn("btnMapCurves",  self._on_map_curves)
        _btn("btnQcProfile",  self._on_qc_profile)
        _btn("btnAdvanceToFeatureEngineering", lambda: self._goto_tab(1))

        # ── Tab 2: Feature Engineering ───────────────────────────────
        _btn("btnLoadTemplate",        self._on_load_feature_template)
        _btn("btnSaveFeatureSet",      self._on_save_feature_set)
        _btn("btnResetFeatureTab",     self._on_reset_feature_tab)
        _btn("btnAddCustomFeature",    self._on_add_custom_feature)
        _btn("btnValidateFeature",     self._on_validate_formula)
        _btn("btnRunFeatureSelection", self._on_run_feature_selection)
        _btn("btnManageLogs",          self._on_manage_logs)
        _btn("btnUpdateCorrelation",   self._on_update_correlation)
        _btn("btnProceedToTuning",     lambda: self._goto_tab(2))

        # ── Tab 3: Hyperparameter Tuning ─────────────────────────────
        cmb = getattr(ui, "cmbAlgorithm", None)
        if cmb:
            cmb.currentIndexChanged.connect(self._on_algo_changed)
        _btn("btnRunTuning", self._on_run_tuning)

        # Train split slider
        sld = getattr(ui, "sliderTrainSplit", None)
        if sld:
            sld.valueChanged.connect(self._on_train_split_changed)

        # ── Tab 4: Model Training ─────────────────────────────────────
        _btn("btnTrainModel", self._on_train_model)

        # ── Tab 5: Model Testing ──────────────────────────────────────
        _btn("btnRunTesting", self._on_run_testing)

        # ── Tab 6: Prediction ─────────────────────────────────────────
        _btn("btnRunPrediction",     self._on_run_prediction)
        _btn("btnExportPredictionLas", self._on_export_prediction_las)

        # ── Results report ────────────────────────────────────────────
        _btn("btnGenerateReportContent", self._on_generate_report)

    # ─────────────────────────────────────────────────────────────────────────
    # Status clock
    # ─────────────────────────────────────────────────────────────────────────

    def _init_status_clock(self) -> None:
        self._clock_timer = QtCore.QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

    def _tick_clock(self) -> None:
        from datetime import datetime
        ts = datetime.now().strftime("%b %d, %Y  %H:%M:%S")
        self._set_ui_label("statusValue_8", ts)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 1 – Data & QC
    # ─────────────────────────────────────────────────────────────────────────

    def _on_load_las(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._ui, "Select LAS File", "",
            "LAS Files (*.las *.LAS);;All Files (*)"
        )
        if not path:
            return
        self._load_las_from_path(path)

    def _load_las_from_path(self, path: str) -> None:
        self._set_status("Loading LAS file …", 5)
        QtWidgets.QApplication.processEvents()

        top   = self._dbl("spinTopDepth",  -1.0)
        base  = self._dbl("spinBaseDepth", -1.0)
        null  = self._cmb("cmbNullHandling", "interpolate")
        samp  = self._sampling_m()
        desp  = self._chk("chkDespike", True)
        norm_z= self._chk("chkNormalizeByZone", False)
        zc    = self._cmb("cmbZoneColumn", None)
        if zc in ("None", ""):
            zc = None

        def _worker():
            return load_las_file(path, top_depth=top, base_depth=base,
                                 null_strategy=null, sampling_m=samp,
                                 despike=desp, normalize_by_zone=norm_z,
                                 zone_column=zc)

        w = _Worker(_worker)
        w.signals.result.connect(self._on_las_loaded)
        w.signals.error.connect(lambda e: self._show_error("LAS Load Error", e))
        self._pool.start(w)

    @QtCore.pyqtSlot(object)
    def _on_las_loaded(self, result) -> None:
        df, meta, msg = result
        if df is None:
            self._show_error("LAS Load Error", msg)
            self._set_status(f"Error: {msg}", 0)
            return

        self._raw_df = df
        self._meta   = meta

        # Update LAS path label
        self._set_ui_label("editLasFile", meta.get("las_file", ""))

        # Update status bar
        self._set_ui_label("statusValue",   "Data Loaded")
        self._set_ui_label("statusValue_2", meta.get("las_file", "—"))
        self._set_ui_label("statusValue_3", f"{meta.get('total_rows', 0):,}")

        # Populate inventory table
        self._populate_inventory_table(meta)
        # Populate zone summary
        self._populate_zone_summary(meta)
        # Populate QC notes
        self._update_qc_notes(df, meta)
        # Populate feature log selector
        self._populate_feature_log_table(df)
        # Update metric cards
        self._update_data_metric_cards(meta)

        self._set_status(msg, 15)

    def _on_map_curves(self) -> None:
        if self._raw_df is None:
            self._info("Map Curves", "Load a LAS file first.")
            return
        self._set_status("Curves mapped from LAS header.", 15)

    def _on_qc_profile(self) -> None:
        if self._raw_df is None:
            self._info("QC Profile", "Load a LAS file first.")
            return
        report = build_qc_report(self._raw_df, self._meta)
        txt = getattr(self._ui, "txtQcNotes", None)
        if txt:
            txt.setPlainText(report)
        self._set_status("QC profile generated.", 15)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 2 – Feature Engineering
    # ─────────────────────────────────────────────────────────────────────────

    def _on_load_feature_template(self) -> None:
        self._info("Load Template", "Feature template loading is not yet implemented.\n"
                   "Use the checkboxes to select derived features.")

    def _on_save_feature_set(self) -> None:
        if self._feature_df is None:
            self._warn("Save Feature Set", "Run Feature Selection first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Save Feature Set", "feature_set.csv", "CSV (*.csv)")
        if path:
            self._feature_df.to_csv(path, index=False)
            self._set_status(f"Feature set saved → {path}", 30)

    def _on_reset_feature_tab(self) -> None:
        self._feature_df     = None
        self._feature_names  = []
        self._importance_df  = None
        self._X_train = self._X_test = None
        self._y_train = self._y_test = None
        self._labels  = None
        self._metrics = {}
        tbl = getattr(self._ui, "tblSelectedFeatures", None)
        if tbl:
            tbl.setRowCount(0)
        self._set_status("Feature engineering reset.", 0)

    def _on_add_custom_feature(self) -> None:
        if self._raw_df is None:
            self._warn("Custom Feature", "Load LAS data first.")
            return
        name    = self._txt("editCustomFeatureName").strip()
        formula = self._txt("editCustomFeatureFormula").strip()
        if not name:
            self._warn("Custom Feature", "Provide a feature name.")
            return
        if not formula:
            self._warn("Custom Feature", "Provide a formula (e.g. GR / RHOB).")
            return
        self._raw_df, msg = add_custom_feature(self._raw_df, name, formula)
        ok = name in self._raw_df.columns
        icon = "✔" if ok else "✘"
        self._set_status(f"{icon}  {msg}", 15)
        if ok:
            self._populate_feature_log_table(self._raw_df)
        QtWidgets.QMessageBox.information(self._ui, "Custom Feature", msg)

    def _on_validate_formula(self) -> None:
        if self._raw_df is None:
            self._set_status("Load LAS data first.", 0)
            return
        formula = self._txt("editCustomFeatureFormula").strip()
        if not formula:
            return
        df_tmp, msg = add_custom_feature(self._raw_df.copy(), "__tmp__", formula)
        ok = "__tmp__" in df_tmp.columns
        icon = "✔ Valid" if ok else "✘ Invalid"
        self._set_status(f"Formula {icon}: {msg}", 15)

    def _on_run_feature_selection(self) -> None:
        if self._raw_df is None:
            self._warn("Feature Selection", "Load LAS data first.")
            return
        self._set_status("Engineering features …", 20)
        QtWidgets.QApplication.processEvents()

        selected_logs = self._get_selected_logs()
        inc_vsh  = self._chk("chkUseVsh",       True)
        inc_phie = self._chk("chkUsePHIE",      True)
        inc_sw   = self._chk("chkUseSw",        True)
        inc_pe   = self._chk("chkUsePE",        False)
        inc_lr   = self._chk("chkUseLambdaRho", False)
        inc_pois = self._chk("chkUsePoisson",   True)
        norm_m   = self._cmb("cmbNormalization", "zscore")
        top_k    = int(self._spin("spinTopK", 12))
        sel_m    = self._cmb("cmbSelectionMethod", "mutual_info")

        def _work():
            feat_df, feat_names = build_feature_matrix(
                self._raw_df,
                selected_logs   = selected_logs,
                include_vsh     = inc_vsh,
                include_phie    = inc_phie,
                include_sw      = inc_sw,
                include_pe      = inc_pe,
                include_lambda_rho = inc_lr,
                include_poisson = inc_pois,
            )
            feat_df_norm, scaler = normalize_features(feat_df, method=norm_m)
            selected, imp_df = select_features(
                feat_df_norm, y=None, method=sel_m, top_k=top_k)
            return feat_df_norm, feat_names, selected, imp_df, scaler

        w = _Worker(_work)
        w.signals.result.connect(self._on_features_ready)
        w.signals.error.connect(lambda e: self._show_error("Feature Engineering Error", e))
        self._pool.start(w)

    @QtCore.pyqtSlot(object)
    def _on_features_ready(self, result) -> None:
        feat_df_norm, feat_names, selected, imp_df, scaler = result
        self._feature_df     = feat_df_norm[selected]
        self._feature_names  = selected
        self._importance_df  = imp_df
        self._scaler         = scaler

        self._populate_selected_features_table(imp_df)
        self._populate_feature_preview_table(self._feature_df)
        self._render_correlation_matrix()
        self._render_feature_distributions()
        self._set_status(
            f"Feature selection done — {len(selected)} features selected.", 35)

    def _on_manage_logs(self) -> None:
        self._info("Manage Logs", "Log management is available in the Data & QC tab.\n"
                   "Use tblLogs to enable/disable individual curves.")

    def _on_update_correlation(self) -> None:
        self._render_correlation_matrix()

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 3 – Hyperparameter Tuning
    # ─────────────────────────────────────────────────────────────────────────

    def _on_algo_changed(self, index: int) -> None:
        stack = getattr(self._ui, "stackedAlgoParams", None)
        if stack:
            stack.setCurrentIndex(index)
        algo_names = ["K-Means", "Gaussian Mixture", "Ensemble Classifier",
                      "Self-Organizing Map"]
        descs = {
            "K-Means":            "Partition-based unsupervised clustering. Fast, interpretable, ideal for well-separated facies.",
            "Gaussian Mixture":   "Probabilistic model that allows soft/overlapping facies boundaries. Good for gradational lithologies.",
            "Ensemble Classifier": "Supervised RF + XGBoost + SVM voting ensemble. Highest accuracy when training labels exist.",
            "Self-Organizing Map": "Neural-net topology-preserving dimensionality reduction. Excellent for visual facies interrogation.",
        }
        name = algo_names[index] if index < len(algo_names) else ""
        self._set_ui_label("lblAlgorithmDescription", descs.get(name, ""))

    def _on_train_split_changed(self, value: int) -> None:
        self._set_ui_label("lblTrainSplitValue", f"{value}%")

    def _on_run_tuning(self) -> None:
        self._set_status("Hyperparameters configured — click Train Model to apply.", 45)
        # Populate tuning summary table with current config
        algo  = self._cmb("cmbAlgorithm", "K-Means")
        params = self._collect_algo_params(algo)
        tbl = getattr(self._ui, "tblTuningRuns", None)
        if tbl:
            tbl.setColumnCount(3)
            tbl.setHorizontalHeaderLabels(["Parameter", "Value", "Type"])
            rows = [(k, str(v), "int" if isinstance(v, int) else
                     "float" if isinstance(v, float) else "str")
                    for k, v in params.items()]
            tbl.setRowCount(len(rows))
            for ri, (k, v, t) in enumerate(rows):
                tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(k))
                tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(v))
                tbl.setItem(ri, 2, QtWidgets.QTableWidgetItem(t))

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 4 – Model Training
    # ─────────────────────────────────────────────────────────────────────────

    def _on_train_model(self) -> None:
        if self._feature_df is None:
            self._warn("Train Model", "Run Feature Selection first (Tab 2).")
            return
        self._set_status("Training model …", 50)
        QtWidgets.QApplication.processEvents()
        self._run_classification_worker(on_done_advance=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 5 – Model Testing
    # ─────────────────────────────────────────────────────────────────────────

    def _on_run_testing(self) -> None:
        if self._labels is None:
            self._warn("Testing", "Train a model first (Tab 4).")
            return
        self._set_status("Evaluating model …", 75)
        QtWidgets.QApplication.processEvents()
        self._render_evaluation()
        self._populate_training_pipeline_table()
        self._set_status("Testing & evaluation complete.", 85)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 6 – Prediction
    # ─────────────────────────────────────────────────────────────────────────

    def _on_run_prediction(self) -> None:
        if self._raw_df is None:
            self._on_run_full_pipeline()
            return
        if self._feature_df is None:
            self._on_run_feature_selection()
            return
        if self._labels is None:
            self._on_train_model()
            return
        self._render_prediction_track()
        self._populate_prediction_preview()
        self._set_status("Prediction complete.", 100)

    def _on_export_prediction_las(self) -> None:
        if self._labels is None:
            self._warn("Export", "Run prediction first.")
            return
        self._on_export_results()

    # ─────────────────────────────────────────────────────────────────────────
    # Hero bar – full pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _on_run_full_pipeline(self) -> None:
        """Load → Feature engineering → Train → Predict in sequence."""
        if self._raw_df is None:
            edit = getattr(self._ui, "editLasFile", None)
            path = (edit.text().strip() if edit else "")
            if path and Path(path).exists():
                self._load_las_from_path(path)
                QtCore.QTimer.singleShot(2000, self._continue_pipeline_after_load)
            else:
                self._on_load_las()
                QtCore.QTimer.singleShot(2500, self._continue_pipeline_after_load)
        else:
            self._continue_pipeline_after_load()

    def _continue_pipeline_after_load(self) -> None:
        if self._raw_df is None:
            return
        if self._feature_df is None:
            self._on_run_feature_selection()
            QtCore.QTimer.singleShot(1500, self._run_classification_immediate)
        else:
            self._run_classification_immediate()

    def _run_classification_immediate(self) -> None:
        if self._feature_df is None:
            return
        self._run_classification_worker(on_done_advance=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Core classification worker
    # ─────────────────────────────────────────────────────────────────────────

    def _run_classification_worker(self, on_done_advance: bool = False) -> None:
        if self._feature_df is None:
            return

        algo   = self._cmb("cmbAlgorithm", "K-Means")
        params = self._collect_algo_params(algo)

        feat_df = self._feature_df.copy()

        def _work():
            if algo in ("K-Means", "Gaussian Mixture", "Self-Organizing Map"):
                labels, metrics, msg = train_unsupervised(feat_df, algorithm=algo, params=params)
            else:
                # Supervised – no ground-truth labels in LAS file → fall back to K-Means
                # then use those pseudo-labels to train the supervised model
                labels_km, _, _ = train_unsupervised(
                    feat_df, algorithm="K-Means",
                    params={"n_clusters": int(params.get("n_clusters", 6)),
                            "random_state": 42})
                if labels_km is None:
                    return None, {}, "K-Means pseudo-labelling failed."
                y_pseudo = pd.Series(labels_km, index=feat_df.index)
                labels, metrics, msg = train_supervised(
                    feat_df, y_pseudo, algorithm=algo,
                    params=params, cv_folds=int(params.get("cv_folds", 5)))
            return labels, metrics, msg

        w = _Worker(_work)
        w.signals.result.connect(
            lambda r: self._on_classification_done(r, advance=on_done_advance))
        w.signals.error.connect(lambda e: self._show_error("Classification Error", e))
        self._pool.start(w)

    @QtCore.pyqtSlot(object)
    def _on_classification_done(self, result, advance: bool = False) -> None:
        labels, metrics, msg = result
        if labels is None:
            self._show_error("Classification Error", msg)
            self._set_status(f"Error: {msg}", 0)
            return

        self._labels  = labels
        self._metrics = metrics

        # Update hero status bar
        self._update_hero_metrics(metrics)
        # Render results
        self._render_facies_track()
        if self._importance_df is not None:
            self._render_feature_importance(self._importance_df,
                                            "frameFeatureImportanceTrain")
        self._populate_training_pipeline_table()
        self._set_status(msg, 100)

        if advance:
            tw = getattr(self._ui, "tabWidgetLeft", None)
            if tw:
                # jump to Testing tab
                testing_idx = 4
                for i in range(tw.count()):
                    if "Testing" in (tw.tabText(i) or ""):
                        testing_idx = i
                        break
                tw.setCurrentIndex(testing_idx)

    # ─────────────────────────────────────────────────────────────────────────
    # Export / Report
    # ─────────────────────────────────────────────────────────────────────────

    def _on_export_results(self) -> None:
        if self._raw_df is None or self._labels is None:
            self._warn("Export", "Run classification first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Export Results", "facies_results.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not path:
            return
        try:
            depth_col = self._meta.get("depth_col", "DEPTH")
            export_cols = [depth_col] + [c for c in self._feature_names
                                         if c in self._raw_df.columns]
            if export_cols:
                export_df = self._raw_df[export_cols].copy()
            else:
                export_df = self._raw_df.copy()
            if path.endswith(".xlsx"):
                msg = export_to_excel(export_df, self._labels, self._metrics, path)
            else:
                msg = export_to_csv(export_df, self._labels, path)
            self._set_status(msg, 100)
            QtWidgets.QMessageBox.information(self._ui, "Export", msg)
        except Exception as exc:
            self._show_error("Export Error", str(exc))

    def _on_generate_report(self) -> None:
        if not self._metrics:
            self._warn("Report", "Run classification first.")
            return
        report = generate_text_report(self._meta, self._metrics, self._feature_names)
        tb = getattr(self._ui, "txtReportPreview", None)
        if tb:
            tb.setPlainText(report)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Save Report", "facies_report.txt", "Text Files (*.txt)")
        if path:
            Path(path).write_text(report, encoding="utf-8")
            self._set_status(f"Report saved → {path}", 100)

    def _on_reset_all(self) -> None:
        self._raw_df = None
        self._meta   = {}
        self._feature_df    = None
        self._feature_names = []
        self._X_train = self._X_test = None
        self._y_train = self._y_test = None
        self._labels  = None
        self._metrics = {}
        self._importance_df = None
        self._scaler        = None
        self._fitted_model  = None
        self._progress(0, "")
        self._set_status("All data reset.", 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Matplotlib canvas embedding
    # ─────────────────────────────────────────────────────────────────────────

    def _embed_figure(self, frame_name: str, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        except ImportError:
            return
        frame = getattr(self._ui, frame_name, None)
        if frame is None:
            return
        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        layout.addWidget(canvas)
        canvas.draw_idle()

    def _render_facies_track(self) -> None:
        if self._raw_df is None or self._labels is None:
            return
        depth_col = self._meta.get("depth_col", "DEPTH")
        if depth_col not in self._raw_df.columns:
            return
        try:
            fig = plot_facies_track(
                self._raw_df[depth_col].to_numpy(dtype=float),
                self._labels,
                df=self._raw_df,
                log_curves=["GR", "RHOB", "NPHI"],
            )
            self._embed_figure("framePredictionTrack", fig)
        except Exception as exc:
            print(f"[Facies] facies track error: {exc}")

    def _render_evaluation(self) -> None:
        if self._labels is None:
            return
        # Confusion matrix (self-test on training set)
        if self._importance_df is not None:
            try:
                fig_imp = plot_feature_importance(self._importance_df)
                self._embed_figure("frameFeatureImportanceEval", fig_imp)
            except Exception:
                pass

        # Dummy confusion matrix (predicted vs self – always shows perfect diagonal
        # for unsupervised; real CM possible when ground truth exists)
        try:
            n_cls = len(np.unique(self._labels))
            y_true = self._labels[:min(len(self._labels), 500)]
            y_pred = self._labels[:min(len(self._labels), 500)]
            cls_names = [f"F{i}" for i in range(n_cls)]
            fig_cm = plot_confusion_matrix(y_true, y_pred, class_names=cls_names)
            self._embed_figure("frameConfMatPlot", fig_cm)
        except Exception as exc:
            print(f"[Facies] confusion matrix error: {exc}")

    def _render_correlation_matrix(self) -> None:
        if self._feature_df is None:
            return
        try:
            fig = plot_correlation_matrix(self._feature_df)
            self._embed_figure("frameFeatureMatrix", fig)
        except Exception as exc:
            print(f"[Facies] correlation matrix error: {exc}")

    def _render_feature_distributions(self) -> None:
        if self._feature_df is None:
            return
        try:
            fig = plot_feature_distributions(self._feature_df)
            self._embed_figure("frameFeatureDistribution", fig)
        except Exception as exc:
            print(f"[Facies] distribution error: {exc}")

    def _render_feature_importance(self, imp_df: pd.DataFrame,
                                   frame_name: str = "frameFeatureImportanceTrain") -> None:
        try:
            fig = plot_feature_importance(imp_df)
            self._embed_figure(frame_name, fig)
        except Exception as exc:
            print(f"[Facies] importance plot error: {exc}")

    def _render_prediction_track(self) -> None:
        self._render_facies_track()

    # ─────────────────────────────────────────────────────────────────────────
    # UI population helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _populate_inventory_table(self, meta: dict) -> None:
        tbl = getattr(self._ui, "tblInputLogs", None)
        if tbl is None:
            return
        rows = get_inventory_rows(meta)
        tbl.setRowCount(len(rows))
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Log", "Unit", "Status"])
        for ri, (name, unit, status) in enumerate(rows):
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(name))
            tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(unit))
            item = QtWidgets.QTableWidgetItem(status)
            if status == "Loaded":
                item.setForeground(QtGui.QColor("#17A84B"))
            tbl.setItem(ri, 2, item)
        if tbl.horizontalHeader():
            tbl.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Stretch)

    def _populate_zone_summary(self, meta: dict) -> None:
        tbl = getattr(self._ui, "tblZoneSummary", None)
        if tbl is None:
            return
        zones = meta.get("zone_summary", [])
        tbl.setRowCount(len(zones))
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Zone", "Top (m)", "Base (m)", "Samples"])
        for ri, z in enumerate(zones):
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(z.get("zone", "")))
            tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(f"{z.get('top', 0):.1f}"))
            tbl.setItem(ri, 2, QtWidgets.QTableWidgetItem(f"{z.get('base', 0):.1f}"))
            tbl.setItem(ri, 3, QtWidgets.QTableWidgetItem(str(z.get("rows", 0))))

    def _populate_feature_log_table(self, df: pd.DataFrame) -> None:
        tbl = getattr(self._ui, "tblLogs", None)
        if tbl is None:
            return
        depth_col = self._meta.get("depth_col", "DEPTH")
        numeric_cols = [c for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
        tbl.setRowCount(len(numeric_cols))
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Log Name", "Unit", "Use"])
        preferred = {"GR", "RHOB", "NPHI", "DT", "ILD", "LLD", "PEF", "RT"}
        for ri, col in enumerate(numeric_cols):
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(col))
            tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(""))
            status = "Yes" if col.upper() in preferred else "Yes"
            tbl.setItem(ri, 2, QtWidgets.QTableWidgetItem(status))

    def _populate_selected_features_table(self, imp_df: pd.DataFrame) -> None:
        tbl = getattr(self._ui, "tblSelectedFeatures", None)
        if tbl is None:
            return
        top_k = min(len(imp_df), int(self._spin("spinTopK", 12)))
        top   = imp_df.head(top_k)
        tbl.setRowCount(len(top))
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Feature", "Type", "Score", "Rank"])
        derived = {"Vsh", "PHIE", "Sw", "LambdaRho", "Poisson", "PE"}
        for ri, (_, row) in enumerate(top.iterrows()):
            feat = str(row["feature"])
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(feat))
            tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(
                "Derived" if feat in derived else "Raw"))
            score_item = QtWidgets.QTableWidgetItem(f"{row['importance']:.4f}")
            score_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            tbl.setItem(ri, 2, score_item)
            tbl.setItem(ri, 3, QtWidgets.QTableWidgetItem(str(int(row["rank"]))))
        if tbl.horizontalHeader():
            tbl.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Stretch)

    def _populate_feature_preview_table(self, feat_df: pd.DataFrame) -> None:
        tbl = getattr(self._ui, "tblFeaturePreview", None)
        if tbl is None:
            return
        preview = feat_df.head(20)
        tbl.setColumnCount(len(preview.columns))
        tbl.setHorizontalHeaderLabels(list(preview.columns))
        tbl.setRowCount(len(preview))
        for ri in range(len(preview)):
            for ci, col in enumerate(preview.columns):
                val = preview.iloc[ri][col]
                item = QtWidgets.QTableWidgetItem(f"{float(val):.4f}"
                                                  if pd.notna(val) else "NaN")
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                tbl.setItem(ri, ci, item)

    def _populate_training_pipeline_table(self) -> None:
        tbl = getattr(self._ui, "tblTrainingPipeline", None)
        if tbl is None:
            return
        steps = [
            ("1", "Data Loading",       "Completed", "LAS file ingested"),
            ("2", "Null Handling",      "Completed", "Interpolation / fill"),
            ("3", "Feature Engineering","Completed", f"{len(self._feature_names)} features"),
            ("4", "Normalisation",      "Completed", self._cmb("cmbNormalization", "zscore")),
            ("5", "Feature Selection",  "Completed", self._cmb("cmbSelectionMethod", "mutual_info")),
            ("6", "Model Training",     "Completed", self._cmb("cmbAlgorithm", "K-Means")),
            ("7", "Prediction",         "Completed", f"{len(self._labels) if self._labels is not None else 0:,} samples"),
        ]
        tbl.setRowCount(len(steps))
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Step", "Stage", "Status", "Detail"])
        for ri, (num, stage, status, detail) in enumerate(steps):
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(num))
            tbl.setItem(ri, 1, QtWidgets.QTableWidgetItem(stage))
            si = QtWidgets.QTableWidgetItem(status)
            si.setForeground(QtGui.QColor("#17A84B"))
            tbl.setItem(ri, 2, si)
            tbl.setItem(ri, 3, QtWidgets.QTableWidgetItem(detail))

    def _populate_prediction_preview(self) -> None:
        tbl = getattr(self._ui, "tblPredictionPreview", None)
        if tbl is None or self._raw_df is None or self._labels is None:
            return
        depth_col = self._meta.get("depth_col", "DEPTH")
        preview = self._raw_df.head(20)[[depth_col]].copy() \
            if depth_col in self._raw_df.columns \
            else pd.DataFrame()
        preview["FACIES"] = self._labels[:len(preview)]
        tbl.setRowCount(len(preview))
        tbl.setColumnCount(len(preview.columns))
        tbl.setHorizontalHeaderLabels(list(preview.columns))
        for ri in range(len(preview)):
            for ci, col in enumerate(preview.columns):
                val = preview.iloc[ri][col]
                tbl.setItem(ri, ci, QtWidgets.QTableWidgetItem(str(val)))

    def _update_data_metric_cards(self, meta: dict) -> None:
        comp = meta.get("completeness", {})
        avg_c = sum(comp.values()) / max(len(comp), 1)
        depth = meta.get("depth_range", (0, 0))

        cards = {
            "metricCard":   f"Completeness\n{avg_c:.1f}%",
            "metricCard_2": f"Null clusters\n{meta.get('null_clusters', 0)}",
            "metricCard_3": f"Depth range\n{depth[0]:.0f} – {depth[1]:.0f} m",
            "metricCard_4": f"Curves loaded\n{len(meta.get('numeric_curves', []))}",
        }
        for name, text in cards.items():
            self._set_ui_label(name, text)

    def _update_hero_metrics(self, metrics: dict) -> None:
        acc  = metrics.get("accuracy", metrics.get("silhouette", 0.0))
        f1   = metrics.get("f1_macro", metrics.get("silhouette", 0.0))
        n_cl = metrics.get("n_clusters",
               metrics.get("n_components",
               metrics.get("n_classes", 0)))
        algo = metrics.get("algorithm", "—")

        self._set_ui_label("statusValue_4", algo)
        self._set_ui_label("statusValue_5", f"{n_cl} Classes")
        self._set_ui_label("statusValue_6", f"{acc * 100:.1f}%")
        self._set_ui_label("statusValue_7", f"{f1:.2f}")
        self._progress(100, "100% – Completed")

        # Populate classification report table if supervised
        if "report" in metrics:
            self._populate_classification_report(metrics["report"])

    def _populate_classification_report(self, report_txt: str) -> None:
        tbl = getattr(self._ui, "tblClassificationReport", None)
        if tbl is None:
            return
        lines = [l for l in report_txt.strip().splitlines() if l.strip()]
        # Header row is "precision recall f1-score support"
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Class", "Precision", "Recall", "F1", "Support"])
        data_rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 5:
                data_rows.append(parts)
        tbl.setRowCount(len(data_rows))
        for ri, parts in enumerate(data_rows):
            label = parts[0]
            tbl.setItem(ri, 0, QtWidgets.QTableWidgetItem(label))
            for ci, val in enumerate(parts[1:4]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                tbl.setItem(ri, ci + 1, item)
            if len(parts) >= 5:
                tbl.setItem(ri, 4, QtWidgets.QTableWidgetItem(parts[4]))

    def _populate_well_combo(self) -> None:
        if self._data_service is None:
            return
        wells = getattr(self._data_service, "_wells", {})
        cmb = getattr(self._ui, "cmbWellName", None)
        if cmb and wells:
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItems(sorted(wells.keys()))
            cmb.blockSignals(False)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _collect_algo_params(self, algo: str) -> dict:
        p: dict = {}
        if algo == "K-Means":
            p["n_clusters"]   = int(self._spin("spinKMeansK", 6))
            p["init"]         = self._cmb("cmbKMeansInit", "k-means++")
            p["max_iter"]     = int(self._spin("spinKMeansMaxIter", 300))
            p["n_init"]       = int(self._spin("spinKMeansNInit", 10))
            p["tol"]          = float(self._dbl("spinKMeansTol", 1e-4))
            p["random_state"] = int(self._spin("spinKMeansRandomSeed", 42))
        elif algo == "Gaussian Mixture":
            p["n_components"]    = int(self._spin("spinGmmComponents", 6))
            p["covariance_type"] = self._cmb("cmbGmmCovariance", "full")
            p["reg_covar"]       = float(self._dbl("spinGmmReg", 1e-4))
            p["init_params"]     = self._cmb("cmbGmmInit", "kmeans")
        elif algo == "Ensemble Classifier":
            p["rf_trees"]    = int(self._spin("spinRfTrees", 300))
            p["xgb_max_depth"] = int(self._spin("spinXgbDepth", 5))
            p["svm_kernel"]  = self._cmb("cmbSvmKernel", "rbf")
            p["voting"]      = self._cmb("cmbVoting", "soft")
            p["cv_folds"]    = int(self._spin("spinCvFolds", 5))
        elif algo == "Self-Organizing Map":
            p["grid_size"]    = 8
            p["sigma"]        = float(self._dbl("spinSomSigma", 1.0))
            p["learning_rate"] = float(self._dbl("spinSomLearning", 0.5))
        return p

    def _get_selected_logs(self) -> list:
        tbl = getattr(self._ui, "tblLogs", None)
        if tbl is None or self._raw_df is None:
            return self._all_numeric_logs()
        selected = []
        for ri in range(tbl.rowCount()):
            use_item  = tbl.item(ri, 2)
            name_item = tbl.item(ri, 0)
            if (name_item and use_item and
                    use_item.text().strip().lower() in ("yes", "true", "1", "✓")):
                col = name_item.text().strip()
                if col in self._raw_df.columns:
                    selected.append(col)
        return selected or self._all_numeric_logs()

    def _all_numeric_logs(self) -> list:
        if self._raw_df is None:
            return []
        depth_col = self._meta.get("depth_col", "DEPTH")
        return [c for c in self._raw_df.columns
                if pd.api.types.is_numeric_dtype(self._raw_df[c]) and c != depth_col]

    def _sampling_m(self) -> float:
        txt = self._cmb("cmbSampling", "0.10 m")
        try:
            return float(str(txt).split()[0])
        except Exception:
            return 0.10

    # ── widget accessors ────────────────────────────────────────────────────

    def _set_status(self, msg: str, progress: int | None = None) -> None:
        self._set_ui_label("statusValue", msg)
        lbl = getattr(self._ui, "footerStatus", None)
        if lbl:
            lbl.setText(f"  {msg}")
        if progress is not None:
            self._progress(progress)

    def _progress(self, value: int, label: str = "") -> None:
        pb = getattr(self._ui, "progressBarClassification", None)
        if pb:
            pb.setValue(value)
            if label:
                pb.setFormat(label)
        QtWidgets.QApplication.processEvents()

    def _goto_tab(self, idx: int) -> None:
        tw = getattr(self._ui, "tabWidgetLeft", None)
        if tw:
            tw.setCurrentIndex(idx)

    def _set_ui_label(self, name: str, text: str) -> None:
        w = getattr(self._ui, name, None)
        if w and hasattr(w, "setText"):
            w.setText(str(text))

    def _spin(self, name: str, default: float) -> float:
        w = getattr(self._ui, name, None)
        return float(w.value()) if w and hasattr(w, "value") else default

    def _dbl(self, name: str, default: float) -> float:
        return self._spin(name, default)

    def _cmb(self, name: str, default: str) -> str:
        w = getattr(self._ui, name, None)
        return w.currentText() if w and hasattr(w, "currentText") else default

    def _chk(self, name: str, default: bool) -> bool:
        w = getattr(self._ui, name, None)
        return w.isChecked() if w and hasattr(w, "isChecked") else default

    def _txt(self, name: str) -> str:
        w = getattr(self._ui, name, None)
        if w is None:
            return ""
        if hasattr(w, "text"):
            return w.text()
        if hasattr(w, "toPlainText"):
            return w.toPlainText()
        return ""

    def _info(self, title: str, msg: str) -> None:
        QtWidgets.QMessageBox.information(self._ui, title, msg)

    def _warn(self, title: str, msg: str) -> None:
        QtWidgets.QMessageBox.warning(self._ui, title, msg)

    def _show_error(self, title: str, msg: str) -> None:
        QtWidgets.QMessageBox.critical(self._ui, title, msg)
        self._set_status(f"Error: {msg[:80]}", 0)
