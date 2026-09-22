"""
Experiment 4 -- does recurrent gain predict behaviour across random graphs?

The real connectome has a blank-field spectral radius of 2.3 and rewired
networks sit at 0.8 +- 0.2; the real network also presses the right key far
more often untrained.  Two separate facts so far.  This asks whether they are
one: across many rewired graphs, does a network's spectral radius predict its
untrained lane-correctness?  If it does, "recurrent gain" is a candidate for
*what* about the real wiring helps; if it does not, the two properties are
independent and the wiring's contribution is elsewhere (e.g. in the
lane-to-descending-group mapping).

Per rewired seed: stability (radius, max Re, fixed point), the untrained
anatomical wiring's lane-response matrix, and noisy untrained play on stages
2-4 (two 20-note charts each).  The real connectome is measured the same way.

    N_SEEDS=20 python -m experiments.e4_covariate
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P  # noqa: E402
from flyosu.controller import lane_response_matrix  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e4_covariate.json")
STAGES = (2, 3, 4)
THETA = 1.5
NOISE = 0.03


def measure(label, kw):
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    out = {"label": label, "stability": fly.stability()}
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    Z = lane_response_matrix(fly, player.norm, player.r0)
    out["lane_response"] = Z.tolist()
    # how separable the four lanes are at the channel level, before any threshold:
    # the margin between each lane's wired channel and the best other channel
    W = player.controller.W
    wired = np.array([Z[l, int(np.argmax(W[l]))] for l in range(4)])
    others = np.array([np.max(np.delete(Z[l], int(np.argmax(W[l])))) for l in range(4)])
    out["wired_margin"] = float(np.mean(wired - others))
    out["untrained"] = {}
    for s in STAGES:
        out["untrained"][f"stage{s}"] = L.evaluate(player, stage=s, n_charts=2, n_notes=20,
                                                   interval_ms=600.0, seed=7000 + 10 * s)
    lc = np.mean([out["untrained"][f"stage{s}"]["lane_correct"] for s in STAGES])
    acc = np.mean([out["untrained"][f"stage{s}"]["accuracy"] for s in STAGES])
    out["lane_correct_mean"] = float(lc)
    out["accuracy_mean"] = float(acc)
    out["seconds"] = round(time.time() - t0, 1)
    st = out["stability"]
    print(f"  {label:<24s} radius {st['spectral_radius']:.2f}  Re {st['max_real']:+.2f}  "
          f"fixed {str(st['fixed_point']):<5s} margin {out['wired_margin']:+.2f}  "
          f"lane-correct {lc:.2f}  acc {acc:.3f}  ({out['seconds']:.0f}s)", flush=True)
    return out


def main():
    n = int(os.environ.get("N_SEEDS", 20))
    results = {"stages": STAGES, "theta": THETA, "noise": NOISE, "runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done:
            continue
        results["runs"].append(measure(label, kw))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report(results)


def report(results):
    ctrl = [r for r in results["runs"] if r["label"] != "real connectome"]
    real = next((r for r in results["runs"] if r["label"] == "real connectome"), None)
    if len(ctrl) < 3:
        return
    rad = np.array([r["stability"]["spectral_radius"] for r in ctrl])
    lc = np.array([r["lane_correct_mean"] for r in ctrl])
    acc = np.array([r["accuracy_mean"] for r in ctrl])
    mg = np.array([r["wired_margin"] for r in ctrl])
    from scipy.stats import spearmanr
    print(f"\n--- {len(ctrl)} rewired networks ---")
    print(f"  radius        {rad.mean():.2f} +- {rad.std():.2f}   [{rad.min():.2f}, {rad.max():.2f}]")
    print(f"  lane-correct  {lc.mean():.2f} +- {lc.std():.2f}")
    print(f"  wired margin  {mg.mean():+.2f} +- {mg.std():.2f}")
    out = {}
    for name, x, y in (("radius vs lane-correct", rad, lc), ("radius vs accuracy", rad, acc),
                       ("margin vs lane-correct", mg, lc), ("radius vs margin", rad, mg)):
        rho, p = spearmanr(x, y)
        out[name] = {"spearman": float(rho), "p": float(p), "n": int(len(x))}
        print(f"  {name:<24s} Spearman rho {rho:+.2f}  p {p:.3f}")
    if real:
        print(f"  real: radius {real['stability']['spectral_radius']:.2f}  margin {real['wired_margin']:+.2f}  "
              f"lane-correct {real['lane_correct_mean']:.2f}  -- {int((lc >= real['lane_correct_mean']).sum())}/"
              f"{len(lc)} rewired reach it")
    results["correlations"] = out
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    else:
        main()
