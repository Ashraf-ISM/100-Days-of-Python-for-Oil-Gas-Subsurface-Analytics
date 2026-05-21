"""Advanced Multi-Well Correlation Workspace Tab.

Provides a fully featured, professional well-correlation panel that can be
embedded inside the existing tabWellCorrelation QWidget.  The widget is
self-contained and reads well data from a DataService-compatible object
(anything exposing ``._wells`` dict and ``._current_well`` string).
"""
from __future__ import annotations

import textwrap
from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets


# ---------------------------------------------------------------------------
# Palette constants
# ---------------------------------------------------------------------------
CLR_BG           = "#0F1923"       # deep navy background
CLR_PANEL        = "#152130"       # slightly lighter panel
CLR_CARD         = "#1C2D3F"       # card surfaces
CLR_CARD_BORDER  = "#2A3F56"       # card borders
CLR_ACCENT       = "#00B4D8"       # bright cyan accent
CLR_ACCENT2      = "#7C5CFF"       # purple accent
CLR_ACCENT3      = "#22D3A6"       # teal accent
CLR_TEXT_PRIMARY = "#E8F1F9"       # primary text (near white)
CLR_TEXT_MUTED   = "#7B9AB5"       # muted / secondary text
CLR_HEADER_GRAD  = ("stop:0 #0D2137, stop:0.5 #0E3159, stop:1 #0F2A4A")
CLR_BTN_RENDER   = "#00B4D8"
CLR_BTN_EXPORT   = "#22D3A6"
CLR_BTN_CLEAR    = "#3A4A5C"

LOG_CURVES = {
    "GR":    ("#4CAF50", "gAPI",    (0,   150)),
    "RHOB":  ("#FF7043", "g/cc",    (1.95, 2.95)),
    "NPHI":  ("#29B6F6", "v/v",     (0.45, -0.15)),
    "RT":    ("#EF9A9A", "ohm·m",   (0.2, 200)),
    "SP":    ("#CE93D8", "mV",      (-160, 40)),
    "CALI":  ("#FFCA28", "in",      (6,   16)),
    "DT":    ("#80DEEA", "μs/ft",   (40,  140)),
    "PHIE":  ("#A5D6A7", "v/v",     (0,   0.4)),
    "VSH":   ("#FFCC80", "v/v",     (0,   1)),
    "SW":    ("#90CAF9", "v/v",     (0,   1)),
}

SS_GLOBAL = f"""
    QWidget {{
        background: {CLR_BG};
        color: {CLR_TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
        font-size: 12px;
    }}
    QFrame {{
        border: none;
    }}
    QScrollBar:vertical {{
        background: {CLR_PANEL};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {CLR_CARD_BORDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {CLR_PANEL};
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {CLR_CARD_BORDER};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QListWidget {{
        background: {CLR_CARD};
        border: 1px solid {CLR_CARD_BORDER};
        border-radius: 6px;
        padding: 4px;
        outline: 0;
    }}
    QListWidget::item {{
        padding: 7px 10px;
        border-radius: 5px;
        color: {CLR_TEXT_PRIMARY};
    }}
    QListWidget::item:selected {{
        background: {CLR_ACCENT2};
        color: #FFFFFF;
    }}
    QListWidget::item:hover:!selected {{
        background: {CLR_CARD_BORDER};
    }}
    QComboBox {{
        background: {CLR_CARD};
        border: 1px solid {CLR_CARD_BORDER};
        border-radius: 5px;
        padding: 5px 10px;
        color: {CLR_TEXT_PRIMARY};
        min-height: 28px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {CLR_ACCENT};
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background: {CLR_CARD};
        border: 1px solid {CLR_ACCENT};
        selection-background-color: {CLR_ACCENT2};
        color: {CLR_TEXT_PRIMARY};
        border-radius: 5px;
    }}
    QCheckBox {{
        color: {CLR_TEXT_PRIMARY};
        spacing: 8px;
        font-size: 12px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 2px solid {CLR_CARD_BORDER};
        background: {CLR_CARD};
    }}
    QCheckBox::indicator:checked {{
        background: {CLR_ACCENT};
        border-color: {CLR_ACCENT};
        image: none;
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {CLR_CARD_BORDER};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {CLR_ACCENT};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {CLR_ACCENT};
        border-radius: 2px;
    }}
    QDoubleSpinBox, QSpinBox {{
        background: {CLR_CARD};
        border: 1px solid {CLR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px 8px;
        color: {CLR_TEXT_PRIMARY};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
    QSpinBox::up-button, QSpinBox::down-button {{
        background: {CLR_CARD_BORDER};
        border-radius: 3px;
        width: 16px;
    }}
    QLabel {{
        background: transparent;
    }}
    QGroupBox {{
        color: {CLR_TEXT_MUTED};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border: 1px solid {CLR_CARD_BORDER};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 6px;
        background: {CLR_CARD};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {CLR_TEXT_MUTED};
    }}
    QSplitter::handle {{
        background: {CLR_CARD_BORDER};
        width: 3px;
    }}
    QToolTip {{
        background: {CLR_CARD};
        color: {CLR_TEXT_PRIMARY};
        border: 1px solid {CLR_ACCENT};
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 11px;
    }}
"""


def _make_push_button(text: str, color: str, text_color: str = "#FFFFFF",
                      min_h: int = 36, bold: bool = True) -> QtWidgets.QPushButton:
    btn = QtWidgets.QPushButton(text)
    btn.setMinimumHeight(min_h)
    btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
    weight = "700" if bold else "500"
    btn.setStyleSheet(
        f"QPushButton {{"
        f"  background: {color};"
        f"  color: {text_color};"
        f"  border: none;"
        f"  border-radius: 8px;"
        f"  padding: 8px 18px;"
        f"  font-size: 12px;"
        f"  font-weight: {weight};"
        f"}}"
        f"QPushButton:hover {{"
        f"  background: {color}CC;"
        f"}}"
        f"QPushButton:pressed {{"
        f"  background: {color}88;"
        f"}}"
    )
    return btn


def _section_label(text: str, parent=None) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text, parent)
    lbl.setStyleSheet(
        f"color: {CLR_TEXT_MUTED};"
        f"font-size: 10px;"
        f"font-weight: 700;"
        f"letter-spacing: 0.8px;"
        f"text-transform: uppercase;"
        f"background: transparent;"
    )
    return lbl


