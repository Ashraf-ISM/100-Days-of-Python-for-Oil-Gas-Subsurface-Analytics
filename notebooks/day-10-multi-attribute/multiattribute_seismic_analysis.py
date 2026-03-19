"""
=============================================================
  MULTI-ATTRIBUTE SEISMIC ANALYSIS — Complete Pipeline
  Works with any SEG-Y file (2D or 3D)
=============================================================

Requirements:
    pip install segyio numpy scipy matplotlib scikit-learn bruges segysak pandas seaborn tqdm

Usage:
    python multiattribute_seismic_analysis.py

Edit the CONFIG section below to point to your SEG-Y file.
=============================================================
"""

# ─────────────────────────────────────────────────────────────
# 0.  IMPORTS
# ─────────────────────────────────────────────────────────────
import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # headless rendering → saves PNG files
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap
import matplotlib.cm as cm

import segyio
from scipy.signal import butter, filtfilt, hilbert, spectrogram
from scipy.ndimage import uniform_filter1d

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────
# 1.  CONFIGURATION  ← edit this block
# ─────────────────────────────────────────────────────────────
CONFIG = {
    # Path to your SEG-Y file
    "segy_path": "/home/ashraf/Downloads/ST8511r92.segy",

    # Output folder for all plots and CSV exports
    "output_dir": "multiattribute_output",

    # Number of traces to process (None = all traces)
    # Set a small number (e.g. 500) for a quick test run
    "max_traces": None,

    # Bandpass filter corners (Hz).  Set to None to skip filtering.
    "bandpass_hz": (5, 10, 80, 100),

    # K-Means: number of facies clusters
    "n_clusters": 5,

    # PCA: number of components to retain
    "n_pca_components": 4,

    # MLP supervised classifier
    # If you have real well-log labels supply them in the function
    # `load_well_labels()` below; otherwise synthetic labels are used
    # for demonstration.
    "use_synthetic_labels": True,

    # Which inline / crossline to display in final section plots
    # (for a 2-D unstructured file these are trace index ranges)
    "display_trace_start": 0,
    "display_trace_end":   200,
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)
OUT = CONFIG["output_dir"]

# ─────────────────────────────────────────────────────────────
# 2.  SEG-Y LOADER
# ─────────────────────────────────────────────────────────────
def load_segy(path, max_traces=None):
    """
    Load SEG-Y data.
    Returns
    -------
    data        : np.ndarray  shape (n_traces, n_samples)
    dt_ms       : float       sample interval in milliseconds
    n_traces    : int
    n_samples   : int
    """
    print(f"\n[1/7] Loading SEG-Y: {path}")
    if not os.path.exists(path):
        print(f"  ⚠  File not found: {path}")
        print("  → Generating SYNTHETIC seismic data for demonstration …")
        return _make_synthetic_segy()

    with segyio.open(path, ignore_geometry=True) as f:
        dt_ms = segyio.tools.dt(f) / 1000.0          # µs → ms
        n_samples = f.samples.size
        n_traces  = f.tracecount

        if max_traces:
            n_traces = min(n_traces, max_traces)

        data = np.zeros((n_traces, n_samples), dtype=np.float32)
        for i in tqdm(range(n_traces), desc="  Reading traces"):
            data[i] = f.trace[i]

    print(f"  ✓  Traces: {n_traces}  |  Samples/trace: {n_samples}  |  dt: {dt_ms} ms")
    return data, dt_ms, n_traces, n_samples


def _make_synthetic_segy(n_traces=500, n_samples=500, dt_ms=2.0):
    """Create a synthetic seismic dataset for demonstration."""
    t   = np.arange(n_samples) * dt_ms / 1000.0      # time in seconds
    f0  = 30.0                                         # dominant frequency Hz
    rng = np.random.default_rng(42)

    data = np.zeros((n_traces, n_samples), dtype=np.float32)
    for i in range(n_traces):
        # Ricker wavelet centred at a varying two-way time
        t0  = 0.2 + 0.3 * (i / n_traces)
        amp = 1.0 + 0.5 * rng.standard_normal()
        u   = np.pi * f0 * (t - t0)
        ricker = amp * (1 - 2*u**2) * np.exp(-u**2)
        # Add a reflector at 0.6 s
        t1 = 0.6
        u1 = np.pi * f0 * (t - t1)
        ricker2 = 0.4 * amp * (1 - 2*u1**2) * np.exp(-u1**2)
        noise   = 0.05 * rng.standard_normal(n_samples)
        data[i] = (ricker + ricker2 + noise).astype(np.float32)

    print(f"  ✓  Synthetic data: {n_traces} traces × {n_samples} samples  |  dt={dt_ms} ms")
    return data, dt_ms, n_traces, n_samples


