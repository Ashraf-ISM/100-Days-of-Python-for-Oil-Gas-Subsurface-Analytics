"""
missing_log_window.py
Thin shim to maintain backwards compatibility.
Exports MissingLogPredictionWindow as an alias for MissingLogPanel.
"""
from .missing_log_panel import MissingLogPanel as MissingLogPredictionWindow
