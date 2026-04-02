def compute_sw(df, a=1, m=2, n=2, Rw=0.1):
    Rt = df["RT"]
    phi = df["PHI"]

    Sw = ((a * Rw) / (phi**m * Rt))**(1/n)
    return Sw.clip(0, 1)
