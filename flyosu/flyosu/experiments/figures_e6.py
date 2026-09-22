"""
Figure for experiment 6: what predicts untrained play, and the threshold sweep.

    python -m experiments.figures_e6
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

from experiments.e6_timing import MIN_COUNTED, THETA, THETA_SWEEP  # noqa: E402
from experiments.figures import INK2, MUTED, RESULTS, SERIES, SURFACE  # noqa: E402
from experiments.figures_e2 import _clean  # noqa: E402


def _scatter(ax, x, y, rx, ry, xlabel, note, rho, p):
    ax.plot(x, y, "o", ms=6, color=SERIES[1], markeredgecolor=SURFACE, markeredgewidth=1.2,
            alpha=0.9, zorder=3)
    ax.plot([rx], [ry], "o", ms=9.5, color=SERIES[0], markeredgecolor=SURFACE, markeredgewidth=1.5,
            zorder=4)
    ax.annotate("real", (rx, ry), xytext=(0, -13), textcoords="offset points", ha="center",
                color=SERIES[0], fontsize=8.5, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=9)
    ax.text(0.03, 0.98, note, transform=ax.transAxes, fontsize=8.5, va="top", color=INK2,
            linespacing=1.45)
    ax.text(0.03, 0.80, f"Spearman ρ {rho:+.2f}, p {p:.3f}", transform=ax.transAxes,
            fontsize=8.5, va="top", color=MUTED)
    ax.set_ylim(0, 1.0); _clean(ax); ax.grid(axis="x", visible=True)


def fig_e6(res, path):
    probes = {r["label"]: r for r in res["runs"]}
    beh = {r["label"]: r for r in json.load(open(os.path.join(RESULTS, "e4_covariate.json")))["runs"]}
    ctrl = [l for l in probes if l != "real connectome" and l in beh]
    y = np.array([beh[l]["lane_correct_mean"] for l in ctrl])
    cor = res["correlations"]

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.0))
    band = np.array([probes[l]["shared_threshold"]["shared_band"] for l in ctrl])
    c = cor["shared band (window)"]
    _scatter(axes[0], band, y, probes["real connectome"]["shared_threshold"]["shared_band"],
             beh["real connectome"]["lane_correct_mean"],
             "shared-threshold band (z units)", "real is off the distribution (0/20)\nbut it does not predict play",
             c["spearman_lane"], c["p_lane"])
    axes[0].set_ylabel("untrained lane-correct (experiment 4)")

    spread = np.array([probes[l]["timing"]["peak_lag_spread_ms"] for l in ctrl])
    c = cor["peak lag spread (ms)"]
    _scatter(axes[1], spread, y, probes["real connectome"]["timing"]["peak_lag_spread_ms"],
             beh["real connectome"]["lane_correct_mean"],
             "spread of channel peak times (ms)", "predicts play across graphs\nbut real is unremarkable (4/20)",
             -c["spearman_lane"], c["p_lane"])

    ax = axes[2]
    ts = {r["label"]: r for r in res.get("theta_sweep", [])}
    if ts:
        for l in ctrl:
            if l not in ts:
                continue
            r = ts[l]
            lc = np.array(r["lane_correct"], dtype=float)
            ok = np.array(r["n_counted"]) >= MIN_COUNTED
            ax.plot(THETA_SWEEP, np.where(ok, lc, np.nan), "-", lw=1.1, color=SERIES[1], alpha=0.45)
        r = ts["real connectome"]
        lc = np.array(r["lane_correct"], dtype=float)
        ok = np.array(r["n_counted"]) >= MIN_COUNTED
        ax.plot(THETA_SWEEP, np.where(ok, lc, np.nan), "-o", lw=2.2, ms=6, color=SERIES[0],
                markeredgecolor=SURFACE, markeredgewidth=1.3, zorder=4, label="real connectome")
        ax.axvline(THETA, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=1)
        ax.text(THETA - 0.05, 0.30, "θ = 1.5, as published", fontsize=8, color=MUTED,
                rotation=90, va="center", ha="right")
        s = res.get("theta_sweep_summary", {})
        if s:
            ax.text(0.03, 0.06, f"at θ 1.5:  real {s['real_at_1_5']:.2f} vs {s['ctrl_at_1_5_mean']:.2f}"
                    f"  ({s['n_ge_fixed']}/{s['n']}, p {s['p_fixed']:.3f})\n"
                    f"own best θ: real {s['real_best']:.2f} vs {s['ctrl_best_mean']:.2f}"
                    f"  ({s['n_ge_best']}/{s['n']}, p {s['p_best']:.3f})",
                    transform=ax.transAxes, fontsize=8.5, color=INK2)
    ax.set_xlabel("shared threshold θ", fontsize=9)
    ax.set_ylabel("lane-correct, stage 3", fontsize=9)
    ax.set_ylim(0, 1.0); _clean(ax); ax.grid(axis="y", visible=True)
    ax.text(0.03, 0.97, "giving every network its own best θ\nhalves the gap", transform=ax.transAxes,
            fontsize=8.5, va="top", color=INK2)

    fig.suptitle("What the untrained advantage is made of — and how much of it was the threshold",
                 fontsize=10.5, fontweight="bold", x=0.012, y=0.985, ha="left")
    fig.text(0.012, 0.925, "20 rewired graphs; behaviour from experiment 4. Right: curves drop out where "
             f"fewer than {MIN_COUNTED} presses land near a note, because lane-correct is a ratio.",
             fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.89)); fig.savefig(path, dpi=160); plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e6_timing.json")) as fh:
        res = json.load(fh)
    fig_e6(res, os.path.join(RESULTS, "fig15_timing.png"))
    print("figure written")


if __name__ == "__main__":
    main()
