from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

ROOT_DIR = Path(__file__).resolve().parent.parent

TRACK_COLOR_CYCLE = [
    "#2563EB",
    "#059669",
    "#DC2626",
    "#7C3AED",
    "#D97706",
    "#0891B2",
]

WELL_COLOR_CYCLE = [
    "#2563EB",
    "#0F766E",
    "#7C3AED",
    "#DC2626",
    "#D97706",
    "#0891B2",
    "#65A30D",
]

CURVE_DEFAULTS = {
    "GR": {"min": 0.0, "max": 150.0, "color": "#4CAF50", "scale": "Linear"},
    "RHOB": {"min": 1.95, "max": 2.95, "color": "#FF7043", "scale": "Linear"},
    "NPHI": {"min": 0.45, "max": -0.15, "color": "#29B6F6", "scale": "Linear"},
    "RT": {"min": 0.2, "max": 2000.0, "color": "#EF9A9A", "scale": "Logarithmic"},
    "SP": {"min": -160.0, "max": 40.0, "color": "#CE93D8", "scale": "Linear"},
    "CALI": {"min": 6.0, "max": 16.0, "color": "#FFCA28", "scale": "Linear"},
    "DT": {"min": 40.0, "max": 140.0, "color": "#80DEEA", "scale": "Linear"},
    "PHIE": {"min": 0.0, "max": 0.4, "color": "#A5D6A7", "scale": "Linear"},
    "VSH": {"min": 0.0, "max": 1.0, "color": "#FFCC80", "scale": "Linear"},
    "SW": {"min": 0.0, "max": 1.0, "color": "#90CAF9", "scale": "Linear"},
    "PERM": {"min": 0.001, "max": 1000.0, "color": "#F48FB1", "scale": "Logarithmic"},
}

PICKS_HEADERS = [
    "Well",
    "Formation",
    "MD (m)",
    "TVD (m)",
    "TVDSS (m)",
    "GR (API)",
    "RHOB (g/cc)",
    "RT (ohm.m)",
    "Vsh (v/v)",
    "Confidence",
    "Picked By",
    "Notes",
]


@dataclass
class TrackConfig:
    name: str
    curve_label: str
    width_px: int = 120
    scale: str = "Linear"
    min_value: float = 0.0
    max_value: float = 150.0
    fill: str = "None"
    color: str = "#2563EB"
    line_width: float = 1.0


@dataclass
class PickRecord:
    well_name: str
    formation: str
    md: float
    tvd: float
    tvdss: float
    gr: float | None
    rhob: float | None
    rt: float | None
    vsh: float | None
    confidence: str
    picked_by: str
    notes: str


