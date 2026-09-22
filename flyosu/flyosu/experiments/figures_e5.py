"""
Figure for experiment 5: the real-vs-control gap as a function of readout capacity.

    python -m experiments.figures_e5
    DATASET=malecns python -m experiments.figures_e5
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

from experiments.e5_reservoir import FAMILIES, READOUTS  # noqa: E402
from experiments.figures import INK2, MUTED, RESULTS, SERIES, SURFACE  # noqa: E402
from experiments.figures_e2 import _clean  # noqa: E402

DATASET = os.environ.get("DATASET", "flywire")
SUFFIX = "" if DATASET == "flywire" else f"_{DATASET}"


def fig_capacity(res, path):
    runs = res["runs"]
    real = next(r for r in runs if r["label"] == "real connectome")
    names = [n for n in READOUTS if n in real["readouts"]]
    x = np.arange(len(names))
    fams = [(fam, key) for key, (fam, _) in FAMILIES.items()
            if any(r["label"].startswith(fam) for r in runs)]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharey=True)
    for ax, metric, title in zip(axes, ("held_out", "transfer"),
                                 ("held-out stage 3 (fitted on stage 3)", "stage 4 with chords, no refit")):
        width = 0.8 / (len(fams) + 1)
        for j, (fam, key) in enumerate(fams):
            for i, name in enumerate(names):
                ctrl = [r for r in runs if r["label"].startswith(fam) and name in r["readouts"]]
                if not ctrl:
                    continue
                v = np.array([r["readouts"][name][metric]["accuracy"] for r in ctrl])
                xx = x[i] - 0.4 + width * (j + 1)
                ax.plot(np.full(len(v), xx) + np.random.default_rng(i).uniform(-width / 4, width / 4, len(v)),
                        v, "o", ms=4, color=SERIES[j + 1], alpha=0.55, markeredgewidth=0, zorder=2)
                ax.plot([xx - width / 2.5, xx + width / 2.5], [v.mean(), v.mean()], color=SERIES[j + 1],
                        lw=2.2, zorder=3, label=f"{fam} (n={len(v)})" if i == 0 else None)
        rv = [real["readouts"][n][metric]["accuracy"] for n in names]
        ax.plot(x, rv, "-", color=SERIES[0], lw=1.2, alpha=0.5, zorder=3)
        ax.plot(x, rv, "o", ms=9, color=SERIES[0], markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4,
                label="real connectome")
        for i, name in enumerate(names):
            ctrl = [r for r in runs if r["label"].startswith("rewired") and name in r["readouts"]]
            if ctrl and metric == "held_out":
                v = np.array([r["readouts"][name][metric]["accuracy"] for r in ctrl])
                n_ge = int((v >= rv[i]).sum())
                ax.text(x[i], 1.03, f"{n_ge}/{len(v)}", ha="center", fontsize=7.5, color=INK2)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{n}\n{real['readouts'][n]['n_params']} params" for n in names], fontsize=8.5)
        ax.set_ylim(0, 1.08); ax.set_title(title, fontsize=9.5, loc="left", color=INK2)
        _clean(ax); ax.grid(axis="y", visible=True)
    axes[0].set_ylabel("osu!mania accuracy, ridge-fitted readout")
    axes[0].legend(loc="lower right", fontsize=8, frameon=False)
    fig.suptitle(f"How much of the gap survives a bigger readout?  ({res['dataset']})",
                 fontsize=10.5, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.9, "one recording per network; every readout label-free and fitted identically; "
             "numbers above: rewired graphs reaching the real network", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, f"e5_reservoir{SUFFIX}.json")) as fh:
        res = json.load(fh)
    fig_capacity(res, os.path.join(RESULTS, f"fig14_capacity{SUFFIX}.png"))
    print("figure written")


if __name__ == "__main__":
    main()