# ─────────────────────────────────────────────────────────────
# 3.  QC PLOTS
# ─────────────────────────────────────────────────────────────
def qc_plots(data, dt_ms):
    print("\n[2/7] QC Plots …")
    n_tr, n_samp = data.shape
    t = np.arange(n_samp) * dt_ms

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("SEG-Y QC", fontsize=14, fontweight="bold")

    # Wiggle section (first 100 traces)
    ax = axes[0]
    n_show = min(100, n_tr)
    for i in range(n_show):
        tr = data[i] / (np.max(np.abs(data)) + 1e-9)
        ax.plot(tr * 2 + i, t, color="black", lw=0.4, alpha=0.7)
    ax.invert_yaxis()
    ax.set_xlabel("Trace"); ax.set_ylabel("Time (ms)")
    ax.set_title("Wiggle Section (first 100 traces)")

    # Amplitude spectrum (mean)
    ax = axes[1]
    freqs = np.fft.rfftfreq(n_samp, d=dt_ms/1000.0)
    specs = np.abs(np.fft.rfft(data, axis=1))
    ax.plot(freqs, specs.mean(axis=0), color="steelblue", lw=1.5)
    ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Amplitude")
    ax.set_title("Mean Amplitude Spectrum"); ax.grid(alpha=0.3)

    # RMS amplitude per trace
    ax = axes[2]
    rms = np.sqrt(np.mean(data**2, axis=1))
    ax.plot(rms, color="firebrick", lw=1.2)
    ax.set_xlabel("Trace"); ax.set_ylabel("RMS Amplitude")
    ax.set_title("RMS Amplitude per Trace"); ax.grid(alpha=0.3)

    plt.tight_layout()
    out = f"{OUT}/01_qc_plots.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")


# ─────────────────────────────────────────────────────────────
# 4.  BANDPASS FILTER
# ─────────────────────────────────────────────────────────────
def bandpass_filter(data, dt_ms, corners):
    """Butterworth bandpass filter applied trace-by-trace."""
    if corners is None:
        return data
    print(f"\n[3/7] Bandpass filter {corners} Hz …")
    fs   = 1000.0 / dt_ms          # sample rate in Hz
    nyq  = 0.5 * fs
    low  = corners[1] / nyq
    high = corners[2] / nyq
    b, a = butter(4, [low, high], btype="band")

    filtered = np.zeros_like(data)
    for i in tqdm(range(data.shape[0]), desc="  Filtering"):
        filtered[i] = filtfilt(b, a, data[i])

    print("  ✓  Bandpass filter applied.")
    return filtered


