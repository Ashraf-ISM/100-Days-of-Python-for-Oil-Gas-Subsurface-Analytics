"""
model_manager.py
Handles saving and loading trained scikit-learn compatible models to/from disk.
"""
from __future__ import annotations

import pickle
from pathlib import Path

from PyQt5 import QtWidgets


class ModelManager:
    """Saves and loads models for the Missing Log Prediction module."""

    def save_model(self, model, metadata: dict, parent_widget=None):
        """Prompt the user for a file path and pickle the model + metadata.""" 
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent_widget, "Save Model",
            "missing_log_model.pkl",
            "Pickle files (*.pkl);;All Files (*)"
        )
        if not path:
            return False

        payload = {"model": model, "metadata": metadata}
        try:
            with open(path, "wb") as fh:
                pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
            QtWidgets.QMessageBox.information(
                parent_widget, "Save Model",
                f"✔  Model saved successfully:\n{path}"
            )
            return True
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                parent_widget, "Save Model Error",
                f"Could not save model:\n{exc}"
            )
            return False

    def load_model(self, parent_widget=None):
        """Prompt the user for a pickle file and return (model, metadata)."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent_widget, "Load Model", "",
            "Pickle files (*.pkl);;All Files (*)"
        )
        if not path:
            return None, None

        try:
            with open(path, "rb") as fh:
                payload = pickle.load(fh)
            model    = payload.get("model")
            metadata = payload.get("metadata", {})
            QtWidgets.QMessageBox.information(
                parent_widget, "Load Model",
                f"✔  Model loaded:\n{Path(path).name}\n\n"
                f"Algorithm: {metadata.get('algorithm', 'Unknown')}\n"
                f"Target: {metadata.get('target', 'Unknown')}\n"
                f"Features: {metadata.get('features', [])}"
            )
            return model, metadata
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                parent_widget, "Load Model Error",
                f"Could not load model:\n{exc}"
            )
            return None, None
