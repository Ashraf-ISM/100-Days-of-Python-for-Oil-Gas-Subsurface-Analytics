"""
facies_classifications/feature_engineering.py
===============================================
Responsible for:
  - Computing derived petrophysical features (Vsh, PHIE, Sw, etc.)
  - Adding user-defined custom features via formula evaluation
  - Normalisation / scaling
  - Feature selection via Mutual Information, RFE, or Tree importance
  - Dimensionality reduction placeholder (PCA / UMAP hooks)

All public functions are pure (no Qt imports).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.feature_selection import (
    SelectKBest,
    mutual_info_classif,
    RFE,
)
from sklearn.ensemble import RandomForestClassifier


# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

DERIVED_FEATURES = {
    "Vsh": "Shale Volume  (GR-based)",
    "PHIE": "Effective Porosity (NPHI-RHOB)",
    "Sw": "Water Saturation (Archie)",
    "LambdaRho": "Lambda-Rho  (RHOB × DT)",
    "Poisson": "Poisson Ratio  (DT-based)",
    "PE": "Photo-electric Factor",
}


# ---------------------------------------------------------------------------
# Public API – derived features
# ---------------------------------------------------------------------------

def compute_vsh(df: pd.DataFrame) -> Optional[pd.Series]:
    """Gamma-Ray Shale Volume (linear)."""
    gr = _find_col(df, "GR", "CGR")
    if gr is None:
        return None
    gr_vals = pd.to_numeric(df[gr], errors="coerce")
    mn, mx  = gr_vals.quantile(0.05), gr_vals.quantile(0.95)
    if mx - mn < 1e-9:
        return pd.Series(np.zeros(len(df)), index=df.index, name="Vsh")
    vsh = (gr_vals - mn) / (mx - mn)
    return vsh.clip(0.0, 1.0).rename("Vsh")


def compute_phie(df: pd.DataFrame, rhob_ma: float = 2.65, rhob_fl: float = 1.0) -> Optional[pd.Series]:
    """Effective porosity from NPHI and RHOB."""
    nphi = _find_col(df, "NPHI")
    rhob = _find_col(df, "RHOB")
    if nphi is None or rhob is None:
        return None
    n = pd.to_numeric(df[nphi], errors="coerce")
    r = pd.to_numeric(df[rhob], errors="coerce")
    phid = (rhob_ma - r) / (rhob_ma - rhob_fl)
    phie = ((n + phid) / 2.0).clip(0.0, 0.6).rename("PHIE")
    return phie


def compute_sw(df: pd.DataFrame, a: float = 1.0, m: float = 2.0, n: float = 2.0, rw: float = 0.1) -> Optional[pd.Series]:
    """Archie water saturation."""
    rt   = _find_col(df, "ILD", "LLD", "RT", "RESD")
    phie = df.get("PHIE")
    if rt is None or phie is None:
        return None
    rt_vals   = pd.to_numeric(df[rt], errors="coerce").clip(lower=0.01)
    phi_vals  = phie.clip(lower=0.001)
    sw_sq = (a * rw) / (rt_vals * phi_vals ** m)
    sw = sw_sq.clip(0.0, 1.0).rename("Sw")
    return sw


def compute_lambda_rho(df: pd.DataFrame) -> Optional[pd.Series]:
    """Lambda-Rho proxy  = RHOB / (DT^2) × scale."""
    rhob = _find_col(df, "RHOB")
    dt   = _find_col(df, "DT", "DTSM", "DTC")
    if rhob is None or dt is None:
        return None
    r = pd.to_numeric(df[rhob], errors="coerce")
    d = pd.to_numeric(df[dt], errors="coerce").clip(lower=0.01)
    lr = (r / (d ** 2) * 1e6).rename("LambdaRho")
    return lr


def compute_poisson(df: pd.DataFrame) -> Optional[pd.Series]:
    """Pseudo Poisson ratio from DT compressional (simplified)."""
    dt = _find_col(df, "DT", "DTC")
    if dt is None:
        return None
    d = pd.to_numeric(df[dt], errors="coerce")
    # approximate Vp from DT (us/ft → ft/s)
    vp = 1e6 / d.clip(lower=10)
    # simplified Poisson (assumes Vp/Vs ≈ 1.7 for most sediments)
    vp_vs = 1.7
    nu = ((vp_vs ** 2 - 2) / (2 * vp_vs ** 2 - 2)).clip(-0.1, 0.5)
    # Return constant-ish series shaped like the GR
    return pd.Series(np.full(len(df), float(nu.mean())), index=df.index, name="Poisson")


def add_custom_feature(df: pd.DataFrame, name: str, formula: str) -> Tuple[pd.DataFrame, str]:
    """Evaluate *formula* using column names as variables and append result.

    Returns
    -------
    (updated_df, message)
    """
    # Build a safe namespace from the DataFrame numeric columns
    namespace: dict = {}
    for col in df.columns:
        try:
            namespace[col] = df[col].to_numpy(dtype=float)
        except Exception:
            pass
    # Add numpy helpers
    namespace.update(
        {
            "mean": np.mean, "std": np.std, "log": np.log,
            "exp": np.exp, "sqrt": np.sqrt, "abs": np.abs,
            "log10": np.log10, "sin": np.sin, "cos": np.cos,
        }
    )
    try:
        result = eval(formula, {"__builtins__": {}}, namespace)  # noqa: S307
        if np.ndim(result) == 0:
            result = np.full(len(df), float(result))
        df[name] = pd.array(result, dtype=float)
        return df, f"Feature '{name}' added successfully."
    except Exception as exc:
        return df, f"Error evaluating formula: {exc}"


# ---------------------------------------------------------------------------
# Public API – feature matrix assembly
# ---------------------------------------------------------------------------

def build_feature_matrix(
    df: pd.DataFrame,
    selected_logs: List[str],
    include_vsh: bool = True,
    include_phie: bool = True,
    include_sw: bool = True,
    include_pe: bool = False,
    include_lambda_rho: bool = False,
    include_poisson: bool = True,
    custom_features: List[str] | None = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """Assemble the feature matrix.

    Returns
    -------
    (feature_df, feature_names)
    """
    feature_df = pd.DataFrame(index=df.index)

    # Raw logs
    for col in selected_logs:
        if col in df.columns:
            feature_df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived features
    if include_vsh:
        s = compute_vsh(df)
        if s is not None:
            feature_df["Vsh"] = s

    if include_phie:
        s = compute_phie(df)
        if s is not None:
            feature_df["PHIE"] = s

    if include_sw and "PHIE" in feature_df:
        # Temporarily attach PHIE to df for Sw calculation
        df_tmp = df.copy()
        df_tmp["PHIE"] = feature_df["PHIE"]
        s = compute_sw(df_tmp)
        if s is not None:
            feature_df["Sw"] = s

    if include_pe:
        pef = _find_col(df, "PEF", "PE")
        if pef:
            feature_df["PE"] = pd.to_numeric(df[pef], errors="coerce")

    if include_lambda_rho:
        s = compute_lambda_rho(df)
        if s is not None:
            feature_df["LambdaRho"] = s

    if include_poisson:
        s = compute_poisson(df)
        if s is not None:
            feature_df["Poisson"] = s

    # Custom columns already in df
    for feat in (custom_features or []):
        if feat in df.columns:
            feature_df[feat] = df[feat]

    feature_names = list(feature_df.columns)
    return feature_df, feature_names


# ---------------------------------------------------------------------------
# Public API – normalisation
# ---------------------------------------------------------------------------

def normalize_features(
    X: pd.DataFrame,
    method: str = "zscore",
    selected_only: bool = True,
) -> Tuple[pd.DataFrame, object]:
    """Scale *X* and return (scaled_X, fitted_scaler).

    Parameters
    ----------
    method:
        ``"zscore"``, ``"robust"``, or ``"minmax"``.
    """
    scaler_map = {
        "zscore": StandardScaler(),
        "robust": RobustScaler(),
        "minmax": MinMaxScaler(),
        "Z-Score Standardization": StandardScaler(),
        "Robust Scaler": RobustScaler(),
        "Min-Max Scaling": MinMaxScaler(),
    }
    scaler = scaler_map.get(method, StandardScaler())
    X_arr = X.to_numpy(dtype=float)
    mask_valid_rows = ~np.isnan(X_arr).any(axis=1)
    X_arr[mask_valid_rows] = scaler.fit_transform(X_arr[mask_valid_rows])
    return pd.DataFrame(X_arr, index=X.index, columns=X.columns), scaler


# ---------------------------------------------------------------------------
# Public API – feature selection
# ---------------------------------------------------------------------------

def select_features(
    X: pd.DataFrame,
    y: pd.Series | None = None,
    method: str = "mutual_info",
    top_k: int = 12,
) -> Tuple[List[str], pd.DataFrame]:
    """Rank and select the top *top_k* features.

    Parameters
    ----------
    y:
        Label vector (required for supervised methods; if ``None`` an
        unsupervised proxy score is used).
    method:
        ``"mutual_info"`` | ``"rfe"`` | ``"tree_importance"``
        | ``"Recursive Feature Elimination"`` | ``"Mutual Information"``
        | ``"Tree Feature Importance"``

    Returns
    -------
    (selected_column_names, feature_importance_df)
    """
    method_map = {
        "Recursive Feature Elimination": "rfe",
        "Mutual Information": "mutual_info",
        "Tree Feature Importance": "tree_importance",
    }
    method = method_map.get(method, method)

    cols = list(X.columns)
    top_k = min(top_k, len(cols))

    # Drop rows where y is NaN (if y is provided)
    if y is not None:
        mask = y.notna()
        X_clean = X[mask]
        y_clean = y[mask]
    else:
        X_clean = X.copy()
        y_clean = None

    # Fill NaN with column medians
    X_filled = X_clean.fillna(X_clean.median())
    X_arr    = X_filled.to_numpy(dtype=float)

    try:
        if method == "mutual_info" and y_clean is not None:
            scores = mutual_info_classif(X_arr, y_clean.to_numpy(), random_state=42)
        elif method == "tree_importance" and y_clean is not None:
            rf = RandomForestClassifier(n_estimators=80, random_state=42, n_jobs=-1)
            rf.fit(X_arr, y_clean.to_numpy())
            scores = rf.feature_importances_
        elif method == "rfe" and y_clean is not None:
            rf  = RandomForestClassifier(n_estimators=60, random_state=42, n_jobs=-1)
            rfe = RFE(rf, n_features_to_select=top_k)
            rfe.fit(X_arr, y_clean.to_numpy())
            scores = rfe.ranking_.astype(float)
            scores = (scores.max() - scores + 1.0)  # invert so higher = better
        else:
            # Unsupervised: variance as proxy
            scores = X_filled.var().to_numpy()
    except Exception:
        scores = np.ones(len(cols))

    imp_df = pd.DataFrame(
        {"feature": cols, "importance": scores, "rank": 0}
    ).sort_values("importance", ascending=False).reset_index(drop=True)
    imp_df["rank"] = np.arange(1, len(imp_df) + 1)

    selected = imp_df.head(top_k)["feature"].tolist()
    return selected, imp_df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col(df: pd.DataFrame, *aliases: str) -> Optional[str]:
    for alias in aliases:
        if alias in df.columns:
            return alias
        # case-insensitive search
        for col in df.columns:
            if col.upper() == alias.upper():
                return col
    return None
