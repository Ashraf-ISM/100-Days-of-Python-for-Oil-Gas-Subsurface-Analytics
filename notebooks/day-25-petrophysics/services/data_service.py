"""Data import + data views population (auto header/log info, rename with undo)."""
from __future__ import annotations

from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets

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

    def on_curve_well_changed(self, name: str):
        if not name or name not in self._wells:
            return
        well = self._wells[name]
        self._update_curves_tree(well)

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
        all_well_combos = (
            "comboActiveWell",
            "comboCurveWell",
            "comboZoneWell",
            "comboStatWell",
            "comboDTWell",
            "comboQCWell",
            "comboLVWell",
            "comboDISWell",
            "comboXplotWell",
            "comboHistWell",
            "comboRoseWell",
            "comboVclWell",
            "comboPhiWell",
            "comboSwWell",
            "comboPermWell",
            "comboNetPayWell",
            "comboELANWell",
            "comboFMIWell",
            "comboWBSWell",
            "comboPPWell",
            "comboGeoWell",
        )
        combos_with_all = {"comboDISWell", "comboHistWell", "comboStatWell", "comboQCWell"}
        wells_sorted = sorted(self._wells.keys())
        for combo_name in all_well_combos:
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(wells_sorted)
            if combo_name in combos_with_all:
                combo.addItem("All Wells")
            if self._current_well:
                idx = combo.findText(self._current_well)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

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
        self._update_plot_curve_combos(well)
        self._update_project_tree()
        self._update_curves_tree(well)

    def _refresh_views(self):
        well = self._get_current_well()
        if not well:
            return
        self._update_curve_lists(well)
        self._populate_header_info(well)
        self._populate_log_info(well)
        self._populate_data_table(well)
        self._populate_rename_table(well)
        self._update_plot_curve_combos(well)
        self._update_project_tree()
        self._update_curves_tree(well)

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

    def _update_plot_curve_combos(self, well):
        df = getattr(well, "data", None)
        if df is None:
            return
        curves = list(df.columns)
        combo_track1 = getattr(self.ui, "triplecombotrack1", None)
        if combo_track1 is not None:
            self._set_checkable_combo(combo_track1, curves, set(), "Track 1 curves...")
        combo_track2 = getattr(self.ui, "triplecombotrack2", None)
        if combo_track2 is not None:
            self._set_checkable_combo(combo_track2, curves, set(), "Track 2 curves...")
        combo_track3 = getattr(self.ui, "triplecombotrack3", None)
        if combo_track3 is not None:
            self._set_checkable_combo(combo_track3, curves, set(), "Track 3 curves...")

        combo_multi = getattr(self.ui, "multitrackcomboBox", None)
        if combo_multi is not None:
            self._set_checkable_combo(combo_multi, curves, set(), "Select curves...")

    def _set_checkable_combo(
        self,
        combo: QtWidgets.QComboBox,
        items: list[str],
        checked: set[str],
        placeholder: str = "Select curves...",
    ) -> None:
        model = QtGui.QStandardItemModel()
        for name in items:
            item = QtGui.QStandardItem(name)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            state = QtCore.Qt.Checked if name in checked else QtCore.Qt.Unchecked
            item.setData(state, QtCore.Qt.CheckStateRole)
            model.appendRow(item)
        combo.setModel(model)
        combo.setEditable(True)
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setReadOnly(True)
            line_edit.setPlaceholderText(placeholder)
        model.itemChanged.connect(lambda _item, target=combo, text=placeholder: self._update_combo_display(target, text))
        self._update_combo_display(combo, placeholder)

    @staticmethod
    def _find_first(columns: list[str], candidates: list[str]) -> str | None:
        upper_map = {c: c.upper() for c in columns}
        for cand in candidates:
            cand_upper = cand.upper()
            for col, col_upper in upper_map.items():
                if col_upper == cand_upper:
                    return col
        for cand in candidates:
            cand_upper = cand.upper()
            for col, col_upper in upper_map.items():
                if cand_upper in col_upper:
                    return col
        return None

    @staticmethod
    def _find_all_matching(columns: list[str], tokens: list[str]) -> list[str]:
        matches: list[str] = []
        tokens_upper = [t.upper() for t in tokens]
        for col in columns:
            col_upper = col.upper()
            if any(tok in col_upper for tok in tokens_upper):
                matches.append(col)
        return matches

    def _select_triple_tracks(self, columns: list[str]):
        gr = self._find_first(columns, ["GR", "GRC", "SGR", "CGR", "GRD", "GAMMA"])
        cali = self._find_first(columns, ["CALI", "CAL", "HCAL", "CALD"])

        resistivity = self._find_all_matching(
            columns, ["RT", "RDEP", "RILD", "LLD", "LLS", "RXO", "RES", "ILD", "ILM", "RS"]
        )
        density = self._find_all_matching(columns, ["RHOB", "RHOZ", "RHO", "DEN", "DENB"])
        porosity = self._find_all_matching(columns, ["NPHI", "PHI", "PHIE", "PHIT", "DPHI", "NPOR", "POR"])

        track1 = [c for c in (gr, cali) if c]
        track2 = resistivity[:]
        track3 = density + porosity

        used = set(track1 + track2 + track3)
        if not track1:
            for col in columns:
                if col not in used:
                    track1 = [col]
                    used.add(col)
                    break
        if not track2:
            for col in columns:
                if col not in used:
                    track2 = [col]
                    used.add(col)
                    break
        if not track3:
            for col in columns:
                if col not in used:
                    track3 = [col]
                    used.add(col)
                    break
        return track1, track2, track3

    def _update_combo_display(
        self,
        combo: QtWidgets.QComboBox,
        placeholder: str = "Select curves...",
    ) -> None:
        model = combo.model()
        if model is None:
            return
        selected: list[str] = []
        for i in range(model.rowCount()):
            item = model.item(i)
            if item is not None and item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        if not selected:
            text = placeholder
        elif len(selected) <= 2:
            text = ", ".join(selected)
        else:
            text = f"{len(selected)} curves selected"
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setText(text)

    def _update_project_tree(self):
        tree = getattr(self.ui, "treeProject", None)
        if tree is None:
            return
        tree.clear()
        for well_name in sorted(self._wells.keys()):
            well = self._wells[well_name]
            well_item = QtWidgets.QTreeWidgetItem([well_name, "[Well]"])
            tree.addTopLevelItem(well_item)
            curves_parent = QtWidgets.QTreeWidgetItem(well_item, ["Curves", ""])
            log_info = getattr(well, "log_info", {}) or {}
            if log_info:
                for curve_name, info in log_info.items():
                    unit = info.get("unit", "")
                    QtWidgets.QTreeWidgetItem(curves_parent, [curve_name, unit])
            else:
                df = getattr(well, "data", None)
                if df is not None:
                    for curve_name in df.columns:
                        QtWidgets.QTreeWidgetItem(curves_parent, [str(curve_name), ""])
        tree.expandAll()

    def _update_curves_tree(self, well):
        tree = getattr(self.ui, "treeCurves", None)
        if tree is None or well is None:
            return
        tree.clear()
        log_info = getattr(well, "log_info", {}) or {}
        if log_info:
            for curve_name, info in log_info.items():
                unit = info.get("unit", "")
                curve_type = info.get("type", "")
                QtWidgets.QTreeWidgetItem(tree, [curve_name, unit, curve_type])
        else:
            df = getattr(well, "data", None)
            if df is None:
                return
            for curve_name in df.columns:
                QtWidgets.QTreeWidgetItem(tree, [str(curve_name), "", ""])

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
