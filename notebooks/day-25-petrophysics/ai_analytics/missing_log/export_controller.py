"""
export_controller.py
Handles exporting prediction results (CSV, LAS, HTML report).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from PyQt5 import QtWidgets


class ExportController:
    """Exports prediction results from the Missing Log module."""

    def export_results(self, df: pd.DataFrame, target: str, features: list[str],
                       result: dict, parent_widget=None):
        """
        Prompt user to choose a format and save results.
        result must contain y_test, y_pred arrays and metric scores.
        """
        path, fmt = QtWidgets.QFileDialog.getSaveFileName(
            parent_widget, "Export Prediction Results",
            f"{target}_prediction_results.csv",
            "CSV File (*.csv);;HTML Report (*.html);;All Files (*)"
        )
        if not path:
            return

        if "html" in fmt.lower() or path.lower().endswith(".html"):
            self._export_html(path, target, features, result, parent_widget)
        else:
            self._export_csv(path, target, result, parent_widget)

    # ── CSV ───────────────────────────────────────────────────────────────────

    def _export_csv(self, path: str, target: str, result: dict, parent):
        try:
            rows = []
            for actual, predicted in zip(result["y_test"], result["y_pred"]):
                rows.append({
                    "Actual":    float(actual),
                    "Predicted": float(predicted),
                    "Residual":  float(actual - predicted),
                })
            pd.DataFrame(rows).to_csv(path, index=False)
            QtWidgets.QMessageBox.information(
                parent, "Export", f"✔  Results saved to:\n{path}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(parent, "Export Error", str(exc))

    # ── HTML ──────────────────────────────────────────────────────────────────

    def _export_html(self, path: str, target: str, features: list[str],
                     result: dict, parent):
        try:
            algo = result.get("algorithm", "Unknown")
            r2   = result.get("r2", 0)
            rmse = result.get("rmse", 0)
            mae  = result.get("mae", 0)
            mape = result.get("mape", 0)
            dur  = result.get("duration", "—")
            imps = result.get("importances", {})

            imp_rows = "".join(
                f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
                for k, v in sorted(imps.items(), key=lambda x: -x[1])
            )

            html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Missing Log Prediction Report — {target}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background:#F8FAFC; color:#1E293B; margin:24px; }}
h1 {{ color:#1D4ED8; }}
h2 {{ color:#374151; border-bottom:2px solid #E2E8F0; padding-bottom:6px; margin-top:24px; }}
table {{ border-collapse:collapse; width:100%; margin-top:12px; }}
th,td {{ border:1px solid #E2E8F0; padding:8px 12px; text-align:left; font-size:13px; }}
th {{ background:#EFF6FF; font-weight:700; color:#1D4ED8; }}
.badge {{ display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:700; }}
.green {{ background:#D1FAE5; color:#059669; }}
.blue  {{ background:#DBEAFE; color:#1D4ED8; }}
.orange{{ background:#FEF3C7; color:#D97706; }}
</style>
</head>
<body>
<h1>Missing Log Prediction — {target}</h1>
<p>Algorithm: <b>{algo}</b> &nbsp;|&nbsp; Training time: <b>{dur}</b></p>

<h2>Model Performance</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>R² Score</td><td><span class='badge green'>{r2:.4f}</span></td></tr>
<tr><td>RMSE</td><td><span class='badge blue'>{rmse:.4f}</span></td></tr>
<tr><td>MAE</td><td><span class='badge blue'>{mae:.4f}</span></td></tr>
<tr><td>MAPE</td><td><span class='badge orange'>{mape:.2f}%</span></td></tr>
<tr><td>CV Mean R²</td><td>{result.get('cv_mean', 0):.4f} ± {result.get('cv_std', 0):.4f}</td></tr>
<tr><td>Train Samples</td><td>{result.get('n_train', 0):,}</td></tr>
<tr><td>Test Samples</td><td>{result.get('n_test', 0):,}</td></tr>
</table>

<h2>Feature Importances</h2>
<table>
<tr><th>Feature</th><th>Importance</th></tr>
{imp_rows}
</table>

<h2>Prediction Sample (first 20)</h2>
<table>
<tr><th>#</th><th>Actual</th><th>Predicted</th><th>Residual</th></tr>
"""
            y_test = result.get("y_test", [])
            y_pred = result.get("y_pred", [])
            for i in range(min(20, len(y_test))):
                actual    = float(y_test[i])
                predicted = float(y_pred[i])
                residual  = actual - predicted
                html += (
                    f"<tr><td>{i+1}</td><td>{actual:.4f}</td>"
                    f"<td>{predicted:.4f}</td><td>{residual:+.4f}</td></tr>\n"
                )

            html += "</table>\n</body>\n</html>"

            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)

            QtWidgets.QMessageBox.information(
                parent, "Export", f"✔  HTML report saved to:\n{path}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(parent, "Export Error", str(exc))
