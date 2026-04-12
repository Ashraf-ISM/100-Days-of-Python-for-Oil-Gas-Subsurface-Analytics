from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "mainwindow.ui"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from controllers.main_controller import MainController  # noqa: E402

from extra.dialogs import AboutHelpDialog

class PetroVisionMainWindow(QtWidgets.QMainWindow):
    def __init__(self, project_path: str | None = None):
        super().__init__()
        ui_path = UI_DIR / UI_FILE  
        uic.loadUi(str(ui_path), self)
        self.setWindowTitle("PetroARX v1.0 - Petrophysics Interpretation Platform")
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is not None:
            self.setCentralWidget(tab_widget)
        self._embed_data_analysis_tab()
        self._embed_borehole_analysis_tab()
        self._embed_pore_pressure_tab()
        self._reorder_tabs()
        self._connect_tab_switches()
        self._connect_edit_actions()
        self.controller = MainController(self)
        self._build_dashboard()
        self.refresh_dashboard_tab()
        
        # Set window geometry
        self.setGeometry(100, 100, 1497, 893)
        
        # Load project if provided
        if project_path and Path(project_path).exists():
            QtCore.QTimer.singleShot(500, 
                lambda p=project_path: self.controller.projects.load_project_from_path(p))

        # Add Data Downloader to Tools menu
        self.actionDataDownloader = QtWidgets.QAction("Data Downloader", self)
        if hasattr(self, "menuTools"):
            self.menuTools.addAction(self.actionDataDownloader)
        self.actionDataDownloader.triggered.connect(self._open_data_downloader)

    def _open_data_downloader(self) -> None:
        from app.data_downloader_dialog import DataDownloaderWindow
        if not hasattr(self, '_data_downloader_win'):
            self._data_downloader_win = DataDownloaderWindow(self)
        self._data_downloader_win.show()
        self._data_downloader_win.raise_()
        self._data_downloader_win.activateWindow()

    # def show_about_dialog(self) -> None:
    #     """Display About dialog for the PetroARX desktop application."""
    #     message = (
    #         "<h3>PetroARX</h3>"
    #         "<p>A desktop petrophysics interpretation workspace for multi-well analysis.</p>"
    #         "<p><b>Core capabilities:</b></p>"
    #         "<ul>"
    #         "<li>Well log loading, curve management, and QC workflows</li>"
    #         "<li>Multi-track plotting and crossplot analysis</li>"
    #         "<li>Shale volume, porosity, permeability, and net pay calculations</li>"
    #         "<li>Water saturation workflows with Archie, Simandoux, Modified Simandoux, and Indonesia methods</li>"
    #         "</ul>"
    #         "<p><b>Quick help:</b> Open Help -> Documentation for usage and workflow guidance.</p>"
    #     )
    #     QtWidgets.QMessageBox.about(self, "About PetroARX", message)

    # def show_help_dialog(self) -> None:
    #     """Display quick in-app help summary."""
    #     message = (
    #         "<h3>PetroARX Help</h3>"
    #         "<p>Use the Dashboard for quick navigation, then run workflows in this order:</p>"
    #         "<ol>"
    #         "<li>Import well data (LAS/CSV/SEGY as available)</li>"
    #         "<li>Review curves and perform QC checks</li>"
    #         "<li>Run interpretation modules (Vsh, Phi, Sw, Net Pay)</li>"
    #         "<li>Review plots and export reports</li>"
    #         "</ol>"
    #         "<p>For project-system details, see QUICKSTART.md and PROJECT_MANAGEMENT_GUIDE.md.</p>"
    #     )
    #     QtWidgets.QMessageBox.information(self, "PetroARX Documentation", message)
    def show_about_dialog(self):
        dialog = AboutHelpDialog(self)
        dialog.exec_()

    def show_help_dialog(self):
        dialog = AboutHelpDialog(self)
        dialog.exec_()

    def _build_dashboard(self) -> None:
        tab = getattr(self, "tabDashboard", None)
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)
        self._clear_layout(layout)

        scroll_area = QtWidgets.QScrollArea(tab)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("border:0;background:transparent;")

        content = QtWidgets.QWidget(scroll_area)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(14)

        hero = QtWidgets.QFrame(content)
        hero.setStyleSheet(
            "QFrame {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1C4A7C, stop:1 #3F7CB6);"
            "border-radius: 18px;"
            "}"
        )
        hero_layout = QtWidgets.QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(18)

        hero_text = QtWidgets.QVBoxLayout()
        hero_title = QtWidgets.QLabel("PetroARX Dashboard", hero)
        hero_title.setStyleSheet("color:#FFFFFF;font-size:24px;font-weight:800;")
        hero_subtitle = QtWidgets.QLabel(
            "Overview of project activity, loaded wells, and quick access to the core interpretation tools.",
            hero,
        )
        hero_subtitle.setStyleSheet("color:rgba(255,255,255,0.86);font-size:12px;")
        hero_subtitle.setWordWrap(True)
        self._dashboard_project_label = QtWidgets.QLabel("Project: -", hero)
        self._dashboard_project_label.setStyleSheet("color:#DCEBFA;font-size:12px;font-weight:600;")
        self._dashboard_well_label = QtWidgets.QLabel("Active well: -", hero)
        self._dashboard_well_label.setStyleSheet("color:#DCEBFA;font-size:12px;font-weight:600;")
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)
        hero_text.addSpacing(4)
        hero_text.addWidget(self._dashboard_project_label)
        hero_text.addWidget(self._dashboard_well_label)
        hero_text.addStretch(1)
        hero_layout.addLayout(hero_text, 3)

        badge_col = QtWidgets.QVBoxLayout()
        badge_col.setSpacing(10)
        self._dashboard_badge_one = self._make_badge("Project Ready", "#EAF4FF", "#1C4A7C")
        self._dashboard_badge_two = self._make_badge("0 Wells", "#EEF9F6", "#0E7A63")
        badge_col.addWidget(self._dashboard_badge_one)
        badge_col.addWidget(self._dashboard_badge_two)
        badge_col.addStretch(1)
        hero_layout.addLayout(badge_col, 1)
        content_layout.addWidget(hero)

        metrics_row = QtWidgets.QHBoxLayout()
        metrics_row.setSpacing(12)
        self._dashboard_metrics = {}
        for title, key, accent in (
            ("Wells Loaded", "wells_loaded", "#2F6FB3"),
            ("Curves", "curve_count", "#1FA67A"),
            ("Avg Data Quality", "data_quality", "#D48A1D"),
            ("Current Samples", "sample_count", "#A354D0"),
        ):
            card, value_label = self._make_metric_card(title, accent)
            self._dashboard_metrics[key] = value_label
            metrics_row.addWidget(card)
        content_layout.addLayout(metrics_row)

        body_row = QtWidgets.QHBoxLayout()
        body_row.setSpacing(14)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(14)
        visual_section = self._make_section("Data Visualization")
        visual_grid = QtWidgets.QGridLayout()
        visual_grid.setSpacing(12)
        self._dashboard_hist_frame = self._make_chart_card("GR Distribution")
        self._dashboard_lith_frame = self._make_chart_card("Lithology Breakdown")
        visual_grid.addWidget(self._dashboard_hist_frame, 0, 0)
        visual_grid.addWidget(self._dashboard_lith_frame, 0, 1)
        visual_section.layout().addLayout(visual_grid)
        left_col.addWidget(visual_section, 3)

        workflow_section = self._make_section("Quick Workflow")
        workflow_grid = QtWidgets.QGridLayout()
        workflow_grid.setSpacing(10)
        self._dashboard_workflow_buttons = [
            getattr(self, "btnDashImportLAS", None),
            getattr(self, "btnDashImportCSV", None),
            getattr(self, "btnDashImportSEGY", None),
            getattr(self, "btnDashLogView", None),
            getattr(self, "btnDashXplot", None),
            getattr(self, "btnDashVsh", None),
            getattr(self, "btnDashSw", None),
            getattr(self, "btnDashGeo", None),
            getattr(self, "btnDashCorr", None),
        ]
        workflow_buttons = [button for button in self._dashboard_workflow_buttons if button is not None]
        for index, button in enumerate(workflow_buttons):
            button.setMinimumHeight(42)
            button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            row, column = divmod(index, 3)
            workflow_grid.addWidget(button, row, column)
        workflow_section.layout().addLayout(workflow_grid)
        left_col.addWidget(workflow_section, 1)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(14)

        quick_section = self._make_section("Quick Actions")
        quick_grid = QtWidgets.QGridLayout()
        quick_grid.setSpacing(10)
        self._dashboard_quick_buttons = [
            self._make_launch_button("Import Data", lambda: self._trigger_widget_click("btnDashImportLAS"), "#2F6FB3"),
            self._make_launch_button("Load Demo Data", self._load_demo_data, "#FF6B6B"),
            self._make_launch_button("Data Downloader", self._open_data_downloader, "#5E35B1"),
            self._make_launch_button("Log Viewer", lambda: self._call_controller_action("_go_to_logviewer_tab"), "#1FA67A"),
            self._make_launch_button("Crossplot", lambda: self._trigger_widget_click("btnDashXplot"), "#D48A1D"),
            self._make_launch_button("Shale Volume", lambda: self._trigger_widget_click("btnDashVsh"), "#A354D0"),
            self._make_launch_button("Water Saturation", lambda: self._trigger_widget_click("btnDashSw"), "#0F8B8D"),
            self._make_launch_button("Well Correlation", lambda: self._trigger_widget_click("btnDashCorr"), "#7C5CFF"),
        ]
        for index, button in enumerate(self._dashboard_quick_buttons):
            row, column = divmod(index, 2)
            quick_grid.addWidget(button, row, column)
        quick_section.layout().addLayout(quick_grid)
        right_col.addWidget(quick_section, 2)

        recent_section = self._make_section("Recent Projects")
        self._dashboard_recent_buttons = [
            getattr(self, "btnDashRecent1", None),
            getattr(self, "btnDashRecent2", None),
            getattr(self, "btnDashRecent3", None),
        ]
        recent_list = QtWidgets.QVBoxLayout()
        recent_list.setSpacing(8)
        for button in self._dashboard_recent_buttons:
            if button is None:
                continue
            button.setMinimumHeight(40)
            recent_list.addWidget(button)
        recent_section.layout().addLayout(recent_list)
        right_col.addWidget(recent_section, 1)

        activity_section = self._make_section("Recent Activity")
        self._dashboard_activity_list = QtWidgets.QListWidget(activity_section)
        self._dashboard_activity_list.setAlternatingRowColors(True)
        self._dashboard_activity_list.setStyleSheet(
            "QListWidget { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; padding:6px; }"
            "QListWidget::item { padding:8px 6px; }"
        )
        activity_section.layout().addWidget(self._dashboard_activity_list)
        right_col.addWidget(activity_section, 1)

        body_row.addLayout(left_col, 2)
        body_row.addLayout(right_col, 1)
        content_layout.addLayout(body_row)

        content_layout.addStretch(1)
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

        tab.setStyleSheet(
            "QWidget#tabDashboard { background: #F3F7FC; }"
            "QFrame#dashCard { background: #FFFFFF; border: 1px solid #D7E2EE; border-radius: 14px; }"
        )

    def _load_demo_data(self) -> None:
        data_svc = getattr(self.controller, "data", None)
        if data_svc is None:
            return
            
        demo_path = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/data/_Gorgonichthys_1_suite3_supercombo_log_Gorgonichthys1_suite2_CMR.las"
        import os
        if not os.path.exists(demo_path):
            QtWidgets.QMessageBox.warning(self, "Demo Data", f"Demo data file not found:\n{demo_path}")
            return
            
        from core.well_data_loader import load_well
        try:
            well, msg = load_well(demo_path, replace_nulls=True, depth_unit="m", depth_type="MD")
            data_svc._register_well(well)
            data_svc._update_well_lists()
            data_svc._refresh_views()
            QtWidgets.QMessageBox.information(self, "Demo Data", f"Demo data loaded successfully.\n{msg}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Demo Data", f"Failed to load demo data:\n{e}")

    def refresh_dashboard_tab(self) -> None:
        data_service = getattr(self.controller, "data", None)
        project_service = getattr(self.controller, "projects", None)

        project_name = "No project"
        if project_service is not None and getattr(project_service, "current_project", None) is not None:
            project_name = project_service.current_project.name
        self._set_label_text("_dashboard_project_label", f"Project: {project_name}")

        well = None
        df = None
        if data_service is not None:
            well = data_service._get_current_well()
            df = getattr(well, "data", None) if well is not None else None

        well_name = getattr(well, "name", "-") if well is not None else "-"
        self._set_label_text("_dashboard_well_label", f"Active well: {well_name}")

        wells_loaded = len(getattr(data_service, "_wells", {})) if data_service is not None else 0
        curve_count = len(df.columns) if df is not None else 0
        sample_count = len(df) if df is not None else 0
        data_quality = self._estimate_data_quality(df)

        self._set_metric_value("wells_loaded", str(wells_loaded))
        self._set_metric_value("curve_count", str(curve_count))
        self._set_metric_value("sample_count", f"{sample_count:,}")
        self._set_metric_value("data_quality", f"{data_quality:.0f}%")
        self._set_label_text("_dashboard_badge_one", "Project Ready")
        self._set_label_text("_dashboard_badge_two", f"{wells_loaded} Wells")

        self._update_recent_projects()
        self._update_activity_list(project_name, well, df)
        self._update_dashboard_charts(df)

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _make_section(self, title: str) -> QtWidgets.QFrame:
        section = QtWidgets.QFrame(self)
        section.setObjectName("dashCard")
        section.setStyleSheet(
            "QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        layout = QtWidgets.QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title_label = QtWidgets.QLabel(title, section)
        title_label.setStyleSheet("font-size:14px;font-weight:700;color:#274B72;")
        layout.addWidget(title_label)
        return section

    def _make_metric_card(self, title: str, accent: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
        card = QtWidgets.QFrame(self)
        card.setObjectName("dashCard")
        card.setStyleSheet(
            "QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_label = QtWidgets.QLabel(title, card)
        title_label.setStyleSheet("color:#5C718A;font-size:11px;font-weight:600;")
        value_label = QtWidgets.QLabel("0", card)
        value_label.setStyleSheet(f"color:{accent};font-size:22px;font-weight:800;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _make_badge(self, text: str, background: str, color: str) -> QtWidgets.QFrame:
        badge = QtWidgets.QFrame(self)
        badge.setStyleSheet(
            f"QFrame {{ background:{background}; border-radius:12px; border:1px solid rgba(255,255,255,0.18); }}"
        )
        layout = QtWidgets.QHBoxLayout(badge)
        layout.setContentsMargins(12, 10, 12, 10)
        label = QtWidgets.QLabel(text, badge)
        label.setStyleSheet(f"color:{color};font-size:12px;font-weight:700;")
        layout.addWidget(label)
        layout.addStretch(1)
        badge._label = label  # type: ignore[attr-defined]
        return badge

    def _make_launch_button(self, text: str, handler, accent: str) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text, self)
        button.setMinimumHeight(44)
        button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        button.setStyleSheet(
            "QPushButton {"
            f"background:{accent};"
            "color:#FFFFFF;"
            "border:none;"
            "border-radius:12px;"
            "padding:10px 12px;"
            "font-size:12px;font-weight:700;"
            "text-align:left;"
            "}"
            "QPushButton:hover { background: #23588F; }"
        )
        button.clicked.connect(handler)
        return button

    def _trigger_widget_click(self, name: str) -> None:
        widget = getattr(self, name, None)
        if widget is not None and hasattr(widget, "click"):
            widget.click()

    def _call_controller_action(self, name: str) -> None:
        controller = getattr(self, "controller", None)
        if controller is None:
            return
        handler = getattr(controller, name, None)
        if callable(handler):
            handler()

    def _make_chart_card(self, title: str, tall: bool = False) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame(self)
        card.setObjectName("dashCard")
        card.setStyleSheet(
            "QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }"
        )
        if tall:
            card.setMinimumHeight(280)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        title_label = QtWidgets.QLabel(title, card)
        title_label.setStyleSheet("font-size:13px;font-weight:700;color:#274B72;")
        layout.addWidget(title_label)
        canvas_host = QtWidgets.QFrame(card)
        canvas_host.setStyleSheet("background:#F8FBFE;border:1px dashed #D4DFEA;border-radius:10px;")
        canvas_layout = QtWidgets.QVBoxLayout(canvas_host)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        layout.addWidget(canvas_host, 1)
        card._canvas_host = canvas_host  # type: ignore[attr-defined]
        card._title_label = title_label  # type: ignore[attr-defined]
        return card

    def _set_metric_value(self, key: str, text: str) -> None:
        metrics = getattr(self, "_dashboard_metrics", {})
        widget = metrics.get(key)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(text)

    def _set_label_text(self, attr_name: str, text: str) -> None:
        widget = getattr(self, attr_name, None)
        if widget is None:
            return
        if hasattr(widget, "setText"):
            widget.setText(text)
        elif hasattr(widget, "_label") and hasattr(widget._label, "setText"):
            widget._label.setText(text)

    def _update_recent_projects(self) -> None:
        from core.project_manager import get_recent_projects
        from pathlib import Path

        recent_paths = get_recent_projects(3)
        labels = [Path(path).stem for path in recent_paths]

        for index, button in enumerate(getattr(self, "_dashboard_recent_buttons", [])):
            if button is None:
                continue
            if index < len(labels):
                button.setText(labels[index])
                button.setToolTip(recent_paths[index])
                button.setEnabled(True)
            else:
                button.setText("No recent project")
                button.setToolTip("No recent project available")
                button.setEnabled(False)

    def _update_activity_list(self, project_name: str, well, df) -> None:
        activity_list = getattr(self, "_dashboard_activity_list", None)
        if activity_list is None:
            return

        activity_list.clear()
        items: list[str] = [f"Project: {project_name}"]
        if well is not None and df is not None:
            depth_col = None
            for name in df.columns:
                if str(name).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                    depth_col = name
                    break
            if depth_col is not None:
                import pandas as pd

                depth_values = pd.to_numeric(df[depth_col], errors="coerce").dropna()
                if not depth_values.empty:
                    items.append(f"Depth range: {depth_values.min():.1f} to {depth_values.max():.1f} m")
            items.append(f"Loaded curves: {len(df.columns)}")
            items.append(f"Samples: {len(df):,}")
            items.append("Dashboard refreshed from the active well.")
        else:
            items.append("Import a LAS or CSV file to activate the charts.")

        for text in items:
            activity_list.addItem(text)

    def _estimate_data_quality(self, df) -> float:
        if df is None or getattr(df, "empty", True):
            return 0.0

        import pandas as pd

        numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
        if not numeric_columns:
            return 0.0

        null_values = [float(df[column].isna().mean() * 100) for column in numeric_columns]
        quality = 100.0 - (sum(null_values) / len(null_values))
        return max(0.0, min(100.0, quality))

    def _update_dashboard_charts(self, df) -> None:
        if df is None or getattr(df, "empty", True):
            self._render_dashboard_message(self._dashboard_hist_frame, "No data loaded yet.")
            self._render_dashboard_message(self._dashboard_lith_frame, "No data loaded yet.")
            return

        import numpy as np
        import pandas as pd

        depth_col = None
        for name in df.columns:
            if str(name).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                depth_col = name
                break

        numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
        if not numeric_columns:
            self._render_dashboard_message(self._dashboard_hist_frame, "No numeric curves found.")
            self._render_dashboard_message(self._dashboard_lith_frame, "No numeric curves found.")
            return

        gr_curve = None
        for candidate in ("GR", "CGR", "GAPI", "API"):
            if candidate in df.columns and pd.api.types.is_numeric_dtype(df[candidate]):
                gr_curve = candidate
                break
        if gr_curve is None:
            gr_curve = numeric_columns[0]

        self._render_histogram_chart(self._dashboard_hist_frame, df[gr_curve], gr_curve)
        self._render_lithology_chart(self._dashboard_lith_frame, df[gr_curve], gr_curve)

    def _render_dashboard_message(self, frame: QtWidgets.QFrame, message: str) -> None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
        ax.axis("off")
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11, color="#5C718A", wrap=True)
        self._render_figure_to_frame(frame, fig)

    def _render_histogram_chart(self, frame: QtWidgets.QFrame, series, curve_name: str) -> None:
        import matplotlib.pyplot as plt
        import pandas as pd

        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if numeric.empty:
            self._render_dashboard_message(frame, f"No valid samples found for {curve_name}.")
            return

        fig, ax = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
        ax.hist(numeric, bins=24, color="#74B86A", edgecolor="white", alpha=0.92)
        ax.set_title(f"{curve_name} Distribution", fontsize=12, fontweight="600")
        ax.set_xlabel(curve_name)
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.16)
        self._render_figure_to_frame(frame, fig)

    def _render_lithology_chart(self, frame: QtWidgets.QFrame, series, curve_name: str) -> None:
        import matplotlib.pyplot as plt
        import pandas as pd

        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if numeric.empty:
            self._render_dashboard_message(frame, f"No valid samples found for {curve_name}.")
            return

        q1, q2, q3 = numeric.quantile([0.25, 0.5, 0.75]).tolist()
        bins = [numeric.min(), q1, q2, q3, numeric.max()]
        counts = [
            int(((numeric >= bins[0]) & (numeric <= bins[1])).sum()),
            int(((numeric > bins[1]) & (numeric <= bins[2])).sum()),
            int(((numeric > bins[2]) & (numeric <= bins[3])).sum()),
            int(((numeric > bins[3]) & (numeric <= bins[4])).sum()),
        ]
        labels = ["Sandstone", "Limestone", "Shale", "Dolomite"]
        colors = ["#4AA3DF", "#7E8BFF", "#4FD1C5", "#F5B661"]

        fig, ax = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
        ax.pie(counts, startangle=90, colors=colors, wedgeprops={"width": 0.42, "edgecolor": "white"})
        ax.set_title(f"{curve_name} Breakdown", fontsize=12, fontweight="600")
        ax.legend(labels, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=8)
        self._render_figure_to_frame(frame, fig)

    def _render_figure_to_frame(self, frame: QtWidgets.QFrame, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
        except Exception:
            return

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, frame)
        toolbar.setStyleSheet(
            "QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }"
        )

        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()

    def _notify_dashboard_refresh(self) -> None:
        try:
            self.refresh_dashboard_tab()
        except Exception:
            pass
    def _embed_borehole_analysis_tab(self) -> None:
        """Embeds the new FMI/Borehole Image analysis module into the existing FMI tab."""
        tab_fmi = getattr(self, "tabFMIAnalysis", None)
        if tab_fmi is None:
            return
        layout = tab_fmi.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab_fmi)
        self._clear_layout(layout)
        
        from borehole_image.image_analysis_tab import ImageAnalysisTab
        self.borehole_analysis_widget = ImageAnalysisTab()
        layout.addWidget(self.borehole_analysis_widget)

    def _embed_pore_pressure_tab(self) -> None:
        """Embeds the new Pore Pressure analysis module into the existing tab."""
        tab_pp = getattr(self, "tabPorePressure", None)
        if tab_pp is None:
            return
        layout = tab_pp.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab_pp)
            layout.setContentsMargins(0, 0, 0, 0)
        self._clear_layout(layout)
        try:
            from geomechanics.pore_pressure_tab import PorePressureTab
            self._pore_pressure_widget = PorePressureTab()
            layout.addWidget(self._pore_pressure_widget)
        except Exception as exc:
            err_lbl = QtWidgets.QLabel(f"Pore Pressure module failed to load:\n{exc}")
            err_lbl.setStyleSheet("color: #FF6B6B; padding: 20px; font-size: 12px;")
            err_lbl.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(err_lbl)
            self._pore_pressure_widget = None

    def _inject_pore_pressure_data_service(self) -> None:
        """Pass the live DataService into the Pore Pressure tab."""
        widget = getattr(self, "_pore_pressure_widget", None)
        if widget is None:
            return
        data_svc = getattr(self, "_data_service", None)
        if data_svc is None:
            controller = getattr(self, "controller", None)
            if controller is not None:
                data_svc = getattr(controller, "data", None)
        if data_svc is not None and hasattr(widget, "set_data_service"):
            widget.set_data_service(data_svc)

    def refresh_pore_pressure_tab(self) -> None:
        self._inject_pore_pressure_data_service()
        widget = getattr(self, "_pore_pressure_widget", None)
        if widget is not None and hasattr(widget, "_refresh_data"):
            try:
                widget._refresh_data()
            except Exception:
                pass

    def _embed_well_correlation_tab(self) -> None:
        """Replace the Well Correlation tab's built-in UI with the advanced widget."""
        tab_wc = getattr(self, "tabWellCorrelation", None)
        if tab_wc is None:
            return
        layout = tab_wc.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab_wc)
            layout.setContentsMargins(0, 0, 0, 0)
        self._clear_layout(layout)
        try:
            from well_correlation.correlation_tab import WellCorrelationTab
            self._well_correlation_widget = WellCorrelationTab(data_service=None)
            layout.addWidget(self._well_correlation_widget)
        except Exception as exc:
            err_lbl = QtWidgets.QLabel(f"Well Correlation module failed to load:\n{exc}")
            err_lbl.setStyleSheet("color: #FF6B6B; padding: 20px; font-size: 12px;")
            err_lbl.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(err_lbl)
            self._well_correlation_widget = None

    def _inject_correlation_data_service(self) -> None:
        """Pass the live DataService into the Well Correlation tab."""
        widget = getattr(self, "_well_correlation_widget", None)
        if widget is None:
            return
        data_svc = getattr(self, "_data_service", None)
        if data_svc is None:
            controller = getattr(self, "controller", None)
            if controller is not None:
                data_svc = getattr(controller, "data", None)
        if data_svc is not None and hasattr(widget, "set_data_service"):
            widget.set_data_service(data_svc)

    def refresh_well_correlation_tab(self) -> None:
        """Called after well import/deletion to refresh the correlation tab well list."""
        widget = getattr(self, "_well_correlation_widget", None)
        if widget is not None and hasattr(widget, "_refresh_well_list"):
            try:
                widget._refresh_well_list()
            except Exception:
                pass


    def _embed_data_analysis_tab(self) -> None:
        """Replace the Data Info & Stats tab with the Data & Analysis dock contents."""
        data_tab = getattr(self, "tabDataInfoStats", None)

        dock = getattr(self, "dockData", None)
        if data_tab is None or dock is None:
            return

        # If already embedded, skip.
        existing_tab = getattr(self, "tabData", None)
        if existing_tab is not None and existing_tab.parent() is data_tab:
            return

        dock_contents = dock.widget() or getattr(self, "dockDataContents", None)
        if dock_contents is None:
            return

        # Clear existing widgets in the tab (keep the layout to avoid warnings)
        existing_layout = data_tab.layout()
        if existing_layout is not None:
            while existing_layout.count():
                item = existing_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
        else:
            existing_layout = QtWidgets.QVBoxLayout(data_tab)
            existing_layout.setContentsMargins(0, 0, 0, 0)

        # Detach contents from dock and hide the dock
        if dock.widget() is dock_contents:
            dock.setWidget(None)
        dock.hide()

        dock_contents.setParent(data_tab)
        dock_contents.setVisible(True)
        dock_contents.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        existing_layout.setContentsMargins(0, 0, 0, 0)
        existing_layout.addWidget(dock_contents)

    def _connect_tab_switches(self) -> None:
        """Wire toolbar/menu actions and dashboard buttons to tab indices."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None:
            return

        def tab_index(tab_name: str, fallback: int | None = None) -> int | None:
            tab = getattr(self, tab_name, None)
            if tab is not None:
                idx = tab_widget.indexOf(tab)
                if idx >= 0:
                    return idx
            return fallback

        def connect_action(action_name: str, idx: int) -> None:
            action = getattr(self, action_name, None)
            if action is None:
                return
            action.triggered.connect(
                lambda checked=False, tab_idx=idx: tab_widget.setCurrentIndex(tab_idx)
            )

        def connect_button(button_name: str, idx: int) -> None:
            button = getattr(self, button_name, None)
            if button is None:
                return
            button.clicked.connect(
                lambda checked=False, tab_idx=idx: tab_widget.setCurrentIndex(tab_idx)
            )

        def connect_action_to_tab(action_name: str, tab_name: str, fallback_idx: int) -> None:
            idx = tab_index(tab_name, fallback_idx)
            if idx is not None:
                connect_action(action_name, idx)

        # Toolbar / menu actions -> main tabs
        connect_action_to_tab("actionNewLogPlot", "tabLogViewer", 1)
        connect_action_to_tab("actiondatainfo", "tabDataInfoStats", 2)
        connect_action_to_tab("actionNewCrossplot", "tabLogViewer", 1)
        connect_action_to_tab("actionNewHistogram", "tabLogViewer", 1)
        connect_action_to_tab("actionQualityControl", "tabQualitycontrol", 3)
        connect_action_to_tab("actionFormationTesting", "tabFormationevaluation", 4)
        rose_idx = tab_index("tabRoseDiagram", None)
        if rose_idx is not None:
            connect_action("actionNewRoseDiagram", rose_idx)
        connect_action_to_tab("actionShaleVolume", "tabShaleVolume", 6)
        connect_action_to_tab("actionPorosityCalc", "tabPorosity", 7)
        connect_action_to_tab("actionWaterSaturation", "tabWaterSaturation", 8)
        connect_action_to_tab("actionPermeability", "tabPermeability", 9)
        connect_action_to_tab("actionNetPay", "tabNetPay", 10)
        connect_action_to_tab("actionWellCorrelation", "tabWellCorrelation", 11)
        connect_action_to_tab("actionMultimineralAnalysis", "tabMultiMineral", 12)
        connect_action_to_tab("actionFMIAnalysis", "tabFMIAnalysis", 13)
        connect_action_to_tab("actionWellboreStability", "tabWellboreStability", 14)
        connect_action_to_tab("actionPorePressure", "tabPorePressure", 15)

        geo_idx = tab_index("tabGeomechanics", 16)
        if geo_idx is not None:
            for name in (
                "actionStressAnalysis",
                "actionWellboreStability",
                "actionFractureAnalysis",
                "actionPorePressure",
                "actionUCS",
                "actionYoungsModulus",
                "actionPoissonRatio",
                "actionBrittlenessIndex",
                "actionMudWeightWindow",
            ):
                connect_action(name, geo_idx)

            connect_button("btnDashGeo", geo_idx)
        else:
            connect_button("btnDashGeo", 16)

        # Dashboard quick-launch buttons
        connect_button("btnDashLogView", tab_index("tabLogViewer", 1) or 1)
        connect_button("btnDashXplot", tab_index("tabLogViewer", 1) or 1)
        connect_button("btnDashVsh", tab_index("tabShaleVolume", 6) or 6)
        connect_button("btnDashSw", tab_index("tabWaterSaturation", 8) or 8)
        connect_button("btnDashCorr", tab_index("tabWellCorrelation", 11) or 11)

    def _connect_edit_actions(self) -> None:
        action_map = {
            "actionUndo": "undo",
            "actionRedo": "redo",
            "actionCut": "cut",
            "actionCopy": "copy",
            "actionPaste": "paste",
            "actionDelete": "delete",
            "actionSelectAll": "select_all",
        }
        for action_name, op_name in action_map.items():
            action = getattr(self, action_name, None)
            if action is None:
                continue
            action.triggered.connect(lambda checked=False, op=op_name: self._run_edit_operation(op))

    def _run_edit_operation(self, op_name: str) -> None:
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return

        if op_name == "copy" and self._copy_from_item_view(focus):
            return
        if op_name == "cut" and self._cut_from_item_view(focus):
            return
        if op_name == "paste" and self._paste_to_item_view(focus):
            return
        if op_name == "delete" and self._delete_from_item_view(focus):
            return

        for widget in self._focus_widget_chain(focus):
            if op_name == "delete" and self._delete_text(widget):
                return
            method_name = "selectAll" if op_name == "select_all" else op_name
            method = getattr(widget, method_name, None)
            if callable(method):
                method()
                return

        fallback_shortcuts = {
            "undo": QtGui.QKeySequence.Undo,
            "redo": QtGui.QKeySequence.Redo,
            "cut": QtGui.QKeySequence.Cut,
            "copy": QtGui.QKeySequence.Copy,
            "paste": QtGui.QKeySequence.Paste,
            "select_all": QtGui.QKeySequence.SelectAll,
            "delete": QtGui.QKeySequence.Delete,
        }
        sequence = fallback_shortcuts.get(op_name)
        if sequence is None:
            return
        key = sequence[0]
        modifiers = QtCore.Qt.KeyboardModifiers(key & int(QtCore.Qt.KeyboardModifierMask))
        key_code = key & ~int(QtCore.Qt.KeyboardModifierMask)
        press = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key_code, modifiers)
        release = QtGui.QKeyEvent(QtCore.QEvent.KeyRelease, key_code, modifiers)
        QtWidgets.QApplication.sendEvent(focus, press)
        QtWidgets.QApplication.sendEvent(focus, release)

    def _focus_widget_chain(self, widget: QtWidgets.QWidget) -> list[QtWidgets.QWidget]:
        chain: list[QtWidgets.QWidget] = []
        current = widget
        while current is not None:
            chain.append(current)
            current = current.parentWidget()
        return chain

    def _delete_text(self, widget: QtWidgets.QWidget) -> bool:
        if hasattr(widget, "del_") and callable(getattr(widget, "del_")):
            widget.del_()
            return True

        if isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            cursor = widget.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()
            else:
                cursor.deleteChar()
            widget.setTextCursor(cursor)
            return True
        return False

    def _copy_from_item_view(self, widget: QtWidgets.QWidget) -> bool:
        view = self._as_item_view(widget)
        if view is None:
            return False
        model = view.model()
        if model is None:
            return False

        indexes = view.selectionModel().selectedIndexes() if view.selectionModel() is not None else []
        if not indexes:
            return False

        rows = sorted({index.row() for index in indexes})
        cols = sorted({index.column() for index in indexes})
        selected = {(index.row(), index.column()): index for index in indexes}

        lines: list[str] = []
        for row in rows:
            parts: list[str] = []
            for col in cols:
                index = selected.get((row, col))
                text = "" if index is None else str(model.data(index, QtCore.Qt.DisplayRole) or "")
                parts.append(text)
            lines.append("\t".join(parts))

        QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        return True

    def _cut_from_item_view(self, widget: QtWidgets.QWidget) -> bool:
        copied = self._copy_from_item_view(widget)
        if not copied:
            return False
        return self._delete_from_item_view(widget)

    def _paste_to_item_view(self, widget: QtWidgets.QWidget) -> bool:
        view = self._as_item_view(widget)
        if view is None:
            return False
        model = view.model()
        if model is None:
            return False

        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            return False

        start = view.currentIndex()
        if not start.isValid():
            return False

        rows = text.splitlines()
        if not rows:
            return False

        for row_offset, row_text in enumerate(rows):
            cells = row_text.split("\t")
            for col_offset, cell_text in enumerate(cells):
                index = model.index(start.row() + row_offset, start.column() + col_offset)
                if not index.isValid():
                    continue
                model.setData(index, cell_text, QtCore.Qt.EditRole)
        return True

    def _delete_from_item_view(self, widget: QtWidgets.QWidget) -> bool:
        view = self._as_item_view(widget)
        if view is None:
            return False
        model = view.model()
        if model is None:
            return False

        indexes = view.selectionModel().selectedIndexes() if view.selectionModel() is not None else []
        if not indexes:
            return False

        for index in indexes:
            model.setData(index, "", QtCore.Qt.EditRole)
        return True

    def _as_item_view(self, widget: QtWidgets.QWidget) -> QtWidgets.QAbstractItemView | None:
        for candidate in self._focus_widget_chain(widget):
            if isinstance(candidate, QtWidgets.QAbstractItemView):
                return candidate
        return None
    
    def closeEvent(self, event):
        """Handle application close - prompt to save if modified.
        
        Args:
            event: QCloseEvent
        """
        if self.controller.projects.is_project_modified():
            reply = QtWidgets.QMessageBox.question(
                self,
                "Save Project?",
                "Project has unsaved changes. Save before closing?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
            )
            
            if reply == QtWidgets.QMessageBox.Save:
                self.controller.projects.save_project()
                event.accept()
            elif reply == QtWidgets.QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def _reorder_tabs(self) -> None:
        """Put the main analysis tabs in a stable, user-friendly order."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None:
            return

        desired_order = [
            "tabDashboard",
            "tabDataInfoStats",
            "tabLogViewer",
            "tabQualitycontrol",
            "tabFormationevaluation",
        ]

        current_tab = tab_widget.currentWidget()
        tab_state: list[tuple[QtWidgets.QWidget, str, QtGui.QIcon, str, str]] = []
        for index in range(tab_widget.count()):
            widget = tab_widget.widget(index)
            tab_state.append(
                (
                    widget,
                    tab_widget.tabText(index),
                    tab_widget.tabIcon(index),
                    tab_widget.tabToolTip(index),
                    tab_widget.tabWhatsThis(index),
                )
            )

        lookup = {
            widget: (text, icon, tooltip, whatsthis)
            for widget, text, icon, tooltip, whatsthis in tab_state
        }

        ordered_widgets: list[QtWidgets.QWidget] = []
        seen: set[QtWidgets.QWidget] = set()
        for tab_name in desired_order:
            widget = getattr(self, tab_name, None)
            if widget is None or widget in seen or tab_widget.indexOf(widget) < 0:
                continue
            ordered_widgets.append(widget)
            seen.add(widget)

        rose_tab = getattr(self, "tabRoseDiagram", None)
        for widget, *_rest in tab_state:
            if rose_tab is not None and widget is rose_tab:
                continue
            if widget not in seen:
                ordered_widgets.append(widget)
                seen.add(widget)

        if [widget for widget, *_rest in tab_state] == ordered_widgets:
            return

        for index in reversed(range(tab_widget.count())):
            tab_widget.removeTab(index)

        for widget in ordered_widgets:
            text, icon, tooltip, whatsthis = lookup[widget]
            new_index = tab_widget.addTab(widget, icon, text)
            if tooltip:
                tab_widget.setTabToolTip(new_index, tooltip)
            if whatsthis:
                tab_widget.setTabWhatsThis(new_index, whatsthis)

        dashboard = getattr(self, "tabDashboard", None)
        if dashboard is not None and tab_widget.indexOf(dashboard) >= 0:
            tab_widget.setCurrentWidget(dashboard)
        elif current_tab is not None:
            tab_widget.setCurrentWidget(current_tab)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PetroVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
