"""
Experiment 3 -- learning, scaled up and fixed.

Experiment 2's part B was one real network against two rewired controls with
an un-annealed learner and unrecorded seeds.  This runs the same comparison
properly, on the direct control for "does the topology matter" (rewired
topology), with:

  * an annealed learning rate (lr_decay 0.97 per episode),
  * recorded seeds for every learner,
  * three conditions per network:
      wired        start from the anatomical wiring, learn W and b
      blank        start from W = 0, b = -0.5, learn W and b
      thresholds   start from the anatomical wiring, learn b only
                   (separates "learn the timing" from "learn the mapping"),
  * the untrained curriculum sweep repeated with photoreceptor noise 0.03
    (experiment 2's untrained numbers were noise-free and deterministic).

    N_LEARN=4 N_EPISODES=30 python -m experiments.e3_learning
    RESUME=1 python -m experiments.e3_learning
    python -m experiments.e3_learning report
"""

from __future__ import annotations

import json
import os
import sys
import time
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e3_learning.json")

CONDITIONS = ("wired", "blank", "thresholds")
STAGES = (1, 2, 3, 4, 5)
THETA = 1.5
LEARNER = dict(sigma=0.2, lr=1.0, lr_decay=0.97, stage=3)


def learning_run(player, condition, n_episodes, seed, every=10):
    ctrl0 = player.controller.copy()
    player.controller.b[:] = -2.0
    mask = L.mask_for("all")
    if condition == "blank":
        player.controller.W[:] = 0.0
        player.controller.b[:] = -0.5
    elif condition == "thresholds":
        mask = L.mask_for("thresholds")
    learner = L.ReadoutLearner(player, mask=mask, seed=seed, **LEARNER)
    evals = [{"episode": 0, **L.evaluate(player, stage=3, n_charts=3)}]
    print(f"      {condition:<10s} ep   0  held-out acc {evals[0]['accuracy']:.3f}", flush=True)
    while len(learner.history) < n_episodes:
        learner.run(min(every, n_episodes - len(learner.history)), verbose=False)
        ev = L.evaluate(player, stage=3, n_charts=3)
        evals.append({"episode": len(learner.history), **ev})
        print(f"      {condition:<10s} ep {len(learner.history):3d}  held-out acc {ev['accuracy']:.3f}  "
              f"hit {ev['hit_rate']:.3f}  lane-correct {ev['lane_correct']:.2f}  "
              f"train reward (last {every}) {learner.curve()[-every:].mean():.3f}", flush=True)
    final = player.controller.params.tolist()
    player.controller = ctrl0
    return {"condition": condition, "seed": seed, "learner": LEARNER,
            "train_reward": learner.curve().tolist(), "held_out": evals,
            "final_params": final}


def untrained_noisy(player, noise=0.03, n_charts=2):
    player.controller.b[:] = -THETA
    saved = player.noise
    player.noise = noise
    out = {}
    for stage in STAGES:
        out[f"stage{stage}"] = L.evaluate(player, stage=stage, n_charts=n_charts,
                                          n_notes=20, interval_ms=600.0, seed=7000 + 10 * stage)
    player.noise = saved
    return out


def run_network(label, kw, n_episodes):
    t0 = time.time()
    print(f"\n=== {label}", flush=True)
    fly = M.build(regime="play", **kw)
    out = {"label": label, "stability": fly.stability()}
    player = P.Player.untrained(fly, theta=2.0)
    out["wiring"] = player.controller.wiring(fly.readout.names)
    out["untrained_noisy"] = untrained_noisy(player)
    row = "  ".join(f"s{s}={out['untrained_noisy'][f'stage{s}']['lane_correct']:.2f}" for s in STAGES)
    print(f"  untrained, noise 0.03, lane-correct: {row}", flush=True)
    for cond in CONDITIONS:
        seed = zlib.crc32(f"{label}|{cond}".encode()) % 100_000
        out[cond] = learning_run(player, cond, n_episodes, seed)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def _save(results):
    os.makedirs(RESULTS, exist_ok=True)
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


def main():
    n_learn = int(os.environ.get("N_LEARN", 4))
    n_ep = int(os.environ.get("N_EPISODES", 30))
    results = {"regime": "play", "dt_ms": M.DT_PLAY, "n_episodes": n_ep,
               "conditions": CONDITIONS, "learner": LEARNER, "untrained_theta": THETA,
               "runs": []}
    if os.environ.get("RESUME") and os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
        print(f"resuming: {len(results['runs'])} runs done")
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", {})] + [(f"rewired topology #{s}", {"shuffle_seed": s})
                                        for s in range(1, n_learn + 1)]
    for label, kw in plan:
        if label in done:
            continue
        results["runs"].append(run_network(label, kw, n_ep))
        _save(results)
    report(results)


def report(results):
    runs = results["runs"]
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"] != "real connectome"]
    if not real:
        return

    def perm(rv, v):
        v = np.asarray(v, float)
        n_ge = int((v >= rv).sum())
        return {"real": float(rv), "control_mean": float(v.mean()), "control_sd": float(v.std()),
                "n": int(len(v)), "n_ge": n_ge, "p": float((n_ge + 1) / (len(v) + 1))}

    summary = {}
    print("\n--- untrained with photoreceptor noise 0.03, lane-correct by stage ---")
    for s in STAGES:
        rv = real["untrained_noisy"][f"stage{s}"]["lane_correct"]
        v = [r["untrained_noisy"][f"stage{s}"]["lane_correct"] for r in ctrl]
        q = perm(rv, v) if v else None
        summary[f"noisy lane-correct s{s}"] = q
        print(f"  stage {s}: real {rv:.3f}" + (f" | rewired {q['control_mean']:.3f}+-{q['control_sd']:.3f} "
                                              f"{q['n_ge']}/{q['n']} p={q['p']:.2f}" if q else ""))

    print("\n--- learning: held-out accuracy (stage 3) by episode ------------------")
    for cond in results["conditions"]:
        print(f"  {cond}:")
        for r in runs:
            if cond not in r:
                continue
            ev = r[cond]["held_out"]
            print(f"    {r['label']:<24s} " + "  ".join(f"ep{e['episode']}={e['accuracy']:.2f}" for e in ev)
                  + f"   lane-correct {ev[0]['lane_correct']:.2f}->{ev[-1]['lane_correct']:.2f}"
                  + f"   err {ev[-1]['error_mean_ms'] if ev[-1]['error_mean_ms'] is not None else float('nan'):+.0f} ms")
        for name, fn in (("final", lambda ev: ev[-1]["accuracy"]),
                         ("best", lambda ev: max(e["accuracy"] for e in ev)),
                         ("area", lambda ev: float(np.mean([e["accuracy"] for e in ev[1:]])))):
            rv = fn(real[cond]["held_out"])
            v = [fn(r[cond]["held_out"]) for r in ctrl if cond in r]
            if v:
                q = perm(rv, v)
                summary[f"{cond} {name}"] = q
                print(f"    {name:<6s} real {rv:.3f} | rewired {q['control_mean']:.3f}+-{q['control_sd']:.3f} "
                      f"{q['n_ge']}/{q['n']} p={q['p']:.2f}")
    results["summary"] = summary
    _save(results)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    else:
        main()
