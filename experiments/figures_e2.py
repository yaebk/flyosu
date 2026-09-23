"""
Figures for experiment 2.  Reads results/e2_play.json, writes PNGs.

    python -m experiments.figures_e2

Uses the same validated palette and style as experiments/figures.py:
real = blue, rewired = orange, shuffled retinotopy = aqua, shuffled channel
labels = violet.  Family identity is always also carried by a text label.
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

FAMILIES = [("real", "real connectome"), ("rewired topology", "rewired topology"),
            ("shuffled retinotopy", "shuffled retinotopy"),
            ("shuffled channel labels", "shuffled channel labels")]
STAGE_NAMES = {1: "one\nlane", 2: "sequence", 3: "random", 4: "chords", 5: "varied\ntempo"}


def _runs(res, fam):
    return [r for r in res["runs"] if r.get("family") == fam]


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", visible=False)


def fig_stability(res, path):
    """Spectral radius at the blank fixed point, real vs each control family."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    e1 = res.get("e1_regime_stability", {}).get("spectral_radius")
    for i, (fam, label) in enumerate(FAMILIES):
        v = np.array([r["stability"]["spectral_radius"] for r in _runs(res, fam)])
        if len(v) == 0:
            continue
        x = i + np.linspace(-0.18, 0.18, len(v)) if len(v) > 1 else [i]
        ax.plot(x, v, "o", ms=7, color=SERIES[i], markeredgecolor=SURFACE,
                markeredgewidth=1.5, zorder=3)
        ax.plot([i - 0.3, i + 0.3], [v.mean()] * 2, color=SERIES[i], lw=2)
        ax.annotate(f"{v.mean():.2f}", (i, v.max()), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK2)
    ax.axhline(1.0, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.annotate("radius 1", (3.45, 1.0), xytext=(0, 4), textcoords="offset points",
                fontsize=8, color=MUTED, ha="right")
    ax.set_xticks(range(4))
    ax.set_xticklabels([l.replace(" ", "\n", 1) for _, l in FAMILIES], fontsize=8.5)
    ax.set_ylabel("spectral radius, blank-field Jacobian")
    ax.set_title("Real wiring amplifies 3x more than degree-matched random wiring")
    sub = "play regime; every network shown has max Re < 1 (stable)"
    if e1:
        sub += f".  Experiment-1 regime, real network: {e1:.1f} (chaotic, off scale)"
    fig.text(0.005, 0.9, sub, fontsize=8, color=INK2)
    _clean(ax); ax.set_ylim(0, 3.8)
    fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def fig_untrained(res, path, theta=None):
    """Untrained accuracy and lane-correctness by curriculum stage, real vs controls."""
    stages = res["stages"]
    theta = res["thetas"][0] if theta is None else theta
    panels = [("accuracy", "osu!mania accuracy"),
              ("lane_correct", "fraction of presses in the right lane")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8), sharey=True)
    for ax, (key, title) in zip(axes, panels):
        ends = []
        for i, (fam, label) in enumerate(FAMILIES):
            rows = _runs(res, fam)
            if not rows:
                continue
            M = np.array([[r["untrained"][f"theta{theta}_stage{s}"][key] for s in stages]
                          for r in rows])
            m, sd = M.mean(0), M.std(0)
            x = np.arange(len(stages))
            ax.plot(x, m, color=SERIES[i], lw=2, marker="o", ms=5, markeredgecolor=SURFACE,
                    markeredgewidth=1.2, solid_capstyle="round")
            if len(rows) > 1:
                ax.fill_between(x, m - sd, m + sd, color=SERIES[i], alpha=0.13, lw=0)
            ends.append((m[-1], label, SERIES[i]))
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels([f"{s}\n{STAGE_NAMES[s]}" for s in stages], fontsize=8)
        ax.set_title(title)
        ax.set_ylim(0, 1.0)
        ax.set_xlim(-0.3, len(stages) - 0.7)
        _clean(ax)
        if ends:
            _edge_labels(ax, len(stages) - 1, [e[0] for e in ends], [e[1] for e in ends],
                         [e[2] for e in ends], gap_frac=0.075)
    axes[0].set_ylabel("untrained fly")
    fig.suptitle(f"Untrained play across the curriculum (anatomical wiring, "
                 f"threshold {theta:g}, no learning)",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "mean +/- sd over 3 control networks per family; the real connectome "
             "is one network.  Lane-correct: right key for the nearest note.",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0, 0.9, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def fig_learning(res, path):
    """Held-out accuracy by episode, real vs rewired, two starts."""
    keys = [("learn_wired", "from the anatomical wiring"), ("learn_blank", "from W = 0")]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), sharey=True)
    for ax, (key, title) in zip(axes, keys):
        ends = []
        xmax = 0
        for i, (fam, label) in enumerate(FAMILIES[:2]):
            rows = [r for r in _runs(res, fam) if key in r]
            for k, r in enumerate(rows):
                ev = r[key]["held_out"]
                x = [e["episode"] for e in ev]; y = [e["accuracy"] for e in ev]
                xmax = max(xmax, max(x))
                ax.plot(x, y, color=SERIES[i], lw=2.2 if fam == "real" else 1.4,
                        alpha=1.0 if fam == "real" else 0.8, marker="o", ms=4,
                        markeredgecolor=SURFACE, markeredgewidth=1, solid_capstyle="round")
                if k == 0:
                    ends.append((y[-1], label + ("" if fam == "real" else f" (x{len(rows)})"),
                                 SERIES[i]))
        ax.set_title(title); ax.set_xlabel("training episodes (2 plays each)")
        ax.set_ylim(0, 1.0); _clean(ax)
        if ends:
            _edge_labels(ax, xmax, [e[0] for e in ends], [e[1] for e in ends],
                         [e[2] for e in ends])
    axes[0].set_ylabel("held-out accuracy (stage 3, 3 charts)")
    fig.suptitle("Learning the 20 readout parameters, connectome frozen",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "reward-modulated perturbation; one line per network",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0, 0.84, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def fig_confusion(res, path):
    """Untrained lane confusion on random charts, real vs a rewired control."""
    theta = res["thetas"][0]
    real = _runs(res, "real")[0]
    ctrl = (_runs(res, "rewired topology") or [None])[0]
    panels = [(real, "real connectome")] + ([(ctrl, "rewired topology #1")] if ctrl else [])
    fig, axes = plt.subplots(1, len(panels), figsize=(3.7 * len(panels), 3.8))
    axes = np.atleast_1d(axes)
    for ax, (r, title) in zip(axes, panels):
        C = np.array(r["untrained"][f"theta{theta}_stage3"]["confusion"], float)
        P = C / np.maximum(C.sum(1, keepdims=True), 1)
        ax.imshow(P, cmap="Blues", vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                if C[i, j]:
                    ax.text(j, i, f"{int(C[i, j])}", ha="center", va="center", fontsize=9,
                            color="white" if P[i, j] > 0.55 else INK2)
        ax.set_xticks(range(4)); ax.set_yticks(range(4))
        ax.set_xticklabels(list("DFJK")); ax.set_yticklabels(list("DFJK"))
        ax.set_xlabel("key pressed"); ax.set_ylabel("lane of the nearest note")
        lc = r["untrained"][f"theta{theta}_stage3"]["lane_correct"]
        ax.set_title(f"{title}\nlane-correct {lc:.2f}", fontsize=9.5)
        ax.grid(False)
    fig.suptitle(f"Which key the untrained fly presses (random lanes, threshold {theta:g})",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e2_play.json")) as fh:
        res = json.load(fh)
    fig_stability(res, os.path.join(RESULTS, "fig6_stability.png"))
    fig_untrained(res, os.path.join(RESULTS, "fig7_untrained.png"))
    fig_confusion(res, os.path.join(RESULTS, "fig8_play_confusion.png"))
    if any("learn_wired" in r for r in res["runs"]):
        fig_learning(res, os.path.join(RESULTS, "fig9_learning.png"))
    print("figures written to", RESULTS)


if __name__ == "__main__":
    main()
