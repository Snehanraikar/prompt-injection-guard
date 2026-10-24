"""Column-width (3.5 in) figures for the IEEE paper, generated from results/*.csv."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from piguard import config as C
from piguard.plots import GRID, INK, INK2, SERIES

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.8})
W = 3.5
R = C.RESULTS_DIR


def save(fig, name):
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def architecture():
    fig, ax = plt.subplots(figsize=(W, 2.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    fs = 5.6

    def box(x, y, w, h, text, fc, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    fc=fc, ec=INK2, lw=0.6))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                fontweight="bold" if bold else "normal", color=INK, linespacing=1.2)

    def arrow(p, q, label=None, off=(0, 0.12), rad=0.0, color=INK2):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, lw=0.6, color=color,
                                     connectionstyle=f"arc3,rad={rad}"))
        if label:
            ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], label, ha="center", va="bottom",
                    fontsize=5.2, color=INK2, bbox=dict(fc="#fcfcfb", ec="none", pad=0.4))

    # Layer 3 container around both detectors
    ax.add_patch(FancyBboxPatch((4.35, 0.25), 3.45, 6.15, boxstyle="round,pad=0.04,rounding_size=0.2",
                                fc="#f6f5f2", ec=INK2, lw=0.6, ls="--"))
    ax.text(6.07, 1.35, "Layer 3: Runtime guard", ha="center", fontsize=fs, fontweight="bold", color=INK)
    ax.text(6.07, 0.55, "policy · alerts · lockdown\naudit log", ha="center", fontsize=5.0, color=INK2, linespacing=1.2)

    box(0.05, 4.75, 1.55, 1.1, "User\ninstruction", "#ffffff")
    box(2.15, 4.75, 1.65, 1.1, "LLM\nagent", "#ffffff", bold=True)
    box(4.6, 4.75, 2.95, 1.1, "Layer 2: Behavioural\nmonitor (allow / block)", "#cde2fb", bold=True)
    box(8.25, 4.75, 1.7, 1.1, "Tool / API", "#ffffff")
    box(4.6, 2.35, 2.95, 1.1, "Layer 1: Content\ndetector (quarantine)", "#fde3d6", bold=True)
    box(8.25, 2.35, 1.7, 1.1, "Tool output\n(untrusted)", "#ffffff")

    arrow((1.6, 5.3), (2.15, 5.3), "$g$")
    arrow((3.8, 5.3), (4.6, 5.3), "$a_t$")
    arrow((7.55, 5.3), (8.25, 5.3), "allow")
    arrow((9.1, 4.75), (9.1, 3.45))
    arrow((8.25, 2.9), (7.55, 2.9), "$o_t$")
    arrow((6.07, 3.45), (6.07, 4.75), "scores", off=(0.42, -0.12))
    arrow((4.6, 2.9), (2.97, 4.75), "sanitised $o_t$", off=(-0.75, -0.35), rad=-0.3)
    save(fig, "fig1_architecture.png")


def layer1():
    t = pd.read_csv(R / "text_metrics.csv")
    t = t[t.threshold_mode == "val-tuned"]
    names = ["protectai_deberta_v2", "wolf_defender", "tfidf_lr", "minilm_xgb", "stacked_ensemble"]
    labels = ["ProtectAI\nDeBERTa-v3*", "Wolf\nDefender*", "TF-IDF\n+LR", "MiniLM\n+XGB", "Stacked\nensemble"]
    fig, ax = plt.subplots(figsize=(W, 1.85))
    import numpy as np
    x = np.arange(len(names))
    for i, (s, lab) in enumerate((("test", "In-distribution test"), ("ood", "Out-of-distribution test"))):
        v = [t[(t.model == n) & (t.eval_set == s)].f1.iloc[0] for n in names]
        bars = ax.bar(x + (i - 0.5) * 0.38, v, 0.35, color=SERIES[i], label=lab)
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.01, f"{val:.2f}", ha="center", va="bottom", fontsize=5.6, color=INK2)
    ax.set_xticks(x, labels)
    ax.set_ylim(0.6, 1.02)
    ax.set_ylabel("F1-score")
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
    save(fig, "fig2_layer1_f1.png")


def layer2():
    b = pd.read_csv(R / "behavior_metrics.csv")
    b = b[b.protocol == "unseen_attacker_goals"].copy()
    lab = {"rule_baseline (L1 flag + risky tool)": "Rule baseline", "text_only_lr (L1 scores)": "Text scores only (LR)",
           "isolation_forest (unsupervised)": "Isolation Forest", "behaviour_only_xgb (no L1)": "Behaviour only (XGB)",
           "full_lr": "Full features (LR)", "full_rf": "Full features (RF)", "full_xgb (proposed)": "Proposed (XGB)"}
    b["name"] = b.model.map(lab)
    fig, ax = plt.subplots(figsize=(W, 1.9))
    y = range(len(b))
    ax.barh(list(y), b.f1, color=[SERIES[0] if "Proposed" not in n else SERIES[1] for n in b.name], height=0.6)
    for yi, v, f in zip(y, b.f1, b.fpr):
        ax.text(v + 0.01, yi, f"F1 {v:.3f}  (FPR {f:.1%})", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(list(y), b.name)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.32)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel("F1-score (hijacked tool-call detection, unseen attacker goals)")
    ax.grid(axis="y", visible=False)
    save(fig, "fig3_layer2_f1.png")


def importance():
    imp = pd.read_csv(R / "behavior_feature_importance.csv", index_col=0).iloc[:, 0].head(10)
    fig, ax = plt.subplots(figsize=(W, 1.75))
    ax.barh(range(len(imp)), imp.values, color=SERIES[0], height=0.6)
    ax.set_yticks(range(len(imp)), [s.replace("_", "\\_") if False else s for s in imp.index], fontfamily="monospace", fontsize=6.3)
    ax.invert_yaxis()
    for i, v in enumerate(imp.values):
        ax.text(v + 0.004, i, f"{v:.3f}", va="center", fontsize=5.8, color=INK2)
    ax.set_xlabel("Share of total XGBoost gain")
    ax.set_xlim(0, imp.max() * 1.18)
    ax.grid(axis="y", visible=False)
    save(fig, "fig4_importance.png")


def guard():
    sw = pd.read_csv(R / "guard_threshold_sweep.csv")
    fig, ax = plt.subplots(figsize=(W, 1.7))
    ax.plot(sw.threshold, sw.attack_prevention_rate * 100, color=SERIES[0], lw=1.4, marker="o", ms=2.5, label="Attack prevention rate")
    ax.plot(sw.threshold, sw.benign_utility * 100, color=SERIES[1], lw=1.4, marker="s", ms=2.5, label="Benign task utility")
    ax.axvline(0.5, color=GRID, lw=0.8, ls="--")
    ax.text(0.52, 97.25, "operating point (0.5)", fontsize=5.6, color=INK2)
    ax.set_ylim(97, 100.3)
    ax.set_xlabel("Layer-2 blocking threshold")
    ax.set_ylabel("Rate (%)")
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
    save(fig, "fig5_tradeoff.png")


if __name__ == "__main__":
    architecture(); layer1(); layer2(); importance(); guard()
    print("figures ->", OUT)
