"""Data import + data views population (auto header/log info, rename with undo)."""
from __future__ import annotations

from typing import Any

from PyQt5 import QtWidgets

from core.well_data_loader import load_well


class DataService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self._wells: dict[str, Any] = {}
        self._current_well: str | None = None
        self._rename_history: dict[str, list[list[str]]] = {}

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
        self._rename_history.setdefault(well.name, [])
        self._update_well_lists()
        self._refresh_views()
        QtWidgets.QMessageBox.information(self.ui, "Import", msg)

    def load_data_view(self):
        self._refresh_views()

    def set_current_well(self, name: str):
        if not name or name not in self._wells:
            return
        self._current_well = name
        self._refresh_views()

    def on_data_tab_changed(self, index: int):
        _ = index
        self._refresh_views()
        tab = getattr(self.ui, "tabData", None)
        if tab is None:
            return
        current = tab.currentWidget()
        if current is not None and current.objectName() == "tabStatistics":
            self.compute_stats()

    def apply_rename(self):
        well = self._get_current_well()
        if not well:
            return
        table = getattr(self.ui, "tableRenameColumns", None)
        df = getattr(well, "data", None)
        if table is None or df is None:
            return
        try:
            old_cols = list(df.columns)
            new_cols = []
            for r in range(table.rowCount()):
                item = table.item(r, 1)
                new_cols.append(item.text().strip() if item else "")
            if any(not c for c in new_cols) or len(set(new_cols)) != len(new_cols):
                QtWidgets.QMessageBox.warning(self.ui, "Rename", "Column names must be unique and non-empty.")
                return
            self._rename_history[well.name].append(old_cols)
            df.columns = new_cols
            self._refresh_views()
        except Exception:
            return

    def reset_rename(self):
        self._populate_rename_table(self._get_current_well())

    def undo_rename(self):
        well = self._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        history = self._rename_history.get(well.name, [])
        if not history:
            return
        prev = history.pop()
        df.columns = prev
        self._refresh_views()

    def compute_stats(self):
        well = self._get_current_well()
        if not well:
            return
    
        df = getattr(well, "data", None)
        table = getattr(self.ui, "tableStatistics", None)
    
        if df is None or table is None:
            return
    
        try:
            # Only numeric columns
            desc = df.describe().transpose()  # transpose for better UI
    
            rows = []
            for col_name, row in desc.iterrows():
                rows.append((
                    col_name,
                    round(row.get("count", 0), 3),
                    round(row.get("mean", 0), 3),
                    round(row.get("std", 0), 3),
                    round(row.get("min", 0), 3),
                    round(row.get("25%", 0), 3),
                    round(row.get("50%", 0), 3),
                    round(row.get("75%", 0), 3),
                    round(row.get("max", 0), 3),
                ))
    
            # Set headers manually (IMPORTANT)
            table.setColumnCount(9)
            table.setHorizontalHeaderLabels([
                "Curve", "Count", "Mean", "Std",
                "Min", "25%", "50%", "75%", "Max"
            ])
    
            self._fill_table(table, rows)
    
        except Exception as e:
            print("Stats Error:", e)

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

        # update curve list combos
        well = self._get_current_well()
        if well is None:
            return
        df = getattr(well, "data", None)
        if df is None:
            return
        curves = list(df.columns)
        for combo_name in ("comboStatCurve", "comboQCCurve"):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            combo.clear()
            combo.addItems(curves)

    def _refresh_views(self):
        well = self._get_current_well()
        if not well:
            return
        self._update_curve_lists(well)
        self._populate_header_info(well)
        self._populate_log_info(well)
        self._populate_data_table(well)
        self._populate_rename_table(well)

    def _update_curve_lists(self, well):
        df = getattr(well, "data", None)
        if df is None:
            return
        curves = list(df.columns)
        for combo_name in ("comboStatCurve", "comboQCCurve"):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            combo.clear()
            combo.addItems(curves)

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
        for section, items in header.items():
            if isinstance(items, dict):
                for key, val in items.items():
                    rows.append((section, key, val.get("unit", "") if isinstance(val, dict) else "", val.get("value", val) if isinstance(val, dict) else val, val.get("desc", "") if isinstance(val, dict) else ""))
            else:
                rows.append((section, str(items), "", "", ""))
        self._fill_table(table, rows)

    def _populate_log_info(self, well):
        table = getattr(self.ui, "tableLogInfo", None)
        if table is None:
            return
        log_info = getattr(well, "log_info", {}) or {}
        rows = []
        for name, info in log_info.items():
            rows.append((name, info.get("unit", ""), info.get("desc", ""), info.get("type", "")))
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
        if table is None or well is None:
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

    @staticmethod
    def _fill_table(table: QtWidgets.QTableWidget, rows: list[tuple]):
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
