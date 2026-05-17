"""
dashboard_panel.py
==================
Self-contained controller for the Dashboard tab (``tabDashboard``)
in PetroARX.

Follows the same delegation pattern used by ``ProjectBrowserPanel``.

Usage
-----
Instantiate once inside ``PetroVisionMainWindow.__init__``::

    from ui.dashboard_panel import DashboardPanel
    self._dashboard_panel = DashboardPanel(self)
"""
from __future__ import annotations

from pathlib import Path
# pyrefly: ignore [missing-import]
from PyQt5 import QtWidgets, QtCore, QtGui

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"


class DashboardPanel:
    """Builds and manages the Dashboard tab UI and refresh logic."""

    def __init__(self, ui: QtWidgets.QMainWindow) -> None:
        self.ui = ui
        self._build()

    # ---- helpers to reach into main window ----
    def _w(self, name: str):
        return getattr(self.ui, name, None)

    def _data_service(self):
        ctrl = getattr(self.ui, "controller", None)
        return getattr(ctrl, "data", None) if ctrl else None

    def _project_service(self):
        ctrl = getattr(self.ui, "controller", None)
        return getattr(ctrl, "projects", None) if ctrl else None

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build(self) -> None:
        tab = self._w("tabDashboard")
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)
        self._clear_layout(layout)

        scroll = QtWidgets.QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("border:0;background:transparent;")

        content = QtWidgets.QWidget(scroll)
        cl = QtWidgets.QVBoxLayout(content)
        cl.setContentsMargins(18, 18, 18, 18)
        cl.setSpacing(14)

        # --- Hero ---
        hero = QtWidgets.QFrame(content)
        hero.setObjectName("dashHero")
        hero.setStyleSheet(
            "QFrame#dashHero {"
            "background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #031B44, stop:0.55 #07356E, stop:1 #0A5FA8);"
            "border:1px solid rgba(255,255,255,0.08);"
            "border-radius:20px;"
            "}"
        )
        hl = QtWidgets.QHBoxLayout(hero)
        hl.setContentsMargins(18, 16, 18, 16)
        hl.setSpacing(12)

        hero_text = QtWidgets.QVBoxLayout()
        ht = QtWidgets.QLabel("PetroARX Dashboard", hero)
        ht.setStyleSheet("color:#F1F7FF;font-size:20px;font-weight:800;")
        hs = QtWidgets.QLabel("AI-powered petrophysical interpretation workspace", hero)
        hs.setStyleSheet("color:rgba(230,241,255,0.9);font-size:11px;font-weight:500;")
        hs.setWordWrap(True)

        info_row = QtWidgets.QHBoxLayout()
        info_row.setSpacing(0)
        self.ui._dashboard_well_label = self._make_hero_info_item(hero, "ACTIVE WELL", "-", "#61E594")
        self.ui._dashboard_project_label = self._make_hero_info_item(hero, "PROJECT", "No Project", "#51B3FF")
        self.ui._dashboard_depth_label = self._make_hero_info_item(hero, "DEPTH RANGE", "-", "#A9C7FF")
        self.ui._dashboard_last_updated_label = self._make_hero_info_item(hero, "LAST UPDATED", "-", "#A9C7FF")
        info_row.addWidget(self.ui._dashboard_well_label, 1)
        info_row.addWidget(self.ui._dashboard_project_label, 1)
        info_row.addWidget(self.ui._dashboard_depth_label, 1)
        info_row.addWidget(self.ui._dashboard_last_updated_label, 1)

        hero_text.addWidget(ht)
        hero_text.addWidget(hs)
        hero_text.addSpacing(6)
        hero_text.addLayout(info_row)
        hero_text.addStretch(1)
        hl.addLayout(hero_text, 8)

        logo_card = QtWidgets.QFrame(hero)
        logo_card.setStyleSheet(
            "QFrame { background:rgba(1,11,29,0.64); border:1px solid rgba(83,178,255,0.38); border-radius:16px; }"
        )
        logo_layout = QtWidgets.QVBoxLayout(logo_card)
        logo_layout.setContentsMargins(12, 12, 12, 12)
        logo_label = QtWidgets.QLabel(logo_card)
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        logo_pixmap = QtGui.QPixmap(str(ASSETS_DIR / "logo-petroarx.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        logo_layout.addWidget(logo_label, 1)
        hl.addWidget(logo_card, 1)

        status_col = QtWidgets.QVBoxLayout()
        status_col.setSpacing(6)
        self.ui._dashboard_badge_one = self._make_status_item("PROJECT STATUS", "Ready", "#61E594")
        self.ui._dashboard_badge_two = self._make_status_item("DATA INTEGRITY", "0%", "#66D7FF")
        self.ui._dashboard_missing_logs = self._make_status_item("MISSING LOGS", "0 Logs", "#FFB04D")
        self.ui._dashboard_interpretation = self._make_status_item("INTERPRETATION READINESS", "Waiting for data", "#50AAFF")
        status_col.addWidget(self.ui._dashboard_badge_one)
        status_col.addWidget(self.ui._dashboard_badge_two)
        status_col.addWidget(self.ui._dashboard_missing_logs)
        status_col.addWidget(self.ui._dashboard_interpretation)
        hl.addLayout(status_col, 2)
        cl.addWidget(hero)

        # --- Metrics row ---
        metrics_row = QtWidgets.QHBoxLayout()
        metrics_row.setSpacing(10)
        self.ui._dashboard_metrics = {}
        for title, subtitle, key, accent in (
            ("WELLS LOADED", "Active well", "wells_loaded", "#2F6FB3"),
            ("CURVES LOADED", "Total curves", "curve_count", "#6A46D7"),
            ("AVG DATA QUALITY", "Excellent", "data_quality", "#E98313"),
            ("CURRENT SAMPLES", "Total data points", "sample_count", "#1FA65F"),
        ):
            card, val = self._make_metric_card(title, subtitle, accent)
            self.ui._dashboard_metrics[key] = val
            metrics_row.addWidget(card)
        cl.addLayout(metrics_row)

        # --- Body ---
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(14)

        left = QtWidgets.QVBoxLayout()
        left.setSpacing(14)

        # Data Visualization
        vis = self._make_section("Data Visualization")
        vg = QtWidgets.QGridLayout()
        vg.setSpacing(12)
        self.ui._dashboard_hist_frame = self._make_chart_card("GR Distribution")
        self.ui._dashboard_radar_frame = self._make_chart_card("Dynamic Log Availability Radar Chart")
        vg.addWidget(self.ui._dashboard_hist_frame, 0, 0)
        vg.addWidget(self.ui._dashboard_radar_frame, 0, 1)
        vis.layout().addLayout(vg)
        left.addWidget(vis, 3)

        # Quick Workflow
        wf = self._make_section("Quick Workflow")
        wfg = QtWidgets.QGridLayout()
        wfg.setSpacing(10)
        self.ui._dashboard_workflow_buttons = [
            self._w("btnDashImportLAS"), self._w("btnDashImportCSV"),
            self._w("btnDashImportSEGY"), self._w("btnDashLogView"),
            self._w("btnDashXplot"), self._w("btnDashVsh"),
            self._w("btnDashSw"), self._w("btnDashGeo"),
            self._w("btnDashCorr"),
        ]
        btns = [b for b in self.ui._dashboard_workflow_buttons if b is not None]
        for i, b in enumerate(btns):
            b.setMinimumHeight(42)
            b.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            r, c = divmod(i, 3)
            wfg.addWidget(b, r, c)
        wf.layout().addLayout(wfg)
        left.addWidget(wf, 1)

        # Right column
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(14)

        # Quick Actions
        qa = self._make_section("Quick Actions")
        qg = QtWidgets.QGridLayout()
        qg.setSpacing(10)

        btn_add = self._make_launch_button("+ Well", self._add_new_well, "#0E7A63")
        btn_add.setObjectName("btnDashAddWell")
        setattr(self.ui, "btnDashAddWell", btn_add)

        btn_imp = self._make_launch_button("Import Well", self._add_new_well, "#2F6FB3")
        btn_imp.setObjectName("btnDashImportWell")
        setattr(self.ui, "btnDashImportWell", btn_imp)

        self.ui._dashboard_quick_buttons = [
            btn_add, btn_imp,
            self._make_launch_button("Load Demo Data", self._load_demo_data, "#FF6B6B"),
            self._make_launch_button("Data Downloader", self._open_data_downloader, "#5E35B1"),
            self._make_launch_button("Log Viewer", lambda: self._call_controller_action("_go_to_logviewer_tab"), "#1FA67A"),
            self._make_launch_button("Crossplot", lambda: self._trigger_widget_click("btnDashXplot"), "#D48A1D"),
            self._make_launch_button("Shale Volume", lambda: self._trigger_widget_click("btnDashVsh"), "#A354D0"),
            self._make_launch_button("Water Saturation", lambda: self._trigger_widget_click("btnDashSw"), "#0F8B8D"),
            self._make_launch_button("Well Correlation", lambda: self._trigger_widget_click("btnDashCorr"), "#7C5CFF"),
        ]
        for i, b in enumerate(self.ui._dashboard_quick_buttons):
            r, c = divmod(i, 2)
            qg.addWidget(b, r, c)
        qa.layout().addLayout(qg)
        right.addWidget(qa, 2)

        # Recent Projects
        rp = self._make_section("Recent Projects")
        self.ui._dashboard_recent_buttons = [
            self._w("btnDashRecent1"), self._w("btnDashRecent2"), self._w("btnDashRecent3"),
        ]
        rl = QtWidgets.QVBoxLayout()
        rl.setSpacing(8)
        for b in self.ui._dashboard_recent_buttons:
            if b is None:
                continue
            b.setMinimumHeight(40)
            rl.addWidget(b)
        rp.layout().addLayout(rl)
        right.addWidget(rp, 1)

        # Activity
        act = self._make_section("Recent Activity")
        self.ui._dashboard_activity_list = QtWidgets.QListWidget(act)
        self.ui._dashboard_activity_list.setAlternatingRowColors(True)
        self.ui._dashboard_activity_list.setStyleSheet(
            "QListWidget { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; padding:6px; }"
            "QListWidget::item { padding:8px 6px; }"
        )
        act.layout().addWidget(self.ui._dashboard_activity_list)
        right.addWidget(act, 1)

        body.addLayout(left, 2)
        body.addLayout(right, 1)
        cl.addLayout(body)
        cl.addStretch(1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        tab.setStyleSheet(
            "QWidget#tabDashboard { background: #F3F7FC; }"
            "QFrame#dashCard { background: #FFFFFF; border: 1px solid #D7E2EE; border-radius: 14px; }"
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        ds = self._data_service()
        ps = self._project_service()

        pname = "No project"
        if ps is not None and getattr(ps, "current_project", None) is not None:
            pname = ps.current_project.name
        self._set_label("_dashboard_project_label", pname)

        well = None; df = None
        if ds is not None:
            well = ds._get_current_well()
            df = getattr(well, "data", None) if well is not None else None

        wname = getattr(well, "name", "-") if well is not None else "-"
        self._set_label("_dashboard_well_label", wname)

        wc = len(getattr(ds, "_wells", {})) if ds is not None else 0
        cc = len(df.columns) if df is not None else 0
        sc = len(df) if df is not None else 0
        dq = self._estimate_data_quality(df)

        self._set_metric("wells_loaded", str(wc))
        self._set_metric("curve_count", str(cc))
        self._set_metric("sample_count", f"{sc:,}")
        self._set_metric("data_quality", f"{dq:.0f}%")
        self._set_label("_dashboard_badge_one", "Ready")
        self._set_label("_dashboard_badge_two", f"Excellent ({dq:.0f}%)")
        self._set_label("_dashboard_missing_logs", self._estimate_missing_logs(df))
        self._set_label("_dashboard_interpretation", self._interpretation_readiness(dq))
        self._set_label("_dashboard_last_updated_label", QtCore.QDateTime.currentDateTime().toString("MMM d, yyyy hh:mm AP"))
        self._set_label("_dashboard_depth_label", self._format_depth_range(df))

        self._update_recent_projects()
        self._update_activity_list(pname, well, df)
        self._update_charts(df)

    def notify_refresh(self) -> None:
        try:
            self.refresh()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Widget factories
    # ------------------------------------------------------------------
    def _make_section(self, title: str) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame(self.ui)
        s.setObjectName("dashCard")
        s.setStyleSheet("QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }")
        ly = QtWidgets.QVBoxLayout(s)
        ly.setContentsMargins(16, 14, 16, 16); ly.setSpacing(10)
        lbl = QtWidgets.QLabel(title, s)
        lbl.setStyleSheet("font-size:13px;font-weight:600;color:#274B72;")
        ly.addWidget(lbl)
        return s

    def _make_metric_card(self, title: str, subtitle: str, accent: str) -> tuple:
        card = QtWidgets.QFrame(self.ui)
        card.setObjectName("dashCard")
        card.setStyleSheet("QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }")
        ly = QtWidgets.QVBoxLayout(card)
        ly.setContentsMargins(14, 10, 14, 10); ly.setSpacing(4)
        tl = QtWidgets.QLabel(title, card)
        tl.setStyleSheet("color:#2D4D74;font-size:10px;font-weight:700;")
        vl = QtWidgets.QLabel("0", card)
        vl.setStyleSheet(f"color:{accent};font-size:22px;font-weight:800;")
        sl = QtWidgets.QLabel(subtitle, card)
        sl.setStyleSheet("color:#5B7290;font-size:9px;font-weight:600;")
        ly.addWidget(tl)
        ly.addWidget(vl)
        ly.addWidget(sl)
        ly.addStretch(1)
        return card, vl

    def _make_hero_info_item(self, parent, title: str, value: str, value_color: str) -> QtWidgets.QFrame:
        box = QtWidgets.QFrame(parent)
        box.setStyleSheet("QFrame { border-right:1px solid rgba(160,198,235,0.2); }")
        ly = QtWidgets.QVBoxLayout(box)
        ly.setContentsMargins(10, 4, 10, 4)
        ly.setSpacing(2)
        t = QtWidgets.QLabel(title, box)
        t.setStyleSheet("color:#9CB9DD;font-size:9px;font-weight:700;")
        v = QtWidgets.QLabel(value, box)
        v.setStyleSheet(f"color:{value_color};font-size:9px;font-weight:700;")
        v.setWordWrap(True)
        ly.addWidget(t)
        ly.addWidget(v)
        box._label = v  # type: ignore[attr-defined]
        return box

    def _make_status_item(self, title: str, value: str, accent: str) -> QtWidgets.QFrame:
        badge = QtWidgets.QFrame(self.ui)
        badge.setStyleSheet(
            "QFrame {"
            "background:rgba(4,29,63,0.68);"
            "border:1px solid rgba(116,171,228,0.18);"
            "border-radius:12px;"
            "}"
        )
        ly = QtWidgets.QVBoxLayout(badge)
        ly.setContentsMargins(9, 7, 9, 7)
        ly.setSpacing(2)
        tl = QtWidgets.QLabel(title, badge)
        tl.setStyleSheet("color:#ADC5E2;font-size:8px;font-weight:700;")
        vl = QtWidgets.QLabel(value, badge)
        vl.setStyleSheet(f"color:{accent};font-size:11px;font-weight:800;")
        ly.addWidget(tl)
        ly.addWidget(vl)
        badge._label = vl  # type: ignore[attr-defined]
        return badge

    def _make_launch_button(self, text: str, handler, accent: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text, self.ui)
        btn.setMinimumHeight(44)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn.setStyleSheet(
            "QPushButton {"
            f"background:{accent};"
            "color:#FFFFFF;border:none;border-radius:12px;"
            "padding:10px 12px;font-size:12px;font-weight:700;text-align:left;"
            "}"
            "QPushButton:hover { background: #23588F; }"
        )
        btn.clicked.connect(handler)
        return btn

    def _make_chart_card(self, title: str, tall: bool = False) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame(self.ui)
        card.setObjectName("dashCard")
        card.setStyleSheet("QFrame#dashCard { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:14px; }")
        if tall:
            card.setMinimumHeight(280)
        ly = QtWidgets.QVBoxLayout(card)
        ly.setContentsMargins(12, 12, 12, 12); ly.setSpacing(8)
        tl = QtWidgets.QLabel(title, card)
        tl.setStyleSheet("font-size:13px;font-weight:700;color:#274B72;")
        ly.addWidget(tl)
        host = QtWidgets.QFrame(card)
        host.setStyleSheet("background:#F8FBFE;border:1px dashed #D4DFEA;border-radius:10px;")
        hl = QtWidgets.QVBoxLayout(host)
        hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(0)
        ly.addWidget(host, 1)
        card._canvas_host = host  # type: ignore[attr-defined]
        card._title_label = tl   # type: ignore[attr-defined]
        return card

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _add_new_well(self) -> None:
        ds = self._data_service()
        if ds is not None and callable(getattr(ds, "import_data", None)):
            imported = ds.import_data()
            if imported:
                ps = self._project_service()
                if ps is not None and callable(getattr(ps, "mark_modified", None)):
                    ps.mark_modified()
        else:
            QtCore.QTimer.singleShot(200, self._add_new_well)

    def _load_demo_data(self) -> None:
        ds = self._data_service()
        if ds is None:
            return
        demo = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/data/_Gorgonichthys_1_suite3_supercombo_log_Gorgonichthys1_suite2_CMR.las"
        import os
        if not os.path.exists(demo):
            QtWidgets.QMessageBox.warning(self.ui, "Demo Data", f"Demo data file not found:\n{demo}")
            return
        from core.well_data_loader import load_well
        try:
            well, msg = load_well(demo, replace_nulls=True, depth_unit="m", depth_type="MD")
            ds._register_well(well)
            ds._update_well_lists()
            ds._refresh_views()
            QtWidgets.QMessageBox.information(self.ui, "Demo Data", f"Demo data loaded successfully.\n{msg}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.ui, "Demo Data", f"Failed to load demo data:\n{e}")

    def _open_data_downloader(self) -> None:
        opener = getattr(self.ui, "_open_data_downloader", None)
        if callable(opener):
            opener()

    def _trigger_widget_click(self, name: str) -> None:
        w = self._w(name)
        if w is not None and hasattr(w, "click"):
            w.click()

    def _call_controller_action(self, name: str) -> None:
        ctrl = getattr(self.ui, "controller", None)
        if ctrl is None:
            return
        h = getattr(ctrl, name, None)
        if callable(h):
            h()

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------
    def _set_metric(self, key: str, text: str) -> None:
        metrics = getattr(self.ui, "_dashboard_metrics", {})
        w = metrics.get(key)
        if w is not None and hasattr(w, "setText"):
            w.setText(text)

    def _set_label(self, attr: str, text: str) -> None:
        w = getattr(self.ui, attr, None)
        if w is None:
            return
        if hasattr(w, "setText"):
            w.setText(text)
        elif hasattr(w, "_label") and hasattr(w._label, "setText"):
            w._label.setText(text)

    def _update_recent_projects(self) -> None:
        from core.project_manager import get_recent_projects
        recent = get_recent_projects(3)
        labels = [Path(p).stem for p in recent]
        for i, btn in enumerate(getattr(self.ui, "_dashboard_recent_buttons", [])):
            if btn is None:
                continue
            if i < len(labels):
                btn.setText(labels[i]); btn.setToolTip(recent[i]); btn.setEnabled(True)
            else:
                btn.setText("No recent project"); btn.setToolTip(""); btn.setEnabled(False)

    def _update_activity_list(self, project_name: str, well, df) -> None:
        al = getattr(self.ui, "_dashboard_activity_list", None)
        if al is None:
            return
        al.clear()
        items: list[str] = [f"Project: {project_name}"]
        if well is not None and df is not None:
            dc = None
            for n in df.columns:
                if str(n).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                    dc = n; break
            if dc is not None:
                import pandas as pd
                dv = pd.to_numeric(df[dc], errors="coerce").dropna()
                if not dv.empty:
                    items.append(f"Depth range: {dv.min():.1f} to {dv.max():.1f} m")
            items.append(f"Loaded curves: {len(df.columns)}")
            items.append(f"Samples: {len(df):,}")
            items.append("Dashboard refreshed from the active well.")
        else:
            items.append("Import a LAS or CSV file to activate the charts.")
        for t in items:
            al.addItem(t)

    def _estimate_data_quality(self, df) -> float:
        if df is None or getattr(df, "empty", True):
            return 0.0
        import pandas as pd
        nc = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not nc:
            return 0.0
        nv = [float(df[c].isna().mean() * 100) for c in nc]
        return max(0.0, min(100.0, 100.0 - sum(nv) / len(nv)))

    def _format_depth_range(self, df) -> str:
        if df is None or getattr(df, "empty", True):
            return "-"
        import pandas as pd
        for col in df.columns:
            if str(col).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                if vals.empty:
                    return "-"
                return f"{vals.min():,.2f} - {vals.max():,.2f} m"
        return "-"

    def _estimate_missing_logs(self, df) -> str:
        if df is None or getattr(df, "empty", True):
            return "0 Logs"
        target = ("GR", "RHOB", "NPHI", "DT", "RT", "PEF")
        present = {str(c).strip().upper() for c in df.columns}
        missing = [name for name in target if name not in present]
        return f"{len(missing)} Logs"

    def _interpretation_readiness(self, quality: float) -> str:
        if quality >= 85:
            return "Good to interpret"
        if quality >= 65:
            return "Fair for interpretation"
        if quality > 0:
            return "Needs cleanup"
        return "Waiting for data"

    # ------------------------------------------------------------------
    # Chart rendering
    # ------------------------------------------------------------------
    def _update_charts(self, df) -> None:
        if df is None or getattr(df, "empty", True):
            self._render_message(self.ui._dashboard_hist_frame, "No data loaded yet.")
            self._render_message(self.ui._dashboard_radar_frame, "No data loaded yet.")
            return
        import pandas as pd
        nc = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not nc:
            self._render_message(self.ui._dashboard_hist_frame, "No numeric curves found.")
            self._render_message(self.ui._dashboard_radar_frame, "No numeric curves found. ")
            return
        gr = None
        for cand in ("GR", "CGR", "GAPI", "API"):
            if cand in df.columns and pd.api.types.is_numeric_dtype(df[cand]):
                gr = cand; break
        if gr is None:
            gr = nc[0]
        self._render_histogram(self.ui._dashboard_hist_frame, df[gr], gr)
        self._render_radar(self.ui._dashboard_radar_frame, df)

    def _render_message(self, frame: QtWidgets.QFrame, msg: str) -> None:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
        ax.axis("off")
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=11, color="#5C718A", wrap=True)
        self._render_figure(frame, fig)

    def _render_histogram(self, frame: QtWidgets.QFrame, series, curve: str) -> None:
        import matplotlib.pyplot as plt
        import pandas as pd
        num = pd.to_numeric(series, errors="coerce").dropna()
        if num.empty:
            self._render_message(frame, f"No valid samples found for {curve}.")
            return
        fig, ax = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
        ax.hist(num, bins=24, color="#74B86A", edgecolor="white", alpha=0.92)
        ax.set_title(f"{curve} Distribution", fontsize=12, fontweight="600")
        ax.set_xlabel(curve); ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.16)
        self._render_figure(frame, fig)

    def _render_radar(self, frame: QtWidgets.QFrame, df) -> None:
        if df is None or getattr(df, "empty", True):
            self._render_message(frame, "No data loaded yet.")
            return
        from plotting.log_availability_radar import build_log_availability_radar_figure
        fig = build_log_availability_radar_figure(df)
        self._render_figure(frame, fig)

    def _render_figure(self, frame: QtWidgets.QFrame, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
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
            w = item.widget()
            if w is not None:
                w.setParent(None); w.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, host)
        toolbar.setStyleSheet("QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }")
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        install_plot_context_menu(canvas, fig, host)

        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def _clear_layout(layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            cl = item.layout()
            if w is not None:
                w.setParent(None); w.deleteLater()
            elif cl is not None:
                DashboardPanel._clear_layout(cl)