# ─────────────────────────────────────────────────────────────
# 5.  ATTRIBUTE EXTRACTION
# ─────────────────────────────────────────────────────────────
def extract_attributes(data, dt_ms):
    """
    Extract 10 seismic attributes for every sample of every trace.

    Returns
    -------
    attr_dict : dict  {name: np.ndarray shape (n_traces, n_samples)}
    """
    print("\n[4/7] Extracting seismic attributes …")
    n_tr, n_samp = data.shape
    dt_s = dt_ms / 1000.0

    attr_dict = {}

    # ── 1. Envelope (Reflection Strength) ────────────────────
    print("  → Envelope (Reflection Strength)")
    env = np.abs(hilbert(data, axis=1))
    attr_dict["Envelope"] = env.astype(np.float32)

    # ── 2. Instantaneous Phase ────────────────────────────────
    print("  → Instantaneous Phase")
    analytic = hilbert(data, axis=1)
    inst_phase = np.angle(analytic)
    attr_dict["Inst_Phase"] = inst_phase.astype(np.float32)

    # ── 3. Cosine of Instantaneous Phase ─────────────────────
    print("  → Cosine of Instantaneous Phase")
    attr_dict["Cos_Phase"] = np.cos(inst_phase).astype(np.float32)

    # ── 4. Instantaneous Frequency ────────────────────────────
    print("  → Instantaneous Frequency")
    # Unwrap phase then differentiate
    unwrapped = np.unwrap(inst_phase, axis=1)
    inst_freq  = np.gradient(unwrapped, dt_s, axis=1) / (2.0 * np.pi)
    # Clip outliers
    inst_freq  = np.clip(inst_freq, 0, 500)
    attr_dict["Inst_Freq"] = inst_freq.astype(np.float32)

    # ── 5. RMS Amplitude (sliding window, 11 samples) ─────────
    print("  → RMS Amplitude (11-sample window)")
    rms_amp = np.sqrt(uniform_filter1d(data**2, size=11, axis=1))
    attr_dict["RMS_Amp"] = rms_amp.astype(np.float32)

    # ── 6. Sweetness ─────────────────────────────────────────
    print("  → Sweetness  (Envelope / sqrt(Inst_Freq))")
    with np.errstate(divide="ignore", invalid="ignore"):
        sweetness = env / np.sqrt(np.abs(inst_freq) + 1e-6)
    attr_dict["Sweetness"] = sweetness.astype(np.float32)

    # ── 7. Amplitude Contrast ─────────────────────────────────
    print("  → Amplitude Contrast")
    amp_contrast = np.gradient(env, axis=1)
    attr_dict["Amp_Contrast"] = amp_contrast.astype(np.float32)

    # ── 8. Thin-Bed Indicator (quadrature component) ──────────
    print("  → Thin-Bed Indicator")
    quad = np.imag(analytic)
    thin_bed = data**2 - quad**2
    attr_dict["Thin_Bed"] = thin_bed.astype(np.float32)

    # ── 9. Dominant Frequency (spectral centroid per sample) ──
    print("  → Dominant Frequency (spectral centroid)")
    freqs = np.fft.rfftfreq(n_samp, d=dt_s)
    spec  = np.abs(np.fft.rfft(data, axis=1))
    dom_freq_val = (spec * freqs[np.newaxis, :]).sum(axis=1) / (spec.sum(axis=1) + 1e-9)
    dom_freq = np.tile(dom_freq_val[:, np.newaxis], (1, n_samp))
    attr_dict["Dom_Freq"] = dom_freq.astype(np.float32)

    # ── 10. Acoustic Impedance proxy (cumulative integration) ─
    print("  → Acoustic Impedance (proxy via cumulative sum)")
    ai = np.cumsum(data, axis=1)
    attr_dict["Acoustic_Imp"] = ai.astype(np.float32)

    print(f"  ✓  {len(attr_dict)} attributes extracted.")
    return attr_dict


