"""
=============================================================================
  CBVS Seismic Data Pipeline
  Read → Convert → Visualize → Save
  Author: Ashraf | IIT (ISM) Dhanbad
=============================================================================

DEPENDENCIES (install once):
    pip install segyio numpy matplotlib scipy segysak

CBVS NOTE:
  CBVS is a Paradigm/Emerson proprietary format. Two reading strategies:
  
  PATH A (Recommended) - Pre-convert CBVS to SEGY using:
    • SeismicUnix: cbvs2su file.cbvs | segywrite tape=file.segy
    • Petrel / Kingdom: Export → SEG-Y
    Then use the segyio-based reader below.

  PATH B - Raw binary reader (works for simple CBVS without compression)
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import os
import struct
import warnings
warnings.filterwarnings("ignore")

# ─── Try importing segyio (optional but preferred) ────────────────────────────
try:
    import segyio
    SEGYIO_AVAILABLE = True
except ImportError:
    SEGYIO_AVAILABLE = False
    print("[WARNING] segyio not installed. Install with: pip install segyio")


# =============================================================================
#  PATH A: Read from SEG-Y (after converting CBVS → SEGY externally)
# =============================================================================

def read_segy(filepath: str) -> dict:
    """
    Read a 2D SEG-Y file and return a dict with data + metadata.

    Parameters
    ----------
    filepath : str
        Path to .segy / .sgy file

    Returns
    -------
    dict with keys:
        data      : np.ndarray, shape (n_traces, n_samples)
        dt        : float, sample interval in seconds
        n_traces  : int
        n_samples : int
        cdp       : np.ndarray, CDP numbers per trace
        twt       : np.ndarray, two-way time axis in seconds
    """
    if not SEGYIO_AVAILABLE:
        raise ImportError("Install segyio: pip install segyio")

    print(f"[INFO] Reading SEG-Y file: {filepath}")
    with segyio.open(filepath, "r", ignore_geometry=True) as f:
        n_traces  = f.tracecount
        n_samples = len(f.samples)
        dt        = segyio.tools.dt(f) / 1e6          # microsec → seconds
        twt       = f.samples / 1000.0                # ms → s (if stored in ms)

        data = np.zeros((n_traces, n_samples), dtype=np.float32)
        cdp  = np.zeros(n_traces, dtype=np.int32)

        for i, tr in enumerate(f.trace):
            data[i, :] = tr
            cdp[i]     = f.header[i][segyio.TraceField.CDP]

    print(f"[INFO] Loaded  : {n_traces} traces × {n_samples} samples")
    print(f"[INFO] dt      : {dt*1000:.3f} ms  |  TWT range: {twt[0]:.3f}–{twt[-1]:.3f} s")

    return {
        "data"     : data,
        "dt"       : dt,
        "n_traces" : n_traces,
        "n_samples": n_samples,
        "cdp"      : cdp,
        "twt"      : twt,
    }


# =============================================================================
#  PATH B: Raw binary CBVS reader (no external conversion needed)
# =============================================================================

class CBVSReader:
    """
    Minimal raw-binary CBVS reader.

    CBVS layout (simplified, uncompressed):
      Bytes  0–3999  : File header (ASCII/binary mix)
      Then N trace records, each:
          Trace header : 240 bytes (SEG-Y style)
          Trace data   : n_samples × 4 bytes (IEEE float32, big-endian)

    If your CBVS file has a different layout (compressed, tiled),
    this reader will need adjustment. Print hex dump to inspect header.
    """

    CBVS_MAGIC = b"CBVS"          # first 4 bytes of a typical CBVS file
    FILE_HDR_SIZE = 4000           # bytes in file header block

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._fh = None

    def _open(self):
        self._fh = open(self.filepath, "rb")

    def _close(self):
        if self._fh:
            self._fh.close()

    def inspect_header(self, n_bytes: int = 64):
        """Print first n_bytes as hex + ASCII for manual inspection."""
        with open(self.filepath, "rb") as f:
            raw = f.read(n_bytes)
        print(f"\n[CBVS HEADER DUMP] First {n_bytes} bytes:")
        for i in range(0, len(raw), 16):
            chunk = raw[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"  {i:04X}  {hex_part:<48}  {asc_part}")

    def read(self, n_samples: int = None, n_traces: int = None,
             endian: str = ">") -> dict:
        """
        Read binary CBVS data.

        Parameters
        ----------
        n_samples : int  - samples per trace (from file or known a-priori)
        n_traces  : int  - number of traces (if None, inferred from file size)
        endian    : str  - ">" big-endian (default), "<" little-endian

        Returns
        -------
        dict with same keys as read_segy()
        """
        self._open()
        raw = self._fh.read()
        self._close()

        # ── detect magic ──────────────────────────────────────────────────
        magic = raw[:4]
        if magic == self.CBVS_MAGIC:
            print("[INFO] CBVS magic bytes detected ✓")
        else:
            print(f"[WARNING] Unexpected magic: {magic!r} — proceeding anyway")

        # ── parse file header for n_samples and dt if not provided ────────
        # Offset 3220–3227 in SEG-Y-style CBVS: sample interval (μs) + n_samples
        # Adjust offsets if your file differs!
        try:
            dt_us      = struct.unpack_from(f"{endian}H", raw, 3216)[0]   # μs
            ns_hdr     = struct.unpack_from(f"{endian}H", raw, 3220)[0]   # samples
            dt         = dt_us * 1e-6
            if n_samples is None:
                n_samples = ns_hdr
            print(f"[INFO] Header → dt={dt*1000:.3f} ms, n_samples={n_samples}")
        except Exception:
            dt = 0.002  # fallback 2 ms
            print(f"[WARNING] Could not parse dt/n_samples from header. "
                  f"Using defaults: dt={dt*1000} ms, n_samples={n_samples}")

        # ── infer trace count ─────────────────────────────────────────────
        data_start    = self.FILE_HDR_SIZE
        trace_hdr_sz  = 240                              # bytes per trace header
        trace_data_sz = n_samples * 4                    # float32
        trace_total   = trace_hdr_sz + trace_data_sz

        available = len(raw) - data_start
        if n_traces is None:
            n_traces = available // trace_total
        print(f"[INFO] Inferred {n_traces} traces × {n_samples} samples")

        # ── read trace data ───────────────────────────────────────────────
        data = np.zeros((n_traces, n_samples), dtype=np.float32)
        cdp  = np.zeros(n_traces, dtype=np.int32)
        fmt  = f"{endian}f"

        for i in range(n_traces):
            offset_hdr  = data_start + i * trace_total
            offset_data = offset_hdr + trace_hdr_sz
            # CDP from trace header byte 21 (word 11, 4-byte int)
            cdp[i]   = struct.unpack_from(f"{endian}i", raw, offset_hdr + 20)[0]
            raw_data = raw[offset_data : offset_data + trace_data_sz]
            arr      = np.frombuffer(raw_data, dtype=np.float32)
            if endian == ">":
                arr = arr.byteswap().newbyteorder()
            data[i, :] = arr[:n_samples]

        twt = np.arange(n_samples) * dt

        return {
            "data"     : data,
            "dt"       : dt,
            "n_traces" : n_traces,
            "n_samples": n_samples,
            "cdp"      : cdp,
            "twt"      : twt,
        }


# =============================================================================
#  SAVE functions
# =============================================================================

def save_npy(seismic: dict, out_dir: str = "."):
    """Save amplitude data and axes as .npy files."""
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, "seismic_data.npy"), seismic["data"])
    np.save(os.path.join(out_dir, "seismic_twt.npy"),  seismic["twt"])
    np.save(os.path.join(out_dir, "seismic_cdp.npy"),  seismic["cdp"])
    print(f"[SAVED] NPY files → {out_dir}/")
    print(f"        seismic_data.npy  shape={seismic['data'].shape}")


def save_segy(seismic: dict, out_path: str):
    """
    Write a 2D section back to SEG-Y using segyio.
    
    Parameters
    ----------
    seismic  : dict returned by read_segy() or CBVSReader.read()
    out_path : str, output .segy path
    """
    if not SEGYIO_AVAILABLE:
        raise ImportError("Install segyio: pip install segyio")

    data     = seismic["data"]
    dt_us    = int(seismic["dt"] * 1e6)        # seconds → microseconds
    n_traces, n_samples = data.shape
    cdp      = seismic["cdp"]

    spec = segyio.spec()
    spec.sorting  = segyio.TraceSortingFormat.CDP_SORTING
    spec.format   = segyio.SegySampleFormat.IBM_FLOAT_4_BYTE
    spec.samples  = np.arange(n_samples, dtype=np.float32) * seismic["dt"] * 1000  # ms
    spec.tracecount = n_traces

    with segyio.create(out_path, spec) as f:
        f.bin.update(tsort=segyio.TraceSortingFormat.CDP_SORTING,
                     hdt=dt_us, dto=dt_us,
                     hns=n_samples, nso=n_samples)
        for i in range(n_traces):
            f.trace[i] = data[i].astype(np.float32)
            f.header[i].update({
                segyio.TraceField.CDP         : int(cdp[i]),
                segyio.TraceField.TRACE_SEQUENCE_LINE: i + 1,
                segyio.TraceField.DelayRecordingTime : 0,
                segyio.TraceField.SAMPLE_COUNT: n_samples,
                segyio.TraceField.INTERVAL    : dt_us,
            })

    print(f"[SAVED] SEG-Y → {out_path}")


# =============================================================================
#  VISUALISATION
# =============================================================================

def plot_seismic_section(seismic: dict,
                         clip_pct: float = 98,
                         cmap: str = "gray",
                         title: str = "2D Seismic Section",
                         out_path: str = None,
                         dpi: int = 300):
    """
    Publication-quality wiggle / variable-density seismic section plot.

    Parameters
    ----------
    seismic   : dict from read_segy() or CBVSReader.read()
    clip_pct  : percentile for amplitude clipping (default 98)
    cmap      : colormap — 'gray', 'seismic', 'RdBu_r', 'bwr'
    title     : plot title
    out_path  : if set, saves PNG to this path
    dpi       : dots-per-inch for saved figure
    """
    data     = seismic["data"].T       # shape → (n_samples, n_traces) for imshow
    twt      = seismic["twt"]
    cdp      = seismic["cdp"]
    n_traces = seismic["n_traces"]

    vmax = np.nanpercentile(np.abs(data), clip_pct)
    vmin = -vmax

    fig, axes = plt.subplots(1, 2, figsize=(18, 9),
                             gridspec_kw={"width_ratios": [3, 1]})

    # ── Left: Variable-density display ────────────────────────────────────
    ax = axes[0]
    im = ax.imshow(data,
                   aspect="auto",
                   cmap=cmap,
                   vmin=vmin, vmax=vmax,
                   extent=[cdp[0], cdp[-1], twt[-1], twt[0]],
                   interpolation="bilinear")
    ax.set_xlabel("CDP Number", fontsize=13, fontweight="bold")
    ax.set_ylabel("Two-Way Time (s)", fontsize=13, fontweight="bold")
    ax.set_title(title, fontsize=15, fontweight="bold", pad=12)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="both", direction="in", top=True, right=True)
    cbar = fig.colorbar(im, ax=ax, orientation="vertical",
                        fraction=0.02, pad=0.02)
    cbar.set_label("Amplitude", fontsize=11)

    # ── Right: RMS amplitude with depth ───────────────────────────────────
    ax2 = axes[1]
    rms = np.sqrt(np.mean(data**2, axis=1))
    ax2.plot(rms, twt, color="#E63946", lw=1.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("RMS Amplitude", fontsize=12)
    ax2.set_title("RMS Profile", fontsize=13, fontweight="bold")
    ax2.set_ylabel("TWT (s)", fontsize=12)
    ax2.tick_params(which="both", direction="in")
    ax2.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax2.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.fill_betweenx(twt, 0, rms, alpha=0.2, color="#E63946")

    plt.tight_layout()

    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Figure → {out_path}")
    plt.show()


def plot_amplitude_spectrum(seismic: dict,
                            n_traces_sample: int = 100,
                            out_path: str = None,
                            dpi: int = 300):
    """
    Plot the average amplitude (frequency) spectrum of the section.

    Parameters
    ----------
    seismic          : dict from reader
    n_traces_sample  : number of traces to average over
    """
    data = seismic["data"]
    dt   = seismic["dt"]
    n_traces, n_samples = data.shape

    step     = max(1, n_traces // n_traces_sample)
    subset   = data[::step, :]
    spectra  = np.abs(np.fft.rfft(subset, axis=1))
    avg_spec = np.mean(spectra, axis=0)
    freqs    = np.fft.rfftfreq(n_samples, d=dt)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(freqs, avg_spec, color="#2A9D8F", lw=2)
    ax.fill_between(freqs, avg_spec, alpha=0.2, color="#2A9D8F")
    ax.set_xlabel("Frequency (Hz)", fontsize=13)
    ax.set_ylabel("Amplitude", fontsize=13)
    ax.set_title("Average Amplitude Spectrum", fontsize=14, fontweight="bold")
    ax.set_xlim(0, freqs[-1])
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(4))
    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Spectrum → {out_path}")
    plt.show()


def plot_trace_wiggle(seismic: dict,
                      n_traces: int = 50,
                      gain: float = 1.0,
                      out_path: str = None,
                      dpi: int = 300):
    """
    Classic wiggle trace display for a subset of traces.

    Parameters
    ----------
    n_traces : how many traces to plot
    gain     : amplitude scale factor
    """
    data     = seismic["data"]
    twt      = seismic["twt"]
    n_total  = seismic["n_traces"]
    step     = max(1, n_total // n_traces)
    subset   = data[::step, :]
    n_plot   = subset.shape[0]

    norm  = np.nanpercentile(np.abs(subset), 95)
    if norm == 0:
        norm = 1.0
    subset = subset / norm * gain

    fig, ax = plt.subplots(figsize=(14, 8))
    for i in range(n_plot):
        tr  = subset[i, :]
        ax.plot(tr + i, twt, color="k", lw=0.4)
        ax.fill_betweenx(twt, i, tr + i,
                         where=(tr > 0), color="#264653", alpha=0.7)

    ax.set_xlim(-1, n_plot)
    ax.invert_yaxis()
    ax.set_xlabel("Trace Index (subsampled)", fontsize=13)
    ax.set_ylabel("Two-Way Time (s)", fontsize=13)
    ax.set_title("Wiggle Trace Display", fontsize=14, fontweight="bold")
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="both", direction="in", right=True)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.tight_layout()

    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Wiggle → {out_path}")
    plt.show()


# =============================================================================
#  MAIN — edit paths below and run
# =============================================================================

if __name__ == "__main__":

    # ─── USER SETTINGS ────────────────────────────────────────────────────
    INPUT_FORMAT = "segy"         # "segy" or "cbvs"
    INPUT_FILE   = "your_file.segy"   # ← change to your file path
    OUTPUT_DIR   = "seismic_output"
    # ──────────────────────────────────────────────────────────────────────

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── STEP 1: Read data ─────────────────────────────────────────────────
    if INPUT_FORMAT == "segy":
        seismic = read_segy(INPUT_FILE)

    elif INPUT_FORMAT == "cbvs":
        reader = CBVSReader(INPUT_FILE)

        # Inspect header first to understand byte layout
        reader.inspect_header(n_bytes=128)

        # Adjust n_samples and endian based on your file
        seismic = reader.read(
            n_samples = 1500,     # ← set from your acquisition params
            endian    = ">",      # ">" big-endian (most seismic) or "<" little
        )

    # ── STEP 2: Save as NPY ───────────────────────────────────────────────
    save_npy(seismic, out_dir=OUTPUT_DIR)

    # ── STEP 3: Save as SEG-Y (optional) ─────────────────────────────────
    if SEGYIO_AVAILABLE:
        save_segy(seismic, out_path=os.path.join(OUTPUT_DIR, "converted.segy"))

    # ── STEP 4: Visualise ─────────────────────────────────────────────────
    plot_seismic_section(
        seismic,
        clip_pct = 98,
        cmap     = "gray",
        title    = "2D Seismic Section",
        out_path = os.path.join(OUTPUT_DIR, "seismic_section.png"),
        dpi      = 300,
    )

    plot_amplitude_spectrum(
        seismic,
        out_path = os.path.join(OUTPUT_DIR, "amplitude_spectrum.png"),
        dpi      = 300,
    )

    plot_trace_wiggle(
        seismic,
        n_traces = 60,
        gain     = 1.2,
        out_path = os.path.join(OUTPUT_DIR, "wiggle_display.png"),
        dpi      = 300,
    )

    print("\n[DONE] All outputs saved to:", OUTPUT_DIR)
