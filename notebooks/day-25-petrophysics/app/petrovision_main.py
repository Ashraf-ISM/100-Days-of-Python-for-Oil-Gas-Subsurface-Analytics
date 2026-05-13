from __future__ import annotations

import sys
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui, uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "mainwindow.ui"
THREE_D_WELL_UI_FILE = "tab_3d_well_visualization.ui" # Ui for the 3d well 
WELL_CORRELATION_UI_FILE = "multiwell_correlation.ui" # Ui file for well correlation
FACIES_CLASSIFICATION_UI_FILE = "facies_classifications.ui" # UI For the facies classifications
ASSETS_DIR = ROOT_DIR / "assets"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from controllers.main_controller import MainController  # noqa: E402
from well_correlation.multiwell_correlation_workspace import MultiWellCorrelationWorkspaceController  # noqa: E402
from Well_3d.well_3d_workspace import Well3DWorkspaceController  # noqa: E402
from plotting.log_availability_radar import build_log_availability_radar_figure  # noqa: E402

from extra.dialogs import AboutHelpDialog

class PetroVisionMainWindow(QtWidgets.QMainWindow):
    def __init__(self, project_path: str | None = None):
        super().__init__()
        ui_path = UI_DIR / UI_FILE  
        uic.loadUi(str(ui_path), self)
        self.setWindowTitle("PetroARX v1.0 - Petrophysics Interpretation Platform")
        
        # Set Window Icon
        logo_path = ASSETS_DIR / "logo-petroarx.png"
        if logo_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(logo_path)))
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is not None:
            self.setCentralWidget(tab_widget)
        self._embed_data_analysis_tab()
        self._embed_borehole_analysis_tab()
        self._embed_pore_pressure_tab()
        self._embed_3d_well_tab()
        self._embed_well_correlation_tab()
        self._init_facies_window()      # standalone separate window (not a tab) 
        self._reorder_tabs()
        self._install_3d_well_action()
        self._connect_tab_switches()
        self._connect_edit_actions()
        # Application-wide undo/redo stack
        self._undo_stack = QtWidgets.QUndoStack(self)
        self._undo_stack.setUndoLimit(100)
        self.controller = MainController(self)
        self._wire_3d_well_controls()
        # Project Browser — delegate to dedicated module
        from ui.project_browser_panel import ProjectBrowserPanel
        self._browser_panel = ProjectBrowserPanel(self)
        self._build_dashboard()
        self.refresh_dashboard_tab()
        self.refresh_3d_well_tab()
        
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

        # AI Analytics connections
        if hasattr(self, "actionMissingLogPrediction"):
            self.actionMissingLogPrediction.triggered.connect(self._open_missing_log_prediction)

    def _open_data_downloader(self) -> None:
        from data.data_downloader_dialog import DataDownloaderWindow
        if not hasattr(self, '_data_downloader_win'):
            self._data_downloader_win = DataDownloaderWindow(self)
        self._data_downloader_win.show()
        self._data_downloader_win.raise_()
        self._data_downloader_win.activateWindow()


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

        # Add Logo to Dashboard
        logo_label = QtWidgets.QLabel(hero)
        logo_pixmap = QtGui.QPixmap(str(ASSETS_DIR / "logo-petroarx.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(120, 120, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        hero_layout.addWidget(logo_label)

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
        self._dashboard_radar_frame = self._make_chart_card("Dynamic Log Availability Radar Chart")
        visual_grid.addWidget(self._dashboard_hist_frame, 0, 0)
        visual_grid.addWidget(self._dashboard_radar_frame, 0, 1)
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

        # + Well / Import Well buttons – exposed as named attributes so the
        # controller can wire them after it is constructed.
        btn_add_well = self._make_launch_button("+ Well", self._add_new_well, "#0E7A63")
        btn_add_well.setObjectName("btnDashAddWell")
        setattr(self, "btnDashAddWell", btn_add_well)

        btn_import_well = self._make_launch_button("Import Well", self._add_new_well, "#2F6FB3")
        btn_import_well.setObjectName("btnDashImportWell")
        setattr(self, "btnDashImportWell", btn_import_well)

        self._dashboard_quick_buttons = [
            btn_add_well,
            btn_import_well,
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


    def _add_new_well(self) -> None:
        """Trigger the well-import dialog (used by '+ Well' / 'Import Well' buttons
        on the dashboard and the Well ▸ Add New Well menu action)."""
        data_svc = getattr(getattr(self, "controller", None), "data", None)
        if data_svc is not None and callable(getattr(data_svc, "import_data", None)):
            imported = data_svc.import_data()
            if imported:
                projects_svc = getattr(getattr(self, "controller", None), "projects", None)
                if projects_svc is not None and callable(getattr(projects_svc, "mark_modified", None)):
                    projects_svc.mark_modified()
        else:
            # controller not yet ready – queue for after init
            QtCore.QTimer.singleShot(200, self._add_new_well)

    def _load_demo_data(self) -> None:
        data_svc = getattr(self.controller, "data", None)
        if data_svc is None:
            return
            
        demo_path = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/data/_Gorgonichthys_1_suite3_supercombo_log_Gorgonichthys1_suite2_CMR.las"
        import os
        if not os.path.exists(demo_path):
            QtWidgets.QMessageBox.warning(self, "Demo Data", f"Demo data file not found:\n{demo_path}")
            return
            
        # pyrefly: ignore [missing-import]
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

    def refresh_porosity_tab(self) -> None:
        data_service = getattr(self.controller, "data", None)
        well = None
        if data_service is not None:
            well = data_service._get_current_well()
            
        df = getattr(well, "data", None) if well is not None else None
        curves = list(df.columns) if df is not None else []
        
        for combo_name, default_search in [
            ("comboPoroDepth", ["DEPTH", "DEPT", "MD"]),
            ("comboPoroRhob", ["RHOB", "ZDEN", "DEN"]),
            ("comboPoroNphi", ["NPHI", "CNC", "NEUT"]),
            ("comboPoroDt", ["DT", "AC", "SON"]),
            ("comboPoroGr", ["GR", "GAM"])
        ]:
            combo = getattr(self, combo_name, None)
            if combo is not None:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(curves)
                # Try to auto-select matching curve
                selected = False
                for search in default_search:
                    for idx, curve in enumerate(curves):
                        if search.upper() in curve.upper():
                            combo.setCurrentIndex(idx)
                            selected = True
                            break
                    if selected: break
                combo.blockSignals(False)

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
            self._render_dashboard_message(self._dashboard_radar_frame, "No data loaded yet.")
            return

        import pandas as pd

        numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
        if not numeric_columns:
            self._render_dashboard_message(self._dashboard_hist_frame, "No numeric curves found.")
            self._render_dashboard_message(self._dashboard_radar_frame, "No numeric curves found.")
            return

        gr_curve = None
        for candidate in ("GR", "CGR", "GAPI", "API"):
            if candidate in df.columns and pd.api.types.is_numeric_dtype(df[candidate]):
                gr_curve = candidate
                break
        if gr_curve is None:
            gr_curve = numeric_columns[0]

        self._render_histogram_chart(self._dashboard_hist_frame, df[gr_curve], gr_curve)
        self._render_log_availability_radar(self._dashboard_radar_frame, df)

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

    def _render_log_availability_radar(self, frame: QtWidgets.QFrame, df) -> None:
        if df is None or getattr(df, "empty", True):
            self._render_dashboard_message(frame, "No data loaded yet.")
            return

        fig = build_log_availability_radar_figure(df)
        self._render_figure_to_frame(frame, fig)

    def _render_figure_to_frame(self, frame: QtWidgets.QFrame, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
            from plotting.plot_context_menu import install_plot_context_menu
        except Exception:
            return

        host = getattr(frame, "_canvas_host", frame)
        layout = host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, host)
        toolbar.setStyleSheet(
            "QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }"
        )

        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        install_plot_context_menu(canvas, fig, host)

        # Close the figure to free up memory from the pyplot global manager
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass


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

    def _embed_3d_well_tab(self) -> None:
        """Create a dedicated 3D well workspace from a standalone Qt Designer UI."""
        tab_widget = getattr(self, "centralTabWidget", None)
        if tab_widget is None or getattr(self, "tab3DWell", None) is not None:
            return

        ui_path = UI_DIR / THREE_D_WELL_UI_FILE
        try:
            page = uic.loadUi(str(ui_path))
        except Exception as exc:
            page = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(page)
            layout.setContentsMargins(18, 18, 18, 18)
            label = QtWidgets.QLabel(f"3D Well workspace failed to load:\n{exc}", page)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setStyleSheet("color:#FF6B6B;font-size:12px;font-weight:600;")
            layout.addWidget(label)

        page.setObjectName("tab3DWell")
        self.tab3DWell = page
        tab_index = tab_widget.addTab(page, "3D Well")
        tab_widget.setTabToolTip(tab_index, "3D well trajectory and survey workspace")
        try:
            self._well_3d_controller = Well3DWorkspaceController(self, page)
        except Exception as exc:
            layout = page.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(page)
                layout.setContentsMargins(18, 18, 18, 18)
            fallback = QtWidgets.QLabel(f"3D Well backend failed to initialize:\n{exc}", page)
            fallback.setAlignment(QtCore.Qt.AlignCenter)
            fallback.setStyleSheet("color:#FF6B6B;font-size:12px;font-weight:600;")
            layout.addWidget(fallback)
            self._well_3d_controller = None

    def _install_3d_well_action(self) -> None:
        if getattr(self, "action3DWellViewer", None) is not None:
            return
        self.action3DWellViewer = QtWidgets.QAction("3D Well Viewer", self)
        self.action3DWellViewer.setObjectName("action3DWellViewer")
        self.action3DWellViewer.setToolTip("Open the 3D well trajectory workspace")
        menu_well = getattr(self, "menuWell", None)
        if menu_well is not None:
            menu_well.addSeparator()
            menu_well.addAction(self.action3DWellViewer)

    def _wire_3d_well_controls(self) -> None:
        controller = getattr(self, "_well_3d_controller", None)
        if controller is not None:
            controller.connect_signals()
            return

        button_map = {
            "btn3DLoadWell": getattr(getattr(self, "controller", None), "data", None).import_data
            if getattr(getattr(self, "controller", None), "data", None) is not None
            else None,
            "btn3DRefresh": self.refresh_3d_well_tab,
            "btn3DExportView": self._export_3d_well_view,
            "btn3DResetView": lambda: self._set_3d_camera(24, -58),
            "btn3DTopView": lambda: self._set_3d_camera(90, -90),
            "btn3DSideView": lambda: self._set_3d_camera(5, -90),
        }
        for name, handler in button_map.items():
            button = getattr(self, name, None)
            if button is not None and handler is not None:
                button.clicked.connect(handler)

        combo = getattr(self, "combo3DWell", None)
        if combo is not None:
            combo.currentTextChanged.connect(self._on_3d_well_selected)

        for name in (
            "combo3DVerticalExag",
            "combo3DColorMode",
            "chk3DShowTrajectory",
            "chk3DShowMarkers",
            "chk3DShowGrid",
            "chk3DShowLabels",
        ):
            widget = getattr(self, name, None)
            if widget is None:
                continue
            signal = getattr(widget, "currentTextChanged", None) or getattr(widget, "toggled", None)
            if signal is not None:
                signal.connect(lambda *args: self.refresh_3d_well_tab())

    def _on_3d_well_selected(self, name: str) -> None:
        if not name:
            return
        controller = getattr(self, "controller", None)
        data_service = getattr(controller, "data", None) if controller is not None else None
        wells = getattr(data_service, "_wells", {}) if data_service is not None else {}
        if name not in wells:
            return
        data_service.set_current_well(name)

    def refresh_3d_well_tab(self) -> None:
        controller = getattr(self, "_well_3d_controller", None)
        if controller is not None:
            controller.refresh()
            return

        combo = getattr(self, "combo3DWell", None)

        controller = getattr(self, "controller", None)
        data_service = getattr(self, "_data_service", None)
        if data_service is None and controller is not None:
            data_service = getattr(controller, "data", None)

        wells = getattr(data_service, "_wells", {}) or {}
        well_names = sorted(wells.keys())
        current_name = getattr(data_service, "_current_well", None) if data_service is not None else None

        if combo is not None:
            blocker = QtCore.QSignalBlocker(combo)
            combo.clear()
            combo.addItems(well_names)
            if current_name in well_names:
                combo.setCurrentText(current_name)
            elif well_names:
                combo.setCurrentIndex(0)
            del blocker

        if not well_names:
            self._set_3d_metric("lbl3DMDRangeValue", "--")
            self._set_3d_metric("lbl3DTVDRangeValue", "--")
            self._set_3d_metric("lbl3DXRangeValue", "--")
            self._set_3d_metric("lbl3DYRangeValue", "--")
            self._set_3d_metric("lbl3DDeviationValue", "--")
            self._set_3d_metric("lbl3DPointsValue", "--")
            self._set_3d_metric("lbl3DHeroActiveWell", "Active well: --")
            self._set_3d_metric("lbl3DHeroTrajectory", "Trajectory source: Waiting for well data")
            self._set_3d_status("Status: Import a well to generate a 3D trajectory preview.")
            self._populate_3d_survey_table(None)
            self._update_3d_insights([
                "No wells are currently loaded into the project.",
                "Import a LAS, CSV, or supported log file to activate the 3D workspace.",
            ])
            self._render_3d_well_message("No wells loaded yet.\nImport a well to generate a 3D trajectory preview.")
            return

        selected_name = combo.currentText().strip() if combo is not None else ""
        if selected_name not in wells:
            selected_name = current_name if current_name in wells else well_names[0]
        well = wells.get(selected_name)
        self._set_3d_metric("lbl3DHeroActiveWell", f"Active well: {selected_name}")

        trajectory, source_text = self._build_3d_well_trajectory(well)
        self._set_3d_metric("lbl3DHeroTrajectory", f"Trajectory source: {source_text}")

        if trajectory is None or trajectory.empty:
            self._set_3d_metric("lbl3DMDRangeValue", "--")
            self._set_3d_metric("lbl3DTVDRangeValue", "--")
            self._set_3d_metric("lbl3DXRangeValue", "--")
            self._set_3d_metric("lbl3DYRangeValue", "--")
            self._set_3d_metric("lbl3DDeviationValue", "--")
            self._set_3d_metric("lbl3DPointsValue", "0")
            self._set_3d_status(f"Status: {source_text}")
            self._populate_3d_survey_table(None)
            self._update_3d_insights([
                f"Well '{selected_name}' is loaded, but no numeric depth trajectory could be derived.",
                "Check the imported curves for measured depth, TVD, deviation, azimuth, or coordinate columns.",
            ])
            self._render_3d_well_message(source_text)
            return

        md_min = float(trajectory["md"].min())
        md_max = float(trajectory["md"].max())
        tvd_min = float(trajectory["tvd"].min())
        tvd_max = float(trajectory["tvd"].max())
        x_min = float(trajectory["x"].min())
        x_max = float(trajectory["x"].max())
        y_min = float(trajectory["y"].min())
        y_max = float(trajectory["y"].max())
        max_dev = float(trajectory["deviation"].max()) if "deviation" in trajectory else 0.0

        self._set_3d_metric("lbl3DMDRangeValue", f"{(md_max - md_min):,.1f} m")
        self._set_3d_metric("lbl3DTVDRangeValue", f"{(tvd_max - tvd_min):,.1f} m")
        self._set_3d_metric("lbl3DXRangeValue", f"{x_min:,.0f} to {x_max:,.0f}")
        self._set_3d_metric("lbl3DYRangeValue", f"{y_min:,.0f} to {y_max:,.0f}")
        self._set_3d_metric("lbl3DDeviationValue", f"{max_dev:,.1f}°")
        self._set_3d_metric("lbl3DPointsValue", f"{len(trajectory):,}")
        self._set_3d_status(f"Status: {source_text}")

        df = getattr(well, "data", None)
        curve_count = len(getattr(df, "columns", [])) if df is not None else 0
        lateral_span = float(trajectory["lateral"].max()) if "lateral" in trajectory else 0.0
        self._update_3d_insights([
            f"Loaded well '{selected_name}' with {curve_count} curves and {len(trajectory):,} trajectory samples.",
            f"Measured depth span is {md_max - md_min:,.1f} m with a TVD span of {tvd_max - tvd_min:,.1f} m.",
            f"Maximum lateral offset reaches {lateral_span:,.1f} m and the peak deviation is {max_dev:,.1f}°.",
            source_text,
        ])
        self._populate_3d_survey_table(trajectory)
        self._plot_3d_well_trajectory(selected_name, trajectory)

    def _build_3d_well_trajectory(self, well):
        import numpy as np
        import pandas as pd

        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return None, "No well data available for trajectory rendering."

        md_col = self._match_well_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        tvd_col = self._match_well_column(df, "TVD", "TVDSS", "TRUEVERTICALDEPTH")
        x_col = self._match_well_column(df, "X", "XCOORD", "XCOORDINATE", "EASTING", "UTMX")
        y_col = self._match_well_column(df, "Y", "YCOORD", "YCOORDINATE", "NORTHING", "UTMY")
        dev_col = self._match_well_column(df, "DEVIATION", "DEVI", "DEV", "INC", "INCLINATION")
        azi_col = self._match_well_column(df, "AZIMUTH", "AZI", "AZM")

        trajectory = pd.DataFrame()
        if md_col is not None:
            trajectory["md"] = pd.to_numeric(df[md_col], errors="coerce")
            md_source = f"MD from '{md_col}'"
        else:
            trajectory["md"] = np.arange(len(df), dtype=float)
            md_source = "MD synthesized from sample index"

        for key, column in (
            ("tvd", tvd_col),
            ("x", x_col),
            ("y", y_col),
            ("deviation", dev_col),
            ("azimuth", azi_col),
        ):
            if column is not None:
                trajectory[key] = pd.to_numeric(df[column], errors="coerce")

        trajectory = trajectory.dropna(subset=["md"]).sort_values("md").drop_duplicates("md").reset_index(drop=True)
        if trajectory.empty:
            return None, "No valid numeric depth values were found in the selected well."

        delta_md = trajectory["md"].diff().fillna(0.0).clip(lower=0.0).to_numpy()
        notes = [md_source]

        if "tvd" in trajectory:
            trajectory["tvd"] = trajectory["tvd"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["tvd"] = trajectory["tvd"] - float(trajectory["tvd"].iloc[0])
            notes.append(f"TVD from '{tvd_col}'")
        elif "deviation" in trajectory:
            deviation_rad = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            trajectory["tvd"] = np.cumsum(delta_md * np.cos(deviation_rad))
            notes.append(f"TVD estimated from '{dev_col}'")
        else:
            trajectory["tvd"] = trajectory["md"] - float(trajectory["md"].iloc[0])
            notes.append("Vertical TVD assumption from measured depth")

        if "x" in trajectory and "y" in trajectory:
            trajectory["x"] = trajectory["x"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["y"] = trajectory["y"].interpolate(limit_direction="both").bfill().ffill()
            trajectory["x"] = trajectory["x"] - float(trajectory["x"].iloc[0])
            trajectory["y"] = trajectory["y"] - float(trajectory["y"].iloc[0])
            notes.append(f"Plan view from '{x_col}' and '{y_col}'")
        elif "deviation" in trajectory and "azimuth" in trajectory:
            deviation_rad = np.radians(trajectory["deviation"].fillna(0.0).to_numpy())
            azimuth_rad = np.radians(trajectory["azimuth"].fillna(0.0).to_numpy())
            step = delta_md * np.sin(deviation_rad)
            trajectory["x"] = np.cumsum(step * np.sin(azimuth_rad))
            trajectory["y"] = np.cumsum(step * np.cos(azimuth_rad))
            notes.append(f"Lateral offsets estimated from '{dev_col}' and '{azi_col}'")
        else:
            trajectory["x"] = 0.0
            trajectory["y"] = 0.0
            notes.append("Vertical well path assumed (no coordinate survey found)")

        if "deviation" not in trajectory:
            trajectory["deviation"] = self._compute_deviation_from_path(
                trajectory["x"].to_numpy(),
                trajectory["y"].to_numpy(),
                trajectory["tvd"].to_numpy(),
            )
        else:
            trajectory["deviation"] = trajectory["deviation"].ffill().fillna(0.0)

        trajectory["lateral"] = np.sqrt((trajectory["x"] ** 2) + (trajectory["y"] ** 2))
        return trajectory, " | ".join(notes)

    def _match_well_column(self, df, *aliases: str) -> str | None:
        lookup = {}
        for column in df.columns:
            normalized = "".join(ch for ch in str(column).upper() if ch.isalnum())
            lookup.setdefault(normalized, column)

        for alias in aliases:
            key = "".join(ch for ch in alias.upper() if ch.isalnum())
            if key in lookup:
                return lookup[key]

        for column in df.columns:
            normalized = "".join(ch for ch in str(column).upper() if ch.isalnum())
            if any("".join(ch for ch in alias.upper() if ch.isalnum()) in normalized for alias in aliases):
                return column
        return None

    def _compute_deviation_from_path(self, x_vals, y_vals, tvd_vals):
        import numpy as np

        dx = np.diff(x_vals, prepend=x_vals[0])
        dy = np.diff(y_vals, prepend=y_vals[0])
        dz = np.diff(tvd_vals, prepend=tvd_vals[0])
        lateral = np.sqrt((dx ** 2) + (dy ** 2))
        vertical = np.maximum(np.abs(dz), 1e-9)
        return np.degrees(np.arctan2(lateral, vertical))

    def _set_3d_metric(self, widget_name: str, text: str) -> None:
        widget = getattr(self, widget_name, None)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(text)

    def _set_3d_status(self, text: str) -> None:
        label = getattr(self, "lbl3DStatusValue", None)
        if label is not None:
            label.setText(text)

    def _update_3d_insights(self, lines: list[str]) -> None:
        widget = getattr(self, "list3DInsights", None)
        if widget is None:
            return
        widget.clear()
        for line in lines:
            widget.addItem(line)

    def _populate_3d_survey_table(self, trajectory) -> None:
        table = getattr(self, "table3DSurveyPreview", None)
        if table is None:
            return

        headers = ["MD", "TVD", "X Offset", "Y Offset", "Deviation"]
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        if trajectory is None or getattr(trajectory, "empty", True):
            table.setRowCount(0)
            return

        preview = trajectory[["md", "tvd", "x", "y", "deviation"]].head(14).reset_index(drop=True)
        table.setRowCount(len(preview))
        for row_idx, row in preview.iterrows():
            for col_idx, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(f"{float(value):,.2f}")
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                table.setItem(row_idx, col_idx, item)

        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

    def _plot_3d_well_trajectory(self, well_name: str, trajectory) -> None:
        import numpy as np
        import matplotlib.pyplot as plt

        if trajectory is None or getattr(trajectory, "empty", True):
            self._render_3d_well_message("No trajectory data available for plotting.")
            return

        exag_text = getattr(getattr(self, "combo3DVerticalExag", None), "currentText", lambda: "1.0x")()
        try:
            vertical_exag = float(str(exag_text).lower().replace("x", "").strip())
        except ValueError:
            vertical_exag = 1.0

        x_vals = trajectory["x"].to_numpy(dtype=float)
        y_vals = trajectory["y"].to_numpy(dtype=float)
        z_vals = trajectory["tvd"].to_numpy(dtype=float) * vertical_exag

        color_mode = getattr(getattr(self, "combo3DColorMode", None), "currentText", lambda: "Measured Depth")()
        if color_mode == "True Vertical Depth":
            color_values = trajectory["tvd"].to_numpy(dtype=float)
            color_label = "TVD (m)"
            cmap = "viridis"
        elif color_mode == "Lateral Offset":
            color_values = trajectory["lateral"].to_numpy(dtype=float)
            color_label = "Lateral Offset (m)"
            cmap = "plasma"
        else:
            color_values = trajectory["md"].to_numpy(dtype=float)
            color_label = "Measured Depth (m)"
            cmap = "cividis"

        fig = plt.figure(figsize=(8.6, 5.8), constrained_layout=True)
        fig.patch.set_facecolor("#F8FBFE")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#FFFFFF")

        if getattr(getattr(self, "chk3DShowTrajectory", None), "isChecked", lambda: True)():
            ax.plot(x_vals, y_vals, z_vals, color="#1F5F99", linewidth=2.6, alpha=0.92)

        scatter = None
        if getattr(getattr(self, "chk3DShowMarkers", None), "isChecked", lambda: True)():
            scatter = ax.scatter(
                x_vals,
                y_vals,
                z_vals,
                c=color_values,
                cmap=cmap,
                s=26,
                alpha=0.95,
                depthshade=True,
                edgecolors="#FFFFFF",
                linewidths=0.35,
            )
        else:
            ax.scatter(x_vals[-1:], y_vals[-1:], z_vals[-1:], color="#FF8A3D", s=48, depthshade=True)

        if scatter is not None:
            colorbar = fig.colorbar(scatter, ax=ax, pad=0.07, shrink=0.82)
            colorbar.set_label(color_label)

        if getattr(getattr(self, "chk3DShowLabels", None), "isChecked", lambda: True)():
            ax.text(x_vals[0], y_vals[0], z_vals[0], "  Wellhead", color="#0F3C66", fontsize=9, weight="bold")
            ax.text(x_vals[-1], y_vals[-1], z_vals[-1], "  TD", color="#D66A1F", fontsize=9, weight="bold")

        ax.set_title(f"{well_name}  |  3D Well Trajectory", fontsize=13, fontweight="bold", color="#163B61", pad=16)
        ax.set_xlabel("X Offset (m)", labelpad=10)
        ax.set_ylabel("Y Offset (m)", labelpad=10)
        ax.set_zlabel(f"TVD x{vertical_exag:.1f} (m)", labelpad=12)
        ax.view_init(elev=24, azim=-58)
        ax.invert_zaxis()

        if getattr(getattr(self, "chk3DShowGrid", None), "isChecked", lambda: True)():
            ax.grid(True, alpha=0.24)
        else:
            ax.grid(False)

        max_range = max(float(np.ptp(x_vals)), float(np.ptp(y_vals)), float(np.ptp(z_vals)), 1.0)
        mid_x = float(np.mean([x_vals.min(), x_vals.max()]))
        mid_y = float(np.mean([y_vals.min(), y_vals.max()]))
        mid_z = float(np.mean([z_vals.min(), z_vals.max()]))
        half_range = max_range / 2.0
        ax.set_xlim(mid_x - half_range, mid_x + half_range)
        ax.set_ylim(mid_y - half_range, mid_y + half_range)
        ax.set_zlim(mid_z + half_range, mid_z - half_range)

        self._render_3d_well_figure(fig, ax)

    def _render_3d_well_message(self, message: str) -> None:
        frame = getattr(self, "frame3DPlotHost", None)
        if frame is None:
            return
        self._three_d_well_axes = None
        self._three_d_well_canvas = None
        self._three_d_well_figure = None

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(10, 10, 10, 10)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        label = QtWidgets.QLabel(message, frame)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color:#5C718A;font-size:12px;font-weight:600;padding:18px;")
        layout.addWidget(label)

    def _render_3d_well_figure(self, fig, ax) -> None:
        frame = getattr(self, "frame3DPlotHost", None)
        if frame is None:
            return
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
        except Exception as exc:
            self._render_3d_well_message(f"Matplotlib Qt backend is unavailable:\n{exc}")
            return

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(10, 10, 10, 10)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#F8FBFE;border:none;")
        layout.addWidget(canvas, 1)
        self._three_d_well_figure = fig
        self._three_d_well_axes = ax
        self._three_d_well_canvas = canvas
        canvas.draw_idle()
        try:
            from plotting.plot_context_menu import install_plot_context_menu
            install_plot_context_menu(canvas, fig, frame)
        except Exception:
            pass

    def _set_3d_camera(self, elev: float, azim: float) -> None:
        controller = getattr(self, "_well_3d_controller", None)
        if controller is not None:
            controller.set_camera(elev, azim)
            return

        axes = getattr(self, "_three_d_well_axes", None)
        canvas = getattr(self, "_three_d_well_canvas", None)
        if axes is None or canvas is None or not hasattr(axes, "view_init"):
            return
        axes.view_init(elev=elev, azim=azim)
        canvas.draw_idle()

    def _export_3d_well_view(self) -> None:
        controller = getattr(self, "_well_3d_controller", None)
        if controller is not None:
            controller.export_view()
            return

        fig = getattr(self, "_three_d_well_figure", None)
        if fig is None:
            QtWidgets.QMessageBox.information(self, "3D Well Export", "No 3D trajectory figure is available yet.")
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export 3D Well Figure",
            str(ROOT_DIR / "outputs" / "3d_well_view.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;PDF Document (*.pdf)",
        )
        if not file_path:
            return
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(file_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
            QtWidgets.QMessageBox.information(self, "3D Well Export", f"Figure exported successfully:\n{file_path}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "3D Well Export", f"Failed to export figure:\n{exc}")

    def _embed_well_correlation_tab(self) -> None:
        """Replace the Well Correlation tab with the standalone Qt Designer workspace."""
        tab_wc = getattr(self, "tabWellCorrelation", None)
        if tab_wc is None:
            return
        layout = tab_wc.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab_wc)
            layout.setContentsMargins(0, 0, 0, 0)
        self._clear_layout(layout)
        try:
            workspace = uic.loadUi(str(UI_DIR / WELL_CORRELATION_UI_FILE))
            workspace.setWindowFlags(QtCore.Qt.Widget)
            layout.addWidget(workspace)
            self._well_correlation_widget = workspace
            self._well_correlation_controller = MultiWellCorrelationWorkspaceController(self, workspace)
        except Exception as exc:
            err_lbl = QtWidgets.QLabel(f"Well Correlation module failed to load:\n{exc}")
            err_lbl.setStyleSheet("color: #FF6B6B; padding: 20px; font-size: 12px;")
            err_lbl.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(err_lbl)
            self._well_correlation_widget = None
            self._well_correlation_controller = None

    def _inject_correlation_data_service(self) -> None:
        """Pass the live DataService into the Well Correlation tab."""
        controller = getattr(self, "_well_correlation_controller", None)
        if controller is None:
            return
        data_svc = getattr(self, "_data_service", None)
        if data_svc is None:
            controller = getattr(self, "controller", None)
            if controller is not None:
                data_svc = getattr(controller, "data", None)
        if data_svc is not None and hasattr(controller, "set_data_service"):
            controller.set_data_service(data_svc)

    def refresh_well_correlation_tab(self) -> None:
        """Called after well import/deletion to refresh the correlation tab well list."""
        controller = getattr(self, "_well_correlation_controller", None)
        if controller is not None and hasattr(controller, "refresh"):
            try:
                controller.refresh()
            except Exception:
                pass


    # ─── Facies Classification – standalone window ───────────────────────────────

    def _init_facies_window(self) -> None:
        """Pre-create the standalone Facies Classification window (hidden)."""
        self._facies_win: "FaciesClassificationWindow | None" = None
        try:
            from Facies_classifications.facies_window import FaciesClassificationWindow
            self._facies_win = FaciesClassificationWindow(UI_DIR, parent=None)
            # Inject data service if already available
            self._inject_facies_data_service()
        except Exception as exc:
            print(f"[PetroARX] Facies window could not be pre-created: {exc}")
            self._facies_win = None

    def _inject_facies_data_service(self) -> None:
        """Pass the live DataService into the Facies Classification window."""
        win = getattr(self, "_facies_win", None)
        if win is None:
            return
        data_svc = getattr(self, "_data_service", None)
        if data_svc is None:
            ctrl = getattr(self, "controller", None)
            if ctrl is not None:
                data_svc = getattr(ctrl, "data", None)
        if data_svc is not None and hasattr(win, "set_data_service"):
            win.set_data_service(data_svc)

    def _open_missing_log_prediction(self) -> None:
        """Create and show the Missing Log Prediction dashboard using modular script."""
        if not hasattr(self, "_missing_log_win") or self._missing_log_win is None:
            try:
                from ai_analytics.missing_log.missing_log_window import MissingLogPredictionWindow
                self._missing_log_win = MissingLogPredictionWindow(UI_DIR, parent=None)
                
                # Pass data service
                self._inject_missing_log_data_service()

            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "AI Analytics Error", 
                    f"Could not launch Missing Log Prediction module:\n{exc}")
                self._missing_log_win = None
                return

        self._missing_log_win.show()
        self._missing_log_win.raise_()
        self._missing_log_win.activateWindow()

    def _inject_missing_log_data_service(self) -> None:
        """Pass the live DataService into the Missing Log Prediction window."""
        win = getattr(self, "_missing_log_win", None)
        if win is None:
            return
        data_svc = getattr(self, "controller", None).data if hasattr(self, "controller") else None
        if data_svc is not None and hasattr(win, "set_data_service"):
            win.set_data_service(data_svc)

    def refresh_facies_classification_tab(self) -> None:
        """Called by DataService after well import/deletion – refreshes the window."""
        self._inject_facies_data_service()
        win = getattr(self, "_facies_win", None)
        if win is not None and hasattr(win, "refresh"):
            try:
                win.refresh()
            except Exception:
                pass

    def _open_facies_window(self, algorithm: str | None = None) -> None:
        """Show the standalone Facies Classification window.

        Parameters
        ----------
        algorithm:
            One of 'kmeans', 'gmm', 'som', 'ensemble', 'randomforest', or
            None (open without pre-selection).
        """
        # Lazy-create if the pre-creation failed
        if getattr(self, "_facies_win", None) is None:
            self._init_facies_window()

        win = getattr(self, "_facies_win", None)
        if win is None:
            QtWidgets.QMessageBox.critical(
                self,
                "Facies Classification",
                "The Facies Classification module could not be loaded.\n"
                "Please check that all dependencies (scikit-learn, matplotlib, "
                "pandas) are installed.",
            )
            return

        # Always inject the latest DataService before showing
        self._inject_facies_data_service()
        win.show_with_algorithm(algorithm)

    # ─── Data Analysis tab ────────────────────────────────────────────────────

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
        connect_action_to_tab("action3DWellViewer", "tab3DWell", 3)
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

        # ── Facies Classification menu actions ──────────────────────────────
        self._wire_facies_menu_actions(tab_widget)

    def _wire_facies_menu_actions(self, tab_widget: QtWidgets.QTabWidget) -> None:  # noqa: ARG002
        """Wire every Facies Classification menu action to _open_facies_window()."""

        # action name → algorithm key passed to _open_facies_window
        action_algo_map = {
            "actionOpenFaciesWorkspace": None,           # no pre-selection
            "actionFaciesKMeans":        "kmeans",
            "actionFaciesGMM":           "gmm",
            "actionFaciesSOM":           "som",
            "actionFaciesEnsemble":      "ensemble",
            "actionFaciesRandomForest":  "randomforest",
            "actionSupervised":          "ensemble",     # legacy menu item
            "actionUnsupervised":        "kmeans",       # legacy menu item
        }

        for action_name, algo_key in action_algo_map.items():
            action = getattr(self, action_name, None)
            if action is None:
                continue
            action.triggered.connect(
                lambda checked=False, _algo=algo_key: self._open_facies_window(_algo)
            )

    def _connect_edit_actions(self) -> None:
        """Wire every Edit menu action to a fully functional handler."""

        # ── Undo / Redo ─────────────────────────────────────────────────────
        undo_action = getattr(self, "actionUndo", None)
        redo_action = getattr(self, "actionRedo", None)
        if undo_action is not None:
            undo_action.setShortcut(QtGui.QKeySequence.Undo)
            undo_action.setEnabled(False)   # enabled once stack has history
            undo_action.triggered.connect(self._do_undo)
        if redo_action is not None:
            redo_action.setShortcut(QtGui.QKeySequence.Redo)
            redo_action.setEnabled(False)
            redo_action.triggered.connect(self._do_redo)

        # ── Clipboard operations ────────────────────────────────────────────
        clipboard_map = {
            "actionCut":       (QtGui.QKeySequence.Cut,       self._do_cut),
            "actionCopy":      (QtGui.QKeySequence.Copy,      self._do_copy),
            "actionPaste":     (QtGui.QKeySequence.Paste,     self._do_paste),
            "actionDelete":    (QtGui.QKeySequence.Delete,    self._do_delete),
            "actionSelectAll": (QtGui.QKeySequence.SelectAll, self._do_select_all),
        }
        for action_name, (shortcut, handler) in clipboard_map.items():
            action = getattr(self, action_name, None)
            if action is not None:
                action.setShortcut(shortcut)
                action.triggered.connect(handler)

        # ── Preferences ─────────────────────────────────────────────────────
        pref_action = getattr(self, "actionPreferences ", None)
        if pref_action is not None:
            pref_action.setShortcut(QtGui.QKeySequence("Ctrl+,"))
            pref_action.triggered.connect(self._open_preferences)

    # ─── Undo / Redo ──────────────────────────────────────────────────────

    def _do_undo(self) -> None:
        """Undo: first try the focused widget's own undo, then the app stack."""
        focus = QtWidgets.QApplication.focusWidget()
        # Let native text widgets handle it first (they have their own undo)
        for widget in self._iter_focus_chain(focus):
            if isinstance(widget, (QtWidgets.QLineEdit,
                                   QtWidgets.QTextEdit,
                                   QtWidgets.QPlainTextEdit)):
                if hasattr(widget, "undo") and callable(widget.undo):
                    widget.undo()
                    return
        # Fall back to the application-level undo stack
        stack = getattr(self, "_undo_stack", None)
        if stack is not None and stack.canUndo():
            stack.undo()
            self._refresh_undo_redo_state()

    def _do_redo(self) -> None:
        """Redo: first try the focused widget's own redo, then the app stack."""
        focus = QtWidgets.QApplication.focusWidget()
        for widget in self._iter_focus_chain(focus):
            if isinstance(widget, (QtWidgets.QLineEdit,
                                   QtWidgets.QTextEdit,
                                   QtWidgets.QPlainTextEdit)):
                if hasattr(widget, "redo") and callable(widget.redo):
                    widget.redo()
                    return
        stack = getattr(self, "_undo_stack", None)
        if stack is not None and stack.canRedo():
            stack.redo()
            self._refresh_undo_redo_state()

    def _refresh_undo_redo_state(self) -> None:
        """Enable/disable Undo & Redo menu items based on stack state."""
        stack = getattr(self, "_undo_stack", None)
        if stack is None:
            return
        undo_action = getattr(self, "actionUndo", None)
        redo_action = getattr(self, "actionRedo", None)
        if undo_action is not None:
            undo_action.setEnabled(stack.canUndo())
            undo_action.setText(f"Undo {stack.undoText()}" if stack.canUndo() else "Undo")
        if redo_action is not None:
            redo_action.setEnabled(stack.canRedo())
            redo_action.setText(f"Redo {stack.redoText()}" if stack.canRedo() else "Redo")

    def push_undo_command(self, command: QtWidgets.QUndoCommand) -> None:
        """Push a custom undo command onto the application stack.

        Use this from any controller that wants Undo/Redo support::

            class SetCurveCommand(QUndoCommand):
                ...
            self.main_window.push_undo_command(SetCurveCommand(...))
        """
        stack = getattr(self, "_undo_stack", None)
        if stack is not None:
            stack.push(command)
            self._refresh_undo_redo_state()

    # ─── Clipboard helpers ───────────────────────────────────────────────────

    def _iter_focus_chain(self, widget) -> list:
        """Walk up the widget parent chain from *widget*."""
        chain = []
        current = widget
        while current is not None:
            chain.append(current)
            current = current.parentWidget()
        return chain

    def _do_cut(self) -> None:
        """Cut selected content from the focused widget."""
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return
        # Native text widgets
        if isinstance(focus, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            if hasattr(focus, "cut"):
                focus.cut()
            return
        # Item views — copy then clear
        if self._clipboard_copy_item_view(focus):
            self._clear_item_view_selection(focus)
            return
        # Fallback: synthesise Ctrl+X key event
        self._send_key_event(focus, QtCore.Qt.Key_X, QtCore.Qt.ControlModifier)

    def _do_copy(self) -> None:
        """Copy selected content from the focused widget."""
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return
        if isinstance(focus, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            if hasattr(focus, "copy"):
                focus.copy()
            return
        if self._clipboard_copy_item_view(focus):
            return
        self._send_key_event(focus, QtCore.Qt.Key_C, QtCore.Qt.ControlModifier)

    def _do_paste(self) -> None:
        """Paste clipboard content into the focused widget."""
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return
        if isinstance(focus, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            if hasattr(focus, "paste"):
                focus.paste()
            return
        if self._clipboard_paste_item_view(focus):
            return
        self._send_key_event(focus, QtCore.Qt.Key_V, QtCore.Qt.ControlModifier)

    def _do_delete(self) -> None:
        """Delete selected content from the focused widget."""
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return
        # Text widgets — delete selection or next char
        if isinstance(focus, (QtWidgets.QLineEdit,)):
            cursor_pos = focus.cursorPosition()
            sel_start  = focus.selectionStart()
            if focus.hasSelectedText():
                focus.del_()
            else:
                focus.setSelection(cursor_pos, 1)
                focus.del_()
            return
        if isinstance(focus, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            cursor = focus.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()
            else:
                cursor.deleteChar()
            focus.setTextCursor(cursor)
            return
        # Item views — clear cell content
        if self._clear_item_view_selection(focus):
            return
        self._send_key_event(focus, QtCore.Qt.Key_Delete, QtCore.Qt.NoModifier)

    def _do_select_all(self) -> None:
        """Select all content in the focused widget."""
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return
        if isinstance(focus, (QtWidgets.QLineEdit,)):
            focus.selectAll()
            return
        if isinstance(focus, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            focus.selectAll()
            return
        if isinstance(focus, QtWidgets.QAbstractItemView):
            focus.selectAll()
            return
        self._send_key_event(focus, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)

    # ─── Item-view clipboard helpers ────────────────────────────────────────────

    def _find_item_view(self, widget) -> "QtWidgets.QAbstractItemView | None":
        """Return the first QAbstractItemView in the focus chain."""
        for candidate in self._iter_focus_chain(widget):
            if isinstance(candidate, QtWidgets.QAbstractItemView):
                return candidate
        return None

    def _clipboard_copy_item_view(self, widget) -> bool:
        view = self._find_item_view(widget)
        if view is None:
            return False
        model = view.model()
        sel_model = view.selectionModel()
        if model is None or sel_model is None:
            return False
        indexes = sel_model.selectedIndexes()
        if not indexes:
            return False
        rows = sorted({idx.row() for idx in indexes})
        cols = sorted({idx.column() for idx in indexes})
        cell_map = {(idx.row(), idx.column()): idx for idx in indexes}
        lines = []
        for row in rows:
            parts = []
            for col in cols:
                cell_idx = cell_map.get((row, col))
                text = str(model.data(cell_idx, QtCore.Qt.DisplayRole) or "") if cell_idx else ""
                parts.append(text)
            lines.append("\t".join(parts))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        return True

    def _clipboard_paste_item_view(self, widget) -> bool:
        view = self._find_item_view(widget)
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
        for row_off, row_text in enumerate(text.splitlines()):
            for col_off, cell_text in enumerate(row_text.split("\t")):
                cell_idx = model.index(start.row() + row_off, start.column() + col_off)
                if cell_idx.isValid():
                    model.setData(cell_idx, cell_text, QtCore.Qt.EditRole)
        return True

    def _clear_item_view_selection(self, widget) -> bool:
        view = self._find_item_view(widget)
        if view is None:
            return False
        model = view.model()
        sel_model = view.selectionModel()
        if model is None or sel_model is None:
            return False
        indexes = sel_model.selectedIndexes()
        if not indexes:
            return False
        for idx in indexes:
            model.setData(idx, "", QtCore.Qt.EditRole)
        return True

    @staticmethod
    def _send_key_event(
        widget: QtWidgets.QWidget,
        key: int,
        modifiers: QtCore.Qt.KeyboardModifiers,
    ) -> None:
        """Synthesise a key-press + key-release event on *widget*.

        This replaces the old segfault-prone approach of indexing a
        QKeySequence.StandardKey enum value with ``sequence[0]``.
        """
        press = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifiers)
        release = QtGui.QKeyEvent(QtCore.QEvent.KeyRelease, key, modifiers)
        QtWidgets.QApplication.sendEvent(widget, press)
        QtWidgets.QApplication.sendEvent(widget, release)

    # ─── Legacy helpers (kept for any external callers) ──────────────────────────

    def _run_edit_operation(self, op_name: str) -> None:
        """Dispatch *op_name* to the correct handler (backward-compat shim)."""
        dispatch = {
            "undo":       self._do_undo,
            "redo":       self._do_redo,
            "cut":        self._do_cut,
            "copy":       self._do_copy,
            "paste":      self._do_paste,
            "delete":     self._do_delete,
            "select_all": self._do_select_all,
        }
        handler = dispatch.get(op_name)
        if handler is not None:
            handler()

    def _focus_widget_chain(self, widget):
        return self._iter_focus_chain(widget)

    def _copy_from_item_view(self, widget) -> bool:
        return self._clipboard_copy_item_view(widget)

    def _cut_from_item_view(self, widget) -> bool:
        if self._clipboard_copy_item_view(widget):
            return self._clear_item_view_selection(widget)
        return False

    def _paste_to_item_view(self, widget) -> bool:
        return self._clipboard_paste_item_view(widget)

    def _delete_from_item_view(self, widget) -> bool:
        return self._clear_item_view_selection(widget)

    def _as_item_view(self, widget) -> "QtWidgets.QAbstractItemView | None":
        return self._find_item_view(widget)

    def _delete_text(self, widget) -> bool:
        if isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            cursor = widget.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()
            else:
                cursor.deleteChar()
            widget.setTextCursor(cursor)
            return True
        return False

    # ─── Preferences dialog ───────────────────────────────────────────────────

    def _open_preferences(self) -> None:
        """Show the Preferences dialog (create on first call, reuse after)."""
        if not hasattr(self, "_pref_dialog") or self._pref_dialog is None:
            self._pref_dialog = _PreferencesDialog(self)
        self._pref_dialog.show()
        self._pref_dialog.raise_()
        self._pref_dialog.activateWindow()



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
            "tab3DWell",
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

    # Set App Icon
    logo_path = ASSETS_DIR / "logo-petroarx.png"
    if logo_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(logo_path)))

    splash = None   # important

    # Splash Screen
    splash_path = ASSETS_DIR / "splash-petroarx.png"

    if splash_path.exists():
        pixmap = QtGui.QPixmap(str(splash_path))
        splash = QtWidgets.QSplashScreen(pixmap)
        splash.show()

        splash.showMessage(
            "Loading PetroARX...",
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignCenter,
            QtCore.Qt.white
        )

        app.processEvents()

    # Load Main Window
    window = PetroVisionMainWindow()

    if splash:
        splash.showMessage(
            "Initializing AI Modules...",
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignCenter,
            QtCore.Qt.white
        )
        app.processEvents()

        QtCore.QTimer.singleShot(
            3000,   # control splash time here
            lambda: (
                window.show(),
                splash.finish(window)
            )
        )
    else:
        window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()