"""
missing_log_panel.py
Professional PyQt5 panel for Missing Log Prediction.
Replaces the old .ui file with a pure Python implementation matching the PetroArx design.
"""
from __future__ import annotations

from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui
import pandas as pd

from .prediction_engine          import MissingLogEngine
from .correlation_viewer         import CorrelationMatrixDialog
from .missing_intervals_viewer   import MissingIntervalsDialog
from .training_controller        import TrainingController
from .model_manager              import ModelManager
from .export_controller          import ExportController
from .actual_vs_predicted_viewer import ActualVsPredictedDialog

# ── UI Design Tokens ─────────────────────────────────────────────────────────
BG_APP       = "#EEF2F7"
BG_CARD      = "#FFFFFF"
BG_HEADER    = "#FFFFFF"
BORDER       = "#E2E8F0"
ACCENT_BLUE  = "#2563EB"
ACCENT_GREEN = "#10B981"
ACCENT_RED   = "#DC2626"
ACCENT_AMBER = "#F59E0B"
TEXT_DARK    = "#1E293B"
TEXT_MED     = "#374151"
TEXT_LIGHT   = "#64748B"

class MissingLogPanel(QtWidgets.QWidget):
    """
    Main widget for the Missing Log Prediction module.
    """
    def __init__(self, ui_dir: Path = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PetroARX AI Analytics — Missing Log Prediction")
        
        # Style the main widget
        self.setStyleSheet(f"background-color: {BG_APP}; font-family: 'Inter', 'Segoe UI', sans-serif;")
        
        # ── state ──────────────────────────────────────────────────────────────
        self._data_service      = None
        self._df: pd.DataFrame | None = None
        self._engine: MissingLogEngine | None = None
        self._feature_checkboxes: list[QtWidgets.QCheckBox] = []
        self._all_wells: dict[str, object] = {}

        # ── service objects ────────────────────────────────────────────────────
        self._trainer   = TrainingController(self)
        self._model_mgr = ModelManager()
        self._exporter  = ExportController()

        self._setup_ui()
        self._init_ui_state()

    # ─────────────────────────────────────────────────────────────────────────
    # UI Setup
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header
        main_layout.addWidget(self._create_header())
        
        # 2. Wizard / Step indicator
        main_layout.addWidget(self._create_wizard_indicator())
        
        # Scroll area for main content
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # 3. Three-column grid
        grid_layout = QtWidgets.QHBoxLayout()
        grid_layout.setSpacing(24)
        
        grid_layout.addWidget(self._create_col1())
        grid_layout.addWidget(self._create_col2())
        grid_layout.addWidget(self._create_col3())
        
        content_layout.addLayout(grid_layout)
        
        # 4. Bottom Tabs
        content_layout.addWidget(self._create_bottom_tabs())
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 5. Bottom Action Bar
        main_layout.addWidget(self._create_action_bar())

    def _create_card(self, title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
        card = QtWidgets.QFrame()
        card.setStyleSheet(f'''
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        ''')
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet(f"color: {TEXT_DARK}; font-weight: bold; font-size: 14px; border: none;")
        layout.addWidget(lbl_title)
        
        # Inner container for contents to avoid border on children
        inner_container = QtWidgets.QWidget()
        inner_container.setStyleSheet("border: none; background: transparent;")
        inner_layout = QtWidgets.QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(8)
        layout.addWidget(inner_container)
        
        return card, inner_layout

    def _create_header(self) -> QtWidgets.QFrame:
        header = QtWidgets.QFrame()
        header.setStyleSheet(f'''
            QFrame {{
                background-color: {BG_HEADER};
                border-bottom: 1px solid {BORDER};
            }}
        ''')
        header.setFixedHeight(64)
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        
        title = QtWidgets.QLabel("Missing Log Prediction")
        title.setStyleSheet(f"color: {TEXT_DARK}; font-size: 18px; font-weight: bold; border: none;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.btnLoadFromProject = self._create_btn("Load from Project", icon="📂", primary=True)
        self.btnLoadFromProject.clicked.connect(self.load_from_active_well)
        layout.addWidget(self.btnLoadFromProject)
        
        self.btnImportExternalLAS = self._create_btn("Upload LAS", icon="📄")
        self.btnImportExternalLAS.clicked.connect(self.import_external_las)
        layout.addWidget(self.btnImportExternalLAS)
        
        self.btnDocumentation = self._create_btn("Documentation", icon="📖")
        self.btnDocumentation.clicked.connect(self._show_help)
        layout.addWidget(self.btnDocumentation)
        
        return header

    def _create_wizard_indicator(self) -> QtWidgets.QFrame:
        wizard = QtWidgets.QFrame()
        wizard.setStyleSheet(f'''
            QFrame {{
                background-color: {BG_CARD};
                border-bottom: 1px solid {BORDER};
            }}
        ''')
        wizard.setFixedHeight(48)
        layout = QtWidgets.QHBoxLayout(wizard)
        layout.setContentsMargins(24, 0, 24, 0)
        
        steps = ["Data", "Configure", "Train", "Diagnose", "Deploy"]
        for i, step in enumerate(steps):
            lbl = QtWidgets.QLabel(f"{i+1}. {step}")
            color = ACCENT_BLUE if i == 0 else TEXT_LIGHT
            weight = "bold" if i == 0 else "normal"
            lbl.setStyleSheet(f"color: {color}; font-weight: {weight}; border: none; font-size: 13px;")
            layout.addWidget(lbl)
            if i < len(steps) - 1:
                arrow = QtWidgets.QLabel("→")
                arrow.setStyleSheet(f"color: {BORDER}; border: none;")
                layout.addWidget(arrow)
        layout.addStretch()
        return wizard

    def _create_col1(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Data Selection Card
        card_ds, lay_ds = self._create_card("Data Selection")
        
        lay_ds.addWidget(QtWidgets.QLabel("Select Well:"))
        self.cboWellSelector = QtWidgets.QComboBox()
        self.cboWellSelector.setStyleSheet(self._combo_style())
        self.cboWellSelector.currentTextChanged.connect(self._on_well_selected)
        lay_ds.addWidget(self.cboWellSelector)
        
        lay_ds.addWidget(QtWidgets.QLabel("Target Log:"))
        self.cboTargetLog = QtWidgets.QComboBox()
        self.cboTargetLog.setStyleSheet(self._combo_style())
        self.cboTargetLog.currentTextChanged.connect(self._on_target_log_changed)
        lay_ds.addWidget(self.cboTargetLog)
        
        stats_layout = QtWidgets.QGridLayout()
        stats_layout.addWidget(QtWidgets.QLabel("Data Points:"), 0, 0)
        self.lblDataPtsVal = QtWidgets.QLabel("—")
        stats_layout.addWidget(self.lblDataPtsVal, 0, 1)
        
        stats_layout.addWidget(QtWidgets.QLabel("Missing:"), 1, 0)
        self.lblMissingVal = QtWidgets.QLabel("—")
        stats_layout.addWidget(self.lblMissingVal, 1, 1)
        
        stats_layout.addWidget(QtWidgets.QLabel("Depth Range:"), 2, 0)
        self.lblDepthVal = QtWidgets.QLabel("—")
        stats_layout.addWidget(self.lblDepthVal, 2, 1)
        
        self.lblUnit = QtWidgets.QLabel("Unit: —")
        stats_layout.addWidget(self.lblUnit, 3, 0, 1, 2)
        
        lay_ds.addLayout(stats_layout)
        
        self.badgeRed = QtWidgets.QLabel("—")
        self.badgeRed.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold;")
        lay_ds.addWidget(self.badgeRed)
        
        self.btnViewIntervals = self._create_btn("View Intervals")
        self.btnViewIntervals.clicked.connect(self._open_missing_intervals)
        lay_ds.addWidget(self.btnViewIntervals)
        
        layout.addWidget(card_ds)
        
        # Input Features Card
        card_feat, lay_feat = self._create_card("Input Features")
        
        toolbar = QtWidgets.QHBoxLayout()
        self.btnAutoSel = self._create_btn("Auto Select")
        self.btnAutoSel.clicked.connect(self._auto_select_features)
        toolbar.addWidget(self.btnAutoSel)
        
        self.btnCorrelation = self._create_btn("Correlation")
        self.btnCorrelation.clicked.connect(self._open_correlation_matrix)
        toolbar.addWidget(self.btnCorrelation)
        
        lay_feat.addLayout(toolbar)
        
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setFixedHeight(150)
        feat_container = QtWidgets.QWidget()
        self.lytFeatures = QtWidgets.QVBoxLayout(feat_container)
        self.lytFeatures.setContentsMargins(0, 0, 0, 0)
        self.lytFeatures.addStretch()
        scroll.setWidget(feat_container)
        lay_feat.addWidget(scroll)
        
        layout.addWidget(card_feat)
        layout.addStretch()
        return col

    def _create_col2(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Model Configuration
        card_cfg, lay_cfg = self._create_card("Model Configuration")
        
        lay_cfg.addWidget(QtWidgets.QLabel("Algorithm:"))
        self.cboAlgorithm = QtWidgets.QComboBox()
        self.cboAlgorithm.addItems(["XGBoost", "Random Forest", "LightGBM", "CatBoost"])
        self.cboAlgorithm.setStyleSheet(self._combo_style())
        lay_cfg.addWidget(self.cboAlgorithm)
        
        lay_cfg.addWidget(QtWidgets.QLabel("Cross Validation Folds:"))
        self.spinCV = QtWidgets.QSpinBox()
        self.spinCV.setRange(2, 10)
        self.spinCV.setValue(5)
        self.spinCV.setStyleSheet(self._input_style())
        lay_cfg.addWidget(self.spinCV)
        
        lay_cfg.addWidget(QtWidgets.QLabel("Test Size (%):"))
        slider_layout = QtWidgets.QHBoxLayout()
        self.sliderTestSize = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sliderTestSize.setRange(10, 50)
        self.sliderTestSize.setValue(20)
        self.lblTestSizeVal = QtWidgets.QLabel("20")
        self.sliderTestSize.valueChanged.connect(lambda v: self.lblTestSizeVal.setText(str(v)))
        slider_layout.addWidget(self.sliderTestSize)
        slider_layout.addWidget(self.lblTestSizeVal)
        lay_cfg.addLayout(slider_layout)
        
        self.chkGPU = QtWidgets.QCheckBox("Enable GPU Acceleration")
        lay_cfg.addWidget(self.chkGPU)
        
        layout.addWidget(card_cfg)
        
        # Training Progress
        card_prog, lay_prog = self._create_card("Training Progress")
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setValue(0)
        self.progressBar.setStyleSheet(f'''
            QProgressBar {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                text-align: center;
                background-color: #F1F5F9;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_BLUE};
                border-radius: 3px;
            }}
        ''')
        lay_prog.addWidget(self.progressBar)
        
        self.lblTrainingStatus = QtWidgets.QLabel("Ready")
        self.lblTrainingStatus.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 12px;")
        lay_prog.addWidget(self.lblTrainingStatus)
        
        self.btnViewTrainingLog = self._create_btn("View Training Log")
        self.btnViewTrainingLog.clicked.connect(self._view_training_log)
        lay_prog.addWidget(self.btnViewTrainingLog)
        
        layout.addWidget(card_prog)
        
        # Prediction Preview placeholder
        card_prev, lay_prev = self._create_card("Prediction Preview")
        self.lblPreview = QtWidgets.QLabel("[ Actual vs Predicted Canvas Placeholder ]")
        self.lblPreview.setAlignment(QtCore.Qt.AlignCenter)
        self.lblPreview.setStyleSheet(f"background-color: #F8FAFC; border: 1px dashed {BORDER}; color: {TEXT_LIGHT};")
        self.lblPreview.setMinimumHeight(120)
        lay_prev.addWidget(self.lblPreview)
        self.btnActualVsPredicted = self._create_btn("Open Full Viewer")
        self.btnActualVsPredicted.clicked.connect(self._open_actual_vs_predicted)
        lay_prev.addWidget(self.btnActualVsPredicted)
        
        layout.addWidget(card_prev)
        layout.addStretch()
        return col

    def _create_col3(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Performance
        card_perf, lay_perf = self._create_card("Performance Metrics")
        
        grid = QtWidgets.QGridLayout()
        self.metrics_labels = {}
        metrics = ["R²", "RMSE", "MAE", "MAPE", "NRMSE", "CCC"]
        for i, m in enumerate(metrics):
            grid.addWidget(QtWidgets.QLabel(f"{m}:"), i//2, (i%2)*2)
            lbl = QtWidgets.QLabel("—")
            lbl.setStyleSheet(f"font-weight: bold; color: {TEXT_DARK};")
            grid.addWidget(lbl, i//2, (i%2)*2 + 1)
            self.metrics_labels[m] = lbl
        lay_perf.addLayout(grid)
        
        self.btnDetailedMetrics = self._create_btn("Detailed Metrics")
        self.btnDetailedMetrics.clicked.connect(self._show_detailed_metrics)
        lay_perf.addWidget(self.btnDetailedMetrics)
        
        layout.addWidget(card_perf)
        
        # Feature Importance
        card_feat, lay_feat = self._create_card("Feature Importance")
        self.lblShap = QtWidgets.QLabel("[ SHAP Bar Chart Placeholder ]")
        self.lblShap.setAlignment(QtCore.Qt.AlignCenter)
        self.lblShap.setStyleSheet(f"background-color: #F8FAFC; border: 1px dashed {BORDER}; color: {TEXT_LIGHT};")
        self.lblShap.setMinimumHeight(120)
        lay_feat.addWidget(self.lblShap)
        self.btnExplainAI = self._create_btn("Explain AI")
        self.btnExplainAI.clicked.connect(self._explain_at_depth)
        lay_feat.addWidget(self.btnExplainAI)
        
        layout.addWidget(card_feat)
        layout.addStretch()
        return col

    def _create_bottom_tabs(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(f'''
            QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 4px; background: {BG_CARD}; }}
            QTabBar::tab {{ background: #F1F5F9; border: 1px solid {BORDER}; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; color: {TEXT_MED}; }}
            QTabBar::tab:selected {{ background: {BG_CARD}; border-bottom-color: {BG_CARD}; color: {ACCENT_BLUE}; font-weight: bold; }}
        ''')
        
        # Just creating empty tabs with buttons to match requested layout
        for title, btns in [
            ("Diagnostics", [("Data Drift", self._view_drift)]),
            ("Feature Engineering", [("Edit Pipeline", self._edit_pipeline)]),
            ("Optimization", [("Optimize", self._run_hyperopt)]),
            ("Deployment", [("Batch Prediction", self._batch_prediction), ("Deploy API", self._deploy_model)])
        ]:
            w = QtWidgets.QWidget()
            l = QtWidgets.QHBoxLayout(w)
            for btn_text, handler in btns:
                btn = self._create_btn(btn_text)
                btn.clicked.connect(handler)
                l.addWidget(btn)
            l.addStretch()
            tabs.addTab(w, title)
            
        return tabs

    def _create_action_bar(self) -> QtWidgets.QFrame:
        bar = QtWidgets.QFrame()
        bar.setStyleSheet(f'''
            QFrame {{
                background-color: {BG_HEADER};
                border-top: 1px solid {BORDER};
            }}
        ''')
        bar.setFixedHeight(64)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        
        self.btnReset = self._create_btn("Reset All")
        self.btnReset.clicked.connect(self._reset_all)
        layout.addWidget(self.btnReset)
        
        layout.addStretch()
        
        self.btnSaveModel = self._create_btn("Save Model")
        self.btnSaveModel.clicked.connect(self._save_model)
        layout.addWidget(self.btnSaveModel)
        
        self.btnExport = self._create_btn("Export Results")
        self.btnExport.clicked.connect(self._export_results)
        layout.addWidget(self.btnExport)
        
        self.btnApply = self._create_btn("Apply Prediction & Save to Well", primary=True)
        self.btnApply.clicked.connect(self._train_and_apply)
        layout.addWidget(self.btnApply)
        
        return bar

    # ── Styling Helpers ──────────────────────────────────────────────────────

    def _create_btn(self, text: str, icon: str = "", primary: bool = False) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(f"{icon} {text}" if icon else text)
        if primary:
            btn.setStyleSheet(f'''
                QPushButton {{
                    background-color: {ACCENT_BLUE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #1D4ED8; }}
            ''')
        else:
            btn.setStyleSheet(f'''
                QPushButton {{
                    background-color: white;
                    color: {TEXT_DARK};
                    border: 1px solid {BORDER};
                    border-radius: 4px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{ background-color: #F8FAFC; }}
            ''')
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        return btn

    def _combo_style(self) -> str:
        return f'''
            QComboBox {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 6px;
                background: white;
                color: {TEXT_DARK};
            }}
        '''

    def _input_style(self) -> str:
        return f'''
            QSpinBox {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 6px;
                background: white;
                color: {TEXT_DARK};
            }}
        '''

    # ─────────────────────────────────────────────────────────────────────────
    # Controller Logic (Copied directly from missing_log_window.py)
    # ─────────────────────────────────────────────────────────────────────────

    def _init_ui_state(self):
        """Set initial placeholder text on stat labels."""
        self.lblDataPtsVal.setText("—")
        self.lblMissingVal.setText("—")
        self.lblDepthVal.setText("—")
        self.lblUnit.setText("Unit: —")
        self.btnViewIntervals.setText("No data loaded")

    def set_data_service(self, data_service):
        self._data_service = data_service
        self._populate_well_selector()
        self.load_from_active_well()

    def _populate_well_selector(self):
        if self._data_service is None:
            return
        self._all_wells = dict(getattr(self._data_service, "_wells", {}))
        self.cboWellSelector.blockSignals(True)
        self.cboWellSelector.clear()
        self.cboWellSelector.addItems(sorted(self._all_wells.keys()))
        cur = getattr(self._data_service, "_current_well", None)
        if cur:
            idx = self.cboWellSelector.findText(cur)
            if idx >= 0:
                self.cboWellSelector.setCurrentIndex(idx)
        self.cboWellSelector.blockSignals(False)

    def _on_well_selected(self, well_name: str):
        well = self._all_wells.get(well_name)
        if well is None:
            return
        self._df = well.data.copy()
        self._engine = MissingLogEngine(self._df)
        self._populate_curve_lists()

    def load_from_active_well(self):
        if self._data_service is None:
            return
        well = self._data_service._get_current_well()
        if well is None:
            QtWidgets.QMessageBox.warning(self, "Data Loading", "No active well found in the project.")
            return
        self._df = well.data.copy()
        self._engine = MissingLogEngine(self._df)
        self._populate_curve_lists()

    def import_external_las(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import LAS Data", "", "LAS Files (*.las *.laz);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            from core.well_data_loader import load_well
            well, _msg = load_well(file_path, replace_nulls=True)
            self._df = well.data
            self._engine = MissingLogEngine(self._df)
            self._populate_curve_lists()
            QtWidgets.QMessageBox.information(self, "Import Success", f"✔  Loaded: {Path(file_path).name}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Import Error", f"Failed to load LAS file:\n{exc}")

    def _populate_curve_lists(self):
        if self._df is None:
            return
        curves = list(self._df.columns)
        self.cboTargetLog.blockSignals(True)
        self.cboTargetLog.clear()
        self.cboTargetLog.addItems(curves)
        self.cboTargetLog.blockSignals(False)

        while self.lytFeatures.count():
            child = self.lytFeatures.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._feature_checkboxes = []
        for curve in curves:
            chk = QtWidgets.QCheckBox(curve)
            chk.setChecked(True)
            self.lytFeatures.addWidget(chk)
            self._feature_checkboxes.append(chk)
        self.lytFeatures.addStretch()

        self._update_data_display()
        self._on_target_log_changed(self.cboTargetLog.currentText())

    def get_selected_features(self) -> list[str]:
        return [c.text() for c in self._feature_checkboxes if c.isChecked()]

    def _on_target_log_changed(self, log_name: str):
        self._update_data_display()
        for chk in self._feature_checkboxes:
            if chk.text() == log_name:
                chk.setChecked(False)
                chk.setEnabled(False)
            else:
                chk.setEnabled(True)

    def _update_data_display(self):
        if self._df is None or self._df.empty or self._engine is None:
            return
        log_name = self.cboTargetLog.currentText()
        if not log_name:
            return

        stats = self._engine.get_log_statistics(log_name)
        if stats:
            self.lblDataPtsVal.setText(f"{stats['total']:,}")
            self.lblMissingVal.setText(f"{stats['missing']:,} ({stats['missing_pct']:.1f}%)")
            self.badgeRed.setText(f"{stats['missing']:,} ({stats['missing_pct']:.1f}%)")

        depth_col = next((c for c in self._df.columns if c.upper() in {"DEPTH","DEPT","MD"}), None)
        if depth_col:
            d_min = self._df[depth_col].min()
            d_max = self._df[depth_col].max()
            self.lblDepthVal.setText(f"{d_min:.1f} – {d_max:.1f} m")

        intervals = self._engine.count_missing_intervals(log_name)
        plural = "interval" if intervals == 1 else "intervals"
        self.btnViewIntervals.setText(f"{intervals} {plural} detected  →")
        self.lblUnit.setText(f"Unit: {self._engine.guess_unit(log_name)}")

    def _open_missing_intervals(self):
        if self._df is None:
            QtWidgets.QMessageBox.information(self, "Missing Intervals", "Load well data first.")
            return
        target = self.cboTargetLog.currentText()
        dlg = MissingIntervalsDialog(self._df, target, parent=self)
        dlg.exec_()

    def _open_correlation_matrix(self):
        if self._df is None:
            QtWidgets.QMessageBox.information(self, "Correlation Matrix", "Load well data first.")
            return
        target = self.cboTargetLog.currentText()
        dlg = CorrelationMatrixDialog(self._df, target, parent=self)
        dlg.exec_()

    def _auto_select_features(self):
        if self._engine is None:
            return
        target = self.cboTargetLog.currentText()
        suggested = self._engine.suggest_features(target)
        for chk in self._feature_checkboxes:
            chk.setChecked(chk.text() in suggested and chk.text() != target)

    def _train_and_apply(self):
        if not getattr(self, "_avp_signal_connected", False):
            self._trainer._worker_finished_signal_proxy = self._on_training_finished
            self._avp_signal_connected = False
        self._trainer.start_training()
        if self._trainer._worker is not None and not getattr(self, "_avp_signal_connected", False):
            self._trainer._worker.finished.connect(self._on_training_finished)
            self._avp_signal_connected = True

    def _on_training_finished(self, result: dict):
        self._open_actual_vs_predicted()
        
        # Also update performance metrics on UI
        if result and "r2" in result:
            self.metrics_labels["R²"].setText(f"{result.get('r2', 0):.4f}")
            self.metrics_labels["RMSE"].setText(f"{result.get('rmse', 0):.4f}")
            self.metrics_labels["MAE"].setText(f"{result.get('mae', 0):.4f}")

    def _open_actual_vs_predicted(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Actual vs Predicted Log", "Please train the model first.")
            return
        if self._df is None:
            QtWidgets.QMessageBox.information(self, "Actual vs Predicted Log", "Load well data first.")
            return
        target = self.cboTargetLog.currentText()
        features = self.get_selected_features()
        dlg = ActualVsPredictedDialog(
            df=self._df, target=target, features=features, result=result, parent=self
        )
        dlg.exec_()

    def _export_results(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Export", "Train the model first.")
            return
        self._exporter.export_results(
            self._df, self.cboTargetLog.currentText(), self.get_selected_features(), result, parent_widget=self
        )

    def _save_model(self):
        result = self._trainer.last_result
        if result is None or result.get("model") is None:
            QtWidgets.QMessageBox.information(self, "Save Model", "Train a model first.")
            return
        meta = {
            "algorithm": result["algorithm"],
            "target": self.cboTargetLog.currentText(),
            "features": self.get_selected_features(),
            "r2": result["r2"],
            "rmse": result["rmse"],
        }
        self._model_mgr.save_model(result["model"], meta, parent_widget=self)

    def _load_model(self):
        model, meta = self._model_mgr.load_model(parent_widget=self)
        if model is not None:
            if meta and "features" in meta:
                for chk in self._feature_checkboxes:
                    chk.setChecked(chk.text() in meta["features"])

    def _batch_prediction(self):
        QtWidgets.QMessageBox.information(self, "Batch Prediction", "Available in the next release.")

    def _deploy_model(self):
        QtWidgets.QMessageBox.information(self, "Deploy Model", "Available in the next release.")

    def _view_training_log(self):
        result = self._trainer.last_result
        if result is None:
            QtWidgets.QMessageBox.information(self, "Training Log", "No training has been run yet.")
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
        QtWidgets.QMessageBox.information(self, "Explain at Depth", "Available in the next release.")

    def _compare_models(self):
        QtWidgets.QMessageBox.information(self, "Compare Models", "Available in the next release.")

    def _edit_pipeline(self):
        QtWidgets.QMessageBox.information(self, "Feature Engineering Pipeline", "Available in the next release.")

    def _run_hyperopt(self):
        QtWidgets.QMessageBox.information(self, "Hyperparameter Optimization", "Available in the next release.")

    def _view_optim_results(self):
        QtWidgets.QMessageBox.information(self, "Optimization Results", "No optimization has been run yet.")

    def _view_drift(self):
        QtWidgets.QMessageBox.information(self, "Data Drift Detection", "Available in the next release.")

    def _reset_all(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Reset All", "Reset all settings and clear loaded data?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self._df = None
        self._engine = None
        self._feature_checkboxes = []
        while self.lytFeatures.count():
            child = self.lytFeatures.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
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
