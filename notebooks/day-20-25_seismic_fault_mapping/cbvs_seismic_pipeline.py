"""
=============================================================================
  CBVS Seismic Data Pipeline  —  OpendTect (dGB) Edition
  Read → Convert → Visualise → Save
  Author : Ashraf | IIT (ISM) Dhanbad
  Fixed  : NumPy 2.0 compatibility + proper dGB/OpendTect CBVS parsing
=============================================================================

DEPENDENCIES:
    pip install segyio numpy matplotlib

CBVS FORMAT NOTES (OpendTect / dGB Earth Sciences):
  * Magic bytes  : 64 47 42  ("dGB")
  * Endianness   : little-endian (LE)
  * No per-trace SEG-Y style 240-byte headers
  * Data block   : packed LE float32  ->  n_traces x n_samples
  * Geometry info stored separately in .par / survey files
  * This reader auto-detects the data-start offset by scanning the file
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import struct
import os
import warnings
warnings.filterwarnings("ignore")

try:
    import segyio
    SEGYIO_AVAILABLE = True
except ImportError:
    SEGYIO_AVAILABLE = False
    print("[WARNING] segyio not installed -> SEG-Y export disabled.")
    print("          Install: pip install segyio\n")


# =============================================================================
#  OpendTect CBVS Reader  (dGB magic)
# =============================================================================

class OpendTectCBVSReader:
    """
    Reader for OpendTect CBVS seismic files (magic: dGB\\x01 or dGB\\x02).

    Layout:
      File header  (variable size, little-endian binary + ASCII)
      Float32 data block  (n_traces x n_samples, LE, NO per-trace headers)
    """

    DGB_MAGIC = b"dGB"

    def __init__(self, filepath: str):
        self.filepath  = filepath
        self.raw       = None
        self._filesize = os.path.getsize(filepath)

    def _load(self):
        with open(self.filepath, "rb") as f:
            self.raw = f.read()

    def inspect_header(self, n_bytes: int = 256):
        with open(self.filepath, "rb") as f:
            raw = f.read(n_bytes)
        print(f"\n[dGB CBVS HEADER DUMP] First {n_bytes} bytes:")
        print(f"  File size : {self._filesize:,} bytes  ({self._filesize/1e6:.2f} MB)")
        for i in range(0, len(raw), 16):
            chunk    = raw[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"  {i:04X}  {hex_part:<48}  {asc_part}")

    def _parse_dgb_header(self):
        """
        Scan for z-sampling triplet (float64 start, float64 step, int32 n)
        which OpendTect stores somewhere in the first 512 bytes.
        """
        raw = self.raw
        version = raw[3]
        print(f"[dGB] Format version byte : 0x{version:02X}  ({version})")

        dt_ms, n_samp, z_start = None, None, None

        for off in range(4, min(len(raw) - 20, 512)):
            try:
                zs  = struct.unpack_from("<d", raw, off)[0]
                zst = struct.unpack_from("<d", raw, off + 8)[0]
                ns  = struct.unpack_from("<i", raw, off + 16)[0]
                if (0.0 <= zs  <= 5000.0 and
                    0.1 <= zst  <= 10.0  and
                    100 <= ns   <= 20000):
                    dt_ms, n_samp, z_start = zst, ns, zs
                    print(f"[dGB] z-sampling at offset 0x{off:04X}: "
                          f"start={zs:.2f} ms, step={zst:.4f} ms, n={ns}")
                    break
            except Exception:
                continue

        return dt_ms, n_samp, z_start

    def _find_data_offset(self, n_samples: int):
        """
        Scan for the byte offset where packed LE float32 data begins.
        Tests candidate offsets and checks for finite non-zero values.
        """
        raw      = self.raw
        fsize    = len(raw)
        trace_sz = n_samples * 4

        for hdr_sz in range(64, 2048, 4):
            data_bytes = fsize - hdr_sz
            if data_bytes < trace_sz:
                continue
            test_len = min(n_samples * 4, data_bytes)
            try:
                test = np.frombuffer(raw[hdr_sz : hdr_sz + test_len], dtype="<f4")
                if np.all(np.isfinite(test)) and np.any(test != 0.0):
                    n_tr = data_bytes // trace_sz
                    print(f"[dGB] Data block at offset 0x{hdr_sz:04X} "
                          f"({hdr_sz} bytes) -> {n_tr} traces")
                    return hdr_sz, n_tr
            except Exception:
                continue

        print("[WARNING] Auto-detect failed. Falling back to offset=128.")
        return 128, (fsize - 128) // trace_sz

    def read(self,
             n_samples  : int   = None,
             dt_ms      : float = None,
             n_traces   : int   = None,
             hdr_offset : int   = None) -> dict:
        """
        Read OpendTect CBVS.

        Parameters
        ----------
        n_samples  : samples/trace  (auto from header if None)
        dt_ms      : sample interval ms  (auto if None)
        n_traces   : trace count  (auto from file size if None)
        hdr_offset : byte offset to data start  (auto if None)
        """
        self._load()
        raw = self.raw

        if raw[:3] == self.DGB_MAGIC:
            print("[INFO] dGB / OpendTect CBVS magic confirmed OK")
        else:
            print(f"[WARNING] Unexpected magic: {raw[:4]!r}")

        hdr_dt_ms, hdr_ns, hdr_z0 = self._parse_dgb_header()

        if n_samples is None:
            n_samples = hdr_ns if hdr_ns else 1500
            print(f"[INFO] n_samples = {n_samples}  (from header scan)")

        if dt_ms is None:
            dt_ms = hdr_dt_ms if hdr_dt_ms else 2.0
            print(f"[INFO] dt        = {dt_ms} ms  (from header scan)")

        dt = dt_ms * 1e-3

        if hdr_offset is None:
            hdr_offset, inferred_ntr = self._find_data_offset(n_samples)
        else:
            inferred_ntr = (len(raw) - hdr_offset) // (n_samples * 4)

        if n_traces is None:
            n_traces = inferred_ntr

        print(f"\n[INFO] Reading : {n_traces} traces x {n_samples} samples")
        print(f"[INFO] dt      : {dt_ms:.4f} ms | record length: "
              f"{n_samples * dt_ms / 1000:.3f} s\n")

        # -- NumPy 2.0-compatible: use dtype='<f4' directly -----------------
        data_bytes = n_traces * n_samples * 4
        data_raw   = raw[hdr_offset : hdr_offset + data_bytes]

        if len(data_raw) < data_bytes:
            print(f"[WARNING] File shorter than expected!")
            n_traces = len(data_raw) // (n_samples * 4)
            data_raw = data_raw[:n_traces * n_samples * 4]

        data = np.frombuffer(data_raw, dtype="<f4").reshape(n_traces, n_samples).copy()
        data = np.where(np.isfinite(data), data, 0.0)

        twt = np.arange(n_samples) * dt
        cdp = np.arange(1, n_traces + 1)

        print(f"[INFO] Amplitude range  : {data.min():.4g}  to  {data.max():.4g}")
        print(f"[INFO] Non-zero traces  : "
              f"{np.sum(np.any(data != 0, axis=1))} / {n_traces}")

        return {
            "data"     : data,
            "dt"       : dt,
            "dt_ms"    : dt_ms,
            "n_traces" : n_traces,
            "n_samples": n_samples,
            "cdp"      : cdp,
            "twt"      : twt,
            "z_start"  : hdr_z0 or 0.0,
        }


# =============================================================================
#  Standard SEG-Y reader
# =============================================================================

def read_segy(filepath: str) -> dict:
    if not SEGYIO_AVAILABLE:
        raise ImportError("Install segyio: pip install segyio")
    print(f"[INFO] Reading SEG-Y: {filepath}")
    with segyio.open(filepath, "r", ignore_geometry=True) as f:
        n_traces  = f.tracecount
        n_samples = len(f.samples)
        dt        = segyio.tools.dt(f) / 1e6
        twt       = f.samples / 1000.0
        data      = np.stack([f.trace[i] for i in range(n_traces)])
        cdp       = np.array([f.header[i][segyio.TraceField.CDP]
                               for i in range(n_traces)], dtype=np.int32)
    print(f"[INFO] {n_traces} traces x {n_samples} samples | dt={dt*1e3:.3f} ms")
    return {"data": data, "dt": dt, "dt_ms": dt*1e3,
            "n_traces": n_traces, "n_samples": n_samples,
            "cdp": cdp, "twt": twt, "z_start": 0.0}


# =============================================================================
#  SAVE
# =============================================================================

def save_npy(seismic: dict, out_dir: str = "."):
    os.makedirs(out_dir, exist_ok=True)
    np.save(os.path.join(out_dir, "seismic_data.npy"), seismic["data"])
    np.save(os.path.join(out_dir, "seismic_twt.npy"),  seismic["twt"])
    np.save(os.path.join(out_dir, "seismic_cdp.npy"),  seismic["cdp"])
    print(f"\n[SAVED] NPY  ->  {out_dir}/seismic_data.npy  "
          f"shape={seismic['data'].shape}")

def save_segy(seismic: dict, out_path: str):

    if not SEGYIO_AVAILABLE:
        print("[SKIP] segyio not available.")
        return

    data = seismic["data"].astype(np.float32)

    # 🔥 clean bad values
    data = np.where(np.abs(data) > 1e6, 0, data)

    dt_us = int(seismic["dt"] * 1e6)
    n_tr, ns = data.shape
    cdp = seismic["cdp"]

    spec = segyio.spec()
    spec.tracecount = n_tr
    spec.format = 5  # ✅ IEEE float
    spec.samples = range(ns)

    # (Optional for 2D)
    # spec.sorting = segyio.TraceSortingFormat.INLINE_SORTING

    with segyio.create(out_path, spec) as f:

        f.bin.update(
            hdt=dt_us,
            dto=dt_us,
            hns=ns,
            nso=ns
        )

        for i in range(n_tr):
            f.trace[i] = data[i]

            f.header[i].update({
            segyio.TraceField.CDP: int(cdp[i]),
            segyio.TraceField.TRACE_SEQUENCE_LINE: i + 1,
        })

    print(f"[SAVED] SEGY -> {out_path}")

# =============================================================================
#  VISUALISATION
# =============================================================================

def plot_seismic_section(seismic, clip_pct=98, cmap="gray",
                         title="2D Seismic Section (OpendTect CBVS)",
                         out_path=None, dpi=300):
    data = seismic["data"].T
    twt  = seismic["twt"]
    cdp  = seismic["cdp"]
    vmax = np.nanpercentile(np.abs(data), clip_pct)
    vmin = -vmax if vmax > 0 else -1

    fig, axes = plt.subplots(1, 2, figsize=(18, 9),
                              gridspec_kw={"width_ratios": [3, 1]})
    ax = axes[0]
    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                   extent=[cdp[0], cdp[-1], twt[-1], twt[0]],
                   interpolation="bilinear")
    ax.set_xlabel("CDP / Trace Number", fontsize=13, fontweight="bold")
    ax.set_ylabel("Two-Way Time  (s)",  fontsize=13, fontweight="bold")
    ax.set_title(title, fontsize=15, fontweight="bold", pad=12)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="both", direction="in", top=True, right=True)
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="Amplitude")

    ax2  = axes[1]
    rms  = np.sqrt(np.mean(data**2, axis=1))
    ax2.plot(rms, twt, color="#E63946", lw=1.5)
    ax2.fill_betweenx(twt, 0, rms, alpha=0.2, color="#E63946")
    ax2.invert_yaxis()
    ax2.set_xlabel("RMS Amplitude", fontsize=12)
    ax2.set_ylabel("TWT  (s)",      fontsize=12)
    ax2.set_title("RMS Profile",    fontsize=13, fontweight="bold")
    ax2.tick_params(which="both", direction="in")
    ax2.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax2.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax2.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Section plot  ->  {out_path}")
    plt.show()


def plot_amplitude_spectrum(seismic, n_traces_sample=100,
                            out_path=None, dpi=300):
    data  = seismic["data"]
    dt    = seismic["dt"]
    step  = max(1, data.shape[0] // n_traces_sample)
    avg   = np.mean(np.abs(np.fft.rfft(data[::step], axis=1)), axis=0)
    freqs = np.fft.rfftfreq(seismic["n_samples"], d=dt)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(freqs, avg, color="#2A9D8F", lw=2)
    ax.fill_between(freqs, avg, alpha=0.2, color="#2A9D8F")
    ax.set_xlabel("Frequency  (Hz)", fontsize=13)
    ax.set_ylabel("Amplitude",       fontsize=13)
    ax.set_title("Average Amplitude Spectrum", fontsize=14, fontweight="bold")
    ax.set_xlim(0, freqs[-1])
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(4))
    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Spectrum      ->  {out_path}")
    plt.show()


def plot_trace_wiggle(seismic, n_traces=50, gain=1.0,
                      out_path=None, dpi=300):
    data   = seismic["data"]
    twt    = seismic["twt"]
    step   = max(1, seismic["n_traces"] // n_traces)
    subset = data[::step]
    n_plot = subset.shape[0]
    norm   = np.nanpercentile(np.abs(subset), 95) or 1.0
    subset = subset / norm * gain

    fig, ax = plt.subplots(figsize=(14, 8))
    for i in range(n_plot):
        tr = subset[i]
        ax.plot(tr + i, twt, color="k", lw=0.4)
        ax.fill_betweenx(twt, i, tr + i, where=(tr > 0),
                         color="#264653", alpha=0.7)
    ax.set_xlim(-1, n_plot)
    ax.invert_yaxis()
    ax.set_xlabel("Trace Index (subsampled)", fontsize=13)
    ax.set_ylabel("Two-Way Time  (s)",        fontsize=13)
    ax.set_title("Wiggle Trace Display",      fontsize=14, fontweight="bold")
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="both", direction="in", right=True)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"[SAVED] Wiggle plot   ->  {out_path}")
    plt.show()


def diagnose_cbvs(filepath: str, n_samples_guess: int = 1500):
    fsize = os.path.getsize(filepath)
    print(f"\n{'='*60}")
    print(f"CBVS DIAGNOSTIC: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    print(f"File size : {fsize:,} bytes  ({fsize/1e6:.3f} MB)")
    print(f"\nIf n_samples = {n_samples_guess}:")
    for hoff in [64, 128, 256, 512, 1024, 2048, 4000]:
        data_sz = fsize - hoff
        if data_sz > 0:
            n_tr = data_sz // (n_samples_guess * 4)
            rem  = data_sz % (n_samples_guess * 4)
            print(f"  hdr={hoff:5d}  ->  {n_tr:6d} traces  (remainder {rem} bytes)")
    print(f"{'='*60}\n")


# =============================================================================
#  MAIN  --  edit settings below
# =============================================================================

if __name__ == "__main__":

    # ---- USER SETTINGS -------------------------------------------------------
    INPUT_FORMAT = "cbvs"           # "cbvs" or "segy"
    INPUT_FILE   = "/media/ashraf/𝓐𝓢𝓗𝓡𝓐𝓕1/Seismic-data/F3_Demo_2023/Seismics/Seismic/Seismic^28.cbvs"   # <- your file name
    OUTPUT_DIR   = "seismic_output"

    # Leave as None to auto-detect. Override if auto-detect is wrong:
    N_SAMPLES    = None     # e.g. 1500
    DT_MS        = None     # e.g. 2.0
    HDR_OFFSET   = None     # e.g. 128
    # --------------------------------------------------------------------------

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # STEP 0: inspect
    if INPUT_FORMAT == "cbvs":
        reader = OpendTectCBVSReader(INPUT_FILE)
        reader.inspect_header(n_bytes=256)
        diagnose_cbvs(INPUT_FILE, n_samples_guess=N_SAMPLES or 1500)

    # STEP 1: read
    if INPUT_FORMAT == "cbvs":
        seismic = reader.read(n_samples=N_SAMPLES, dt_ms=DT_MS,
                              hdr_offset=HDR_OFFSET)
    else:
        seismic = read_segy(INPUT_FILE)

    # STEP 2: save NPY
    save_npy(seismic, out_dir=OUTPUT_DIR)

    # STEP 3: save SEG-Y
    save_segy(seismic, out_path=os.path.join(OUTPUT_DIR, "converted.segy"))

    # STEP 4: visualise
    plot_seismic_section(
        seismic, clip_pct=98, cmap="gray",
        out_path=os.path.join(OUTPUT_DIR, "seismic_section.png"), dpi=300)

    plot_amplitude_spectrum(
        seismic,
        out_path=os.path.join(OUTPUT_DIR, "amplitude_spectrum.png"), dpi=300)

    plot_trace_wiggle(
        seismic, n_traces=60, gain=1.2,
        out_path=os.path.join(OUTPUT_DIR, "wiggle_display.png"), dpi=300)

    print(f"\n{'='*50}")
    print(f"  ALL DONE  ->  outputs in: {OUTPUT_DIR}/")
    print(f"{'='*50}")
