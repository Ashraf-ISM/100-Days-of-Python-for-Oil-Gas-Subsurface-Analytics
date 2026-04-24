"""Project lifecycle — create / open / save with .ash archive format.

This service owns the entire project workflow:
  • New project
  • Open project (file dialog → load_ash → full state restore)
  • Save / Save As (collect AppState snapshot → save_ash → progress dialog)
  • Load-summary dialog shown after a successful open
  • Recent-projects registry + dashboard button refresh  
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets 

from core.app_state import AppState
from core.project_manager import (
    ProjectData,
    add_recent_project,
    get_recent_projects,
    load_ash,
    remove_recent_project,
    save_ash,
)

# ── Colour palette used throughout the dialogs ──────────────────────────────── 
_CLR_BG        = "#0F1B2D"
_CLR_SURFACE   = "#152236"
_CLR_CARD      = "#1A2D45"
_CLR_BORDER    = "#1E3A5F"
_CLR_ACCENT    = "#2A6FD4"
_CLR_ACCENT2   = "#1A56A8"
_CLR_TEXT      = "#E8EFF8"
_CLR_SUBTEXT   = "#8BA3C1"
_CLR_SUCCESS   = "#10B981"
_CLR_WARNING   = "#F59E0B"
_CLR_LABEL     = "#A8C0DC"

_FONT_BODY    = "font-family: 'Segoe UI', 'Inter', sans-serif;"
_STYLE_DIALOG = f"""
    QDialog {{
        background: {_CLR_BG};
        {_FONT_BODY}
    }}
    QLabel {{
        color: {_CLR_TEXT};
        {_FONT_BODY}
    }}
    QLineEdit, QTextEdit, QComboBox {{
        background: {_CLR_CARD};
        border: 1px solid {_CLR_BORDER};
        border-radius: 6px;
        color: {_CLR_TEXT};
        padding: 6px 10px;
        font-size: 13px;
        {_FONT_BODY}
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border-color: {_CLR_ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background: {_CLR_CARD};
        color: {_CLR_TEXT};
        selection-background-color: {_CLR_ACCENT};
    }}
    QPushButton {{
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
        {_FONT_BODY}
    }}
    QPushButton#btnPrimary {{
        background: {_CLR_ACCENT};
        color: #FFFFFF;
        border: none;
    }}
    QPushButton#btnPrimary:hover {{
        background: {_CLR_ACCENT2};
    }}
    QPushButton#btnSecondary {{
        background: transparent;
        color: {_CLR_SUBTEXT};
        border: 1px solid {_CLR_BORDER};
    }}
    QPushButton#btnSecondary:hover {{
        color: {_CLR_TEXT};
        border-color: {_CLR_ACCENT};
    }}
    QFrame#card {{
        background: {_CLR_CARD};
        border: 1px solid {_CLR_BORDER};
        border-radius: 10px;
    }}
    QFrame#header {{
        background: {_CLR_SURFACE};
        border-bottom: 1px solid {_CLR_BORDER};
        border-radius: 0px;
    }}
    QTableWidget {{
        background: {_CLR_CARD};
        color: {_CLR_TEXT};
        gridline-color: {_CLR_BORDER};
        border: 1px solid {_CLR_BORDER};
        border-radius: 6px;
        {_FONT_BODY}
    }}
    QTableWidget::item {{
        padding: 4px 8px;
    }}
    QTableWidget::item:selected {{
        background: {_CLR_ACCENT};
    }}
    QHeaderView::section {{
        background: {_CLR_SURFACE};
        color: {_CLR_SUBTEXT};
        border: none;
        border-bottom: 1px solid {_CLR_BORDER};
        padding: 6px 8px;
        font-size: 11px;
        font-weight: 600;
        {_FONT_BODY}
    }}
    QScrollBar:vertical {{
        background: {_CLR_SURFACE};
        width: 6px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {_CLR_BORDER};
        border-radius: 3px;
        min-height: 20px;
    }}
