"""
facies_classifications/model_trainer.py
=========================================
Responsible for:
  - Training K-Means, Gaussian Mixture, Ensemble (RF + XGBoost + SVM),
    and Self-Organising Map classifiers
  - Cross-validation and hyperparameter configuration
  - Returning labelled predictions together with model metrics
  - Utilities for saving / loading trained models

All public functions are pure (no Qt imports).
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    silhouette_score,
)
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

try:
    from xgboost import XGBClassifier  # type: ignore
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

try:
    import minisom  # type: ignore
    _HAS_SOM = True
except ImportError:
    _HAS_SOM = False


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
TrainResult = Tuple[Optional[np.ndarray], Dict[str, Any], str]
"""(label_array | None, metrics_dict, status_message)"""


# ---------------------------------------------------------------------------
# Public API – model factory
# ---------------------------------------------------------------------------

def build_kmeans(
    n_clusters: int = 6,
    init: str = "k-means++",
    max_iter: int = 300,
    n_init: int = 10,
    tol: float = 1e-4,
    random_state: int = 42,
) -> KMeans:
    return KMeans(
        n_clusters=n_clusters,
        init=init.lower().replace(" ", "") if init.lower() != "k-means++" else "k-means++",
        max_iter=max_iter,
        n_init=n_init,
        tol=tol,
        random_state=random_state,
    )


def build_gmm(
    n_components: int = 6,
    covariance_type: str = "full",
    reg_covar: float = 1e-4,
    init_params: str = "kmeans",
) -> GaussianMixture:
    return GaussianMixture(
        n_components=n_components,
        covariance_type=covariance_type.lower(),
        reg_covar=reg_covar,
        init_params=init_params.lower(),
        random_state=42,
    )


def build_ensemble(
    rf_trees: int = 300,
    xgb_max_depth: int = 5,
    svm_kernel: str = "rbf",
    voting: str = "soft",
) -> VotingClassifier:
    rf = RandomForestClassifier(n_estimators=rf_trees, random_state=42, n_jobs=-1)
    estimators = [("rf", rf)]

    if _HAS_XGB:
        xgb = XGBClassifier(
            max_depth=xgb_max_depth,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )
        estimators.append(("xgb", xgb))

    svm = SVC(kernel=svm_kernel, probability=True, random_state=42)
    estimators.append(("svm", svm))

    vote_method = "soft" if voting.lower().startswith("soft") else "hard"
    return VotingClassifier(estimators=estimators, voting=vote_method)


def build_rf_classifier(n_estimators: int = 300, random_state: int = 42) -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=n_estimators, random_state=random_state, n_jobs=-1)


# ---------------------------------------------------------------------------
# Public API – training
# ---------------------------------------------------------------------------

def train_unsupervised(
    X: pd.DataFrame,
    algorithm: str = "K-Means",
    params: Dict[str, Any] | None = None,
) -> TrainResult:
    """Train an unsupervised model and return integer cluster labels.

    Parameters
    ----------
    algorithm:
        ``"K-Means"`` or ``"Gaussian Mixture"`` or ``"Self-Organizing Map"``.
    params:
        Algorithm-specific parameters to override defaults.
    """
    params = params or {}
    X_filled = _prepare(X)
    if X_filled is None:
        return None, {}, "Feature matrix is empty or all-NaN."

    try:
        if algorithm in ("K-Means", "k-means"):
            model  = build_kmeans(**{k: v for k, v in params.items() if k in
                                      ("n_clusters", "init", "max_iter", "n_init", "tol", "random_state")})
            labels = model.fit_predict(X_filled)
            sil    = _silhouette(X_filled, labels)
            metrics = {
                "algorithm": "K-Means",
                "n_clusters": model.n_clusters,
                "inertia": float(model.inertia_),
                "silhouette": sil,
                "n_samples": len(X_filled),
            }
            return labels, metrics, f"K-Means trained — {model.n_clusters} clusters, silhouette={sil:.3f}"

        elif algorithm in ("Gaussian Mixture", "GMM"):
            model  = build_gmm(**{k: v for k, v in params.items() if k in
                                    ("n_components", "covariance_type", "reg_covar", "init_params")})
            labels = model.fit_predict(X_filled)
            sil    = _silhouette(X_filled, labels)
            metrics = {
                "algorithm": "Gaussian Mixture",
                "n_components": model.n_components,
                "bic": float(model.bic(X_filled)),
                "aic": float(model.aic(X_filled)),
                "silhouette": sil,
                "n_samples": len(X_filled),
            }
            return labels, metrics, f"GMM trained — {model.n_components} components, silhouette={sil:.3f}"

        elif algorithm in ("Self-Organizing Map", "SOM"):
            if not _HAS_SOM:
                return None, {}, "minisom package not found. Install with: pip install minisom"
            grid = int(params.get("grid_size", 8))
            som = minisom.MiniSom(grid, grid, X_filled.shape[1], sigma=1.0, learning_rate=0.5, random_seed=42)
            som.train_random(X_filled, num_iteration=5000)
            labels = np.array([som.winner(x)[0] * grid + som.winner(x)[1] for x in X_filled])
            sil = _silhouette(X_filled, labels)
            metrics = {
                "algorithm": "SOM",
                "grid_size": grid,
                "silhouette": sil,
                "n_samples": len(X_filled),
                "quantization_error": float(som.quantization_error(X_filled)),
            }
            return labels, metrics, f"SOM trained — {grid}×{grid} grid, silhouette={sil:.3f}"

        else:
            return None, {}, f"Unknown unsupervised algorithm: '{algorithm}'"

    except Exception as exc:
        return None, {}, f"Training failed: {exc}"


def train_supervised(
    X: pd.DataFrame,
    y: pd.Series,
    algorithm: str = "Ensemble Classifier",
    params: Dict[str, Any] | None = None,
    cv_folds: int = 5,
) -> TrainResult:
    """Train a supervised model with stratified CV and return class labels.

    Parameters
    ----------
    y:
        Integer or string class labels.
    """
    params  = params or {}
    X_filled = _prepare(X)
    if X_filled is None:
        return None, {}, "Feature matrix is empty."

    # Align y
    mask = y.notna()
    X_sup = X_filled[mask]
    y_arr = y[mask].to_numpy()

    # Encode labels
    le = LabelEncoder()
    y_enc = le.fit_transform(y_arr)

    if len(np.unique(y_enc)) < 2:
        return None, {}, "Need at least 2 distinct classes to train a supervised model."

    try:
        if algorithm == "Ensemble Classifier":
            model = build_ensemble(
                rf_trees     = int(params.get("rf_trees", 300)),
                xgb_max_depth= int(params.get("xgb_max_depth", 5)),
                svm_kernel   = str(params.get("svm_kernel", "rbf")),
                voting       = str(params.get("voting", "soft")),
            )
        else:
            model = build_rf_classifier(
                n_estimators= int(params.get("rf_trees", 300)),
                random_state= int(params.get("random_state", 42)),
            )

        # Cross-validation
        cv_scores = cross_val_score(
            model, X_sup, y_enc,
            cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42),
            scoring="f1_macro",
            n_jobs=-1,
        )
        # Final fit on full training data
        model.fit(X_sup, y_enc)
        preds_enc = model.predict(X_filled)
        preds     = le.inverse_transform(preds_enc)

        acc = accuracy_score(y_enc, model.predict(X_sup))
        f1  = f1_score(y_enc, model.predict(X_sup), average="macro", zero_division=0)
        report = classification_report(
            y_enc, model.predict(X_sup),
            target_names=[str(c) for c in le.classes_],
            zero_division=0,
        )
        metrics = {
            "algorithm": algorithm,
            "accuracy": float(acc),
            "f1_macro": float(f1),
            "cv_f1_mean": float(cv_scores.mean()),
            "cv_f1_std": float(cv_scores.std()),
            "n_classes": len(le.classes_),
            "class_names": [str(c) for c in le.classes_],
            "report": report,
            "n_samples": len(X_sup),
        }

        # Store full-array predictions (NaN rows get the nearest class)
        status = (
            f"{algorithm} trained — acc={acc:.3f}, F1={f1:.3f}, "
            f"CV-F1={cv_scores.mean():.3f}±{cv_scores.std():.3f}"
        )
        return preds_enc, metrics, status

    except Exception as exc:
        return None, {}, f"Supervised training failed: {exc}"


# ---------------------------------------------------------------------------
# Public API – prediction on new data
# ---------------------------------------------------------------------------

def predict_new(model, X: pd.DataFrame, label_encoder=None) -> Optional[np.ndarray]:
    """Apply a fitted model to new feature data."""
    X_filled = _prepare(X)
    if X_filled is None:
        return None
    try:
        preds = model.predict(X_filled)
        if label_encoder is not None:
            preds = label_encoder.inverse_transform(preds.astype(int))
        return preds
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API – persistence
# ---------------------------------------------------------------------------

def save_model(model, path: str | Path, metadata: Dict[str, Any] | None = None) -> str:
    """Pickle the trained model alongside a JSON sidecar with metrics."""
    import pickle
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    if metadata:
        sidecar = path.with_suffix(".json")
        with open(sidecar, "w") as f:
            json.dump(metadata, f, indent=2)
    return f"Model saved to {path}"


def load_model(path: str | Path) -> Tuple[Any, Dict[str, Any]]:
    """Load a pickled model and its JSON sidecar (if present)."""
    import pickle
    path = Path(path)
    with open(path, "rb") as f:
        model = pickle.load(f)
    metadata: Dict[str, Any] = {}
    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        with open(sidecar) as f:
            metadata = json.load(f)
    return model, metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prepare(X: pd.DataFrame) -> Optional[np.ndarray]:
    """Fill NaNs, ensure float64, return numpy or None."""
    if X is None or X.empty:
        return None
    X_arr = X.fillna(X.median()).to_numpy(dtype=float)
    if X_arr.size == 0:
        return None
    return X_arr


def _silhouette(X: np.ndarray, labels: np.ndarray) -> float:
    unique = np.unique(labels)
    if len(unique) < 2:
        return 0.0
    try:
        return float(silhouette_score(X, labels, sample_size=min(5000, len(X))))
    except Exception:
        return 0.0
