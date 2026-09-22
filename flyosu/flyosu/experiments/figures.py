"""
Figures for experiment 1.  Reads results/e1_sensorimotor.json, writes PNGs.

    python -m experiments.figures
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")

# validated categorical palette (blue / orange / aqua / violet), light surface
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8985"
GRID = "#e6e5e1"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.size": 9,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "legend.frameon": False,
})


def _spread(vals, gap):
    """Nudge label positions apart while keeping their order."""
    order = np.argsort(vals)
    out = np.array(vals, float)
    for k in range(1, len(order)):
        i, j = order[k - 1], order[k]
        if out[j] - out[i] < gap:
            out[j] = out[i] + gap
    return out


def _edge_labels(ax, x, ys, labels, colors, gap_frac=0.085):
    """Right-edge series labels, de-collided vertically."""
    lo, hi = ax.get_ylim()
    pos = _spread(list(ys), (hi - lo) * gap_frac)
    for y1, lab, col in zip(pos, labels, colors):
        ax.annotate(lab, (x, y1), xytext=(8, 0), textcoords="offset points",
                    color=col, fontsize=8.5, fontweight="bold", va="center",
                    annotation_clip=False)


def tidy(ax, top=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(top)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.set_axisbelow(True)


def fig_tuning(res, path):
    """Per-channel azimuth tuning curves, real vs one rewired control."""
    real = next(r for r in res["runs"] if r["family"] == "real")
    ctrl = next((r for r in res["runs"] if r["family"] == "rewired topology"), None)
    panels = [("Real connectome", real)] + ([("Rewired topology (control)", ctrl)]
                                            if ctrl else [])
    fig, axes = plt.subplots(1, len(panels), figsize=(5.4 * len(panels), 3.6),
                             sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (title, run) in zip(axes, panels):
        az = np.array(run["A_tuning"]["azimuths"])
        M = np.array(run["A_tuning"]["channels_centred"]) * 100
        for i, name in enumerate(run["channels"]):
            ax.plot(az, M[:, i], color=SERIES[i], lw=2, solid_capstyle="round")
        _edge_labels(ax, az[-1], M[-1], run["channels"], SERIES)
        lo, hi = ax.get_ylim()
        for lane, key in zip(res["lanes"], res["keys"]):
            ax.axvline(lane, color=MUTED, lw=0.8, ls=(0, (3, 3)), zorder=0)
            ax.annotate(key, (lane, hi), xytext=(0, -2),
                        textcoords="offset points", ha="center", va="top",
                        color=MUTED, fontsize=8)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xlim(az[0] - 3, az[-1] + 26)
        ax.set_ylim(lo, hi)
        ax.set_title(title, loc="left")
        ax.set_xlabel("stimulus azimuth (deg,  + = fly's right)")
        tidy(ax)
    axes[0].set_ylabel("channel activity, centred (% of range)")
    fig.suptitle("Descending-neuron channels are tuned to visual field position",
                 x=0.005, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def fig_decoding(res, path):
    """Lane decoding accuracy by stage, real vs each control family."""
    stages = ["optic lobe", "visual projection", "central brain",
              "descending (population)", "4 pooled channels"]
    fams = ["real", "rewired topology", "shuffled retinotopy",
            "shuffled channel labels"]
    labels = ["Real connectome", "Rewired topology", "Shuffled retinotopy",
              "Shuffled channel labels"]

    data = {}
    for f in fams:
        rows = [r for r in res["runs"] if r.get("family") == f]
        if rows:
            data[f] = {s: np.array([r["B_lanes"][s]["acc"] for r in rows])
                       for s in stages}

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.0),
                                  gridspec_kw={"width_ratios": [1.45, 1]})

    # left: accuracy through the pathway
    x = np.arange(len(stages))
    ends = []
    for i, f in enumerate(fams):
        if f not in data:
            continue
        m = np.array([data[f][s].mean() for s in stages])
        sd = np.array([data[f][s].std() for s in stages])
        ax.plot(x, m, color=SERIES[i], lw=2, marker="o", ms=5,
                markeredgecolor=SURFACE, markeredgewidth=1.4)
        if sd.max() > 0:
            ax.fill_between(x, m - sd, m + sd, color=SERIES[i], alpha=0.13, lw=0)
        ends.append((m[-1], labels[i], SERIES[i]))
    for (yv0, lab, col), yv in zip(ends, _spread([e[0] for e in ends], 0.062)):
        ax.annotate(lab, (x[-1], yv), xytext=(9, 0),
                    textcoords="offset points", color=col, fontsize=8.5,
                    fontweight="bold", va="center", annotation_clip=False)
    ax.axhline(0.25, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.annotate("chance", (0, 0.25), textcoords="offset points", xytext=(2, 4),
                color=MUTED, fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(["optic\nlobe", "visual\nprojection", "central\nbrain",
                        "descending\n(1,303 cells)", "4 pooled\nchannels"])
    ax.set_ylim(0.15, 1.06)
    ax.set_ylabel("lane decoding accuracy")
    ax.set_title("Lane identity survives to the motor output", loc="left")
    ax.set_xlim(-0.3, len(stages) + 0.85)
    tidy(ax)

    # right: the readout that matters, per seed
    key = "4 pooled channels"
    ys, cols, names = [], [], []
    for i, f in enumerate(fams):
        if f not in data:
            continue
        ys.append(data[f][key]); cols.append(SERIES[i]); names.append(labels[i])
    right = max(float(v.max()) for v in ys)
    for i, (v, c) in enumerate(zip(ys, cols)):
        ax2.barh(i, v.mean(), height=0.52, color=c, zorder=2)
        if len(v) > 1:
            ax2.plot(v, np.full(len(v), i), "o", ms=4.0, color=SURFACE,
                     markeredgecolor=c, markeredgewidth=1.2, zorder=3, alpha=0.9)
        ax2.annotate(f"{v.mean():.2f}", (right, i), xytext=(9, 0),
                     textcoords="offset points", va="center", fontsize=8.5,
                     fontweight="bold", color=INK2)
    ax2.axvline(0.25, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
    ax2.set_yticks(range(len(names)))
    ax2.set_yticklabels(names, fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlim(0, min(1.0, right + 0.16))
    ax2.set_xlabel("lane decoding accuracy, four pooled channels")
    ax2.set_title("Reading through anatomical channels", loc="left")
    ax2.grid(axis="y", visible=False)
    tidy(ax2)

    fig.suptitle("Real connectome vs. three matched controls",
                 x=0.005, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def fig_approach(res, path):
    """Channel activity as a note descends toward the judgment line."""
    real = next(r for r in res["runs"] if r["family"] == "real")
    a = real["C_approach"]
    el = np.array(a["elevations"])
    M = np.array(a["channels_centred"]) * 100
    if not a.get("warmed"):      # first sample is a cold-start transient
        el, M = el[1:], M[1:] - M[1:].mean(0)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    rho = [float(np.corrcoef(el, M[:, i])[0, 1]) for i in range(4)]
    for i, name in enumerate(real["channels"]):
        ax.plot(el, M[:, i], color=SERIES[i], lw=2, solid_capstyle="round")
    lab = [f"{n}  r={v:+.2f}" for n, v in zip(real["channels"], rho)]
    _edge_labels(ax, el[-1], M[-1], lab, SERIES)
    ax.axvline(res["el_judge"], color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.annotate("judgment line", (res["el_judge"], ax.get_ylim()[0]),
                xytext=(-5, 4), textcoords="offset points", color=MUTED,
                fontsize=8, va="bottom", ha="right")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.invert_xaxis()
    ax.set_xlabel("note elevation (deg)   -- note descends left to right -->")
    ax.set_ylabel("channel activity, centred (% of range)")
    ax.set_title(f"A note falling in lane {a['lane']:+.0f}deg", loc="left")
    ax.set_xlim(el[0] + 3, el[-1] - 26)
    tidy(ax)
    fig.suptitle("The output carries when the note arrives, not just where",
                 x=0.005, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def fig_confusion(res, path):
    """Confusion matrix of the untrained argmax policy, real vs control."""
    real = next(r for r in res["runs"] if r["family"] == "real")
    ctrl = next((r for r in res["runs"] if r["family"] == "rewired topology"), None)
    panels = [("Real connectome", real)] + ([("Rewired topology", ctrl)]
                                            if ctrl else [])
    fig, axes = plt.subplots(1, len(panels), figsize=(4.1 * len(panels), 3.7))
    axes = np.atleast_1d(axes)
    for ax, (title, run) in zip(axes, panels):
        ap = run["B_lanes"]["argmax_policy"]
        conf = np.array(ap["confusion"], float)
        order = [run["channels"].index(c) for c in ap["channel_for_lane"]]
        conf = conf[:, order]
        conf = conf / conf.sum(1, keepdims=True)
        im = ax.imshow(conf, cmap="Blues", vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                ax.text(j, i, f"{conf[i, j]:.2f}", ha="center", va="center",
                        fontsize=9,
                        color="#ffffff" if conf[i, j] > 0.55 else INK2)
        ax.set_xticks(range(4)); ax.set_yticks(range(4))
        ax.set_xticklabels(ap["channel_for_lane"], fontsize=8.5)
        ax.set_yticklabels([f"lane {k}" for k in res["keys"]], fontsize=8.5)
        ax.set_xlabel("channel that fired most")
        ax.set_title(f"{title}   acc {ap['accuracy']:.2f}", loc="left")
        ax.grid(False)
    axes[0].set_ylabel("lane stimulated")
    fig.suptitle("No learning: just press the key of the loudest channel",
                 x=0.005, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def fig_controls(res, path):
    """Every metric, real against each control family's distribution."""
    metrics = [
        ("argmax policy", lambda r: r["B_lanes"]["argmax_policy"]["accuracy"],
         "untrained policy accuracy"),
        ("max channel modulation",
         lambda r: max(r["A_tuning"]["modulation_depth"]),
         "channel modulation depth"),
        ("note-approach signal",
         lambda r: r["C_approach"]["max_abs_correlation"],
         "note-approach signal  |r|"),
        ("4 pooled channels",
         lambda r: r["B_lanes"]["4 pooled channels"]["acc"],
         "trained decoder accuracy"),
    ]
    fams = ["rewired topology", "shuffled retinotopy", "shuffled channel labels"]
    short = ["rewired\ntopology", "shuffled\nretinotopy", "shuffled\nchannel labels"]

    fig, axes = plt.subplots(1, len(metrics), figsize=(3.35 * len(metrics), 3.9))
    rng = np.random.default_rng(0)
    for ax, (key, fn, title) in zip(axes, metrics):
        real = fn(next(r for r in res["runs"] if r["family"] == "real"))
        counts = []
        for i, f in enumerate(fams):
            v = np.array([fn(r) for r in res["runs"] if r.get("family") == f])
            if not len(v):
                continue
            jitter = rng.uniform(-0.13, 0.13, len(v))
            ax.plot(np.full(len(v), i) + jitter, v, "o", ms=5,
                    color=SURFACE, markeredgecolor=SERIES[i + 1],
                    markeredgewidth=1.4, zorder=2)
            ax.plot([i - 0.28, i + 0.28], [v.mean()] * 2, color=SERIES[i + 1],
                    lw=2.5, solid_capstyle="round", zorder=3)
            counts.append((i, f"{int((v >= real).sum())}/{len(v)}"))
        ax.axhline(real, color=SERIES[0], lw=2, zorder=4)
        # headroom so the per-family counts sit clear of the data
        lo, hi = ax.get_ylim()
        pad = (hi - lo) * 0.13
        ax.set_ylim(lo - pad, hi)
        for i, txt in counts:
            ax.annotate(txt, (i, lo - pad * 0.55), ha="center", va="center",
                        fontsize=8, color=MUTED)
        ax.annotate(f"real  {real:.2f}", (-0.5, real), xytext=(3, 5),
                    textcoords="offset points", ha="left",
                    color=SERIES[0], fontsize=8.5, fontweight="bold")
        ax.set_xticks(range(len(fams)))
        ax.set_xticklabels(short, fontsize=8)
        ax.set_xlim(-0.55, len(fams) - 0.45)
        ax.set_title(title, loc="left", fontsize=9.5)
        ax.grid(axis="x", visible=False)
        tidy(ax)
    axes[0].set_ylabel("score")
    fig.suptitle("Where the real wiring matters -- and where a trained decoder "
                 "erases the difference",
                 x=0.005, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.005, 0.895, "each dot is one randomised network (15 per family); "
             "bar = family mean; fraction = controls reaching the real network",
             fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main():
    with open(os.path.join(RESULTS, "e1_sensorimotor.json")) as fh:
        res = json.load(fh)
    jobs = [("fig1_tuning.png", fig_tuning),
            ("fig2_decoding.png", fig_decoding),
            ("fig3_approach.png", fig_approach),
            ("fig4_confusion.png", fig_confusion),
            ("fig5_controls.png", fig_controls)]
    for name, fn in jobs:
        p = os.path.join(RESULTS, name)
        fn(res, p)
        print("wrote", p)


if __name__ == "__main__":
    main()


