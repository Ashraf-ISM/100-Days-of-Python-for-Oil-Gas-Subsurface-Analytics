"""
PetroARX – About / Help dialog
Advanced redesign: sidebar navigation, QPainter header, drop-shadow cards,
QPropertyAnimation fade transitions, hover-state event filters, keyboard
shortcut reference, and technology stack page.
"""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt5.QtGui import (QColor, QFont, QLinearGradient, QPainter,
                         QPen)

# ─────────────────────────────────────────────────────────────────────────────
#  Design tokens
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "navy_deep":   "#08131F",
    "navy":        "#0D1F35",
    "navy_mid":    "#162C45",
    "navy_light":  "#1E3D5C",
    "accent":      "#27AE74",
    "accent_dim":  "#1E8A5C",
    "accent_glow": "#3ECFA0",
    "bg":          "#F2F5F9",
    "bg_card":     "#FFFFFF",
    "border":      "#DDE3EE",
    "text_h":      "#0D1F35",
    "text_body":   "#3A4B5E",
    "text_muted":  "#7A8A9C",
    "sidebar_bg":  "#0F1E30",
    "sidebar_sel": "#162C45",
    "sidebar_ind": "#27AE74",
}

FONT_DISPLAY = "Segoe UI Semibold"
FONT_BODY    = "Segoe UI"


# ─────────────────────────────────────────────────────────────────────────────
#  Tiny helpers
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, weight: QFont.Weight = QFont.Normal,
          family: str = FONT_BODY) -> QFont:
    f = QFont(family, size)
    f.setWeight(weight)
    return f


def _shadow(blur: int = 18, dy: int = 4,
            alpha: int = 30) -> QtWidgets.QGraphicsDropShadowEffect:
    s = QtWidgets.QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, dy)
    s.setColor(QColor(0, 0, 0, alpha))
    return s


def _h_sep() -> QtWidgets.QFrame:
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{C['border']}; border:none;")
    return f


def _lbl(text: str, size: int = 10, color: str = C["text_body"],
         bold: bool = False, wrap: bool = False,
         family: str = FONT_BODY) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setFont(_font(size, QFont.DemiBold if bold else QFont.Normal, family))
    w.setStyleSheet(f"color:{color}; background:transparent;")
    w.setWordWrap(wrap)
    return w


def _caps(text: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text.upper())
    lbl.setStyleSheet(f"""
        font-size: 7pt;
        font-weight: 700;
        letter-spacing: 2px;
        color: {C['text_muted']};
        background: transparent;
    """)
    return lbl


def _scrollable(inner: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
    sa = QtWidgets.QScrollArea()
    sa.setWidget(inner)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QtWidgets.QFrame.NoFrame)
    sa.setStyleSheet("""
        QScrollArea { background: transparent; border: none; }
        QScrollBar:vertical {
            width: 5px; background: transparent; border-radius: 3px;
        }
        QScrollBar::handle:vertical {
            background: #C8D0DC; border-radius: 3px; min-height: 24px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """)
    return sa


# ─────────────────────────────────────────────────────────────────────────────
#  Custom painted header
# ─────────────────────────────────────────────────────────────────────────────

