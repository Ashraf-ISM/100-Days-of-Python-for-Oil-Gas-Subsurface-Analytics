"""QC engine stub."""
from __future__ import annotations

from qc.qc_rules import DEFAULT_RULES


def run_qc(*_args, **_kwargs):
    rules = DEFAULT_RULES
    return [
        {"check": "missing_values", "status": "PASS", "count": 0, "details": f"max_pct={rules['missing_values']['max_pct']}"},
        {"check": "spike_detection", "status": "PASS", "count": 0, "details": f"zscore={rules['spike_detection']['zscore']}"},
        {"check": "depth_gaps", "status": "PASS", "count": 0, "details": f"max_gap={rules['depth_gaps']['max_gap']}"},
    ]
