"""QC rule defaults."""
DEFAULT_RULES = {
    "missing_values": {"max_pct": 5.0},
    "spike_detection": {
        "mode":                 "Standard",     # Standard | Advanced | ML
        "mad_multiplier":       3.0,
        "window":               5,
        "confidence_threshold": 0.5,
        "cross_log_validation": True,
        "correction":           "local_median", # local_median | linear | cubic | keep
        # Legacy key kept for backward-compat with old engine references
        "zscore":               4.0,
    },
    "depth_gaps": {"max_gap": 1.0},
}