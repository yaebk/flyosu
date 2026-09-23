"""
Experiment 18 -- capability: make the fly play harder charts.

**This is engineering, not a comparison.**  It uses the real connectome only,
runs no controls, and claims no p-values.  Tuning a readout to play better is
not a protocol violation because nothing here is being tested against a null;
keep it that way, and do not let any number from this file leak into a
registered comparison.

Experiment 5 produced the best fly so far: a `pca16` ridge readout, 68
parameters, connectome frozen, **0.917** on held-out stage-3 charts at 600 ms.
It was fitted on four stage-3 charts at 600 ms and then played everywhere else
without refitting, and that is where it falls over:

    stage 3 @ 600 ms  0.917      the condition it was fitted on
    stage 5 varied    0.608      rhythm it never saw
    stage 4 chords    0.506      chords it never saw
    stage 4 @ 400 ms  0.286      "chord density, not lane identity, is the wall"

Every one of those is a *transfer* number.  `docs/RESULTS_E5.md` named the
obvious follow-up -- "fit on stage 4 and see" -- and nobody ran it.  So the
question here is how much of the wall is the network's capacity and how much is
simply that the readout was only ever shown one kind of chart.

**Arms.**  Four training compositions, each 8 charts x 24 notes, same seed, same
`pca16` features, same solver.  The only thing that varies is what the readout
is shown while being fitted:

    s3_600      stage 3 @ 600           experiment 5's diet, with twice the data
    s4_600      stage 4 @ 600           chords only -- the flagged follow-up
    mixed       3@600, 4@600, 5@600, 3@450   a bit of everything
    mixed_fast  3@600, 4@600, 4@400, 3@450   everything, weighted toward density

**Test battery.**  Held-out charts nobody was fitted on, three per condition at
20 notes, seed 999 -- stage 3 @ 600 and @ 450, stage 4 @ 600 and @ 400, stage 5
@ 600.  The same battery for every arm, so the rows are comparable.

The `s3_600` arm exists to separate "more data helped" from "more *varied* data
helped".  Experiment 5's own 0.917 came from four charts; this arm gets eight of
the same kind, so if it moves, the extra frames are doing it.

    ARM=mixed python -m experiments.e18_capability
    python -m experiments.e18_capability report
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e18_capability.json")

THETA = 1.5
NOISE = 0.03
READOUT_K = 16                       # pca16, experiment 5's best
N_CHARTS = 8
N_NOTES = 24
TRAIN_SEED = 100

ARMS = {
    "s3_600":     ((3, 600.0),),
    "s4_600":     ((4, 600.0),),
    "mixed":      ((3, 600.0), (4, 600.0), (5, 600.0), (3, 450.0)),
    "mixed_fast": ((3, 600.0), (4, 600.0), (4, 400.0), (3, 450.0)),
}

# Held-out battery: the conditions experiment 5 measured, plus a denser
# single-note one.  Same seeds for every arm.
BATTERY = {
    "s3_600": dict(stage=3, interval_ms=600.0),
    "s3_450": dict(stage=3, interval_ms=450.0),
    "s4_600": dict(stage=4, interval_ms=600.0),
    "s4_400": dict(stage=4, interval_ms=400.0),
    "s5_600": dict(stage=5, interval_ms=600.0),
}
BATTERY_KW = dict(n_charts=3, n_notes=20, seed=999)

# What experiment 5's readout scored on the same conditions, for reference.
E5_REFERENCE = {"s3_600": 0.917, "s4_600": 0.506, "s4_400": 0.286, "s5_600": 0.608}


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def run_arm(arm: str) -> dict:
    specs = ARMS[arm]
    t0 = time.time()
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    states = calibration_states(fly, player.r0)
    rr = R.RidgeReadout(player, n_charts=N_CHARTS, n_notes=N_NOTES,
                        seed=TRAIN_SEED, chart_specs=specs)
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=READOUT_K, states=states)
    print(f"[{arm}] recording {N_CHARTS} charts: "
          + ", ".join(f"s{s}@{i:.0f}" for s, i in specs), flush=True)
    rr.record()
    d = rr.solve()
    out = {"arm": arm, "specs": [list(s) for s in specs], "n_params": d["n_params"],
           "train_reward": d["train_reward"], "frames": d["frames"],
           "lanes": d["lanes"], "battery": {}}
    for name, cond in BATTERY.items():
        e = L.evaluate(player, **cond, **BATTERY_KW)
        n_c = int(np.array(e["confusion"]).sum())
        out["battery"][name] = {
            "accuracy": float(e["accuracy"]), "hit_rate": float(e["hit_rate"]),
            "stray_per_note": float(e["stray_per_note"]),
            "lane_correct": (float(e["lane_correct"]) if n_c >= 20 else None),
            "reward": float(e["accuracy"] - L.STRAY_PENALTY * e["stray_per_note"])}
        b = out["battery"][name]
        ref = E5_REFERENCE.get(name)
        print(f"  [{arm}] {name:<8s} acc {b['accuracy']:.3f}"
              + (f" (e5 {ref:.3f}, {b['accuracy'] - ref:+.3f})" if ref else "")
              + f"  hit {b['hit_rate']:.2f}  stray {b['stray_per_note']:.2f}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    arm = os.environ.get("ARM")
    if arm not in ARMS:
        raise SystemExit(f"set ARM to one of: {', '.join(ARMS)}")
    path = PATH[:-5] + f"_{arm}.json"
    with open(path, "w") as fh:
        json.dump(run_arm(arm), fh, indent=1)
    print(f"wrote {os.path.basename(path)}", flush=True)


def report():
    runs = {}
    for f in sorted(glob.glob(PATH[:-5] + "_*.json")):
        r = _load(f, None)
        if r:
            runs[r["arm"]] = r
    if not runs:
        print("no arms finished yet"); return
    order = [a for a in ARMS if a in runs]
    print("\n=== experiment 18: capability, real connectome, pca16 ===")
    print(f"  {N_CHARTS} training charts x {N_NOTES} notes per arm; battery is "
          f"{BATTERY_KW['n_charts']} held-out charts x {BATTERY_KW['n_notes']} notes")
    head = f"  {'condition':<10s}" + "".join(f"{a:>12s}" for a in order) + f"{'e5':>9s}"
    print("\n  ACCURACY\n" + head)
    for name in BATTERY:
        row = f"  {name:<10s}"
        best = max(runs[a]["battery"][name]["accuracy"] for a in order)
        for a in order:
            v = runs[a]["battery"][name]["accuracy"]
            row += f"{('*' if v == best else ' ') + format(v, '.3f'):>12s}"
        ref = E5_REFERENCE.get(name)
        row += f"{format(ref, '.3f') if ref else '-':>9s}"
        print(row)
    print("\n  HIT RATE\n" + head[:-9])
    for name in BATTERY:
        print(f"  {name:<10s}" + "".join(
            f"{runs[a]['battery'][name]['hit_rate']:>12.3f}" for a in order))
    print("\n  STRAYS PER NOTE\n" + head[:-9])
    for name in BATTERY:
        print(f"  {name:<10s}" + "".join(
            f"{runs[a]['battery'][name]['stray_per_note']:>12.3f}" for a in order))
    print("\n  mean accuracy over the battery")
    for a in order:
        m = float(np.mean([runs[a]["battery"][n]["accuracy"] for n in BATTERY]))
        print(f"    {a:<12s} {m:.3f}   ({runs[a]['seconds']:.0f}s, "
              f"{runs[a]['n_params']} params)")
    with open(PATH, "w") as fh:
        json.dump({"arms": runs, "battery": BATTERY, "e5_reference": E5_REFERENCE}, fh, indent=1)


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "") == "report":
        report()
    else:
        main()
