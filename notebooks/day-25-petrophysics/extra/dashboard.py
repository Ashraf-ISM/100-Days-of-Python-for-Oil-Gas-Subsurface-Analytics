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