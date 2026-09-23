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

``INTERVAL_MS`` is experiment 12's handle.  Experiment 11 found that the real
network wants to wait 630-652 ms on three of its four lanes while the gap
between notes is 600 ms, and offered "the scheduled press lands on the next
note" as a candidate explanation for why delays help every control and not it.
Widening the interval is the test: the delays come from an 800 ms silent probe
and so do not move, the gap does.  Each run also records a paired no-delay arm
(same network, threshold, charts and noise seed) so "gain from delays" is a
within-network difference at that interval; at 600 ms the arm is experiment 7's.

    N_SEEDS=20 python -m experiments.e11_delays
    INTERVAL_MS=1400 N_SEEDS=10 python -m experiments.e11_delays
    python -m experiments.e11_delays report
    INTERVAL_MS=1400 python -m experiments.e11_delays report
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
INTERVAL_MS = float(os.environ.get("INTERVAL_MS", 600.0))

# Every parameter that changes the result goes in the filename.  This project
# has already lost a run to the opposite habit: a second run wrote the first
# one's path, found every label in ``done``, skipped all the work and looked
# like it had succeeded.  The one exception is the default (600 ms interval,
# 1000 ms cap), which keeps the original name so experiment 11's completed run
# is reused rather than recomputed.
_TAG = "" if INTERVAL_MS == 600.0 else f"_interval{int(INTERVAL_MS)}"
PATH = os.path.join(RESULTS, f"e11_delays_cap{int(MAX_DELAY_MS)}{_TAG}.json")

# Networks are independent -- different W, no shared state -- so they can be run
# in parallel processes for an exact speedup.  The machine has 12 cores and the
# sparse matvec is single-threaded, so this is the one large win available
# without touching the numerics (batching trajectories as a sparse-dense product
# would only be 1.4x overall and would perturb the arithmetic, which this
# project cannot afford: the model cache is keyed on parameters, not code).
# Each shard writes its own file so the checkpoint writes cannot race; ``merge``
# folds them into PATH.
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"
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

    The cap deliberately does *not* move with ``INTERVAL_MS``.  The delays come
    from the silent probe, which is an 800 ms descent whatever the chart does,
    so the largest delay any network can ask for is 800 ms at every interval
    and 1000 ms is non-binding at every interval.  Tying the cap to the
    interval would make the wider-interval conditions a different procedure as
    well as a different chart.
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
    lc0, acc0, n0 = [], [], []
    for th in THETA_SWEEP:
        d = delays_from_probe(tr, wiring, th)
        ctrl = base.with_delays(d)
        ctrl.b = np.full(4, -float(th))
        player.controller = ctrl
        e = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                       interval_ms=INTERVAL_MS, seed=7000 + 10 * SWEEP_STAGE)
        lc.append(e["lane_correct"]); acc.append(e["accuracy"])
        n.append(int(np.array(e["confusion"]).sum())); dl.append(d.tolist())
        # Paired no-delay arm: the same network, threshold, charts and noise
        # seed with the crossing pressing immediately, so "gain from delays"
        # is a within-network difference at this interval rather than a
        # comparison against experiment 7, which only exists at 600 ms.
        # When every delay is zero the two policies are the same policy
        # (``tests.test_play`` asserts it), so the play is not repeated.
        if float(d.max()) <= 0.0:
            e0 = e
        else:
            ctrl0 = base.copy()
            ctrl0.b = np.full(4, -float(th))
            player.controller = ctrl0
            e0 = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                            interval_ms=INTERVAL_MS, seed=7000 + 10 * SWEEP_STAGE)
        lc0.append(e0["lane_correct"]); acc0.append(e0["accuracy"])
        n0.append(int(np.array(e0["confusion"]).sum()))
    ok = np.array(n) >= MIN_COUNTED
    i = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
    ok0 = np.array(n0) >= MIN_COUNTED
    i0 = int(np.argmax(np.where(ok0, lc0, -1.0))) if ok0.any() else int(np.argmax(lc0))
    out = {"label": label, "wiring": list(wiring), "theta": list(THETA_SWEEP),
           "interval_ms": INTERVAL_MS, "max_delay_ms": MAX_DELAY_MS,
           "lane_correct": lc, "accuracy": acc, "n_counted": n, "delays": dl,
           "eligible": ok.tolist(), "best_theta": float(THETA_SWEEP[i]),
           "best_lane_correct": float(lc[i]), "best_accuracy": float(max(acc)),
           "delays_at_best": dl[i],
           "nodelay_lane_correct": lc0, "nodelay_accuracy": acc0,
           "nodelay_n_counted": n0, "nodelay_eligible": ok0.tolist(),
           "nodelay_best_theta": float(THETA_SWEEP[i0]),
           "nodelay_best_lane_correct": float(lc0[i0]),
           "nodelay_best_accuracy": float(max(acc0)),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<24s} lane " + " ".join(f"{v:.2f}" for v in lc) +
          f"   best {out['best_lane_correct']:.2f}@{out['best_theta']:.1f}  "
          f"acc {out['best_accuracy']:.3f} (no delays {out['nodelay_best_accuracy']:.3f})  "
          f"delays {np.round(dl[i]).astype(int).tolist()} ms  "
          f"({out['seconds']:.0f}s)", flush=True)
    return out


