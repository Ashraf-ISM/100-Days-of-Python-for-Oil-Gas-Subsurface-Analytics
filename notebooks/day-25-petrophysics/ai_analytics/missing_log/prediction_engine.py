import pandas as pd
import numpy as np

class MissingLogEngine:
    """
    Core ML logic for Predicting Missing Well Logs.
    """
    def __init__(self, data: pd.DataFrame):
        self.df = data

    def get_log_statistics(self, target_log: str):
        """Analyze the target log for missing data stats."""
        if target_log not in self.df.columns:
            return None
            
        series = self.df[target_log]
        total_count = len(series)
        missing_count = series.isna().sum()
        missing_pct = (missing_count / total_count) * 100 if total_count > 0 else 0
        
        return {
            "total": total_count,
            "missing": missing_count,
            "missing_pct": missing_pct,
            "valid": total_count - missing_count
        }

    def suggest_features(self, target_log: str):
        """Suggest candidate features based on correlation."""
        if target_log not in self.df.columns:
            return []
            
        numeric_df = self.df.select_dtypes(include=[np.number])
        if target_log not in numeric_df.columns:
            return []
            
        correlations = numeric_df.corr()[target_log].abs().sort_values(ascending=False)
        # Exclude self
        candidates = correlations.index[correlations.index != target_log].tolist()
        return candidates[:5]

    def train_simple_model(self, target_log: str, feature_logs: list[str]):
        """Placeholder for actual ML training logic."""
        # In a real scenario, we'd use Scikit-Learn here
        pass
