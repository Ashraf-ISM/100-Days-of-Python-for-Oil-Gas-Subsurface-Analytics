# pyrefly: ignore [missing-import]
from PyQt5 import QtWidgets, QtGui, QtCore


def build_dashboard(self) -> None:
    """Build full PetroARX dashboard UI (compatible with main logic)."""

    tab = getattr(self, "tabDashboard", None)
    if tab is None:
        print("❌ tabDashboard not found")
        return

    # Layout
    layout = tab.layout()
    if layout is None:
        layout = QtWidgets.QVBoxLayout(tab)

    # Clear existing
    if hasattr(self, "_clear_layout"):
        self._clear_layout(layout)

    # ===== Scroll Area =====
    scroll_area = QtWidgets.QScrollArea(tab)
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

    content = QtWidgets.QWidget()
    content_layout = QtWidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(15, 15, 15, 15)
    content_layout.setSpacing(12)

    # ================= HERO =================
    hero = QtWidgets.QFrame()
    hero.setStyleSheet(
        "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1C4A7C, stop:1 #3F7CB6);"
        "border-radius:16px;"
    )

    hero_layout = QtWidgets.QVBoxLayout(hero)

    title = QtWidgets.QLabel("PetroARX Dashboard")
    title.setStyleSheet("color:white;font-size:22px;font-weight:800;")

    subtitle = QtWidgets.QLabel(
        "Overview of wells, logs and interpretation workflow"
    )
    subtitle.setStyleSheet("color:white;font-size:12px;")

    # IMPORTANT: labels used in refresh_dashboard_tab()
    self._dashboard_project_label = QtWidgets.QLabel("Project: -")
    self._dashboard_project_label.setStyleSheet("color:#DCEBFA;font-size:12px;")

    self._dashboard_well_label = QtWidgets.QLabel("Active well: -")
    self._dashboard_well_label.setStyleSheet("color:#DCEBFA;font-size:12px;")

    hero_layout.addWidget(title)
    hero_layout.addWidget(subtitle)
    hero_layout.addWidget(self._dashboard_project_label)
    hero_layout.addWidget(self._dashboard_well_label)

    content_layout.addWidget(hero)

    # ================= METRICS =================
    metrics_layout = QtWidgets.QHBoxLayout()
    self._dashboard_metrics = {}

    def make_metric(title, key):
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "background:white;border:1px solid #D7E2EE;border-radius:10px;"
        )
        l = QtWidgets.QVBoxLayout(card)

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("font-size:11px;color:#5C718A;")

        value = QtWidgets.QLabel("0")
        value.setStyleSheet("font-size:18px;font-weight:800;")

        l.addWidget(label)
        l.addWidget(value)

        self._dashboard_metrics[key] = value
        return card

    metrics_layout.addWidget(make_metric("Wells Loaded", "wells_loaded"))
    metrics_layout.addWidget(make_metric("Curves", "curve_count"))
    metrics_layout.addWidget(make_metric("Samples", "sample_count"))
    metrics_layout.addWidget(make_metric("Data Quality", "data_quality"))

    content_layout.addLayout(metrics_layout)

    # ================= CHARTS (CRITICAL FIX) =================
    chart_layout = QtWidgets.QHBoxLayout()

    self._dashboard_hist_frame = QtWidgets.QFrame()
    self._dashboard_hist_frame.setStyleSheet(
        "background:white;border:1px solid #D7E2EE;border-radius:10px;"
    )

    self._dashboard_lith_frame = QtWidgets.QFrame()
    self._dashboard_lith_frame.setStyleSheet(
        "background:white;border:1px solid #D7E2EE;border-radius:10px;"
    )

    chart_layout.addWidget(self._dashboard_hist_frame)
    chart_layout.addWidget(self._dashboard_lith_frame)

    content_layout.addLayout(chart_layout)

    # ================= QUICK ACTIONS =================
    actions_layout = QtWidgets.QGridLayout()

    def make_button(text, handler=None):
        btn = QtWidgets.QPushButton(text)
        btn.setMinimumHeight(40)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        if handler:
            btn.clicked.connect(handler)
        return btn

    actions_layout.addWidget(make_button("Import LAS"), 0, 0)
    actions_layout.addWidget(make_button("Log Viewer"), 0, 1)
    actions_layout.addWidget(make_button("Crossplot"), 1, 0)
    actions_layout.addWidget(make_button("Shale Volume"), 1, 1)

    content_layout.addLayout(actions_layout)

    # ================= RECENT PROJECTS =================
    self._dashboard_recent_buttons = [
        QtWidgets.QPushButton("Recent 1"),
        QtWidgets.QPushButton("Recent 2"),
        QtWidgets.QPushButton("Recent 3"),
    ]

    recent_layout = QtWidgets.QVBoxLayout()
    for btn in self._dashboard_recent_buttons:
        btn.setMinimumHeight(35)
        recent_layout.addWidget(btn)

    content_layout.addLayout(recent_layout)

    # ================= ACTIVITY =================
    self._dashboard_activity_list = QtWidgets.QListWidget()
    content_layout.addWidget(self._dashboard_activity_list)

    # ===== FINAL =====
    scroll_area.setWidget(content)
    layout.addWidget(scroll_area)

    print("✅ Dashboard loaded successfully")