"""
ml_qc_panel.py
==============
Programmatic layout builder for the ML Based QC sub-tab.

tabMLQC is now a sub-tab of tabQCInner, which lives inside tabQualitycontrol
(the unified "Quality Control" top-level tab).  Tab hierarchy:
    centralTabWidget → tabQualitycontrol → tabQCInner → tabMLQC  (this tab)
                                                      → tabQCStat (Statistical QC)

Called from MLQCService.__init__() immediately after widget discovery.
Rebuilds the tabMLQC content with:
  ┌─────────────────────────────────────────────────────────────────┐
  │  ROW 1: Well | Curve | Model | Contamination%                  │
  │  ROW 2: From | To | Multi-Curve  ──────── [▶ Run] [Reset]     │
  ├───────────┬──────────────────────────────┬─────────────────────┤
  │ SIDEBAR   │  LOG VIEW (dominant)         │  DETECTED ANOMALIES │
  │ Modules   │              ┌───────────────│  table (full ht)    │
  │ Summary   │              │ Score Scatter │  status label       │
  │ Cards     │              │ Feature Bar   │  [Export][Report]   │
  └───────────┴──────────────┴───────────────┴─────────────────────┘
"""
from __future__ import annotations
from PyQt5 import QtWidgets, QtCore, QtGui


# ── colour palette ────────────────────────────────────────────────────────────
_CARD_BG     = "#FFFFFF"
_CARD_BORDER = "1px solid #D8E2EC"
_CARD_RADIUS = "border-radius:8px"
_FRAME_STYLE = "background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;"
_SIDE_STYLE  = "background:#F4F7FB;border:1px solid #C9D7E6;border-radius:8px;"
_RUN_STYLE   = ("background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #27AE60,stop:1 #1E8449);"
                "color:white;border:1px solid #196F3D;"
                "border-radius:5px;padding:5px 18px;font-weight:700;font-size:12px;")
_RST_STYLE   = ("background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #5DADE2,stop:1 #2E86C1);"
                "color:white;border:1px solid #1A5276;"
                "border-radius:5px;padding:5px 12px;font-weight:600;")
_EXP_STYLE   = ("background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #4A82C4,stop:1 #2A5C9E);"
                "color:white;border:1px solid #1D4A85;"
                "border-radius:4px;padding:5px 14px;font-weight:600;")


def _lbl(text: str, style: str = "", word_wrap: bool = False) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    if style:
        w.setStyleSheet(style)
    if word_wrap:
        w.setWordWrap(True)
    return w


def _hdr(text: str) -> QtWidgets.QLabel:
    return _lbl(text, "font-weight:700;font-size:10px;color:#2A5090;letter-spacing:1px;")


def _card_pair(title: str, obj_name: str, color: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
    """Small summary card (title + big number)."""
    card = QtWidgets.QFrame()
    card.setStyleSheet(f"{_CARD_BG};{_CARD_BORDER};{_CARD_RADIUS};")
    card.setFrameShape(QtWidgets.QFrame.StyledPanel)
    vb = QtWidgets.QVBoxLayout(card)
    vb.setContentsMargins(6, 4, 6, 4)
    vb.setSpacing(1)
    t = _lbl(title, "color:#61788F;font-size:9px;font-weight:600;")
    t.setAlignment(QtCore.Qt.AlignCenter)
    vb.addWidget(t)
    val = _lbl("—", f"font-size:15px;font-weight:700;color:{color};")
    val.setObjectName(obj_name)
    val.setAlignment(QtCore.Qt.AlignCenter)
    vb.addWidget(val)
    return card, val


def _placeholder(text: str, min_h: int = 120) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        "color:#7B8FA6;font-size:11px;"
        "border:1px dashed #C8D7E8;border-radius:6px;background:#F8FBFE;"
    )
    w.setAlignment(QtCore.Qt.AlignCenter)
    w.setWordWrap(True)
    w.setMinimumHeight(min_h)
    return w


