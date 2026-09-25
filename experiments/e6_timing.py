"""
Experiment 6 -- where is the untrained advantage?

Experiment 4 measured untrained play on the real connectome and 20 rewired
graphs and found the real network far ahead (0.82 vs 0.29 +- 0.15, 0/20,
p = 0.048) -- but neither the spectral radius (rho = 0.20) nor the wiring
margin (rho = -0.03) predicted play across those graphs.  Something about the
real wiring makes the untrained policy work and none of the quantities measured
so far is it.

This measures four more candidates on the *same 21 networks*, and correlates
them against the behaviour experiment 4 already recorded.  No new play is
simulated for the rewired graphs, so the behavioural numbers are exactly the
ones the p = 0.048 was computed from, and the only new cost is the probes.

The candidates (``flyosu/probes.py``), in the order they occurred:

  shared-threshold band   the untrained controller has ONE threshold for all
                          four keys.  Every channel must clear it during its
                          own lane and stay under it during the other three.
                          Experiment 4's margin was measured lane by lane and
                          could not see a scale mismatch between channels.
  crossing timing         when each channel first crosses the policy's actual
                          theta, relative to the judgment line, and how many
                          lanes cross inside the window where a press is judged
                          rather than being a stray.
  selectivity             how much of the hit window the right channel spends
                          as the largest of the four.
  chord behaviour         what two simultaneous notes do to a channel that one
                          note drives.

Then the causal test the correlations suggest.  If the real wiring's advantage
is that *one* threshold serves all four of its keys, then handing every network
four per-key thresholds -- read off the same single-note probe, halfway between
each key's own hit and its worst false alarm -- should help the controls more
than it helps the real network, and the gap should narrow.  Phase 2 does
exactly that and replays experiment 4's untrained protocol (stages 2-4, two
20-note charts each, the same seeds) so the numbers sit next to its 0.82 vs
0.29 without any re-measurement of the baseline.

Per-key thresholds are four more numbers chosen with lane knowledge, on top of
the 4.6 bits the anatomical wiring already uses; like the wiring, they come
from a silent probe and no reward, and they are declared rather than hidden.

Phase 3 is a robustness check on the project's only p < 0.05 result rather than
a new question.  Experiments 2, 3 and 4 all fixed theta = 1.5 for every
network, real and control alike.  That is a matched procedure, but it is not
the same as a matched *outcome*: if 1.5 happens to sit well for the real
network and badly for the controls, part of the untrained gap is a threshold
choice rather than the wiring.  Phase 3 sweeps theta per network and gives
every one of them its own best -- the most generous control the untrained
protocol admits -- on stage 3 alone to keep it affordable.

    python -m experiments.e6_timing
    N_SEEDS=20 python -m experiments.e6_timing
    PHASE=2 N_SEEDS=20 python -m experiments.e6_timing
    PHASE=3 N_SEEDS=20 python -m experiments.e6_timing
    python -m experiments.e6_timing report
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, probes as PR  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e6_timing.json")
E4 = os.path.join(RESULTS, "e4_covariate.json")
THETA = 1.5
STAGES = (2, 3, 4)          # experiment 4's untrained protocol, verbatim
NOISE = 0.03
THETA_SWEEP = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
SWEEP_STAGE = 3
# lane-correctness is a ratio over presses that landed near a note, so a
# network that presses twice and gets both right scores 1.00.  At theta 1.5
# every network in experiment 4 counted 45-237 presses over 120 notes, so its
# p = 0.048 is unaffected; a threshold sweep is not, because high thresholds
# silence a network.  A theta is eligible only if it produces this many
# counted presses over the sweep's 40 notes.
MIN_COUNTED = 20

# predictor name -> (how to pull it out of a probe result, which way is "better")
PREDICTORS = {
    "shared band (window)": lambda d: d["shared_threshold"]["shared_band"],
    "shared band (whole descent)": lambda d: d["shared_threshold_all"]["shared_band"],
    "worst-key margin": lambda d: d["shared_threshold"]["worst_key_margin"],
    "lanes crossing on time": lambda d: d["crossings"]["n_on_time"],
    "lanes crossing at all": lambda d: d["crossings"]["n_fire"],
    "false keys driven": lambda d: -d["crossings"]["n_false_keys"],
    "mean crossing lag (ms)": lambda d: (d["crossings"]["mean_crossing_ms"]
                                         if d["crossings"]["mean_crossing_ms"] is not None else -1e4),
    "peak lag, |mean| (ms)": lambda d: -d["timing"]["peak_lag_abs_mean_ms"],
    "peak lag spread (ms)": lambda d: -d["timing"]["peak_lag_spread_ms"],
    "argmax fraction": lambda d: d["selectivity"]["argmax_mean"],
    "peak margin": lambda d: d["selectivity"]["peak_margin_mean"],
    "chord delta (z)": lambda d: d["chords"]["delta_mean_z"],
    "chord, uninvolved keys": lambda d: -d["chords"]["uninvolved_peak_mean"],
}


def measure(label, kw):
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=THETA)
    wiring = [int(np.argmax(player.controller.W[l])) for l in range(4)]
    out = PR.measure(fly, player.norm, player.r0, wiring=wiring, theta=THETA)
    out["label"] = label
    out["seconds"] = round(time.time() - t0, 1)
    st, cr, ti = out["shared_threshold"], out["crossings"], out["timing"]
    print(f"  {label:<24s} band {st['shared_band']:+.2f} (all {out['shared_threshold_all']['shared_band']:+.2f})  "
          f"cross {cr['n_fire']}/4 on-time {cr['n_on_time']}  false {cr['n_false_keys']}  "
          f"peak lag {ti['peak_lag_mean_ms']:+.0f}+-{ti['peak_lag_spread_ms']:.0f} ms  "
          f"argmax {out['selectivity']['argmax_mean']:.2f}  ({out['seconds']:.0f}s)", flush=True)
    return out


def per_key(label, kw, probe):
    """Phase 2: replace the one shared threshold with four from the probe."""
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    theta_k = np.asarray(probe["shared_threshold"]["theta_per_key"], dtype=float)
    player.controller.b[:] = -theta_k
    out = {"label": label, "theta_per_key": theta_k.tolist(), "untrained": {}}
    for s in STAGES:
        out["untrained"][f"stage{s}"] = L.evaluate(player, stage=s, n_charts=2, n_notes=20,
                                                   interval_ms=600.0, seed=7000 + 10 * s)
    out["lane_correct_mean"] = float(np.mean([out["untrained"][f"stage{s}"]["lane_correct"]
                                              for s in STAGES]))
    out["accuracy_mean"] = float(np.mean([out["untrained"][f"stage{s}"]["accuracy"]
                                          for s in STAGES]))
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<24s} theta {np.round(theta_k, 2)}  lane-correct {out['lane_correct_mean']:.2f}  "
          f"acc {out['accuracy_mean']:.3f}  ({out['seconds']:.0f}s)", flush=True)
    return out


def best_theta(label, kw):
    """Phase 3: each network's best shared threshold, on stage 3."""
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    out = {"label": label, "theta": list(THETA_SWEEP), "lane_correct": [], "accuracy": [],
           "n_counted": []}
    for th in THETA_SWEEP:
        player.controller.b[:] = -float(th)
        e = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                       interval_ms=600.0, seed=7000 + 10 * SWEEP_STAGE)
        out["lane_correct"].append(e["lane_correct"]); out["accuracy"].append(e["accuracy"])
        out["n_counted"].append(int(np.array(e["confusion"]).sum()))
    lc = np.array(out["lane_correct"]); ok = np.array(out["n_counted"]) >= MIN_COUNTED
    i = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
    j = int(np.argmax(out["accuracy"]))
    k = list(THETA_SWEEP).index(THETA)
    out["eligible"] = ok.tolist()
    out["best_theta"] = float(THETA_SWEEP[i])
    out["best_lane_correct"] = float(lc[i])
    out["best_is_eligible"] = bool(ok.any())
    out["best_acc_theta"] = float(THETA_SWEEP[j]); out["best_accuracy"] = float(out["accuracy"][j])
    out["at_1_5"] = float(lc[k]); out["acc_at_1_5"] = float(out["accuracy"][k])
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<24s} lane " + " ".join(f"{v:.2f}" for v in out["lane_correct"]) +
          "  n " + " ".join(f"{n:3d}" for n in out["n_counted"]) +
          f"   best {out['best_lane_correct']:.2f}@{out['best_theta']:.1f} "
          f"(1.5:{out['at_1_5']:.2f})  acc best {out['best_accuracy']:.3f}@{out['best_acc_theta']:.1f} "
          f"(1.5:{out['acc_at_1_5']:.3f})  ({out['seconds']:.0f}s)", flush=True)
    return out


