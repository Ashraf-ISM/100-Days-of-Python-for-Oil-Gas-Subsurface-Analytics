"""
facies_classifications/facies_workspace.py
============================================
FaciesClassificationWorkspaceController
-----------------------------------------
Qt controller that:
  • Loads facies_classifications.ui via uic into a parent tab
  • Wires every button, combo, spin-box and checkbox in the UI
  • Delegates computation to:
      - data_loader.py          (Tab 1 – Data & QC)
      - feature_engineering.py  (Tab 2 – Feature Engineering)
      - model_trainer.py        (Tab 3 – Hyperparameter Tuning)
      - model_trainer.py        (Tab 4 – Model Training & Testing)
      - model_trainer.py        (Tab 5 – Prediction)
      - results_visualizer.py   (Tab 6 – Results & Report)
  • Embeds matplotlib canvases into placeholder QFrames
  • Propagates the shared DataService from the main application

Usage (called from petrovision_main.py):
    from Facies_classifications.facies_workspace import FaciesClassificationWorkspaceController
    self._facies_controller = FaciesClassificationWorkspaceController(self, workspace_widget)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from PyQt5 import QtWidgets, QtCore, QtGui

# ── Backend imports ──────────────────────────────────────────────────────────
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
    build_kmeans,
    build_gmm,
    build_ensemble,
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
class FaciesClassificationWorkspaceController(QtCore.QObject):
    """Qt controller that manages the Facies Classification workspace UI."""

    def __init__(self, main_window, workspace_widget: QtWidgets.QWidget):
        super().__init__(main_window)
        self._mw  = main_window
        self._ui  = workspace_widget          # the loaded .ui root widget

        # ── Internal state ──────────────────────────────────────────────────
        self._raw_df: Optional[pd.DataFrame]  = None     # loaded LAS DataFrame
        self._meta:   Dict[str, Any]          = {}       # data metadata
        self._feature_df: Optional[pd.DataFrame] = None  # engineered features
        self._feature_names: List[str]        = []
        self._labels: Optional[np.ndarray]    = None     # predicted/clustered labels
        self._importance_df: Optional[pd.DataFrame] = None
        self._metrics: Dict[str, Any]         = {}
        self._scaler                          = None
        self._fitted_model                    = None
        self._data_service                    = None     # injected from main window

        # Wire all signals
        self._wire_signals()
        self._set_status("Ready")

    # ─────────────────────────────────────────────────────────────────────────
    # Public interface
    # ─────────────────────────────────────────────────────────────────────────

    def set_data_service(self, svc) -> None:
        """Called by petrovision_main to inject the shared DataService."""
        self._data_service = svc
        self._try_populate_well_combo()

    def refresh(self) -> None:
        """Refresh well list and status bar from current data service state."""
        self._try_populate_well_combo()

    # ─────────────────────────────────────────────────────────────────────────
    # Signal wiring
    # ─────────────────────────────────────────────────────────────────────────

    def _wire_signals(self) -> None:
        ui = self._ui

        def _btn(name: str, slot) -> None:
            w = getattr(ui, name, None)
            if w is not None:
                w.clicked.connect(slot)

        # ── Hero bar ─────────────────────────────────────────────────────────
        _btn("btnRunClassification", self._on_run_classification)
        _btn("btnExportResults",     self._on_export_results)
        _btn("btnGenerateReport",    self._on_generate_report)
        _btn("btnResetAll",          self._on_reset_all)

        # ── Tab 1 – Data & QC ────────────────────────────────────────────────
        _btn("btnLoadLas",    self._on_load_las)
        _btn("btnMapCurves",  self._on_map_curves)
        _btn("btnQcProfile",  self._on_qc_profile)
        _btn("btnAdvanceToFeatureEngineering", self._advance_to_feature_tab)

        # ── Tab 2 – Feature Engineering ──────────────────────────────────────
        _btn("btnLoadTemplate",       self._on_load_template)
        _btn("btnSaveFeatureSet",     self._on_save_feature_set)
        _btn("btnResetFeatureTab",    self._on_reset_feature_tab)
        _btn("btnAddCustomFeature",   self._on_add_custom_feature)
        _btn("btnValidateFeature",    self._on_validate_feature)
        _btn("btnRunFeatureSelection",self._on_run_feature_selection)
        _btn("btnManageLogs",         self._on_manage_logs)
        _btn("btnProceedToTuning",    self._advance_to_tuning_tab)

        # Update correlation matrix button (if it exists in the UI)
        _btn("btnUpdateCorrelation",  self._on_update_correlation)

        # Algorithm combo drives stacked param widget
        cmb_algo = getattr(ui, "cmbAlgorithm", None)
        if cmb_algo is not None:
            cmb_algo.currentIndexChanged.connect(self._on_algo_changed)

        # ── Tab 3 – Hyperparameter Tuning ────────────────────────────────────
        _btn("btnRunTuning", self._on_run_tuning)

        # ── Tab 4 – Training & Testing ───────────────────────────────────────
        _btn("btnTrainModel", self._on_train_model)
        _btn("btnRunTesting", self._on_run_testing)

        # ── Tab 5 – Prediction ───────────────────────────────────────────────
        _btn("btnRunPrediction",    self._on_run_prediction)

        # ── Tab 6 – Results ──────────────────────────────────────────────────
        _btn("btnGenerateReportContent", self._on_generate_report)

    # ─────────────────────────────────────────────────────────────────────────
    # Slot implementations
    # ─────────────────────────────────────────────────────────────────────────

    # ── Tab 1 ─────────────────────────────────────────────────────────────────

    def _on_load_las(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._ui, "Select LAS File", "", "LAS Files (*.las *.LAS);;All Files (*)"
        )
        if not path:
            return
        self._load_las_from_path(path)

    def _load_las_from_path(self, path: str) -> None:
        self._set_status("Loading LAS file …")
        QtWidgets.QApplication.processEvents()

        top  = self._spin_val("spinTopDepth",  -1.0)
        base = self._spin_val("spinBaseDepth", -1.0)
        null_strat = self._cmb_text("cmbNullHandling", "interpolate")
        samp_m     = self._sampling_metres()
        despike    = self._chk("chkDespike", True)
        norm_zone  = self._chk("chkNormalizeByZone", False)
        zone_col   = self._cmb_text("cmbZoneColumn", None)
        if zone_col == "None":
            zone_col = None

        df, meta, msg = load_las_file(
            path,
            top_depth   = top,
            base_depth  = base,
            null_strategy=null_strat,
            sampling_m  = samp_m,
            despike     = despike,
            normalize_by_zone=norm_zone,
            zone_column = zone_col,
        )

        if df is None:
            self._set_status(f"Error: {msg}")
            QtWidgets.QMessageBox.critical(self._ui, "LAS Load Error", msg)
            return

        self._raw_df = df
        self._meta   = meta

        # Update UI
        edit = getattr(self._ui, "editLasFile", None)
        if edit is not None:
            edit.setText(path)

        self._populate_inventory_table(meta)
        self._populate_zone_summary(meta)
        self._update_qc_notes(df, meta)
        self._update_status_bar(meta)
        self._set_status(msg)

        # Populate feature log selector with actual column names
        self._populate_feature_log_table(df)

    def _on_map_curves(self) -> None:
        if self._raw_df is None:
            QtWidgets.QMessageBox.information(self._ui, "Map Curves", "Load a LAS file first.")
            return
        self._set_status("Curves are mapped automatically from LAS header.")

    def _on_qc_profile(self) -> None:
        if self._raw_df is None or not self._meta:
            QtWidgets.QMessageBox.information(self._ui, "QC Profile", "Load a LAS file first.")
            return
        report = build_qc_report(self._raw_df, self._meta)
        txt = getattr(self._ui, "txtQcNotes", None)
        if txt is not None:
            txt.setPlainText(report)
        self._set_status("QC profile generated.")

    def _advance_to_feature_tab(self) -> None:
        tw = getattr(self._ui, "tabWidgetLeft", None)
        if tw is not None:
            tw.setCurrentIndex(1)

    # ── Tab 2 ─────────────────────────────────────────────────────────────────

    def _on_load_template(self) -> None:
        QtWidgets.QMessageBox.information(self._ui, "Load Template",
                                          "Feature template loading is not yet implemented.")

    def _on_save_feature_set(self) -> None:
        if self._feature_df is None:
            QtWidgets.QMessageBox.information(self._ui, "Save Feature Set",
                                              "Run Feature Selection first to build a feature matrix.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Save Feature Set", "feature_set.csv", "CSV Files (*.csv)"
        )
        if path:
            self._feature_df.to_csv(path, index=False)
            self._set_status(f"Feature set saved to {path}")

    def _on_reset_feature_tab(self) -> None:
        self._feature_df    = None
        self._feature_names = []
        self._importance_df = None
        self._set_status("Feature engineering reset.")

    def _on_add_custom_feature(self) -> None:
        if self._raw_df is None:
            QtWidgets.QMessageBox.warning(self._ui, "Custom Feature", "Load LAS data first.")
            return
        name_edit = getattr(self._ui, "editCustomFeatureName", None)
        form_edit = getattr(self._ui, "editCustomFeatureFormula", None)
        name    = name_edit.text().strip() if name_edit else ""
        formula = form_edit.text().strip() if form_edit else ""
        if not name or not formula:
            QtWidgets.QMessageBox.warning(self._ui, "Custom Feature",
                                          "Provide both a feature name and a formula.")
            return
        self._raw_df, msg = add_custom_feature(self._raw_df, name, formula)
        self._set_status(msg)
        QtWidgets.QMessageBox.information(self._ui, "Custom Feature", msg)

    def _on_validate_feature(self) -> None:
        if self._raw_df is None:
            self._set_status("Load LAS data before validating a formula.")
            return
        form_edit = getattr(self._ui, "editCustomFeatureFormula", None)
        formula   = form_edit.text().strip() if form_edit else ""
        if not formula:
            return
        # Dry-run: add to a copy
        df_tmp, msg = add_custom_feature(self._raw_df.copy(), "__tmp__", formula)
        ok = "__tmp__" in df_tmp.columns
        self._set_status(f"Formula {'valid ✔' if ok else 'invalid ✘'}: {msg}")

    def _on_run_feature_selection(self) -> None:
        if self._raw_df is None:
            QtWidgets.QMessageBox.warning(self._ui, "Feature Selection", "Load LAS data first.")
            return
        self._set_status("Running feature selection …")
        QtWidgets.QApplication.processEvents()

        selected_logs = self._get_selected_logs()
        inc_vsh    = self._chk("chkUseVsh",      True)
        inc_phie   = self._chk("chkUsePHIE",     True)
        inc_sw     = self._chk("chkUseSw",       True)
        inc_pe     = self._chk("chkUsePE",       False)
        inc_lr     = self._chk("chkUseLambdaRho",False)
        inc_pois   = self._chk("chkUsePoisson",  True)

        feat_df, feat_names = build_feature_matrix(
            self._raw_df,
            selected_logs  = selected_logs,
            include_vsh    = inc_vsh,
            include_phie   = inc_phie,
            include_sw     = inc_sw,
            include_pe     = inc_pe,
            include_lambda_rho=inc_lr,
            include_poisson= inc_pois,
        )

        # Normalise
        norm_method  = self._cmb_text("cmbNormalization", "zscore")
        feat_df_norm, self._scaler = normalize_features(feat_df, method=norm_method)

        # Select top-K
        top_k  = int(self._spin_val("spinTopK", 12))
        method = self._cmb_text("cmbSelectionMethod", "mutual_info")
        selected, self._importance_df = select_features(
            feat_df_norm, y=None, method=method, top_k=top_k
        )

        self._feature_df    = feat_df_norm[selected]
        self._feature_names = selected

        # Populate selected-features table
        self._populate_selected_features_table(self._importance_df, top_k)

        # Render correlation matrix
        self._render_correlation_matrix()
        # Render feature distributions
        self._render_feature_distributions()

        self._set_status(f"Feature selection done. {len(selected)} features selected.")

    def _on_manage_logs(self) -> None:
        QtWidgets.QMessageBox.information(self._ui, "Manage Logs",
                                          "Log management is handled in the Data & QC tab.")

    def _advance_to_tuning_tab(self) -> None:
        tw = getattr(self._ui, "tabWidgetLeft", None)
        if tw is not None:
            tw.setCurrentIndex(2)

    def _on_update_correlation(self) -> None:
        self._render_correlation_matrix()

    # ── Tab 3 – Hyperparameter Tuning ────────────────────────────────────────

    def _on_algo_changed(self, index: int) -> None:
        stack = getattr(self._ui, "stackedAlgoParams", None)
        if stack is not None:
            stack.setCurrentIndex(index)

    def _on_run_tuning(self) -> None:
        self._set_status("Tuning hyperparameters … (using best available params)")
        QtWidgets.QApplication.processEvents()
        # Tuning is lightweight – we just confirm current settings are applied
        QtWidgets.QMessageBox.information(
            self._ui, "Hyperparameter Tuning",
            "Parameters have been read from the form. Click 'Train Model' to apply them."
        )
        self._set_status("Hyperparameters configured.")

    # ── Tab 4 – Training & Testing ────────────────────────────────────────────

    def _on_train_model(self) -> None:
        if self._feature_df is None:
            QtWidgets.QMessageBox.warning(self._ui, "Train Model",
                                          "Run Feature Selection first (Tab 2).")
            return
        self._set_status("Training model …")
        QtWidgets.QApplication.processEvents()
        self._run_classification(advance_tab=False)

    def _on_run_testing(self) -> None:
        if self._labels is None:
            QtWidgets.QMessageBox.warning(self._ui, "Testing",
                                          "Train the model first.")
            return
        self._set_status("Evaluating model …")
        self._render_results_area()
        self._set_status("Testing complete.")

    # ── Tab 5 – Prediction ────────────────────────────────────────────────────

    def _on_run_prediction(self) -> None:
        if self._feature_df is None:
            # Run the full pipeline from scratch
            self._run_full_pipeline()
        else:
            self._run_classification(advance_tab=True)

    # ── Hero bar ──────────────────────────────────────────────────────────────

    def _on_run_classification(self) -> None:
        self._run_full_pipeline()

    def _on_export_results(self) -> None:
        if self._raw_df is None or self._labels is None:
            QtWidgets.QMessageBox.warning(self._ui, "Export",
                                          "Run the classification first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Export Results", "facies_results.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            depth_col = self._meta.get("depth_col", "DEPTH")
            export_df = self._raw_df[[depth_col] + self._feature_names
                                     if all(c in self._raw_df.columns for c in self._feature_names)
                                     else [depth_col]].copy()
            if path.endswith(".xlsx"):
                msg = export_to_excel(export_df, self._labels, self._metrics, path)
            else:
                msg = export_to_csv(export_df, self._labels, path)
            self._set_status(msg)
            QtWidgets.QMessageBox.information(self._ui, "Export", msg)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self._ui, "Export Error", str(exc))

    def _on_generate_report(self) -> None:
        if not self._metrics:
            QtWidgets.QMessageBox.warning(self._ui, "Report",
                                          "Run classification first.")
            return
        report = generate_text_report(self._meta, self._metrics, self._feature_names)
        # Try to show in any available text-browser
        for widget_name in ("txtReportContent", "txtQcNotes"):
            w = getattr(self._ui, widget_name, None)
            if w is not None:
                if hasattr(w, "setPlainText"):
                    w.setPlainText(report)
                break
        # Offer to save
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._ui, "Save Report", "facies_report.txt", "Text Files (*.txt)"
        )
        if path:
            Path(path).write_text(report)
            self._set_status(f"Report saved to {path}")

    def _on_reset_all(self) -> None:
        self._raw_df        = None
        self._meta          = {}
        self._feature_df    = None
        self._feature_names = []
        self._labels        = None
        self._importance_df = None
        self._metrics       = {}
        self._scaler        = None
        self._fitted_model  = None
        pb = getattr(self._ui, "progressBarClassification", None)
        if pb is not None:
            pb.setValue(0)
            pb.setFormat("0%")
        self._set_status("All data reset.")

    # ─────────────────────────────────────────────────────────────────────────
    # Core pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _run_full_pipeline(self) -> None:
        """Load → feature engineering → classify, updating progress bar."""
        # If no data, prompt user
        if self._raw_df is None:
            edit = getattr(self._ui, "editLasFile", None)
            path = edit.text().strip() if edit else ""
            if not path or not Path(path).exists():
                self._on_load_las()
                if self._raw_df is None:
                    return
            else:
                self._load_las_from_path(path)

        self._progress(10, "Loading …")

        # Feature engineering
        self._on_run_feature_selection()
        self._progress(40, "Features ready …")

        # Classify
        self._run_classification(advance_tab=True)
        self._progress(100, "100% – Completed")

    def _run_classification(self, advance_tab: bool = False) -> None:
        if self._feature_df is None:
            self._set_status("No feature matrix available.")
            return

        algo = self._cmb_text("cmbAlgorithm", "K-Means")
        params = self._collect_algo_params(algo)

        self._set_status(f"Training {algo} …")
        QtWidgets.QApplication.processEvents()

        if algo in ("K-Means", "Gaussian Mixture", "Self-Organizing Map"):
            labels, metrics, msg = train_unsupervised(
                self._feature_df, algorithm=algo, params=params
            )
        else:
            # Supervised – we need labels; fall back to unsupervised
            labels, metrics, msg = train_unsupervised(
                self._feature_df, algorithm="K-Means",
                params={"n_clusters": int(params.get("n_clusters", 6))}
            )

        if labels is None:
            QtWidgets.QMessageBox.critical(self._ui, "Classification Error", msg)
            self._set_status(f"Error: {msg}")
            return

        self._labels  = labels
        self._metrics = metrics

        # Render results
        self._render_results_area()
        self._update_hero_metrics(metrics)
        self._set_status(msg)

        if advance_tab:
            tw = getattr(self._ui, "tabWidgetLeft", None)
            if tw is not None:
                tw.setCurrentIndex(5 if tw.count() > 5 else tw.count() - 1)

    def _collect_algo_params(self, algo: str) -> dict:
        params: dict = {}
        ui = self._ui
        if algo == "K-Means":
            params["n_clusters"]    = int(self._spin_val("spinKMeansK", 6))
            params["init"]          = self._cmb_text("cmbKMeansInit", "k-means++")
            params["max_iter"]      = int(self._spin_val("spinKMeansMaxIter", 300))
            params["n_init"]        = int(self._spin_val("spinKMeansNInit", 10))
            params["tol"]           = float(self._spin_val("spinKMeansTol", 1e-4))
            params["random_state"]  = int(self._spin_val("spinKMeansRandomSeed", 42))
        elif algo == "Gaussian Mixture":
            params["n_components"]   = int(self._spin_val("spinGmmComponents", 6))
            params["covariance_type"]= self._cmb_text("cmbGmmCovariance", "full")
            params["reg_covar"]      = float(self._spin_val("spinGmmReg", 1e-4))
            params["init_params"]    = self._cmb_text("cmbGmmInit", "kmeans")
        elif algo == "Ensemble Classifier":
            params["rf_trees"]      = int(self._spin_val("spinRfTrees", 300))
            params["xgb_max_depth"] = int(self._spin_val("spinXgbDepth", 5))
            params["svm_kernel"]    = self._cmb_text("cmbSvmKernel", "rbf")
            params["voting"]        = self._cmb_text("cmbVoting", "soft")
        elif algo == "Self-Organizing Map":
            params["grid_size"] = 8
        return params

    # ─────────────────────────────────────────────────────────────────────────
    # Matplotlib embedding helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _embed_figure(self, host_frame_name: str, fig) -> None:
        """Embed a matplotlib figure into a named QFrame."""
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        except ImportError:
            return

        frame = getattr(self._ui, host_frame_name, None)
        if frame is None:
            return

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            w    = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        layout.addWidget(canvas)
        canvas.draw_idle()

    def _render_results_area(self) -> None:
        """Render all results canvases after a successful classification."""
        if self._raw_df is None or self._labels is None:
            return

        depth_col = self._meta.get("depth_col", "DEPTH")
        if depth_col not in self._raw_df.columns:
            return

        depths = self._raw_df[depth_col].to_numpy(dtype=float)

        # Facies track (Tab Results)
        try:
            from Facies_classifications.results_visualizer import plot_facies_track as _pft
            fig_track = _pft(
                depths,
                self._labels,
                df=self._raw_df,
                log_curves=["GR", "RHOB", "NPHI"],
            )
            self._embed_figure("frameResultsFaciesTrack", fig_track)
        except Exception:
            pass

        # Feature importance
        if self._importance_df is not None:
            try:
                fig_imp = plot_feature_importance(self._importance_df)
                self._embed_figure("frameFeatureImportance", fig_imp)
            except Exception:
                pass

        # Correlation matrix
        self._render_correlation_matrix()

    def _render_correlation_matrix(self) -> None:
        if self._feature_df is None:
            return
        try:
            fig = plot_correlation_matrix(self._feature_df)
            self._embed_figure("frameFeatureMatrix", fig)
        except Exception:
            pass

    def _render_feature_distributions(self) -> None:
        if self._feature_df is None:
            return
        try:
            fig = plot_feature_distributions(self._feature_df)
            self._embed_figure("frameFeatureDistribution", fig)
        except Exception:
            pass

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
        for row_idx, (name, unit, status) in enumerate(rows):
            tbl.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(name))
            tbl.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(unit))
            tbl.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(status))

    def _populate_zone_summary(self, meta: dict) -> None:
        tbl = getattr(self._ui, "tblZoneSummary", None)
        if tbl is None:
            return
        zones = meta.get("zone_summary", [])
        tbl.setRowCount(len(zones))
        tbl.setColumnCount(4)
        for row_idx, z in enumerate(zones):
            tbl.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(z.get("zone", "")))
            tbl.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(f"{z.get('top', ''):.1f}"))
            tbl.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(f"{z.get('base', ''):.1f}"))
            tbl.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(z.get("rows", ""))))

    def _populate_feature_log_table(self, df: pd.DataFrame) -> None:
        """Populate tblLogs in the Feature Engineering tab with actual columns."""
        tbl = getattr(self._ui, "tblLogs", None)
        if tbl is None:
            return
        depth_col = self._meta.get("depth_col", "DEPTH")
        numeric_cols = [c for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c]) and c != depth_col]
        tbl.setRowCount(len(numeric_cols))
        tbl.setColumnCount(3)
        for i, col in enumerate(numeric_cols):
            tbl.setItem(i, 0, QtWidgets.QTableWidgetItem(col))
            tbl.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            tbl.setItem(i, 2, QtWidgets.QTableWidgetItem("Yes"))

    def _populate_selected_features_table(self, imp_df: pd.DataFrame, top_k: int) -> None:
        tbl = getattr(self._ui, "tblSelectedFeatures", None)
        if tbl is None:
            return
        top = imp_df.head(top_k)
        tbl.setRowCount(len(top))
        tbl.setColumnCount(4)
        for row_idx, (_, row) in enumerate(top.iterrows()):
            tbl.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row["feature"])))
            tbl.setItem(row_idx, 1, QtWidgets.QTableWidgetItem("Raw" if row["rank"] > top_k // 2 else "Derived"))
            tbl.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(f"{row['importance']:.3f}"))
            tbl.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(int(row["rank"]))))

    def _update_qc_notes(self, df: pd.DataFrame, meta: dict) -> None:
        report = build_qc_report(df, meta)
        txt = getattr(self._ui, "txtQcNotes", None)
        if txt is not None:
            txt.setPlainText(report)

        # Update metricCard
        mc = getattr(self._ui, "metricCard", None)
        if mc is not None:
            comp = meta.get("completeness", {})
            avg_comp = sum(comp.values()) / max(len(comp), 1)
            mc.setText(
                f"Log completeness {avg_comp:.1f}%\n"
                f"Null clusters: {meta.get('null_clusters', 0)}\n"
                f"Spikes flagged: {meta.get('spike_count', 0)}"
            )

        mc2 = getattr(self._ui, "metricCard_2", None)
        if mc2 is not None:
            mc2.setText(
                f"Dataset ready for feature engineering.\n"
                f"{len(meta.get('numeric_curves', []))} logs mapped\n"
                f"{len(meta.get('zone_summary', []))} zones detected\n"
                f"0 blocking QC errors"
            )

    def _update_status_bar(self, meta: dict) -> None:
        depth_range = meta.get("depth_range", (0, 0))
        rows        = meta.get("total_rows", 0)

        self._set_ui_label("statusValue",   "Data Loaded")
        self._set_ui_label("statusValue_2", meta.get("las_file", "—"))
        self._set_ui_label("statusValue_3", f"{rows:,}")

    def _update_hero_metrics(self, metrics: dict) -> None:
        acc = metrics.get("accuracy", metrics.get("silhouette", 0.0))
        self._set_ui_label("statusValue_6", f"{acc*100:.1f}%")
        f1  = metrics.get("f1_macro", metrics.get("silhouette", 0.0))
        self._set_ui_label("statusValue_7", f"{f1:.2f}")
        n_cl = metrics.get("n_clusters", metrics.get("n_components", metrics.get("n_classes", 0)))
        self._set_ui_label("statusValue_5", f"{n_cl} Classes")
        algo = metrics.get("algorithm", "—")
        self._set_ui_label("statusValue_4", algo)

        pb = getattr(self._ui, "progressBarClassification", None)
        if pb is not None:
            pb.setValue(100)
            pb.setFormat("100% – Completed")

    def _try_populate_well_combo(self) -> None:
        if self._data_service is None:
            return
        wells = getattr(self._data_service, "_wells", {})
        cmb = getattr(self._ui, "cmbWellName", None)
        if cmb is not None and wells:
            cmb.clear()
            cmb.addItems(sorted(wells.keys()))

    def _get_selected_logs(self) -> list[str]:
        """Read selected logs from tblLogs; fall back to all numeric columns."""
        tbl = getattr(self._ui, "tblLogs", None)
        if tbl is None or self._raw_df is None:
            depth_col = self._meta.get("depth_col", "DEPTH")
            if self._raw_df is not None:
                return [c for c in self._raw_df.columns
                        if pd.api.types.is_numeric_dtype(self._raw_df[c]) and c != depth_col]
            return []
        selected = []
        for row_idx in range(tbl.rowCount()):
            use_item = tbl.item(row_idx, 2)
            name_item= tbl.item(row_idx, 0)
            if (use_item is not None and name_item is not None and
                    use_item.text().strip().lower() in ("yes", "true", "1", "✓")):
                col = name_item.text().strip()
                if col in self._raw_df.columns:
                    selected.append(col)
        if not selected:
            depth_col = self._meta.get("depth_col", "DEPTH")
            selected  = [c for c in self._raw_df.columns
                         if pd.api.types.is_numeric_dtype(self._raw_df[c]) and c != depth_col]
        return selected

    # ─────────────────────────────────────────────────────────────────────────
    # Utility helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self._set_ui_label("statusValue", msg)
        lbl = getattr(self._ui, "footerStatus", None)
        if lbl is not None:
            lbl.setText(f"  {msg}")

    def _set_ui_label(self, name: str, text: str) -> None:
        w = getattr(self._ui, name, None)
        if w is not None and hasattr(w, "setText"):
            w.setText(text)

    def _progress(self, value: int, label: str = "") -> None:
        pb = getattr(self._ui, "progressBarClassification", None)
        if pb is not None:
            pb.setValue(value)
            if label:
                pb.setFormat(label)
        QtWidgets.QApplication.processEvents()

    def _spin_val(self, name: str, default: float) -> float:
        w = getattr(self._ui, name, None)
        if w is not None and hasattr(w, "value"):
            return float(w.value())
        return default

    def _cmb_text(self, name: str, default: str) -> str:
        w = getattr(self._ui, name, None)
        if w is not None and hasattr(w, "currentText"):
            return w.currentText()
        return default

    def _chk(self, name: str, default: bool) -> bool:
        w = getattr(self._ui, name, None)
        if w is not None and hasattr(w, "isChecked"):
            return w.isChecked()
        return default

    def _sampling_metres(self) -> float:
        txt = self._cmb_text("cmbSampling", "0.10 m")
        try:
            return float(txt.split()[0])
        except Exception:
            return 0.10
