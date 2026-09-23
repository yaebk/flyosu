"""
Figures for experiment 3.  Reads results/e3_learning.json and
results/e3_stability.json, writes PNGs.

    python -m experiments.figures_e3
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.figures import INK2, MUTED, RESULTS, SERIES, SURFACE, _edge_labels  # noqa: E402
from experiments.figures_e2 import FAMILIES, _clean  # noqa: E402

COND_TITLES = {"wired": "from the anatomical wiring", "blank": "from W = 0",
               "thresholds": "thresholds only (timing)"}


def fig_learning(res, path):
    conds = list(res["conditions"])
    runs = res["runs"]
    fig, axes = plt.subplots(1, len(conds), figsize=(4.0 * len(conds), 3.7), sharey=True)
    for ax, cond in zip(np.atleast_1d(axes), conds):
        ends, xmax = [], 0
        ctrl = [r for r in runs if r["label"] != "real connectome" and cond in r]
        for r in ctrl:
            ev = r[cond]["held_out"]
            x = [e["episode"] for e in ev]; y = [e["accuracy"] for e in ev]
            xmax = max(xmax, max(x))
            ax.plot(x, y, color=SERIES[1], lw=1.3, alpha=0.75, marker="o", ms=3.5,
                    markeredgecolor=SURFACE, markeredgewidth=1, solid_capstyle="round")
        if ctrl:
            Y = np.array([[e["accuracy"] for e in r[cond]["held_out"]] for r in ctrl])
            ends.append((Y[:, -1].mean(), f"rewired topology (x{len(ctrl)})", SERIES[1]))
        real = next((r for r in runs if r["label"] == "real connectome" and cond in r), None)
        if real:
            ev = real[cond]["held_out"]
            x = [e["episode"] for e in ev]; y = [e["accuracy"] for e in ev]
            xmax = max(xmax, max(x))
            ax.plot(x, y, color=SERIES[0], lw=2.4, marker="o", ms=4.5, markeredgecolor=SURFACE,
                    markeredgewidth=1, solid_capstyle="round", zorder=4)
            ends.append((y[-1], "real connectome", SERIES[0]))
        ax.set_title(COND_TITLES.get(cond, cond)); ax.set_xlabel("training episodes")
        ax.set_ylim(0, 0.5); _clean(ax)
        if ends:
            _edge_labels(ax, xmax, [e[0] for e in ends], [e[1] for e in ends], [e[2] for e in ends])
    np.atleast_1d(axes)[0].set_ylabel("held-out accuracy (stage 3, 3 charts)")
    L = res["learner"]
    fig.suptitle("Learning the readout, connectome frozen: real vs rewired",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, f"reward-modulated perturbation, sigma {L['sigma']}, lr {L['lr']} "
             f"annealed x{L['lr_decay']}/episode; one line per network", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0, 0.88, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def fig_radius(st, path):
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    for i, (fam, label) in enumerate(FAMILIES):
        v = np.array([r["spectral_radius"] for r in st["runs"] if r["family"] == fam])
        if len(v) == 0:
            continue
        x = i + np.linspace(-0.22, 0.22, len(v)) if len(v) > 1 else [i]
        ax.plot(x, v, "o", ms=6.5, color=SERIES[i], markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)
        ax.plot([i - 0.32, i + 0.32], [v.mean()] * 2, color=SERIES[i], lw=2)
        ax.annotate(f"{v.mean():.2f}" + (f" ± {v.std():.2f}" if len(v) > 1 else ""), (i, v.max()),
                    xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
    ax.axhline(1.0, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.annotate("radius 1", (3.5, 1.0), xytext=(0, 4), textcoords="offset points", fontsize=8,
                color=MUTED, ha="right")
    ax.set_xticks(range(4))
    ax.set_xticklabels([l.replace(" ", "\n", 1) for _, l in FAMILIES], fontsize=8.5)
    ax.set_ylabel("spectral radius, blank-field Jacobian")
    fig.suptitle("Recurrent gain is a property of the graph, not the eye map or output grouping",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "play regime; one dot per network; bar = mean.  Same graph -> same radius; "
             "rewired graph -> a third of it.", fontsize=8, color=INK2)
    _clean(ax); ax.set_ylim(0, 3.9)
    fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig(path, dpi=160); plt.close(fig)


def fig_noisy(res, e2, path):
    """Untrained lane-correctness, noise-free (e2) vs noise 0.03 (e3), real vs rewired."""
    stages = [1, 2, 3, 4, 5]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    real3 = next(r for r in res["runs"] if r["label"] == "real connectome")
    ctrl3 = [r for r in res["runs"] if r["label"] != "real connectome"]
    real2 = next(r for r in e2["runs"] if r["family"] == "real")
    ctrl2 = [r for r in e2["runs"] if r["family"] == "rewired topology"]
    x = np.arange(len(stages))
    series = [
        ("real, noise 0.03", SERIES[0], "-", [real3["untrained_noisy"][f"stage{s}"]["lane_correct"] for s in stages]),
        ("real, noise-free", SERIES[0], (0, (4, 2)), [real2["untrained"][f"theta1.5_stage{s}"]["lane_correct"] for s in stages]),
        (f"rewired, noise 0.03 (x{len(ctrl3)})", SERIES[1], "-",
         np.mean([[r["untrained_noisy"][f"stage{s}"]["lane_correct"] for s in stages] for r in ctrl3], 0)),
        (f"rewired, noise-free (x{len(ctrl2)})", SERIES[1], (0, (4, 2)),
         np.mean([[r["untrained"][f"theta1.5_stage{s}"]["lane_correct"] for s in stages] for r in ctrl2], 0)),
    ]
    ends = []
    for label, col, ls, y in series:
        ax.plot(x, y, color=col, ls=ls, lw=2, marker="o", ms=4.5, markeredgecolor=SURFACE,
                markeredgewidth=1.1, solid_capstyle="round")
        ends.append((y[-1], label, col))
    ax.set_xticks(x)
    ax.set_xticklabels(["1\none lane", "2\nsequence", "3\nrandom", "4\nchords", "5\nvaried"], fontsize=8)
    ax.set_ylim(0, 1.05); ax.set_xlim(-0.3, 4.7)
    ax.set_ylabel("fraction of presses in the right lane")
    fig.suptitle("Untrained lane-correctness with and without photoreceptor noise",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "noise-free runs from experiment 2 (different charts); noise 0.03 per receptor per frame",
             fontsize=8, color=INK2)
    _clean(ax)
    _edge_labels(ax, 4, [e[0] for e in ends], [e[1] for e in ends], [e[2] for e in ends], gap_frac=0.08)
    fig.tight_layout(rect=(0, 0, 0.78, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e3_learning.json")) as fh:
        res = json.load(fh)
    fig_learning(res, os.path.join(RESULTS, "fig10_learning3.png"))
    p = os.path.join(RESULTS, "e3_stability.json")
    if os.path.exists(p):
        with open(p) as fh:
            fig_radius(json.load(fh), os.path.join(RESULTS, "fig11_radius.png"))
    p = os.path.join(RESULTS, "e2_play.json")
    if os.path.exists(p):
        with open(p) as fh:
            fig_noisy(res, json.load(fh), os.path.join(RESULTS, "fig12_noisy_untrained.png"))
    print("figures written to", RESULTS)


if __name__ == "__main__":
    main()
