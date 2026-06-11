"""
correlation_viewer.py
Opens a professional feature correlation matrix dialog.
"""
from __future__ import annotations

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui


class CorrelationMatrixDialog(QtWidgets.QDialog):
    """
    Shows a heatmap correlation matrix using matplotlib embedded in PyQt5.
    Dynamically adapts layout and label density based on number of features.
    """

    def __init__(self, df, target_log: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Feature Correlation Matrix")
        self.setMinimumSize(900, 700)
        self.resize(1000, 760)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)

        # ─── header ────────────────────────────────────────────────────────────
        header = QtWidgets.QLabel(
            f"📊  Correlation Matrix  —  Target: <b>{target_log}</b>"
        )
        header.setStyleSheet(
            "font-size:14px; color:#1E293B; font-weight:700; padding:6px 0;"
        )
        main_layout.addWidget(header)

        info = QtWidgets.QLabel(
            "Cells show Pearson correlation coefficient."
            "Select a feature log and click <b>Use as Feature</b> to add to the model."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:11px; color:#64748B; margin-bottom:6px;")
        main_layout.addWidget(info)

        # ─── scrollable content area ───────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, stretch=1)

        # ─── embed matplotlib ──────────────────────────────────────────────────
        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
            import matplotlib.ticker as ticker

            numeric = df.select_dtypes(include=[np.number])
            corr = numeric.corr()
            cols = list(corr.columns)
            n = len(cols)

            # ── dynamic sizing ─────────────────────────────────────────────────
            cell_px   = max(32, min(60, 480 // max(n, 1)))
            fig_w_in  = max(7, n * cell_px / 80 + 2.5)
            fig_h_in  = max(5.5, n * cell_px / 80 + 2.0)
            fig_w_in  = min(fig_w_in, 16)
            fig_h_in  = min(fig_h_in, 12)

            fig = Figure(figsize=(fig_w_in, fig_h_in), dpi=100)
            fig.patch.set_facecolor("#F8FAFC")
            ax = fig.add_subplot(111)
            ax.set_facecolor("#F8FAFC")

            # diverging colormap
            cmap = plt.get_cmap("RdYlGn")
            im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="equal")

            # colorbar
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, shrink=0.85)
            cbar.ax.tick_params(labelsize=8)

            # ── tick labels ────────────────────────────────────────────────────
            ax.set_xticks(range(n))
            ax.set_yticks(range(n))

            # adaptive font size for labels
            if n <= 10:
                label_fs = 9
            elif n <= 20:
                label_fs = 7.5
            elif n <= 30:
                label_fs = 6.5
            else:
                label_fs = 5.5

            ax.set_xticklabels(
                cols, rotation=90, ha="center", va="top",
                fontsize=label_fs, fontfamily="monospace"
            )
            ax.set_yticklabels(
                cols, fontsize=label_fs, fontfamily="monospace"
            )

            # move x-ticks to top so they don't clash with bottom panel
            ax.xaxis.set_ticks_position("top")
            ax.xaxis.set_label_position("top")

            # minor ticks for grid lines between cells
            ax.set_xticks([x - 0.5 for x in range(1, n)], minor=True)
            ax.set_yticks([y - 0.5 for y in range(1, n)], minor=True)
            ax.grid(which="minor", color="#CBD5E1", linewidth=0.4)
            ax.tick_params(which="minor", length=0)

            # ── cell annotations (only when matrix is small enough) ────────────
            if n <= 15:
                ann_fs = max(5, 8 - n * 0.15)
                for i in range(n):
                    for j in range(n):
                        val = corr.values[i, j]
                        txt_color = "white" if abs(val) > 0.65 else "#1E293B"
                        ax.text(
                            j, i, f"{val:.2f}",
                            ha="center", va="center",
                            fontsize=ann_fs, color=txt_color,
                            fontweight="bold"
                        )

            # ── highlight target row / col ─────────────────────────────────────
            if target_log in cols:
                tidx = cols.index(target_log)
                for spine_pos in [tidx - 0.5, tidx + 0.5]:
                    ax.axhline(spine_pos, color="#2563EB", linewidth=2, zorder=5)
                    ax.axvline(spine_pos, color="#2563EB", linewidth=2, zorder=5)

                ax.set_title(
                    f"Pearson Correlation  —  Highlighted: {target_log}",
                    fontsize=12, color="#1E293B", fontweight="bold",
                    pad=12, loc="left"
                )
            else:
                ax.set_title(
                    "Pearson Correlation Matrix",
                    fontsize=12, color="#1E293B", fontweight="bold",
                    pad=12, loc="left"
                )

            fig.tight_layout(pad=1.5)

            canvas = FigureCanvas(fig)
            # set fixed canvas height so it doesn't squash
            canvas_h = int(fig_h_in * 100)
            canvas.setMinimumHeight(canvas_h)
            canvas.setMaximumHeight(canvas_h + 80)
            content_layout.addWidget(canvas)

            # ─── sorted importance panel ───────────────────────────────────────
            if target_log in cols:
                self._build_importance_panel(content_layout, corr, target_log)

        except ImportError:
            content_layout.addWidget(
                QtWidgets.QLabel(
                    "⚠  matplotlib is required for this view.\n\npip install matplotlib"
                )
            )

        # ─── close button ──────────────────────────────────────────────────────
        close_btn = QtWidgets.QPushButton("✕  Close")
        close_btn.setStyleSheet(
            "background:#F1F5F9; color:#374151; border-radius:6px; "
            "padding:6px 20px; font-weight:600;"
        )
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

    # ───────────────────────────────────────────────────────────────────────────
    def _build_importance_panel(self, layout: QtWidgets.QVBoxLayout,
                                 corr, target_log: str):
        """Ranked correlation bar panel below the heatmap."""
        grp = QtWidgets.QGroupBox(
            f"Correlation with '{target_log}' (sorted by |r|) "
        )
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
                f"font-size:10px; font-weight:700; "
                f"color:{'#059669' if val >= 0 else '#DC2626'};"
            )
            row.addWidget(val_lbl)

            grp_layout.addLayout(row)

        layout.addWidget(grp)
