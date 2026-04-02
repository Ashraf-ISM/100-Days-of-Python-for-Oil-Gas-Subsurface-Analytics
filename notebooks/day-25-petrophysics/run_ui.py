from __future__ import annotations

import sys
from pathlib import Path

# Ensure local imports (core/, calculations/, plotting/) work when run from repo root.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from PyQt5 import QtWidgets, uic  # noqa: E402

from core.las_reader import load_las, load_csv, generate_demo_well  # noqa: E402
from plotting.log_plotter import LogPlotWidget  # noqa: E402


class PetrophysicsWorkstation(QtWidgets.QMainWindow):
    def __init__(self, las_or_csv_path: str | None = None):
        super().__init__()

        ui_path = THIS_DIR / "ui" / "petrophysicsWorkstaton.ui"
        uic.loadUi(str(ui_path), self)

        self._wells: dict[str, object] = {}
        self._current_well_name: str | None = None

        # Embed matplotlib log plotter into the placeholder layout.
        log_layout = self.findChild(QtWidgets.QVBoxLayout, "logCanvasLayout")
        if log_layout is not None:
            placeholder = self.findChild(QtWidgets.QLabel, "lblLogCanvasPlaceholder")
            if placeholder is not None:
                placeholder.setParent(None)
            self._log_plot = LogPlotWidget(self)
            log_layout.addWidget(self._log_plot)
        else:
            self._log_plot = None

        self._wire_ui()
        self._load_initial_well(las_or_csv_path)

    # ── UI wiring ──────────────────────────────────────────────────────────

    def _wire_ui(self) -> None:
        self.btnBrowseFile = self.findChild(QtWidgets.QPushButton, "btnBrowseFile")
        self.btnImport = self.findChild(QtWidgets.QPushButton, "btnImport")
        self.comboImportFormat = self.findChild(QtWidgets.QComboBox, "comboImportFormat")
        self.lineEditFilePath = self.findChild(QtWidgets.QLineEdit, "lineEditFilePath")
        self.comboDepthType = self.findChild(QtWidgets.QComboBox, "comboDepthType")
        self.comboDepthUnit = self.findChild(QtWidgets.QComboBox, "comboDepthUnit")
        self.chkNullReplace = self.findChild(QtWidgets.QCheckBox, "chkNullReplace")
        self.progressImport = self.findChild(QtWidgets.QProgressBar, "progressImport")
        self.comboLogDisplayWell = self.findChild(QtWidgets.QComboBox, "comboLogDisplayWell")
        self.spinDepthFrom = self.findChild(QtWidgets.QDoubleSpinBox, "spinDepthFrom")
        self.spinDepthTo = self.findChild(QtWidgets.QDoubleSpinBox, "spinDepthTo")
        self.txtOutputLog = self.findChild(QtWidgets.QTextBrowser, "txtOutputLog")

        self._inject_plot_controls()

        if self.btnBrowseFile is not None:
            self.btnBrowseFile.clicked.connect(self._on_browse_file)
        if self.btnImport is not None:
            self.btnImport.clicked.connect(self._on_import_file)
        if self.comboLogDisplayWell is not None:
            self.comboLogDisplayWell.currentTextChanged.connect(self._on_well_changed)
        if self.spinDepthFrom is not None:
            self.spinDepthFrom.valueChanged.connect(self._plot_current_well)
        if self.spinDepthTo is not None:
            self.spinDepthTo.valueChanged.connect(self._plot_current_well)
        if self.comboPlotType is not None:
            self.comboPlotType.currentTextChanged.connect(self._plot_current_well)
        for combo in (self.comboCurveA, self.comboCurveB, self.comboCurveC):
            if combo is not None:
                combo.currentTextChanged.connect(self._plot_current_well)

        # Menu actions (if used)
        action_import_las = self.findChild(QtWidgets.QAction, "actionImportLAS")
        action_import_dlis = self.findChild(QtWidgets.QAction, "actionImportDLIS")
        action_import_csv = self.findChild(QtWidgets.QAction, "actionImportCSV")
        if action_import_las is not None:
            action_import_las.triggered.connect(self._on_browse_file)
        if action_import_dlis is not None:
            action_import_dlis.triggered.connect(self._on_browse_file)
        if action_import_csv is not None:
            action_import_csv.triggered.connect(self._on_browse_file)

    def _inject_plot_controls(self) -> None:
        toolbar_layout = self.findChild(QtWidgets.QHBoxLayout, "logDisplayToolbarLayout")
        if toolbar_layout is None:
            self.comboPlotType = None
            self.comboCurveA = None
            self.comboCurveB = None
            self.comboCurveC = None
            return

        self.comboPlotType = QtWidgets.QComboBox(self)
        self.comboPlotType.addItems([
            "Multi-Track",
            "Triple Combo",
            "Cross Plot",
            "Pair Plot",
            "Histogram",
            "Box Plot",
        ])

        self.lblCurveA = QtWidgets.QLabel("Curve A:", self)
        self.lblCurveB = QtWidgets.QLabel("Curve B:", self)
        self.lblCurveC = QtWidgets.QLabel("Curve C:", self)
        self.comboCurveA = QtWidgets.QComboBox(self)
        self.comboCurveB = QtWidgets.QComboBox(self)
        self.comboCurveC = QtWidgets.QComboBox(self)

        # Insert at end for a clean, minimal add-on.
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(QtWidgets.QLabel("Plot:", self))
        toolbar_layout.addWidget(self.comboPlotType)
        toolbar_layout.addWidget(self.lblCurveA)
        toolbar_layout.addWidget(self.comboCurveA)
        toolbar_layout.addWidget(self.lblCurveB)
        toolbar_layout.addWidget(self.comboCurveB)
        toolbar_layout.addWidget(self.lblCurveC)
        toolbar_layout.addWidget(self.comboCurveC)

        self._update_curve_controls_visibility()
        self.comboPlotType.currentTextChanged.connect(self._update_curve_controls_visibility)

    def _update_curve_controls_visibility(self) -> None:
        if self.comboPlotType is None:
            return
        mode = self.comboPlotType.currentText().lower()
        show_a = True
        show_b = "cross" in mode or "pair" in mode or "triple" in mode or "multi" in mode
        show_c = "pair" in mode or "triple" in mode or "multi" in mode
        if "hist" in mode or "box" in mode:
            show_b = False
            show_c = False

        self.lblCurveA.setVisible(show_a)
        self.comboCurveA.setVisible(show_a)
        self.lblCurveB.setVisible(show_b)
        self.comboCurveB.setVisible(show_b)
        self.lblCurveC.setVisible(show_c)
        self.comboCurveC.setVisible(show_c)

    # ── Logging ────────────────────────────────────────────────────────────

    def _log(self, message: str, level: str = "INFO") -> None:
        if self.txtOutputLog is None:
            return
        prefix = f"[{level}] "
        self.txtOutputLog.append(prefix + message)

    def _load_initial_well(self, path: str | None):
        if path:
            well, msg = self._load_well_from_path(path)
        else:
            well = generate_demo_well()
            msg = f"Loaded demo well: {well.name}"

        self._set_current_well(well, msg)

    # ── Data loading ───────────────────────────────────────────────────────

    def _depth_type_value(self) -> str:
        if self.comboDepthType is None:
            return "MD"
        text = self.comboDepthType.currentText()
        if text.startswith("TVDSS"):
            return "TVDSS"
        if text.startswith("TVD"):
            return "TVD"
        return "MD"

    def _depth_unit_value(self) -> str:
        if self.comboDepthUnit is None:
            return "m"
        text = self.comboDepthUnit.currentText().lower()
        return "ft" if "feet" in text else "m"

    def _load_well_from_path(self, path: str):
        depth_unit = self._depth_unit_value()
        depth_type = self._depth_type_value()
        replace_nulls = self.chkNullReplace.isChecked() if self.chkNullReplace else True

        suffix = Path(path).suffix.lower()
        if suffix in (".las", ".laz", ".dlis"):
            well, msg = load_las(
                path,
                replace_nulls=replace_nulls,
                depth_unit=depth_unit,
                depth_type=depth_type,
            )
        else:
            well, msg = load_csv(
                path,
                replace_nulls=replace_nulls,
                depth_unit=depth_unit,
                depth_type=depth_type,
            )
        return well, msg

    def _set_current_well(self, well, msg: str) -> None:
        self._wells[well.name] = well
        self._current_well_name = well.name

        if self.comboLogDisplayWell is not None:
            if self.comboLogDisplayWell.findText(well.name) == -1:
                self.comboLogDisplayWell.addItem(well.name)
            self.comboLogDisplayWell.setCurrentText(well.name)

        self._populate_curve_selectors(well)
        self._update_depth_controls(well)
        self._plot_current_well()

        self.statusBar().showMessage(msg)
        self._log(msg, "INFO")

    def _populate_curve_selectors(self, well) -> None:
        combos = [self.comboCurveA, self.comboCurveB, self.comboCurveC]
        for combo in combos:
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Select curve...")
            for name in well.curve_names():
                combo.addItem(name)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _update_depth_controls(self, well) -> None:
        if self.spinDepthFrom is None or self.spinDepthTo is None:
            return
        depth_min = float(well.depth_min)
        depth_max = float(well.depth_max)
        suffix = f" {well.depth_unit}"
        self.spinDepthFrom.blockSignals(True)
        self.spinDepthTo.blockSignals(True)
        self.spinDepthFrom.setSuffix(suffix)
        self.spinDepthTo.setSuffix(suffix)
        self.spinDepthFrom.setRange(depth_min, depth_max)
        self.spinDepthTo.setRange(depth_min, depth_max)
        self.spinDepthFrom.setValue(depth_min)
        self.spinDepthTo.setValue(depth_max)
        self.spinDepthFrom.blockSignals(False)
        self.spinDepthTo.blockSignals(False)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_browse_file(self) -> None:
        if self.comboImportFormat is None:
            filter_str = "Data Files (*.las *.laz *.dlis *.csv *.txt *.xlsx *.xls);;All Files (*)"
        else:
            fmt = self.comboImportFormat.currentText().lower()
            if "las" in fmt:
                filter_str = "LAS Files (*.las *.laz);;All Files (*)"
            elif "dlis" in fmt:
                filter_str = "DLIS Files (*.dlis);;All Files (*)"
            elif "excel" in fmt:
                filter_str = "Excel Files (*.xlsx *.xls);;All Files (*)"
            else:
                filter_str = "CSV / Text Files (*.csv *.txt);;All Files (*)"

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select data file",
            str(THIS_DIR),
            filter_str,
        )
        if not path:
            return
        if self.lineEditFilePath is not None:
            self.lineEditFilePath.setText(path)
        self._log(f"Selected file: {path}", "INFO")

    def _on_import_file(self) -> None:
        if self.lineEditFilePath is None:
            return
        path = self.lineEditFilePath.text().strip()
        if not path:
            self._log("No file selected. Click Browse first.", "WARN")
            return

        if self.progressImport is not None:
            self.progressImport.setValue(15)
        well, msg = self._load_well_from_path(path)
        if self.progressImport is not None:
            self.progressImport.setValue(100)
        self._set_current_well(well, msg)

    def _on_well_changed(self, name: str) -> None:
        if not name:
            return
        if name in self._wells:
            self._current_well_name = name
            self._update_depth_controls(self._wells[name])
            self._plot_current_well()

    def _plot_current_well(self) -> None:
        if self._log_plot is None or self._current_well_name is None:
            return
        well = self._wells.get(self._current_well_name)
        if well is None:
            return
        depth_from = self.spinDepthFrom.value() if self.spinDepthFrom else None
        depth_to = self.spinDepthTo.value() if self.spinDepthTo else None
        if depth_from is not None and depth_to is not None and depth_from > depth_to:
            depth_from, depth_to = depth_to, depth_from
        mode = self.comboPlotType.currentText() if self.comboPlotType else "Multi-Track"
        curves = []
        for combo in (self.comboCurveA, self.comboCurveB, self.comboCurveC):
            if combo is None:
                continue
            name = combo.currentText()
            if name and name != "Select curve...":
                curves.append(name)
        self._log_plot.plot_mode(well, mode, curves, depth_from=depth_from, depth_to=depth_to)


def main():
    app = QtWidgets.QApplication(sys.argv)
    data_path = sys.argv[1] if len(sys.argv) > 1 else None
    win = PetrophysicsWorkstation(data_path)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
