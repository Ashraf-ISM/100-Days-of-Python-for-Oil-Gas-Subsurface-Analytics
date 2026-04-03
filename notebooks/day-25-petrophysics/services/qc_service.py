"""Quality control entry points."""
from __future__ import annotations

from PyQt5 import QtWidgets

from qc.qc_engine import run_qc


class QCService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui

    def run_qc(self):
        # TODO: fetch active well + curve and run actual QC checks
        QtWidgets.QMessageBox.information(self.ui, "QC", "Run QC (stub).")

    def export_qc(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export QC Report",
            "qc_report.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        QtWidgets.QMessageBox.information(self.ui, "QC", f"QC report exported:\n{path}")
