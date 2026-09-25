"""
Experiment 2 -- the fly plays.

Experiment 1 asked whether the connectome maps visual position to distinct
motor output under a static protocol.  This one closes the loop: notes fall in
real time, the network runs continuously, the four channels drive four keys,
and osu!mania's own judge keeps score.  Everything is run on the real
connectome and on the three matched control families from experiment 1.

Regime.  All of this uses ``model.build(regime="play")``: the experiment-1
calibration with per-neuron gain capped so the blank field is a fixed point.
Run continuously, the experiment-1 regime is chaotic and its ongoing activity
swamps the pooled channels (docs/CALIBRATION.md, "Ongoing activity"); part A0
records that so the regime change is measured, not asserted.

  A0  stability     drift and spectral radius at the blank field, both regimes
  A1  static probe  experiment 1's probe B, re-run in the play regime
  A2  untrained     the anatomical policy on curriculum stages 1-5
  B   learning      20 readout parameters, reward-modulated perturbation,
                    connectome frozen; real vs rewired; held-out evaluation
                    every 10 episodes.  Two starts: anatomical wiring
                    (learn timing and mixing) and W = 0 (discover the mapping).

    N_CTRL=3 N_LEARN=3 N_EPISODES=40 python -m experiments.e2_play
    RESUME=1 python -m experiments.e2_play          # continue a saved run
"""

from __future__ import annotations

import json
import os
import sys
import time
import zlib

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P  # noqa: E402
from flyosu.controller import best_assignment  # noqa: E402
from flyosu.encoder import EL_JUDGE, LANE_AZ  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e2_play.json")

CONTROLS = [("rewired topology", "shuffle_seed"),
            ("shuffled retinotopy", "retino_seed"),
            ("shuffled channel labels", "channel_seed")]
THETAS = (1.5, 2.0)
STAGES = (1, 2, 3, 4, 5)


# ---------------------------------------------------------------------------

def decode(X, y, seed=0):
    F = (X - X.mean(0)) / (X.std(0) + 1e-8)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    return float(cross_val_score(LogisticRegression(max_iter=3000), F, y, cv=cv).mean())


def probe_static(fly, r0, n_trials=30, noise=0.03, seed=0, dt=M.DT_PLAY):
    """Experiment 1's probe B (jitter + photoreceptor noise), from the fixed point."""
    rng = np.random.default_rng(seed)
    R, y = [], []
    for li, az in enumerate(LANE_AZ):
        for _ in range(n_trials):
            ext = fly.stimulus([(az + rng.normal(0, 4.0), EL_JUDGE + rng.normal(0, 6.0),
                                 rng.uniform(0.8, 1.0))])
            p = fly.ph_local
            ext[p] = np.clip(ext[p] + rng.normal(0, noise, len(p)), 0, 1)
            R.append(fly.net.run(ext, duration_ms=300.0, dt=dt, r0=r0)[0]); y.append(li)
    R, y = np.array(R), np.array(y)
    ch = np.array([fly.channels(r) for r in R])
    Z = (ch - ch.mean(0)) / (ch.std(0) + 1e-9)
    conf = np.zeros((4, 4), int)
    for t, p in zip(y, Z.argmax(1)):
        conf[t, p] += 1
    best = best_assignment(conf.astype(float))
    return {"argmax_policy": float(sum(conf[i, best[i]] for i in range(4)) / conf.sum()),
            "4 pooled channels": decode(ch, y),
            "descending (population)": decode(R[:, fly.dn], y)}


def untrained_play(player, n_charts=2, n_notes=20, interval_ms=600.0):
    out = {}
    for theta in THETAS:
        player.controller.b[:] = -theta
        for stage in STAGES:
            ev = L.evaluate(player, stage=stage, n_charts=n_charts, n_notes=n_notes,
                            interval_ms=interval_ms, seed=5000 + 10 * stage)
            out[f"theta{theta}_stage{stage}"] = ev
    return out


def learning_run(player, n_episodes, wired, seed, every=10):
    ctrl0 = player.controller.copy()
    if not wired:
        # no wiring, and a threshold low enough that perturbations of W can
        # produce presses at all -- at b = -2 the drive never crosses zero and
        # reward has no gradient
        player.controller.W[:] = 0.0
        player.controller.b[:] = -0.5
    learner = L.ReadoutLearner(player, stage=3, sigma=0.2, lr=1.0, seed=seed)
    evals = [{"episode": 0, **L.evaluate(player, stage=3, n_charts=3)}]
    print(f"      ep   0  held-out acc {evals[0]['accuracy']:.3f}  hit {evals[0]['hit_rate']:.3f}", flush=True)
    while len(learner.history) < n_episodes:
        learner.run(min(every, n_episodes - len(learner.history)), verbose=False)
        ev = L.evaluate(player, stage=3, n_charts=3)
        evals.append({"episode": len(learner.history), **ev})
        print(f"      ep {len(learner.history):3d}  held-out acc {ev['accuracy']:.3f}  "
              f"hit {ev['hit_rate']:.3f}  lane-correct {ev['lane_correct']:.2f}  "
              f"train reward (last {every}) {learner.curve()[-every:].mean():.3f}", flush=True)
    final = player.controller.copy()
    player.controller = ctrl0
    return {"wired_start": wired, "seed": seed, "train_reward": learner.curve().tolist(),
            "held_out": evals, "final_params": final.params.tolist()}


