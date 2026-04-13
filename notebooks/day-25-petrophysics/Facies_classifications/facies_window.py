"""
Facies_classifications/facies_window.py
=========================================
FaciesClassificationWindow
--------------------------
A fully self-contained, standalone QMainWindow that:
  • Loads  ui/facies_classifications.ui  as its central widget
  • Instantiates FaciesClassificationWorkspaceController to wire all logic
  • Receives the shared DataService from the main application (optional)
  • Can pre-select an algorithm (K-Means / GMM / SOM / Ensemble) via open()
  • Supports Ctrl+W / close button to hide (not destroy) so re-opening is fast

Usage from petrovision_main.py:
    from Facies_classifications.facies_window import FaciesClassificationWindow
    self._facies_win = FaciesClassificationWindow(ui_dir, parent=self)
    self._facies_win.set_data_service(data_svc)
    self._facies_win.show_with_algorithm("kmeans")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui, uic


# ── Path gymnastics so we can import sibling packages ───────────────────────
THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Algorithm display names used in cmbAlgorithm (must match .ui exactly)
_ALGO_TEXT = {
    "kmeans":       "K-Means",
    "gmm":          "Gaussian Mixture",
    "som":          "Self-Organizing Map",
    "ensemble":     "Ensemble Classifier",
    "randomforest": "Ensemble Classifier",   # RF lives inside Ensemble page
}


class FaciesClassificationWindow(QtWidgets.QMainWindow):
    """Standalone window wrapping facies_classifications.ui."""

    # Emitted when the window is closed so the parent can react if needed
    closed = QtCore.pyqtSignal()

    def __init__(self, ui_dir: Path, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._ui_dir = ui_dir
        self._controller = None
        self._data_service = None

        self._build_ui()
        self._apply_window_chrome()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def set_data_service(self, svc) -> None:
        """Inject the shared DataService (called from the main window)."""
        self._data_service = svc
        if self._controller is not None and hasattr(self._controller, "set_data_service"):
            self._controller.set_data_service(svc)

    def show_with_algorithm(self, algorithm: str | None = None) -> None:
        """Raise the window and optionally pre-select *algorithm* in the combo."""
        self._pre_select_algorithm(algorithm)
        self.show()
        self.raise_()
        self.activateWindow()

    def refresh(self) -> None:
        """Refresh well lists etc. after data changes in the main window."""
        if self._data_service is not None:
            self.set_data_service(self._data_service)
        if self._controller is not None and hasattr(self._controller, "refresh"):
            try:
                self._controller.refresh()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Load the Qt Designer UI and wire the controller."""
        ui_path = self._ui_dir / "facies_classifications.ui"
        try:
            self._workspace = uic.loadUi(str(ui_path))
            # Make the loaded widget behave as a plain widget (not a window)
            self._workspace.setWindowFlags(QtCore.Qt.Widget)
        except Exception as exc:
            self._workspace = self._error_widget(
                f"Could not load facies_classifications.ui:\n{exc}"
            )

        # Wrap in a scroll area so the large UI doesn't get clipped on small screens
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._workspace)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setCentralWidget(scroll)

        # Instantiate the backend controller
        try:
            from Facies_classifications.facies_workspace import (
                FaciesClassificationWorkspaceController,
            )
            self._controller = FaciesClassificationWorkspaceController(
                self, self._workspace
            )
        except Exception as exc:
            err = QtWidgets.QLabel(
                f"Facies controller failed to initialise:\n{exc}"
            )
            err.setAlignment(QtCore.Qt.AlignCenter)
            err.setStyleSheet("color:#FF6B6B;font-size:12px;font-weight:600;padding:20px;")
            # Overlay the error label on top of whatever loaded
            overlay = QtWidgets.QWidget(self._workspace)
            overlay_layout = QtWidgets.QVBoxLayout(overlay)
            overlay_layout.addWidget(err)
            overlay.setStyleSheet("background:rgba(255,255,255,0.9);")
            overlay.resize(self._workspace.size())

    def _apply_window_chrome(self) -> None:
        """Set title, icon, size, keyboard shortcuts."""
        self.setWindowTitle("PetroARX – Facies Classification")
        self.setMinimumSize(1200, 780)
        self.resize(1480, 880)

        # Status bar hint
        self.statusBar().showMessage(
            "Ready  |  Load a LAS file → Run Feature Selection → Classify"
        )

        # Menubar with just File > Close
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        act_close = QtWidgets.QAction("&Close Window", self)
        act_close.setShortcut(QtGui.QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self.close)
        file_menu.addAction(act_close)

        act_export = QtWidgets.QAction("&Export Results…", self)
        act_export.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        act_export.triggered.connect(self._trigger_export)
        file_menu.addAction(act_export)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        act_about = QtWidgets.QAction("About Facies Classification", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _pre_select_algorithm(self, algorithm: str | None) -> None:
        """Set cmbAlgorithm and stackedAlgoParams to match *algorithm*."""
        if algorithm is None:
            return
        ws = self._workspace
        cmb = getattr(ws, "cmbAlgorithm", None)
        if cmb is None:
            return
        target_text = _ALGO_TEXT.get(algorithm.lower(), "")
        if not target_text:
            return
        idx = cmb.findText(target_text)
        if idx >= 0:
            cmb.setCurrentIndex(idx)
            stack = getattr(ws, "stackedAlgoParams", None)
            if stack is not None:
                stack.setCurrentIndex(idx)
            if self._controller and hasattr(self._controller, "_on_algo_changed"):
                try:
                    self._controller._on_algo_changed(idx)
                except Exception:
                    pass

    def _trigger_export(self) -> None:
        if self._controller and hasattr(self._controller, "_on_export_results"):
            try:
                self._controller._on_export_results()
            except Exception:
                pass

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "About Facies Classification",
            "<b>PetroARX – Facies Classification Module</b><br><br>"
            "Supported methods:<br>"
            "<ul>"
            "<li><b>Unsupervised:</b> K-Means, Gaussian Mixture Model, Self-Organizing Map</li>"
            "<li><b>Supervised:</b> Ensemble (RF + XGBoost + SVM)</li>"
            "</ul>"
            "Workflow: Load LAS → Feature Engineering → "
            "Hyperparameter Tuning → Train → Predict → Export",
        )

    @staticmethod
    def _error_widget(message: str) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lyt = QtWidgets.QVBoxLayout(w)
        lbl = QtWidgets.QLabel(message)
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color:#D9534F;font-size:13px;font-weight:600;"
            "background:#FFF5F5;padding:30px;border-radius:8px;"
        )
        lyt.addStretch()
        lyt.addWidget(lbl)
        lyt.addStretch()
        return w

    # ─────────────────────────────────────────────────────────────────────────
    # Qt event overrides
    # ─────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        """Hide instead of destroy so re-opening is instant."""
        self.hide()
        self.closed.emit()
        event.ignore()          # prevent actual destruction