def _tag_label(text: str, color: str, parent=None) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text, parent)
    lbl.setStyleSheet(
        f"background: {color}33;"
        f"color: {color};"
        f"border: 1px solid {color}55;"
        f"border-radius: 5px;"
        f"padding: 2px 8px;"
        f"font-size: 10px;"
        f"font-weight: 700;"
    )
    lbl.setAlignment(QtCore.Qt.AlignCenter)
    return lbl


# ---------------------------------------------------------------------------
class GlowFrame(QtWidgets.QFrame):
    """A card-style frame with a subtle glow border."""
    def __init__(self, parent=None, accent: str = CLR_ACCENT, radius: int = 12):
        super().__init__(parent)
        self.setObjectName("GlowFrame")
        self.setStyleSheet(
            f"QFrame#GlowFrame {{"
            f"  background: {CLR_CARD};"
            f"  border: 1px solid {accent}33;"
            f"  border-radius: {radius}px;"
            f"}}"
        )


# ---------------------------------------------------------------------------
class AnimatedButton(QtWidgets.QPushButton):
    """Push button with a subtle scale animation on press via palette."""
    def __init__(self, text: str, color: str, parent=None):
        super().__init__(text, parent)
        self._color = color
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setMinimumHeight(40)
        self._apply_style(pressed=False)

    def _apply_style(self, pressed: bool) -> None:
        alpha = "BB" if pressed else "FF"
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background: {self._color}{alpha};"
            f"  color: #FFFFFF;"
            f"  border: none;"
            f"  border-radius: 9px;"
            f"  padding: 10px 22px;"
            f"  font-size: 13px;"
            f"  font-weight: 700;"
            f"  letter-spacing: 0.3px;"
            f"}}"
            f"QPushButton:hover {{ background: {self._color}DD; }}"
            f"QPushButton:pressed {{ background: {self._color}88; }}"
        )

    def mousePressEvent(self, e):
        self._apply_style(True)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._apply_style(False)
        super().mouseReleaseEvent(e)


