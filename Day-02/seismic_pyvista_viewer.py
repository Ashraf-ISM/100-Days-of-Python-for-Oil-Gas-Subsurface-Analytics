"""
Seismic SEG-Y Visualization with PyVista
=========================================
Supports both real SEG-Y files and synthetic data.
Includes LIVE interactive 3D windows + screenshot saving.

Install dependencies:
    pip install segyio pyvista numpy matplotlib

Usage:
    python seismic_segy_pyvista.py --segy /home/ashraf/Downloads/ST8511r92.segy
    python seismic_segy_pyvista.py --synthetic
    python seismic_segy_pyvista.py --segy file.segy --save-only   # no window, just PNGs
"""

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt

try:
    import pyvista as pv
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    print("[WARNING] pyvista not installed.  pip install pyvista")

try:
    import segyio
    HAS_SEGYIO = True
except ImportError:
    HAS_SEGYIO = False
    print("[WARNING] segyio not installed.   pip install segyio")


# ─── 1. DATA LOADING ─────────────────────────────────────────────────────────

def load_segy(filepath: str):
    """
    Load a post-stack 3-D SEG-Y file.
    Tries structured read first; falls back to unstructured if geometry
    headers are missing (common with 2-D or prestack data).
    """
    if not HAS_SEGYIO:
        raise ImportError("segyio is required to load SEG-Y files.")

    print(f"[INFO] Loading SEG-Y file: {filepath}")

    # ── Attempt structured (3-D) read ────────────────────────────────────────
    try:
        with segyio.open(filepath, ignore_geometry=False) as f:
            inlines    = f.ilines
            crosslines = f.xlines
            n_samples  = f.samples.size
            dt         = segyio.tools.dt(f) / 1_000   # µs → ms
            cube       = segyio.tools.cube(f)          # (n_il, n_xl, n_t)

        print(f"[INFO] Structured read OK — cube shape: {cube.shape}")
        info = dict(inlines=inlines, crosslines=crosslines,
                    n_samples=n_samples, dt_ms=dt, t_start_ms=0.0,
                    source="segy_3d")
        return cube.astype(np.float32), info

    except Exception as e:
        print(f"[WARN] Structured read failed ({e}). Trying unstructured…")

    # ── Fallback: unstructured read ───────────────────────────────────────────
    with segyio.open(filepath, ignore_geometry=True) as f:
        n_traces  = f.tracecount
        n_samples = f.samples.size
        dt        = segyio.tools.dt(f) / 1_000
        print(f"[INFO] Unstructured: {n_traces} traces × {n_samples} samples, dt={dt} ms")
        data = np.stack([f.trace[i] for i in range(n_traces)], axis=0).astype(np.float32)

    # Reshape into pseudo-3D (square-ish)
    n_xl  = max(1, int(round(n_traces ** 0.5)))
    n_il  = max(1, (n_traces + n_xl - 1) // n_xl)
    n_pad = n_il * n_xl - n_traces
    if n_pad:
        data = np.vstack([data, np.zeros((n_pad, n_samples), dtype=np.float32)])

    cube = data.reshape(n_il, n_xl, n_samples)
    print(f"[INFO] Pseudo-3D cube shape: {cube.shape}")

    info = dict(inlines=np.arange(n_il), crosslines=np.arange(n_xl),
                n_samples=n_samples, dt_ms=dt if dt > 0 else 2.0,
                t_start_ms=0.0, source="segy_2d")
    return cube, info


def make_synthetic_cube(n_inlines=60, n_crosslines=80, n_samples=120, seed=42):
    """Generate a realistic synthetic 3-D seismic cube."""
    print(f"[INFO] Generating synthetic cube ({n_inlines}×{n_crosslines}×{n_samples})")
    rng  = np.random.default_rng(seed)
    cube = np.zeros((n_inlines, n_crosslines, n_samples), dtype=np.float32)

    def ricker(f=30.0, length=21):
        t = (np.arange(length) - length // 2)
        return (1 - 2*(np.pi*f*t/length)**2) * np.exp(-(np.pi*f*t/length)**2)

    wav = ricker(); wav_h = wav.size // 2

    horizons = [(n_samples*0.20,  0.05,  0.04, 1.0,  1.5e-4),
                (n_samples*0.45, -0.03,  0.06, 0.8,  1.0e-4),
                (n_samples*0.70,  0.04, -0.05, 0.6, -1.2e-4)]

    for base, di, dx, amp, curv in horizons:
        for i in range(n_inlines):
            for j in range(n_crosslines):
                ci, cj = i - n_inlines//2, j - n_crosslines//2
                t0 = int(np.clip(base + di*ci + dx*cj + curv*(ci**2+cj**2),
                                 wav_h, n_samples-wav_h-1))
                for k in range(-wav_h, wav_h+1):
                    if 0 <= t0+k < n_samples:
                        cube[i, j, t0+k] += amp * wav[k+wav_h]

    ci, cx = n_inlines//2, n_crosslines//2
    ct = int(n_samples * 0.45)
    ii, xi = np.ogrid[:n_inlines, :n_crosslines]
    patch = ((ii-ci)/(n_inlines//8))**2 + ((xi-cx)/(n_crosslines//8))**2 < 1
    cube[patch, ct-2:ct+3] += 1.5
    cube += 0.08 * rng.standard_normal(cube.shape).astype(np.float32)

    info = dict(inlines=np.arange(n_inlines), crosslines=np.arange(n_crosslines),
                n_samples=n_samples, dt_ms=2.0, t_start_ms=0.0, source="synthetic")
    return cube, info


# ─── 2. PYVISTA GRID BUILDER ─────────────────────────────────────────────────

def cube_to_grid(cube, info):
    """Pack amplitude cube into a PyVista ImageData (works on all PyVista versions)."""
    ni, nx, nt = cube.shape
    dt = info["dt_ms"]
    GridClass = getattr(pv, "ImageData", None) or getattr(pv, "UniformGrid")
    grid = GridClass()
    grid.dimensions = (ni+1, nx+1, nt+1)
    grid.spacing    = (1.0, 1.0, dt)
    grid.origin     = (0.0, 0.0, info["t_start_ms"])
    grid.cell_data["amplitude"] = cube.ravel(order="F")
    return grid


# ─── 3. MATPLOTLIB 2-D OVERVIEW ──────────────────────────────────────────────

def plot_2d_sections(cube, info, out_dir="."):
    ni, nx, nt = cube.shape
    dt   = info["dt_ms"]
    clip = float(np.percentile(np.abs(cube), 98))
    cmap = "seismic"
    il_i, xl_i, t_i = ni//2, nx//2, nt//2

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    axes[0].imshow(cube[il_i, :, :].T, aspect="auto", cmap=cmap,
                   vmin=-clip, vmax=clip, extent=[0, nx, nt*dt, 0])
    axes[0].set_title(f"Inline {info['inlines'][il_i]}", fontsize=11)
    axes[0].set_xlabel("Crossline"); axes[0].set_ylabel("Time (ms)")

    axes[1].imshow(cube[:, xl_i, :].T, aspect="auto", cmap=cmap,
                   vmin=-clip, vmax=clip, extent=[0, ni, nt*dt, 0])
    axes[1].set_title(f"Crossline {info['crosslines'][xl_i]}", fontsize=11)
    axes[1].set_xlabel("Inline"); axes[1].set_ylabel("Time (ms)")

    axes[2].imshow(cube[:, :, t_i].T, aspect="auto", cmap=cmap,
                   vmin=-clip, vmax=clip, extent=[0, ni, 0, nx])
    axes[2].set_title(f"Time slice @ {t_i*dt:.0f} ms", fontsize=11)
    axes[2].set_xlabel("Inline"); axes[2].set_ylabel("Crossline")

    plt.suptitle(f"2-D Seismic Sections  [{info.get('source','')}]",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = f"{out_dir}/seismic_2d_sections.png"
    plt.savefig(path, dpi=150)
    plt.show()   # ← shows the matplotlib figure interactively
    plt.close()
    print(f"[INFO] Saved: {path}")


def plot_rms_map(cube, info, out_dir="."):
    ni, nx, nt = cube.shape
    w0, w1 = int(nt*0.35), int(nt*0.55)
    rms = np.sqrt(np.mean(cube[:, :, w0:w1]**2, axis=2))
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(rms.T, origin="lower", aspect="auto",
                   cmap="hot", extent=[0, ni, 0, nx])
    plt.colorbar(im, ax=ax, label="RMS Amplitude")
    ax.set_xlabel("Inline"); ax.set_ylabel("Crossline")
    ax.set_title(f"RMS Amplitude Map  (samples {w0}–{w1})")
    plt.tight_layout()
    path = f"{out_dir}/seismic_rms_map.png"
    plt.savefig(path, dpi=150)
    plt.show()   # ← shows the matplotlib figure interactively
    plt.close()
    print(f"[INFO] Saved: {path}")


# ─── 4. PYVISTA 3-D VISUALISATIONS ───────────────────────────────────────────

def viz_slices(cube, info, out_dir=".", save_only=False):
    """
    Three orthogonal amplitude slices.

    Parameters
    ----------
    save_only : bool
        If True  → renders off-screen and saves a PNG only (no window).
        If False → opens a LIVE interactive 3-D window. Close it to continue.
                   A screenshot is also saved automatically when you close.
    """
    ni, nx, nt = cube.shape
    grid  = cube_to_grid(cube, info)
    clip  = float(np.percentile(np.abs(cube), 98))
    cmap  = plt.get_cmap("RdBu_r", 256)

    sl_il = grid.slice(normal="x", origin=(ni//2, 0, 0))
    sl_xl = grid.slice(normal="y", origin=(0, nx//2, 0))
    sl_t  = grid.slice(normal="z", origin=(0, 0, (nt//2)*info["dt_ms"]))

    pv.set_plot_theme("document")

    # ── KEY CHANGE: off_screen=save_only ─────────────────────────────────────
    # off_screen=False  → interactive window opens (rotate / zoom / pan)
    # off_screen=True   → headless render, PNG only
    pl = pv.Plotter(off_screen=save_only, window_size=[1400, 900],
                    title="Seismic – Orthogonal Slices")
    pl.set_background("white")

    kw = dict(scalars="amplitude", cmap=cmap,
              clim=(-clip, clip), show_scalar_bar=False, lighting=False)
    pl.add_mesh(sl_il, **kw)
    pl.add_mesh(sl_xl, **kw)
    pl.add_mesh(sl_t,  **kw)

    pl.add_scalar_bar("Amplitude", vertical=True, height=0.6,
                      position_x=0.85, position_y=0.2,
                      n_labels=5, fmt="%.2f", color="black")
    pl.show_bounds(grid="back", location="outer", ticks="both", font_size=9,
                   color="black", xlabel="Inline",
                   ylabel="Crossline", zlabel="Time (ms)")
    pl.add_title("Seismic – Orthogonal Slices  (drag to rotate | scroll to zoom)",
                 font_size=11, color="black")

    pl.camera_position = "iso"
    pl.camera.azimuth   = -45
    pl.camera.elevation = 25

    path = f"{out_dir}/seismic_3d_slices.png"

    if save_only:
        pl.screenshot(path)
        pl.close()
        print(f"[INFO] Saved: {path}")
    else:
        print("[INFO] 3-D slice window open — drag to rotate, scroll to zoom.")
        print("       Close the window to continue to the volume render…")
        # show() opens the interactive window and BLOCKS until user closes it
        pl.show(screenshot=path)
        print(f"[INFO] Screenshot saved: {path}")


def viz_volume(cube, info, out_dir=".", save_only=False):
    """
    Full volume rendering — high amplitudes opaque, near-zero transparent.

    Parameters
    ----------
    save_only : bool
        Same as viz_slices — False = live window, True = PNG only.
    """
    ni, nx, nt = cube.shape
    grid  = cube_to_grid(cube, info)
    clip  = float(np.percentile(np.abs(cube), 98))
    cmap  = plt.get_cmap("RdBu_r", 512)

    pv.set_plot_theme("document")

    # ── KEY CHANGE: off_screen=save_only ─────────────────────────────────────
    pl = pv.Plotter(off_screen=save_only, window_size=[1400, 900],
                    title="Seismic Volume Rendering")
    pl.set_background("#0d1117")

    pl.add_volume(grid, scalars="amplitude", cmap=cmap,
                  clim=(-clip, clip),
                  opacity=[1.0, 0.3, 0.0, 0.3, 1.0],
                  opacity_unit_distance=max(ni, nx, nt) / 4,
                  shade=False)

    pl.add_scalar_bar("Amplitude", vertical=True, height=0.55,
                      position_x=0.87, position_y=0.22,
                      n_labels=5, fmt="%.2f", color="white")
    pl.show_bounds(grid="back", location="outer", ticks="both", font_size=9,
                   color="white", xlabel="Inline",
                   ylabel="Crossline", zlabel="Time (ms)")
    pl.add_title("Seismic Volume Rendering  (drag to rotate | scroll to zoom)",
                 font_size=11, color="white")

    pl.camera_position = "iso"
    pl.camera.azimuth   = -50
    pl.camera.elevation = 30

    path = f"{out_dir}/seismic_3d_volume.png"

    if save_only:
        pl.screenshot(path)
        pl.close()
        print(f"[INFO] Saved: {path}")
    else:
        print("[INFO] 3-D volume window open — drag to rotate, scroll to zoom.")
        print("       Close the window to finish.")
        pl.show(screenshot=path)
        print(f"[INFO] Screenshot saved: {path}")


# ─── 5. ENTRY POINT ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Seismic SEG-Y visualisation with PyVista",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live 3-D windows + screenshots (default):
  python seismic_segy_pyvista.py --segy /home/ashraf/Downloads/ST8511r92.segy

  # PNGs only, no windows (e.g. on a headless server):
  python seismic_segy_pyvista.py --segy file.segy --save-only

  # Synthetic data with live windows:
  python seismic_segy_pyvista.py --synthetic
        """
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--segy",      metavar="FILE",
                       help="Path to a SEG-Y / .sgy file")
    group.add_argument("--synthetic", action="store_true", default=False,
                       help="Use synthetic data instead of a real file")
    parser.add_argument("--outdir",    default=".",
                        help="Directory to save output PNGs (default: .)")
    parser.add_argument("--save-only", action="store_true", default=False,
                        help="Render off-screen only — no interactive windows")
    args = parser.parse_args()

    if args.segy:
        cube, info = load_segy(args.segy)
    else:
        cube, info = make_synthetic_cube()

    print(f"[INFO] Cube shape      : {cube.shape}")
    print(f"[INFO] Amplitude range : [{cube.min():.4f}, {cube.max():.4f}]")
    print(f"[INFO] Sample interval : {info['dt_ms']} ms")
    print(f"[INFO] Source          : {info.get('source')}")
    print(f"[INFO] Interactive 3-D : {'NO (--save-only)' if args.save_only else 'YES'}")

    os.makedirs(args.outdir, exist_ok=True)

    # 2-D matplotlib plots (always shown + saved)
    plot_2d_sections(cube, info, args.outdir)
    plot_rms_map(cube, info, args.outdir)

    # 3-D PyVista plots
    if HAS_PYVISTA:
        viz_slices(cube, info, args.outdir, save_only=args.save_only)
        viz_volume(cube, info, args.outdir, save_only=args.save_only)
    else:
        print("[INFO] Install pyvista for 3-D views:  pip install pyvista")

    print("\n[DONE] All outputs saved.")


if __name__ == "__main__":
    main()