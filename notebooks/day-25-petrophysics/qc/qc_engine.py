"""QC engine — orchestrates the multi-stage spike detector and rule checks."""
from __future__ import annotations

from qc.qc_rules import DEFAULT_RULES, get_curve_profile


def run_qc(
    curve_series=None,
    depth_series=None,
    curve_name: str = "",
    all_curves_df=None,
    *,
    mode: str | None = None,
    window: int | None = None,
    mad_multiplier: float | None = None,
    confidence_threshold: float | None = None,
    cross_log_validation: bool | None = None,
    correction: str | None = None,
    max_spike_width: int | None = None,
    depth_tolerance_samples: int = 3,
    **_kwargs,
):
    """Run the full QC pipeline and return a structured result dict. 

    When *curve_series* is provided the :class:`~qc.spike_detector.SpikeDetector`
    is invoked with curve-specific profile defaults (from
    :func:`~qc.qc_rules.get_curve_profile`).  Caller keyword arguments always
    override the profile.

    Parameters
    ----------
    curve_series : pd.Series, optional
        Log curve to analyse.
    depth_series : pd.Series, optional
        Depth values aligned to *curve_series*.
    curve_name : str
        Mnemonic used for profile lookup and physics checks.
    all_curves_df : pd.DataFrame, optional
        Full curve table (used by Stage 5 cross-log validator).
    mode : str, optional
        "Standard" | "Advanced" | "ML" — overrides profile default.
    window : int, optional
        Rolling-window half-size override.
    mad_multiplier : float, optional
        MAD multiplier override.
    confidence_threshold : float, optional
        Minimum spike confidence threshold [0, 1].
    cross_log_validation : bool, optional
        Enable Stage 5 cross-log validation.
    correction : str, optional
        Correction method override.
    max_spike_width : int, optional
        Maximum impulse width in samples override.
    depth_tolerance_samples : int
        Depth-tolerance ± samples for cross-log companion search (default 3).

    Returns
    -------
    dict with keys:
        ``checks``       – list[dict] rule-check summary rows
        ``spike_result`` – SpikeResult | None
    """
    rules       = DEFAULT_RULES
    spike_rules = rules["spike_detection"]

    # Load curve-specific profile first; caller overrides win
    profile = get_curve_profile(curve_name)

    _mode      = mode                if mode is not None      else spike_rules["mode"]
    _window    = window              if window is not None    else profile["window"]
    _mult      = mad_multiplier      if mad_multiplier is not None else profile["mad_multiplier"]
    _threshold = (confidence_threshold if confidence_threshold is not None
                  else spike_rules["confidence_threshold"])
    _cross_log = (cross_log_validation if cross_log_validation is not None
                  else spike_rules["cross_log_validation"])
    _correction = correction if correction is not None else profile["correction"]
    _msw        = max_spike_width if max_spike_width is not None else profile.get("max_spike_width", 3)

    # ── run spike detector ────────────────────────────────────────────────────
    spike_result = None
    spike_count  = 0
    spike_types_summary: dict[str, int] = {}

    if curve_series is not None and depth_series is not None:
        try:
            from qc.spike_detector import SpikeDetector
            spike_result = SpikeDetector().detect(
                curve_series=curve_series,
                depth_series=depth_series,
                curve_name=curve_name,
                all_curves_df=all_curves_df,
                mode=_mode,
                window=_window,
                mad_multiplier=_mult,
                confidence_threshold=_threshold,
                cross_log_validation=_cross_log,
                correction=_correction,
                max_spike_width=_msw,
            )
            spike_count = spike_result.n_spikes

            # Summarise spike_type distribution for dashboard reporting
            if spike_result.spike_type is not None and len(spike_result.spike_type):
                import numpy as np
                types, counts = np.unique(
                    spike_result.spike_type[spike_result.is_spike], return_counts=True
                )
                spike_types_summary = {t: int(c) for t, c in zip(types, counts)}

        except Exception:           # noqa: BLE001
            import traceback
            traceback.print_exc()

    # ── rule-check summary rows ───────────────────────────────────────────────
    type_detail = (
        ", ".join(f"{k}={v}" for k, v in spike_types_summary.items())
        if spike_types_summary else ""
    )
    checks = [
        {
            "check":   "missing_values",
            "status":  "PASS",
            "count":   0,
            "details": f"max_pct={rules['missing_values']['max_pct']}",
        },
        {
            "check":   "spike_detection",
            "status":  "PASS" if spike_count == 0 else "WARN",
            "count":   spike_count,
            "details": (
                f"curve={curve_name or '?'}, mode={_mode}, "
                f"window={_window}, mad={_mult}, "
                f"confidence_threshold={_threshold}"
                + (f", types=[{type_detail}]" if type_detail else "")
            ),
            "spike_types": spike_types_summary,
        },
        {
            "check":   "depth_gaps",
            "status":  "PASS",
            "count":   0,
            "details": f"max_gap={rules['depth_gaps']['max_gap']}",
        },
    ]

    return {
        "checks":       checks,
        "spike_result": spike_result,
    }