# ---------------------------------------------------------------------------
class WellCorrelationTab(QtWidgets.QWidget):
    """Advanced, professional Multi-Well Correlation Workspace."""

    def __init__(self, data_service=None, parent=None):
        super().__init__(parent)
        self._data_service = data_service
        self._selected_wells: list[str] = []
        self._canvas = None
        self._fig = None
        self.setStyleSheet(SS_GLOBAL)
        self._build_ui()
        self._refresh_well_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Header banner ──────────────────────────────────────────────
        root.addWidget(self._build_header())

        # ── Metric cards row ───────────────────────────────────────────
        root.addWidget(self._build_metrics_row())

        # ── Main body (splitter: sidebar | canvas) ─────────────────────
        root.addWidget(self._build_body(), stretch=1)

        # ── Status bar ─────────────────────────────────────────────────
        root.addWidget(self._build_status_bar())

    # ── Header ────────────────────────────────────────────────────────
    def _build_header(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setMinimumHeight(82)
        frame.setMaximumHeight(100)
        frame.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"    {CLR_HEADER_GRAD});"
            "  border: 1px solid #1A3A5C;"
            "  border-radius: 12px;"
            "}"
        )
        h = QtWidgets.QHBoxLayout(frame)
        h.setContentsMargins(20, 14, 20, 14)
        h.setSpacing(16)

        # Icon pill
        icon_frame = QtWidgets.QFrame()
        icon_frame.setFixedSize(48, 48)
        icon_frame.setStyleSheet(
            f"QFrame {{ background: {CLR_ACCENT}22;"
            f"border: 1px solid {CLR_ACCENT}55; border-radius: 10px; }}"
        )
        icon_lbl = QtWidgets.QLabel("⛳", icon_frame)
        icon_lbl.setStyleSheet(
            "font-size: 22px; background: transparent; border: none;"
        )
        icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        il = QtWidgets.QVBoxLayout(icon_frame)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(icon_lbl)
        h.addWidget(icon_frame)

        # Text block
        txt = QtWidgets.QVBoxLayout()
        txt.setSpacing(3)
        title = QtWidgets.QLabel("Multi-Well Correlation Workspace")
        title.setStyleSheet(
            f"color: {CLR_TEXT_PRIMARY}; font-size: 17px; font-weight: 800;"
            f"background: transparent; border: none;"
        )
        sub = QtWidgets.QLabel(
            "Select wells · pick curves · configure alignment · render synchronized tracks"
        )
        sub.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 11px;"
            f"background: transparent; border: none;"
        )
        txt.addWidget(title)
        txt.addWidget(sub)
        h.addLayout(txt, 1)

        # Status badge
        self._lbl_status = _tag_label("● Ready", CLR_ACCENT3)
        self._lbl_status.setFixedWidth(90)
        h.addWidget(self._lbl_status)

        # Refresh btn
        btn_refresh = _make_push_button("↻ Refresh Wells", CLR_ACCENT2, min_h=32)
        btn_refresh.setFixedWidth(140)
        btn_refresh.clicked.connect(self._refresh_well_list)
        h.addWidget(btn_refresh)

        return frame

    # ── Metric cards ──────────────────────────────────────────────────
    def _build_metrics_row(self) -> QtWidgets.QFrame:
        wrap = QtWidgets.QFrame()
        wrap.setMaximumHeight(80)
        row = QtWidgets.QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self._metric_wells_loaded = self._make_metric_card("Wells Loaded", "0", CLR_ACCENT)
        self._metric_selected     = self._make_metric_card("Selected", "0", CLR_ACCENT2)
        self._metric_curves       = self._make_metric_card("Avg Curves", "—", CLR_ACCENT3)
        self._metric_depth_range  = self._make_metric_card("Depth Span (m)", "—", "#F5A623")

        for card in (self._metric_wells_loaded, self._metric_selected,
                     self._metric_curves, self._metric_depth_range):
            row.addWidget(card)
        return wrap

    def _make_metric_card(self, label: str, value: str,
                          color: str) -> QtWidgets.QFrame:
        card = GlowFrame(accent=color, radius=10)
        card.setMinimumHeight(64)
        vl = QtWidgets.QVBoxLayout(card)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 10px; font-weight: 600;")
        val = QtWidgets.QLabel(value)
        val.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: 800;"
        )
        val.setObjectName(f"metric_val_{label.replace(' ', '_')}")
        vl.addWidget(lbl)
        vl.addWidget(val)
        card._val_label = val  # type: ignore[attr-defined]
        return card

    def _set_metric(self, card: QtWidgets.QFrame, text: str) -> None:
        lbl = getattr(card, "_val_label", None)
        if lbl is not None:
            lbl.setText(text)

    # ── Main body ─────────────────────────────────────────────────────
    def _build_body(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(
            "QSplitter::handle { background: #1F3248; border-radius: 2px; }"
        )
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_canvas_area())
        splitter.setSizes([310, 900])
        return splitter

    # ── Sidebar ───────────────────────────────────────────────────────
    def _build_sidebar(self) -> QtWidgets.QFrame:
        sidebar = QtWidgets.QFrame()
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(360)
        sidebar.setStyleSheet(
            f"QFrame {{ background: {CLR_PANEL}; border-radius: 12px; }}"
        )
        sv = QtWidgets.QScrollArea()
        sv.setFrameShape(QtWidgets.QFrame.NoFrame)
        sv.setWidgetResizable(True)
        sv.setWidget(sidebar)
        sv.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        vl = QtWidgets.QVBoxLayout(sidebar)
        vl.setContentsMargins(14, 14, 14, 14)
        vl.setSpacing(12)

        # Well selection
        vl.addWidget(self._build_well_selection_card())
        # Track / curve selector
        vl.addWidget(self._build_track_selector_card())
        # Alignment settings
        vl.addWidget(self._build_alignment_card())
        # Display options
        vl.addWidget(self._build_display_options_card())
        vl.addStretch(1)

        wrap = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(sv)
        return wrap  # type: ignore[return-value]

    def _build_well_selection_card(self) -> QtWidgets.QFrame:
        card = GlowFrame(radius=10)
        vl = QtWidgets.QVBoxLayout(card)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(_section_label("Well Selection"))
        self._lbl_well_count = QtWidgets.QLabel("0 wells")
        self._lbl_well_count.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 10px; font-weight: 700;"
        )
        row.addStretch()
        row.addWidget(self._lbl_well_count)
        vl.addLayout(row)

        # Search box
        self._well_search = QtWidgets.QLineEdit()
        self._well_search.setPlaceholderText("🔍   Search wells…")
        self._well_search.setFixedHeight(30)
        self._well_search.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {CLR_BG};"
            f"  border: 1px solid {CLR_CARD_BORDER};"
            f"  border-radius: 6px;"
            f"  padding: 4px 10px;"
            f"  color: {CLR_TEXT_PRIMARY};"
            f"}}"
            f"QLineEdit:focus {{ border-color: {CLR_ACCENT}; }}"
        )
        self._well_search.textChanged.connect(self._filter_wells)
        vl.addWidget(self._well_search)

        self._list_wells = QtWidgets.QListWidget()
        self._list_wells.setMinimumHeight(160)
        self._list_wells.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self._list_wells.setStyleSheet(
            f"QListWidget {{"
            f"  background: {CLR_BG};"
            f"  border: 1px solid {CLR_CARD_BORDER};"
            f"  border-radius: 6px;"
            f"  padding: 4px;"
            f"}}"
            f"QListWidget::item {{"
            f"  padding: 8px 10px;"
            f"  border-radius: 5px;"
            f"}}"
            f"QListWidget::item:selected {{"
            f"  background: {CLR_ACCENT2};"
            f"  color: #FFFFFF;"
            f"}}"
            f"QListWidget::item:hover:!selected {{"
            f"  background: {CLR_CARD_BORDER};"
            f"}}"
        )
        self._list_wells.itemSelectionChanged.connect(self._on_well_selection_changed)
        vl.addWidget(self._list_wells)

        # Select-all / Clear buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_all = _make_push_button("Select All", CLR_CARD_BORDER,
                                     CLR_TEXT_PRIMARY, min_h=28, bold=False)
        btn_none = _make_push_button("Clear", CLR_CARD_BORDER,
                                      CLR_TEXT_PRIMARY, min_h=28, bold=False)
        btn_all.setFixedHeight(28)
        btn_none.setFixedHeight(28)
        btn_all.clicked.connect(self._list_wells.selectAll)
        btn_none.clicked.connect(self._list_wells.clearSelection)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        vl.addLayout(btn_row)
        return card

    def _build_track_selector_card(self) -> QtWidgets.QFrame:
        card = GlowFrame(accent=CLR_ACCENT2, radius=10)
        vl = QtWidgets.QVBoxLayout(card)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        vl.addWidget(_section_label("Track Configuration"))

        track_options = [
            ("Track 1", ["GR", "SP", "CALI"]),
            ("Track 2", ["RHOB", "NPHI", "DT"]),
            ("Track 3", ["RT", "RES", "ILD"]),
            ("Track 4", ["PHIE", "VSH", "SW"]),
        ]
        self._track_combos: list[QtWidgets.QComboBox] = []
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        for i, (label, _ ) in enumerate(track_options):
            lbl = QtWidgets.QLabel(label)
            lbl.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 11px;")
            combo = QtWidgets.QComboBox()
            combo.addItems(["GR", "RHOB", "NPHI", "RT", "SP", "CALI", "DT",
                            "PHIE", "VSH", "SW", "PERM", "DTS", "None"])
            default_map = {"Track 1": "GR", "Track 2": "RHOB",
                           "Track 3": "RT", "Track 4": "PHIE"}
            combo.setCurrentText(default_map.get(label, "GR"))
            combo.setFixedHeight(28)
            self._track_combos.append(combo)
            grid.addWidget(lbl, i, 0)
            grid.addWidget(combo, i, 1)
        vl.addLayout(grid)

        # Track count
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("Visible Tracks:"))
        self._spin_tracks = QtWidgets.QSpinBox()
        self._spin_tracks.setRange(1, 6)
        self._spin_tracks.setValue(3)
        self._spin_tracks.setFixedWidth(60)
        self._spin_tracks.setFixedHeight(28)
        row2.addWidget(self._spin_tracks)
        row2.addStretch()
        vl.addLayout(row2)
        return card

    def _build_alignment_card(self) -> QtWidgets.QFrame:
        card = GlowFrame(accent=CLR_ACCENT3, radius=10)
        vl = QtWidgets.QVBoxLayout(card)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        vl.addWidget(_section_label("Alignment & Depth"))

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)

        # Datum
        lbl_datum = QtWidgets.QLabel("Datum:")
        lbl_datum.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 11px;")
        self._combo_datum = QtWidgets.QComboBox()
        self._combo_datum.addItems(["MD (Measured Depth)", "TVDSS", "TVDML",
                                     "Formation Top", "Sea Level"])
        self._combo_datum.setFixedHeight(28)
        grid.addWidget(lbl_datum, 0, 0)
        grid.addWidget(self._combo_datum, 0, 1)

        # Template
        lbl_tpl = QtWidgets.QLabel("Template:")
        lbl_tpl.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 11px;")
        self._combo_template = QtWidgets.QComboBox()
        self._combo_template.addItems([
            "Standard Triple Combo",
            "Formation Evaluation",
            "Resistivity Suite",
            "Porosity & Saturation",
            "Geomechanics Suite",
            "Custom",
        ])
        self._combo_template.setFixedHeight(28)
        grid.addWidget(lbl_tpl, 1, 0)
        grid.addWidget(self._combo_template, 1, 1)

        # Scale
        lbl_scale = QtWidgets.QLabel("Scale (ft):")
        lbl_scale.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 11px;")
        self._combo_scale = QtWidgets.QComboBox()
        self._combo_scale.addItems(["1:200", "1:500", "1:1000", "1:2000", "Auto"])
        self._combo_scale.setFixedHeight(28)
        grid.addWidget(lbl_scale, 2, 0)
        grid.addWidget(self._combo_scale, 2, 1)

        vl.addLayout(grid)

        # Depth range
        vl.addWidget(_section_label("Depth Range Override"))
        depth_row = QtWidgets.QHBoxLayout()
        self._spin_depth_from = QtWidgets.QDoubleSpinBox()
        self._spin_depth_from.setRange(0, 20000)
        self._spin_depth_from.setValue(0)
        self._spin_depth_from.setSuffix(" m")
        self._spin_depth_from.setFixedHeight(28)
        self._spin_depth_to = QtWidgets.QDoubleSpinBox()
        self._spin_depth_to.setRange(0, 20000)
        self._spin_depth_to.setValue(5000)
        self._spin_depth_to.setSuffix(" m")
        self._spin_depth_to.setFixedHeight(28)
        lbl_to = QtWidgets.QLabel("→")
        lbl_to.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 14px;")
        depth_row.addWidget(self._spin_depth_from)
        depth_row.addWidget(lbl_to)
        depth_row.addWidget(self._spin_depth_to)
        vl.addLayout(depth_row)
        return card

    def _build_display_options_card(self) -> QtWidgets.QFrame:
        card = GlowFrame(accent="#F5A623", radius=10)
        vl = QtWidgets.QVBoxLayout(card)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        vl.addWidget(_section_label("Display Options"))

        self._chk_markers    = self._make_check("Show Formation Markers", True)
        self._chk_sync_depth = self._make_check("Synchronize Depth Scrolling", True)
        self._chk_highlight  = self._make_check("Highlight Pay Zones", False)
        self._chk_fill_lt    = self._make_check("Lithology Track Fill", True)
        self._chk_grid       = self._make_check("Show Depth Grid", True)
        self._chk_headers    = self._make_check("Show Curve Headers", True)
        self._chk_legend     = self._make_check("Show Legend", True)
        self._chk_dark_mode  = self._make_check("Dark Canvas", True, checked=True)

        for chk in (self._chk_markers, self._chk_sync_depth, self._chk_highlight,
                    self._chk_fill_lt, self._chk_grid, self._chk_headers,
                    self._chk_legend, self._chk_dark_mode):
            vl.addWidget(chk)

        # Color scheme
        vl.addWidget(_section_label("Curve Color Scheme"))
        self._combo_colors = QtWidgets.QComboBox()
        self._combo_colors.addItems(
            ["Industry Standard", "Earth Tones", "Spectral", "Monochrome", "High Contrast"]
        )
        self._combo_colors.setFixedHeight(28)
        vl.addWidget(self._combo_colors)
        return card

    def _make_check(self, text: str, enabled: bool,
                    checked: bool = False) -> QtWidgets.QCheckBox:
        chk = QtWidgets.QCheckBox(text)
        chk.setEnabled(enabled)
        chk.setChecked(checked or enabled)
        return chk

    # ── Canvas area ───────────────────────────────────────────────────
    def _build_canvas_area(self) -> QtWidgets.QWidget:
        wrap = QtWidgets.QWidget()
        vl = QtWidgets.QVBoxLayout(wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)

        # Toolbar
        vl.addWidget(self._build_canvas_toolbar())

        # Canvas frame
        self._canvas_frame = GlowFrame(radius=12)
        self._canvas_frame.setStyleSheet(
            f"QFrame#GlowFrame {{"
            f"  background: #0A1520;"
            f"  border: 1px solid {CLR_CARD_BORDER};"
            f"  border-radius: 12px;"
            f"}}"
        )
        cf_layout = QtWidgets.QVBoxLayout(self._canvas_frame)
        cf_layout.setContentsMargins(0, 0, 0, 0)
        cf_layout.setSpacing(0)

        # Placeholder
        self._placeholder = self._build_placeholder()
        cf_layout.addWidget(self._placeholder)
        vl.addWidget(self._canvas_frame, stretch=1)
        return wrap

    def _build_canvas_toolbar(self) -> QtWidgets.QFrame:
        bar = QtWidgets.QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"QFrame {{"
            f"  background: {CLR_CARD};"
            f"  border: 1px solid {CLR_CARD_BORDER};"
            f"  border-radius: 10px;"
            f"}}"
        )
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        # Render button
        self._btn_render = AnimatedButton("⬛ Render Correlation Panel", CLR_BTN_RENDER)
        self._btn_render.setFixedHeight(38)
        self._btn_render.setMinimumWidth(230)
        self._btn_render.clicked.connect(self._on_render)
        h.addWidget(self._btn_render)

        h.addWidget(self._v_sep())

        # Export button
        btn_export = AnimatedButton("↗ Export PNG", CLR_BTN_EXPORT)
        btn_export.setFixedHeight(38)
        btn_export.setFixedWidth(130)
        btn_export.clicked.connect(self._on_export)
        h.addWidget(btn_export)

        # Export PDF
        btn_pdf = AnimatedButton("📄 PDF Report", "#9C27B0")
        btn_pdf.setFixedHeight(38)
        btn_pdf.setFixedWidth(130)
        btn_pdf.clicked.connect(self._on_export_pdf)
        h.addWidget(btn_pdf)

        h.addWidget(self._v_sep())

        # Clear
        btn_clear = _make_push_button("✕ Clear", CLR_BTN_CLEAR,
                                       CLR_TEXT_MUTED, min_h=38)
        btn_clear.setFixedHeight(38)
        btn_clear.setFixedWidth(80)
        btn_clear.clicked.connect(self._on_clear)
        h.addWidget(btn_clear)

        h.addStretch()

        # Right side: progress indicator
        self._lbl_progress = QtWidgets.QLabel("No data loaded")
        self._lbl_progress.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 11px;"
        )
        h.addWidget(self._lbl_progress)
        return bar

    def _v_sep(self) -> QtWidgets.QFrame:
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {CLR_CARD_BORDER};")
        return sep

    def _build_placeholder(self) -> QtWidgets.QFrame:
        ph = QtWidgets.QFrame()
        ph.setStyleSheet("QFrame { background: transparent; }")
        vl = QtWidgets.QVBoxLayout(ph)
        vl.setAlignment(QtCore.Qt.AlignCenter)
        vl.setSpacing(16)

        icon = QtWidgets.QLabel("⛳")
        icon.setStyleSheet(
            "font-size: 52px; background: transparent; color: #2A3F56;"
        )
        icon.setAlignment(QtCore.Qt.AlignCenter)
        vl.addWidget(icon)

        title = QtWidgets.QLabel("Multi-Well Correlation Canvas")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {CLR_TEXT_MUTED};"
            f"background: transparent;"
        )
        title.setAlignment(QtCore.Qt.AlignCenter)
        vl.addWidget(title)

        hint = QtWidgets.QLabel(
            "Select 2 or more wells from the sidebar,\n"
            "configure tracks and alignment, then click\n"
            "  Render Correlation Panel  to begin."
        )
        hint.setStyleSheet(
            f"font-size: 12px; color: #4A6480; background: transparent;"
        )
        hint.setAlignment(QtCore.Qt.AlignCenter)
        vl.addWidget(hint)

        # Quick-tip badges
        tips_row = QtWidgets.QHBoxLayout()
        tips_row.setAlignment(QtCore.Qt.AlignCenter)
        tips_row.setSpacing(8)
        for tip, color in (
            ("Ctrl+Click to multi-select", CLR_ACCENT),
            ("Shift+Click for range", CLR_ACCENT2),
            ("Right-click for context menu", CLR_ACCENT3),
        ):
            tips_row.addWidget(_tag_label(tip, color))
        vl.addLayout(tips_row)
        return ph

    # ── Status bar ────────────────────────────────────────────────────
    def _build_status_bar(self) -> QtWidgets.QFrame:
        bar = QtWidgets.QFrame()
        bar.setFixedHeight(34)
        bar.setStyleSheet(
            f"QFrame {{"
            f"  background: {CLR_PANEL};"
            f"  border: 1px solid {CLR_CARD_BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(0)
        self._lbl_status_left = QtWidgets.QLabel("Selected Wells: 0")
        self._lbl_status_left.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 11px;"
        )
        self._lbl_status_right = QtWidgets.QLabel(
            "Tip: Ctrl/Cmd+Click to select multiple wells"
        )
        self._lbl_status_right.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 11px;"
        )
        h.addWidget(self._lbl_status_left)
        h.addStretch()
        h.addWidget(self._lbl_status_right)
        return bar

    # ------------------------------------------------------------------
    # Data / interaction logic
    # ------------------------------------------------------------------
    def set_data_service(self, svc) -> None:
        self._data_service = svc
        self._refresh_well_list()

    def _refresh_well_list(self) -> None:
        self._list_wells.clear()
        wells: dict = {}
        if self._data_service is not None:
            wells = getattr(self._data_service, "_wells", {}) or {}

        well_names = sorted(wells.keys())
        self._lbl_well_count.setText(f"{len(well_names)} wells")
        self._set_metric(self._metric_wells_loaded, str(len(well_names)))

        for name in well_names:
            item = QtWidgets.QListWidgetItem()
            well = wells.get(name)
            df = getattr(well, "data", None)
            curve_cnt = len(df.columns) if df is not None else 0

            # Rich item with sub-text
            widget = self._make_well_item(name, curve_cnt)
            item.setSizeHint(widget.sizeHint())
            item.setData(QtCore.Qt.UserRole, name)
            self._list_wells.addItem(item)
            self._list_wells.setItemWidget(item, widget)

        self._update_status()

    def _make_well_item(self, name: str, curve_cnt: int) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet("background: transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(10)

        # Dot indicator
        dot = QtWidgets.QLabel("●")
        dot.setStyleSheet(f"color: {CLR_ACCENT3}; font-size: 10px; background: transparent;")
        h.addWidget(dot)

        # Name + curve count
        vl = QtWidgets.QVBoxLayout()
        vl.setSpacing(1)
        lbl_name = QtWidgets.QLabel(name)
        lbl_name.setStyleSheet(
            f"color: {CLR_TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
            f"background: transparent;"
        )
        lbl_info = QtWidgets.QLabel(f"{curve_cnt} curves")
        lbl_info.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        vl.addWidget(lbl_name)
        vl.addWidget(lbl_info)
        h.addLayout(vl)
        h.addStretch()

        # Curve count badge
        badge = _tag_label(f"{curve_cnt}", CLR_ACCENT)
        badge.setFixedWidth(36)
        h.addWidget(badge)
        return w

    def _filter_wells(self, text: str) -> None:
        text = text.strip().lower()
        for i in range(self._list_wells.count()):
            item = self._list_wells.item(i)
            name = str(item.data(QtCore.Qt.UserRole) or "").lower()
            item.setHidden(bool(text) and text not in name)

    def _on_well_selection_changed(self) -> None:
        selected_items = self._list_wells.selectedItems()
        self._selected_wells = [
            str(item.data(QtCore.Qt.UserRole))
            for item in selected_items
            if item.data(QtCore.Qt.UserRole)
        ]
        count = len(self._selected_wells)
        self._lbl_status_left.setText(f"Selected Wells: {count}")
        self._set_metric(self._metric_selected, str(count))

        # Update avg curves metric
        if self._data_service is not None and count > 0:
            wells = getattr(self._data_service, "_wells", {}) or {}
            total = 0
            valid = 0
            for wn in self._selected_wells:
                well = wells.get(wn)
                df = getattr(well, "data", None)
                if df is not None:
                    total += len(df.columns)
                    valid += 1
            avg = round(total / valid) if valid else 0
            self._set_metric(self._metric_curves, str(avg))

        self._update_status()

    def _update_status(self) -> None:
        count = len(self._selected_wells)
        if count == 0:
            self._lbl_status.setText("● Ready")
            self._lbl_status.setStyleSheet(
                f"background: {CLR_ACCENT3}33; color: {CLR_ACCENT3};"
                f"border: 1px solid {CLR_ACCENT3}55; border-radius: 5px;"
                f"padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )
        elif count == 1:
            self._lbl_status.setText("⚠ Select 2+")
            self._lbl_status.setStyleSheet(
                "background: #F5A62333; color: #F5A623;"
                "border: 1px solid #F5A62355; border-radius: 5px;"
                "padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )
        else:
            self._lbl_status.setText(f"● {count} Wells")
            self._lbl_status.setStyleSheet(
                f"background: {CLR_ACCENT}33; color: {CLR_ACCENT};"
                f"border: 1px solid {CLR_ACCENT}55; border-radius: 5px;"
                f"padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _on_render(self) -> None:
        if not self._selected_wells:
            QtWidgets.QMessageBox.information(
                self, "No Wells Selected",
                "Please select at least 2 wells from the sidebar before rendering."
            )
            return

        self._lbl_progress.setText("⏳ Rendering…")
        QtWidgets.QApplication.processEvents()

        try:
            self._render_correlation()
        except Exception as exc:
            self._lbl_progress.setText(f"Error: {exc}")
            QtWidgets.QMessageBox.warning(self, "Render Error", str(exc))
        finally:
            pass

    #                 # Headers
    #                 if self._chk_headers.isChecked():
    #                     ax.set_title(
    #                         f"{curve_name}",
    #                         color=CURVE_COLORS.get(curve_name.upper(), ("#00B4D8", None))[0],
    #                         fontsize=8, fontweight="700", pad=3
    #                     )

    #                 # Well label on first track
    #                 if t_idx == 0:
    #                     ax.set_ylabel(
    #                         wname, color=fg, fontsize=9, fontweight="700"
    #                     )

    #                 # Only show y ticks on first track per well
    #                 if t_idx > 0:
    #                     ax.set_yticks([])
    #                 else:
    #                     ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
    #                     ax.tick_params(axis='y', labelsize=7, labelcolor=fg)

    #                 ax.tick_params(axis='x', labelsize=6, labelcolor=fg, rotation=45)

    #             except Exception:
    #                 ax.text(0.5, 0.5, "Error", ha="center", va="center",
    #                         color="red", transform=ax.transAxes)

    #             ax_idx += 1

    #     # Well separation lines
    #     if self._chk_headers.isChecked() and n_tracks > 1:
    #         for sep_i in range(1, n_wells):
    #             sep_idx = sep_i * n_tracks
    #             if sep_idx < len(axes):
    #                 axes[sep_idx].spines["left"].set_edgecolor(CLR_ACCENT)
    #                 axes[sep_idx].spines["left"].set_linewidth(2)

    #     # Super title
    #     datum_text = self._combo_datum.currentText()
    #     fig.suptitle(
    #         f"Well Correlation Panel  ·  {n_wells} Wells  ·  {datum_text}",
    #         color=fg, fontsize=12, fontweight="800", y=1.01
    #     )
    #     fig.tight_layout(pad=0.5, h_pad=0.3, w_pad=0.1)

    #     self._embed_figure(fig)
    #     self._fig = fig
    #     self._lbl_progress.setText(
    #         f"✓ Rendered: {n_wells} wells × {n_tracks} tracks"
    #     )

    #     # Update depth metric
    #     try:
    #         span = depth_max - depth_min
    #         self._set_metric(self._metric_depth_range, f"{span:.0f}")
    #     except Exception:
    #         pass

    def _render_correlation(self) -> None:
        import matplotlib
        matplotlib.use("Qt5Agg")
    
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        import numpy as np
        import pandas as pd
    
        dark = self._chk_dark_mode.isChecked()
    
        bg = "#0A1520" if dark else "#FFFFFF"
        fg = "#C8D8E8" if dark else "#2A3A4A"
        grid_clr = "#1A2E42" if dark else "#E8EFF6"
    
        wells_data: list[tuple[str, Any, Any]] = []
    
        if self._data_service is not None:
            _wells = getattr(self._data_service, "_wells", {}) or {}
    
            for wn in self._selected_wells:
                well = _wells.get(wn)
                df = getattr(well, "data", None) if well is not None else None
                wells_data.append((wn, well, df))
    
        n_wells = len(wells_data) 
    
        track_curves = [
            cb.currentText()
            for cb in self._track_combos
            if cb.currentText() != "None"
        ]
    
        n_tracks = min(self._spin_tracks.value(), len(track_curves))
    
        if n_tracks < 1:
            n_tracks = 1
    
        fig_w = max(10.0, n_wells * n_tracks * 1.6 + 1.0)
        fig_h = 9.0
    
        fig, axes = plt.subplots(
            nrows=1,
            ncols=n_wells * n_tracks,
            figsize=(fig_w, fig_h),
            sharey=False,
        )
    
        fig.patch.set_facecolor(bg)
    
        if n_wells * n_tracks == 1:
            axes = [axes]
        else:
            axes = list(axes)
    
        depth_min = self._spin_depth_from.value()
        depth_max = self._spin_depth_to.value()
    
        CURVE_COLORS = {
            "GR":   ("#4CAF50", (0, 150)),
            "RHOB": ("#FF7043", (1.95, 2.95)),
            "NPHI": ("#29B6F6", (0.45, -0.15)),
            "RT":   ("#EF9A9A", (0.2, 2000)),
            "SP":   ("#CE93D8", (-160, 40)),
            "CALI": ("#FFCA28", (6, 16)),
            "DT":   ("#80DEEA", (40, 140)),
            "PHIE": ("#A5D6A7", (0, 0.4)),
            "VSH":  ("#FFCC80", (0, 1)),
            "SW":   ("#90CAF9", (0, 1)),
            "PERM": ("#F48FB1", (0.001, 1000)),
        }
    
        # ---------------------------------------------------------
        # STORE REFERENCE WELL DATA
        # ---------------------------------------------------------
        reference_data = {}
    
        ax_idx = 0
    
        for w_idx, (wname, well, df) in enumerate(wells_data):
    
            for t_idx in range(n_tracks):
    
                if ax_idx >= len(axes):
                    break
    
                ax = axes[ax_idx]
    
                ax.set_facecolor(bg)
    
                ax.tick_params(colors=fg, labelsize=7)
    
                for spine in ax.spines.values():
                    spine.set_edgecolor(grid_clr)
    
                if df is None or df.empty:
    
                    ax.text(
                        0.5,
                        0.5,
                        f"{wname}\n(no data)",
                        ha="center",
                        va="center",
                        color=fg,
                        fontsize=8,
                        transform=ax.transAxes,
                    )
    
                    ax.set_yticks([])
    
                    ax_idx += 1
                    continue
    
                curve_name = (
                    track_curves[t_idx]
                    if t_idx < len(track_curves)
                    else "GR"
                )
    
                # ---------------------------------------------------------
                # FIND DEPTH COLUMN
                # ---------------------------------------------------------
                depth_col = None
    
                for cname in df.columns:
                    if str(cname).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                        depth_col = cname
                        break
    
                if depth_col is None:
                    depth_col = df.columns[0]
    
                try:
    
                    depth = pd.to_numeric(
                        df[depth_col],
                        errors="coerce"
                    )
    
                    mask = (
                        (depth >= depth_min)
                        & (depth <= depth_max)
                    )
    
                    if mask.sum() == 0:
                        mask = pd.Series([True] * len(df))
    
                    depth_plot = depth[mask].values
    
                    if curve_name in df.columns:
    
                        vals = pd.to_numeric(
                            df[curve_name],
                            errors="coerce"
                        )[mask].values
    
                        c_color, x_range = CURVE_COLORS.get(
                            curve_name.upper(),
                            ("#00B4D8", (None, None))
                        )
    
                        # ---------------------------------------------------------
                        # PLOT CURVE
                        # ---------------------------------------------------------
                        ax.plot(
                            vals,
                            depth_plot,
                            color=c_color,
                            linewidth=0.9,
                            alpha=0.92,
                        )
    
                        # ---------------------------------------------------------
                        # FILL
                        # ---------------------------------------------------------
                        if self._chk_fill_lt.isChecked():
    
                            ax.fill_betweenx(
                                depth_plot,
                                vals,
                                alpha=0.12,
                                color=c_color
                            )
    
                        # ---------------------------------------------------------
                        # X LIMIT
                        # ---------------------------------------------------------
                        if x_range[0] is not None:
                            ax.set_xlim(*x_range)
    
                        # ---------------------------------------------------------
                        # FORMATION MARKERS
                        # ---------------------------------------------------------
                        if (
                            self._chk_markers.isChecked()
                            and len(depth_plot) > 10
                        ):
    
                            n_markers = min(
                                4,
                                max(1, len(depth_plot) // 200)
                            )
    
                            for midx in np.linspace(
                                0,
                                len(depth_plot) - 1,
                                n_markers,
                                dtype=int
                            ):
    
                                d = depth_plot[midx]
    
                                ax.axhline(
                                    d,
                                    color="#F5A623",
                                    linewidth=0.6,
                                    linestyle="--",
                                    alpha=0.55,
                                )
    
                        # ---------------------------------------------------------
                        # PAY ZONE HIGHLIGHT
                        # ---------------------------------------------------------
                        if self._chk_highlight.isChecked():
    
                            if curve_name.upper() in {"PHIE", "SW"}:
    
                                threshold = (
                                    0.1
                                    if curve_name.upper() == "PHIE"
                                    else 0.5
                                )
    
                                compare = (
                                    vals > threshold
                                    if curve_name.upper() == "PHIE"
                                    else vals < threshold
                                )
    
                                ax.fill_betweenx(
                                    depth_plot,
                                    x_range[0] or vals.min(),
                                    x_range[1] or vals.max(),
                                    where=compare,
                                    color="#FFD700",
                                    alpha=0.08,
                                )
    
                        # ---------------------------------------------------------
                        # STORE FIRST WELL AS REFERENCE
                        # ---------------------------------------------------------
                        corr_percent = None
    
                        if w_idx == 0:
    
                            reference_data[curve_name] = (
                                depth_plot.copy(),
                                vals.copy()
                            )
    
                        else:
    
                            if curve_name in reference_data:
    
                                ref_depth, ref_vals = reference_data[curve_name]
    
                                try:
    
                                    common_depth = np.linspace(
                                        max(
                                            np.nanmin(ref_depth),
                                            np.nanmin(depth_plot)
                                        ),
                                        min(
                                            np.nanmax(ref_depth),
                                            np.nanmax(depth_plot)
                                        ),
                                        1000
                                    )
    
                                    ref_interp = np.interp(
                                        common_depth,
                                        ref_depth,
                                        ref_vals
                                    )
    
                                    vals_interp = np.interp(
                                        common_depth,
                                        depth_plot,
                                        vals
                                    )
    
                                    valid = (
                                        np.isfinite(ref_interp)
                                        & np.isfinite(vals_interp)
                                    )
    
                                    if valid.sum() > 10:
    
                                        corr = np.corrcoef(
                                            ref_interp[valid],
                                            vals_interp[valid]
                                        )[0, 1]
    
                                        corr_percent = corr * 100
    
                                except Exception:
                                    pass
    
                        # ---------------------------------------------------------
                        # CORRELATION BADGE
                        # ---------------------------------------------------------
                        if corr_percent is not None:
    
                            if corr_percent >= 80:
                                corr_color = "#00E676"
    
                            elif corr_percent >= 60:
                                corr_color = "#FFD54F"
    
                            else:
                                corr_color = "#FF5252"
    
                            ax.text(
                                0.03,
                                0.97,
                                f"{corr_percent:.1f}%",
                                transform=ax.transAxes,
                                fontsize=7,
                                fontweight="bold",
                                va="top",
                                ha="left",
                                color=corr_color,
                                bbox=dict(
                                    boxstyle="round,pad=0.25",
                                    fc="#102530" if dark else "#F3F7FA",
                                    ec=corr_color,
                                    lw=0.8,
                                    alpha=0.95,
                                ),
                            )
    
                    else:
    
                        ax.text(
                            0.5,
                            0.5,
                            f"{curve_name}\n(N/A)",
                            ha="center",
                            va="center",
                            color=fg,
                            fontsize=8,
                            transform=ax.transAxes,
                        )
    
                    # ---------------------------------------------------------
                    # DEPTH AXIS
                    # ---------------------------------------------------------
                    if (
                        len(depth_plot) > 1
                        and depth_plot[-1] > depth_plot[0]
                    ):
    
                        ax.set_ylim(
                            depth_plot.max(),
                            depth_plot.min()
                        )
    
                    else:
                        ax.invert_yaxis()
    
                    # ---------------------------------------------------------
                    # GRID
                    # ---------------------------------------------------------
                    if self._chk_grid.isChecked():
    
                        ax.grid(
                            axis="y",
                            color=grid_clr,
                            linewidth=0.4,
                            alpha=0.6,
                        )
    
                        ax.grid(
                            axis="x",
                            color=grid_clr,
                            linewidth=0.3,
                            alpha=0.4,
                        )
    
                    # ---------------------------------------------------------
                    # TITLES
                    # ---------------------------------------------------------
                    if self._chk_headers.isChecked():
    
                        ax.set_title(
                            f"{curve_name}",
                            color=CURVE_COLORS.get(
                                curve_name.upper(),
                                ("#00B4D8", None)
                            )[0],
                            fontsize=8,
                            fontweight="700",
                            pad=3,
                        )
    
                    # ---------------------------------------------------------
                    # WELL LABEL
                    # ---------------------------------------------------------
                    if t_idx == 0:
    
                        ax.set_ylabel(
                            wname,
                            color=fg,
                            fontsize=9,
                            fontweight="700",
                        )
    
                    # ---------------------------------------------------------
                    # Y TICKS
                    # ---------------------------------------------------------
                    if t_idx > 0:
    
                        ax.set_yticks([])
    
                    else:
    
                        ax.yaxis.set_major_formatter(
                            ticker.FormatStrFormatter("%.0f")
                        )
    
                        ax.tick_params(
                            axis='y',
                            labelsize=7,
                            labelcolor=fg
                        )
    
                    ax.tick_params(
                        axis='x',
                        labelsize=6,
                        labelcolor=fg,
                        rotation=45,
                    )
    
                except Exception:
    
                    ax.text(
                        0.5,
                        0.5,
                        "Error",
                        ha="center",
                        va="center",
                        color="red",
                        transform=ax.transAxes,
                    )
    
                ax_idx += 1
    
        # ---------------------------------------------------------
        # WELL SEPARATION
        # ---------------------------------------------------------
        if self._chk_headers.isChecked() and n_tracks > 1:
    
            for sep_i in range(1, n_wells):
    
                sep_idx = sep_i * n_tracks
    
                if sep_idx < len(axes):
    
                    axes[sep_idx].spines["left"].set_edgecolor(CLR_ACCENT)
                    axes[sep_idx].spines["left"].set_linewidth(2)
    
        # ---------------------------------------------------------
        # SUPER TITLE
        # ---------------------------------------------------------
        datum_text = self._combo_datum.currentText()
    
        fig.suptitle(
            f"Well Correlation Panel  ·  "
            f"{n_wells} Wells  ·  "
            f"{datum_text}",
            color=fg,
            fontsize=12,
            fontweight="800",
            y=1.01,
        )
    
        fig.tight_layout(
            pad=0.5,
            h_pad=0.3,
            w_pad=0.1,
        )
    
        self._embed_figure(fig)
    
        self._fig = fig
    
        self._lbl_progress.setText(
            f"✓ Rendered: {n_wells} wells × {n_tracks} tracks"
        )
    
        # ---------------------------------------------------------
        # UPDATE METRIC
        # ---------------------------------------------------------
        try:
    
            span = depth_max - depth_min
    
            self._set_metric(
                self._metric_depth_range,
                f"{span:.0f}"
            )
    
        except Exception:
            pass

    def _embed_figure(self, fig) -> None:
        try:
            from matplotlib.backends.backend_qt5agg import (
                FigureCanvasQTAgg as FigureCanvas,
                NavigationToolbar2QT as NavToolbar,
            )
        except ImportError:
            return

        layout = self._canvas_frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self._canvas_frame)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        # Remove old widgets
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        # Toolbar
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background: #0A1520;")
        toolbar = NavToolbar(canvas, self._canvas_frame)
        toolbar.setStyleSheet(
            "QToolBar { background: #0D1F30; border: none;"
            "border-bottom: 1px solid #1A3A56; }"
            "QToolButton { background: transparent; color: #7B9AB5; }"
            "QToolButton:hover { background: #1C2D3F; border-radius: 4px; }"
        )
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        self._canvas = canvas
        try:
            from plotting.plot_context_menu import install_plot_context_menu
            install_plot_context_menu(canvas, fig, self._canvas_frame)
        except Exception:
            pass

    # ── Export handlers ───────────────────────────────────────────────
    def _on_export(self) -> None:
        if self._fig is None:
            QtWidgets.QMessageBox.information(
                self, "Nothing to Export",
                "Render a correlation panel first."
            )
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export PNG", "well_correlation.png",
            "PNG Image (*.png);;All Files (*)"
        )
        if path:
            self._fig.savefig(path, dpi=200, bbox_inches="tight",
                              facecolor=self._fig.get_facecolor())
            QtWidgets.QMessageBox.information(
                self, "Exported", f"Saved to:\n{path}"
            )

    def _on_export_pdf(self) -> None:
        if self._fig is None:
            QtWidgets.QMessageBox.information(
                self, "Nothing to Export",
                "Render a correlation panel first."
            )
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export PDF", "well_correlation.pdf",
            "PDF Document (*.pdf);;All Files (*)"
        )
        if path:
            self._fig.savefig(path, format="pdf", bbox_inches="tight",
                              facecolor=self._fig.get_facecolor())
            QtWidgets.QMessageBox.information(
                self, "Exported", f"Saved to:\n{path}"
            )

    def _on_clear(self) -> None:
        self._fig = None
        self._canvas = None
        layout = self._canvas_frame.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            layout.addWidget(self._placeholder)
            self._placeholder.show()
        self._lbl_progress.setText("Canvas cleared")
        self._set_metric(self._metric_depth_range, "—")
