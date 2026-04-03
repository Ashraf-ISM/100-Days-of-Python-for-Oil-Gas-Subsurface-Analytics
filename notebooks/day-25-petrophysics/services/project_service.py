"""Project create/open/save helpers."""
from __future__ import annotations

from PyQt5 import QtWidgets


class ProjectService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self.project_name = "Untitled"

    def new_project(self):
        name, ok = QtWidgets.QInputDialog.getText(self.ui, "New Project", "Project name:")
        if not ok or not name.strip():
            return
        self.project_name = name.strip()
        self._apply_project_name()

    def save_project(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Save Project",
            f"{self.project_name}.pproj",
            "Project Files (*.pproj)",
        )
        if not path:
            return
        # TODO: serialize project data
        QtWidgets.QMessageBox.information(self.ui, "Saved", f"Project saved:\n{path}")

    def _apply_project_name(self):
        self.ui.setWindowTitle(f"PetroAnalyst Pro v1.0 — {self.project_name}")
        tree = getattr(self.ui, "treeProject", None)
        if tree is not None and tree.topLevelItemCount() > 0:
            tree.topLevelItem(0).setText(0, self.project_name)
