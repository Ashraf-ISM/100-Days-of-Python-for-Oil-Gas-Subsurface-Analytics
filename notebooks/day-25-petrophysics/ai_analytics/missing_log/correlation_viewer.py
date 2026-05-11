"""
correlation_viewer.py
Opens a professional feature correlation matrix dialog .
"""
from __future__ import annotations

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui 


class CorrelationMatrixDialog(QtWidgets.QDialog):
    """
    Shows a heatmap correlation matrix using matplotlib embedded in PyQt5  .
    """

    def __init__(self, df, target_log: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Feature Correlation Matrix")
        self.setMinimumSize(800, 640)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        layout = QtWidgets.QVBoxLayout(self)

        # ─── header ────────────────────────────────────────────────────────────
        header = QtWidgets.QLabel(
            f"📊  Correlation Matrix  —  Target: <b>{target_log}</b>"
        ) 
        header.setStyleSheet(
            "font-size:14px; color:#1E293B; font-weight:700; padding:6px 0;"
        )
        layout.addWidget(header) 

        info = QtWidgets.QLabel(
            "Cells show Pearson correlation coefficient. "
            "Select a feature log and click <b>Use as Feature</b> to add to the model."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:11px; color:#64748B; margin-bottom:6px;")
        layout.addWidget(info)

        # ─── embed matplotlib ──────────────────────────────────────────────────
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors

            numeric = df.select_dtypes(include=[np.number])
            corr = numeric.corr()

            fig, ax = plt.subplots(figsize=(10, 7))
            fig.patch.set_facecolor("#F8FAFC")
            ax.set_facecolor("#F8FAFC")

            # diverging colormap: blue = positive, red = negative
            cmap = plt.get_cmap("RdYlGn")
            im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

            cols = list(corr.columns)
            ax.set_xticks(range(len(cols)))
            ax.set_yticks(range(len(cols)))
            ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels(cols, fontsize=8)

            # annotate cells
            for i in range(len(cols)):
                for j in range(len(cols)):
                    val = corr.values[i, j]
                    color = "white" if abs(val) > 0.6 else "black"
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            fontsize=7, color=color, fontweight="bold")

            # highlight target row/col
            if target_log in cols:
                tidx = cols.index(target_log)
                ax.axhline(tidx - 0.5, color="#2563EB", linewidth=2)
                ax.axhline(tidx + 0.5, color="#2563EB", linewidth=2)
                ax.axvline(tidx - 0.5, color="#2563EB", linewidth=2)
                ax.axvline(tidx + 0.5, color="#2563EB", linewidth=2)

                # Add sorted bar chart for target log on the side
                target_corr = corr[target_log].drop(target_log).sort_values()
                ax.set_title(
                    f"Pearson Correlation — Highlighted: {target_log}",
                    fontsize=12, color="#1E293B", fontweight="bold", pad=10
                )

            fig.tight_layout()

            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

            # ─── sorted importance panel ───────────────────────────────────────
            if target_log in cols:
                self._build_importance_panel(layout, corr, target_log)

        except ImportError:
            layout.addWidget(
                QtWidgets.QLabel("⚠  matplotlib is required for this view.\n\npip install matplotlib")
            )

        # ─── close button ──────────────────────────────────────────────────────
        close_btn = QtWidgets.QPushButton("✕  Close")
        close_btn.setStyleSheet(
            "background:#F1F5F9; color:#374151; border-radius:6px; padding:6px 20px; font-weight:600;"
        )
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

    def _build_importance_panel(self, layout: QtWidgets.QVBoxLayout,
                                 corr, target_log: str):
        """Ranked correlation bar panel below the heatmap."""
        grp = QtWidgets.QGroupBox(f"Correlation with '{target_log}' (sorted by |r|)")
        grp.setStyleSheet(
            "QGroupBox { font-size:11px; font-weight:700; color:#1E293B; "
            "border:1px solid #E2E8F0; border-radius:8px; margin-top:8px; }"
            "QGroupBox::title { subcontrol-origin:margin; padding:4px 8px; }"
        )
        grp_layout = QtWidgets.QVBoxLayout(grp)

        target_corr = corr[target_log].drop(target_log).sort_values(
            key=lambda x: x.abs(), ascending=False
        )

        for curve, val in target_corr.items():
            row = QtWidgets.QHBoxLayout()

            name_lbl = QtWidgets.QLabel(str(curve))
            name_lbl.setFixedWidth(140)
            name_lbl.setStyleSheet("font-size:10px; color:#374151;")
            row.addWidget(name_lbl)

            bar = QtWidgets.QProgressBar()
            bar.setMaximum(100)
            bar.setValue(int(abs(val) * 100))
            color = "#10B981" if val >= 0 else "#EF4444"
            bar.setStyleSheet(
                f"QProgressBar {{ background:#E2E8F0; border-radius:4px; height:10px; }}"
                f"QProgressBar::chunk {{ background:{color}; border-radius:4px; }}"
            )
            bar.setTextVisible(False)
            row.addWidget(bar)

            val_lbl = QtWidgets.QLabel(f"{val:+.3f}")
            val_lbl.setFixedWidth(54)
            val_lbl.setStyleSheet(
                f"font-size:10px; font-weight:700; color:{'#059669' if val>=0 else '#DC2626'};"
            )
            row.addWidget(val_lbl)

            grp_layout.addLayout(row)

        layout.addWidget(grp)
