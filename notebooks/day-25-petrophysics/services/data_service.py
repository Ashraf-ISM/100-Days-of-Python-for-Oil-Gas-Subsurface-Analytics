"""Data import + data views population (auto header/log info, rename with undo)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from PyQt5 import QtCore, QtGui, QtWidgets

from core.well_data_loader import load_well


class PandasModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        if self._data is None: return 0
        return len(self._data)

    def columnCount(self, parent=None):
        if self._data is None: return 0
        return len(self._data.columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            val = self._data.iat[index.row(), index.column()]
            import pandas as pd
            if pd.isna(val):
                return ""
            if isinstance(val, float):
                return f"{val:.4f}"
            return str(val)
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == QtCore.Qt.Vertical:
                return str(self._data.index[section])
        return None


class DataService:
    def __init__(self, ui: QtWidgets.QMainWindow):
        self.ui = ui
        self._wells: dict[str, Any] = {}
        self._current_well: str | None = None
        self._all_wells_mode = False
        self._rename_history: dict[str, list[list[str]]] = {}
        self._depth_filter_initialized: set[str] = set()
        self._build_data_info_dashboard()

    def _build_data_info_dashboard(self) -> None:
        """Create the dashboard-style layout inside the Data Info & Stats tab."""
        if getattr(self.ui, "_data_info_dashboard_built", False):
            return

        tab = getattr(self.ui, "tabDataInfoStats", None)
        if tab is None:
            return

        layout = tab.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(10)

        scroll_area = QtWidgets.QScrollArea(tab)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("border:0;background:transparent;")

        content = QtWidgets.QWidget(scroll_area)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        def make_section(title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
            frame = QtWidgets.QFrame(content)
            frame.setStyleSheet(
                "QFrame { background:#FFFFFF; border:1px solid #D7E2EE; border-radius:10px; }"
            )
            frame_layout = QtWidgets.QVBoxLayout(frame)
            frame_layout.setContentsMargins(12, 12, 12, 12)
            frame_layout.setSpacing(10)
            title_label = QtWidgets.QLabel(title, frame)
            title_label.setStyleSheet(
                "font-size:14px;font-weight:700;color:#274B72;"
            )
            frame_layout.addWidget(title_label)
            return frame, frame_layout

        def make_card(title: str, attr_name: str) -> QtWidgets.QFrame:
            card = QtWidgets.QFrame(content)
            card.setStyleSheet(
                "QFrame { background:#F8FBFE; border:1px solid #D7E2EE; border-radius:10px; }"
            )
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            title_label = QtWidgets.QLabel(title, card)
            title_label.setStyleSheet("font-size:11px;color:#5C718A;font-weight:600;")
            value_label = QtWidgets.QLabel("--", card)
            value_label.setStyleSheet("font-size:17px;font-weight:800;color:#1F4E79;")
            value_label.setWordWrap(True)
            setattr(self.ui, attr_name, value_label)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            return card

        # KPI strip
        kpi_section, kpi_layout = make_section("Dataset Overview")
        kpi_row = QtWidgets.QHBoxLayout()
        kpi_row.setSpacing(10)
        for title, attr_name in (
            ("Depth Range", "lblDISDepthRangeValue"),
            ("Total Samples", "lblDISTotalSamplesValue"),
            ("Number of Curves", "lblDISNumCurvesValue"),
            ("Average Null %", "lblDISAvgNullValue"),
        ):
            kpi_row.addWidget(make_card(title, attr_name))
        kpi_section.layout().addLayout(kpi_row)
        content_layout.addWidget(kpi_section)

        # Depth filter + actions
        filter_section, filter_layout = make_section("Depth Filter")
        filter_row = QtWidgets.QGridLayout()
        filter_row.setHorizontalSpacing(10)
        filter_row.setVerticalSpacing(8)

        lbl_from = QtWidgets.QLabel("From Depth", filter_section)
        lbl_to = QtWidgets.QLabel("To Depth", filter_section)
        spin_from = QtWidgets.QDoubleSpinBox(filter_section)
        spin_to = QtWidgets.QDoubleSpinBox(filter_section)
        for spin in (spin_from, spin_to):
            spin.setDecimals(2)
            spin.setMaximum(1000000.0)
            spin.setMinimum(-1000000.0)
            spin.setSingleStep(1.0)
            spin.setSuffix(" m")
        setattr(self.ui, "spinDISFromDepth", spin_from)
        setattr(self.ui, "spinDISToDepth", spin_to)
        filter_row.addWidget(lbl_from, 0, 0)
        filter_row.addWidget(spin_from, 0, 1)
        filter_row.addWidget(lbl_to, 0, 2)
        filter_row.addWidget(spin_to, 0, 3)
        filter_layout.addLayout(filter_row)
        filter_layout.addWidget(QtWidgets.QLabel("All dashboard panels update dynamically when the depth range changes.", filter_section))
        content_layout.addWidget(filter_section)

        # Core stats and coverage side by side
        stats_row = QtWidgets.QHBoxLayout()
        stats_row.setSpacing(12)

        stats_section, stats_layout = make_section("Curve Statistics")
        core_table = QtWidgets.QTableWidget(stats_section)
        core_table.setAlternatingRowColors(True)
        core_table.setColumnCount(8)
        core_table.setHorizontalHeaderLabels(["Curve", "Unit", "Min", "Max", "Mean", "Std", "Null %", "Count"])
        core_table.horizontalHeader().setStretchLastSection(True)
        core_table.setSortingEnabled(False)
        setattr(self.ui, "tableDISCoreStats", core_table)
        stats_layout.addWidget(core_table)
        stats_row.addWidget(stats_section, 2)

        coverage_section, coverage_layout = make_section("Data Coverage")
        coverage_table = QtWidgets.QTableWidget(coverage_section)
        coverage_table.setAlternatingRowColors(True)
        coverage_table.setColumnCount(4)
        coverage_table.setHorizontalHeaderLabels(["Curve", "Coverage %", "Null %", "Count"])
        coverage_table.horizontalHeader().setStretchLastSection(True)
        coverage_table.setSortingEnabled(False)
        setattr(self.ui, "tableDISCoverage", coverage_table)
        coverage_layout.addWidget(coverage_table)
        stats_row.addWidget(coverage_section, 1)

        stats_container = QtWidgets.QWidget(content)
        stats_container.setLayout(stats_row)
        content_layout.addWidget(stats_container)

        # Distribution viewer
        dist_section, dist_layout = make_section("Distribution Viewer")
        dist_controls = QtWidgets.QGridLayout()
        dist_controls.setHorizontalSpacing(10)
        dist_controls.setVerticalSpacing(8)
        dist_curve_label = QtWidgets.QLabel("Curve", dist_section)
        dist_curve_combo = QtWidgets.QComboBox(dist_section)
        dist_refresh_btn = QtWidgets.QPushButton("Update Distribution", dist_section)
        setattr(self.ui, "comboDISDistCurve", dist_curve_combo)
        setattr(self.ui, "btnDISDistRefresh", dist_refresh_btn)
        dist_controls.addWidget(dist_curve_label, 0, 0)
        dist_controls.addWidget(dist_curve_combo, 0, 1)
        dist_controls.addWidget(dist_refresh_btn, 0, 2)
        dist_layout.addLayout(dist_controls)

        dist_frame = QtWidgets.QFrame(dist_section)
        dist_frame.setMinimumHeight(320)
        dist_frame.setStyleSheet("background:#F8FBFE;border:1px dashed #C9D7E6;border-radius:8px;")
        dist_frame.setLayout(QtWidgets.QVBoxLayout())
        dist_frame.layout().setContentsMargins(0, 0, 0, 0)
        setattr(self.ui, "frameDISDistributionCanvas", dist_frame)
        dist_layout.addWidget(dist_frame)
        content_layout.addWidget(dist_section)


        # Well Data showing
        data_section, data_layout = make_section("Well Data")
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_rename = QtWidgets.QPushButton("Rename Columns...", data_section)
        btn_rename.setStyleSheet("padding: 4px 12px; background: #2A6FD4; color: white; border-radius: 4px; font-weight: bold;")
        setattr(self.ui, "btnDISRenameColumns", btn_rename)
        
        btn_undo = QtWidgets.QPushButton("Undo Rename", data_section)
        btn_undo.setStyleSheet("padding: 4px 12px; background: #F0F4F8; color: #2A6FD4; border: 1px solid #2A6FD4; border-radius: 4px;")
        setattr(self.ui, "btnDISUndoRename", btn_undo)
        
        btn_layout.addWidget(btn_rename)
        btn_layout.addWidget(btn_undo)
        btn_layout.addStretch()
        data_layout.addLayout(btn_layout)
        
        data_view = QtWidgets.QTableView(data_section)
        data_view.setAlternatingRowColors(True)
        data_view.setMinimumHeight(400)
        data_view.setStyleSheet("QTableView { background: #FFFFFF; border: 1px solid #D7E2EE; border-radius: 8px; font-size: 11px; } QTableView::item { padding: 4px; }")
        setattr(self.ui, "tableDISWellData", data_view)
        data_layout.addWidget(data_view)
        content_layout.addWidget(data_section)

        content_layout.addStretch(1)
        scroll_area.setWidget(content)

        inner_tab = getattr(self.ui, "tabDISInner", None)
        if inner_tab is not None:
            inner_tab.hide()

        layout.insertWidget(1, scroll_area)

        spin_from.valueChanged.connect(self.compute_stats)
        spin_to.valueChanged.connect(self.compute_stats)
        dist_curve_combo.currentTextChanged.connect(self.compute_stats)
        dist_refresh_btn.clicked.connect(self.compute_stats)

        self.ui._data_info_dashboard_built = True

        # Correlation matrix display
        corr_section, corr_layout = make_section("Correlation Matrix")
        corr_frame = QtWidgets.QFrame(corr_section)
        corr_frame.setMinimumHeight(360)
        corr_frame.setStyleSheet("background:#F8FBFE;border:1px dashed #C9D7E6;border-radius:8px;")
        corr_frame.setLayout(QtWidgets.QVBoxLayout())
        corr_frame.layout().setContentsMargins(0, 0, 0, 0)
        setattr(self.ui, "frameDISCorrelationCanvas", corr_frame)
        corr_layout.addWidget(corr_frame)
        content_layout.addWidget(corr_section)

    def import_data(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.ui,
            "Import Well Data (Single or Multi-Well)",
            "",
            "Well Data (*.las *.laz *.dlis *.dl *.csv *.xlsx *.xls *.txt *.dat *.asc *.ascii)",
        )
        if not paths:
            return False

        loaded = 0
        failed = 0
        loaded_messages: list[str] = []
        for path in paths:
            try:
                well, msg = load_well(path, replace_nulls=True, depth_unit="m", depth_type="MD")
            except Exception:
                failed += 1
                continue
            self._register_well(well)
            loaded += 1
            loaded_messages.append(msg)

        if loaded == 0:
            QtWidgets.QMessageBox.warning(self.ui, "Import", "No wells were imported.")
            return False

        self._update_well_lists()
        self._refresh_views()

        lines = [f"Imported {loaded} well(s)."]
        for message in loaded_messages[:6]:
            lines.append(f"- {message}")
        if len(loaded_messages) > 6:
            lines.append(f"...and {len(loaded_messages) - 6} more.")
        if failed:
            lines.append(f"Failed imports: {failed}")
        QtWidgets.QMessageBox.information(self.ui, "Import", "\n".join(lines))
        return True

    def remove_current_well(self):
        if not self._wells:
            QtWidgets.QMessageBox.information(self.ui, "Delete Well", "No wells are loaded.")
            return

        target_name = self._current_well or sorted(self._wells.keys())[0]
        reply = QtWidgets.QMessageBox.question(
            self.ui,
            "Delete Well",
            f"Remove well '{target_name}' from this session?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        self._wells.pop(target_name, None)
        self._rename_history.pop(target_name, None)
        self._depth_filter_initialized.discard(target_name)
        self._depth_filter_initialized.discard("All Wells")
        self._all_wells_mode = False

        if self._wells:
            self._current_well = sorted(self._wells.keys())[0]
            self._update_well_lists()
            self._refresh_views()
            return

        self._current_well = None
        self._update_well_lists()
        self._clear_views_without_well()

    def _register_well(self, well) -> None:
        requested_name = str(getattr(well, "name", "") or "Well")
        unique_name = self._unique_well_name(requested_name)
        well.name = unique_name
        self._wells[unique_name] = well
        self._current_well = unique_name
        self._all_wells_mode = False
        self._rename_history.setdefault(unique_name, [])
        self._depth_filter_initialized.discard("All Wells")

    def _unique_well_name(self, requested: str) -> str:
        base = requested.strip() or "Well"
        if base not in self._wells:
            return base
        suffix = 2
        while True:
            candidate = f"{base}_{suffix}"
            if candidate not in self._wells:
                return candidate
            suffix += 1

    def load_data_view(self):
        self._refresh_views()

    def set_current_well(self, name: str):
        if not name:
            return
        if name == "All Wells":
            self._all_wells_mode = True
            self.compute_stats()
            return
        if name not in self._wells:
            return
        self._all_wells_mode = False
        self._current_well = name
        self._refresh_views()

    def on_curve_well_changed(self, name: str):
        if not name or name == "All Wells" or name not in self._wells:
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

    def show_rename_dialog(self):
        well = self._get_current_well()
        if not well:
            return
        df = getattr(well, "data", None)
        if df is None:
            QtWidgets.QMessageBox.information(self.ui, "Rename Column", "No well data loaded.")
            return

        dialog = QtWidgets.QDialog(self.ui)
        dialog.setWindowTitle(f"Rename Columns - {getattr(well, 'name', 'Well')}")
        dialog.resize(350, 450)
        layout = QtWidgets.QVBoxLayout(dialog)

        lbl = QtWidgets.QLabel("Edit the 'New Name' column to rename curves.")
        layout.addWidget(lbl)

        table = QtWidgets.QTableWidget(dialog)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSortingEnabled(False)
        cols = list(df.columns)
        table.setRowCount(len(cols))
        for i, name in enumerate(cols):
            item_orig = QtWidgets.QTableWidgetItem(str(name))
            item_orig.setFlags(item_orig.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(i, 0, item_orig)
            item_new = QtWidgets.QTableWidgetItem(str(name))
            table.setItem(i, 1, item_new)

        layout.addWidget(table)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)

        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_cols = []
            for r in range(table.rowCount()):
                item = table.item(r, 1)
                new_cols.append(item.text().strip() if item else "")
            
            if any(not c for c in new_cols) or len(set(new_cols)) != len(new_cols):
                QtWidgets.QMessageBox.warning(self.ui, "Rename", "Column names must be unique and non-empty.")
                return
            
            if new_cols != cols:
                self._rename_history[well.name].append(cols)
                df.columns = new_cols
                self._refresh_views()

    def compute_stats(self):
        target = self._get_active_analysis_target()
        if target is None:
            return

        well, df = target
        if df is None:
            return

        try:
            self._update_dashboard_overview(well, df)
            self._update_distribution_view(well, df)
            self._update_correlation_view(df)
            self._update_coverage_view(well, df)
            self._update_insight_box(well, df)

            well_data_table = getattr(self.ui, "tableDISWellData", None)
            if well_data_table is not None:
                try:
                    model = PandasModel(df)
                    well_data_table.setModel(model)
                except Exception as e:
                    print("Could not update Pandas model:", e)

            # Only numeric columns
            desc = df.describe().transpose() if not df.empty else df.head(0)
            log_info = getattr(well, "log_info", {}) or {}

            legacy_table = self._get_widget("tableStatistics")
            if legacy_table is not None:
                legacy_rows = []
                for col_name, row in desc.iterrows():
                    legacy_rows.append((
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
                legacy_table.setColumnCount(9)
                legacy_table.setHorizontalHeaderLabels([
                    "Curve", "Count", "Mean", "Std",
                    "Min", "25%", "50%", "75%", "Max"
                ])
                self._fill_table(legacy_table, legacy_rows)

            summary_rows = []
            for col_name, row in desc.iterrows():
                unit = log_info.get(col_name, {}).get("unit", "") if isinstance(log_info, dict) else ""
                series = df[col_name] if col_name in df.columns else None
                null_pct = round(float(series.isna().mean() * 100), 2) if series is not None else 0.0
                summary_rows.append((
                    col_name,
                    unit,
                    self._safe_number(row.get("min", 0)),
                    self._safe_number(row.get("max", 0)),
                    self._safe_number(row.get("mean", 0)),
                    self._safe_number(row.get("std", 0)),
                    f"{null_pct}%",
                    self._safe_number(row.get("count", 0)),
                ))

            for summary_table in (
                self._get_widget("tableDISCoreStats"),
                self._get_widget("tableDISSummary"),
            ):
                if summary_table is not None:
                    summary_table.setColumnCount(8)
                    summary_table.setHorizontalHeaderLabels([
                        "Curve", "Unit", "Min", "Max", "Mean", "Std", "Null %", "Count"
                    ])
                    self._fill_table(summary_table, summary_rows)

        except Exception as e:
            print("Stats Error:", e)

    def export_report(self):
        well = self._get_current_well()
        if not well:
            QtWidgets.QMessageBox.information(self.ui, "Export Report", "Load a well before exporting a report.")
            return

        df = self._filtered_dataframe(well)
        if df is None or df.empty:
            QtWidgets.QMessageBox.information(self.ui, "Export Report", "No data is available in the current depth range.")
            return

        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export Report",
            f"{getattr(well, 'name', 'well')}_report.html",
            "HTML Report (*.html);;CSV Summary (*.csv)",
        )
        if not path:
            return

        if path.lower().endswith(".csv") or ("CSV" in selected_filter and not path.lower().endswith((".html", ".htm"))):
            if not path.lower().endswith(".csv"):
                path = f"{path}.csv"
            self._export_report_csv(well, df, path)
        else:
            if not path.lower().endswith((".html", ".htm")):
                path = f"{path}.html"
            self._export_report_html(well, df, path)

    def _export_report_csv(self, well, df, path: str) -> None:
        import pandas as pd

        desc = df.describe().transpose() if not df.empty else df.head(0)
        log_info = getattr(well, "log_info", {}) or {}
        rows = []
        for col_name, row in desc.iterrows():
            unit = log_info.get(col_name, {}).get("unit", "") if isinstance(log_info, dict) else ""
            series = df[col_name] if col_name in df.columns else None
            null_pct = round(float(series.isna().mean() * 100), 2) if series is not None else 0.0
            rows.append(
                {
                    "Curve": col_name,
                    "Unit": unit,
                    "Min": self._safe_number(row.get("min", 0)),
                    "Max": self._safe_number(row.get("max", 0)),
                    "Mean": self._safe_number(row.get("mean", 0)),
                    "Std": self._safe_number(row.get("std", 0)),
                    "Null %": f"{null_pct}%",
                    "Count": self._safe_number(row.get("count", 0)),
                }
            )
        pd.DataFrame(rows).to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self.ui, "Export Report", f"Report exported:\n{path}")

    def _export_report_html(self, well, df, path: str) -> None:
        import pandas as pd

        overview_rows = []
        depth_col = self._depth_column(df)
        if depth_col is not None and depth_col in df.columns:
            depth_values = df[depth_col].dropna()
            if not depth_values.empty:
                depth_range = f"{self._safe_number(depth_values.min())} to {self._safe_number(depth_values.max())} m"
            else:
                depth_range = "--"
        else:
            depth_range = "--"

        overview_rows.append(("Well", getattr(well, "name", "Unknown")))
        overview_rows.append(("Depth Range", depth_range))
        overview_rows.append(("Total Samples", f"{len(df):,}"))
        overview_rows.append(("Number of Curves", str(len([c for c in df.columns if c != depth_col]))))

        desc = df.describe().transpose() if not df.empty else df.head(0)
        log_info = getattr(well, "log_info", {}) or {}
        summary_rows = []
        for col_name, row in desc.iterrows():
            unit = log_info.get(col_name, {}).get("unit", "") if isinstance(log_info, dict) else ""
            series = df[col_name] if col_name in df.columns else None
            null_pct = round(float(series.isna().mean() * 100), 2) if series is not None else 0.0
            summary_rows.append(
                {
                    "Curve": col_name,
                    "Unit": unit,
                    "Min": self._safe_number(row.get("min", 0)),
                    "Max": self._safe_number(row.get("max", 0)),
                    "Mean": self._safe_number(row.get("mean", 0)),
                    "Std": self._safe_number(row.get("std", 0)),
                    "Null %": f"{null_pct}%",
                    "Count": self._safe_number(row.get("count", 0)),
                }
            )

        overview_html = "".join(
            f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in overview_rows
        )
        summary_html = pd.DataFrame(summary_rows).to_html(index=False, escape=False) if summary_rows else "<p>No statistics available.</p>"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>PetroARX Report - {getattr(well, 'name', 'Well')}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #1E293B; }}
h1 {{ color: #274B72; margin-bottom: 0; }}
h2 {{ color: #274B72; margin-top: 28px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border: 1px solid #D7E2EE; padding: 8px 10px; text-align: left; }}
th {{ background: #F8FBFE; }}
.meta {{ margin-top: 6px; color: #5C718A; }}
</style>
</head>
<body>
<h1>PetroARX Report</h1>
<div class='meta'>Generated for {getattr(well, 'name', 'Unknown well')}</div>
<h2>Overview</h2>
<table>{overview_html}</table>
<h2>Curve Statistics</h2>
{summary_html}
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html)

        QtWidgets.QMessageBox.information(self.ui, "Export Report", f"Report exported:\n{path}")

    def _update_well_lists(self):
        all_well_combos = (
            "comboActiveWell",
            "comboCurveWell",
            "comboZoneWell",
            "comboStatWell",
            "comboDTWell",
            "comboQCWell",
            "comboFeWell",
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
        combos_with_all = {"comboDISWell", "comboHistWell", "comboStatWell"}
        wells_sorted = sorted(self._wells.keys())
        for combo_name in all_well_combos:
            combo = getattr(self.ui, combo_name, None)
            if combo is None or not self._is_live_widget(combo):
                continue
            try:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(wells_sorted)
                if combo_name in combos_with_all:
                    combo.addItem("All Wells")
                if self._current_well:
                    idx = combo.findText(self._current_well)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
            except RuntimeError:
                continue
            finally:
                try:
                    combo.blockSignals(False)
                except RuntimeError:
                    pass

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
        self.compute_stats()
        dashboard_refresh = getattr(self.ui, "refresh_dashboard_tab", None)
        if callable(dashboard_refresh):
            dashboard_refresh()
        porosity_refresh = getattr(self.ui, "refresh_porosity_tab", None)
        if callable(porosity_refresh):
            porosity_refresh()
        corr_refresh = getattr(self.ui, "refresh_well_correlation_tab", None)
        if callable(corr_refresh):
            corr_refresh()
        pp_refresh = getattr(self.ui, "refresh_pore_pressure_tab", None)
        if callable(pp_refresh):
            pp_refresh()
        well3d_refresh = getattr(self.ui, "refresh_3d_well_tab", None)
        if callable(well3d_refresh):
            well3d_refresh()
        facies_refresh = getattr(self.ui, "refresh_facies_classification_tab", None)
        if callable(facies_refresh):
            facies_refresh()

    def _clear_views_without_well(self) -> None:
        for table_name in (
            "tableData",
            "tableRenameColumns",
            "tableDISCoreStats",
            "tableDISCoverage",
            "tableDISHeader",
            "tableDISCurveInfo",
            "tableStatistics",
        ):
            table = getattr(self.ui, table_name, None)
            if table is not None:
                table.clearContents()
                table.setRowCount(0)

        for combo_name in ("comboDISDistCurve", "comboStatCurve", "comboQCCurve"):
            combo = getattr(self.ui, combo_name, None)
            if combo is not None:
                combo.clear()

        for label_name in (
            "lblDISDepthRangeValue",
            "lblDISTotalSamplesValue",
            "lblDISNumCurvesValue",
            "lblDISAvgNullValue",
            "lblDISInsights",
        ):
            label = getattr(self.ui, label_name, None)
            if label is not None:
                label.setText("--")

        dashboard_refresh = getattr(self.ui, "refresh_dashboard_tab", None)
        if callable(dashboard_refresh):
            dashboard_refresh()
        porosity_refresh = getattr(self.ui, "refresh_porosity_tab", None)
        if callable(porosity_refresh):
            porosity_refresh()
        well3d_refresh = getattr(self.ui, "refresh_3d_well_tab", None)
        if callable(well3d_refresh):
            well3d_refresh()

    def _get_active_analysis_target(self):
        if self._all_wells_mode:
            merged = self._build_multiwell_dataframe()
            if merged is None:
                return None
            pseudo_well = SimpleNamespace(name="All Wells", data=merged, log_info={})
            self._ensure_depth_filter_initialized(pseudo_well)
            filtered = self._filtered_dataframe(pseudo_well)
            return pseudo_well, filtered

        well = self._get_current_well()
        if not well:
            return None
        self._ensure_depth_filter_initialized(well)
        filtered = self._filtered_dataframe(well)
        return well, filtered

    def _build_multiwell_dataframe(self):
        import pandas as pd

        frames = []
        for well_name in sorted(self._wells.keys()):
            well = self._wells[well_name]
            df = getattr(well, "data", None)
            if df is None or getattr(df, "empty", True):
                continue
            tagged = df.copy()
            tagged["WELL"] = well_name
            frames.append(tagged)

        if not frames:
            return None
        return pd.concat(frames, ignore_index=True, sort=False)

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
        for combo_name in (
            "comboXplotX",
            "comboXplotY",
            "comboXplotColor",
            "comboLVCrossX",
            "comboLVCrossY",
            "comboLVCrossColor",
            "comboQCCurve",
            "comboHistCurve",
            "comboLVQCCurve",
            "comboLVHistCurve",
            "comboVclGR",
            "comboDISDistCurve",
            "comboGeoDT",
            "comboGeoDTS",
            "comboGeoRHOB",
        ):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            current_text = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            if combo_name in ("comboXplotColor", "comboLVCrossColor"):
                combo.addItem("None")
            combo.addItems(curves)
            if current_text:
                index = combo.findText(current_text)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.blockSignals(False)

        for combo_name, preferred in (
            ("comboGeoDT", "DT"),
            ("comboGeoDTS", "DTS"),
            ("comboGeoRHOB", "RHOB"),
        ):
            combo = getattr(self.ui, combo_name, None)
            if combo is None:
                continue
            idx = combo.findText(preferred)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        if "DEPTH" in df.columns:
            depth_values = df["DEPTH"].dropna()
            if not depth_values.empty:
                for name, value in (
                    ("spinQCFrom", float(depth_values.min())),
                    ("spinQCTo", float(depth_values.max())),
                    ("spinFEFrom", float(depth_values.min())),
                    ("spinFETo", float(depth_values.max())),
                    ("spinLVQCFrom", float(depth_values.min())),
                    ("spinLVQCTo", float(depth_values.max())),
                ):
                    spin = getattr(self.ui, name, None)
                    if spin is not None:
                        spin.blockSignals(True)
                        spin.setValue(value)
                        spin.blockSignals(False)

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

        combo_pairplot = getattr(self.ui, "pairplotcomboBox", None)
        if combo_pairplot is not None:
            default_pair_curves = set(curves[: min(4, len(curves))])
            self._set_checkable_combo(
                combo_pairplot,
                curves,
                default_pair_curves,
                "Select 2-4 curves...",
            )

        pairplot_hue_widget = getattr(self.ui, "pairplotcombocolorby", None)
        if pairplot_hue_widget is not None:
            hue_choices = ["None"] + curves
            # Support both combo and line-edit based UI variants.
            if hasattr(pairplot_hue_widget, "clear") and hasattr(pairplot_hue_widget, "addItems"):
                current_text = pairplot_hue_widget.currentText().strip()
                pairplot_hue_widget.blockSignals(True)
                pairplot_hue_widget.clear()
                pairplot_hue_widget.addItems(hue_choices)
                target_text = current_text if current_text in hue_choices else "None"
                pairplot_hue_widget.setCurrentText(target_text)
                pairplot_hue_widget.blockSignals(False)
            else:
                completer = QtWidgets.QCompleter(hue_choices, pairplot_hue_widget)
                completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
                pairplot_hue_widget.setCompleter(completer)
                if not pairplot_hue_widget.text().strip():
                    pairplot_hue_widget.setText("None")
                pairplot_hue_widget.setPlaceholderText("None or curve name")

        combo_violinplot = getattr(self.ui, "violinplotcomboBox", None)
        if combo_violinplot is not None:
            default_violin_curves = set(curves[: min(4, len(curves))])
            self._set_checkable_combo(
                combo_violinplot,
                curves,
                default_violin_curves,
                "Select 1-4 curves...",
            )

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

    # ── Project Browser Tree Helpers ─────────────────────────────────────────

    # Palette constants for the light-themed tree (must match project_browser_panel.py)
    _C_PROJECT   = "#1565C0"   # deep-blue    – project root
    _C_ACTIVE    = "#2E7D32"   # deep-green   – active well
    _C_INACTIVE  = "#455A64"   # dark slate   – inactive well
    _C_FOLDER    = "#546E7A"   # blue-grey    – sub-folders
    _C_CURVE_RAW = "#455A64"   # dark teal    – raw curve row
    _C_CURVE_CMP = "#E65100"   # deep-orange  – computed curve rows
    _C_BADGE_OK  = "#1B5E20"   # dark-green   – ACTIVE badge foreground
    _C_BADGE_CNT = "#546E7A"   # slate        – curve-count badge 

    def _make_tree_item(
        self,
        col0: str,
        col1: str = "",
        color: str = "#CFD8DC",
        bold: bool = False,
        italic: bool = False,
        font_size: int = 8,
        icon_sp=None,          # QStyle.StandardPixmap or None
    ) -> QtWidgets.QTreeWidgetItem:
        """Create a styled QTreeWidgetItem with consistent font and colour."""
        item = QtWidgets.QTreeWidgetItem([col0, col1])
        fg = QtGui.QColor(color)
        font = QtGui.QFont()
        font.setPointSize(font_size)
        font.setBold(bold)
        font.setItalic(italic)
        for col in (0, 1):
            item.setForeground(col, fg)
            item.setFont(col, font)
        if icon_sp is not None:
            try:
                style = QtWidgets.QApplication.style()
                icon = style.standardIcon(icon_sp)
                item.setIcon(0, icon)
            except Exception:
                pass
        return item

    def _update_project_tree(self):
        """Rebuild the Project tab tree with professional icons and styling."""
        tree = getattr(self.ui, "treeProject", None)
        if tree is None:
            return

        tree.blockSignals(True)
        tree.clear()

        style = QtWidgets.QApplication.style()
        SP = QtWidgets.QStyle

        wells_sorted = sorted(self._wells.keys())
        n_wells = len(wells_sorted)

        # ── Project root node ──────────────────────────────────────────────────
        proj_svc = getattr(getattr(self.ui, "_project_service", None), "current_project", None)
        proj_name = getattr(proj_svc, "name", "Unsaved Project") if proj_svc else "Unsaved Project"
        proj_label = f"{proj_name}"
        proj_badge = f"{n_wells} well{'s' if n_wells != 1 else ''}"

        root = self._make_tree_item(
            proj_label, proj_badge,
            color=self._C_PROJECT,
            bold=True, font_size=9,
            icon_sp=SP.SP_DriveHDIcon,
        )
        tree.addTopLevelItem(root)

        for well_name in wells_sorted:
            well = self._wells[well_name]
            is_active = (well_name == self._current_well)

            # count curves
            df = getattr(well, "data", None)
            log_info = getattr(well, "log_info", {}) or {}
            all_curves = list(df.columns) if df is not None else list(log_info.keys())
            n_curves = len(all_curves)

            # ── Well node ──────────────────────────────────────────────────────
            well_label = well_name
            well_badge = f"● ACTIVE  ·  {n_curves} curves" if is_active else f"{n_curves} curves"
            well_color = self._C_ACTIVE if is_active else self._C_INACTIVE
            well_icon  = SP.SP_MessageBoxInformation if is_active else SP.SP_DirIcon

            well_item = self._make_tree_item(
                well_label, well_badge,
                color=well_color,
                bold=is_active, font_size=9,
                icon_sp=well_icon,
            )
            if is_active:
                # Extra bold green for the active badge column
                badge_font = QtGui.QFont()
                badge_font.setPointSize(8)
                badge_font.setBold(True)
                well_item.setFont(1, badge_font)
                well_item.setForeground(1, QtGui.QColor(self._C_BADGE_OK))
            root.addChild(well_item)

            # ── Well Logs sub-folder ───────────────────────────────────────────
            COMPUTED_SUFFIXES = {"VSH","PHIT","PHIE","SW","SXO","PERM","NET_PAY",
                                  "VWCL","PAYFLAG","VSH_LINEAR","VSH_LARIONOV",
                                  "VSH_CLAVIER","VSH_STEIBER","GR_INDEX"}
            raw_curves, computed_curves = [], []
            for cn in all_curves:
                cnu = str(cn).upper()
                if any(cnu == sfx or cnu.startswith(sfx + "_") for sfx in COMPUTED_SUFFIXES):
                    computed_curves.append(cn)
                else:
                    raw_curves.append(cn)

            logs_folder = self._make_tree_item(
                f"Well Logs  ({n_curves})", "",
                color=self._C_FOLDER,
                italic=True, font_size=8,
                icon_sp=SP.SP_FileDialogDetailedView,
            )
            well_item.addChild(logs_folder)

            # raw curves
            for cn in raw_curves:
                unit = ""
                if cn in log_info:
                    unit = log_info[cn].get("unit", "")
                c_item = self._make_tree_item(
                    str(cn), unit,
                    color=self._C_CURVE_RAW,
                    font_size=8,
                    icon_sp=SP.SP_FileIcon,
                )
                logs_folder.addChild(c_item)

            # computed curves (amber)
            for cn in computed_curves:
                unit = ""
                if cn in log_info:
                    unit = log_info[cn].get("unit", "")
                c_item = self._make_tree_item(
                    str(cn), f"{unit}  [Computed]",
                    color=self._C_CURVE_CMP,
                    font_size=8,
                    icon_sp=SP.SP_FileIcon,
                )
                logs_folder.addChild(c_item)

            # ── Static sub-folders ────────────────────────────────────────────
            static_folders = [
                ("Well Tops",   SP.SP_CommandLink),
                ("Trajectory",  SP.SP_BrowserReload),
                ("Core Data",   SP.SP_DialogResetButton),
                ("DST Data",    SP.SP_FileDialogContentsView),
            ]
            for folder_label, folder_icon in static_folders:
                f_item = self._make_tree_item(
                    folder_label, "",
                    color=self._C_FOLDER,
                    italic=True, font_size=8,
                    icon_sp=folder_icon,
                )
                well_item.addChild(f_item)

        # Expand project root and all well nodes; keep curve folders collapsed
        root.setExpanded(True)
        for i in range(root.childCount()):
            root.child(i).setExpanded(True)

        tree.blockSignals(False)

    def _update_curves_tree(self, well):
        """Rebuild the Curves tab tree with categorised groups and icons."""
        tree = getattr(self.ui, "treeCurves", None)
        if tree is None or well is None:
            return

        tree.blockSignals(True)
        tree.clear()

        style = QtWidgets.QApplication.style()
        SP = QtWidgets.QStyle

        df = getattr(well, "data", None)
        log_info = getattr(well, "log_info", {}) or {}
        all_curves = list(df.columns) if df is not None else list(log_info.keys())

        COMPUTED_KEYS = {"VSH","PHIT","PHIE","SW","SXO","PERM","NET_PAY",
                         "VWCL","PAYFLAG","VSH_LINEAR","VSH_LARIONOV",
                         "VSH_CLAVIER","VSH_STEIBER","GR_INDEX"}
        QC_KEYS = {"QC","FLAG","SPIKE","OUTLIER","MISSING"}

        raw_curves, computed_curves, qc_curves = [], [], []
        for cn in all_curves:
            cnu = str(cn).upper()
            if any(cnu == k or cnu.startswith(k+"_") for k in QC_KEYS):
                qc_curves.append(cn)
            elif any(cnu == k or cnu.startswith(k+"_") for k in COMPUTED_KEYS):
                computed_curves.append(cn)
            else:
                raw_curves.append(cn)

        def _add_group(label: str, curves: list, color: str, badge_color: str, icon_sp):
            if not curves:
                return
            grp_item = QtWidgets.QTreeWidgetItem([f"{label}  ({len(curves)})", "", ""])
            grp_font = QtGui.QFont()
            grp_font.setBold(True)
            grp_font.setPointSize(8)
            grp_item.setFont(0, grp_font)
            grp_item.setForeground(0, QtGui.QColor(badge_color))
            try:
                grp_item.setIcon(0, style.standardIcon(icon_sp))
            except Exception:
                pass
            tree.addTopLevelItem(grp_item)

            for cn in curves:
                info = log_info.get(cn, {}) if isinstance(log_info, dict) else {}
                unit = info.get("unit", "") if isinstance(info, dict) else ""
                ctype = info.get("type", "") if isinstance(info, dict) else ""
                c_item = QtWidgets.QTreeWidgetItem([str(cn), unit, ctype])
                c_font = QtGui.QFont()
                c_font.setPointSize(8)
                c_item.setFont(0, c_font)
                c_item.setForeground(0, QtGui.QColor(color))
                c_item.setForeground(1, QtGui.QColor("#607D8B"))
                c_item.setForeground(2, QtGui.QColor("#546E7A"))
                try:
                    c_item.setIcon(0, style.standardIcon(SP.SP_FileIcon))
                except Exception:
                    pass
                grp_item.addChild(c_item)
            grp_item.setExpanded(True)

        _add_group("Raw Logs",      raw_curves,      self._C_CURVE_RAW, "#1565C0", SP.SP_FileDialogDetailedView)
        _add_group("Computed Logs", computed_curves, self._C_CURVE_CMP, "#E65100", SP.SP_FileDialogInfoView)
        _add_group("QC Flags",      qc_curves,       "#C62828",         "#C62828", SP.SP_MessageBoxWarning)

        tree.blockSignals(False)

    def _get_current_well(self):
        if self._current_well and self._current_well in self._wells:
            return self._wells[self._current_well]
        return None

    def _populate_header_info(self, well):
        table = self._get_widget("tableDISHeader", "tableHeaderInfo")
        if table is None:
            return
        header = getattr(well, "header", {}) or {}
        rows = []
        for section, items in header.items():
            if isinstance(items, dict):
                for key, val in items.items():
                    if isinstance(val, dict):
                        field_name = f"{section}.{key}"
                        value = val.get("value", "")
                        unit = val.get("unit", "")
                        desc = val.get("desc", "")
                    else:
                        field_name = f"{section}.{key}"
                        value = val
                        unit = ""
                        desc = ""
                    rows.append((field_name, value, unit, desc))
            else:
                rows.append((str(section), str(items), "", ""))

        if table.objectName() == "tableDISHeader":
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Field", "Value", "Unit"])
            self._fill_table(table, [(field, value, unit) for field, value, unit, _desc in rows])
            return

        self._fill_table(table, rows)

    def _populate_log_info(self, well):
        df = getattr(well, "data", None)
        log_info = getattr(well, "log_info", {}) or {}

        legacy_table = self._get_widget("tableLogInfo")
        if legacy_table is not None:
            rows = []
            for name, info in log_info.items():
                rows.append((name, info.get("unit", ""), info.get("desc", ""), info.get("type", "")))
            self._fill_table(legacy_table, rows)

        curve_table = self._get_widget("tableDISCurveInfo")
        if curve_table is None:
            return

        rows = []
        columns = list(getattr(df, "columns", [])) if df is not None else list(log_info.keys())
        for name in columns:
            series = df[name] if df is not None and name in df.columns else None
            unit = ""
            if name in log_info:
                unit = log_info[name].get("unit", "")
            min_val, max_val, mean_val, null_pct = self._series_summary(series)
            rows.append((str(name), unit, min_val, max_val, mean_val, null_pct))
        self._fill_table(curve_table, rows)

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
        table.clearContents()
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        table.resizeColumnsToContents()

    def _get_widget(self, *names: str):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget is not None:
                return widget
        return None

    @staticmethod
    def _safe_number(value):
        try:
            return round(float(value), 3)
        except Exception:
            return ""

    def _series_summary(self, series):
        if series is None:
            return "", "", "", ""
        try:
            numeric = series.dropna()
            null_pct = round(series.isna().mean() * 100, 2)
            if numeric.empty:
                return "", "", "", f"{null_pct}%"
            return (
                self._safe_number(numeric.min()),
                self._safe_number(numeric.max()),
                self._safe_number(numeric.mean()),
                f"{null_pct}%",
            )
        except Exception:
            return "", "", "", ""

    def _filtered_dataframe(self, well):
        import pandas as pd

        df = getattr(well, "data", None)
        if df is None:
            return None

        depth_col = self._depth_column(df)
        if depth_col is None:
            return df.copy()

        from_depth, to_depth = self._depth_filter_values()
        if from_depth is None or to_depth is None:
            return df.copy()

        low, high = sorted((from_depth, to_depth))
        depth_values = pd.to_numeric(df[depth_col], errors="coerce")
        filtered = df.loc[depth_values.between(low, high)].copy()
        return filtered if not filtered.empty else df.iloc[0:0].copy()

    def _ensure_depth_filter_initialized(self, well) -> None:
        """Seed the depth filter from the full dataset the first time a well is shown."""
        well_name = getattr(well, "name", None)
        if not well_name or well_name in self._depth_filter_initialized:
            return

        df = getattr(well, "data", None)
        if df is None:
            return

        depth_col = self._depth_column(df)
        if depth_col is None:
            self._depth_filter_initialized.add(well_name)
            return

        import pandas as pd

        depth_values = pd.to_numeric(df[depth_col], errors="coerce").dropna()
        if depth_values.empty:
            self._depth_filter_initialized.add(well_name)
            return

        spin_from = getattr(self.ui, "spinDISFromDepth", None)
        spin_to = getattr(self.ui, "spinDISToDepth", None)
        if spin_from is None or spin_to is None:
            self._depth_filter_initialized.add(well_name)
            return

        current_low, current_high = sorted((float(spin_from.value()), float(spin_to.value())))
        data_low = float(depth_values.min())
        data_high = float(depth_values.max())

        # The generated UI ships with placeholder values (0-7) that do not match real well depth.
        # Seed the filter once so the first dashboard refresh uses the actual depth span.
        if current_high < data_low or current_low > data_high or (current_low == 0.0 and current_high == 7.0):
            spin_from.blockSignals(True)
            spin_to.blockSignals(True)
            spin_from.setValue(data_low)
            spin_to.setValue(data_high)
            spin_from.blockSignals(False)
            spin_to.blockSignals(False)

        self._depth_filter_initialized.add(well_name)

    def _depth_filter_values(self) -> tuple[float | None, float | None]:
        spin_from = getattr(self.ui, "spinDISFromDepth", None)
        spin_to = getattr(self.ui, "spinDISToDepth", None)
        if spin_from is None or spin_to is None:
            return None, None
        return float(spin_from.value()), float(spin_to.value())

    @staticmethod
    def _depth_column(df):
        for name in df.columns:
            if str(name).strip().upper() in {"DEPTH", "DEPT", "MD"}:
                return name
        return None

    @staticmethod
    def _is_live_widget(widget) -> bool:
        try:
            widget.objectName()
            return True
        except RuntimeError:
            return False

    def _numeric_curves(self, df) -> list[str]:
        import pandas as pd

        depth_col = self._depth_column(df)
        curves = []
        for column in df.columns:
            if depth_col is not None and column == depth_col:
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                curves.append(str(column))
        return curves

    def _curve_unit(self, well, curve: str) -> str:
        log_info = getattr(well, "log_info", {}) or {}
        if isinstance(log_info, dict) and curve in log_info:
            return str(log_info[curve].get("unit", ""))
        return ""

    def _update_dashboard_overview(self, well, df) -> None:
        depth_col = self._depth_column(df)
        depth_range = "--"
        if depth_col is not None and depth_col in df.columns:
            depth_values = df[depth_col].dropna()
            if not depth_values.empty:
                depth_range = f"{self._safe_number(depth_values.min())}–{self._safe_number(depth_values.max())} m"

        curves = [str(column) for column in df.columns if self._depth_column(df) != column]
        total_samples = len(df)
        avg_null = 0.0
        if curves:
            null_values = []
            for curve in curves:
                if curve in df.columns:
                    null_values.append(float(df[curve].isna().mean() * 100))
            if null_values:
                avg_null = sum(null_values) / len(null_values)

        lbl_depth = getattr(self.ui, "lblDISDepthRangeValue", None)
        if lbl_depth is not None:
            lbl_depth.setText(depth_range)

        lbl_samples = getattr(self.ui, "lblDISTotalSamplesValue", None)
        if lbl_samples is not None:
            lbl_samples.setText(f"{total_samples:,}")

        lbl_curves = getattr(self.ui, "lblDISNumCurvesValue", None)
        if lbl_curves is not None:
            lbl_curves.setText(str(len(curves)))

        lbl_null = getattr(self.ui, "lblDISAvgNullValue", None)
        if lbl_null is not None:
            lbl_null.setText(f"{avg_null:.1f}%")

        spin_from = getattr(self.ui, "spinDISFromDepth", None)
        spin_to = getattr(self.ui, "spinDISToDepth", None)
        if spin_from is not None and spin_to is not None and depth_col is not None:
            depth_values = df[depth_col].dropna()
            if not depth_values.empty:
                spin_from.blockSignals(True)
                spin_to.blockSignals(True)
                spin_from.setValue(float(depth_values.min()))
                spin_to.setValue(float(depth_values.max()))
                spin_from.blockSignals(False)
                spin_to.blockSignals(False)

    def _update_distribution_view(self, well, df) -> None:
        curve_combo = getattr(self.ui, "comboDISDistCurve", None)
        frame = getattr(self.ui, "frameDISDistributionCanvas", None)
        if curve_combo is None or frame is None:
            return

        import matplotlib.pyplot as plt
        import pandas as pd

        curves = self._numeric_curves(df)
        current_text = curve_combo.currentText().strip()
        curve_combo.blockSignals(True)
        curve_combo.clear()
        curve_combo.addItems(curves)
        if current_text in curves:
            curve_combo.setCurrentText(current_text)
        elif curves:
            curve_combo.setCurrentIndex(0)
        curve_combo.blockSignals(False)

        curve = curve_combo.currentText().strip() if curves else ""
        if not curve or curve not in df.columns:
            self._render_message_figure(frame, "Distribution Viewer", "Select a curve to inspect histogram and boxplot.")
            return

        series = pd.to_numeric(df[curve], errors="coerce").dropna()
        if series.empty:
            self._render_message_figure(frame, "Distribution Viewer", f"No valid numeric samples found for {curve}.")
            return

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
        axes[0].hist(series, bins=24, color="#2A6FD4", alpha=0.85, edgecolor="white")
        axes[0].set_title(f"Histogram of {curve}")
        axes[0].set_xlabel(curve)
        axes[0].set_ylabel("Count")
        axes[0].grid(axis="y", alpha=0.18)

        axes[1].boxplot(series, vert=False, patch_artist=True, boxprops={"facecolor": "#DDEBFF", "color": "#2A6FD4"}, medianprops={"color": "#163A66", "linewidth": 2})
        axes[1].set_title(f"Boxplot of {curve}")
        axes[1].set_yticks([])
        axes[1].set_xlabel(curve)
        axes[1].grid(axis="x", alpha=0.18)

        self._render_figure(frame, fig, f"Distribution: {curve}")

    def _update_correlation_view(self, df) -> None:
        frame = getattr(self.ui, "frameDISCorrelationCanvas", None)
        if frame is None:
            return

        import matplotlib.pyplot as plt
        import seaborn as sns

        curves = self._numeric_curves(df)
        if len(curves) < 2:
            self._render_message_figure(frame, "Correlation Matrix", "Select at least two numeric curves to build the correlation matrix.")
            return

        corr_df = df[curves].corr(numeric_only=True)
        if corr_df.empty:
            self._render_message_figure(frame, "Correlation Matrix", "Correlation matrix is unavailable for the current filter.")
            return

        fig, ax = plt.subplots(figsize=(8.8, 6.6), constrained_layout=True)
        sns.heatmap(
            corr_df,
            ax=ax,
            cmap="RdBu_r",
            center=0,
            vmin=-1,
            vmax=1,
            square=False,
            cbar_kws={"shrink": 0.8},
        )
        ax.set_title("Correlation Matrix", fontsize=13, fontweight="600")
        self._render_figure(frame, fig, "Correlation Matrix")

    def _update_coverage_view(self, well, df) -> None:
        table = getattr(self.ui, "tableDISCoverage", None)
        if table is None:
            return

        curves = [str(column) for column in df.columns if self._depth_column(df) != column]
        table.setRowCount(len(curves))
        rows = []
        total = len(df)
        for curve in curves:
            if curve not in df.columns:
                continue
            series = df[curve]
            null_pct = float(series.isna().mean() * 100) if total else 0.0
            coverage_pct = max(0.0, 100.0 - null_pct)
            rows.append((curve, f"{coverage_pct:.1f}%", f"{null_pct:.1f}%", str(int(series.notna().sum()))))
        self._fill_table(table, rows)

    def _update_insight_box(self, well, df) -> None:
        label = getattr(self.ui, "lblDISInsights", None)
        if label is None:
            return

        curves = self._numeric_curves(df)
        if not curves:
            label.setText("No numeric curves were found in the current selection.")
            return

        notes: list[str] = []
        for curve in curves[:4]:
            unit = self._curve_unit(well, curve)
            series = df[curve].dropna()
            if series.empty:
                continue
            mean_value = float(series.mean())
            if curve.upper() == "GR" and mean_value > 80:
                notes.append("High GR suggests a shale-rich interval.")
            elif curve.upper() in {"RHOB", "DEN", "DENSITY"} and mean_value < 2.25:
                notes.append("Low bulk density can indicate lighter lithology or gas effect.")
            elif curve.upper() in {"NPHI", "PHIN"} and series.max() - series.min() > 0.2:
                notes.append("Neutron porosity spread is significant; review fluid and lithology effects.")
            elif curve.upper() in {"RT", "RES", "RESD", "ILD"} and mean_value > 10:
                notes.append("Resistivity is elevated, which may support hydrocarbon presence.")
            elif unit:
                notes.append(f"{curve} ({unit}) is available for pre-interpretation review.")

        if not notes:
            notes = [
                "Curves are loaded and ready for pre-interpretation analysis.",
                "Use the distribution and correlation panels to choose crossplots and QC checks.",
            ]

        label.setText("\n".join(f"- {note}" for note in notes[:4]))

    def _render_figure(self, frame: QtWidgets.QFrame, fig, title: str) -> None:
        if fig is None or frame is None:
            return
        
        try:
            # Check if frame is still alive (Qt C++ object not deleted)
            frame.objectName()
        except RuntimeError:
            return

        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
            from plotting.plot_context_menu import install_plot_context_menu
        except Exception:
            return

        layout = frame.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setContentsMargins(0, 0, 0, 0)
        
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:#FFFFFF;")
        toolbar = NavigationToolbar(canvas, frame)
        toolbar.setStyleSheet(
            "QToolBar { background:#F7FAFD; border:0; border-bottom:1px solid #D5E1EC; }"
        )

        title_label = QtWidgets.QLabel(title, frame)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet(
            "padding:6px 0 4px 0;font-size:13px;font-weight:600;color:#24466B;"
        )

        layout.addWidget(title_label)
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        canvas.draw_idle()
        install_plot_context_menu(canvas, fig, frame)

        # Close the figure to free up memory from the pyplot global manager
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass

    def _render_message_figure(self, frame: QtWidgets.QFrame, title: str, message: str) -> None:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
        ax.axis("off")
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color="#4A6A8A", wrap=True)
        ax.set_title(title, fontsize=13, fontweight="600")
        self._render_figure(frame, fig, title)