def main():
    n = int(os.environ.get("N_SEEDS", 20))
    results = {"sweep_stage": SWEEP_STAGE, "theta": list(THETA_SWEEP),
               "interval_ms": INTERVAL_MS, "max_delay_ms": MAX_DELAY_MS, "runs": []}
    if os.path.exists(SHARD_PATH):
        with open(SHARD_PATH) as fh:
            results = json.load(fh)
        # belt and braces on top of the filename: refuse to append runs made at
        # one interval to a file recorded at another.
        prev = results.get("interval_ms", 600.0)
        if float(prev) != INTERVAL_MS:
            raise SystemExit(f"{PATH} holds interval {prev} ms, not {INTERVAL_MS} ms")
        results["interval_ms"] = INTERVAL_MS
        results["max_delay_ms"] = MAX_DELAY_MS
    done = {r["label"] for r in results["runs"]}
    # a shard must also skip anything the canonical file already holds, so a
    # resumed parallel run does not redo the sequential run's networks
    if SHARD is not None and os.path.exists(PATH):
        with open(PATH) as fh:
            done |= {r["label"] for r in json.load(fh)["runs"]}
    print(f"interval {INTERVAL_MS:.0f} ms, delay cap {MAX_DELAY_MS:.0f} ms -> "
          f"{os.path.basename(SHARD_PATH)} ({len(done)} networks already done)", flush=True)
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    if SHARD is not None:
        plan = [pk for i, pk in enumerate(plan) if i % NSHARD == int(SHARD)]
    for label, kw in plan:
        if label in done:
            continue
        results["runs"].append(measure(label, kw))
        with open(SHARD_PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    if SHARD is None:
        report(results)
    else:
        print(f"shard {SHARD} done: {len(results['runs'])} networks in "
              f"{os.path.basename(SHARD_PATH)}; run `merge` to fold in.")


def report(results):
    runs = {r["label"]: r for r in results["runs"]}
    real = runs.get("real connectome")
    ctrl = [r for k, r in runs.items() if k != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    base = {}
    if os.path.exists(E7) and results.get("interval_ms", 600.0) == 600.0:
        # experiment 7's no-delay sweep is only comparable at its own interval
        with open(E7) as fh:
            base = {r["label"]: r["band"] for r in json.load(fh)["runs"]}
    elif "nodelay_accuracy" in real:
        base = {r["label"]: {"best_lane_correct": r["nodelay_best_lane_correct"],
                             "best_accuracy": r["nodelay_best_accuracy"]}
                for r in results["runs"]}
    print(f"\n=== experiment 11: per-key delays, band wiring, "
          f"{results.get('interval_ms', 600.0):.0f} ms note interval ===")
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
                  f"{b_ge}/{len(bc)}  p {(b_ge + 1) / (len(bc) + 1):.3f}")
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


def merge():
    """Fold every shard file for this (interval, cap) into the canonical PATH."""
    import glob
    results = {"sweep_stage": SWEEP_STAGE, "theta": list(THETA_SWEEP),
               "interval_ms": INTERVAL_MS, "max_delay_ms": MAX_DELAY_MS, "runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    seen = {r["label"] for r in results["runs"]}
    for f in sorted(glob.glob(PATH[:-5] + "_shard*of*.json")):
        with open(f) as fh:
            got = json.load(fh)
        if float(got.get("interval_ms", 600.0)) != INTERVAL_MS:
            raise SystemExit(f"{f} holds a different interval; refusing to merge")
        for r in got["runs"]:
            if r["label"] not in seen:
                results["runs"].append(r); seen.add(r["label"])
        print(f"  {os.path.basename(f):<52s} {len(got['runs']):>2} runs")
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"merged -> {os.path.basename(PATH)}: {len(results['runs'])} networks")
    report(results)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "report":
        with open(PATH) as fh:
            report(json.load(fh))
    elif cmd == "merge":
        merge()
    else:
        main()