"""


# ═════════════════════════════════════════════════════════════════════════════
#  Helper: make a styled section label
# ═════════════════════════════════════════════════════════════════════════════

def _section_label(text: str, parent=None) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text, parent)
    lbl.setStyleSheet(
        f"color: {_CLR_SUBTEXT}; font-size: 11px; font-weight: 700; "
        f"letter-spacing: 1px; text-transform: uppercase; "
        f"padding-bottom: 2px; border-bottom: 1px solid {_CLR_BORDER};"
    )
    return lbl


def _field_label(text: str, required: bool = False, parent=None) -> QtWidgets.QLabel:
    mark = f' <span style="color:{_CLR_WARNING}">*</span>' if required else ""
    lbl = QtWidgets.QLabel(f"{text}{mark}", parent)
    lbl.setStyleSheet(f"color: {_CLR_LABEL}; font-size: 12px; font-weight: 600;")
    lbl.setTextFormat(QtCore.Qt.RichText)
    return lbl


# ═════════════════════════════════════════════════════════════════════════════
#  Dialog: New Project
# ═════════════════════════════════════════════════════════════════════════════

class NewProjectDialog(QtWidgets.QDialog):
    """Professional new-project creation dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project — PetroARX")
        self.setFixedSize(540, 560)
        self.setStyleSheet(_STYLE_DIALOG)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QtWidgets.QFrame(self)
        header.setObjectName("header")
        header.setFixedHeight(72)
        hbox = QtWidgets.QHBoxLayout(header)
        hbox.setContentsMargins(24, 0, 24, 0)

        icon_lbl = QtWidgets.QLabel("⬡", header)
        icon_lbl.setStyleSheet(
            f"color: {_CLR_ACCENT}; font-size: 30px; font-weight: 800;"
        )
        title_lbl = QtWidgets.QLabel("New Project", header)
        title_lbl.setStyleSheet(
            f"color: {_CLR_TEXT}; font-size: 20px; font-weight: 700;"
        )
        sub_lbl = QtWidgets.QLabel("PetroARX Petrophysics Suite", header)
        sub_lbl.setStyleSheet(f"color: {_CLR_SUBTEXT}; font-size: 11px;")

        vbox_title = QtWidgets.QVBoxLayout()
        vbox_title.setSpacing(2)
        vbox_title.addWidget(title_lbl)
        vbox_title.addWidget(sub_lbl)

        hbox.addWidget(icon_lbl)
        hbox.addSpacing(12)
        hbox.addLayout(vbox_title)
        hbox.addStretch()
        root.addWidget(header)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QtWidgets.QWidget(self)
        body.setStyleSheet(f"background: {_CLR_BG};")
        form = QtWidgets.QVBoxLayout(body)
        form.setContentsMargins(24, 20, 24, 0)
        form.setSpacing(14)

        form.addWidget(_section_label("Project Identity", body))

        # Project name
        form.addWidget(_field_label("Project Name", required=True, parent=body))
        self.nameEdit = QtWidgets.QLineEdit(body)
        self.nameEdit.setPlaceholderText("e.g. North Sea Block 14 — Exploration")
        self.nameEdit.setText("New Project")
        form.addWidget(self.nameEdit)

        # Two-column: Field | Basin
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(12)

        col1 = QtWidgets.QVBoxLayout()
        col1.addWidget(_field_label("Field Name", parent=body))
        self.fieldEdit = QtWidgets.QLineEdit(body)
        self.fieldEdit.setPlaceholderText("e.g. Gullfaks")
        col1.addWidget(self.fieldEdit)

        col2 = QtWidgets.QVBoxLayout()
        col2.addWidget(_field_label("Basin", parent=body))
        self.basinEdit = QtWidgets.QLineEdit(body)
        self.basinEdit.setPlaceholderText("e.g. North Sea")
        col2.addWidget(self.basinEdit)

        row1.addLayout(col1)
        row1.addLayout(col2)
        form.addLayout(row1)

        # Two-column: Country | Operator
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(12)

        col3 = QtWidgets.QVBoxLayout()
        col3.addWidget(_field_label("Country", parent=body))
        self.countryEdit = QtWidgets.QLineEdit(body)
        self.countryEdit.setPlaceholderText("e.g. Norway")
        col3.addWidget(self.countryEdit)

        col4 = QtWidgets.QVBoxLayout()
        col4.addWidget(_field_label("Operator / Company", parent=body))
        self.operatorEdit = QtWidgets.QLineEdit(body)
        self.operatorEdit.setPlaceholderText("e.g. Equinor ASA")
        col4.addWidget(self.operatorEdit)

        row2.addLayout(col3)
        row2.addLayout(col4)
        form.addLayout(row2)

        form.addSpacing(4)
        form.addWidget(_section_label("Description", body))

        form.addWidget(_field_label("Project Description", parent=body))
        self.descEdit = QtWidgets.QTextEdit(body)
        self.descEdit.setPlaceholderText(
            "Optional — summarise the project scope, objectives, or data sources..."
        )
        self.descEdit.setFixedHeight(80)
        form.addWidget(self.descEdit)
        form.addStretch()

        root.addWidget(body, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QtWidgets.QFrame(self)
        footer.setStyleSheet(
            f"background: {_CLR_SURFACE}; border-top: 1px solid {_CLR_BORDER};"
        )
        fbox = QtWidgets.QHBoxLayout(footer)
        fbox.setContentsMargins(24, 14, 24, 14)

        hint = QtWidgets.QLabel(
            f'<span style="color:{_CLR_WARNING}">*</span>'
            f' <span style="color:{_CLR_SUBTEXT}; font-size:11px;">Required field</span>',
            footer,
        )
        hint.setTextFormat(QtCore.Qt.RichText)

        cancel_btn = QtWidgets.QPushButton("Cancel", footer)
        cancel_btn.setObjectName("btnSecondary")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)

        create_btn = QtWidgets.QPushButton("✦  Create Project", footer)
        create_btn.setObjectName("btnPrimary")
        create_btn.setFixedWidth(160)
        create_btn.clicked.connect(self._on_create)

        fbox.addWidget(hint)
        fbox.addStretch()
        fbox.addWidget(cancel_btn)
        fbox.addSpacing(8)
        fbox.addWidget(create_btn)
        root.addWidget(footer)

    def _on_create(self) -> None:
        if not self.nameEdit.text().strip():
            self.nameEdit.setFocus()
            self.nameEdit.setStyleSheet(
                self.nameEdit.styleSheet()
                + f"border-color: {_CLR_WARNING};"
            )
            return
        self.accept()

    # ── Result accessors ──────────────────────────────────────────────────────

    def project_name(self) -> str:
        return self.nameEdit.text().strip() or "Untitled"

    def metadata(self) -> dict:
        return {
            "description": self.descEdit.toPlainText().strip(),
            "field": self.fieldEdit.text().strip(),
            "basin": self.basinEdit.text().strip(),
            "country": self.countryEdit.text().strip(),
            "operator": self.operatorEdit.text().strip(),
            "region": "",
        }