def plot_attributes(data, attr_dict, dt_ms,
                    trace_start=0, trace_end=200):
    """Plot raw data + all attributes side by side."""
    print("  → Plotting attribute sections …")
    t_end   = min(trace_end, data.shape[0])
    t_start = max(trace_start, 0)
    n_samp  = data.shape[1]
    t_axis  = np.arange(n_samp) * dt_ms

    all_items = [("Raw Seismic", data)] + list(attr_dict.items())
    n_panels  = len(all_items)
    cols = 4
    rows = int(np.ceil(n_panels / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(cols*5, rows*4))
    axes = axes.flatten()

    for idx, (name, arr) in enumerate(all_items):
        section = arr[t_start:t_end, :]
        vmax = np.percentile(np.abs(section), 98)
        im = axes[idx].imshow(
            section.T,
            aspect="auto",
            extent=[t_start, t_end, t_axis[-1], t_axis[0]],
            cmap="seismic" if "Raw" in name or "Phase" in name else "plasma",
            vmin=-vmax if "Raw" in name else None,
            vmax=vmax,
        )
        axes[idx].set_title(name, fontsize=10, fontweight="bold")
        axes[idx].set_xlabel("Trace")
        axes[idx].set_ylabel("Time (ms)")
        plt.colorbar(im, ax=axes[idx], pad=0.02, fraction=0.046)

    # Hide unused panels
    for idx in range(n_panels, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle("Seismic Attributes Gallery", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    out = f"{OUT}/02_attribute_gallery.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")


# ─────────────────────────────────────────────────────────────
# 6.  BUILD FEATURE MATRIX
# ─────────────────────────────────────────────────────────────
def build_feature_matrix(attr_dict):
    """
    Flatten all attributes into a 2-D feature matrix.
    Returns
    -------
    X       : np.ndarray  shape (n_traces*n_samples, n_attrs)
    names   : list of str
    shape   : (n_traces, n_samples)
    """
    print("\n[5/7] Building feature matrix …")
    names  = list(attr_dict.keys())
    arrays = [attr_dict[k].ravel() for k in names]
    X = np.column_stack(arrays)

    # Replace NaN / Inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    n_tr, n_samp = list(attr_dict.values())[0].shape
    print(f"  ✓  Feature matrix: {X.shape[0]:,} samples × {X.shape[1]} attributes")
    return X, names, (n_tr, n_samp)


def scale_features(X):
    scaler = StandardScaler()
    return scaler.fit_transform(X), scaler


# ─────────────────────────────────────────────────────────────
# 7a.  PCA
# ─────────────────────────────────────────────────────────────
def run_pca(X_scaled, n_components, data_shape):
    print(f"\n[6/7] PCA  ({n_components} components) …")
    pca    = PCA(n_components=n_components, random_state=42)

    # PCA on a random subset for speed (max 200k samples)
    n_sub  = min(200_000, X_scaled.shape[0])
    idx    = np.random.default_rng(0).choice(X_scaled.shape[0], n_sub, replace=False)
    pca.fit(X_scaled[idx])

    X_pca  = pca.transform(X_scaled)

    ev = pca.explained_variance_ratio_
    print(f"  ✓  Explained variance: {[f'{v:.1%}' for v in ev]}  (total {ev.sum():.1%})")

    # ── Scree plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    comp_labels = [f"PC{i+1}" for i in range(n_components)]

    axes[0].bar(comp_labels, ev * 100, color="steelblue", edgecolor="white")
    axes[0].set_ylabel("Explained Variance (%)")
    axes[0].set_title("Scree Plot")
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].scatter(X_pca[:5000, 0], X_pca[:5000, 1],
                    alpha=0.3, s=2, c="steelblue")
    axes[1].set_xlabel("PC1"); axes[1].set_ylabel("PC2")
    axes[1].set_title("PC1 vs PC2 (first 5 000 points)")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    out = f"{OUT}/03_pca_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")

    # ── PC1 section
    n_tr, n_samp = data_shape
    pc1_section = X_pca[:, 0].reshape(n_tr, n_samp)

    fig, ax = plt.subplots(figsize=(12, 5))
    vmax = np.percentile(np.abs(pc1_section), 98)
    im = ax.imshow(pc1_section.T, aspect="auto", cmap="RdBu_r",
                   vmin=-vmax, vmax=vmax)
    plt.colorbar(im, ax=ax, label="PC1 Value")
    ax.set_title("PCA Component 1 — Seismic Section")
    ax.set_xlabel("Trace"); ax.set_ylabel("Sample")
    plt.tight_layout()
    out2 = f"{OUT}/04_pca_component1_section.png"
    plt.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out2}")

    return X_pca, pca


