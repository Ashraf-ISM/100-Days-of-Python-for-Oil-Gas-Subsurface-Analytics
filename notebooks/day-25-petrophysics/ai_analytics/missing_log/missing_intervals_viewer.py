"""
missing_intervals_viewer.py
Shows a table of detected missing intervals for the target log.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui


class MissingIntervalsDialog(QtWidgets.QDialog):
    """
    Detects and displays contiguous missing intervals in the selected log.
    """

    def __init__(self, df: pd.DataFrame, target_log: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Missing Intervals — {target_log}")
        self.setMinimumSize(560, 420)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._df = df
        self._target = target_log

        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header = QtWidgets.QLabel(
            f"🔍  Detected Missing Intervals for <b>{target_log}</b>"
        )
        header.setStyleSheet("font-size:13px; font-weight:700; color:#1E293B; padding:4px 0;")
        layout.addWidget(header)

        intervals = self._detect_intervals()

        summary = QtWidgets.QLabel(
            f"Found <b>{len(intervals)}</b> missing interval(s)  |  "
            f"Total missing: <b>{sum(e - s for s, e in intervals):,}</b> samples"
        )
        summary.setStyleSheet("font-size:11px; color:#64748B; margin-bottom:6px;")
        layout.addWidget(summary)

        # Table
        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["#", "Start Index", "End Index", "Length", "Depth Range"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setStyleSheet(
            "QTableWidget { font-size:11px; border:1px solid #E2E8F0; border-radius:6px; }"
            "QHeaderView::section { background:#F1F5F9; font-weight:700; color:#374151; "
            "border:none; padding:4px 8px; }"
        )

        depth_col = next((c for c in df.columns if c.upper() in ["DEPTH","DEPT","MD"]), None)
        table.setRowCount(len(intervals))
        for i, (start, end) in enumerate(intervals):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(start)))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(end - 1)))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(end - start)))
            if depth_col is not None:
                d_start = df[depth_col].iloc[start] if start < len(df) else "—"
                d_end = df[depth_col].iloc[min(end - 1, len(df) - 1)]
                table.setItem(i, 4, QtWidgets.QTableWidgetItem(
                    f"{d_start:.1f} – {d_end:.1f} m"
                ))
            else:
                table.setItem(i, 4, QtWidgets.QTableWidgetItem("N/A"))

        layout.addWidget(table)

        # Close button
        btn = QtWidgets.QPushButton("✕  Close")
        btn.setStyleSheet(
            "background:#F1F5F9; color:#374151; border-radius:6px; padding:6px 20px; font-weight:600;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignRight)

    def _detect_intervals(self) -> list[tuple[int, int]]:
        """Return list of (start, end) row index pairs for NaN runs."""
        if self._target not in self._df.columns:
            return []
        is_nan = self._df[self._target].isna()
        intervals: list[tuple[int, int]] = []
        in_gap = False
        start = 0
        for idx, flag in enumerate(is_nan):
            if flag and not in_gap:
                start = idx
                in_gap = True
            elif not flag and in_gap:
                intervals.append((start, idx))
                in_gap = False
        if in_gap:
            intervals.append((start, len(is_nan)))
        return intervals
