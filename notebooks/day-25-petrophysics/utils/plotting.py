import matplotlib.pyplot as plt

def plot_logs(df):
    fig, axes = plt.subplots(ncols=3, figsize=(10, 8), sharey=True)

    axes[0].plot(df["GR"], df["DEPTH"])
    axes[0].set_title("Gamma Ray")

    axes[1].plot(df["PHI"], df["DEPTH"])
    axes[1].set_title("Porosity")

    axes[2].plot(df["Sw"], df["DEPTH"])
    axes[2].set_title("Water Saturation")

    for ax in axes:
        ax.invert_yaxis()

    plt.tight_layout()
    plt.show()
