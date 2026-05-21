"""
facies_classifications/results_visualizer.py
=============================================
Responsible for:
  - Plotting facies tracks on the well log (matplotlib)
  - Rendering the confusion matrix
  - Rendering feature importance bar charts
  - Rendering correlation heat-maps and feature distribution plots
  - Exporting results to CSV/Excel
  - Generating a text / HTML report

All public functions are pure (no Qt imports).
matplotlib figures are returned so the caller can embed them in a Qt canvas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from sklearn.metrics import confusion_matrix


matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


# ---------------------------------------------------------------------------
# Colour palette for facies
# ---------------------------------------------------------------------------

FACIES_PALETTE = [
    "#4A90D9",  # Sandstone – blue
    "#E8A838",  # Limestone – amber
    "#5DB85C",  # Shale – green
    "#D96B6B",  # Dolomite – red-orange
    "#9B59B6",  # Tight Sand – purple
    "#45C4AF",  # Coal – teal
    "#F1948A",  # Siltstone – pink
    "#A9CCE3",  # Evaporite – light-blue
    "#82E0AA",  # Carbonate – light-green
    "#F7DC6F",  # Unconsolidated – yellow
]


def _facies_cmap(n: int) -> list[str]:
    colours = FACIES_PALETTE[:n]
    while len(colours) < n:
        colours.append("#AAAAAA")
    return colours


# ---------------------------------------------------------------------------
# Facies log track
# ---------------------------------------------------------------------------

def plot_facies_track(
    depths: np.ndarray,
    labels: np.ndarray,
    df: Optional[pd.DataFrame] = None,
    log_curves: Sequence[str] = ("GR", "RHOB", "NPHI"),
    label_names: Optional[Dict[int, str]] = None,
    figsize: Tuple[float, float] = (10.0, 8.0),
) -> Figure:
    """Return a matplotlib Figure with the facies track alongside log curves."""
    unique_labels = np.unique(labels[~np.isnan(labels.astype(float))])
    n_classes     = len(unique_labels)
    colours       = _facies_cmap(n_classes)
    colour_map    = {int(lbl): colours[i] for i, lbl in enumerate(unique_labels)}

    curve_cols = []
    if df is not None:
        for c in log_curves:
            if c in df.columns:
                curve_cols.append(c)

    n_cols = 1 + len(curve_cols)
    fig, axes = plt.subplots(
        1, n_cols,
        figsize=figsize,
        sharey=True,
        gridspec_kw={"wspace": 0.08},
    )
    if n_cols == 1:
        axes = [axes]

    # ---- Facies track (first panel) ----------------------------------------
    ax_f = axes[0]
    for i in range(len(depths) - 1):
        lbl = int(labels[i]) if not np.isnan(float(labels[i])) else -1
        col = colour_map.get(lbl, "#CCCCCC")
        ax_f.fill_betweenx(
            [depths[i], depths[i + 1]],
            0, 1,
            color=col, linewidth=0,
        )

    # Legend
    from matplotlib.patches import Patch
    legend_elements = []
    for lbl, col in colour_map.items():
        name = label_names.get(lbl, f"Facies {lbl}") if label_names else f"Facies {lbl}"
        legend_elements.append(Patch(facecolor=col, label=name))
    ax_f.legend(handles=legend_elements, loc="lower left", fontsize=7, frameon=True, framealpha=0.8)
    ax_f.set_xlabel("Facies")
    ax_f.set_xlim(0, 1)
    ax_f.set_title("Facies", fontweight="bold")
    ax_f.set_ylabel("Depth (m)")
    ax_f.invert_yaxis()
    ax_f.get_xaxis().set_ticks([])

    # ---- Log curve panels ----------------------------------------------------
    for idx, curve in enumerate(curve_cols):
        ax = axes[idx + 1]
        vals = pd.to_numeric(df[curve], errors="coerce")
        ax.plot(vals.to_numpy(), depths, color=FACIES_PALETTE[idx % len(FACIES_PALETTE)], lw=1.0)
        ax.set_title(curve, fontweight="bold")
        ax.set_xlabel(curve)
        ax.invert_yaxis()
        ax.grid(axis="y", alpha=0.15)

    fig.suptitle("Facies Classification Track", fontweight="bold", fontsize=11)
    return fig


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------

def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (6.5, 5.0),
) -> Figure:
    cm = confusion_matrix(y_true, y_pred)
    n  = cm.shape[0]

    if class_names is None or len(class_names) != n:
        class_names = [f"F{i}" for i in range(n)]

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.04)

    thresh = cm.max() / 2.0
    for i in range(n):
        for j in range(n):
            ax.text(j, i, str(cm[i, j]),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontsize=8)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(class_names, rotation=35, ha="right", fontsize=8)
    ax.set_yticklabels(class_names, fontsize=8)
    ax.set_xlabel("Predicted Facies")
    ax.set_ylabel("True Facies")
    ax.set_title("Confusion Matrix", fontweight="bold")
    return fig


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------

def plot_feature_importance(
    importance_df: pd.DataFrame,
    top_k: int = 12,
    figsize: Tuple[float, float] = (6.5, 4.5),
) -> Figure:
    """importance_df must have columns ['feature', 'importance']."""
    top = importance_df.head(top_k).sort_values("importance")
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    bars = ax.barh(
        top["feature"],
        top["importance"],
        color="#4A90D9",
        edgecolor="white",
        linewidth=0.5,
    )
    for bar in bars:
        ax.text(
            bar.get_width() + max(top["importance"]) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.3f}",
            va="center", ha="left", fontsize=7,
        )
    ax.set_xlabel("Importance Score")
    ax.set_title(f"Top {top_k} Features", fontweight="bold")
    ax.set_xlim(0, top["importance"].max() * 1.18)
    return fig


# ---------------------------------------------------------------------------
# Correlation heat-map
# ---------------------------------------------------------------------------

def plot_correlation_matrix(
    X: pd.DataFrame,
    figsize: Tuple[float, float] = (7.0, 6.0),
) -> Figure:
    corr = X.corr(numeric_only=True)
    n    = len(corr)
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    cax = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(cax, ax=ax, fraction=0.035, pad=0.04)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=40, ha="right", fontsize=7)
    ax.set_yticklabels(corr.columns, fontsize=7)
    ax.set_title("Feature Correlation Matrix", fontweight="bold")
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{corr.iloc[i, j] * 100:.0f}%",
                    ha="center", va="center", fontsize=5.5,
                    color="white" if abs(corr.iloc[i, j]) > 0.6 else "black")
    return fig


# ---------------------------------------------------------------------------
# Feature distribution (violin / histogram grid)
# ---------------------------------------------------------------------------

def plot_feature_distributions(
    X: pd.DataFrame,
    labels: Optional[np.ndarray] = None,
    n_cols: int = 3,
    figsize: Optional[Tuple[float, float]] = None,
) -> Figure:
    features = list(X.columns)
    n        = len(features)
    n_rows   = int(np.ceil(n / n_cols))
    if figsize is None:
        figsize = (n_cols * 3.5, n_rows * 2.8)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, constrained_layout=True)
    axes_flat = axes.flatten() if n > 1 else [axes]

    for idx, feat in enumerate(features):
        ax  = axes_flat[idx]
        vals = pd.to_numeric(X[feat], errors="coerce").dropna()
        ax.hist(vals, bins=28, color="#4A90D9", edgecolor="white", alpha=0.85)
        ax.set_title(feat, fontsize=8, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=6)

    for idx in range(n, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle("Feature Distributions", fontweight="bold", fontsize=10)
    return fig


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_csv(df: pd.DataFrame, labels: np.ndarray, path: str) -> str:
    """Append a 'FACIES' column and export to CSV."""
    out = df.copy()
    out["FACIES"] = labels
    out.to_csv(path, index=False)
    return f"Results exported to {path}"


def export_to_excel(df: pd.DataFrame, labels: np.ndarray, metrics: Dict[str, Any], path: str) -> str:
    """Export data + metrics to an Excel workbook with two sheets."""
    out = df.copy()
    out["FACIES"] = labels
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="FaciesData", index=False)
        metrics_df = pd.DataFrame(
            [(k, str(v)) for k, v in metrics.items() if k != "report"],
            columns=["Metric", "Value"],
        )
        metrics_df.to_excel(writer, sheet_name="Metrics", index=False)
    return f"Results exported to {path}"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_text_report(
    metadata: Dict[str, Any],
    metrics: Dict[str, Any],
    feature_names: List[str],
) -> str:
    """Generate a plain-text summary report."""
    lines = [
        "=" * 60,
        "       PetroARX  –  Facies Classification Report",
        "=" * 60,
        "",
        "Dataset",
        "-------",
        f"  LAS file      : {metadata.get('las_file', 'unknown')}",
        f"  Depth range   : {metadata.get('depth_range', ('?', '?'))}",
        f"  Total samples : {metadata.get('total_rows', '?'):,}",
        "",
        "Features Used",
        "-------------",
    ]
    for feat in feature_names:
        lines.append(f"  • {feat}")
    lines += [
        "",
        "Model Performance",
        "-----------------",
    ]
    for k, v in metrics.items():
        if k == "report":
            lines += ["", "Classification Report", "---------------------", v]
        elif isinstance(v, float):
            lines.append(f"  {k:<22}: {v:.4f}")
        else:
            lines.append(f"  {k:<22}: {v}")

    lines += ["", "=" * 60, "  Generated by PetroARX Facies Classification Module", "=" * 60]
    return "\n".join(lines)
