"""Data import and table population."""
from __future__ import annotations

from PyQt5 import QtWidgets

from core.well_data_loader import load_well


class DataService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self._wells = {}

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
        self._update_well_lists()
        QtWidgets.QMessageBox.information(self.ui, "Import", msg)

    def _update_well_lists(self):
        for combo_name in ("comboActiveWell", "comboCurveWell", "comboZoneWell", "comboStatWell", "comboDTWell", "comboQCWell"):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            combo.clear()
            combo.addItems(sorted(self._wells.keys()))
