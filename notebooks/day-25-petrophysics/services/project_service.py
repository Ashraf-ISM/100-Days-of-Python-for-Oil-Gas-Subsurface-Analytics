"""Project create/open/save with full data flow integration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5 import QtWidgets, QtCore

from core.project_manager import (
    ProjectData,
    save_project,
    load_project,
    get_recent_projects,
    add_recent_project,
)


class ProjectService:
    """Manages project lifecycle and UI state synchronization."""
    
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self.current_project: ProjectData | None = None
        self.modified = False
    
    # ========== Project Creation & Opening ==========
    
    def new_project(self) -> bool:
        """Create new project with user input."""
        dialog = QtWidgets.QDialog(self.ui)
        dialog.setWindowTitle("New Project")
        dialog.setGeometry(200, 200, 400, 200)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Project name
        layout.addWidget(QtWidgets.QLabel("Project Name:"))
        name_input = QtWidgets.QLineEdit()
        name_input.setText("New Project")
        layout.addWidget(name_input)
        
        # Project description
        layout.addWidget(QtWidgets.QLabel("Description:"))
        desc_input = QtWidgets.QTextEdit()
        desc_input.setMaximumHeight(80)
        layout.addWidget(desc_input)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("Create")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return False
        
        name = name_input.text().strip() or "Untitled"
        desc = desc_input.toPlainText().strip()
        
        self.current_project = ProjectData(name=name)
        self.current_project.metadata["description"] = desc
        self.modified = False
        
        self._update_ui_state()
        QtWidgets.QMessageBox.information(
            self.ui, "Project Created", f"New project '{name}' created."
        )
        return True
    
    def open_project(self) -> bool:
        """Open existing project file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui,
            "Open Project",
            str(Path.home()),
            "PetroVision Projects (*.pproj);;All Files (*)",
        )
        if not path:
            return False
        
        return self.load_project_from_path(path)
    
    def load_project_from_path(self, path: str) -> bool:
        """Load project from specific path.
        
        Args:
            path: Full path to project file
        
        Returns:
            True if successful
        """
        project = load_project(path)
        if project is None:
            QtWidgets.QMessageBox.warning(
                self.ui, "Error", f"Failed to load project:\n{path}"
            )
            return False
        
        self.current_project = project
        self.modified = False
        add_recent_project(path)
        
        self._update_ui_state()
        QtWidgets.QMessageBox.information(
            self.ui, "Project Loaded", 
            f"Project '{project.name}' loaded from:\n{path}"
        )
        return True
    
    def load_recent_project(self, path: str) -> bool:
        """Load a recent project.
        
        Args:
            path: Project file path
        
        Returns:
            True if successful
        """
        if not Path(path).exists():
            QtWidgets.QMessageBox.warning(
                self.ui, "Error", 
                f"Project file not found:\n{path}"
            )
            return False
        
        return self.load_project_from_path(path)
    
    # ========== Project Saving ==========
    
    def save_project(self) -> bool:
        """Save current project."""
        if self.current_project is None:
            return self.save_project_as()
        
        if self.current_project.path is None:
            return self.save_project_as()
        
        return self._perform_save(self.current_project.path)
    
    def save_project_as(self) -> bool:
        """Save project with new name/location."""
        if self.current_project is None:
            QtWidgets.QMessageBox.warning(
                self.ui, "Error", "No project to save."
            )
            return False
        
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Save Project As",
            f"{self.current_project.name}.pproj",
            "PetroVision Projects (*.pproj);;All Files (*)",
        )
        if not path:
            return False
        
        if not path.endswith(".pproj"):
            path = f"{path}.pproj"
        
        return self._perform_save(path)
    
    def _perform_save(self, path: str) -> bool:
        """Perform the actual save operation.
        
        Args:
            path: File path to save to
        
        Returns:
            True if successful
        """
        if self.current_project is None:
            return False
        
        self.current_project.path = path
        
        # Serialize wells data
        self._serialize_well_data()
        
        success = save_project(path, self.current_project)
        if success:
            self.modified = False
            add_recent_project(path)
            self._update_ui_state()
            QtWidgets.QMessageBox.information(
                self.ui, "Saved", 
                f"Project saved to:\n{path}"
            )
            return True
        else:
            QtWidgets.QMessageBox.critical(
                self.ui, "Error", 
                f"Failed to save project to:\n{path}"
            )
            return False
    
    # ========== Project Data Management ==========
    
    def _serialize_well_data(self) -> None:
        """Serialize well data from data service to project."""
        if self.current_project is None:
            return
        
        data_service = getattr(self.ui, "_data_service", None)
        if data_service is None:
            return
        
        wells = getattr(data_service, "_wells", {})
        for well_name, well in wells.items():
            well_data = {
                "name": well.name,
                "header": well.header,
                "log_info": well.log_info,
            }
            
            # Serialize dataframe to records format
            df = getattr(well, "data", None)
            if df is not None:
                well_data["data"] = df.to_dict(orient="records")
            
            self.current_project.wells[well_name] = well_data
    
    def _deserialize_well_data(self) -> dict:
        """Deserialize well data from project into memory.
        
        Returns:
            Dictionary of well objects ready for data service
        """
        if self.current_project is None:
            return {}
        
        from core.data_model import Well
        import pandas as pd
        
        wells = {}
        for well_name, well_data in self.current_project.wells.items():
            well = Well(
                name=well_data.get("name", well_name),
                header=well_data.get("header", {}),
                log_info=well_data.get("log_info", {})
            )
            
            # Deserialize dataframe from records
            records = well_data.get("data", [])
            if records:
                well.data = pd.DataFrame(records)
            
            wells[well_name] = well
        
        return wells
    
    def mark_modified(self) -> None:
        """Mark project as modified."""
        self.modified = True
        self._update_ui_state()
    
    # ========== UI State Management ==========
    
    def _update_ui_state(self) -> None:
        """Update UI to reflect current project state."""
        if self.current_project is None:
            self._set_window_title("PetroAnalyst Pro v1.0")
            self._update_project_header("No Project", "")
        else:
            title = f"PetroAnalyst Pro v1.0 — {self.current_project.name}"
            if self.modified:
                title += " *"
            self._set_window_title(title)
            
            well_count = len(self.current_project.wells)
            status = f"Well: {list(self.current_project.wells.keys())[0] if well_count > 0 else 'None'}"
            if well_count > 1:
                status += f" (+{well_count - 1} more)"
            
            self._update_project_header(
                self.current_project.name,
                status
            )
    
    def _set_window_title(self, title: str) -> None:
        """Set application window title."""
        self.ui.setWindowTitle(title)
    
    def _update_project_header(self, project_name: str, status: str) -> None:
        """Update dashboard project header labels.
        
        Args:
            project_name: Name of current project
            status: Status string
        """
        label = getattr(self.ui, "lblProjName", None)
        if label is not None:
            label.setText(f"Project: {project_name}")
        
        label = getattr(self.ui, "lblProjDetails", None)
        if label is not None:
            label.setText(status)
    
    def refresh_recent_projects(self) -> None:
        """Update recent projects list in UI."""
        recent = get_recent_projects(3)
        
        # Update recent project buttons
        for i, path in enumerate(recent):
            button_name = f"btnDashRecent{i+1}"
            button = getattr(self.ui, button_name, None)
            if button is not None:
                project_name = Path(path).stem
                button.setText(f"📦 {project_name}")
                button.setToolTip(path)
                button.clicked.disconnect()
                button.clicked.connect(
                    lambda checked=False, p=path: self.load_recent_project(p)
                )
        
        # Hide unused buttons
        for i in range(len(recent), 3):
            button_name = f"btnDashRecent{i+1}"
            button = getattr(self.ui, button_name, None)
            if button is not None:
                button.hide()
    
    def get_current_project(self) -> ProjectData | None:
        """Get currently open project."""
        return self.current_project
    
    def is_project_modified(self) -> bool:
        """Check if project has unsaved changes."""
        return self.modified
