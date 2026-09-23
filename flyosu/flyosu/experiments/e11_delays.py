"""
Experiment 11 -- per-key delays, the one lever experiment 8 left.

Experiment 8 established a ceiling that no sensory front end removes: the four
channels peak 200-600 ms before the note reaches the judgment line, and the
*spread* between them (100-400 ms) is the network's own latency structure, not
the stimulus.  An encoder can shift the mean and not the spread, so under one
shared threshold at most one or two lanes of four are ever on time.  Its
conclusion was that the fix belongs in the controller.

This is that fix, and it is the first change to the policy's *form* rather than
its numbers: a crossing no longer presses the key, it *schedules* a press
``delay_ms[k]`` later (``Controller.with_delays``).  Four more numbers, read
off the same silent single-note probe every other untrained quantity comes
from: each key waits by however early its own channel crosses, so the press
lands at the judgment line instead of hundreds of milliseconds before it.

That is lane knowledge, like the wiring permutation, and is declared the same
way -- 4 numbers from a silent probe, no reward, and derived per network from
that network's own probe, so every control gets its own best delays rather than
the real network's.  Experiments 6 and 7 are the reason for that insistence:
twice, a procedure matched in form but developed on the real connectome turned
out to favour it.

Protocol is otherwise the project's current fair one: band wiring
(``probes.band_assignment``), theta swept per network and scored at its own
best, press-count guard on lane-correctness.  Experiment 7's no-delay numbers
are the baseline and are reused rather than repeated.

    N_SEEDS=20 python -m experiments.e11_delays
    python -m experiments.e11_delays report
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
MAX_DELAY_MS = float(os.environ.get("MAX_DELAY_MS", 1000.0))
PATH = os.path.join(RESULTS, f"e11_delays_cap{int(MAX_DELAY_MS)}.json")
E7 = os.path.join(RESULTS, "e7_wiring.json")
THETA_SWEEP = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
SWEEP_STAGE = 3
MIN_COUNTED = 20
NOISE = 0.03


def delays_from_probe(tr, wiring, theta):
    """How long each key should wait: however early its own channel crosses.

    Uses the first upward crossing of ``theta`` on that lane's wired channel,
    relative to the judgment line; a channel that never crosses gets no delay.
    Recomputed for every theta in the sweep, because where a channel crosses
    depends on the threshold it is crossing.

    ``MAX_DELAY_MS`` must be large enough never to bind, or it becomes exactly
    the kind of procedural choice experiments 6 and 7 were about.  The first
    run of this experiment capped at 600 ms and it bound on 3 of the real
    network's 4 lanes against 11 of 80 control lanes -- an asymmetry favouring
    the controls, the mirror image of the earlier ones.  A note is visible for
    ``approach_ms`` (800), so no crossing can be earlier than that; the default
    1000 ms cannot bind.
    """
    out = np.zeros(len(wiring))
    for lane, ch in enumerate(wiring):
        v = tr.z[lane, :, ch]
        up = np.flatnonzero((v > theta) & (np.concatenate([[-np.inf], v[:-1]]) <= theta))
        if len(up):
            out[lane] = min(max(-float(tr.t[up[0]]), 0.0), MAX_DELAY_MS)
    return out


def measure(label, kw):
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    tr = PR.lane_traces(fly, player.norm, player.r0)
    wiring = PR.band_assignment(tr)
    W = np.zeros((4, 4))
    for lane, ch in enumerate(wiring):
        W[lane, ch] = 1.0
    base = player.controller
    base.W = W
    lc, acc, n, dl = [], [], [], []
    for th in THETA_SWEEP:
        d = delays_from_probe(tr, wiring, th)
        ctrl = base.with_delays(d)
        ctrl.b = np.full(4, -float(th))
        player.controller = ctrl
        e = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                       interval_ms=600.0, seed=7000 + 10 * SWEEP_STAGE)
        lc.append(e["lane_correct"]); acc.append(e["accuracy"])
        n.append(int(np.array(e["confusion"]).sum())); dl.append(d.tolist())
    ok = np.array(n) >= MIN_COUNTED
    i = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
    out = {"label": label, "wiring": list(wiring), "theta": list(THETA_SWEEP),
           "lane_correct": lc, "accuracy": acc, "n_counted": n, "delays": dl,
           "eligible": ok.tolist(), "best_theta": float(THETA_SWEEP[i]),
           "best_lane_correct": float(lc[i]), "best_accuracy": float(max(acc)),
           "delays_at_best": dl[i], "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<24s} lane " + " ".join(f"{v:.2f}" for v in lc) +
          f"   best {out['best_lane_correct']:.2f}@{out['best_theta']:.1f}  "
          f"acc {out['best_accuracy']:.3f}  delays {np.round(dl[i]).astype(int).tolist()} ms  "
          f"({out['seconds']:.0f}s)", flush=True)
    return out


def main():
    n = int(os.environ.get("N_SEEDS", 20))
    results = {"sweep_stage": SWEEP_STAGE, "theta": list(THETA_SWEEP), "runs": []}
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
    runs = {r["label"]: r for r in results["runs"]}
    real = runs.get("real connectome")
    ctrl = [r for k, r in runs.items() if k != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    base = {}
    if os.path.exists(E7):
        with open(E7) as fh:
            base = {r["label"]: r["band"] for r in json.load(fh)["runs"]}
    print("\n=== experiment 11: per-key delays, on top of the band wiring ===")
    summary = []
    for key, lbl in (("best_lane_correct", "lane-correct, own best theta"),
                     ("best_accuracy", "accuracy, own best theta")):
        rv = real[key]
        cv = np.array([r[key] for r in ctrl])
        n_ge = int((cv >= rv).sum())
        print(f"\n  {lbl}")
        print(f"    with delays   real {rv:.3f}  rewired {cv.mean():.3f} +- {cv.std():.3f}  "
              f"{n_ge}/{len(cv)}  p {(n_ge + 1) / (len(cv) + 1):.3f}")
        row = {"metric": lbl, "real": float(rv), "ctrl_mean": float(cv.mean()),
               "ctrl_sd": float(cv.std()), "n_ge": n_ge, "n": len(cv),
               "p": (n_ge + 1) / (len(cv) + 1)}
        if base:
            br = base["real connectome"][key]
            bc = np.array([base[r["label"]][key] for r in ctrl if r["label"] in base])
            b_ge = int((bc >= br).sum())
            print(f"    no delays     real {br:.3f}  rewired {bc.mean():.3f} +- {bc.std():.3f}  "
                  f"{b_ge}/{len(bc)}  p {(b_ge + 1) / (len(bc) + 1):.3f}   (experiment 7)")
            print(f"    change        real {rv - br:+.3f}   rewired {cv.mean() - bc.mean():+.3f}")
            row.update({"base_real": float(br), "base_ctrl_mean": float(bc.mean()),
                        "base_n_ge": b_ge})
        summary.append(row)
    d = np.array([r["delays_at_best"] for r in ctrl])
    print(f"\n  delays chosen: real {np.round(real['delays_at_best']).astype(int).tolist()} ms, "
          f"rewired mean {d.mean():.0f} ms (max {d.max():.0f})")
    results["summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    else:
        main()
