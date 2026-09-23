"""
Experiment 5 -- the supervised ceiling, as a function of readout capacity.

Experiments 2-4 trained the 20-parameter readout by reward-modulated
perturbation, which costs about an hour per network and left every comparison
short of controls.  ``reservoir.py`` fits the same readout in closed form from
one recording per network.  This experiment uses that to ask the question
experiment 1 raised and nothing since could afford to answer with numbers: how
does the gap between the real connectome and its controls depend on how much
the readout is allowed to do?

Per network, one recording of the descending population during four stage-3
charts, then four readouts fitted from it:

    channels   the four anatomical channels, normalised      4 x 4 + 4 = 20
    pca4       top-4 PCs of the population, calibration set  4 x 4 + 4 = 20
    pca8       top-8                                         4 x 8 + 4 = 36
    pca16      top-16                                        4 x 16 + 4 = 68

``channels`` and ``pca4`` have the same parameter count, so their difference is
what the anatomical grouping is worth against a data-driven one of the same
size.  Each readout is evaluated on three held-out stage-3 charts (the same
seeds as experiment 3) and, without refitting, on two stage-4 charts (chords).

Controls: rewired topology (the direct test), shuffled retinotopy (same graph,
scrambled input map), and shuffled channel labels (same network, descending
neurons regrouped at random -- only the ``channels`` readout can see it, so only
that readout is fitted for this family).  Everything is identical across
networks: charts, seeds, feature-fitting ensemble, controller, parameter
counts.

    N_CTRL=10 python -m experiments.e5_reservoir
    DATASET=malecns N_CTRL=4 FAMILIES=rewired python -m experiments.e5_reservoir
    python -m experiments.e5_reservoir report
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DATASET = os.environ.get("DATASET", "flywire")
PATH = os.path.join(RESULTS, "e5_reservoir" + ("" if DATASET == "flywire" else f"_{DATASET}") + ".json")

FAMILIES = {"rewired": ("rewired topology", "shuffle_seed"),
            "retino": ("shuffled retinotopy", "retino_seed"),
            "channels": ("shuffled channel labels", "channel_seed")}
READOUTS = ("channels", "pca4", "pca8", "pca16")
THETA = 1.5
NOISE = 0.03
TRAIN = dict(stage=3, n_charts=4, n_notes=24, interval_ms=600.0, seed=100)
HELD_OUT = dict(stage=3, n_charts=3, n_notes=20, interval_ms=600.0, seed=999)
TRANSFER = dict(stage=4, n_charts=2, n_notes=20, interval_ms=600.0, seed=2999)


def measure(label, kw, readouts):
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    out = {"label": label, "dataset": DATASET, "stability": fly.stability(), "readouts": {}}
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    states = calibration_states(fly, player.r0)
    rr = R.RidgeReadout(player, **TRAIN)
    rr.record()
    out["seconds_record"] = round(time.time() - t0, 1)
    out["frames"] = int(sum(len(r.t) for r in rr.recordings))
    for name in readouts:
        rr.features = (None if name == "channels" else
                       R.PopulationProjection.fit(fly, player.r0, k=int(name[3:]), states=states))
        d = rr.solve()
        d["held_out"] = L.evaluate(player, **HELD_OUT)
        d["transfer"] = L.evaluate(player, **TRANSFER)
        if rr.features is not None:
            d["explained"] = rr.features.explained.tolist()
        out["readouts"][name] = d
        h, tr = d["held_out"], d["transfer"]
        print(f"  {label:<26s} {name:<8s} {d['n_params']:>3d} params  train {d['train_reward']:.2f}  "
              f"held-out acc {h['accuracy']:.3f} hit {h['hit_rate']:.2f} lane {h['lane_correct']:.2f}  "
              f"stage-4 acc {tr['accuracy']:.3f}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<26s} radius {out['stability']['spectral_radius']:.2f}  ({out['seconds']:.0f}s)", flush=True)
    return out


def main():
    n = int(os.environ.get("N_CTRL", 10))
    fams = [f.strip() for f in os.environ.get("FAMILIES", "rewired,retino,channels").split(",")]
    results = {"dataset": DATASET, "train": TRAIN, "held_out": HELD_OUT, "transfer": TRANSFER,
               "theta": THETA, "noise": NOISE, "runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", {}, READOUTS)]
    for f in fams:
        fam, kwarg = FAMILIES[f]
        for s in range(1, n + 1):
            plan.append((f"{fam} #{s}", {kwarg: s}, ("channels",) if f == "channels" else READOUTS))
    for label, kw, readouts in plan:
        if label in done:
            continue
        results["runs"].append(measure(label, kw, readouts))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report(results)


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def report(results):
    runs = results["runs"]
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    if real is None:
        return
    print(f"\n=== experiment 5, {results['dataset']}: supervised ceiling vs readout capacity ===")
    summary = {}
    for name in READOUTS:
        if name not in real["readouts"]:
            continue
        rd = real["readouts"][name]
        print(f"\n{name} ({rd['n_params']} params)   real: held-out acc {rd['held_out']['accuracy']:.3f}  "
              f"lane {rd['held_out']['lane_correct']:.2f}  stage-4 {rd['transfer']['accuracy']:.3f}")
        summary[name] = {"real": rd["held_out"]["accuracy"], "families": {}}
        for fam, _ in FAMILIES.values():
            ctrl = [r for r in runs if r["label"].startswith(fam) and name in r["readouts"]]
            if not ctrl:
                continue
            acc = np.array([r["readouts"][name]["held_out"]["accuracy"] for r in ctrl])
            lane = np.array([r["readouts"][name]["held_out"]["lane_correct"] for r in ctrl])
            tr = np.array([r["readouts"][name]["transfer"]["accuracy"] for r in ctrl])
            n_ge = int((acc >= rd["held_out"]["accuracy"]).sum())
            print(f"   {fam:<26s} n={len(ctrl):<2d} acc {acc.mean():.3f} +- {acc.std():.3f}  "
                  f"lane {lane.mean():.2f}  stage-4 {tr.mean():.3f}   "
                  f"{n_ge}/{len(ctrl)} reach real  p {_p(n_ge, len(ctrl)):.3f}")
            summary[name]["families"][fam] = {"n": len(ctrl), "acc_mean": float(acc.mean()),
                                              "acc_sd": float(acc.std()), "lane_mean": float(lane.mean()),
                                              "transfer_mean": float(tr.mean()), "n_ge": n_ge,
                                              "p": _p(n_ge, len(ctrl))}
    results["summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    else:
        main()
