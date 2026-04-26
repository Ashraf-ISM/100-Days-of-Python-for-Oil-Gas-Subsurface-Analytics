"""QC rule defaults."""
DEFAULT_RULES = {
    "missing_values": {"max_pct": 5.0},
    "spike_detection": {"zscore": 4.0},
    "depth_gaps": {"max_gap": 1.0},
}