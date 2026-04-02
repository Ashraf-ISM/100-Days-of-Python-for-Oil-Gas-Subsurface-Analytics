def compute_vsh(GR):
    GR_min = GR.min()
    GR_max = GR.max()
    Vsh = (GR - GR_min) / (GR_max - GR_min)
    return Vsh.clip(0, 1)
