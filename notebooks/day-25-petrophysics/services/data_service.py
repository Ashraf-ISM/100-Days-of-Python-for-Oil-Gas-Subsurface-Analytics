"""Data import + data views population (stub)."""
from __future__ import annotations

from typing import Any

from PyQt5 import QtWidgets

from core.well_data_loader import load_well


class DataService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self._wells: dict[str, Any] = {}
        self._current_well: str | None = None

    def import_data(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui,
            "Import Well Data",
            "",
            "Well Data (*.las *.laz *.dlis *.dl *.csv *.txt *.dat *.asc)",
        )
        if not path:
            return
        well, msg = load_well(path, replace_nulls=True, depth_unit="m", depth_type="MD")
        self._wells[well.name] = well
        self._current_well = well.name
        self._update_well_lists()
        self._refresh_views()
        QtWidgets.QMessageBox.information(self.ui, "Import", msg)

    def _update_well_lists(self):
        for combo_name in (
            "comboActiveWell",
            "comboCurveWell",
            "comboZoneWell",
            "comboStatWell",
            "comboDTWell",
            "comboQCWell",
        ):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            combo.clear()
            combo.addItems(sorted(self._wells.keys()))
            if self._current_well:
                idx = combo.findText(self._current_well)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _refresh_views(self):
        well = self._get_current_well()
        if not well:
            return
        self._populate_header_info(well)
        self._populate_log_info(well)
        self._populate_data_table(well)
        self._populate_rename_table(well)
        self._populate_stats_stub()

    def _get_current_well(self):
        if self._current_well and self._current_well in self._wells:
            return self._wells[self._current_well]
        return None

    def _populate_header_info(self, well):
        table = getattr(self.ui, "tableHeaderInfo", None)
        if table is None:
            return
        header = getattr(well, "header", {}) or {}
        rows = []
        for key, val in header.items():
            rows.append(("HEADER", key, "", str(val), ""))
        self._fill_table(table, rows)

    def _populate_log_info(self, well):
        table = getattr(self.ui, "tableLogInfo", None)
        if table is None:
            return
        log_info = getattr(well, "log_info", {}) or {}
        rows = []
        for name, info in log_info.items():
            rows.append((name, info.get("unit", ""), info.get("type", ""), info.get("mnemonic", ""), info.get("desc", "")))
        self._fill_table(table, rows)

    def _populate_data_table(self, well):
        table = getattr(self.ui, "tableData", None)
        if table is None:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        try:
            columns = list(df.columns)
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels([str(c) for c in columns])
            table.setRowCount(min(len(df), 200))
            for r in range(min(len(df), 200)):
                for c, col in enumerate(columns):
                    table.setItem(r, c, QtWidgets.QTableWidgetItem(str(df.iloc[r][col])))
        except Exception:
            return

    def _populate_rename_table(self, well):
        table = getattr(self.ui, "tableRenameColumns", None)
        if table is None:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        try:
            cols = list(df.columns)
            table.setRowCount(len(cols))
            for i, name in enumerate(cols):
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(name)))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(name)))
        except Exception:
            return

    def _populate_stats_stub(self):
        table = getattr(self.ui, "tableStatistics", None)
        if table is None:
            return
        table.setRowCount(0)

    @staticmethod
    def _fill_table(table: QtWidgets.QTableWidget, rows: list[tuple]):
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
