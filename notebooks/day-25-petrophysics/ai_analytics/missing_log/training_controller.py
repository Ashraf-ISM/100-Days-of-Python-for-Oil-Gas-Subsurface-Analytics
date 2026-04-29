"""
training_controller.py
Handles ML model training, cross-validation, and prediction in a background thread.
"""
from __future__ import annotations

import time
import traceback
from typing import Optional

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtWidgets


# ──────────────────────────────────────────────────────────────────────────────
# Background worker thread and training controller 
# ──────────────────────────────────────────────────────────────────────────────

class TrainingWorker(QtCore.QThread):
    """Runs training on a background thread and emits progress + results."""

    progress = QtCore.pyqtSignal(int, str)          # (percent, status_text) 
    finished = QtCore.pyqtSignal(dict)               # result dict
    failed   = QtCore.pyqtSignal(str)               # error message

    def __init__(self, df: pd.DataFrame, target: str, features: list[str],
                 algorithm: str, test_size: float, cv_folds: int,
                 random_state: int, parent=None):
        super().__init__(parent)
        self.df           = df
        self.target       = target
        self.features     = features 
        self.algorithm    = algorithm
        self.test_size    = test_size
        self.cv_folds     = cv_folds
        self.random_state = random_state

    def run(self):
        t_start = time.perf_counter()
        try:
            self.progress.emit(5, "Preparing data …")
            X, y = self._prepare_data()

            self.progress.emit(20, "Splitting train/test …")
            from sklearn.model_selection import train_test_split, cross_val_score
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.test_size, random_state=self.random_state
            )

            self.progress.emit(35, "Building model …")
            model = self._build_model()

            self.progress.emit(50, "Cross-validating  …")
            cv_scores = cross_val_score(
                model, X_train, y_train,
                cv=self.cv_folds, scoring="r2",
                n_jobs=-1
            )

            self.progress.emit(70, "Training final model …")
            model.fit(X_train, y_train)

            self.progress.emit(85, "Evaluating …")
            from sklearn.metrics import (
                r2_score, mean_squared_error, mean_absolute_error
            )
            y_pred = model.predict(X_test)
            r2   = float(r2_score(y_test, y_pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
            mae  = float(mean_absolute_error(y_test, y_pred))
            mape = float(np.mean(np.abs((y_test - y_pred) / (np.abs(y_test) + 1e-9))) * 100)

            # Feature importances (if available)
            importances: dict[str, float] = {}
            if hasattr(model, "feature_importances_"):
                for name, imp in zip(self.features, model.feature_importances_):
                    importances[name] = float(imp)
            elif hasattr(model, "coef_"):
                for name, coef in zip(self.features, model.coef_.ravel()):
                    importances[name] = abs(float(coef))

            duration = time.perf_counter() - t_start
            minutes  = int(duration // 60)
            seconds  = int(duration % 60)

            self.progress.emit(100, "Completed ✔")
            self.finished.emit({
                "model":       model,
                "r2":          r2,
                "rmse":        rmse,
                "mae":         mae,
                "mape":        mape,
                "cv_scores":   cv_scores.tolist(),
                "cv_mean":     float(cv_scores.mean()),
                "cv_std":      float(cv_scores.std()),
                "importances": importances,
                "n_train":     len(X_train),
                "n_test":      len(X_test),
                "n_features":  len(self.features),
                "duration":    f"{minutes:02d}:{seconds:02d}",
                "algorithm":   self.algorithm,
                "X_test":      X_test,
                "y_test":      y_test,
                "y_pred":      y_pred,
            })

        except Exception as exc:
            self.failed.emit(traceback.format_exc())

    # ── helpers ────────────────────────────────────────────────────────────────

    def _prepare_data(self):
        df = self.df.copy()
        # Drop rows where ANY selected column is NaN
        cols = self.features + [self.target]
        df = df[cols].dropna()
        X = df[self.features].values
        y = df[self.target].values
        return X, y

    def _build_model(self):
        algo = self.algorithm.lower()
        rs   = self.random_state

        if "xgboost" in algo:
            try:
                from xgboost import XGBRegressor
                return XGBRegressor(n_estimators=200, random_state=rs,
                                    verbosity=0, n_jobs=-1)
            except ImportError:
                pass  # fall through to sklearn RF

        if "lightgbm" in algo:
            try:
                from lightgbm import LGBMRegressor
                return LGBMRegressor(n_estimators=200, random_state=rs,
                                     verbose=-1, n_jobs=-1)
            except ImportError:
                pass

        if "catboost" in algo:
            try:
                from catboost import CatBoostRegressor
                return CatBoostRegressor(iterations=200, random_seed=rs,
                                         verbose=0)
            except ImportError:
                pass

        if "neural" in algo or "ann" in algo:
            try:
                from sklearn.neural_network import MLPRegressor
                return MLPRegressor(hidden_layer_sizes=(128, 64, 32),
                                    max_iter=500, random_state=rs)
            except Exception:
                pass

        if "support vector" in algo or "svr" in algo:
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import make_pipeline
            from sklearn.svm import SVR
            return make_pipeline(StandardScaler(), SVR(kernel="rbf"))

        # Default: Random Forest
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=200, random_state=rs, n_jobs=-1)


# ──────────────────────────────────────────────────────────────────────────────
# High-level training controller
# ──────────────────────────────────────────────────────────────────────────────

class TrainingController:
    """
    Manages a single training session for the Missing Log window.
    """

    def __init__(self, window):
        """window: the MissingLogPredictionWindow instance."""
        self._win    = window
        self._worker: Optional[TrainingWorker] = None
        self._result: Optional[dict]           = None

    def start_training(self):
        """Kick off a background training job."""
        win = self._win
        df  = getattr(win, "_df", None)
        if df is None or df.empty:
            QtWidgets.QMessageBox.warning(win, "Training",
                                          "Please load well data first.")
            return

        target   = win.cboTargetLog.currentText()
        features = win.get_selected_features()
        if not features:
            QtWidgets.QMessageBox.warning(win, "Training",
                                          "Select at least one input feature.")
            return

        # Gather algorithm / CV settings
        algorithm    = win.cboAlgorithm.currentText() if hasattr(win, "cboAlgorithm") else "Random Forest"
        cv_text      = win.cboCrossVal.currentText()  if hasattr(win, "cboCrossVal")  else "5-Fold"
        cv_folds     = int(cv_text.split("-")[0]) if cv_text[0].isdigit() else 5
        test_pct     = win.sliderTestSize.value() / 100.0 if hasattr(win, "sliderTestSize") else 0.2
        random_state = win.spinRandState.value()  if hasattr(win, "spinRandState")   else 42

        self._worker = TrainingWorker(
            df=df, target=target, features=features,
            algorithm=algorithm, test_size=test_pct,
            cv_folds=cv_folds, random_state=random_state,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, pct: int, text: str):
        win = self._win
        if hasattr(win, "progressTraining"):
            win.progressTraining.setValue(pct)
        if hasattr(win, "statusCompleted"):
            win.statusCompleted.setText(text)

    def _on_finished(self, result: dict):
        self._result = result
        win = self._win

        # Update metric labels
        _set(win, "metricValGreen", f"{result['r2']:.4f}")
        _set(win, "metricValBlue",  f"{result['rmse']:.4f}")
        _set(win, "metricValBlue",  f"{result['mae']:.4f}")
        _set(win, "metricValOrange",f"{result['mape']:.2f}%")

        # Training panel
        _set(win, "metricVal",     f"{result['n_train']:,}", index=1)
        _set(win, "metricVal",     f"{result['n_test']:,}",  index=2)
        _set(win, "metricVal",     f"{result['n_features']}", index=3)
        _set(win, "statusCompleted", "✔  Completed")
        _set(win, "lblTrainTimeVal", result["duration"])

        # Progress bar
        if hasattr(win, "progressTraining"):
            win.progressTraining.setValue(100)

        QtWidgets.QMessageBox.information(
            win, "Training Complete",
            f"✔ Training finished!\n\n"
            f"R²={result['r2']:.4f} | RMSE={result['rmse']:.4f}\n"
            f"MAE={result['mae']:.4f} | MAPE={result['mape']:.2f}%\n\n"
            f"CV mean R² = {result['cv_mean']:.4f} ± {result['cv_std']:.4f}\n"
            f"Training time: {result['duration']}"
        )

    def _on_failed(self, msg: str):
        win = self._win
        if hasattr(win, "statusCompleted"):
            win.statusCompleted.setText("✖  Failed")
        QtWidgets.QMessageBox.critical(win, "Training Error", msg)

    @property
    def last_result(self) -> Optional[dict]:
        return self._result


def _set(win, name: str, val: str, index: int = 0):
    """Helper: set text on a named or indexed widget."""
    widgets = win.findChildren(QtWidgets.QLabel, name)
    if widgets and index < len(widgets):
        widgets[index].setText(val)
