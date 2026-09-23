"""
Figure for experiment 7: a better wiring rule, and what it does to the gap.

    python -m experiments.figures_e7
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

from experiments.figures import INK2, MUTED, RESULTS, SERIES, SURFACE  # noqa: E402
from experiments.figures_e2 import _clean  # noqa: E402


def _paired(ax, a, b, ra, rb, ylabel, title):
    for u, v in zip(a, b):
        ax.plot([0, 1], [u, v], "-", lw=1.0, color=SERIES[1], alpha=0.45, zorder=2)
    ax.plot(np.zeros(len(a)), a, "o", ms=5, color=SERIES[1], alpha=0.75, markeredgewidth=0, zorder=3)
    ax.plot(np.ones(len(b)), b, "o", ms=5, color=SERIES[1], alpha=0.75, markeredgewidth=0, zorder=3)
    ax.plot([0, 1], [ra, rb], "-o", lw=2.4, ms=8.5, color=SERIES[0], markeredgecolor=SURFACE,
            markeredgewidth=1.4, zorder=5, label="real connectome")
    ax.plot([-0.18, 0.18], [np.mean(a)] * 2, lw=2.4, color=SERIES[1], zorder=4)
    ax.plot([0.82, 1.18], [np.mean(b)] * 2, lw=2.4, color=SERIES[1], zorder=4,
            label="rewired ×20 (mean)")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["margin rule\n(as published)", "band rule\n(new)"],
                                              fontsize=8.5)
    ax.set_xlim(-0.35, 1.35); ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=9.5, loc="left", color=INK2)
    _clean(ax); ax.grid(axis="y", visible=True)


def fig_e7(res, path):
    runs = {r["label"]: r for r in res["runs"]}
    real = runs["real connectome"]
    ctrl = [r for k, r in runs.items() if k != "real connectome"]
    e6 = {r["label"]: r for r in json.load(open(os.path.join(RESULTS, "e6_timing.json")))["theta_sweep"]}

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.1))

    mb = np.array([r["margin_band"] for r in ctrl]); bb = np.array([r["band_band"] for r in ctrl])
    _paired(axes[0], mb, bb, real["margin_band"], real["band_band"],
            "shared-threshold band (z units)", "the quantity the new rule optimises")
    axes[0].text(0.03, 0.97, f"controls reaching real:\n{(mb >= real['margin_band']).sum()}/20  →  "
                 f"{(bb >= real['band_band']).sum()}/20", transform=axes[0].transAxes,
                 fontsize=8.5, va="top", color=INK2, linespacing=1.45)

    for ax, key, lbl, title in ((axes[1], "best_lane_correct", "lane-correct, own best θ",
                                 "lane-correct (stage 3)"),
                                (axes[2], "best_accuracy", "accuracy, own best θ",
                                 "osu!mania accuracy (stage 3)")):
        a = np.array([e6[r["label"]][key] for r in ctrl])
        b = np.array([r["band"][key] for r in ctrl])
        ra, rb = e6["real connectome"][key], real["band"][key]
        _paired(ax, a, b, ra, rb, lbl, title)
        ax.text(0.03, 0.97, f"controls reaching real:\n{(a >= ra).sum()}/20  →  {(b >= rb).sum()}/20",
                transform=ax.transAxes, fontsize=8.5, va="top", color=INK2, linespacing=1.45)
        ax.set_ylim(0, None)
    axes[2].legend(loc="lower right", fontsize=8, frameon=False)

    fig.suptitle("Fix the wiring rule and the controls catch up — the real network was already at its best",
                 fontsize=10.5, fontweight="bold", x=0.012, y=0.985, ha="left")
    fig.text(0.012, 0.925, "every network also given its own best threshold (experiment 6's fair protocol); "
             "the two rules disagree on 15 of 21 networks, but not on the real one",
             fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.89)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e7_wiring.json")) as fh:
        res = json.load(fh)
    fig_e7(res, os.path.join(RESULTS, "fig16_wiring.png"))
    print("figure written")


if __name__ == "__main__":
    main()