# ---------------------------------------------------------------------------

def run_network(label, family, kw, n_learn_episodes, do_learn):
    t0 = time.time()
    print(f"\n=== {label}", flush=True)
    out = {"label": label, "family": family}
    fly = M.build(regime="play", **kw)
    out["stability"] = fly.stability()
    print(f"  A0 play regime: fixed point {out['stability']['fixed_point']}  "
          f"radius {out['stability']['spectral_radius']:.2f}  Re {out['stability']['max_real']:.2f}")
    player = P.Player.untrained(fly, theta=2.0)
    out["wiring"] = player.controller.wiring(fly.readout.names)
    out["channel_names"] = fly.readout.names
    out["static_probe"] = probe_static(fly, player.r0)
    sp = out["static_probe"]
    print(f"  A1 static probe B: argmax {sp['argmax_policy']:.3f}  4ch {sp['4 pooled channels']:.3f}  "
          f"DN {sp['descending (population)']:.3f}")
    out["untrained"] = untrained_play(player)
    for theta in THETAS:
        row = "  ".join(f"s{s}={out['untrained'][f'theta{theta}_stage{s}']['accuracy']:.2f}" for s in STAGES)
        print(f"  A2 untrained theta {theta}: acc {row}")
    if do_learn:
        for wired in (True, False):
            print(f"  B  learning from {'anatomical wiring' if wired else 'W = 0'} ...")
            player.controller.b[:] = -2.0
            out[f"learn_{'wired' if wired else 'blank'}"] = learning_run(
                player, n_learn_episodes, wired, seed=zlib.crc32(label.encode()) % 1000)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def _save(results):
    os.makedirs(RESULTS, exist_ok=True)
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


def main():
    n_ctrl = int(os.environ.get("N_CTRL", 3))
    n_learn = int(os.environ.get("N_LEARN", 3))
    n_ep = int(os.environ.get("N_EPISODES", 40))
    results = {"regime": "play", "dt_ms": M.DT_PLAY, "thetas": THETAS, "stages": STAGES,
               "n_episodes": n_ep, "runs": []}
    if os.environ.get("RESUME") and os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
        print(f"resuming: {len(results['runs'])} runs done")
    done = {r["label"] for r in results["runs"]}

    # the experiment-1 regime, for the record: chaotic blank field
    if "e1_regime_stability" not in results:
        fly = M.build()
        results["e1_regime_stability"] = fly.stability()
        print("e1 regime blank field:", results["e1_regime_stability"])
        del fly
        _save(results)

    plan = [("real connectome", "real", {}, True)]
    for family, kwarg in CONTROLS:
        for s in range(1, n_ctrl + 1):
            plan.append((f"{family} #{s}", family, {kwarg: s},
                         family == "rewired topology" and s <= n_learn))
    for label, family, kw, learn in plan:
        if label in done:
            continue
        results["runs"].append(run_network(label, family, kw, n_ep, learn))
        _save(results)
    report(results)


def report(results):
    runs = results["runs"]

    def rows(fam):
        return [r for r in runs if r["family"] == fam]

    def perm(real, v):
        v = np.asarray(v, float)
        if len(v) == 0:
            return None
        n_ge = int((v >= real).sum())
        return {"real": float(real), "control_mean": float(v.mean()), "control_sd": float(v.std()),
                "n": int(len(v)), "n_ge": n_ge, "p": float((n_ge + 1) / (len(v) + 1)),
                "effect_sd": float((real - v.mean()) / (v.std() + 1e-12))}

    metrics = {
        "spectral radius": lambda r: r["stability"]["spectral_radius"],
        "static argmax": lambda r: r["static_probe"]["argmax_policy"],
        "static 4ch decoder": lambda r: r["static_probe"]["4 pooled channels"],
    }
    for theta in THETAS:
        for s in STAGES:
            metrics[f"untrained acc t{theta} s{s}"] = (
                lambda r, t=theta, s=s: r["untrained"][f"theta{t}_stage{s}"]["accuracy"])
            metrics[f"untrained lane-correct t{theta} s{s}"] = (
                lambda r, t=theta, s=s: r["untrained"][f"theta{t}_stage{s}"]["lane_correct"])

    print("\n--- summary: real vs each control family (p floor 1/(n+1)) ---------")
    summary = {}
    real = rows("real")
    if not real:
        return
    real = real[0]
    for name, fn in metrics.items():
        rv = fn(real)
        line = f"{name:<36s} real {rv:.3f}"
        summary[name] = {"real": rv}
        for fam, _ in CONTROLS:
            v = [fn(r) for r in rows(fam)]
            q = perm(rv, v)
            summary[name][fam] = q
            if q:
                line += f" | {fam[:9]:<9s} {q['control_mean']:.3f}+-{q['control_sd']:.3f} {q['n_ge']}/{q['n']} p={q['p']:.2f}"
        print(line)

    print("\n--- learning (stage 3, held-out accuracy by episode) ------------------")
    for key in ("learn_wired", "learn_blank"):
        print(f"  {key}:")
        for r in runs:
            if key in r:
                ev = r[key]["held_out"]
                print(f"    {r['label']:<24s} " + "  ".join(f"ep{e['episode']}={e['accuracy']:.2f}" for e in ev)
                      + f"   lane-correct {ev[0]['lane_correct']:.2f}->{ev[-1]['lane_correct']:.2f}")
    results["summary"] = summary
    _save(results)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    else:
        main()