# ═════════════════════════════════════════════════════════════════════════════
#  Dialog: Load Summary
# ═════════════════════════════════════════════════════════════════════════════

class LoadSummaryDialog(QtWidgets.QDialog):
    """Card-based summary shown after a project is successfully opened."""

    def __init__(self, project: ProjectData, wells: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project Loaded — PetroARX")
        self.setMinimumSize(620, 460)
        self.setStyleSheet(_STYLE_DIALOG)
        self._project = project
        self._wells = wells
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QtWidgets.QFrame(self)
        header.setObjectName("header")
        header.setFixedHeight(72)
        hbox = QtWidgets.QHBoxLayout(header)
        hbox.setContentsMargins(24, 0, 24, 0)

        icon_lbl = QtWidgets.QLabel("✔", header)
        icon_lbl.setStyleSheet(
            f"color: {_CLR_SUCCESS}; font-size: 28px; font-weight: 800;"
        )

        title_lbl = QtWidgets.QLabel(
            f"Project Loaded: {self._project.name}", header
        )
        title_lbl.setStyleSheet(
            f"color: {_CLR_TEXT}; font-size: 18px; font-weight: 700;"
        )

        saved_dt = self._project.modified or ""
        try:
            saved_dt = datetime.fromisoformat(saved_dt).strftime("%d %b %Y  %H:%M")
        except Exception:
            pass
        sub_lbl = QtWidgets.QLabel(f"Last saved: {saved_dt}", header)
        sub_lbl.setStyleSheet(f"color: {_CLR_SUBTEXT}; font-size: 11px;")

        vbox_t = QtWidgets.QVBoxLayout()
        vbox_t.setSpacing(2)
        vbox_t.addWidget(title_lbl)
        vbox_t.addWidget(sub_lbl)

        hbox.addWidget(icon_lbl)
        hbox.addSpacing(12)
        hbox.addLayout(vbox_t)
        hbox.addStretch()
        root.addWidget(header)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QtWidgets.QWidget(self)
        body.setStyleSheet(f"background: {_CLR_BG};")
        blayout = QtWidgets.QVBoxLayout(body)
        blayout.setContentsMargins(24, 18, 24, 0)
        blayout.setSpacing(14)

        # Metadata cards row
        meta = self._project.metadata or {}
        card_row = QtWidgets.QHBoxLayout()
        card_row.setSpacing(10)
        for label, value in (
            ("Field", meta.get("field", "—") or "—"),
            ("Basin", meta.get("basin", "—") or "—"),
            ("Country", meta.get("country", "—") or "—"),
            ("Wells Loaded", str(len(self._wells))),
        ):
            card = self._make_meta_card(label, value)
            card_row.addWidget(card)
        blayout.addLayout(card_row)

        # Well table
        blayout.addWidget(_section_label("Well Summary", body))

        table = QtWidgets.QTableWidget(0, 4, body)
        table.setHorizontalHeaderLabels(
            ["Well Name", "Curves", "Depth Range", "Computed Curves"]
        )
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        table.setFixedHeight(min(max(len(self._wells) * 34 + 38, 80), 260))

        _COMPUTED = {"VSH", "Vsh", "PHIT", "PHIE", "SW", "PERM", "NET_PAY", "PayFlag"}

        for row_idx, (name, well) in enumerate(self._wells.items()):
            table.insertRow(row_idx)
            df = getattr(well, "data", None)

            # Depth range
            depth_rng = "—"
            if df is not None:
                depth_col = next(
                    (c for c in df.columns if str(c).upper() in {"DEPTH", "DEPT", "MD"}),
                    None,
                )
                if depth_col:
                    depths = pd.to_numeric(df[depth_col], errors="coerce").dropna()
                    if not depths.empty:
                        depth_rng = f"{depths.min():.1f} – {depths.max():.1f} m"

            # Computed curves present
            computed_present: list[str] = []
            if df is not None:
                computed_present = [
                    c for c in df.columns if str(c).upper() in {x.upper() for x in _COMPUTED}
                ]
            computed_str = ", ".join(computed_present) if computed_present else "None"

            num_curves = len(df.columns) if df is not None else 0

            for col_idx, text in enumerate(
                [name, str(num_curves), depth_rng, computed_str]
            ):
                item = QtWidgets.QTableWidgetItem(text)
                item.setFlags(QtCore.Qt.ItemIsEnabled)
                if col_idx == 3 and computed_present:
                    item.setForeground(QtGui.QColor(_CLR_SUCCESS))
                table.setItem(row_idx, col_idx, item)

        blayout.addWidget(table)

        # Description
        desc = meta.get("description", "").strip()
        if desc:
            blayout.addWidget(_section_label("Description", body))
            desc_lbl = QtWidgets.QLabel(desc, body)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {_CLR_SUBTEXT}; font-size: 12px; "
                f"background: {_CLR_CARD}; border: 1px solid {_CLR_BORDER}; "
                f"border-radius: 8px; padding: 10px;"
            )
            blayout.addWidget(desc_lbl)

        blayout.addStretch()
        root.addWidget(body, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QtWidgets.QFrame(self)
        footer.setStyleSheet(
            f"background: {_CLR_SURFACE}; border-top: 1px solid {_CLR_BORDER};"
        )
        fbox = QtWidgets.QHBoxLayout(footer)
        fbox.setContentsMargins(24, 14, 24, 14)

        path_lbl = QtWidgets.QLabel(
            f'<span style="color:{_CLR_SUBTEXT}; font-size: 10px;">'
            f'{self._project.path or ""}</span>',
            footer,
        )
        path_lbl.setTextFormat(QtCore.Qt.RichText)
        path_lbl.setWordWrap(False)

        ok_btn = QtWidgets.QPushButton("Continue  →", footer)
        ok_btn.setObjectName("btnPrimary")
        ok_btn.setFixedWidth(130)
        ok_btn.clicked.connect(self.accept)

        fbox.addWidget(path_lbl, 1)
        fbox.addWidget(ok_btn)
        root.addWidget(footer)

    def _make_meta_card(self, label: str, value: str) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame(self)
        card.setObjectName("card")
        cl = QtWidgets.QVBoxLayout(card)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(2)
        lbl = QtWidgets.QLabel(label, card)
        lbl.setStyleSheet(f"color: {_CLR_SUBTEXT}; font-size: 10px; font-weight: 700;")
        val = QtWidgets.QLabel(value, card)
        val.setStyleSheet(f"color: {_CLR_TEXT}; font-size: 15px; font-weight: 800;")
        val.setWordWrap(True)
        cl.addWidget(lbl)
        cl.addWidget(val)
        return card


# ═════════════════════════════════════════════════════════════════════════════
#  Main Service
# ═════════════════════════════════════════════════════════════════════════════

class ProjectService:
    """Manages project lifecycle: new / open / save / save-as."""

    def __init__(self, ui: QtWidgets.QMainWindow) -> None:
        self.ui = ui
        self.current_project: ProjectData | None = None
        self.modified: bool = False

    # =========================================================================
    #  Public API
    # =========================================================================

    def new_project(self) -> bool:
        """Show the New Project dialog and initialise a blank project."""
        dlg = NewProjectDialog(self.ui)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return False

        self.current_project = ProjectData(name=dlg.project_name())
        self.current_project.metadata = dlg.metadata()
        self.modified = False
        self._update_ui_state()
        return True

    def open_project(self) -> bool:
        """Open a file dialog and load the selected .ash project."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui,
            "Open PetroARX Project",
            str(Path.home()),
            "PetroARX Session (*.ash);;All Files (*)",
        )
        if not path:
            return False
        return self.load_project_from_path(path)

    def load_project_from_path(self, path: str) -> bool:
        """Load a project from *path* and restore all application state."""
        if not Path(path).exists():
            QtWidgets.QMessageBox.warning(
                self.ui, "Project Not Found",
                f"The project file could not be found:\n\n{path}",
            )
            remove_recent_project(path)
            self.refresh_recent_projects()
            return False

        # ── Show loading indicator ────────────────────────────────────────────
        progress = self._make_progress("Opening Project", "Loading wells and settings…")
        QtWidgets.QApplication.processEvents()

        project, wells, app_state = load_ash(path)

        progress.close()

        if project is None:
            QtWidgets.QMessageBox.critical(
                self.ui, "Load Failed",
                f"Could not open the project file.\n\nThe file may be corrupt "
                f"or was saved with an incompatible version.\n\nPath:\n{path}",
            )
            return False

        self.current_project = project
        self.modified = False

        # ── Inject wells into DataService ─────────────────────────────────────
        data_svc = self._data_service()
        if data_svc is not None and wells:
            data_svc._wells = wells
            # Restore active well
            active = app_state.active_well
            if active and active in wells:
                data_svc._current_well = active
            elif wells:
                data_svc._current_well = next(iter(wells))
            data_svc._rename_history = dict(app_state.rename_history or {})
            data_svc._update_well_lists()
            data_svc._refresh_views()

        # ── Restore UI panel values ───────────────────────────────────────────
        self._restore_app_state(app_state)

        # ── Bookkeeping ───────────────────────────────────────────────────────
        add_recent_project(path)
        self.refresh_recent_projects()
        self._update_ui_state()

        # ── Summary dialog ────────────────────────────────────────────────────
        summary = LoadSummaryDialog(project, wells, self.ui)
        summary.exec_()

        # ── Trigger interpretation workspace re-render ────────────────────────
        # Deferred by 300 ms so the main event loop fully processes the dialog
        # close before the matplotlib canvases try to paint.  The callback
        # (registered by MainController) detects which computed curves are
        # present in the loaded DataFrame and re-renders the Vsh track,
        # Porosity workspace, Sw workspace, and Net Pay panel accordingly.
        post_load = getattr(self.ui, "on_project_loaded", None)
        if callable(post_load):
            QtCore.QTimer.singleShot(300, post_load)

        return True


    def load_recent_project(self, path: str) -> bool:
        """Load a project from the recent list; path may be empty string."""
        if not path:
            return False
        return self.load_project_from_path(path)

    def save_project(self) -> bool:
        """Save current project (prompt Save As if no path is set)."""
        if self.current_project is None:
            return self.save_project_as()
        if not self.current_project.path:
            return self.save_project_as()
        return self._perform_save(self.current_project.path)

    def save_project_as(self) -> bool:
        """Show a Save As dialog then persist."""
        # If no project yet, create a blank one silently
        if self.current_project is None:
            self.current_project = ProjectData(name="Untitled")

        default_name = f"{self.current_project.name}.ash"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Save Project As — PetroARX",
            str(Path.home() / default_name),
            "PetroARX Session (*.ash);;All Files (*)",
        )
        if not path:
            return False
        if not path.lower().endswith(".ash"):
            path = f"{path}.ash"
        return self._perform_save(path)

    def mark_modified(self) -> None:
        """Flag the project as having unsaved changes."""
        self.modified = True
        self._update_ui_state()

    def refresh_recent_projects(self) -> None:
        """Refresh the dashboard recent-project buttons."""
        recent = get_recent_projects(3)
        for i in range(3):
            btn_name = f"btnDashRecent{i + 1}"
            btn = getattr(self.ui, btn_name, None)
            if btn is None:
                continue
            if i < len(recent):
                p = recent[i]
                proj_name = Path(p).stem
                # Last-modified timestamp
                try:
                    ts = os.path.getmtime(p)
                    dt_str = datetime.fromtimestamp(ts).strftime("%d %b %Y")
                except Exception:
                    dt_str = ""
                btn.setText(f"📂  {proj_name}")
                btn.setToolTip(f"{p}\nLast saved: {dt_str}")
                btn.show()
                # Reconnect to avoid duplicate signals
                try:
                    btn.clicked.disconnect()
                except RuntimeError:
                    pass
                btn.clicked.connect(
                    lambda _=False, _p=p: self.load_recent_project(_p)
                )
            else:
                btn.hide()

    def get_current_project(self) -> ProjectData | None:
        return self.current_project

    def is_project_modified(self) -> bool:
        return self.modified

    # =========================================================================
    #  Internal — save
    # =========================================================================

    def _perform_save(self, path: str) -> bool:
        """Collect all state and write the .ash archive."""
        if self.current_project is None:
            return False

        self.current_project.path = path

        # ── Collect wells ─────────────────────────────────────────────────────
        data_svc = self._data_service()
        wells: dict = {}
        if data_svc is not None:
            wells = dict(getattr(data_svc, "_wells", {}))

        # ── Snapshot AppState ─────────────────────────────────────────────────
        app_state = self._collect_app_state(data_svc)

        # ── Progress dialog ───────────────────────────────────────────────────
        n_wells = len(wells)
        progress = self._make_progress(
            "Saving Project",
            f"Serialising {n_wells} well(s) to {Path(path).name}…",
        )
        QtWidgets.QApplication.processEvents()

        ok = save_ash(path, self.current_project, wells, app_state)

        progress.close()

        if ok:
            self.modified = False
            add_recent_project(path)
            self.refresh_recent_projects()
            self._update_ui_state()
            self._show_save_toast(path)
        else:
            QtWidgets.QMessageBox.critical(
                self.ui,
                "Save Failed",
                f"Could not write the project file:\n\n{path}\n\n"
                "Check disk space and write permissions.",
            )
        return ok

    # =========================================================================
    #  Internal — AppState collect / restore
    # =========================================================================

    def _collect_app_state(self, data_svc) -> AppState:
        """Read current UI widget values into a fresh AppState."""
        s = AppState()

        if data_svc is not None:
            s.active_well = getattr(data_svc, "_current_well", "") or ""
            s.rename_history = dict(getattr(data_svc, "_rename_history", {}))

        ui = self.ui

        def _spin(name: str, default: float) -> float:
            w = getattr(ui, name, None)
            if w is None:
                return default
            try:
                return float(w.value())
            except RuntimeError:
                return default
            except Exception:
                return default

        def _combo(name: str, default: str) -> str:
            w = getattr(ui, name, None)
            if w is None:
                return default
            try:
                return w.currentText()
            except RuntimeError:
                return default
            except Exception:
                return default

        def _line(name: str, default: str) -> str:
            w = getattr(ui, name, None)
            if w is None:
                return default
            try:
                return w.text().strip()
            except RuntimeError:
                return default
            except Exception:
                return default

        def _checked(name: str, default: bool) -> bool:
            w = getattr(ui, name, None)
            if w is None:
                return default
            try:
                return bool(w.isChecked())
            except RuntimeError:
                return default
            except Exception:
                return default

        # Vsh
        s.vsh_gr_curve    = _combo("comboVclGR", "")
        s.vsh_gr_min      = _spin("spinVclGRmin", 15.0)
        s.vsh_gr_max      = _spin("spinVclGRmax", 120.0)
        s.vsh_method      = _combo("vshMethodComboBox", "Linear")
        s.vsh_out_name    = _line("lineVclOutName", "VSH")

        # Porosity
        s.phi_method      = _combo("comboPhiMethod", "Density-Neutron (PHIE)")
        s.phi_matrix_type = _combo("comboPoroMatrixType", "Sandstone")
        s.phi_rho_ma      = _spin("spinPoroRhoma", 2.65) or _spin("spinPhiRhoma", 2.65)
        s.phi_rho_f       = _spin("spinPoroRhof", 1.0)  or _spin("spinPhiRhof", 1.0)
        s.phi_dt_ma       = _spin("spinPoroDtma", 55.5)
        s.phi_dt_f        = _spin("spinPoroDtf", 189.0)
        s.phi_phi_sh      = _spin("spinPoroPhish", 0.1)
        s.phi_vsh_cut     = _spin("spinPoroVshCut", 0.5)
        s.phi_shale_corr  = _checked("checkPoroShaleCorr", False)
        s.phi_out_name    = _line("linePhiOutName", "PHIE")

        # Sw
        s.sw_method       = _combo("comboSwMethod", "Archie")
        s.sw_rw           = _spin("spinSwRw", 0.05)
        s.sw_a            = _spin("spinSwA", 1.0)
        s.sw_m            = _spin("spinSwM", 2.0)
        s.sw_n            = _spin("spinSwN", 2.0)
        s.sw_rsh          = _spin("spinSwFormRw", 2.0)
        s.sw_rt_curve     = _combo("comboSwRt", "")
        s.sw_phi_curve    = _combo("comboSwPhie", "")
        s.sw_out_name     = _line("lineSwOutName", "SW")

        # Net Pay
        s.net_pay_vsh_cut  = _spin("spinNetPayVcl", 0.4)
        s.net_pay_phi_cut  = _spin("spinNetPayPhi", 0.05)
        s.net_pay_sw_cut   = _spin("spinNetPaySw", 0.65)
        s.net_pay_out_name = _line("lineNetPayOut", "NET_PAY")

        # QC
        s.qc_curve          = _combo("comboQCCurve", "")
        s.qc_method         = _combo("comboQCMethod", "")
        s.qc_threshold      = _spin("spinQCThreshold", 3.0)
        s.qc_window         = int(_spin("spinQCWindow", 5))
        s.qc_from           = _spin("spinQCFrom", 0.0)
        s.qc_to             = _spin("spinQCTo", 9999.0)
        s.qc_check_missing  = _checked("checkQCMissing", True)
        s.qc_check_outliers = _checked("checkQCOutliers", True)
        s.qc_check_spikes   = _checked("checkQCSpikes", True)
        s.qc_check_negative = _checked("checkQCNegative", False)

        # Depth filter
        s.depth_from = _spin("spinDISFromDepth", 0.0)
        s.depth_to   = _spin("spinDISToDepth", 9999.0)

        return s

    def _restore_app_state(self, s: AppState) -> None:
        """Push AppState values back into UI widgets."""
        ui = self.ui

        def _set_spin(name: str, value: float) -> None:
            w = getattr(ui, name, None)
            if w is not None and hasattr(w, "setValue"):
                try:
                    w.blockSignals(True)
                    w.setValue(value)
                    w.blockSignals(False)
                except Exception:
                    pass

        def _set_combo(name: str, value: str) -> None:
            w = getattr(ui, name, None)
            if w is not None and hasattr(w, "setCurrentText"):
                try:
                    w.blockSignals(True)
                    w.setCurrentText(value)
                    w.blockSignals(False)
                except Exception:
                    pass

        def _set_line(name: str, value: str) -> None:
            w = getattr(ui, name, None)
            if w is not None and hasattr(w, "setText"):
                try:
                    w.setText(value)
                except Exception:
                    pass

        def _set_check(name: str, value: bool) -> None:
            w = getattr(ui, name, None)
            if w is not None and hasattr(w, "setChecked"):
                try:
                    w.blockSignals(True)
                    w.setChecked(value)
                    w.blockSignals(False)
                except Exception:
                    pass

        # Vsh
        _set_combo("comboVclGR",       s.vsh_gr_curve)
        _set_spin("spinVclGRmin",       s.vsh_gr_min)
        _set_spin("spinVclGRmax",       s.vsh_gr_max)
        _set_combo("vshMethodComboBox", s.vsh_method)
        _set_line("lineVclOutName",     s.vsh_out_name)

        # Porosity
        _set_combo("comboPhiMethod",      s.phi_method)
        _set_combo("comboPoroMatrixType", s.phi_matrix_type)
        _set_spin("spinPoroRhoma",        s.phi_rho_ma)
        _set_spin("spinPhiRhoma",         s.phi_rho_ma)
        _set_spin("spinPoroRhof",         s.phi_rho_f)
        _set_spin("spinPhiRhof",          s.phi_rho_f)
        _set_spin("spinPoroDtma",         s.phi_dt_ma)
        _set_spin("spinPoroDtf",          s.phi_dt_f)
        _set_spin("spinPoroPhish",        s.phi_phi_sh)
        _set_spin("spinPoroVshCut",       s.phi_vsh_cut)
        _set_check("checkPoroShaleCorr",  s.phi_shale_corr)
        _set_line("linePhiOutName",       s.phi_out_name)

        # Sw
        _set_combo("comboSwMethod",  s.sw_method)
        _set_spin("spinSwRw",        s.sw_rw)
        _set_spin("spinSwA",         s.sw_a)
        _set_spin("spinSwM",         s.sw_m)
        _set_spin("spinSwN",         s.sw_n)
        _set_spin("spinSwFormRw",    s.sw_rsh)
        _set_line("lineSwOutName",   s.sw_out_name)

        # Net Pay
        _set_spin("spinNetPayVcl",  s.net_pay_vsh_cut)
        _set_spin("spinNetPayPhi",  s.net_pay_phi_cut)
        _set_spin("spinNetPaySw",   s.net_pay_sw_cut)
        _set_line("lineNetPayOut",  s.net_pay_out_name)

        # QC
        _set_spin("spinQCThreshold",  s.qc_threshold)
        _set_spin("spinQCWindow",     float(s.qc_window))
        _set_spin("spinQCFrom",       s.qc_from)
        _set_spin("spinQCTo",         s.qc_to)
        _set_check("checkQCMissing",   s.qc_check_missing)
        _set_check("checkQCOutliers",  s.qc_check_outliers)
        _set_check("checkQCSpikes",    s.qc_check_spikes)
        _set_check("checkQCNegative",  s.qc_check_negative)

        # Depth filter
        _set_spin("spinDISFromDepth", s.depth_from)
        _set_spin("spinDISToDepth",   s.depth_to)

    # =========================================================================
    #  Internal — UI state
    # =========================================================================

    def _update_ui_state(self) -> None:
        """Sync window title and dashboard labels with current project."""
        if self.current_project is None:
            self.ui.setWindowTitle("PetroARX")
            self._set_dashboard_labels("No Project Loaded", "")
            return

        name  = self.current_project.name
        dirty = " ●" if self.modified else ""
        self.ui.setWindowTitle(f"PetroARX  —  {name}{dirty}")

        meta = self.current_project.metadata or {}
        field_str = meta.get("field", "") or ""
        well_count = len(self.current_project.well_names)
        status = (
            f"{field_str}  ·  {well_count} well(s)" if field_str
            else f"{well_count} well(s) loaded"
        )
        self._set_dashboard_labels(name, status)

    def _set_dashboard_labels(self, name: str, status: str) -> None:
        for attr, text in (("lblProjName", f"Project: {name}"), ("lblProjDetails", status)):
            lbl = getattr(self.ui, attr, None)
            if lbl is not None:
                lbl.setText(text)

    # =========================================================================
    #  Internal — helpers
    # =========================================================================

    def _data_service(self):
        """Return the DataService instance attached to the main window."""
        return getattr(self.ui, "_data_service", None)

    @staticmethod
    def _make_progress(title: str, msg: str) -> QtWidgets.QProgressDialog:
        dlg = QtWidgets.QProgressDialog(msg, None, 0, 0)
        dlg.setWindowTitle(title)
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.setStyleSheet(
            f"QProgressDialog {{ background: {_CLR_BG}; color: {_CLR_TEXT}; "
            f"border: 1px solid {_CLR_BORDER}; border-radius: 8px; padding: 16px; }}"
            f"QLabel {{ color: {_CLR_TEXT}; font-size: 13px; }}"
            f"QProgressBar {{ border: none; background: {_CLR_CARD}; "
            f"border-radius: 4px; height: 6px; }}"
            f"QProgressBar::chunk {{ background: {_CLR_ACCENT}; border-radius: 4px; }}"
        )
        dlg.show()
        QtWidgets.QApplication.processEvents()
        return dlg

    def _show_save_toast(self, path: str) -> None:
        """Show a brief, non-intrusive status bar message after saving."""
        status_bar = getattr(self.ui, "statusBar", None)
        if callable(status_bar):
            self.ui.statusBar().showMessage(
                f"✔  Project saved — {Path(path).name}", 4000
            )
        else:
            # Fallback: small info dialog
            QtWidgets.QMessageBox.information(
                self.ui,
                "Project Saved",
                f"Project saved successfully:\n{path}",
            )
