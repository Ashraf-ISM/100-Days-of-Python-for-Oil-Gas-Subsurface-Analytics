from __future__ import annotations

from pathlib import Path

from PyQt5 import QtWidgets, uic

THIS_DIR = Path(__file__).resolve().parent
UI_PATH = THIS_DIR.parent / "ui" / "calculationgui.ui"


class CalculationWindow(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        uic.loadUi(str(UI_PATH), self)
        self._wire_ui()
        self._update_formula_preview()

    def set_available_curves(self, curves: list[str]) -> None:
        curves = [str(curve) for curve in curves]
        for combo_name in ("comboLeftCurve", "comboRightCurve"):
            combo = getattr(self, combo_name, None)
            if combo is None:
                continue
            current_text = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(curves)
            if current_text:
                index = combo.findText(current_text)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.blockSignals(False)
        self._update_formula_preview()

    def _wire_ui(self) -> None:
        for widget_name, signal_name in (
            ("comboLeftCurve", "currentTextChanged"),
            ("comboOperation", "currentTextChanged"),
            ("comboRightCurve", "currentTextChanged"),
            ("lineOutputCurve", "textChanged"),
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                getattr(widget, signal_name).connect(self._update_formula_preview)

        button = getattr(self, "btnRunCalculation", None)
        if button is not None:
            button.clicked.connect(self._show_placeholder_message)

        button_box = getattr(self, "buttonBox", None)
        if button_box is not None:
            button_box.rejected.connect(self.close)

    def _update_formula_preview(self) -> None:
        left = self._current_combo_text("comboLeftCurve", "CURVE_A")
        operation = self._current_combo_text("comboOperation", "+")
        right = self._current_combo_text("comboRightCurve", "CURVE_B")
        output = self._line_text("lineOutputCurve", "CALC_RESULT")

        preview = getattr(self, "plainFormulaPreview", None)
        if preview is not None:
            preview.setPlainText(f"{output} = {left} {operation} {right}")

    def _show_placeholder_message(self) -> None:
        formula = getattr(self, "plainFormulaPreview", None)
        formula_text = formula.toPlainText() if formula is not None else "Calculation"
        QtWidgets.QMessageBox.information(
            self,
            "Calculation Workspace",
            f"Workspace opened successfully.\n\nSelected formula:\n{formula_text}",
        )

    def _current_combo_text(self, name: str, fallback: str) -> str:
        combo = getattr(self, name, None)
        if combo is None:
            return fallback
        text = combo.currentText().strip()
        return text or fallback

    def _line_text(self, name: str, fallback: str) -> str:
        line_edit = getattr(self, name, None)
        if line_edit is None:
            return fallback
        text = line_edit.text().strip()
        return text or fallback
