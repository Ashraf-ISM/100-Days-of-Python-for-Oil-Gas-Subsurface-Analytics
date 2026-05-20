"""
ml_qc_models.py
===============
Model wrappers for ML-based anomaly detection on well log data.

Each class exposes a uniform interface::

    detector = IsolationForestDetector(contamination=0.05)
    mask, scores = detector.fit_predict(X)          # X: (n, d) float array
    importance   = detector.feature_importance()    # (d,) float array | None

All classes handle edge-cases gracefully (tiny datasets, import errors).
"""
from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Base class
# ─────────────────────────────────────────────────────────────────────────────

class BaseMLDetector(ABC):
    """Abstract base for all ML anomaly detectors."""

    @abstractmethod
    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run detection on feature matrix X.

        Returns
        -------
        mask   : bool ndarray (n,)  — True where anomaly detected
        scores : float ndarray (n,) — higher value = more anomalous
        """

    def feature_importance(self) -> Optional[np.ndarray]:
        """Return per-feature importance scores (None if not available)."""
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Isolation Forest
# ─────────────────────────────────────────────────────────────────────────────

class IsolationForestDetector(BaseMLDetector):
    """sklearn Isolation Forest wrapper."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 200,
                 random_state: int = 42):
        self.contamination = float(np.clip(contamination, 0.01, 0.49))
        self.n_estimators  = n_estimators
        self.random_state  = random_state
        self._model = None

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            return np.zeros(len(X), dtype=bool), np.zeros(len(X))

        model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )
        preds  = model.fit_predict(X)          # +1 normal, -1 anomaly
        scores = -model.score_samples(X)       # higher = more anomalous
        scores = np.clip(scores - scores.min(), 0, None)
        self._model = model
        return preds == -1, scores

    def feature_importance(self) -> Optional[np.ndarray]:
        """Isolation Forest has no native feature importance; return None."""
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Local Outlier Factor
# ─────────────────────────────────────────────────────────────────────────────

class LOFDetector(BaseMLDetector):
    """sklearn Local Outlier Factor wrapper."""

    def __init__(self, contamination: float = 0.05, n_neighbors: int = 20):
        self.contamination = float(np.clip(contamination, 0.01, 0.49))
        self.n_neighbors   = n_neighbors

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            from sklearn.neighbors import LocalOutlierFactor
        except ImportError:
            return np.zeros(len(X), dtype=bool), np.zeros(len(X))

        n_neighbors = min(self.n_neighbors, max(len(X) - 1, 1))
        model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=self.contamination,
        )
        preds  = model.fit_predict(X)
        scores = -model.negative_outlier_factor_   # higher = more anomalous
        scores = np.clip(scores - scores.min(), 0, None)
        return preds == -1, scores


# ─────────────────────────────────────────────────────────────────────────────
# One-Class SVM
# ─────────────────────────────────────────────────────────────────────────────

class OneClassSVMDetector(BaseMLDetector):
    """sklearn One-Class SVM wrapper (RBF kernel)."""

    def __init__(self, nu: float = 0.05, kernel: str = "rbf", gamma: str = "scale"):
        self.nu     = float(np.clip(nu, 0.01, 0.99))
        self.kernel = kernel
        self.gamma  = gamma

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            from sklearn.svm import OneClassSVM
        except ImportError:
            return np.zeros(len(X), dtype=bool), np.zeros(len(X))

        model  = OneClassSVM(nu=self.nu, kernel=self.kernel, gamma=self.gamma)
        preds  = model.fit_predict(X)
        scores = -model.score_samples(X)
        scores = np.clip(scores - scores.min(), 0, None)
        return preds == -1, scores


# ─────────────────────────────────────────────────────────────────────────────
# DBSCAN
# ─────────────────────────────────────────────────────────────────────────────

class DBSCANDetector(BaseMLDetector):
    """sklearn DBSCAN wrapper — points labelled -1 are treated as anomalies."""

    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        self.eps         = eps
        self.min_samples = min_samples

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            from sklearn.cluster import DBSCAN
        except ImportError:
            return np.zeros(len(X), dtype=bool), np.zeros(len(X))

        model  = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = model.fit_predict(X)
        mask   = labels == -1

        # Score: distance to nearest core-sample centroid (proxied by L2 norm)
        try:
            from sklearn.metrics import pairwise_distances_argmin_min
            core_idx = model.core_sample_indices_
            if len(core_idx) > 0:
                _, scores = pairwise_distances_argmin_min(X, X[core_idx])
            else:
                scores = np.linalg.norm(X - X.mean(axis=0), axis=1)
        except Exception:  # noqa: BLE001
            scores = np.linalg.norm(X - X.mean(axis=0), axis=1)

        scores = np.clip(scores - scores.min(), 0, None)
        return mask, scores


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_MAP: dict[str, type] = {
    "Isolation Forest": IsolationForestDetector,
    "LOF":              LOFDetector,
    "One-Class SVM":    OneClassSVMDetector,
    "DBSCAN":           DBSCANDetector,
}


def get_detector(model_name: str, contamination: float = 0.05) -> BaseMLDetector:
    """Instantiate a detector by name.

    Parameters
    ----------
    model_name    : one of ``_MODEL_MAP`` keys (case-sensitive)
    contamination : fraction of data expected to be anomalous [0.01, 0.49] 
    """
    cls = _MODEL_MAP.get(model_name, IsolationForestDetector)

    # Some models use nu / eps instead of contamination
    if cls is DBSCANDetector:
        return cls(eps=max(0.1, contamination * 5), min_samples=5)
    if cls is OneClassSVMDetector:
        return cls(nu=contamination)
    return cls(contamination=contamination)


MODEL_NAMES: list[str] = list(_MODEL_MAP.keys())