# ─────────────────────────────────────────────────────────────
# 7b.  K-MEANS CLUSTERING
# ─────────────────────────────────────────────────────────────
def run_kmeans(X_pca, n_clusters, data_shape):
    print(f"\n[6/7] K-Means clustering  (k={n_clusters}) …")

    # Fit on subset for speed
    n_sub = min(200_000, X_pca.shape[0])
    idx   = np.random.default_rng(1).choice(X_pca.shape[0], n_sub, replace=False)
    km    = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
    km.fit(X_pca[idx])

    print("  → Predicting on full dataset …")
    labels = km.predict(X_pca)

    n_tr, n_samp = data_shape
    facies_section = labels.reshape(n_tr, n_samp)

    # ── Facies section plot
    cmap = ListedColormap(plt.cm.tab10.colors[:n_clusters])

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(facies_section.T, aspect="auto",
                   cmap=cmap, vmin=-0.5, vmax=n_clusters - 0.5,
                   interpolation="nearest")
    cbar = plt.colorbar(im, ax=ax, ticks=range(n_clusters))
    cbar.set_label("Facies Cluster")
    cbar.set_ticklabels([f"F{i+1}" for i in range(n_clusters)])
    ax.set_title(f"K-Means Facies Classification  (k={n_clusters})")
    ax.set_xlabel("Trace"); ax.set_ylabel("Sample")
    plt.tight_layout()
    out = f"{OUT}/05_kmeans_facies.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")

    # ── Cluster statistics
    df_stats = pd.DataFrame(X_pca[:, :4],
                            columns=[f"PC{i+1}" for i in range(4)])
    df_stats["Cluster"] = labels
    stats = df_stats.groupby("Cluster").agg(["mean", "std"]).round(3)
    csv_out = f"{OUT}/06_cluster_statistics.csv"
    stats.to_csv(csv_out)
    print(f"  ✓  Cluster stats → {csv_out}")

    # ── Pair plot of PC1-PC3 coloured by cluster (subsample)
    sub = np.random.default_rng(2).choice(X_pca.shape[0],
                                          min(10_000, X_pca.shape[0]),
                                          replace=False)
    df_sub = pd.DataFrame(X_pca[sub, :3],
                          columns=["PC1", "PC2", "PC3"])
    df_sub["Cluster"] = labels[sub].astype(str)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    pairs = [("PC1", "PC2"), ("PC1", "PC3"), ("PC2", "PC3")]
    colors = plt.cm.tab10.colors
    for ax, (px, py) in zip(axes, pairs):
        for c in sorted(df_sub["Cluster"].unique()):
            sub_c = df_sub[df_sub["Cluster"] == c]
            ax.scatter(sub_c[px], sub_c[py],
                       s=2, alpha=0.4,
                       color=colors[int(c)],
                       label=f"F{int(c)+1}")
        ax.set_xlabel(px); ax.set_ylabel(py)
        ax.legend(markerscale=4, fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("Cluster Separation in PCA Space", fontweight="bold")
    plt.tight_layout()
    out2 = f"{OUT}/07_cluster_pca_space.png"
    plt.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out2}")

    return labels, km


# ─────────────────────────────────────────────────────────────
# 7c.  CORRELATION HEATMAP
# ─────────────────────────────────────────────────────────────
def attribute_correlation(X_scaled, attr_names):
    print("\n[6/7] Attribute correlation matrix …")
    n_sub = min(50_000, X_scaled.shape[0])
    idx   = np.random.default_rng(3).choice(X_scaled.shape[0], n_sub, replace=False)
    df    = pd.DataFrame(X_scaled[idx], columns=attr_names)
    corr  = df.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f",
                cmap="coolwarm", center=0,
                linewidths=0.5, ax=ax)
    ax.set_title("Attribute Correlation Matrix", fontweight="bold", pad=12)
    plt.tight_layout()
    out = f"{OUT}/08_attribute_correlation.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")


# ─────────────────────────────────────────────────────────────
# 8.  SUPERVISED MLP CLASSIFIER
# ─────────────────────────────────────────────────────────────
def load_well_labels(data_shape, kmeans_labels, use_synthetic):
    """
    Return (X_well, y_well) at well-sample positions.

    REAL USAGE:
      Replace the synthetic block below with your actual well-log
      derived labels (e.g. GR-classified lithofacies at each trace/sample).

    Expected format:
      X_well : feature rows at well locations
      y_well : integer lithofacies label
    """
    n_tr, n_samp = data_shape
    if use_synthetic:
        # Use K-Means labels as pseudo-training labels (well locations = random subset)
        n_well = min(20_000, kmeans_labels.shape[0])
        idx    = np.random.default_rng(4).choice(
                     kmeans_labels.shape[0], n_well, replace=False)
        return idx, kmeans_labels[idx]
    else:
        # ── Plug your real well data here ──────────────────
        # Example:
        #   well_df = pd.read_csv("well_logs.csv")
        #   # Map (trace_number, sample_index) → flat index
        #   flat_idx = well_df["trace"] * n_samp + well_df["sample"]
        #   return flat_idx.values, well_df["lithofacies"].values
        raise NotImplementedError("Supply real well labels in load_well_labels().")