def phase3():
    with open(PATH) as fh:
        results = json.load(fh)
    n = int(os.environ.get("N_SEEDS", 20))
    runs = results.setdefault("theta_sweep", [])
    done = {r["label"] for r in runs}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done:
            continue
        runs.append(best_theta(label, kw))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report(results)


def phase2():
    with open(PATH) as fh:
        results = json.load(fh)
    probes = {r["label"]: r for r in results["runs"]}
    n = int(os.environ.get("N_SEEDS", 20))
    runs = results.setdefault("per_key", [])
    done = {r["label"] for r in runs}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done or label not in probes:
            continue
        runs.append(per_key(label, kw, probes[label]))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report(results)


def main():
    n = int(os.environ.get("N_SEEDS", 20))
    results = {"theta": THETA, "runs": []}
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


def behaviour() -> dict:
    """Untrained lane-correctness per network, from experiment 4."""
    with open(E4) as fh:
        e4 = json.load(fh)
    return {r["label"]: r for r in e4["runs"]}


def report(results):
    from scipy.stats import spearmanr
    beh = behaviour()
    runs = [r for r in results["runs"] if r["label"] in beh]
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"] != "real connectome"]
    if len(ctrl) < 3:
        print("not enough controls yet")
        return
    y = np.array([beh[r["label"]]["lane_correct_mean"] for r in ctrl])
    acc = np.array([beh[r["label"]]["accuracy_mean"] for r in ctrl])
    print(f"\n=== {len(ctrl)} rewired graphs, behaviour from experiment 4 ===")
    print(f"{'predictor':<30s} {'real':>8s} {'rewired mean':>14s} {'n>=real':>8s} "
          f"{'rho(lane)':>10s} {'p':>7s} {'rho(acc)':>9s}")
    table = {}
    for name, fn in PREDICTORS.items():
        x = np.array([fn(r) for r in ctrl], dtype=float)
        rho, p = spearmanr(x, y)
        rho_a, _ = spearmanr(x, acc)
        rv = fn(real) if real else np.nan
        n_ge = int((x >= rv).sum()) if real else -1
        print(f"{name:<30s} {rv:>8.2f} {x.mean():>8.2f} +-{x.std():<4.2f} {n_ge:>4d}/{len(x):<3d} "
              f"{rho:>+10.2f} {p:>7.3f} {rho_a:>+9.2f}")
        table[name] = {"real": float(rv), "ctrl_mean": float(x.mean()), "ctrl_sd": float(x.std()),
                       "n_ge": n_ge, "n": len(x), "spearman_lane": float(rho), "p_lane": float(p),
                       "spearman_acc": float(rho_a)}
    results["correlations"] = table
    results["behaviour_source"] = "e4_covariate.json"

    pk = {r["label"]: r for r in results.get("per_key", [])}
    if len(pk) > 3:
        shared_real = beh["real connectome"]["lane_correct_mean"]
        shared_ctrl = y
        pk_ctrl = np.array([pk[r["label"]]["lane_correct_mean"] for r in ctrl if r["label"] in pk])
        pk_real = pk["real connectome"]["lane_correct_mean"] if "real connectome" in pk else np.nan
        n_ge = int((pk_ctrl >= pk_real).sum())
        print("\n=== phase 2: four per-key thresholds instead of one shared ===")
        print(f"  real     lane-correct {shared_real:.2f} -> {pk_real:.2f}  "
              f"({pk_real - shared_real:+.2f})")
        print(f"  rewired  lane-correct {shared_ctrl.mean():.2f} +- {shared_ctrl.std():.2f} -> "
              f"{pk_ctrl.mean():.2f} +- {pk_ctrl.std():.2f}  "
              f"({pk_ctrl.mean() - shared_ctrl.mean():+.2f}, n={len(pk_ctrl)})")
        print(f"  {n_ge}/{len(pk_ctrl)} rewired reach the real network  p {(n_ge + 1) / (len(pk_ctrl) + 1):.3f}"
              f"   (was 0/20, p 0.048 with one threshold)")
        results["per_key_summary"] = {
            "real_shared": float(shared_real), "real_per_key": float(pk_real),
            "ctrl_shared_mean": float(shared_ctrl.mean()), "ctrl_per_key_mean": float(pk_ctrl.mean()),
            "ctrl_per_key_sd": float(pk_ctrl.std()), "n": int(len(pk_ctrl)), "n_ge": n_ge,
            "p": (n_ge + 1) / (len(pk_ctrl) + 1)}
    ts = {r["label"]: r for r in results.get("theta_sweep", [])}
    if len(ts) > 3 and "real connectome" in ts:
        rl = ts["real connectome"]
        cv = np.array([ts[r["label"]]["best_lane_correct"] for r in ctrl if r["label"] in ts])
        at = np.array([ts[r["label"]]["at_1_5"] for r in ctrl if r["label"] in ts])
        n_ge = int((cv >= rl["best_lane_correct"]).sum())
        n_ge_fixed = int((at >= rl["at_1_5"]).sum())
        print(f"\n=== phase 3: every network given its own best threshold (stage {SWEEP_STAGE}) ===")
        print(f"  at theta 1.5 (as in experiments 2-4):  real {rl['at_1_5']:.2f}  "
              f"rewired {at.mean():.2f} +- {at.std():.2f}  {n_ge_fixed}/{len(at)}  "
              f"p {(n_ge_fixed + 1) / (len(at) + 1):.3f}")
        print(f"  each at its own best theta:            real {rl['best_lane_correct']:.2f} "
              f"(theta {rl['best_theta']:.1f})  rewired {cv.mean():.2f} +- {cv.std():.2f}  "
              f"{n_ge}/{len(cv)}  p {(n_ge + 1) / (len(cv) + 1):.3f}")
        ar = np.array([ts[r["label"]]["best_accuracy"] for r in ctrl if r["label"] in ts])
        a15 = np.array([ts[r["label"]]["acc_at_1_5"] for r in ctrl if r["label"] in ts])
        n_ga = int((ar >= rl["best_accuracy"]).sum()); n_g15 = int((a15 >= rl["acc_at_1_5"]).sum())
        print(f"  accuracy at 1.5:                       real {rl['acc_at_1_5']:.3f}  "
              f"rewired {a15.mean():.3f} +- {a15.std():.3f}  {n_g15}/{len(a15)}  "
              f"p {(n_g15 + 1) / (len(a15) + 1):.3f}")
        print(f"  accuracy, each at its own best theta:  real {rl['best_accuracy']:.3f}  "
              f"rewired {ar.mean():.3f} +- {ar.std():.3f}  {n_ga}/{len(ar)}  "
              f"p {(n_ga + 1) / (len(ar) + 1):.3f}")
        print("  rewired best thetas: " +
              " ".join(f"{ts[r['label']]['best_theta']:.1f}" for r in ctrl if r["label"] in ts))
        results["theta_sweep_summary"] = {
            "stage": SWEEP_STAGE, "real_at_1_5": rl["at_1_5"],
            "real_best": rl["best_lane_correct"], "real_best_theta": rl["best_theta"],
            "ctrl_at_1_5_mean": float(at.mean()), "ctrl_best_mean": float(cv.mean()),
            "ctrl_best_sd": float(cv.std()), "n": int(len(cv)),
            "n_ge_fixed": n_ge_fixed, "p_fixed": (n_ge_fixed + 1) / (len(at) + 1),
            "n_ge_best": n_ge, "p_best": (n_ge + 1) / (len(cv) + 1),
            "real_acc_at_1_5": rl["acc_at_1_5"], "real_acc_best": rl["best_accuracy"],
            "ctrl_acc_at_1_5_mean": float(a15.mean()), "ctrl_acc_best_mean": float(ar.mean()),
            "n_ge_acc_fixed": n_g15, "p_acc_fixed": (n_g15 + 1) / (len(a15) + 1),
            "n_ge_acc_best": n_ga, "p_acc_best": (n_ga + 1) / (len(ar) + 1),
            "min_counted": MIN_COUNTED}
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    elif os.environ.get("PHASE") == "2":
        phase2()
    elif os.environ.get("PHASE") == "3":
        phase3()
    else:
        main()
