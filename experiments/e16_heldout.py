"""
Experiment 16 -- the untrained comparison, on charts nobody tuned against.

Every behavioural comparison in this project has been scored on the same charts
the threshold was chosen on.  Experiment 13 showed what that costs: on the male
CNS the real network's apparent advantage (0.258 against 0.131) was almost
entirely selection, and it inverted on held-out charts (0.122 against 0.138).
The controls, being twenty draws from a distribution, absorb an optimistic
threshold far better than a single network does.

That cuts one way there and the other way here.  The best untrained arm this
project has produced is experiment 11's per-key delays at a 1400 ms interval,
where the real connectome scores 0.454 against the controls' 0.736 and is
beaten by 19 of 20.  If threshold selection flatters the controls more than it
flatters the real network -- which is the direction experiment 13 found -- then
that gap is an *underestimate* and held-out scoring should widen it.  If it
flatters the real network more, the gap should narrow.  Either way the headline
number of the project's strongest behavioural comparison is currently measured
in a way we already know is biased, and nobody has checked which way.

Nothing is re-chosen here.  Each network's policy is read off its finished
experiment 11 run -- its wiring from its own silent probe, its threshold as the
accuracy-maximising value on the sweep charts, and the four delays that theta
implies -- and replayed on three charts it has never seen (seed 999, experiment
3's held-out seeds, disjoint from the sweep's seed 7030).

**Prediction, recorded before the numbers.**  Both the real network and the
controls lose accuracy; the ordering does not change and the real connectome is
still beaten by at least 18 of 20 controls.  The gap widens rather than narrows,
because experiment 13's asymmetry says the single network pays more for an
optimistic threshold than a twenty-draw distribution does.  A narrowing to
within one standard deviation would be the first sign in seven varied policies
that the deficit is procedural rather than real, and would have to be chased.

    INTERVAL_MS=1400 python -m experiments.e16_heldout
    INTERVAL_MS=1400 NSHARD=6 SHARD=0 python -m experiments.e16_heldout
    INTERVAL_MS=1400 python -m experiments.e16_heldout merge
    INTERVAL_MS=1400 python -m experiments.e16_heldout report
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
INTERVAL_MS = float(os.environ.get("INTERVAL_MS", 1400.0))
MAX_DELAY_MS = float(os.environ.get("MAX_DELAY_MS", 1000.0))

# The finished experiment 11 run this reads its policies from.  Same naming
# rule as e11 itself, so the 600 ms default maps onto the original file.
_TAG = "" if INTERVAL_MS == 600.0 else f"_interval{int(INTERVAL_MS)}"
SOURCE = os.path.join(RESULTS, f"e11_delays_cap{int(MAX_DELAY_MS)}{_TAG}.json")
PATH = os.path.join(RESULTS, f"e16_heldout_interval{int(INTERVAL_MS)}.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

MIN_COUNTED = 20            # lane-correct is a ratio; experiment 6
NOISE = 0.03

# Three charts at seed 999, the seeds experiment 3 reserved.  The sweep in
# experiment 11 used two charts at seed 7030, so no chart is shared.  The
# interval follows the condition being replayed, because a policy tuned at
# 1400 ms has no business being scored at 600 ms.
HELD_OUT = dict(stage=3, n_charts=3, n_notes=20, seed=999)


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def chosen_policy(run: dict) -> dict:
    """The policy experiment 11's headline number actually used.

    ``best_accuracy`` there is a maximum over the theta sweep, so the threshold
    it implies is ``argmax(accuracy)`` -- not ``best_theta``, which is the
    lane-correctness argmax under the press guard and answers a different
    question.  Taking the wrong one would replay a policy that never produced
    the number being tested, so it is spelled out rather than assumed.
    """
    acc = np.asarray(run["accuracy"], dtype=float)
    i = int(np.argmax(acc))
    return {"theta": float(run["theta"][i]),
            "delays": [float(d) for d in run["delays"][i]],
            "sweep_accuracy": float(acc[i]),
            "sweep_index": i}


def measure(run: dict) -> dict:
    t0 = time.time()
    pol = chosen_policy(run)
    kw = {} if run["label"] == "real connectome" else {
        "shuffle_seed": int(run["label"].split("#")[1])}
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    # The wiring is taken from the stored run rather than re-derived from a
    # fresh silent probe.  It is deterministic given the network, but reading
    # it back guarantees the replayed policy is the one that was scored.
    W = np.zeros((4, 4))
    for lane, ch in enumerate(run["wiring"]):
        W[lane, ch] = 1.0
    ctrl = player.controller.copy()
    ctrl.W = W
    ctrl.b = np.full(4, -pol["theta"])
    player.controller = ctrl.with_delays(np.asarray(pol["delays"]))
    e = L.evaluate(player, interval_ms=INTERVAL_MS, **HELD_OUT)
    n_c = int(np.array(e["confusion"]).sum())
    out = {"label": run["label"], **pol,
           "accuracy": float(e["accuracy"]), "hit_rate": float(e["hit_rate"]),
           "stray_per_note": float(e["stray_per_note"]),
           "n_counted": n_c, "eligible": bool(n_c >= MIN_COUNTED),
           "lane_correct": (float(e["lane_correct"]) if n_c >= MIN_COUNTED else None),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {run['label']:<20s} th {pol['theta']:.1f}  "
          f"sweep {pol['sweep_accuracy']:.3f} -> held-out {out['accuracy']:.3f}  "
          f"lane " + ("-" if out["lane_correct"] is None else f"{out['lane_correct']:.3f}")
          + f"  presses {n_c}", flush=True)
    return out


def main():
    src = _load(SOURCE, None)
    if src is None:
        raise SystemExit(f"{SOURCE} not found; run experiment 11 at this interval first")
    res = _load(SHARD_PATH, {"interval_ms": INTERVAL_MS, "source": os.path.basename(SOURCE),
                             "held_out": dict(HELD_OUT, interval_ms=INTERVAL_MS), "runs": []})
    done = {r["label"] for r in res["runs"]}
    if SHARD is not None:
        done |= {r["label"] for r in _load(PATH, {"runs": []})["runs"]}
    plan = list(src["runs"])
    if SHARD is not None:
        plan = [r for i, r in enumerate(plan) if i % NSHARD == int(SHARD)]
    print(f"interval {INTERVAL_MS:.0f} ms -> {os.path.basename(SHARD_PATH)} "
          f"({len(done)} done, {len(plan)} planned)", flush=True)
    for run in plan:
        if run["label"] in done:
            continue
        res["runs"].append(measure(run))
        with open(SHARD_PATH, "w") as fh:
            json.dump(res, fh, indent=1)
    if SHARD is None:
        report(res)


def merge():
    res = _load(PATH, {"interval_ms": INTERVAL_MS, "source": os.path.basename(SOURCE),
                       "held_out": dict(HELD_OUT, interval_ms=INTERVAL_MS), "runs": []})
    seen = {r["label"] for r in res["runs"]}
    for f in sorted(glob.glob(PATH[:-5] + "_shard*of*.json")):
        got = _load(f, {"runs": []})
        if float(got.get("interval_ms", INTERVAL_MS)) != INTERVAL_MS:
            raise SystemExit(f"{f} holds a different interval; refusing to merge")
        for r in got["runs"]:
            if r["label"] not in seen:
                res["runs"].append(r); seen.add(r["label"])
        print(f"  {os.path.basename(f):<46s} {len(got['runs']):>2} runs")
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"merged -> {len(res['runs'])} networks")
    report(res)


def report(res):
    runs = {r["label"]: r for r in res["runs"]}
    real = runs.get("real connectome")
    ctl = [r for lbl, r in runs.items() if lbl.startswith("rewired")]
    if real is None or not ctl:
        print("need the real network and at least one control"); return
    n = len(ctl)
    print(f"\n=== experiment 16: held-out play, {res['interval_ms']:.0f} ms interval ===")
    print(f"  {n} rewired controls, one-sided p = (n_ge + 1)/(n + 1), floor {_p(0, n):.3f}")
    print("  policies frozen from experiment 11; nothing re-chosen here")

    sa = np.array([r["sweep_accuracy"] for r in ctl])
    ha = np.array([r["accuracy"] for r in ctl])
    rs, rh = real["sweep_accuracy"], real["accuracy"]
    nge = int((ha >= rh).sum())
    nge_s = int((sa >= rs).sum())
    print(f"\n  sweep (e11)    real {rs:.3f}   rewired {sa.mean():.3f} +- {sa.std(ddof=1):.3f}"
          f"   {nge_s}/{n} reach real   p {_p(nge_s, n):.3f}   gap {sa.mean() - rs:+.3f}")
    print(f"  held-out       real {rh:.3f}   rewired {ha.mean():.3f} +- {ha.std(ddof=1):.3f}"
          f"   {nge}/{n} reach real   p {_p(nge, n):.3f}   gap {ha.mean() - rh:+.3f}")
    print(f"  drop           real {rh - rs:+.3f}   rewired {(ha - sa).mean():+.3f}"
          f" +- {(ha - sa).std(ddof=1):.3f}")

    bad = [r["label"] for r in ctl + [real] if not r["eligible"]]
    if bad:
        print(f"  !! press guard never met (lane-correct undefined, dropped): {', '.join(bad)}")
    lcs = np.array([r["lane_correct"] for r in ctl if r["lane_correct"] is not None])
    if real["lane_correct"] is None:
        print("  lane-correct   real -  (press guard never met)")
    elif len(lcs):
        m = int((lcs >= real["lane_correct"]).sum())
        print(f"  lane-correct   real {real['lane_correct']:.3f}   rewired {lcs.mean():.3f}"
              f" +- {lcs.std(ddof=1):.3f}   {m}/{len(lcs)} reach real   p {_p(m, len(lcs)):.3f}")

    res["summary"] = {
        "n": n, "real_sweep": rs, "real_heldout": rh,
        "ctl_sweep_mean": float(sa.mean()), "ctl_heldout_mean": float(ha.mean()),
        "ctl_heldout_sd": float(ha.std(ddof=1)),
        "n_ge_sweep": nge_s, "p_sweep": _p(nge_s, n),
        "n_ge_heldout": nge, "p_heldout": _p(nge, n),
        "gap_sweep": float(sa.mean() - rs), "gap_heldout": float(ha.mean() - rh),
        "real_drop": float(rh - rs), "ctl_drop_mean": float((ha - sa).mean())}
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "report":
        report(_load(PATH, {"runs": []}))
    elif cmd == "merge":
        merge()
    else:
        main()
