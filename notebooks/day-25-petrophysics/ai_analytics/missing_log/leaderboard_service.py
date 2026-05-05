"""
leaderboard_service.py
----------------------
Trains multiple ML algorithms sequentially in a background thread and
emits a ranked leaderboard (by R² score) when done.

Supported algorithms (in order of training):
  1. XGBoost Regressor
  2. LightGBM
  3. Random Forest
  4. CatBoost

Usage::

    svc = LeaderboardService(df, target, features, random_state=42)
    svc.leaderboard_ready.connect(my_slot)   # slot receives list[dict]
    svc.progress.connect(update_status)       # slot receives (pct, message)
    svc.start()
"""
from __future__ import annotations

import time
import traceback
from typing import List

import numpy as np
import pandas as pd

from PyQt5.QtCore import QThread, pyqtSignal


class LeaderboardService(QThread):
    """
    Background thread that trains multiple algorithms and returns a ranked table.

    Signals
    -------
    progress(int, str)         : percent complete and status message
    leaderboard_ready(list)    : list of dicts [{model, r2, rmse}, ...]
                                  sorted by r2 descending
    failed(str)                : error traceback on unexpected exception
    """

    progress          = pyqtSignal(int, str)
    leaderboard_ready = pyqtSignal(list)
    failed            = pyqtSignal(str)

    # ── algorithms to benchmark ───────────────────────────────────────────────
    _ALGOS = [
        ("XGBoost Regressor", "_build_xgb"),
        ("LightGBM",          "_build_lgbm"),
        ("Random Forest",     "_build_rf"),
        ("CatBoost",          "_build_cat"),
    ]

    def __init__(
        self,
        df: pd.DataFrame,
        target: str,
        features: List[str],
        test_size: float = 0.2,
        random_state: int = 42,
        parent=None,
    ):
        super().__init__(parent)
        self.df           = df
        self.target       = target
        self.features     = features
        self.test_size    = test_size
        self.random_state = random_state

    # ── thread entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            X, y = self._prepare_data()
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import r2_score, mean_squared_error

            X_tr, X_te, y_tr, y_te = train_test_split(
                X, y,
                test_size=self.test_size,
                random_state=self.random_state,
            )

            results: list[dict] = []
            n = len(self._ALGOS)

            for i, (name, builder_name) in enumerate(self._ALGOS):
                pct = int(10 + (i / n) * 85)
                self.progress.emit(pct, f"Training {name}…")
                try:
                    builder = getattr(self, builder_name)
                    model   = builder()
                    model.fit(X_tr, y_tr)
                    y_hat = model.predict(X_te)
                    r2   = float(r2_score(y_te, y_hat))
                    rmse = float(np.sqrt(mean_squared_error(y_te, y_hat)))
                    results.append({"model": name, "r2": r2, "rmse": rmse})
                except Exception:
                    # algorithm not installed — add placeholder
                    results.append({"model": name, "r2": None, "rmse": None})

            # sort by r2 descending (None at bottom)
            results.sort(
                key=lambda d: d["r2"] if d["r2"] is not None else -999,
                reverse=True,
            )
            self.progress.emit(100, "Leaderboard ready ✔")
            self.leaderboard_ready.emit(results)

        except Exception:
            self.failed.emit(traceback.format_exc())

    # ── data preparation ──────────────────────────────────────────────────────

    def _prepare_data(self):
        cols = self.features + [self.target]
        df   = self.df[cols].dropna()
        return df[self.features].values, df[self.target].values

    # ── model builders ────────────────────────────────────────────────────────

    def _build_xgb(self):
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=150, random_state=self.random_state,
            verbosity=0, n_jobs=-1,
        )

    def _build_lgbm(self):
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=150, random_state=self.random_state,
            verbose=-1, n_jobs=-1,
        )

    def _build_rf(self):
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(
            n_estimators=150, random_state=self.random_state, n_jobs=-1,
        )

    def _build_cat(self):
        from catboost import CatBoostRegressor
        return CatBoostRegressor(
            iterations=150, random_seed=self.random_state, verbose=0,
        )