def _plot_frame(title: str, ph_text: str, ph_name: str, min_h: int = 120) -> QtWidgets.QFrame:
    frame = QtWidgets.QFrame()
    frame.setStyleSheet(_FRAME_STYLE)
    frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
    sp = frame.sizePolicy()
    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
    frame.setSizePolicy(sp)
    vb = QtWidgets.QVBoxLayout(frame)
    vb.setContentsMargins(8, 8, 8, 8)
    vb.setSpacing(4)
    vb.addWidget(_lbl(title, "font-weight:700;color:#2A4E77;font-size:11px;"))
    ph = _placeholder(ph_text, min_h)
    ph.setObjectName(ph_name)
    vb.addWidget(ph, 1)
    return frame


class MLQCPanel:
    """Rebuilds the tabMLQC layout in pure Python for precise control."""

    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        tab = getattr(ui, "tabMLQC", None)
        if tab is None:
            return
        self._tab = tab
        self._rebuild(tab)
        self._register_named_widgets(tab)

    # ── widget registration ───────────────────────────────────────────────────
    def _reg(self, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Register widget on self.ui by its objectName; return widget."""
        name = widget.objectName()
        if name:
            setattr(self.ui, name, widget)
        return widget

    def _register_named_widgets(self, root: QtWidgets.QWidget) -> None:
        """Walk the rebuilt widget tree and register every named widget on ui."""
        for child in root.findChildren(QtWidgets.QWidget):
            name = child.objectName()
            if name and not name.startswith("qt_"):
                setattr(self.ui, name, child)

    # ─────────────────────────────────────────────────────────────────────────
    def _rebuild(self, tab: QtWidgets.QWidget) -> None:
        # Wipe existing layout
        old = tab.layout()
        if old is not None:
            while old.count():
                item = old.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
            QtWidgets.QWidget().setLayout(old)

        root = QtWidgets.QVBoxLayout(tab)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── TOP CONTROLS BAR ─────────────────────────────────────────────────
        top = self._build_top_bar()
        root.addWidget(top)

        # ── BODY ─────────────────────────────────────────────────────────────
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(8)

        body.addWidget(self._build_sidebar(), 0)           # fixed width
        body.addLayout(self._build_center(), 3)            # dominant
        body.addWidget(self._build_right_panel(), 1)       # table panel

        root.addLayout(body, 1)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_top_bar(self) -> QtWidgets.QFrame:
        bar = QtWidgets.QFrame()
        bar.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:8px;")
        bar.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bar.setMaximumHeight(90)

        grid = QtWidgets.QGridLayout(bar)
        grid.setContentsMargins(12, 8, 12, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        def lbl(t): return _lbl(t, "font-weight:600;color:#2A4E77;font-size:11px;")

        # Row 0 ──────────────────────────────────────────────────────────────
        grid.addWidget(lbl("Well:"), 0, 0)
        well_cb = QtWidgets.QComboBox(); well_cb.setObjectName("comboMLQCWell")
        well_cb.setMinimumWidth(140)
        grid.addWidget(well_cb, 0, 1)

        grid.addWidget(lbl("Curve:"), 0, 2)
        curve_cb = QtWidgets.QComboBox(); curve_cb.setObjectName("comboMLQCCurve")
        curve_cb.setMinimumWidth(110)
        grid.addWidget(curve_cb, 0, 3)

        grid.addWidget(lbl("Model:"), 0, 4)
        model_cb = QtWidgets.QComboBox(); model_cb.setObjectName("comboMLQCModel")
        model_cb.setMinimumWidth(155)
        for m in ["Isolation Forest", "LOF", "One-Class SVM", "DBSCAN"]:
            model_cb.addItem(m)
        grid.addWidget(model_cb, 0, 5)

        grid.addWidget(lbl("Contamination:"), 0, 6)
        cont_sp = QtWidgets.QSpinBox(); cont_sp.setObjectName("spinMLQCContamination")
        cont_sp.setRange(1, 40); cont_sp.setValue(5); cont_sp.setSuffix("%")
        cont_sp.setMinimumWidth(75)
        grid.addWidget(cont_sp, 0, 7)

        spc0 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        grid.addItem(spc0, 0, 8)

        # Row 1 ──────────────────────────────────────────────────────────────
        grid.addWidget(lbl("Depth From:"), 1, 0)
        from_sp = QtWidgets.QDoubleSpinBox(); from_sp.setObjectName("spinMLQCDepthFrom")
        from_sp.setMaximum(100000); from_sp.setDecimals(1); from_sp.setMinimumWidth(90)
        grid.addWidget(from_sp, 1, 1)

        grid.addWidget(lbl("To:"), 1, 2)
        to_sp = QtWidgets.QDoubleSpinBox(); to_sp.setObjectName("spinMLQCDepthTo")
        to_sp.setMaximum(100000); to_sp.setDecimals(1); to_sp.setMinimumWidth(90)
        grid.addWidget(to_sp, 1, 3)

        mc = QtWidgets.QCheckBox("Multi-Curve Features")
        mc.setObjectName("checkMLQCMultiCurve"); mc.setChecked(True)
        grid.addWidget(mc, 1, 4, 1, 2)

        spc1 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        grid.addItem(spc1, 1, 6)

        run_btn = QtWidgets.QPushButton("▶  Run ML QC")
        run_btn.setObjectName("btnRunMLQC")
        run_btn.setStyleSheet(_RUN_STYLE)
        run_btn.setMinimumHeight(32)
        grid.addWidget(run_btn, 1, 7)

        rst_btn = QtWidgets.QPushButton("Reset")
        rst_btn.setObjectName("btnResetMLQC")
        rst_btn.setStyleSheet(_RST_STYLE)
        grid.addWidget(rst_btn, 1, 8)

        return bar

    # ─────────────────────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QtWidgets.QFrame:
        side = QtWidgets.QFrame()
        side.setFixedWidth(215)
        side.setStyleSheet(_SIDE_STYLE)
        side.setFrameShape(QtWidgets.QFrame.StyledPanel)

        vb = QtWidgets.QVBoxLayout(side)
        vb.setContentsMargins(10, 10, 10, 10)
        vb.setSpacing(8)

        # ML Modules
        vb.addWidget(_hdr("ML QC MODULES"))
        steps_frame = QtWidgets.QFrame()
        steps_frame.setStyleSheet("background:#FFFFFF;border:1px solid #D7E2EE;border-radius:6px;")
        svb = QtWidgets.QVBoxLayout(steps_frame)
        svb.setContentsMargins(8, 8, 8, 8); svb.setSpacing(3)
        for i, txt in enumerate(["① Data Preparation", "② Feature Engineering",
                                   "③ Model Training", "④ Anomaly Detection"]):
            bg = "background:#EBF5FB;border-radius:4px;" if i == 0 else ""
            svb.addWidget(_lbl(txt, f"color:#2A5090;font-size:11px;padding:3px 6px;{bg}"))
        vb.addWidget(steps_frame)

        # QC Summary
        vb.addWidget(_hdr("QC SUMMARY"))

        # Big score card
        score_card = QtWidgets.QFrame()
        score_card.setStyleSheet(f"background:{_CARD_BG};{_CARD_BORDER};{_CARD_RADIUS};")
        score_card.setFrameShape(QtWidgets.QFrame.StyledPanel)
        sc_vb = QtWidgets.QVBoxLayout(score_card)
        sc_vb.setContentsMargins(6, 6, 6, 6); sc_vb.setSpacing(2)
        st = _lbl("QC SCORE", "color:#61788F;font-size:9px;font-weight:600;letter-spacing:1px;")
        st.setAlignment(QtCore.Qt.AlignCenter); sc_vb.addWidget(st)
        sv = _lbl("—", "font-size:24px;font-weight:700;color:#27AE60;")
        sv.setObjectName("lblMLQCScore"); sv.setAlignment(QtCore.Qt.AlignCenter)
        sc_vb.addWidget(sv)
        vb.addWidget(score_card)

        # 2x2 mini cards
        grid = QtWidgets.QGridLayout(); grid.setSpacing(5)
        pairs = [
            ("Anomalies", "lblMLQCAnomalyCount", "#E55353", 0, 0),
            ("Good %",    "lblMLQCGoodPct",      "#27AE60", 0, 1),
            ("Missing",   "lblMLQCMissingPct",   "#F59E0B", 1, 0),
            ("Reliability","lblMLQCReliability", "#2A6FD4", 1, 1),
        ]
        for title, name, color, r, c in pairs:
            card, _ = _card_pair(title, name, color)
            grid.addWidget(card, r, c)
        vb.addLayout(grid)

        # Active model label
        vb.addWidget(_lbl("Active Model", "color:#61788F;font-size:9px;font-weight:600;"))
        am = _lbl("—", "font-size:11px;font-weight:700;color:#2A5090;"
                       "padding:3px 6px;background:#EBF5FB;border-radius:4px;", word_wrap=True)
        am.setObjectName("lblMLQCModel")
        vb.addWidget(am)

        vb.addStretch(1)
        return side

    # ─────────────────────────────────────────────────────────────────────────
    def _build_center(self) -> QtWidgets.QHBoxLayout:
        """Horizontal split: log view (dominant left) | scatter+feature (right column)."""
        hb = QtWidgets.QHBoxLayout(); hb.setSpacing(8)

        # ── Log View (tallest, most important) ────────────────────────────────
        log_frame = _plot_frame(
            "Anomaly Log View",
            "Run ML QC to view anomaly-flagged depth track.\n"
            "Anomalies are colour-coded by severity score.",
            "lblMLQCLogPlaceholder",
            min_h=400,
        )
        log_frame.setObjectName("frameMLQCLogView")
        log_frame.setMinimumWidth(300)
        hb.addWidget(log_frame, 3)      # ← 3x wider than right column

        # ── Right column: scatter + feature bar ───────────────────────────────
        right_col = QtWidgets.QVBoxLayout(); right_col.setSpacing(8)

        sc_frame = _plot_frame(
            "Anomaly Score vs Depth",
            "Score distribution will appear here after running ML QC.",
            "lblMLQCScatterPlaceholder",
            min_h=160,
        )
        sc_frame.setObjectName("frameMLQCScatter")
        right_col.addWidget(sc_frame, 1)

        feat_frame = _plot_frame(
            "Feature Contributions",
            "Feature importance chart will appear here.",
            "lblMLQCFeaturePlaceholder",
            min_h=130,
        )
        feat_frame.setObjectName("frameMLQCFeatureBar")
        right_col.addWidget(feat_frame, 1)

        hb.addLayout(right_col, 2)      # ← 2x for right column
        return hb

    # ─────────────────────────────────────────────────────────────────────────
    def _build_right_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setMinimumWidth(290)
        panel.setMaximumWidth(380)
        panel.setStyleSheet(_SIDE_STYLE)
        panel.setFrameShape(QtWidgets.QFrame.StyledPanel)

        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(10, 10, 10, 10)
        vb.setSpacing(6)

        vb.addWidget(_hdr("DETECTED ANOMALIES"))

        # Table
        tbl = QtWidgets.QTableWidget()
        tbl.setObjectName("tableMLQCIssues")
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Depth", "Curve", "Value", "Score", "Severity"])
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        tbl.setColumnWidth(0, 65)   # Depth
        tbl.setColumnWidth(1, 50)   # Curve
        tbl.setColumnWidth(2, 60)   # Value
        tbl.setColumnWidth(3, 55)   # Score
        sp = tbl.sizePolicy()
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        tbl.setSizePolicy(sp)
        vb.addWidget(tbl, 1)

        # Status
        status = _lbl(
            "Ready — load a well and click ▶ Run ML QC",
            "color:#61788F;font-size:10px;font-style:italic;",
            word_wrap=True,
        )
        status.setObjectName("lblMLQCStatus")
        vb.addWidget(status)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout(); btn_row.setSpacing(8)
        exp = QtWidgets.QPushButton("Export CSV")
        exp.setObjectName("btnExportMLQC")
        exp.setStyleSheet(_EXP_STYLE)
        btn_row.addWidget(exp)
        rpt = QtWidgets.QPushButton("Generate Report")
        rpt.setObjectName("btnMLQCReport")
        btn_row.addWidget(rpt)
        vb.addLayout(btn_row)

        return panel
