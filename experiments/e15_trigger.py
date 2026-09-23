"""
Experiment 15 -- move the press later without paying for it.

Experiment 12 ended on one observation worth chasing.  At a wide note interval
the real connectome's lane-correctness *without any delays* is 1.000 against the
controls' 0.56 -- it picks the right key almost every time and simply presses
too early to score -- and the per-key delay fix of experiment 11 then trades
that away, costing it 0.355 of lane-correctness while lifting the controls.

Per-key delays are also the most expensive thing the untrained policy declares:
four numbers read off a silent probe, on top of the wiring permutation.  The two
triggers tested here cost **nothing extra**.  They reuse the same wiring and the
same threshold and only change *which edge of the drive fires the key*:

    cross   the drive crosses threshold upward      (every prior experiment)
    peak    the drive turns over while still above  (the channel's own peak)
    fall    the drive falls back below threshold

On a single bump these fire in that order, so both alternatives move the press
later than the crossing, which is the direction experiment 8 said was needed.

The question is not whether they beat the delays on absolute accuracy.  It is
whether the real connectome's ranking against its controls improves when the
timing is fixed by a mechanism that does not discard its lane choice.  Every
behavioural comparison in this project currently fails to favour the real
connectome; this is a test of whether that is a fact about the connectome or a
fact about the controller we have been giving it.

**Prediction, recorded before the numbers.**  If the real network's early,
accurate lane choice is a genuine property and the delays were destroying it,
then under `peak` or `fall` its lane-correctness should stay near its no-delay
value (1.000 at 1400 ms) while its accuracy rises toward its delayed value
(0.454), and its rank should improve on the 18-19/20 that delays produce.  If
instead it lands where the delays left it, the early lane choice was never
worth anything and the controller is not what is holding it back.

    INTERVAL_MS=1400 N_SEEDS=20 python -m experiments.e15_trigger
    INTERVAL_MS=1400 NSHARD=6 SHARD=0 python -m experiments.e15_trigger
    INTERVAL_MS=1400 python -m experiments.e15_trigger merge
    INTERVAL_MS=1400 python -m experiments.e15_trigger report
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, probes as PR  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
INTERVAL_MS = float(os.environ.get("INTERVAL_MS", 1400.0))
PATH = os.path.join(RESULTS, f"e15_trigger_interval{int(INTERVAL_MS)}.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

TRIGGERS = ("cross", "peak", "fall")
THETA_SWEEP = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
SWEEP_STAGE = 3
MIN_COUNTED = 20            # lane-correct is a ratio; experiment 6
NOISE = 0.03


def measure(label: str, kw: dict) -> dict:
    """One network, every trigger, swept over theta.

    Wiring is `band_assignment` from this network's own silent probe, exactly as
    in experiments 7, 11 and 12, so nothing here is inherited from the real
    network and the only thing that changes between arms is the firing edge.
    """
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    tr = PR.lane_traces(fly, player.norm, player.r0)
    wiring = PR.band_assignment(tr)
    W = np.zeros((4, 4))
    for lane, ch in enumerate(wiring):
        W[lane, ch] = 1.0
    out = {"label": label, "wiring": list(wiring), "theta": list(THETA_SWEEP), "arms": {}}
    for trig in TRIGGERS:
        lc, acc, n = [], [], []
        for th in THETA_SWEEP:
            ctrl = player.controller.copy()
            ctrl.W = W.copy()
            ctrl.b = np.full(4, -float(th))
            ctrl.trigger = trig
            ctrl.delay_ms = None
            player.controller = ctrl
            e = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                           interval_ms=INTERVAL_MS, seed=7000 + 10 * SWEEP_STAGE)
            lc.append(e["lane_correct"]); acc.append(e["accuracy"])
            n.append(int(np.array(e["confusion"]).sum()))
        ok = np.array(n) >= MIN_COUNTED
        i = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
        out["arms"][trig] = {
            "lane_correct": lc, "accuracy": acc, "n_counted": n,
            "eligible": ok.tolist(), "any_eligible": bool(ok.any()),
            "best_theta": float(THETA_SWEEP[i]),
            "lane_correct_guarded": (float(lc[i]) if ok.any() else None),
            "best_accuracy": float(max(acc))}
        b = out["arms"][trig]
        print(f"  {label:<20s} {trig:<6s} acc {b['best_accuracy']:.3f}  "
              f"lane {'-' if b['lane_correct_guarded'] is None else format(b['lane_correct_guarded'], '.3f')}"
              f" @th {b['best_theta']:.1f}  counted {n}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def main():
    n = int(os.environ.get("N_SEEDS", 20))
    res = _load(SHARD_PATH, {"interval_ms": INTERVAL_MS, "triggers": list(TRIGGERS),
                             "theta": list(THETA_SWEEP), "runs": []})
    done = {r["label"] for r in res["runs"]}
    if SHARD is not None:
        done |= {r["label"] for r in _load(PATH, {"runs": []})["runs"]}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    if SHARD is not None:
        plan = [pk for i, pk in enumerate(plan) if i % NSHARD == int(SHARD)]
    print(f"interval {INTERVAL_MS:.0f} ms -> {os.path.basename(SHARD_PATH)} "
          f"({len(done)} done)", flush=True)
    for label, kw in plan:
        if label in done:
            continue
        res["runs"].append(measure(label, kw))
        with open(SHARD_PATH, "w") as fh:
            json.dump(res, fh, indent=1)
    if SHARD is None:
        report(res)


def merge():
    res = _load(PATH, {"interval_ms": INTERVAL_MS, "triggers": list(TRIGGERS),
                       "theta": list(THETA_SWEEP), "runs": []})
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


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def report(res):
    runs = {r["label"]: r for r in res["runs"]}
    real = runs.get("real connectome")
    ctl = [r for lbl, r in runs.items() if lbl.startswith("rewired")]
    if real is None or not ctl:
        print("need the real network and at least one control"); return
    n = len(ctl)
    print(f"\n=== experiment 15: firing edge, {res['interval_ms']:.0f} ms interval ===")
    print(f"  {n} rewired controls, one-sided p = (n_ge + 1)/(n + 1), floor {_p(0, n):.3f}")
    print(f"  {len(TRIGGERS)} arms on the same networks: Bonferroni floor {len(TRIGGERS) * _p(0, n):.3f}")
    bad = [f"{r['label']}/{t}" for r in ctl + [real] for t in TRIGGERS
           if not r["arms"][t]["any_eligible"]]
    if bad:
        print(f"  !! press guard never met (lane-correct undefined, dropped): {', '.join(bad)}")
    summary = {}
    for t in TRIGGERS:
        a = np.array([r["arms"][t]["best_accuracy"] for r in ctl])
        ra = real["arms"][t]["best_accuracy"]
        nge = int((a >= ra).sum())
        lcs = [r["arms"][t]["lane_correct_guarded"] for r in ctl]
        lcs = np.array([v for v in lcs if v is not None])
        rlc = real["arms"][t]["lane_correct_guarded"]
        print(f"\n  {t}")
        print(f"    accuracy       real {ra:.3f}   rewired {a.mean():.3f} +- {a.std(ddof=1):.3f}"
              f"   {nge}/{n} reach real   p {_p(nge, n):.3f}")
        if rlc is None:
            print("    lane-correct   real -  (press guard never met)")
        else:
            m = int((lcs >= rlc).sum())
            print(f"    lane-correct   real {rlc:.3f}   rewired {lcs.mean():.3f} +- {lcs.std(ddof=1):.3f}"
                  f"   {m}/{len(lcs)} reach real   p {_p(m, len(lcs)):.3f}")
        summary[t] = {"real_accuracy": float(ra), "ctl_accuracy_mean": float(a.mean()),
                      "n_ge": nge, "n": n, "p": _p(nge, n),
                      "real_lane_correct": rlc}
    res["summary"] = summary
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
