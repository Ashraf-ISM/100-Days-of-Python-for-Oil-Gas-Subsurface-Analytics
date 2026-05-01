"""Rock physics calculations panel""" 

from __future__ import annotations
def compute(*args, **kwargs):
    raise NotImplementedError("Calculation not implemented yet")


def compute_porosity_density(rho_b, rho_ma=2.65, rho_fl=1.0):
    """
    Compute porosity from bulk density using the density-porosity equation.
    
    Inputs:
        rho_b (float or np.array): Bulk density (g/cm³)
        rho_ma (float): Matrix density (g/cm³), default = 2.65 for limestone/dolomite
        rho_fl (float): Fluid density (g/cm³), default = 1.0 for fresh water
        
    Returns:
        float or np.array: Porosity (decimal, 0–1)
    """
    if isinstance(rho_b, (int, float)):
        rho_b = float(rho_b)
        if rho_b <= 0:
            raise ValueError("Bulk density must be positive")
        if rho_b > rho_ma:
            return 0.0
        
        # Density-porosity equation: phi = (rho_ma - rho_b) / (rho_ma - rho_fl)
        phi = (rho_ma - rho_b) / (rho_ma - rho_fl + 1e-9)
        return max(0.0, min(phi, 1.0))
    
    else:
        import numpy as np
        rho_b = np.asarray(rho_b, dtype=float)
        rho_b = np.where(rho_b <= 0, np.nan, rho_b)
        
        # Apply formula with safeguards
        phi = (rho_ma - rho_b) / (rho_ma - rho_fl + 1e-9)
        phi = np.where(phi < 0, 0.0, phi)
        phi = np.where(phi > 1, 1.0, phi)
        return phi
