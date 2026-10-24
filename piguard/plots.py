"""Static report figures (matplotlib) using a CVD-validated categorical palette."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve, roc_curve

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold", "legend.frameon": False,
})


def roc_pr(curves, path, title):
    """curves: list of (label, y, p). One colour per model, fixed order."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for i, (name, y, p) in enumerate(curves):
        c = SERIES[i % len(SERIES)]
        fpr, tpr, _ = roc_curve(y, p)
        a1.plot(fpr, tpr, color=c, lw=2, label=name)
        pr, rc, _ = precision_recall_curve(y, p)
        a2.plot(rc, pr, color=c, lw=2, label=name)
    a1.plot([0, 1], [0, 1], color=GRID, lw=1, ls="--")
    a1.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC")
    a2.set(xlabel="Recall", ylabel="Precision", title="Precision-Recall")
    a2.legend(loc="lower left", fontsize=8)
    fig.suptitle(title, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def grouped_bars(labels, groups, path, title, ylabel, ylim=(0, 1)):
    """groups: dict series_name -> list of values aligned with labels."""
    fig, ax = plt.subplots(figsize=(max(7, 1.3 * len(labels) * len(groups) / 2), 4.6))
    w = 0.8 / len(groups)
    x = np.arange(len(labels))
    for i, (g, vals) in enumerate(groups.items()):
        bars = ax.bar(x + (i - (len(groups) - 1) / 2) * w, vals, w * 0.92, color=SERIES[i], label=g)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7, color=INK2)
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set(ylabel=ylabel, ylim=ylim)
    ax.set_title(title, pad=30)
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=min(len(groups), 4), loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def confusion(cm, path, title, labels=("benign", "attack")):
    fig, ax = plt.subplots(figsize=(3.8, 3.4))
    ax.imshow(cm, cmap="Blues")
    ax.grid(False)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i][j]:,}", ha="center", va="center",
                    color="white" if cm[i][j] > np.max(cm) / 2 else INK, fontsize=11)
    ax.set_xticks([0, 1], labels)
    ax.set_yticks([0, 1], labels)
    ax.set(xlabel="Predicted", ylabel="Actual", title=title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
