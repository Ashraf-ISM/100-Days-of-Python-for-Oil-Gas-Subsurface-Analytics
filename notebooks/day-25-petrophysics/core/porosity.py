def compute_porosity(df, rho_matrix=2.65, rho_fluid=1.0):
    rho_bulk = df["RHOB"]

    phi_d = (rho_matrix - rho_bulk) / (rho_matrix - rho_fluid)

    if "NPHI" in df.columns:
        phi = (phi_d + df["NPHI"]) / 2
    else:
        phi = phi_d

    return phi.clip(0, 0.5)
