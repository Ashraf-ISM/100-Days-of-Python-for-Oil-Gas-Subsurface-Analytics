from PyQt5 import QtWidgets, QtCore, QtGui


# ─────────────────────────────────────────────────────────────────────────────
#  Palette / style constants
# ─────────────────────────────────────────────────────────────────────────────
_NAVY       = "#0D1F35"
_NAVY_MID   = "#1B3A57"
_NAVY_LIGHT = "#24466B"
_ACCENT     = "#2E8B57"          # sea-green – petroleum industry feel
_ACCENT2    = "#3AA76D"
_BORDER     = "#D4DCE8"
_BG         = "#F5F7FA"
_BG_CARD    = "#FFFFFF"
_TEXT_MAIN  = "#1A2535"
_TEXT_SUB   = "#5A6A7E"
_TEXT_MUTED = "#8896A8"


_DIALOG_STYLE = f"""
QDialog {{
    background-color: {_BG};
    font-family: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', sans-serif;
}}

/* ── Tab bar ─────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {_BORDER};
    border-radius: 10px;
    background: {_BG_CARD};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT_SUB};
    padding: 9px 22px;
    font-size: 10pt;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    color: {_ACCENT};
    border-bottom: 2px solid {_ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {_NAVY_LIGHT};
}}

/* ── Scroll area ─────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    width: 6px;
    background: {_BG};
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER};
    border-radius: 3px;
    min-height: 30px;
}}

/* ── Close button ────────────────────────────────────── */
QPushButton#closeBtn {{
    background-color: {_ACCENT};
    color: white;
    font-size: 10pt;
    font-weight: 600;
    padding: 8px 28px;
    border-radius: 7px;
    border: none;
    letter-spacing: 0.3px;
}}
QPushButton#closeBtn:hover {{
    background-color: {_ACCENT2};
}}
QPushButton#closeBtn:pressed {{
    background-color: {_ACCENT};
    padding-top: 9px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Small helpers
# ─────────────────────────────────────────────────────────────────────────────

def _h_rule(color: str = _BORDER) -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setStyleSheet(f"color: {color}; background: {color}; border: none; max-height: 1px;")
    return line


def _label(text: str, size: int = 10, color: str = _TEXT_MAIN,
           bold: bool = False, wrap: bool = False) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    weight = "600" if bold else "400"
    lbl.setStyleSheet(
        f"font-size: {size}pt; color: {color}; font-weight: {weight}; background: transparent;"
    )
    lbl.setWordWrap(wrap)
    return lbl


def _section_title(text: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text.upper())
    lbl.setStyleSheet(f"""
        font-size: 7.5pt;
        font-weight: 700;
        color: {_TEXT_MUTED};
        letter-spacing: 1.5px;
        background: transparent;
    """)
    return lbl


def _card(parent_layout: QtWidgets.QLayout,
          icon: str, title: str, body: str) -> None:
    """Append a feature card (icon + bold title + muted body) to parent_layout."""
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(14)
    row.setContentsMargins(0, 0, 0, 0)

    # Icon bubble
    icon_lbl = QtWidgets.QLabel(icon)
    icon_lbl.setFixedSize(38, 38)
    icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
    icon_lbl.setStyleSheet(f"""
        font-size: 16pt;
        background: {_BG};
        border: 1px solid {_BORDER};
        border-radius: 10px;
    """)

    # Text
    text_col = QtWidgets.QVBoxLayout()
    text_col.setSpacing(2)
    text_col.setContentsMargins(0, 0, 0, 0)
    text_col.addWidget(_label(title, size=10, color=_TEXT_MAIN, bold=True))
    text_col.addWidget(_label(body,  size=9,  color=_TEXT_SUB,  wrap=True))

    row.addWidget(icon_lbl, 0)
    row.addLayout(text_col, 1)

    wrapper = QtWidgets.QWidget()
    wrapper.setLayout(row)
    wrapper.setStyleSheet(f"""
        QWidget {{
            background: {_BG_CARD};
            border: 1px solid {_BORDER};
            border-radius: 10px;
            padding: 8px 10px;
        }}
    """)
    parent_layout.addWidget(wrapper)


def _step_row(number: str, text: str) -> QtWidgets.QWidget:
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(12)
    row.setContentsMargins(0, 0, 0, 0)

    num_lbl = QtWidgets.QLabel(number)
    num_lbl.setFixedSize(28, 28)
    num_lbl.setAlignment(QtCore.Qt.AlignCenter)
    num_lbl.setStyleSheet(f"""
        font-size: 9pt;
        font-weight: 700;
        color: white;
        background: {_ACCENT};
        border-radius: 14px;
    """)

    text_lbl = _label(text, size=10, color=_TEXT_MAIN, wrap=True)

    row.addWidget(num_lbl, 0, QtCore.Qt.AlignTop)
    row.addWidget(text_lbl, 1)

    wrapper = QtWidgets.QWidget()
    wrapper.setLayout(row)
    wrapper.setStyleSheet("background: transparent;")
    return wrapper


def _tip_row(icon: str, text: str) -> QtWidgets.QWidget:
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 0, 0, 0)

    icon_lbl = QtWidgets.QLabel(icon)
    icon_lbl.setFixedWidth(22)
    icon_lbl.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
    icon_lbl.setStyleSheet("font-size: 12pt; background: transparent;")

    text_lbl = _label(text, size=10, color=_TEXT_SUB, wrap=True)

    row.addWidget(icon_lbl, 0)
    row.addWidget(text_lbl, 1)

    wrapper = QtWidgets.QWidget()
    wrapper.setLayout(row)
    wrapper.setStyleSheet("background: transparent;")
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
#  Main dialog
# ─────────────────────────────────────────────────────────────────────────────

class AboutHelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PetroARX – Information")
        self.setMinimumSize(640, 580)
        self.setMaximumWidth(720)
        self.setStyleSheet(_DIALOG_STYLE)
        self._build_ui()

    # ── Shell ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._header_banner())

        body = QtWidgets.QVBoxLayout()
        body.setContentsMargins(24, 18, 24, 20)
        body.setSpacing(14)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._about_tab(),   "  About  ")
        tabs.addTab(self._help_tab(),    "  Workflow  ")
        tabs.addTab(self._credits_tab(), "  Credits  ")
        body.addWidget(tabs)

        # Footer row
        footer = QtWidgets.QHBoxLayout()
        ver = _label("v1.0.0  ·  Build 2026", size=8, color=_TEXT_MUTED)
        footer.addWidget(ver)
        footer.addStretch()

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        body.addLayout(footer)

        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(body)
        root.addWidget(wrapper)

    # ── Header banner ──────────────────────────────────────────────────────

    def _header_banner(self) -> QtWidgets.QWidget:
        banner = QtWidgets.QWidget()
        banner.setFixedHeight(110)
        banner.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {_NAVY},
                    stop:0.6 {_NAVY_MID},
                    stop:1 {_NAVY_LIGHT}
                );
            }}
        """)

        layout = QtWidgets.QHBoxLayout(banner)
        layout.setContentsMargins(28, 16, 28, 16)
        layout.setSpacing(18)

        # Logo block
        logo_box = QtWidgets.QVBoxLayout()
        logo_box.setSpacing(3)

        logo_text = QtWidgets.QLabel("PetroARX")
        logo_text.setStyleSheet("""
            font-size: 22pt;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.5px;
            background: transparent;
        """)

        tagline = QtWidgets.QLabel("Petrophysics Interpretation Platform")
        tagline.setStyleSheet(f"""
            font-size: 9pt;
            color: rgba(255,255,255,0.65);
            background: transparent;
            letter-spacing: 0.3px;
        """)

        logo_box.addWidget(logo_text)
        logo_box.addWidget(tagline)
        layout.addLayout(logo_box, 1)

        # Badge
        badge = QtWidgets.QLabel("v1.0")
        badge.setFixedSize(54, 54)
        badge.setAlignment(QtCore.Qt.AlignCenter)
        badge.setStyleSheet(f"""
            font-size: 11pt;
            font-weight: 700;
            color: {_ACCENT2};
            background: rgba(255,255,255,0.10);
            border: 2px solid rgba(255,255,255,0.18);
            border-radius: 27px;
        """)
        layout.addWidget(badge, 0)

        return banner

    # ── About tab ─────────────────────────────────────────────────────────

    def _about_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer.setStyleSheet("background: transparent;")
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(outer)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout = QtWidgets.QVBoxLayout(outer)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        intro = _label(
            "PetroARX is a modern desktop platform for advanced petrophysical "
            "interpretation, multi-well analysis, and formation evaluation — "
            "designed for efficiency and accuracy in complex reservoir characterisation.",
            size=10, color=_TEXT_SUB, wrap=True
        )
        layout.addWidget(intro)
        layout.addWidget(_h_rule())
        layout.addSpacing(4)
        layout.addWidget(_section_title("Core Capabilities"))
        layout.addSpacing(6)

        features = [
            ("📂", "Well Data Management",
             "Import, organise, and manage LAS 2.0/3.0 and CSV well datasets with full curve metadata support."),
            ("🔍", "Quality Control",
             "Automated QC workflows — missing value detection, outlier flagging, spike smoothing, and export."),
            ("📊", "Multi-Track Log Plotting",
             "Configurable depth-track views, crossplots, histograms, and overlay visualisations."),
            ("⚙️", "Petrophysical Modules",
             "Integrated Vsh, porosity (Phi), water saturation (Sw), permeability (K), and net-pay workflows."),
            ("🧪", "Advanced Interpretation",
             "Pore pressure prediction, geomechanics analysis, and image log processing modules."),
            ("🌐", "Multi-Well Correlation",
             "Side-by-side well comparison, marker correlation, and basin-scale analysis tools."),
        ]
        for icon, title, body in features:
            _card(layout, icon, title, body)

        layout.addStretch()

        tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    # ── Help / Workflow tab ────────────────────────────────────────────────

    def _help_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer.setStyleSheet("background: transparent;")
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(outer)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout = QtWidgets.QVBoxLayout(outer)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        layout.addWidget(_section_title("Recommended Workflow"))
        layout.addSpacing(6)

        steps = [
            ("1", "Import Well Data",
             "Load LAS 2.0/3.0 or CSV files via File → Import. Verify curve names and units."),
            ("2", "Quality Control",
             "Open the Quality Control tab. Select a curve, configure method and threshold, then Run QC."),
            ("3", "Formation Evaluation",
             "Run Vsh, Porosity, and Water Saturation modules in sequence using the top tab bar."),
            ("4", "Review Plots",
             "Use the Well Log Plots tab to visualise multi-track displays and crossplots."),
            ("5", "Export Results",
             "Export cleaned data, calculated curves, and plots via File → Export or each module's export button."),
        ]

        for number, title, body in steps:
            step_widget = _step_row(number, f"  {title} — {body}")
            layout.addWidget(step_widget)

        layout.addSpacing(10)
        layout.addWidget(_h_rule())
        layout.addSpacing(6)
        layout.addWidget(_section_title("Best Practice Tips"))
        layout.addSpacing(6)

        tips = [
            ("✅", "Always run QC before any interpretation module to avoid propagating bad data."),
            ("📏", "Verify depth consistency and units (MD vs TVDSS) before multi-well correlation."),
            ("🔄", "Validate input curves visually in the log viewer before running calculations."),
            ("💾", "Save your project regularly — use File → Save Project to preserve all settings."),
            ("📖", "Refer to the full documentation for algorithm references and parameter guidance."),
        ]

        for icon, text in tips:
            layout.addWidget(_tip_row(icon, text))

        layout.addStretch()

        tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    # ── Credits tab ───────────────────────────────────────────────────────

    def _credits_tab(self) -> QtWidgets.QWidget:
        outer = QtWidgets.QWidget()
        outer.setStyleSheet("background: transparent;")

        layout = QtWidgets.QVBoxLayout(outer)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Built-with section
        layout.addWidget(_section_title("Built With"))
        layout.addSpacing(4)

        tech_grid = QtWidgets.QGridLayout()
        tech_grid.setSpacing(8)
        tech_items = [
            ("Python 3.10+",   "Core runtime"),
            ("PyQt5",          "Desktop UI framework"),
            ("pandas",         "Data wrangling"),
            ("NumPy",          "Numerical engine"),
            ("Matplotlib",     "Plotting & visualisation"),
            ("scikit-learn",   "Machine learning (QC)"),
            ("lasio",          "LAS file I/O"),
            ("welly",          "Well log utilities"),
        ]
        for idx, (lib, desc) in enumerate(tech_items):
            chip = QtWidgets.QWidget()
            chip.setStyleSheet(f"""
                QWidget {{
                    background: {_BG};
                    border: 1px solid {_BORDER};
                    border-radius: 8px;
                    padding: 4px 8px;
                }}
            """)
            chip_layout = QtWidgets.QVBoxLayout(chip)
            chip_layout.setContentsMargins(8, 6, 8, 6)
            chip_layout.setSpacing(1)
            chip_layout.addWidget(_label(lib,  size=9,  color=_TEXT_MAIN, bold=True))
            chip_layout.addWidget(_label(desc, size=8,  color=_TEXT_MUTED))
            tech_grid.addWidget(chip, idx // 2, idx % 2)

        layout.addLayout(tech_grid)
        layout.addWidget(_h_rule())

        # Licence / info
        layout.addWidget(_section_title("Licence & Info"))
        layout.addSpacing(4)

        info_lines = [
            ("🔖", "Version",    "1.0.0  (Build 2026)"),
            ("⚖️",  "Licence",   "Proprietary — All rights reserved"),
            ("✉️",  "Support",   "support@petroarx.io"),
            ("🌐", "Website",    "www.petroarx.io"),
        ]
        for icon, key, val in info_lines:
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(_label(icon, size=11))
            row.addWidget(_label(key + ":", size=9, color=_TEXT_MUTED, bold=True))
            row.addWidget(_label(val,       size=9, color=_TEXT_MAIN))
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()

        # Copyright strip
        copy_lbl = _label(
            "© 2026 PetroARX. All rights reserved.",
            size=8, color=_TEXT_MUTED
        )
        copy_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(copy_lbl)

        return outer