class _HeaderBanner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, _event):                          # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.00, QColor(C["navy_deep"]))
        g.setColorAt(0.55, QColor(C["navy_mid"]))
        g.setColorAt(1.00, QColor(C["navy_light"]))
        p.fillRect(self.rect(), g)

        # Decorative concentric arcs, bottom-right corner
        p.setOpacity(0.09)
        pen_arc = QPen(QColor("#FFFFFF"), 1.2)
        p.setPen(pen_arc)
        cx, cy = self.width() + 10, self.height() + 20
        for r in (80, 130, 180, 230, 280):
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Subtle dot grid, left region
        p.setOpacity(0.05)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        for row in range(4, self.height() - 4, 12):
            for col in range(10, 230, 16):
                p.drawEllipse(col, row, 2, 2)

        # Accent bar at the very bottom
        p.setOpacity(1.0)
        bar_g = QLinearGradient(0, 0, self.width(), 0)
        bar_g.setColorAt(0.0, QColor(C["accent"]))
        bar_g.setColorAt(0.5, QColor(C["accent_glow"]))
        bar_g.setColorAt(1.0, QColor(C["accent"]))
        p.fillRect(0, self.height() - 3, self.width(), 3, bar_g)
        p.end()

    def populate(self):
        lo = QtWidgets.QHBoxLayout(self)
        lo.setContentsMargins(28, 14, 28, 18)
        lo.setSpacing(20)

        left = QtWidgets.QVBoxLayout()
        left.setSpacing(4)

        name = QtWidgets.QLabel("PetroARX")
        name.setFont(QFont(FONT_DISPLAY, 22))
        name.setStyleSheet(
            "color:#FFFFFF; letter-spacing:-0.5px; background:transparent;")

        tag = QtWidgets.QLabel("Petrophysics Interpretation Platform")
        tag.setStyleSheet(
            "color:rgba(255,255,255,0.55); font-size:9pt; background:transparent;")

        pill = QtWidgets.QLabel("  v 1.0  ")
        pill.setStyleSheet(f"""
            color: {C['accent_glow']};
            background: rgba(39,174,116,0.15);
            border: 1px solid {C['accent_glow']};
            border-radius: 9px;
            font-size: 8pt; font-weight: 600;
            padding: 1px 6px;
        """)
        pill.setFixedHeight(20)
        pill.setAlignment(Qt.AlignCenter)

        tag_row = QtWidgets.QHBoxLayout()
        tag_row.setSpacing(10)
        tag_row.addWidget(tag)
        tag_row.addWidget(pill)
        tag_row.addStretch()

        left.addStretch()
        left.addWidget(name)
        left.addLayout(tag_row)
        left.addStretch()
        lo.addLayout(left, 1)

        right = QtWidgets.QHBoxLayout()
        right.setSpacing(8)
        for icon, value, label in (
            ("📊", "10+",   "Modules"),
            ("🔩", "LAS 2/3", "Format"),
            ("🌐", "Multi", "Well"),
        ):
            right.addWidget(self._stat_badge(icon, value, label))
        lo.addLayout(right)

    @staticmethod
    def _stat_badge(icon: str, value: str, label: str) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedSize(70, 70)
        w.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
            }
        """)
        lo = QtWidgets.QVBoxLayout(w)
        lo.setContentsMargins(4, 6, 4, 6)
        lo.setSpacing(1)
        for txt, size, color in (
            (icon,  13, "#FFFFFF"),
            (value,  9, C["accent_glow"]),
            (label,  7, "rgba(255,255,255,0.45)"),
        ):
            lbl = QtWidgets.QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"font-size:{size}pt; color:{color}; background:transparent;")
            lo.addWidget(lbl)
        return w


# ─────────────────────────────────────────────────────────────────────────────
#  Hover card
# ─────────────────────────────────────────────────────────────────────────────

class _HoverCard(QtWidgets.QWidget):
    def __init__(self, icon: str, title: str, body: str, parent=None):
        super().__init__(parent)
        self._shadow_fx = _shadow(10, 2, 16)
        self.setGraphicsEffect(self._shadow_fx)
        self._apply_style(False)

        lo = QtWidgets.QHBoxLayout(self)
        lo.setContentsMargins(14, 11, 14, 11)
        lo.setSpacing(14)

        ic = QtWidgets.QLabel(icon)
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"""
            font-size: 16pt;
            background: {C['bg']};
            border: 1px solid {C['border']};
            border-radius: 10px;
        """)
        lo.addWidget(ic, 0, Qt.AlignTop)

        col = QtWidgets.QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(_lbl(title, 10, C["text_h"], bold=True))
        col.addWidget(_lbl(body,   9, C["text_muted"], wrap=True))
        lo.addLayout(col, 1)

    def _apply_style(self, hovered: bool):
        border = C["accent"] if hovered else C["border"]
        self.setStyleSheet(f"""
            QWidget {{
                background: {C['bg_card']};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        if hovered:
            self._shadow_fx.setBlurRadius(24)
            self._shadow_fx.setColor(QColor(0, 0, 0, 40))
        else:
            self._shadow_fx.setBlurRadius(10)
            self._shadow_fx.setColor(QColor(0, 0, 0, 16))

    def enterEvent(self, _e):   self._apply_style(True)   # noqa: N802
    def leaveEvent(self, _e):   self._apply_style(False)  # noqa: N802


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar nav button
# ─────────────────────────────────────────────────────────────────────────────

class _NavBtn(QtWidgets.QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_txt = icon
        self._label_txt = label
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.setFlat(True)
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

        lo = QtWidgets.QHBoxLayout(self)
        lo.setContentsMargins(14, 0, 14, 0)
        lo.setSpacing(10)

        self._ind = QtWidgets.QWidget()
        self._ind.setFixedSize(3, 22)
        self._ind.setStyleSheet("background:transparent; border-radius:2px;")

        self._ic = QtWidgets.QLabel(icon)
        self._ic.setFixedSize(22, 22)
        self._ic.setAlignment(Qt.AlignCenter)
        self._ic.setStyleSheet(
            "font-size:13pt; background:transparent; color:rgba(255,255,255,0.5);")

        self._txt = QtWidgets.QLabel(label)
        self._txt.setStyleSheet(
            "font-size:10pt; font-weight:500; color:rgba(255,255,255,0.6); background:transparent;")

        lo.addWidget(self._ind, 0)
        lo.addWidget(self._ic, 0)
        lo.addWidget(self._txt, 1)
        self.setStyleSheet("QPushButton{background:transparent;border:none;text-align:left;}")

    def setChecked(self, v: bool):
        super().setChecked(v)
        if v:
            self.setStyleSheet(
                f"QPushButton{{background:{C['sidebar_sel']};border:none;border-radius:8px;}}")
            self._ind.setStyleSheet(
                f"background:{C['sidebar_ind']};border-radius:2px;")
            self._ic.setStyleSheet(
                "font-size:13pt;background:transparent;color:#FFFFFF;")
            self._txt.setStyleSheet(
                "font-size:10pt;font-weight:600;color:#FFFFFF;background:transparent;")
        else:
            self.setStyleSheet("QPushButton{background:transparent;border:none;}")
            self._ind.setStyleSheet("background:transparent;border-radius:2px;")
            self._ic.setStyleSheet(
                "font-size:13pt;background:transparent;color:rgba(255,255,255,0.5);")
            self._txt.setStyleSheet(
                "font-size:10pt;font-weight:500;color:rgba(255,255,255,0.55);background:transparent;")


# ─────────────────────────────────────────────────────────────────────────────
#  Animated stacked widget (opacity fade)
# ─────────────────────────────────────────────────────────────────────────────

class _FadeStack(QtWidgets.QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False

    def slide_to(self, index: int):
        if self._busy or index == self.currentIndex():
            return
        self._busy = True
        next_w = self.widget(index)
        fx = QtWidgets.QGraphicsOpacityEffect(next_w)
        next_w.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _done():
            self.setCurrentIndex(index)
            next_w.setGraphicsEffect(None)
            self._busy = False

        anim.finished.connect(_done)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._anim = anim


# ─────────────────────────────────────────────────────────────────────────────
#  Page builders
# ─────────────────────────────────────────────────────────────────────────────

def _about_page() -> QtWidgets.QWidget:
    inner = QtWidgets.QWidget()
    inner.setStyleSheet("background:transparent;")
    lo = QtWidgets.QVBoxLayout(inner)
    lo.setContentsMargins(28, 24, 28, 24)
    lo.setSpacing(10)

    lo.addWidget(_lbl("About PetroARX", 15, C["text_h"],
                      bold=True, family=FONT_DISPLAY))
    lo.addWidget(_lbl(
        "A modern, full-featured desktop platform for petrophysical interpretation, "
        "formation evaluation, and multi-well basin analysis — built for geoscientists "
        "and reservoir engineers who demand precision.",
        10, C["text_body"], wrap=True,
    ))
    lo.addSpacing(4)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)
    lo.addWidget(_caps("Core Capabilities"))
    lo.addSpacing(8)

    features = [
        ("📂", "Well Data Management",
         "Import and manage LAS 2.0/3.0 and CSV datasets with full curve metadata and unit validation."),
        ("🔍", "Quality Control Engine",
         "Automated QC — missing values, outlier detection (IQR, Z-Score, Isolation Forest), spike smoothing."),
        ("📊", "Multi-Track Log Viewer",
         "Configurable depth-track plots, crossplots, histograms, and overlay visualisations."),
        ("⚙️", "Petrophysical Modules",
         "Integrated Vsh, Porosity (Phi), Water Saturation (Sw), Permeability (K), and Net Pay workflows."),
        ("🧪", "Advanced Interpretation",
         "Pore pressure prediction, geomechanics analysis, and image log processing."),
        ("🌐", "Multi-Well Correlation",
         "Side-by-side well comparison, stratigraphic marker picks, and basin-scale analysis."),
    ]
    for icon, title, body in features:
        lo.addWidget(_HoverCard(icon, title, body))

    lo.addStretch()
    return _scrollable(inner)


def _workflow_page() -> QtWidgets.QWidget:
    inner = QtWidgets.QWidget()
    inner.setStyleSheet("background:transparent;")
    lo = QtWidgets.QVBoxLayout(inner)
    lo.setContentsMargins(28, 24, 28, 24)
    lo.setSpacing(10)

    lo.addWidget(_lbl("Recommended Workflow", 15, C["text_h"],
                      bold=True, family=FONT_DISPLAY))
    lo.addWidget(_lbl(
        "Follow these steps for consistent, reliable petrophysical results.",
        10, C["text_body"], wrap=True,
    ))
    lo.addSpacing(4)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)
    lo.addWidget(_caps("Step-by-Step Guide"))
    lo.addSpacing(8)

    steps = [
        ("Import Well Data",
         "Load LAS 2.0/3.0 or CSV files via File → Import. Verify curve names, units, and depth range."),
        ("Run Quality Control",
         "Open the Quality Control tab. Configure detection method and threshold, then Run QC."),
        ("Formation Evaluation",
         "Execute Vsh, Porosity, Sw modules in sequence using the module ribbon at the top."),
        ("Review & Validate Plots",
         "Use Well Log Plots to inspect multi-track views and crossplots before finalising."),
        ("Export Results",
         "Export cleaned curves and computed parameters via File → Export or each module's export button."),
    ]
    for i, (title, body) in enumerate(steps, 1):
        row_w = QtWidgets.QWidget()
        row_w.setStyleSheet(f"""
            QWidget {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        row_w.setGraphicsEffect(_shadow(8, 2, 12))
        rlo = QtWidgets.QHBoxLayout(row_w)
        rlo.setContentsMargins(14, 11, 14, 11)
        rlo.setSpacing(14)

        num = QtWidgets.QLabel(str(i))
        num.setFixedSize(30, 30)
        num.setAlignment(Qt.AlignCenter)
        num.setStyleSheet(f"""
            font-size:10pt; font-weight:700; color:white;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {C['accent_glow']}, stop:1 {C['accent']});
            border-radius:15px;
        """)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(_lbl(title, 10, C["text_h"], bold=True))
        col.addWidget(_lbl(body,   9, C["text_muted"], wrap=True))

        rlo.addWidget(num, 0, Qt.AlignTop)
        rlo.addLayout(col, 1)
        lo.addWidget(row_w)

    lo.addSpacing(10)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)
    lo.addWidget(_caps("Best Practice Tips"))
    lo.addSpacing(8)

    tips = [
        ("✅", "Always run QC before interpretation to prevent bad data propagating downstream."),
        ("📏", "Verify depth consistency (MD vs TVDSS) before any multi-well correlation."),
        ("🔄", "Visually validate input curves in the log viewer before running calculations."),
        ("💾", "Save your project regularly — File → Save Project preserves all settings."),
        ("📖", "Refer to the full documentation for algorithm references and parameter guidance."),
    ]
    for icon, text in tips:
        tip_w = QtWidgets.QWidget()
        tip_w.setStyleSheet("background:transparent;")
        tip_lo = QtWidgets.QHBoxLayout(tip_w)
        tip_lo.setContentsMargins(4, 2, 4, 2)
        tip_lo.setSpacing(12)
        ic = QtWidgets.QLabel(icon)
        ic.setFixedWidth(22)
        ic.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        ic.setStyleSheet("font-size:11pt; background:transparent;")
        tip_lo.addWidget(ic, 0)
        tip_lo.addWidget(_lbl(text, 9, C["text_body"], wrap=True), 1)
        lo.addWidget(tip_w)

    lo.addStretch()
    return _scrollable(inner)


def _tech_page() -> QtWidgets.QWidget:
    inner = QtWidgets.QWidget()
    inner.setStyleSheet("background:transparent;")
    lo = QtWidgets.QVBoxLayout(inner)
    lo.setContentsMargins(28, 24, 28, 24)
    lo.setSpacing(10)

    lo.addWidget(_lbl("Technology Stack", 15, C["text_h"],
                      bold=True, family=FONT_DISPLAY))
    lo.addWidget(_lbl(
        "Built on a robust scientific Python stack for reliability, performance, "
        "and extensibility across complex interpretation workflows.",
        10, C["text_body"], wrap=True,
    ))
    lo.addSpacing(4)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)
    lo.addWidget(_caps("Core Libraries"))
    lo.addSpacing(8)

    libs = [
        ("🐍", "Python 3.10+",   "Core runtime and application logic"),
        ("🖥️", "PyQt5",          "Desktop UI framework — widgets, painting"),
        ("🐼", "pandas",         "Well log data wrangling and operations"),
        ("🔢", "NumPy",          "Vectorised numerical computation"),
        ("📈", "Matplotlib",     "Log tracks, histograms, crossplots"),
        ("🤖", "scikit-learn",   "Machine learning for QC (Isolation Forest)"),
        ("📄", "lasio",          "LAS 2.0 / 3.0 parsing and writing"),
        ("📐", "SciPy",          "Signal processing and statistics"),
    ]
    grid = QtWidgets.QGridLayout()
    grid.setSpacing(8)
    for idx, (ic_txt, name, desc) in enumerate(libs):
        chip = QtWidgets.QWidget()
        chip.setStyleSheet(f"""
            QWidget {{
                background:{C['bg_card']};
                border:1px solid {C['border']};
                border-radius:10px;
            }}
        """)
        chip.setGraphicsEffect(_shadow(8, 2, 10))
        cl = QtWidgets.QVBoxLayout(chip)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(3)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        ic_lbl = QtWidgets.QLabel(ic_txt)
        ic_lbl.setStyleSheet("font-size:13pt; background:transparent;")
        head.addWidget(ic_lbl)
        head.addWidget(_lbl(name, 9, C["text_h"], bold=True))
        head.addStretch()
        cl.addLayout(head)
        cl.addWidget(_lbl(desc, 8, C["text_muted"], wrap=True))
        grid.addWidget(chip, idx // 2, idx % 2)

    lo.addLayout(grid)
    lo.addSpacing(12)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)
    lo.addWidget(_caps("Application Info"))
    lo.addSpacing(6)

    info_w = QtWidgets.QWidget()
    info_w.setStyleSheet(f"""
        QWidget {{
            background:{C['bg_card']};
            border:1px solid {C['border']};
            border-radius:12px;
        }}
    """)
    info_w.setGraphicsEffect(_shadow(10, 2, 14))
    il = QtWidgets.QVBoxLayout(info_w)
    il.setContentsMargins(18, 14, 18, 14)
    il.setSpacing(8)
    for icon, key, val in (
        ("🔖", "Version",  "1.0.0  (Build 2026)"),
        ("⚖️",  "Licence", "Proprietary — All rights reserved"),
        ("✉️",  "Support", "support@petroarx.io"),
        ("🌐", "Website",  "www.petroarx.io"),
    ):
        r = QtWidgets.QHBoxLayout()
        r.setSpacing(10)
        r.addWidget(_lbl(icon, 11))
        r.addWidget(_lbl(key + ":", 9, C["text_muted"], bold=True))
        r.addWidget(_lbl(val,       9, C["text_h"]))
        r.addStretch()
        il.addLayout(r)
    lo.addWidget(info_w)
    lo.addStretch()

    copy = _lbl("© 2026 PetroARX. All rights reserved.", 8, C["text_muted"])
    copy.setAlignment(Qt.AlignCenter)
    lo.addWidget(copy)
    return _scrollable(inner)


def _shortcuts_page() -> QtWidgets.QWidget:
    inner = QtWidgets.QWidget()
    inner.setStyleSheet("background:transparent;")
    lo = QtWidgets.QVBoxLayout(inner)
    lo.setContentsMargins(28, 24, 28, 24)
    lo.setSpacing(10)

    lo.addWidget(_lbl("Keyboard Shortcuts", 15, C["text_h"],
                      bold=True, family=FONT_DISPLAY))
    lo.addWidget(_lbl(
        "Speed up common tasks with these keyboard shortcuts.",
        10, C["text_body"], wrap=True,
    ))
    lo.addSpacing(4)
    lo.addWidget(_h_sep())
    lo.addSpacing(6)

    sections = {
        "File Operations": [
            ("Ctrl + N",       "New Project"),
            ("Ctrl + O",       "Open Project"),
            ("Ctrl + S",       "Save Project"),
            ("Ctrl + Shift+E", "Export as PDF"),
        ],
        "Well Data": [
            ("Ctrl + I",  "Import LAS / CSV"),
            ("Ctrl + R",  "Refresh Well Tree"),
            ("Delete",    "Remove Selected Well"),
        ],
        "View & Plot": [
            ("Ctrl + P",  "Open Plot Window"),
            ("Ctrl + +",  "Zoom In"),
            ("Ctrl + -",  "Zoom Out"),
            ("F11",       "Full-Screen Toggle"),
        ],
        "Quality Control": [
            ("Ctrl + Q",       "Run QC"),
            ("Ctrl + Shift+Q", "Reset QC"),
            ("Ctrl + E",       "Export Cleaned Data"),
        ],
    }

    for section, rows in sections.items():
        lo.addWidget(_caps(section))
        lo.addSpacing(4)

        tbl_w = QtWidgets.QWidget()
        tbl_w.setStyleSheet(f"""
            QWidget {{
                background:{C['bg_card']};
                border:1px solid {C['border']};
                border-radius:10px;
            }}
        """)
        tbl_w.setGraphicsEffect(_shadow(8, 2, 10))
        tbl_lo = QtWidgets.QVBoxLayout(tbl_w)
        tbl_lo.setContentsMargins(0, 0, 0, 0)
        tbl_lo.setSpacing(0)

        n = len(rows)
        for i, (key, desc) in enumerate(rows):
            row_bg = C["bg"] if i % 2 == 0 else C["bg_card"]
            if i == 0 and n == 1:
                radius = "border-radius:10px;"
            elif i == 0:
                radius = "border-top-left-radius:10px; border-top-right-radius:10px;"
            elif i == n - 1:
                radius = "border-bottom-left-radius:10px; border-bottom-right-radius:10px;"
            else:
                radius = ""

            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet(f"background:{row_bg}; {radius}")
            rlo = QtWidgets.QHBoxLayout(row_w)
            rlo.setContentsMargins(16, 9, 16, 9)
            rlo.setSpacing(0)

            key_lbl = QtWidgets.QLabel(key)
            key_lbl.setStyleSheet(f"""
                font-size:9pt;
                font-family:'Consolas','Courier New',monospace;
                font-weight:600;
                color:{C['accent_dim']};
                background:rgba(39,174,116,0.08);
                border:1px solid rgba(39,174,116,0.25);
                border-radius:5px;
                padding:2px 8px;
            """)
            key_lbl.setFixedWidth(150)

            rlo.addWidget(key_lbl)
            rlo.addSpacing(14)
            rlo.addWidget(_lbl(desc, 9, C["text_body"]), 1)
            tbl_lo.addWidget(row_w)

        lo.addWidget(tbl_w)
        lo.addSpacing(10)

    lo.addStretch()
    return _scrollable(inner)


# ─────────────────────────────────────────────────────────────────────────────
#  Main dialog
# ─────────────────────────────────────────────────────────────────────────────

class AboutHelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PetroARX — Information Center")
        self.setMinimumSize(860, 620)
        self.setMaximumSize(1040, 800)
        self.setStyleSheet(f"QDialog {{ background:{C['bg']}; }}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._build_ui()

    # ── Root layout ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Painted header
        self._hdr = _HeaderBanner(self)
        self._hdr.populate()
        root.addWidget(self._hdr)

        # Sidebar + content
        body_row = QtWidgets.QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)
        body_row.addWidget(self._build_sidebar())

        right_col = QtWidgets.QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        right_col.addWidget(self._build_stack(), 1)
        right_col.addWidget(self._build_footer())
        body_row.addLayout(right_col, 1)

        body_w = QtWidgets.QWidget()
        body_w.setLayout(body_row)
        root.addWidget(body_w, 1)

    # ── Sidebar ───────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QtWidgets.QWidget:
        side = QtWidgets.QWidget()
        side.setFixedWidth(185)
        side.setStyleSheet(f"background:{C['sidebar_bg']};")

        lo = QtWidgets.QVBoxLayout(side)
        lo.setContentsMargins(8, 18, 8, 18)
        lo.setSpacing(3)

        nav_cap = QtWidgets.QLabel("NAVIGATION")
        nav_cap.setStyleSheet(f"""
            font-size:7pt; font-weight:700; letter-spacing:2px;
            color:rgba(255,255,255,0.25); background:transparent;
            padding-left:16px;
        """)
        lo.addWidget(nav_cap)
        lo.addSpacing(6)

        pages = [
            ("📋", "About"),
            ("🗺️",  "Workflow"),
            ("🔬", "Technology"),
            ("⌨️",  "Shortcuts"),
        ]
        self._nav_btns: list[_NavBtn] = []
        for icon, label in pages:
            btn = _NavBtn(icon, label, side)
            btn.clicked.connect(self._make_nav(len(self._nav_btns)))
            lo.addWidget(btn)
            self._nav_btns.append(btn)

        lo.addStretch()

        bld = QtWidgets.QLabel("Build 2026.1")
        bld.setAlignment(Qt.AlignCenter)
        bld.setStyleSheet(
            "font-size:7pt; color:rgba(255,255,255,0.18); background:transparent;")
        lo.addWidget(bld)

        self._nav_btns[0].setChecked(True)
        return side

    def _make_nav(self, index: int):
        def _handler():
            for i, btn in enumerate(self._nav_btns):
                btn.setChecked(i == index)
            self._stack.slide_to(index)
        return _handler

    # ── Stacked pages ─────────────────────────────────────────────────────

    def _build_stack(self) -> _FadeStack:
        self._stack = _FadeStack()
        self._stack.setStyleSheet(f"background:{C['bg']};")
        for page_fn in (_about_page, _workflow_page, _tech_page, _shortcuts_page):
            self._stack.addWidget(page_fn())
        return self._stack

    # ── Footer ────────────────────────────────────────────────────────────

    def _build_footer(self) -> QtWidgets.QWidget:
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"""
            background:{C['bg_card']};
            border-top:1px solid {C['border']};
        """)
        lo = QtWidgets.QHBoxLayout(footer)
        lo.setContentsMargins(24, 0, 24, 0)
        lo.setSpacing(10)

        lo.addWidget(_lbl(
            "PetroARX v1.0  ·  © 2026 All rights reserved.",
            8, C["text_muted"],
        ))
        lo.addStretch()

        docs_btn = QtWidgets.QPushButton("📖  Documentation")
        docs_btn.setFixedHeight(32)
        docs_btn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        docs_btn.setStyleSheet(f"""
            QPushButton {{
                font-size:9pt;
                color:{C['accent_dim']};
                background:rgba(39,174,116,0.08);
                border:1px solid rgba(39,174,116,0.30);
                border-radius:7px;
                padding:0 14px;
            }}
            QPushButton:hover {{
                background:rgba(39,174,116,0.16);
                border-color:{C['accent']};
            }}
        """)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setFixedSize(90, 32)
        close_btn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                font-size:10pt; font-weight:600; color:white;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['accent_glow']}, stop:1 {C['accent']});
                border:none;
                border-radius:7px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['accent_glow']}, stop:1 {C['accent_dim']});
            }}
            QPushButton:pressed {{ padding-top:1px; }}
        """)
        close_btn.setGraphicsEffect(_shadow(10, 3, 45))

        lo.addWidget(docs_btn)
        lo.addWidget(close_btn)
        return footer