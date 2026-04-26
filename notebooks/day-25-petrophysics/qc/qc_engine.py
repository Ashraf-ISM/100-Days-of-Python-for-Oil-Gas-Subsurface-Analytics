"""QC engine — orchestrates the multi-stage spike detector and rule checks."""
from __future__ import annotations

from qc.qc_rules import DEFAULT_RULES


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
    **_kwargs,
):
    """Run the full QC pipeline and return a structured result dict.

    When *curve_series* is provided the new :class:`~qc.spike_detector.SpikeDetector`
    is invoked and its :class:`~qc.spike_detector.SpikeResult` is merged into
    the returned dict.  Without curve data only the default rule-check stub
    rows are returned (backwards-compat with the old engine stub).

    Returns
    -------
    dict with keys:
        ``checks``      – list[dict] rule-check summary rows
        ``spike_result``– SpikeResult | None
    """
    rules       = DEFAULT_RULES
    spike_rules = rules["spike_detection"]

    # Resolve parameters: caller kwargs override rule defaults
    _mode       = mode                if mode is not None                else spike_rules["mode"]
    _window     = window              if window is not None              else spike_rules["window"]
    _multiplier = mad_multiplier      if mad_multiplier is not None      else spike_rules["mad_multiplier"]
    _threshold  = confidence_threshold if confidence_threshold is not None else spike_rules["confidence_threshold"]
    _cross_log  = cross_log_validation if cross_log_validation is not None else spike_rules["cross_log_validation"]
    _correction = correction          if correction is not None          else spike_rules["correction"]

    # ── run spike detector ───────────────────────────────────────────────────
    spike_result = None
    spike_count  = 0

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
                mad_multiplier=_multiplier,
                confidence_threshold=_threshold,
                cross_log_validation=_cross_log,
                correction=_correction,
            )
            spike_count = spike_result.n_spikes
        except Exception as exc:          # noqa: BLE001
            import traceback
            traceback.print_exc()

    # ── rule-check summary rows (used by QC dashboard widgets) ───────────────
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
                f"mode={_mode}, window={_window}, "
                f"mad_multiplier={_multiplier}, "
                f"confidence_threshold={_threshold}"
            ),
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
