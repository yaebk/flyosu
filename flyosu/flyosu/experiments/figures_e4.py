"""
Figure for experiment 4: spectral radius vs untrained behaviour across rewired graphs.

    python -m experiments.figures_e4
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

from experiments.figures import INK2, RESULTS, SERIES, SURFACE  # noqa: E402
from experiments.figures_e2 import _clean  # noqa: E402


def fig_covariate(res, path):
    ctrl = [r for r in res["runs"] if r["label"] != "real connectome"]
    real = next(r for r in res["runs"] if r["label"] == "real connectome")
    cors = res.get("correlations", {})
    panels = [("spectral_radius", "spectral radius, blank-field Jacobian", "radius vs lane-correct"),
              ("max_real", "max Re of the leading eigenvalue", None)]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7), sharey=True)
    for ax, (key, xlabel, ckey) in zip(axes, panels):
        x = np.array([r["stability"][key] for r in ctrl])
        y = np.array([r["lane_correct_mean"] for r in ctrl])
        ax.plot(x, y, "o", ms=6.5, color=SERIES[1], markeredgecolor=SURFACE, markeredgewidth=1.3,
                alpha=0.9, zorder=3)
        ax.plot([real["stability"][key]], [real["lane_correct_mean"]], "o", ms=9, color=SERIES[0],
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
        ax.annotate("real connectome", (real["stability"][key], real["lane_correct_mean"]),
                    xytext=(-8, 0), textcoords="offset points", ha="right", va="center",
                    color=SERIES[0], fontsize=8.5, fontweight="bold")
        ax.text(0.03, 0.95, f"{len(ctrl)} rewired graphs", transform=ax.transAxes, fontsize=8.5,
                color=SERIES[1], fontweight="bold", va="top")
        if ckey and ckey in cors:
            c = cors[ckey]
            ax.text(0.03, 0.87, f"Spearman ρ {c['spearman']:+.2f}, p {c['p']:.2f} (rewired only)",
                    transform=ax.transAxes, fontsize=8.5, color=INK2, va="top")
        ax.set_xlabel(xlabel); ax.set_ylim(0, 1.0)
        _clean(ax); ax.grid(axis="x", visible=True)
    axes[0].set_ylabel("untrained lane-correct (stages 2-4, noise 0.03)")
    fig.suptitle("Recurrent gain does not predict lane choice across random graphs",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    n_ge = int(sum(r["lane_correct_mean"] >= real["lane_correct_mean"] for r in ctrl))
    fig.text(0.02, 0.9, f"the real connectome is off both distributions; {n_ge}/{len(ctrl)} rewired graphs "
             f"reach its lane-correctness (p = {(n_ge + 1) / (len(ctrl) + 1):.3f})", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e4_covariate.json")) as fh:
        res = json.load(fh)
    fig_covariate(res, os.path.join(RESULTS, "fig13_covariate.png"))
    print("figure written")


if __name__ == "__main__":
    main()
