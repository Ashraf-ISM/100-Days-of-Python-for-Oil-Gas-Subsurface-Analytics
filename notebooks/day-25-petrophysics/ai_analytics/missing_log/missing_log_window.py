from __future__ import annotations
import os
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import pandas as pd
from .prediction_engine import MissingLogEngine

class MissingLogPredictionWindow(QtWidgets.QWidget):
    """
    Controller/Window for the Missing Log Prediction module.
    Handles data loading from PetroARX project or external files,
    and manages the ML prediction workflow.
    """
    def __init__(self, ui_dir: Path, parent=None):
        super().__init__(parent)
        self.ui_dir = ui_dir
        ui_path = ui_dir / "MissingLogPrediction.ui"
        uic.loadUi(str(ui_path), self)
        
        self.setWindowTitle("PetroARX AI Analytics — Missing Log Prediction")
        self._data_service = None
        self._df = None
        self._engine = None
        
        self._setup_connections()
        self._init_ui_state()

    def _setup_connections(self):
        """Connect UI signals to handlers."""
        # Data source buttons (we will add these to the UI)
        if hasattr(self, "btnLoadFromProject"):
            self.btnLoadFromProject.clicked.connect(self.load_from_active_well)
        if hasattr(self, "btnImportExternalLAS"):
            self.btnImportExternalLAS.clicked.connect(self.import_external_las)
            
        # Navigation buttons
        if hasattr(self, "btnDocumentation"):
            self.btnDocumentation.clicked.connect(self._show_help)
        if hasattr(self, "btnHowItWorks"):
            self.btnHowItWorks.clicked.connect(self._show_help)
            
        # Target log selection signal
        if hasattr(self, "cboTargetLog"):
            self.cboTargetLog.currentTextChanged.connect(self._on_target_log_changed)

    def _init_ui_state(self):
        """Initialize labels and tables to empty/default states."""
        if hasattr(self, "lblDataPtsVal"): self.lblDataPtsVal.setText("-")
        if hasattr(self, "lblMissingVal"): self.lblMissingVal.setText("-")
        if hasattr(self, "lblDepthVal"): self.lblDepthVal.setText("-")

    def set_data_service(self, data_service):
        """Inject the PetroARX data service."""
        self._data_service = data_service
        self.load_from_active_well() # Auto-load current well if available

    def load_from_active_well(self):
        """Load data from the currently active well in PetroARX."""
        if self._data_service is None:
            return
            
        well = self._data_service._get_current_well()
        if well is None:
            QtWidgets.QMessageBox.warning(self, "Data Loading", "No active well found in the project.")
            return
            
        self._df = well.data.copy()
        self._engine = MissingLogEngine(self._df)
        well_name = well.name
        self._update_data_display(f"Project Well: {well_name}")
        self._populate_curve_lists()

    def import_external_las(self):
        """Allow user to upload a LAS file separately."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import LAS Data", "", "LAS Files (*.las);;All Files (*.*)"
        )
        if not file_path:
            return
            
        try:
            from core.well_data_loader import load_well
            well, msg = load_well(file_path, replace_nulls=True)
            self._df = well.data
            self._engine = MissingLogEngine(self._df)
            self._update_data_display(f"External File: {Path(file_path).name}")
            self._populate_curve_lists()
            QtWidgets.QMessageBox.information(self, "Import Success", f"Successfully loaded data from {Path(file_path).name}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import Error", f"Failed to load external LAS file:\n{e}")

    def _update_data_display(self, source_name: str = ""):
        """Update UI labels with data statistics."""
        if self._df is None or self._df.empty or self._engine is None:
            return
            
        cur_log = self.cboTargetLog.currentText()
        if not cur_log:
            return

        stats = self._engine.get_log_statistics(cur_log)
        
        if stats:
            if hasattr(self, "lblDataPtsVal"): 
                self.lblDataPtsVal.setText(f"{stats['total']:,}")
            if hasattr(self, "lblMissingVal"): 
                self.lblMissingVal.setText(f"{stats['missing']:,} ({stats['missing_pct']:.1f}%)")
        
        depth_col = next((c for c in self._df.columns if c.upper() in ["DEPTH", "DEPT", "MD"]), None)
        if depth_col is not None:
            d_min = self._df[depth_col].min()
            d_max = self._df[depth_col].max()
            if hasattr(self, "lblDepthVal"): 
                self.lblDepthVal.setText(f"{d_min:.1f} – {d_max:.1f} m")

    def _on_target_log_changed(self, log_name: str):
        """Called when user picks a different target log."""
        self._update_data_display()
        # Optionally update suggested features
        # self._update_feature_suggestions(log_name)

    def _populate_curve_lists(self):
        """Populate comboboxes and dynamically create checkboxes for features."""
        if self._df is None:
            return
            
        curves = list(self._df.columns)
        
        # 1. Update Target Log Dropdown
        if hasattr(self, "cboTargetLog"):
            self.cboTargetLog.blockSignals(True)
            self.cboTargetLog.clear()
            self.cboTargetLog.addItems(curves)
            self.cboTargetLog.blockSignals(False)
            # Trigger initial stats
            self._update_data_display()

        # 2. Update Feature Checkboxes
        if hasattr(self, "lytFeatures"):
            # Clear existing checkboxes
            while self.lytFeatures.count():
                child = self.lytFeatures.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Add new checkboxes for all curves
            self._feature_checkboxes = []
            for curve in curves:
                chk = QtWidgets.QCheckBox(curve)
                # By default, check all numeric curves except target log? 
                # Or just let user choose.
                chk.setChecked(False) 
                self.lytFeatures.addWidget(chk)
                self._feature_checkboxes.append(chk)
            
            # Add a spacer at the bottom of the layout to keep checkboxes at top
            self.lytFeatures.addStretch()

    def get_selected_features(self) -> list[str]:
        """Return list of names for all checked feature logs."""
        if not hasattr(self, "_feature_checkboxes"):
            return []
        return [chk.text() for chk in self._feature_checkboxes if chk.isChecked()]

    def _show_help(self):
        """Show documentation or tutorial."""
        QtWidgets.QMessageBox.information(self, "Documentation", "Missing Log Prediction workflow guide comes here.")