class MultiWellCorrelationWorkspaceController(QtCore.QObject):
    def __init__(self, window: QtWidgets.QMainWindow, workspace: QtWidgets.QMainWindow):
        super().__init__(workspace)
        self.window = window
        self.workspace = workspace
        self._tracks: list[TrackConfig] = []
        self._selected_wells: list[str] = []
        self._well_colors: dict[str, str] = {}
        self._well_datums: dict[str, str] = {}
        self._well_kb: dict[str, float] = {}
        self._well_shifts: dict[str, float] = {}
        self._zones: list[dict[str, str]] = []
        self._picks: list[PickRecord] = []
        self._fig = None
        self._canvas = None
        self._minimap_fig = None
        self._minimap_canvas = None
        self._axes_meta: dict[int, dict[str, Any]] = {}
        self._current_pick: dict[str, Any] | None = None
        self._mode = "pan"
        self._signals_ready = False
        self._track_curve_choices: list[str] = ["GR", "RHOB", "NPHI", "RT"]

        self._initialize_ui()
        self.connect_signals()
        self.refresh()

    def set_data_service(self, svc) -> None:
        self.window._data_service = svc
        self.refresh()

    def refresh(self) -> None:
        self._populate_well_tree()
        self._populate_track_curve_choices()
        self._populate_track_list()
        self._populate_zone_tree()
        self._populate_pick_filters()
        self._sync_depth_controls()
        self._update_headers()
        self._update_counts()
        self._update_selected_well_panel()
        self._update_track_form()
        self._render_correlation()

    def connect_signals(self) -> None:
        if self._signals_ready:
            return
        self._signals_ready = True

        self._widget("editSearchWells").textChanged.connect(self._filter_wells)
        self._widget("treeWells").itemChanged.connect(self._on_tree_item_changed)
        self._widget("treeWells").itemSelectionChanged.connect(self._on_tree_selection_changed)

        self._connect_button("btnAddWell", self._add_selected_wells)
        self._connect_button("btnRemoveWell", self._remove_selected_wells)
        self._connect_button("btnWellMoveLeft", lambda: self._move_selected_well(-1))
        self._connect_button("btnWellMoveRight", lambda: self._move_selected_well(1))
        self._connect_button("btnWellSortByLocation", self._sort_wells_by_location)
        self._connect_button("btnWellColor", self._pick_selected_well_color)

        self._connect_signal("dspinKB", "valueChanged", self._on_well_property_changed)
        self._connect_signal("cmbWellDatum", "currentTextChanged", self._on_well_property_changed)
        self._connect_signal("dspinGlobalShift", "valueChanged", lambda _v: self._render_correlation())
        self._connect_signal("dspinWellShift", "valueChanged", self._on_well_shift_changed)
        self._connect_signal("cmbAlignReference", "currentTextChanged", lambda _v: self._render_correlation())

        self._widget("listTracks").currentRowChanged.connect(self._update_track_form)
        self._connect_button("btnAddTrack", self._add_track)
        self._connect_button("btnRemoveTrack", self._remove_track)
        self._connect_button("btnMoveTrackLeft", lambda: self._move_track(-1))
        self._connect_button("btnMoveTrackRight", lambda: self._move_track(1))
        self._connect_button("btnTrackColor", self._pick_track_color)
        self._connect_button("btnApplyTrackConfig", self._apply_track_form)

        self._connect_button("btnImportTops", self._import_tops_csv)
        self._connect_button("btnAddZone", self._add_zone)
        self._connect_button("btnRemoveZone", self._remove_zone)
        self._connect_button("btnZoneColor", self._pick_zone_color)
        self._connect_button("btnClearPicks", self._clear_picks)
        self._widget("treeZones").itemSelectionChanged.connect(self._update_pick_formation_choices)

        self._connect_button("btnAutoCorrelate", self._auto_correlate)
        self._connect_button("btnConfirmPick", self._confirm_current_pick)
        self._connect_button("btnDeletePick", self._delete_current_pick)

        self._connect_button("btnApplyDisplay", self._render_correlation)
        for name in (
            "chkShowDepthGrid",
            "chkShowMajorGrid",
            "chkShowMinorGrid",
            "chkShowWellNames",
            "chkShowFormationNames",
            "chkShowDepthLabels",
            "chkShowCurveHeaders",
            "chkShowPickValues",
            "chkAlternateTrackBg",
            "rdoBgWhite",
            "rdoBgCream",
            "rdoBgCustom",
            "chkAutoPropagate",
            "chkSnapToLog",
            "chkInterpolateUncertain",
        ):
            self._connect_signal(name, "toggled", lambda _checked: self._render_correlation())

        for name in (
            "dspinMajorGrid",
            "dspinMinorGrid",
            "spinLabelFontSize",
            "dspinCorrelLineWidth",
            "sliderZoneFillOpacity",
            "dspinSnapWindow",
            "dspinDepthFrom",
            "dspinDepthTo",
        ):
            self._connect_signal(name, "valueChanged", self._on_depth_spin_changed)

        self._connect_signal("sliderDepthTop", "valueChanged", self._on_depth_slider_changed)
        self._connect_signal("sliderDepthBottom", "valueChanged", self._on_depth_slider_changed)
        self._connect_signal("sliderZoomLevel", "valueChanged", self._on_zoom_changed)

        self._connect_button("btnZoomIn", lambda: self._nudge_zoom(10))
        self._connect_button("btnZoomOut", lambda: self._nudge_zoom(-10))
        self._connect_button("btnZoomFitAll", self._fit_all_depth)
        self._connect_button("btnZoom200m", lambda: self._set_depth_window(200.0))
        self._connect_button("btnZoom500m", lambda: self._set_depth_window(500.0))
        self._connect_button("btnFitAll", self._fit_all_depth)

        self._connect_button("btnExportPreview", self._preview_export)
        self._connect_button("btnExport", self._export_current_view)
        self._connect_button("btnPicksExportCSV", self._export_picks_csv)
        self._connect_button("btnPicksClearAll", self._clear_picks)
        self._connect_signal("cmbPicksFilterZone", "currentTextChanged", lambda _v: self._populate_picks_table())
        self._connect_signal("cmbPicksFilterWell", "currentTextChanged", lambda _v: self._populate_picks_table())

        self._connect_mode_button("btnModePan", "pan")
        self._connect_mode_button("btnModeZoom", "zoom")
        self._connect_mode_button("btnModePick", "pick")
        self._connect_mode_button("btnModeCorrelate", "correlate")
        self._connect_mode_button("btnModeMeasure", "measure")

        for action_name, handler in (
            ("actionImportLAS", self._import_wells),
            ("actionImportTops", self._import_tops_csv),
            ("actionAutoCorrelate", self._auto_correlate),
            ("actionExportPDF", lambda: self._export_figure("pdf")),
            ("actionExportSVG", lambda: self._export_figure("svg")),
            ("actionExportCSV", self._export_picks_csv),
            ("actionFitAll", self._fit_all_depth),
            ("actionZoomIn", lambda: self._nudge_zoom(10)),
            ("actionZoomOut", lambda: self._nudge_zoom(-10)),
            ("actionAddWell", self._add_selected_wells),
            ("actionRemoveWell", self._remove_selected_wells),
            ("actionSelectAllWells", self._select_all_wells),
            ("actionSortByLocation", self._sort_wells_by_location),
            ("actionToggleLeftPanel", lambda: self._toggle_panel("frameLeft")),
            ("actionToggleRightPanel", lambda: self._toggle_panel("frameRight")),
            ("actionTogglePicksTable", self._toggle_picks_dock),
            ("actionDeleteSelectedPicks", self._delete_selected_pick_rows),
            ("actionShowDepthGrid", self._toggle_depth_grid),
            ("actionExit", lambda: None),
        ):
            self._connect_action(action_name, handler)

    def _initialize_ui(self) -> None:
        self.workspace.setWindowFlags(QtCore.Qt.Widget)
        self.workspace.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks | QtWidgets.QMainWindow.AllowTabbedDocks)

        tree = self._widget("treeWells")
        tree.setHeaderLabels(["Well / Curve", "Status"])
        tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        self._widget("tableCorrelationPicks").setHorizontalHeaderLabels(PICKS_HEADERS)
        table = self._widget("tableCorrelationPicks")
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        button_group = QtWidgets.QButtonGroup(self.workspace)
        button_group.setExclusive(True)
        for name in ("btnModePan", "btnModeZoom", "btnModePick", "btnModeCorrelate", "btnModeMeasure"):
            button = self._widget(name)
            button_group.addButton(button)
        self._widget("btnModePan").setChecked(True)

        self._tracks = [
            self._default_track(1, "GR"),
            self._default_track(2, "RHOB"),
            self._default_track(3, "RT"),
        ]
        self._zones = [
            {"name": "Reservoir Top", "color": "#2563EB"},
            {"name": "Reservoir Base", "color": "#DC2626"},
        ]
        self._set_text("lblZoomValue", "100%")
        self._update_pick_formation_choices()

    def _default_track(self, index: int, curve_label: str) -> TrackConfig:
        token = self._curve_token(curve_label)
        defaults = CURVE_DEFAULTS.get(token, {"min": 0.0, "max": 150.0, "color": TRACK_COLOR_CYCLE[(index - 1) % len(TRACK_COLOR_CYCLE)], "scale": "Linear"})
        return TrackConfig(
            name=f"Track {index}",
            curve_label=curve_label,
            width_px=120,
            scale=defaults["scale"],
            min_value=float(defaults["min"]),
            max_value=float(defaults["max"]),
            fill="None",
            color=str(defaults["color"]),
            line_width=1.0,
        )

    def _widget(self, name: str):
        return self.workspace.findChild(QtCore.QObject, name)

    def _connect_button(self, name: str, handler) -> None:
        button = self._widget(name)
        if button is not None and hasattr(button, "clicked"):
            button.clicked.connect(handler)

    def _connect_signal(self, name: str, signal_name: str, handler) -> None:
        widget = self._widget(name)
        if widget is None:
            return
        signal = getattr(widget, signal_name, None)
        if signal is not None:
            signal.connect(handler)

    def _connect_action(self, name: str, handler) -> None:
        action = self._widget(name)
        if action is not None and hasattr(action, "triggered"):
            action.triggered.connect(handler)

    def _connect_mode_button(self, name: str, mode: str) -> None:
        button = self._widget(name)
        if button is not None:
            button.clicked.connect(lambda checked=False, target=mode: self._set_mode(target))

    def _data_service(self):
        data_service = getattr(self.window, "_data_service", None)
        if data_service is None:
            controller = getattr(self.window, "controller", None)
            data_service = getattr(controller, "data", None) if controller is not None else None
        return data_service

    def _wells(self) -> dict[str, Any]:
        data_service = self._data_service()
        return getattr(data_service, "_wells", {}) or {}

    def _selected_top_level_item(self):
        tree = self._widget("treeWells")
        for item in tree.selectedItems():
            if item.parent() is None:
                return item
            return item.parent()
        return None

    def _selected_well_name(self) -> str | None:
        item = self._selected_top_level_item()
        return item.text(0) if item is not None else None

    def _populate_well_tree(self) -> None:
        tree = self._widget("treeWells")
        wells = self._wells()
        ordered_names = self._selected_wells + [name for name in sorted(wells) if name not in self._selected_wells]
        current_name = self._selected_well_name()

        blocker = QtCore.QSignalBlocker(tree)
        tree.clear()
        for index, name in enumerate(ordered_names):
            well = wells.get(name)
            if well is None:
                continue
            df = getattr(well, "data", None)
            item = QtWidgets.QTreeWidgetItem([name, "Shown" if name in self._selected_wells else "Hidden"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(0, QtCore.Qt.Checked if name in self._selected_wells else QtCore.Qt.Unchecked)
            item.setData(0, QtCore.Qt.UserRole, name)
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(self._well_colors.get(name, self._well_color(name, index)))))
            tree.addTopLevelItem(item)

            for curve in list(getattr(df, "columns", []))[:24]:
                child = QtWidgets.QTreeWidgetItem([str(curve), "Curve"])
                child.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                item.addChild(child)

            if current_name == name:
                tree.setCurrentItem(item)
        del blocker

        if not self._selected_wells and ordered_names:
            first = ordered_names[0]
            self._selected_wells = [first]
            if tree.topLevelItemCount():
                first_item = tree.topLevelItem(0)
                first_item.setCheckState(0, QtCore.Qt.Checked)

    def _populate_track_curve_choices(self) -> None:
        curves = set()
        for well in self._wells().values():
            df = getattr(well, "data", None)
            if df is None:
                continue
            for column in df.columns:
                series = pd.to_numeric(df[column], errors="coerce")
                if series.notna().sum() > 1:
                    curves.add(str(column))

        ranked = ["(none)", *sorted(curves)]
        if len(ranked) == 1:
            ranked.extend(["GR", "RHOB", "NPHI", "RT"])
        self._track_curve_choices = ranked

        combo = self._widget("cmbTrackCurve")
        current = combo.currentText()
        blocker = QtCore.QSignalBlocker(combo)
        combo.clear()
        combo.addItems(ranked)
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        del blocker

    def _populate_track_list(self) -> None:
        widget = self._widget("listTracks")
        current_row = widget.currentRow()
        blocker = QtCore.QSignalBlocker(widget)
        widget.clear()
        for track in self._tracks:
            widget.addItem(f"{track.name}  |  {track.curve_label}")
        del blocker
        if self._tracks:
            widget.setCurrentRow(max(0, min(current_row, len(self._tracks) - 1)))

    def _populate_zone_tree(self) -> None:
        tree = self._widget("treeZones")
        blocker = QtCore.QSignalBlocker(tree)
        tree.clear()
        tree.setHeaderLabels(["Zone", "Color"])
        for zone in self._zones:
            item = QtWidgets.QTreeWidgetItem([zone["name"], zone["color"]])
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(zone["color"])))
            item.setForeground(1, QtGui.QBrush(QtGui.QColor(zone["color"])))
            tree.addTopLevelItem(item)
        del blocker
        self._update_pick_formation_choices()

    def _populate_pick_filters(self) -> None:
        for combo_name, values in (
            ("cmbPicksFilterZone", ["All zones", *sorted({pick.formation for pick in self._picks})]),
            ("cmbPicksFilterWell", ["All wells", *sorted({pick.well_name for pick in self._picks})]),
        ):
            combo = self._widget(combo_name)
            current = combo.currentText()
            blocker = QtCore.QSignalBlocker(combo)
            combo.clear()
            combo.addItems(values)
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            del blocker
        self._populate_picks_table()

    def _populate_picks_table(self) -> None:
        table = self._widget("tableCorrelationPicks")
        zone_filter = self._widget("cmbPicksFilterZone").currentText()
        well_filter = self._widget("cmbPicksFilterWell").currentText()

        filtered = []
        for pick in self._picks:
            if zone_filter != "All zones" and pick.formation != zone_filter:
                continue
            if well_filter != "All wells" and pick.well_name != well_filter:
                continue
            filtered.append(pick)

        table.setSortingEnabled(False)
        table.setRowCount(len(filtered))
        for row, pick in enumerate(filtered):
            values = [
                pick.well_name,
                pick.formation,
                f"{pick.md:,.2f}",
                f"{pick.tvd:,.2f}",
                f"{pick.tvdss:,.2f}",
                self._fmt_optional(pick.gr),
                self._fmt_optional(pick.rhob),
                self._fmt_optional(pick.rt),
                self._fmt_optional(pick.vsh),
                pick.confidence,
                pick.picked_by,
                pick.notes,
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                table.setItem(row, col, item)
        table.setSortingEnabled(True)

    def _sync_depth_controls(self) -> None:
        top_slider = self._widget("sliderDepthTop")
        bottom_slider = self._widget("sliderDepthBottom")
        top_spin = self._widget("dspinDepthFrom")
        bottom_spin = self._widget("dspinDepthTo")

        min_depth, max_depth = self._depth_bounds()
        slider_max = max(100, int(np.ceil(max_depth)))
        for slider in (top_slider, bottom_slider):
            slider.blockSignals(True)
            slider.setMinimum(int(np.floor(min_depth)))
            slider.setMaximum(slider_max)
            slider.blockSignals(False)

        top_value = max(min_depth, min(float(top_spin.value()), max_depth))
        bottom_value = max(top_value + 1.0, min(float(bottom_spin.value()), max_depth))

        top_spin.blockSignals(True)
        bottom_spin.blockSignals(True)
        top_slider.blockSignals(True)
        bottom_slider.blockSignals(True)
        top_spin.setValue(top_value)
        bottom_spin.setValue(bottom_value)
        top_slider.setValue(int(round(top_value)))
        bottom_slider.setValue(int(round(bottom_value)))
        top_spin.blockSignals(False)
        bottom_spin.blockSignals(False)
        top_slider.blockSignals(False)
        bottom_slider.blockSignals(False)

        self._set_text("lblDepthSliderFrom", f"{top_value:,.0f} m")
        self._set_text("lblDepthSliderTo", f"{bottom_value:,.0f} m")

    def _depth_bounds(self) -> tuple[float, float]:
        depths = []
        for name in self._selected_wells or sorted(self._wells()):
            well = self._wells().get(name)
            if well is None:
                continue
            frame = self._depth_frame(well)
            if frame is None or frame.empty:
                continue
            depths.append(float(frame["display"].min()))
            depths.append(float(frame["display"].max()))
        if not depths:
            return 0.0, 3000.0
        return max(0.0, min(depths)), max(depths)

    def _update_headers(self) -> None:
        layout = self._widget("wellHeadersContainerLayout")
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        if not self._selected_wells:
            placeholder = QtWidgets.QLabel("Load wells to begin correlation")
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            placeholder.setStyleSheet("color:#94A3B8; font-size:11px; padding:8px;")
            layout.addWidget(placeholder)
            layout.addStretch(1)
            return

        show_names = self._is_checked("chkShowWellNames", True)
        for index, name in enumerate(self._selected_wells):
            frame = QtWidgets.QFrame()
            frame.setMinimumWidth(max(110, sum(track.width_px for track in self._tracks) // max(len(self._tracks), 1)))
            frame.setStyleSheet(
                "background:#FFFFFF;border-right:1px solid #D1D9E6;border-bottom:1px solid #D1D9E6;"
            )
            v = QtWidgets.QVBoxLayout(frame)
            v.setContentsMargins(8, 4, 8, 4)
            title = QtWidgets.QLabel(name if show_names else f"Well {index + 1}")
            title.setAlignment(QtCore.Qt.AlignCenter)
            title.setStyleSheet(f"font-weight:700; color:{self._well_colors.get(name, self._well_color(name, index))};")
            subtitle = QtWidgets.QLabel(" | ".join(track.curve_label for track in self._tracks))
            subtitle.setAlignment(QtCore.Qt.AlignCenter)
            subtitle.setStyleSheet("font-size:9px; color:#64748B;")
            v.addWidget(title)
            v.addWidget(subtitle)
            layout.addWidget(frame)
        layout.addStretch(1)

    def _update_counts(self) -> None:
        self._set_text("lblWellCount", f"Wells: {len(self._selected_wells)}")
        self._set_text("lblZoneCount", f"Zones: {len(self._zones)}")
        self._set_text("lblPickCount", f"Picks: {len(self._picks)}")
        self._set_text("lblStatWellsPicked", f"{len({pick.well_name for pick in self._picks})} / {max(len(self._selected_wells), 1)}")
        self._update_zone_stats()

    def _update_zone_stats(self) -> None:
        if not self._picks:
            self._set_text("lblStatAvgThick", "—  m")
            self._set_text("lblStatMaxThick", "—  m")
            self._set_text("lblStatDip", "—  °")
            return
        grouped: dict[str, list[PickRecord]] = {}
        for pick in self._picks:
            grouped.setdefault(pick.formation, []).append(pick)
        spreads = []
        for picks in grouped.values():
            values = [pick.md for pick in picks]
            if len(values) > 1:
                spreads.append(max(values) - min(values))
        if spreads:
            self._set_text("lblStatAvgThick", f"{np.mean(spreads):,.1f}  m")
            self._set_text("lblStatMaxThick", f"{np.max(spreads):,.1f}  m")
            self._set_text("lblStatDip", f"{min(89.9, np.mean(spreads) / 20.0):,.1f}  °")
        else:
            self._set_text("lblStatAvgThick", "0.0  m")
            self._set_text("lblStatMaxThick", "0.0  m")
            self._set_text("lblStatDip", "0.0  °")

    def _update_selected_well_panel(self) -> None:
        name = self._selected_well_name()
        if not name:
            self._set_text("lblWellNameValue", "—")
            return
        self._set_text("lblWellNameValue", name)
        datum = self._well_datums.get(name, "KB")
        kb = self._well_kb.get(name, self._infer_well_kb(self._wells().get(name)))
        shift = self._well_shifts.get(name, 0.0)

        self._widget("dspinKB").blockSignals(True)
        self._widget("dspinKB").setValue(kb)
        self._widget("dspinKB").blockSignals(False)
        self._widget("cmbWellDatum").blockSignals(True)
        self._widget("cmbWellDatum").setCurrentText(datum)
        self._widget("cmbWellDatum").blockSignals(False)
        self._widget("dspinWellShift").blockSignals(True)
        self._widget("dspinWellShift").setValue(shift)
        self._widget("dspinWellShift").blockSignals(False)

        color = self._well_colors.get(name, self._well_color(name, 0))
        self._widget("btnWellColor").setStyleSheet(f"background:{color};")
        self._set_text("lblWellColorHex", color)

    def _update_track_form(self) -> None:
        index = self._widget("listTracks").currentRow()
        if index < 0 or index >= len(self._tracks):
            return
        track = self._tracks[index]

        combo = self._widget("cmbTrackCurve")
        blocker = QtCore.QSignalBlocker(combo)
        if combo.findText(track.curve_label) < 0:
            combo.addItem(track.curve_label)
        combo.setCurrentText(track.curve_label)
        del blocker

        self._widget("spinTrackWidth").setValue(track.width_px)
        self._widget("cmbTrackScale").setCurrentText(track.scale)
        self._widget("dspinTrackMin").setValue(track.min_value)
        self._widget("dspinTrackMax").setValue(track.max_value)
        self._widget("cmbTrackFill").setCurrentText(track.fill)
        self._widget("btnTrackColor").setStyleSheet(f"background:{track.color};")
        self._widget("dspinTrackLineWidth").setValue(track.line_width)

    def _apply_track_form(self) -> None:
        index = self._widget("listTracks").currentRow()
        if index < 0 or index >= len(self._tracks):
            return
        track = self._tracks[index]
        track.width_px = int(self._widget("spinTrackWidth").value())
        track.curve_label = self._widget("cmbTrackCurve").currentText()
        track.scale = self._widget("cmbTrackScale").currentText()
        track.min_value = float(self._widget("dspinTrackMin").value())
        track.max_value = float(self._widget("dspinTrackMax").value())
        track.fill = self._widget("cmbTrackFill").currentText()
        track.line_width = float(self._widget("dspinTrackLineWidth").value())
        self._populate_track_list()
        self._update_headers()
        self._render_correlation()

    def _update_pick_formation_choices(self) -> None:
        combo = self._widget("cmbPickFormation")
        current = combo.currentText()
        choices = [zone["name"] for zone in self._zones] or ["Untitled Formation"]
        blocker = QtCore.QSignalBlocker(combo)
        combo.clear()
        combo.addItems(choices)
        if current and combo.findText(current) >= 0:
            combo.setCurrentText(current)
        del blocker

    def _filter_wells(self, text: str) -> None:
        tree = self._widget("treeWells")
        query = text.strip().lower()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            visible = not query or query in item.text(0).lower()
            item.setHidden(not visible)

    def _on_tree_item_changed(self, item, column: int) -> None:
        if item.parent() is not None or column != 0:
            return
        name = item.data(0, QtCore.Qt.UserRole) or item.text(0)
        if item.checkState(0) == QtCore.Qt.Checked:
            if name not in self._selected_wells:
                self._selected_wells.append(name)
        else:
            self._selected_wells = [well for well in self._selected_wells if well != name]
        item.setText(1, "Shown" if name in self._selected_wells else "Hidden")
        self._update_headers()
        self._update_counts()
        self._sync_depth_controls()
        self._render_correlation()

    def _on_tree_selection_changed(self) -> None:
        self._update_selected_well_panel()

    def _add_selected_wells(self) -> None:
        tree = self._widget("treeWells")
        for item in tree.selectedItems():
            top = item if item.parent() is None else item.parent()
            top.setCheckState(0, QtCore.Qt.Checked)

    def _remove_selected_wells(self) -> None:
        tree = self._widget("treeWells")
        for item in tree.selectedItems():
            top = item if item.parent() is None else item.parent()
            top.setCheckState(0, QtCore.Qt.Unchecked)

    def _move_selected_well(self, step: int) -> None:
        name = self._selected_well_name()
        if not name or name not in self._selected_wells:
            return
        index = self._selected_wells.index(name)
        new_index = max(0, min(len(self._selected_wells) - 1, index + step))
        if new_index == index:
            return
        self._selected_wells.pop(index)
        self._selected_wells.insert(new_index, name)
        self.refresh()

    def _sort_wells_by_location(self) -> None:
        def key_func(name: str):
            well = self._wells().get(name)
            frame = self._depth_frame(well)
            x_mean = float(frame["x"].mean()) if frame is not None and "x" in frame else 0.0
            y_mean = float(frame["y"].mean()) if frame is not None and "y" in frame else 0.0
            return (x_mean, y_mean, name.lower())

        self._selected_wells = sorted(self._selected_wells, key=key_func)
        self.refresh()

    def _pick_selected_well_color(self) -> None:
        name = self._selected_well_name()
        if not name:
            return
        current = QtGui.QColor(self._well_colors.get(name, self._well_color(name, 0)))
        color = QtWidgets.QColorDialog.getColor(current, self.workspace, "Choose Well Color")
        if color.isValid():
            self._well_colors[name] = color.name()
            self.refresh()

    def _on_well_property_changed(self, *_args) -> None:
        name = self._selected_well_name()
        if not name:
            return
        self._well_kb[name] = float(self._widget("dspinKB").value())
        self._well_datums[name] = self._widget("cmbWellDatum").currentText()
        self._render_correlation()

    def _on_well_shift_changed(self, value: float) -> None:
        name = self._selected_well_name()
        if not name:
            return
        self._well_shifts[name] = float(value)
        self._render_correlation()

    def _add_track(self) -> None:
        index = len(self._tracks) + 1
        default_curve = self._track_curve_choices[min(index, len(self._track_curve_choices) - 1)] if self._track_curve_choices else "GR"
        if default_curve == "(none)":
            default_curve = "GR"
        self._tracks.append(self._default_track(index, default_curve))
        self._populate_track_list()
        self._widget("listTracks").setCurrentRow(len(self._tracks) - 1)
        self._update_headers()
        self._render_correlation()

    def _remove_track(self) -> None:
        if len(self._tracks) <= 1:
            return
        index = self._widget("listTracks").currentRow()
        if index < 0:
            return
        self._tracks.pop(index)
        for i, track in enumerate(self._tracks, start=1):
            track.name = f"Track {i}"
        self.refresh()

    def _move_track(self, step: int) -> None:
        index = self._widget("listTracks").currentRow()
        if index < 0:
            return
        new_index = max(0, min(len(self._tracks) - 1, index + step))
        if new_index == index:
            return
        track = self._tracks.pop(index)
        self._tracks.insert(new_index, track)
        self._populate_track_list()
        self._widget("listTracks").setCurrentRow(new_index)
        self._update_headers()
        self._render_correlation()

    def _pick_track_color(self) -> None:
        index = self._widget("listTracks").currentRow()
        if index < 0:
            return
        current = QtGui.QColor(self._tracks[index].color)
        color = QtWidgets.QColorDialog.getColor(current, self.workspace, "Choose Track Color")
        if color.isValid():
            self._tracks[index].color = color.name()
            self._widget("btnTrackColor").setStyleSheet(f"background:{color.name()};")
            self._render_correlation()

    def _add_zone(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self.workspace, "Add Zone", "Formation name:")
        if not ok or not name.strip():
            return
        zone_name = name.strip()
        if zone_name in {zone["name"] for zone in self._zones}:
            return
        self._zones.append({"name": zone_name, "color": WELL_COLOR_CYCLE[len(self._zones) % len(WELL_COLOR_CYCLE)]})
        self.refresh()

    def _remove_zone(self) -> None:
        tree = self._widget("treeZones")
        item = tree.currentItem()
        if item is None:
            return
        zone_name = item.text(0)
        self._zones = [zone for zone in self._zones if zone["name"] != zone_name]
        self._picks = [pick for pick in self._picks if pick.formation != zone_name]
        self.refresh()

    def _pick_zone_color(self) -> None:
        tree = self._widget("treeZones")
        item = tree.currentItem()
        if item is None:
            return
        zone_name = item.text(0)
        zone = next((zone for zone in self._zones if zone["name"] == zone_name), None)
        if zone is None:
            return
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(zone["color"]), self.workspace, "Choose Zone Color")
        if color.isValid():
            zone["color"] = color.name()
            self.refresh()

    def _import_tops_csv(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.workspace,
            "Import Formation Tops CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self.workspace, "Import Tops", f"Failed to read CSV:\n{exc}")
            return

        formation_col = self._find_column(df, "FORMATION", "ZONE", "TOP", "NAME")
        depth_col = self._find_column(df, "MD", "DEPTH", "DEPT")
        tvd_col = self._find_column(df, "TVD", "TVDSS")
        well_col = self._find_column(df, "WELL", "WELLNAME")
        if formation_col is None or depth_col is None:
            QtWidgets.QMessageBox.warning(
                self.workspace,
                "Import Tops",
                "CSV needs at least formation and depth columns.",
            )
            return

        imported = 0
        for _, row in df.iterrows():
            formation = str(row[formation_col]).strip()
            if not formation:
                continue
            if formation not in {zone["name"] for zone in self._zones}:
                self._zones.append({"name": formation, "color": WELL_COLOR_CYCLE[len(self._zones) % len(WELL_COLOR_CYCLE)]})
            well_name = str(row[well_col]).strip() if well_col is not None else (self._selected_wells[0] if self._selected_wells else "")
            if not well_name:
                continue
            md = float(pd.to_numeric(row[depth_col], errors="coerce"))
            if not np.isfinite(md):
                continue
            tvd = float(pd.to_numeric(row[tvd_col], errors="coerce")) if tvd_col is not None else md
            pick = PickRecord(
                well_name=well_name,
                formation=formation,
                md=md,
                tvd=tvd,
                tvdss=-tvd,
                gr=None,
                rhob=None,
                rt=None,
                vsh=None,
                confidence="Imported",
                picked_by="CSV",
                notes=Path(file_path).name,
            )
            self._picks.append(pick)
            imported += 1

        self.refresh()
        QtWidgets.QMessageBox.information(self.workspace, "Import Tops", f"Imported {imported} picks from CSV.")

    def _clear_picks(self) -> None:
        self._picks.clear()
        self._current_pick = None
        self._populate_picks_table()
        self._update_counts()
        self._clear_pick_labels()
        self._render_correlation()

    def _auto_correlate(self) -> None:
        if len(self._selected_wells) < 2:
            QtWidgets.QMessageBox.information(self.workspace, "Auto Correlation", "Select at least 2 wells first.")
            return
        zone_names = [zone["name"] for zone in self._zones] or ["Auto Zone 1", "Auto Zone 2", "Auto Zone 3"]
        top = float(self._widget("dspinDepthFrom").value())
        bottom = float(self._widget("dspinDepthTo").value())
        if bottom <= top:
            bottom = top + 300.0
        fractions = np.linspace(0.2, 0.8, min(3, len(zone_names)))
        self._picks = [pick for pick in self._picks if pick.confidence != "Auto"]
        for idx, fraction in enumerate(fractions):
            formation = zone_names[idx]
            target_depth = top + fraction * (bottom - top)
            for well_name in self._selected_wells:
                values = self._sample_well_at_depth(well_name, target_depth)
                if values is None:
                    continue
                self._picks.append(
                    PickRecord(
                        well_name=well_name,
                        formation=formation,
                        md=values["md"],
                        tvd=values["tvd"],
                        tvdss=values["tvdss"],
                        gr=values["gr"],
                        rhob=values["rhob"],
                        rt=values["rt"],
                        vsh=values["vsh"],
                        confidence="Auto",
                        picked_by="Auto",
                        notes=self._widget("cmbAutoCorrelMethod").currentText(),
                    )
                )
        self.refresh()

    def _confirm_current_pick(self) -> None:
        if self._current_pick is None:
            QtWidgets.QMessageBox.information(self.workspace, "Confirm Pick", "Click in the correlation view first.")
            return
        formation = self._widget("cmbPickFormation").currentText() or "Untitled Formation"
        pending = self._current_pick
        records = [pending]

        if self._is_checked("chkAutoPropagate", False):
            for well_name in self._selected_wells:
                if well_name == pending["well_name"]:
                    continue
                propagated = self._sample_well_at_depth(well_name, pending["md"])
                if propagated is not None:
                    records.append(propagated)

        confidence = "Uncertain" if self._is_checked("chkInterpolateUncertain", True) else "Certain"
        for record in records:
            self._picks.append(
                PickRecord(
                    well_name=record["well_name"],
                    formation=formation,
                    md=record["md"],
                    tvd=record["tvd"],
                    tvdss=record["tvdss"],
                    gr=record["gr"],
                    rhob=record["rhob"],
                    rt=record["rt"],
                    vsh=record["vsh"],
                    confidence=confidence,
                    picked_by="User",
                    notes="Interactive pick",
                )
            )
        self.refresh()

    def _delete_current_pick(self) -> None:
        if not self._picks:
            return
        if self._current_pick is None:
            self._picks.pop()
            self.refresh()
            return
        well_name = self._current_pick["well_name"]
        md = self._current_pick["md"]
        remaining = []
        deleted = False
        for pick in self._picks:
            if not deleted and pick.well_name == well_name and abs(pick.md - md) <= 1.0:
                deleted = True
                continue
            remaining.append(pick)
        self._picks = remaining
        self.refresh()

    def _delete_selected_pick_rows(self) -> None:
        table = self._widget("tableCorrelationPicks")
        rows = sorted({item.row() for item in table.selectedItems()}, reverse=True)
        if not rows:
            return
        visible = []
        zone_filter = self._widget("cmbPicksFilterZone").currentText()
        well_filter = self._widget("cmbPicksFilterWell").currentText()
        for pick in self._picks:
            if zone_filter != "All zones" and pick.formation != zone_filter:
                continue
            if well_filter != "All wells" and pick.well_name != well_filter:
                continue
            visible.append(pick)
        target_ids = {id(visible[row]) for row in rows if row < len(visible)}
        self._picks = [pick for pick in self._picks if id(pick) not in target_ids]
        self.refresh()

    def _on_depth_spin_changed(self, *_args) -> None:
        top = float(self._widget("dspinDepthFrom").value())
        bottom = float(self._widget("dspinDepthTo").value())
        if bottom <= top:
            bottom = top + 1.0
            self._widget("dspinDepthTo").blockSignals(True)
            self._widget("dspinDepthTo").setValue(bottom)
            self._widget("dspinDepthTo").blockSignals(False)
        self._widget("sliderDepthTop").blockSignals(True)
        self._widget("sliderDepthBottom").blockSignals(True)
        self._widget("sliderDepthTop").setValue(int(round(top)))
        self._widget("sliderDepthBottom").setValue(int(round(bottom)))
        self._widget("sliderDepthTop").blockSignals(False)
        self._widget("sliderDepthBottom").blockSignals(False)
        self._set_text("lblDepthSliderFrom", f"{top:,.0f} m")
        self._set_text("lblDepthSliderTo", f"{bottom:,.0f} m")
        self._render_correlation()

    def _on_depth_slider_changed(self, *_args) -> None:
        top = float(self._widget("sliderDepthTop").value())
        bottom = float(self._widget("sliderDepthBottom").value())
        if bottom <= top:
            sender = self.workspace.sender()
            if sender is self._widget("sliderDepthTop"):
                bottom = top + 1.0
                self._widget("sliderDepthBottom").blockSignals(True)
                self._widget("sliderDepthBottom").setValue(int(round(bottom)))
                self._widget("sliderDepthBottom").blockSignals(False)
            else:
                top = bottom - 1.0
                self._widget("sliderDepthTop").blockSignals(True)
                self._widget("sliderDepthTop").setValue(int(round(top)))
                self._widget("sliderDepthTop").blockSignals(False)
        self._widget("dspinDepthFrom").blockSignals(True)
        self._widget("dspinDepthTo").blockSignals(True)
        self._widget("dspinDepthFrom").setValue(top)
        self._widget("dspinDepthTo").setValue(bottom)
        self._widget("dspinDepthFrom").blockSignals(False)
        self._widget("dspinDepthTo").blockSignals(False)
        self._set_text("lblDepthSliderFrom", f"{top:,.0f} m")
        self._set_text("lblDepthSliderTo", f"{bottom:,.0f} m")
        self._render_correlation()

    def _on_zoom_changed(self, value: int) -> None:
        self._set_text("lblZoomValue", f"{value}%")
        self._render_correlation()

    def _nudge_zoom(self, delta: int) -> None:
        slider = self._widget("sliderZoomLevel")
        slider.setValue(max(slider.minimum(), min(slider.maximum(), slider.value() + delta)))

    def _fit_all_depth(self) -> None:
        top, bottom = self._depth_bounds()
        self._widget("dspinDepthFrom").setValue(top)
        self._widget("dspinDepthTo").setValue(bottom)

    def _set_depth_window(self, span: float) -> None:
        top = float(self._widget("dspinDepthFrom").value())
        self._widget("dspinDepthTo").setValue(top + span)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        label = {
            "pan": "Pan",
            "zoom": "Zoom",
            "pick": "Pick",
            "correlate": "Correlate",
            "measure": "Measure",
        }.get(mode, mode.title())
        self._status_bar().showMessage(f"Mode: {label}")

    def _toggle_panel(self, name: str) -> None:
        panel = self._widget(name)
        panel.setVisible(not panel.isVisible())

    def _toggle_picks_dock(self) -> None:
        dock = self._widget("dockPicksTable")
        dock.setVisible(not dock.isVisible())

    def _toggle_depth_grid(self) -> None:
        checkbox = self._widget("chkShowDepthGrid")
        checkbox.setChecked(not checkbox.isChecked())

    def _import_wells(self) -> None:
        data_service = self._data_service()
        if data_service is not None:
            data_service.import_data()

    def _preview_export(self) -> None:
        if self._fig is None:
            self._render_correlation()
        if self._fig is None:
            QtWidgets.QMessageBox.information(self.workspace, "Preview Export", "Render a correlation view first.")
            return
        QtWidgets.QMessageBox.information(
            self.workspace,
            "Preview Export",
            f"Ready to export {len(self._selected_wells)} well(s) with {len(self._tracks)} track(s).",
        )

    def _export_current_view(self) -> None:
        if self._widget("rdoExportCSV").isChecked():
            self._export_picks_csv()
            return
        if self._widget("rdoExportPDF").isChecked():
            self._export_figure("pdf")
        elif self._widget("rdoExportSVG").isChecked():
            self._export_figure("svg")
        elif self._widget("rdoExportTIFF").isChecked():
            self._export_figure("tiff")
        else:
            self._export_figure("png")

    def _export_figure(self, fmt: str) -> None:
        if self._fig is None:
            QtWidgets.QMessageBox.information(self.workspace, "Export", "Render a correlation view first.")
            return
        ext = "tif" if fmt == "tiff" else fmt
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.workspace,
            f"Export {fmt.upper()}",
            str(ROOT_DIR / "outputs" / f"multiwell_correlation.{ext}"),
            f"{fmt.upper()} Files (*.{ext});;All Files (*)",
        )
        if not file_path:
            return
        dpi_text = self._widget("cmbExportDPI").currentText()
        dpi = 150
        if "300" in dpi_text:
            dpi = 300
        elif "600" in dpi_text:
            dpi = 600
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            self._fig.savefig(file_path, dpi=dpi, bbox_inches="tight", facecolor=self._fig.get_facecolor(), format=fmt)
            QtWidgets.QMessageBox.information(self.workspace, "Export", f"Saved to:\n{file_path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self.workspace, "Export", f"Failed to export:\n{exc}")

    def _export_picks_csv(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.workspace,
            "Export Picks CSV",
            str(ROOT_DIR / "outputs" / "correlation_picks.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return
        df = pd.DataFrame(
            [
                {
                    "Well": pick.well_name,
                    "Formation": pick.formation,
                    "MD (m)": pick.md,
                    "TVD (m)": pick.tvd,
                    "TVDSS (m)": pick.tvdss,
                    "GR (API)": pick.gr,
                    "RHOB (g/cc)": pick.rhob,
                    "RT (ohm.m)": pick.rt,
                    "Vsh (v/v)": pick.vsh,
                    "Confidence": pick.confidence,
                    "Picked By": pick.picked_by,
                    "Notes": pick.notes,
                }
                for pick in self._picks
            ]
        )
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(file_path, index=False)
            QtWidgets.QMessageBox.information(self.workspace, "Export CSV", f"Saved to:\n{file_path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self.workspace, "Export CSV", f"Failed to export:\n{exc}")

    def _render_correlation(self) -> None:
        frame = self._widget("frameCorrelationView")
        if frame is None:
            return
        if not self._selected_wells:
            self._render_message(frame, "No wells selected.\nCheck two or more wells in the browser to start correlation.")
            self._render_minimap([])
            self._clear_pick_labels()
            return

        try:
            import matplotlib.pyplot as plt
            import matplotlib.ticker as ticker
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        except Exception as exc:
            self._render_message(frame, f"Matplotlib Qt backend is unavailable:\n{exc}")
            return

        selected_wells = [name for name in self._selected_wells if name in self._wells()]
        tracks = [track for track in self._tracks if track.curve_label and track.curve_label != "(none)"] or self._tracks[:1]
        if not selected_wells:
            self._render_message(frame, "Selected wells are no longer available.")
            return

        background = self._background_color()
        foreground = "#F8FAFC" if background == "#1E293B" else "#1E293B"
        grid_color = "#CBD5E1" if background != "#1E293B" else "#334155"
        font_size = int(self._widget("spinLabelFontSize").value())
        top_depth = float(self._widget("dspinDepthFrom").value())
        bottom_depth = float(self._widget("dspinDepthTo").value())
        zoom = max(self._widget("sliderZoomLevel").value() / 100.0, 0.2)
        fig_width = max(10.0, sum(track.width_px for track in tracks) * len(selected_wells) / 120.0)
        scale_factor = self._vertical_scale_factor()
        fig_height = max(7.5, ((bottom_depth - top_depth) / max(scale_factor, 1.0)) / 45.0 / zoom + 6.0)

        fig, axes = plt.subplots(
            nrows=1,
            ncols=max(1, len(selected_wells) * len(tracks)),
            figsize=(fig_width, fig_height),
            sharey=False,
        )
        fig.patch.set_facecolor(background)
        axes_list = [axes] if not isinstance(axes, np.ndarray) else list(axes.flat)
        self._axes_meta = {}

        axis_index = 0
        plotted_depths = []
        for well_index, well_name in enumerate(selected_wells):
            well = self._wells()[well_name]
            depth_frame = self._depth_frame(well)
            if depth_frame is None or depth_frame.empty:
                continue
            well_shift = float(self._widget("dspinGlobalShift").value()) + self._well_shifts.get(well_name, 0.0)
            depth_frame = depth_frame.copy()
            depth_frame["display"] = depth_frame["display"] + well_shift
            depth_frame = depth_frame[(depth_frame["display"] >= top_depth) & (depth_frame["display"] <= bottom_depth)]
            if depth_frame.empty:
                continue
            plotted_depths.append(depth_frame["display"].to_numpy(dtype=float))

            for track_index, track in enumerate(tracks):
                if axis_index >= len(axes_list):
                    break
                ax = axes_list[axis_index]
                axis_index += 1
                ax.set_facecolor(background if not self._is_checked("chkAlternateTrackBg", False) or track_index % 2 == 0 else "#F8FAFD")
                for spine in ax.spines.values():
                    spine.set_edgecolor(grid_color)
                ax.tick_params(colors=foreground, labelsize=max(6, font_size - 1))

                curve_name = self._match_curve_column(getattr(well, "data", None), track.curve_label)
                if curve_name is not None:
                    series = pd.to_numeric(well.data[curve_name], errors="coerce")
                    frame_data = pd.DataFrame({"depth": depth_frame["display"], "curve": series.reindex(depth_frame.index)})
                    frame_data = frame_data.dropna(subset=["curve"])
                else:
                    frame_data = pd.DataFrame(columns=["depth", "curve"])

                if frame_data.empty:
                    ax.text(0.5, 0.5, f"{track.curve_label}\nN/A", ha="center", va="center", color=foreground, transform=ax.transAxes, fontsize=font_size)
                else:
                    x = frame_data["curve"].to_numpy(dtype=float)
                    y = frame_data["depth"].to_numpy(dtype=float)
                    x = self._prepare_curve_values(x, track.scale)
                    x_min, x_max = self._resolve_track_range(track, x)
                    line_color = track.color
                    ax.plot(x, y, color=line_color, linewidth=track.line_width, alpha=0.95)
                    self._apply_fill(ax, x, y, x_min, x_max, track)
                    if track.scale == "Logarithmic":
                        ax.set_xscale("log")
                    ax.set_xlim(x_min, x_max)

                ax.set_ylim(bottom_depth, top_depth)
                if self._is_checked("chkShowDepthGrid", True):
                    ax.grid(axis="y", color=grid_color, linewidth=0.5, alpha=0.75)
                if self._is_checked("chkShowMajorGrid", True):
                    ax.yaxis.set_major_locator(ticker.MultipleLocator(max(1.0, float(self._widget("dspinMajorGrid").value()))))
                if self._is_checked("chkShowMinorGrid", True):
                    ax.yaxis.set_minor_locator(ticker.MultipleLocator(max(0.5, float(self._widget("dspinMinorGrid").value()))))
                if not self._is_checked("chkShowDepthLabels", True) or track_index > 0:
                    ax.set_yticklabels([])
                else:
                    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
                    ax.set_ylabel(well_name if self._is_checked("chkShowWellNames", True) else "", color=foreground, fontsize=font_size, fontweight="bold")
                if self._is_checked("chkShowCurveHeaders", True):
                    ax.set_title(track.curve_label, fontsize=font_size, color=line_color, pad=4, fontweight="bold")
                if self._is_checked("chkShowPickValues", True):
                    self._draw_picks(ax, well_name, track_index == 0, foreground)

                self._axes_meta[id(ax)] = {"well_name": well_name, "track": track}

        for extra_ax in axes_list[axis_index:]:
            extra_ax.set_visible(False)

        datum_text = self._widget("cmbDepthReference").currentText()
        fig.suptitle(
            f"Multi-Well Correlation  |  {len(selected_wells)} wells  |  {len(tracks)} tracks  |  {datum_text}",
            fontsize=font_size + 3,
            color=foreground,
            fontweight="bold",
            y=0.995,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.985), w_pad=0.15)

        self._render_figure(frame, fig, FigureCanvas(fig))
        self._render_minimap(plotted_depths)
        self._status_bar().showMessage(f"Rendered {len(selected_wells)} well(s) × {len(tracks)} track(s)")

    def _render_figure(self, frame: QtWidgets.QFrame, fig, canvas) -> None:
        layout = frame.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        layout.addWidget(canvas, 1)
        self._fig = fig
        self._canvas = canvas
        canvas.mpl_connect("motion_notify_event", self._on_motion)
        canvas.mpl_connect("button_press_event", self._on_click)
        canvas.draw_idle()
        try:
            from plotting.plot_context_menu import install_plot_context_menu
            install_plot_context_menu(canvas, fig, frame)
        except Exception:
            pass

    def _render_minimap(self, plotted_depths: list[np.ndarray]) -> None:
        frame = self._widget("frameMinimapCanvas")
        if frame is None:
            return
        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(2, 2, 2, 2)

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        if not plotted_depths:
            label = QtWidgets.QLabel("Overview will appear after rendering.")
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setStyleSheet("color:#94A3B8; font-size:10px;")
            layout.addWidget(label)
            return

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        except Exception:
            return

        fig, ax = plt.subplots(figsize=(5.2, 0.8))
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#FFFFFF")
        for index, depths in enumerate(plotted_depths):
            ax.plot([index, index], [depths.min(), depths.max()], color=self._well_color(self._selected_wells[index], index), linewidth=6, solid_capstyle="round")
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout(pad=0.2)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        self._minimap_fig = fig
        self._minimap_canvas = canvas

    def _render_message(self, frame: QtWidgets.QFrame, message: str) -> None:
        layout = frame.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        label = QtWidgets.QLabel(message, frame)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color:#94A3B8; font-size:13px; font-weight:500; padding:40px;")
        layout.addWidget(label)
        self._fig = None
        self._canvas = None

    def _on_motion(self, event) -> None:
        if event.inaxes is None or event.ydata is None:
            self._set_text("lblCursorDepth", "Depth: —")
            self._set_text("lblCursorWell", "Well: —")
            self._set_text("lblCursorValue", "Value: —")
            return
        meta = self._axes_meta.get(id(event.inaxes), {})
        self._set_text("lblCursorDepth", f"Depth: {event.ydata:,.2f} m")
        self._set_text("lblCursorWell", f"Well: {meta.get('well_name', '—')}")
        if event.xdata is not None:
            self._set_text("lblCursorValue", f"Value: {event.xdata:,.3f}")

    def _on_click(self, event) -> None:
        if event.inaxes is None or event.ydata is None:
            return
        meta = self._axes_meta.get(id(event.inaxes))
        if meta is None:
            return
        sample = self._sample_well_at_depth(meta["well_name"], float(event.ydata))
        if sample is None:
            return
        self._current_pick = sample
        self._set_text("lblPickedWell", sample["well_name"])
        self._set_text("lblPickedMD", f"{sample['md']:,.2f} m")
        self._set_text("lblPickedTVD", f"{sample['tvd']:,.2f} m")
        self._set_text("lblPickedGR", f"{self._fmt_optional(sample['gr'])}  API")
        self._set_text("lblPickedRHOB", f"{self._fmt_optional(sample['rhob'])}  g/cc")
        self._set_text("lblPickedRT", f"{self._fmt_optional(sample['rt'])}  ohm.m")
        self._status_bar().showMessage(f"Picked {sample['well_name']} at MD {sample['md']:,.1f} m")

    def _sample_well_at_depth(self, well_name: str, depth_value: float) -> dict[str, Any] | None:
        well = self._wells().get(well_name)
        if well is None:
            return None
        frame = self._depth_frame(well)
        if frame is None or frame.empty:
            return None
        shift = float(self._widget("dspinGlobalShift").value()) + self._well_shifts.get(well_name, 0.0)
        target_display = depth_value - shift
        idx = int((frame["display"] - target_display).abs().idxmin())
        row = frame.loc[idx]
        return {
            "well_name": well_name,
            "md": float(row["md"]),
            "tvd": float(row["tvd"]),
            "tvdss": float(row["tvdss"]),
            "gr": self._sample_curve(row, "GR"),
            "rhob": self._sample_curve(row, "RHOB"),
            "rt": self._sample_curve(row, "RT"),
            "vsh": self._sample_curve(row, "VSHALE"),
        }

    def _sample_curve(self, row: pd.Series, curve_name: str) -> float | None:
        token = self._curve_token(curve_name)
        if token in row and pd.notna(row[token]):
            return float(row[token])
        return None

    def _draw_picks(self, ax, well_name: str, draw_labels: bool, foreground: str) -> None:
        formations = {zone["name"]: zone["color"] for zone in self._zones}
        for pick in self._picks:
            if pick.well_name != well_name:
                continue
            color = formations.get(pick.formation, "#2563EB")
            ax.axhline(pick.md + self._well_shifts.get(well_name, 0.0) + float(self._widget("dspinGlobalShift").value()), color=color, linestyle=self._line_style(), linewidth=float(self._widget("dspinCorrelLineWidth").value()), alpha=0.9)
            if draw_labels and self._is_checked("chkShowFormationNames", True):
                ax.text(0.02, pick.md, pick.formation, transform=ax.get_yaxis_transform(), color=color, fontsize=max(6, int(self._widget("spinLabelFontSize").value()) - 1), va="bottom")

    def _line_style(self) -> str:
        text = self._widget("cmbCorrelLineType").currentText().lower()
        if "dash" in text:
            return "--"
        if "dot" in text:
            return ":"
        return "-"

    def _prepare_curve_values(self, values: np.ndarray, scale: str) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return np.array([1.0, 1.0])
        if scale == "Logarithmic":
            arr = arr[arr > 0]
            if arr.size == 0:
                arr = np.array([0.1, 1.0])
        return arr

    def _resolve_track_range(self, track: TrackConfig, values: np.ndarray) -> tuple[float, float]:
        x_min = float(track.min_value)
        x_max = float(track.max_value)
        if values.size:
            if x_min == 0.0 and x_max == 0.0:
                x_min = float(np.nanmin(values))
                x_max = float(np.nanmax(values))
            elif x_min == x_max:
                x_min = float(np.nanmin(values))
                x_max = float(np.nanmax(values))
        if x_max <= x_min:
            x_max = x_min + 1.0
        if track.scale == "Logarithmic":
            x_min = max(x_min, 0.001)
            x_max = max(x_max, x_min * 10)
        return x_min, x_max

    def _apply_fill(self, ax, x: np.ndarray, y: np.ndarray, x_min: float, x_max: float, track: TrackConfig) -> None:
        fill = track.fill.lower()
        alpha = max(0.02, min(self._widget("sliderZoneFillOpacity").value() / 100.0, 0.75))
        if fill.startswith("left"):
            ax.fill_betweenx(y, x_min, x, color=track.color, alpha=alpha)
        elif fill.startswith("right"):
            ax.fill_betweenx(y, x, x_max, color=track.color, alpha=alpha)
        elif fill.startswith("bilateral"):
            mid = (x_min + x_max) / 2.0
            ax.fill_betweenx(y, mid, x, color=track.color, alpha=alpha)
        elif fill.startswith("solid"):
            ax.fill_betweenx(y, x_min, x_max, color=track.color, alpha=alpha * 0.6)

    def _depth_frame(self, well) -> pd.DataFrame | None:
        df = getattr(well, "data", None)
        if df is None or getattr(df, "empty", True):
            return None
        frame = pd.DataFrame(index=df.index)
        md_col = self._match_column(df, "MD", "DEPTH", "DEPT", "MEASUREDDEPTH")
        tvd_col = self._match_column(df, "TVD", "TRUEVERTICALDEPTH")
        tvdss_col = self._match_column(df, "TVDSS")
        x_col = self._match_column(df, "X", "XCOORD", "EASTING", "UTMX")
        y_col = self._match_column(df, "Y", "YCOORD", "NORTHING", "UTMY")

        if md_col is not None:
            frame["md"] = pd.to_numeric(df[md_col], errors="coerce")
        else:
            frame["md"] = np.arange(len(df), dtype=float)
        if tvd_col is not None:
            frame["tvd"] = pd.to_numeric(df[tvd_col], errors="coerce")
        else:
            frame["tvd"] = frame["md"]
        if tvdss_col is not None:
            frame["tvdss"] = pd.to_numeric(df[tvdss_col], errors="coerce")
        else:
            kb = self._infer_well_kb(well)
            frame["tvdss"] = kb - frame["tvd"]
        frame["x"] = pd.to_numeric(df[x_col], errors="coerce") if x_col is not None else 0.0
        frame["y"] = pd.to_numeric(df[y_col], errors="coerce") if y_col is not None else 0.0

        for label, aliases in {
            "GR": ("GR", "GAMMA", "GAMMARAY"),
            "RHOB": ("RHOB", "DEN", "DENSITY"),
            "RT": ("RT", "ILD", "RDEP", "RESD"),
            "VSHALE": ("VSHALE", "VSH", "VCL"),
        }.items():
            column = self._match_column(df, *aliases)
            if column is not None:
                frame[label] = pd.to_numeric(df[column], errors="coerce")

        depth_ref = self._widget("cmbDepthReference").currentText()
        if depth_ref.startswith("TVDSS"):
            frame["display"] = frame["tvdss"].abs()
        elif depth_ref.startswith("TVD"):
            frame["display"] = frame["tvd"]
        else:
            frame["display"] = frame["md"]
        return frame.dropna(subset=["display"]).sort_values("display").reset_index(drop=True)

    def _match_curve_column(self, df: pd.DataFrame | None, label: str) -> str | None:
        if df is None:
            return None
        token = self._curve_token(label)
        alias_map = {
            "GR": ("GR", "GAMMA", "GAMMARAY"),
            "RT": ("RT", "ILD", "RDEP", "RESD", "RESISTIVITY"),
            "RHOB": ("RHOB", "RHOZ", "DEN", "DENSITY"),
            "NPHI": ("NPHI", "NEUTRON"),
            "VSHALE": ("VSHALE", "VSH", "VCL"),
            "PHIE": ("PHIE", "PHI", "POR"),
            "SW": ("SW", "SATW"),
            "PERM": ("PERM", "PERMEABILITY", "K"),
            "NETPAYFLAG": ("NETPAY", "NETPAYFLAG", "PAY"),
        }
        aliases = alias_map.get(token, (label,))
        return self._match_column(df, *aliases)

    def _match_column(self, df: pd.DataFrame, *aliases: str) -> str | None:
        lookup = {self._normalize(column): column for column in df.columns}
        for alias in aliases:
            key = self._normalize(alias)
            if key in lookup:
                return lookup[key]
        for column in df.columns:
            norm = self._normalize(column)
            if any(self._normalize(alias) in norm for alias in aliases):
                return str(column)
        return None

    def _curve_token(self, label: str) -> str:
        token = self._normalize(label)
        mapping = {
            "GR": "GR",
            "RHOB": "RHOB",
            "NPHI": "NPHI",
            "RTRESISTIVITY": "RT",
            "RT": "RT",
            "VSHALE": "VSHALE",
            "PHIE": "PHIE",
            "SW": "SW",
            "PERMEABILITY": "PERM",
            "PERM": "PERM",
            "NETPAYFLAG": "NETPAYFLAG",
        }
        return mapping.get(token, token)

    def _infer_well_kb(self, well) -> float:
        if well is None:
            return 0.0
        header = getattr(well, "header", {}) or {}
        for section in header.values():
            if isinstance(section, dict):
                for key, value in section.items():
                    if "KB" in str(key).upper():
                        if isinstance(value, dict):
                            numeric = pd.to_numeric(value.get("value"), errors="coerce")
                        else:
                            numeric = pd.to_numeric(value, errors="coerce")
                        if pd.notna(numeric):
                            return float(numeric)
        return 0.0

    def _find_column(self, df: pd.DataFrame, *aliases: str) -> str | None:
        return self._match_column(df, *aliases)

    def _background_color(self) -> str:
        if self._is_checked("rdoBgCustom", False):
            return "#1E293B"
        if self._is_checked("rdoBgCream", False):
            return "#FFFDF7"
        return "#FFFFFF"

    def _vertical_scale_factor(self) -> float:
        text = self._widget("cmbVerticalScale").currentText()
        if ":" not in text:
            return 1000.0
        try:
            return float(text.split(":")[1].strip())
        except Exception:
            return 1000.0

    def _well_color(self, name: str, index: int) -> str:
        if name not in self._well_colors:
            self._well_colors[name] = WELL_COLOR_CYCLE[index % len(WELL_COLOR_CYCLE)]
        return self._well_colors[name]

    def _select_all_wells(self) -> None:
        tree = self._widget("treeWells")
        for i in range(tree.topLevelItemCount()):
            tree.topLevelItem(i).setCheckState(0, QtCore.Qt.Checked)

    def _set_text(self, name: str, text: str) -> None:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(text)

    def _clear_pick_labels(self) -> None:
        for name, value in (
            ("lblPickedWell", "—"),
            ("lblPickedMD", "—"),
            ("lblPickedTVD", "—"),
            ("lblPickedGR", "—  API"),
            ("lblPickedRHOB", "—  g/cc"),
            ("lblPickedRT", "—  ohm.m"),
        ):
            self._set_text(name, value)

    def _is_checked(self, name: str, default: bool) -> bool:
        widget = self._widget(name)
        if widget is not None and hasattr(widget, "isChecked"):
            return bool(widget.isChecked())
        return default

    def _status_bar(self):
        bar = getattr(self.workspace, "statusBar", None)
        if callable(bar):
            return bar()
        return bar

    @staticmethod
    def _normalize(value: Any) -> str:
        return "".join(ch for ch in str(value).upper() if ch.isalnum())

    @staticmethod
    def _fmt_optional(value: float | None) -> str:
        if value is None or not np.isfinite(value):
            return "—"
        return f"{value:,.3f}"