def run_supervised_mlp(X_scaled, X_pca, data_shape,
                       kmeans_labels, n_clusters, use_synthetic):
    print("\n[7/7] Supervised MLP Classifier …")

    well_idx, y_well = load_well_labels(
        data_shape, kmeans_labels, use_synthetic)

    X_well = X_pca[well_idx]            # use PCA features

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_well, y_well,
        test_size=0.25, random_state=42,
        stratify=y_well if len(np.unique(y_well)) > 1 else None)

    print(f"  Train: {X_tr.shape[0]:,}   Test: {X_te.shape[0]:,}")

    mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        max_iter=300,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42,
        verbose=False,
    )
    mlp.fit(X_tr, y_tr)

    y_pred = mlp.predict(X_te)
    print("\n  Classification Report:")
    print(classification_report(y_te, y_pred,
          target_names=[f"F{i+1}" for i in range(n_clusters)],
          zero_division=0))

    # ── Confusion matrix
    cm_arr = confusion_matrix(y_te, y_pred)
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(cm_arr, annot=True, fmt="d", cmap="Blues",
                xticklabels=[f"F{i+1}" for i in range(n_clusters)],
                yticklabels=[f"F{i+1}" for i in range(n_clusters)],
                ax=ax)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title("MLP Confusion Matrix", fontweight="bold")
    plt.tight_layout()
    out = f"{OUT}/09_mlp_confusion_matrix.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out}")

    # ── Learning curve (loss)
    if hasattr(mlp, "loss_curve_"):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(mlp.loss_curve_, color="steelblue", label="Training loss")
        if hasattr(mlp, "validation_scores_") and mlp.validation_scores_:
            ax.plot(mlp.validation_scores_, color="firebrick",
                    linestyle="--", label="Validation score")
        ax.set_xlabel("Epoch"); ax.set_ylabel("Loss / Score")
        ax.set_title("MLP Learning Curve"); ax.legend(); ax.grid(alpha=0.3)
        plt.tight_layout()
        out2 = f"{OUT}/10_mlp_learning_curve.png"
        plt.savefig(out2, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  ✓  Saved → {out2}")

    # ── Predict full volume
    print("  → Predicting full seismic volume …")
    n_tr, n_samp = data_shape

    CHUNK = 500_000
    all_pred = np.zeros(X_pca.shape[0], dtype=np.int32)
    for start in range(0, X_pca.shape[0], CHUNK):
        end = min(start + CHUNK, X_pca.shape[0])
        all_pred[start:end] = mlp.predict(X_pca[start:end])

    mlp_section = all_pred.reshape(n_tr, n_samp)

    cmap = ListedColormap(plt.cm.tab10.colors[:n_clusters])
    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(mlp_section.T, aspect="auto",
                   cmap=cmap, vmin=-0.5, vmax=n_clusters - 0.5,
                   interpolation="nearest")
    cbar = plt.colorbar(im, ax=ax, ticks=range(n_clusters))
    cbar.set_label("Predicted Facies")
    cbar.set_ticklabels([f"F{i+1}" for i in range(n_clusters)])
    ax.set_title("MLP Predicted Facies Section")
    ax.set_xlabel("Trace"); ax.set_ylabel("Sample")
    plt.tight_layout()
    out3 = f"{OUT}/11_mlp_predicted_facies.png"
    plt.savefig(out3, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓  Saved → {out3}")

    return mlp, all_pred


# ─────────────────────────────────────────────────────────────
# 9.  EXPORT ATTRIBUTES TO CSV
# ─────────────────────────────────────────────────────────────
def export_attributes(attr_dict, kmeans_labels, mlp_labels, data_shape):
    print("\n  → Exporting attribute summary CSV …")
    n_tr, n_samp = data_shape
    # Aggregate per trace (mean of each attribute across time)
    rows = {}
    rows["Trace"] = np.arange(n_tr)
    for name, arr in attr_dict.items():
        rows[f"{name}_mean"] = arr.mean(axis=1)
        rows[f"{name}_std"]  = arr.std(axis=1)

    dominant_facies = []
    for i in range(n_tr):
        flat_start = i * n_samp
        flat_end   = flat_start + n_samp
        vals, cnts = np.unique(kmeans_labels[flat_start:flat_end], return_counts=True)
        dominant_facies.append(vals[cnts.argmax()])
    rows["KMeans_DominantFacies"] = dominant_facies

    dominant_mlp = []
    for i in range(n_tr):
        flat_start = i * n_samp
        flat_end   = flat_start + n_samp
        vals, cnts = np.unique(mlp_labels[flat_start:flat_end], return_counts=True)
        dominant_mlp.append(vals[cnts.argmax()])
    rows["MLP_DominantFacies"] = dominant_mlp

    df = pd.DataFrame(rows)
    out = f"{OUT}/12_attribute_per_trace.csv"
    df.to_csv(out, index=False)
    print(f"  ✓  Saved → {out}")


# ─────────────────────────────────────────────────────────────
# 10.  SUMMARY DASHBOARD for Results
# ─────────────────────────────────────────────────────────────
def summary_dashboard(data, attr_dict, kmeans_labels,
                      mlp_labels, dt_ms, data_shape, n_clusters):
    print("\n  → Generating summary dashboard …")
    n_tr, n_samp = data_shape
    t_axis = np.arange(n_samp) * dt_ms
    cmap   = ListedColormap(plt.cm.tab10.colors[:n_clusters])

    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor("#1a1a2e")
    gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.4, wspace=0.35)

    kw = dict(facecolor="#1a1a2e")
    text_kw = dict(color="white")

    def _imshow(ax, arr, title, cmap_="seismic", percentile=98):
        vmax = np.percentile(np.abs(arr), percentile)
        vmin = -vmax if cmap_ == "seismic" else arr.min()
        im = ax.imshow(arr.T, aspect="auto",
                       extent=[0, n_tr, t_axis[-1], t_axis[0]],
                       cmap=cmap_, vmin=vmin, vmax=vmax)
        ax.set_title(title, **text_kw, fontsize=9, pad=4)
        ax.tick_params(colors="white", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")
        plt.colorbar(im, ax=ax, pad=0.02, fraction=0.046).ax.yaxis.set_tick_params(color="white", labelsize=6)
        return ax

    # Raw seismic
    ax = fig.add_subplot(gs[0, 0], **kw)
    _imshow(ax, data, "Raw Seismic", "seismic")

    # Envelope
    ax = fig.add_subplot(gs[0, 1], **kw)
    _imshow(ax, attr_dict["Envelope"], "Envelope", "hot", 99)

    # Inst Frequency
    ax = fig.add_subplot(gs[0, 2], **kw)
    _imshow(ax, attr_dict["Inst_Freq"], "Inst. Frequency", "plasma", 99)

    # Sweetness
    ax = fig.add_subplot(gs[0, 3], **kw)
    _imshow(ax, attr_dict["Sweetness"], "Sweetness", "plasma", 99)

    # Cos Phase
    ax = fig.add_subplot(gs[1, 0], **kw)
    _imshow(ax, attr_dict["Cos_Phase"], "Cos Phase", "RdBu_r", 99)

    # RMS Amplitude
    ax = fig.add_subplot(gs[1, 1], **kw)
    _imshow(ax, attr_dict["RMS_Amp"], "RMS Amplitude", "hot", 99)

    # Acoustic Impedance proxy
    ax = fig.add_subplot(gs[1, 2], **kw)
    _imshow(ax, attr_dict["Acoustic_Imp"], "Acoustic Imp.", "viridis", 99)

    # Thin Bed
    ax = fig.add_subplot(gs[1, 3], **kw)
    _imshow(ax, attr_dict["Thin_Bed"], "Thin-Bed Indicator", "coolwarm", 99)

    # K-Means facies
    ax = fig.add_subplot(gs[2, 0:2], **kw)
    kmf = kmeans_labels.reshape(n_tr, n_samp)
    im  = ax.imshow(kmf.T, aspect="auto",
                    extent=[0, n_tr, t_axis[-1], t_axis[0]],
                    cmap=cmap, vmin=-0.5, vmax=n_clusters - 0.5,
                    interpolation="nearest")
    ax.set_title("K-Means Facies", **text_kw, fontsize=9)
    cbar = plt.colorbar(im, ax=ax, ticks=range(n_clusters), pad=0.02, fraction=0.046)
    cbar.set_ticklabels([f"F{i+1}" for i in range(n_clusters)])
    cbar.ax.yaxis.set_tick_params(color="white", labelsize=7)
    ax.tick_params(colors="white", labelsize=7)

    # MLP facies
    ax = fig.add_subplot(gs[2, 2:4], **kw)
    mlf = mlp_labels.reshape(n_tr, n_samp)
    im  = ax.imshow(mlf.T, aspect="auto",
                    extent=[0, n_tr, t_axis[-1], t_axis[0]],
                    cmap=cmap, vmin=-0.5, vmax=n_clusters - 0.5,
                    interpolation="nearest")
    ax.set_title("MLP Predicted Facies", **text_kw, fontsize=9)
    cbar = plt.colorbar(im, ax=ax, ticks=range(n_clusters), pad=0.02, fraction=0.046)
    cbar.set_ticklabels([f"F{i+1}" for i in range(n_clusters)])
    cbar.ax.yaxis.set_tick_params(color="white", labelsize=7)
    ax.tick_params(colors="white", labelsize=7)

    fig.suptitle("Multi-Attribute Seismic Analysis — Summary Dashboard",
                 color="white", fontsize=15, fontweight="bold", y=1.01)

    out = f"{OUT}/00_summary_dashboard.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✓  Saved → {out}")


# ─────────────────────────────────────────────────────────────
# 11.  MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  MULTI-ATTRIBUTE SEISMIC ANALYSIS")
    print("=" * 60)

    # 1. Load data
    data, dt_ms, n_traces, n_samples = load_segy(
        CONFIG["segy_path"], CONFIG["max_traces"])

    # 2. QC
    qc_plots(data, dt_ms)

    # 3. Filter
    data_filt = bandpass_filter(data, dt_ms, CONFIG["bandpass_hz"])

    # 4. Attributes
    attr_dict = extract_attributes(data_filt, dt_ms)
    plot_attributes(data_filt, attr_dict, dt_ms,
                    CONFIG["display_trace_start"],
                    CONFIG["display_trace_end"])

    # 5. Feature matrix
    X, attr_names, data_shape = build_feature_matrix(attr_dict)
    X_scaled, scaler          = scale_features(X)

    # 6. Correlation
    attribute_correlation(X_scaled, attr_names)

    # 7. PCA
    X_pca, pca = run_pca(X_scaled,
                          CONFIG["n_pca_components"],
                          data_shape)

    # 8. K-Means
    km_labels, km_model = run_kmeans(X_pca,
                                      CONFIG["n_clusters"],
                                      data_shape)

    # 9. MLP
    mlp_model, mlp_labels = run_supervised_mlp(
        X_scaled, X_pca, data_shape,
        km_labels,
        CONFIG["n_clusters"],
        CONFIG["use_synthetic_labels"])

    # 10. Export
    export_attributes(attr_dict, km_labels, mlp_labels, data_shape)

    # 11. Dashboard
    summary_dashboard(data_filt, attr_dict,
                      km_labels, mlp_labels,
                      dt_ms, data_shape,
                      CONFIG["n_clusters"])

    print("\n" + "=" * 60)
    print(f"  ✅  All outputs saved to:  {OUT}/")
    print("=" * 60)
    print("\nOutput files:")
    for f in sorted(os.listdir(OUT)):
        print(f"  {OUT}/{f}")


if __name__ == "__main__":
    main()
