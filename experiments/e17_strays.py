"""
Experiment 17 -- pre-registered: does the real connectome press less junk?

Experiment 16 found, after its own numbers were in, that ``accuracy`` in
``mania.py`` is a weighted mean over *notes* and is completely blind to presses
that land on nothing.  Held out at 1400 ms the twenty rewired controls made
2.21 stray presses per note against the real network's 0.48, with all twenty
worse and no overlap at all, while the real network's hit rate was above their
mean.  That was a discovery, not a test, and `docs/RESULTS_E16.md` says so.

This is the test.  Endpoints, controls, charts, threshold and the stopping rule
are all fixed here before anything is measured, in the manner of
`docs/PREREGISTRATION.md`, and the controls are run and committed before the
real network so there is no distribution to tune against.

**The threshold is declared, not swept, and that is the substantive change.**
Experiment 16 showed the sweep was selecting for mashing: accuracy cannot see
strays, so pressing more can only help it, and the accuracy-maximising theta
was the *lowest* value offered (0.5) for the real network and for 19 of the 20
controls.  Every "best threshold" this project has quoted was therefore partly
a measurement of that blindness.  Here theta is 1.5 -- the default in
``Player.untrained``, used since experiment 1 and never fitted to anything --
so no chart chooses any number.

**Policy (zero parameters chosen on any chart).**  Wiring from each network's
own silent probe via ``band_assignment``; theta = 1.5 declared; per-key delays
from that same probe at that theta via experiment 11's ``delays_from_probe``,
cap 1000 ms, which cannot bind because the probe is only 800 ms long.

**Charts.**  Stage 3, five charts of 20 notes at a 1400 ms interval, seed
20260923.  That seed has never been used anywhere in this project -- the sweeps
use 7030 and the held-out sets use 999 -- so nothing here has been seen by any
network or by me.

**Co-primary endpoints, Bonferroni over two (floor 2/41 = 0.049 at n = 40).**

1. ``reward`` = accuracy - 0.05 * strays-per-note, the project's declared
   evaluation rule (``learn.STRAY_PENALTY``).  One-sided, real *higher*.
   Experiment 16 measured this at 0.545 against 0.582, p = 0.571, so it is
   genuinely open.  The constant is 0.05 because that is what the codebase
   declares; experiment 16 deliberately refused to use the 0.4 ridge-fitting
   constant that would have separated them, because it was chosen after the
   fact.

2. ``stray_per_note``, one-sided, real *lower*, among networks that clear the
   activity guard.

**The activity guard.**  A network that never presses has zero strays and would
win endpoint 2 by refusing to play; this project has already emitted phantom
numbers three times from exactly that degeneracy.  So endpoint 2 is computed
only over networks reaching ``MIN_COUNTED`` = 20 presses near a note, the same
constant experiment 6 introduced and every experiment since has used, and every
excluded network is named in the report.  If the real network itself fails the
guard, endpoint 2 is declared void rather than scored.

**Declared sensitivity analysis, and why it is here.**  A three-control pilot
was run before this docstring was frozen, to check the guard was not
degenerate at theta = 1.5.  It was not -- but one of the three controls made no
press near any note while still producing 0.48 strays per note, which exposes a
bias the guard introduces: excluded networks are inactive ones, inactive
networks tend to have *few* strays, and dropping them therefore removes
low-stray competitors and flatters whichever network is being tested.  So
endpoint 2 is reported twice, guarded (primary, as declared above) and over all
40 controls regardless of activity (sensitivity).  Both are declared here,
before the real network is built; if they disagree, the write-up reports the
disagreement rather than the friendlier of the two.  The pilot touched controls
only and its numbers are not written to the result file.

**Secondary, reported without inference:** accuracy, hit rate, lane-correctness
under the same guard.  These are descriptive; no p is claimed for them.

**Prediction, recorded before the numbers.**  Endpoint 2 replicates: the real
connectome makes fewer strays per note than at least 38 of the 40 controls.
Endpoint 1 does not reach the Bonferroni floor, because 0.05 is far too weak a
penalty to convert a 1.7-stray difference into the ~0.12 accuracy the controls
are ahead by -- 1.7 * 0.05 is 0.085, which does not close it.  If that is right
then the honest summary of the project becomes "the real connectome plays more
sparingly and no better", and the declared scoring rule does not reward
sparingness enough to show it.

**The freeze.**  ``controls`` must finish and be committed before ``real`` will
run; ``real`` refuses to overwrite an existing measurement.  ``pilot`` runs
three controls only, to check the activity guard is not degenerate, and never
touches the real network.

    NSHARD=6 SHARD=0 python -m experiments.e17_strays controls
    python -m experiments.e17_strays merge
    python -m experiments.e17_strays real
    python -m experiments.e17_strays report
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
from experiments.e11_delays import delays_from_probe  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e17_strays.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

N_CONTROLS = 40
THETA = 1.5                 # declared, not swept; Player.untrained's default
MIN_COUNTED = 20            # activity guard; experiment 6
NOISE = 0.03
STRAY_PENALTY = L.STRAY_PENALTY          # 0.05, the declared evaluation rule
CHARTS = dict(stage=3, n_charts=5, n_notes=20, interval_ms=1400.0, seed=20260923)


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def measure(label: str, kw: dict) -> dict:
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    tr = PR.lane_traces(fly, player.norm, player.r0)
    wiring = PR.band_assignment(tr)
    W = np.zeros((4, 4))
    for lane, ch in enumerate(wiring):
        W[lane, ch] = 1.0
    ctrl = player.controller.copy()
    ctrl.W = W
    ctrl.b = np.full(4, -THETA)
    delays = delays_from_probe(tr, wiring, THETA)
    player.controller = ctrl.with_delays(delays)
    e = L.evaluate(player, **CHARTS)
    n_c = int(np.array(e["confusion"]).sum())
    out = {"label": label, "wiring": list(wiring), "theta": THETA,
           "delays": [float(d) for d in delays],
           "accuracy": float(e["accuracy"]), "hit_rate": float(e["hit_rate"]),
           "stray_per_note": float(e["stray_per_note"]),
           "reward": float(e["accuracy"] - STRAY_PENALTY * e["stray_per_note"]),
           "n_counted": n_c, "eligible": bool(n_c >= MIN_COUNTED),
           "lane_correct": (float(e["lane_correct"]) if n_c >= MIN_COUNTED else None),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<20s} acc {out['accuracy']:.3f}  hit {out['hit_rate']:.3f}  "
          f"stray/note {out['stray_per_note']:.3f}  reward {out['reward']:+.3f}  "
          f"presses {n_c}{'' if out['eligible'] else ' (GUARD FAIL)'}", flush=True)
    return out


def _fresh():
    return {"theta": THETA, "charts": CHARTS, "stray_penalty": STRAY_PENALTY,
            "min_counted": MIN_COUNTED, "n_controls": N_CONTROLS, "runs": []}


def run_controls():
    res = _load(SHARD_PATH, _fresh())
    done = {r["label"] for r in res["runs"]}
    if SHARD is not None:
        done |= {r["label"] for r in _load(PATH, {"runs": []})["runs"]}
    plan = [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, N_CONTROLS + 1)]
    if SHARD is not None:
        plan = [pk for i, pk in enumerate(plan) if i % NSHARD == int(SHARD)]
    print(f"controls -> {os.path.basename(SHARD_PATH)} "
          f"({len(done)} done, {len(plan)} planned)", flush=True)
    for label, kw in plan:
        if label in done:
            continue
        res["runs"].append(measure(label, kw))
        with open(SHARD_PATH, "w") as fh:
            json.dump(res, fh, indent=1)


def run_pilot():
    """Three controls only, to check the activity guard is not degenerate.

    This never builds the real network, so it cannot leak the quantity the
    experiment is about.  Its output is not written to PATH.
    """
    print("pilot: three controls, checking the activity guard", flush=True)
    for s in (1, 2, 3):
        measure(f"rewired #{s}", {"shuffle_seed": s})


def run_real():
    res = _load(PATH, None)
    ctl = [] if res is None else [r for r in res["runs"] if r["label"].startswith("rewired")]
    if len(ctl) < N_CONTROLS:
        raise SystemExit(f"the freeze: {len(ctl)}/{N_CONTROLS} controls measured; "
                         "finish and commit the controls before the real network")
    if any(r["label"] == "real connectome" for r in res["runs"]):
        raise SystemExit("the real network is already measured; refusing to overwrite")
    res["runs"].append(measure("real connectome", {}))
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    report(res)


def merge():
    res = _load(PATH, _fresh())
    seen = {r["label"] for r in res["runs"]}
    for f in sorted(glob.glob(PATH[:-5] + "_shard*of*.json")):
        got = _load(f, {"runs": []})
        if got.get("theta") != THETA or got.get("charts") != CHARTS:
            raise SystemExit(f"{f} holds a different condition; refusing to merge")
        for r in got["runs"]:
            if r["label"] not in seen:
                res["runs"].append(r); seen.add(r["label"])
        print(f"  {os.path.basename(f):<40s} {len(got['runs']):>2} runs")
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    n = len([r for r in res["runs"] if r["label"].startswith("rewired")])
    print(f"merged -> {n}/{N_CONTROLS} controls")


def report(res):
    runs = {r["label"]: r for r in res["runs"]}
    real = runs.get("real connectome")
    ctl = [r for lbl, r in runs.items() if lbl.startswith("rewired")]
    n = len(ctl)
    print(f"\n=== experiment 17: strays, pre-registered ===")
    print(f"  theta {THETA} declared; {CHARTS['n_charts']} charts x {CHARTS['n_notes']} "
          f"notes at {CHARTS['interval_ms']:.0f} ms, seed {CHARTS['seed']}")
    print(f"  {n} rewired controls; one-sided p floor {_p(0, n):.3f}, "
          f"two co-primaries -> Bonferroni floor {2 * _p(0, n):.3f}")
    if real is None:
        print("  real network not yet measured (the freeze)"); return

    def line(key, lower_is_better, arr, rv, label):
        nge = int((arr <= rv).sum()) if lower_is_better else int((arr >= rv).sum())
        print(f"  {label:<16s} real {rv:+.3f}   rewired {arr.mean():+.3f} "
              f"+- {arr.std(ddof=1):.3f}   {nge}/{len(arr)} {'below' if lower_is_better else 'reach'}"
              f" real   p {_p(nge, len(arr)):.3f}")
        return {"real": float(rv), "ctl_mean": float(arr.mean()),
                "ctl_sd": float(arr.std(ddof=1)), "n_ge": nge, "n": len(arr),
                "p": _p(nge, len(arr))}

    summary = {}
    print("\n  CO-PRIMARY")
    summary["reward"] = line("reward", False,
                             np.array([r["reward"] for r in ctl]), real["reward"],
                             "reward @0.05")
    bad = [r["label"] for r in ctl + [real] if not r["eligible"]]
    if bad:
        print(f"  !! activity guard failed ({MIN_COUNTED} presses): {', '.join(bad)}")
    if not real["eligible"]:
        print("  stray endpoint VOID: the real network never reaches the activity guard")
        summary["stray_per_note"] = None
    else:
        ok = np.array([r["stray_per_note"] for r in ctl if r["eligible"]])
        summary["stray_per_note"] = line("stray_per_note", True, ok,
                                         real["stray_per_note"], "stray/note")
        print("\n  DECLARED SENSITIVITY (guard dropped; inactive controls make few "
              "strays, so\n  excluding them flatters whoever is being tested)")
        allc = np.array([r["stray_per_note"] for r in ctl])
        summary["stray_per_note_unguarded"] = line(
            "stray_per_note", True, allc, real["stray_per_note"], "stray/note all")

    print("\n  SECONDARY (descriptive, no inference claimed)")
    for k in ("accuracy", "hit_rate"):
        a = np.array([r[k] for r in ctl])
        print(f"  {k:<16s} real {real[k]:.3f}   rewired {a.mean():.3f} +- {a.std(ddof=1):.3f}"
              f"   {int((a >= real[k]).sum())}/{n} reach real")
    lcs = np.array([r["lane_correct"] for r in ctl if r["lane_correct"] is not None])
    if real["lane_correct"] is not None and len(lcs):
        print(f"  {'lane_correct':<16s} real {real['lane_correct']:.3f}   "
              f"rewired {lcs.mean():.3f} +- {lcs.std(ddof=1):.3f}   "
              f"{int((lcs >= real['lane_correct']).sum())}/{len(lcs)} reach real")
    res["summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "controls":
        run_controls()
    elif cmd == "pilot":
        run_pilot()
    elif cmd == "real":
        run_real()
    elif cmd == "merge":
        merge()
    elif cmd == "report":
        report(_load(PATH, _fresh()))
    else:
        raise SystemExit(__doc__.strip().splitlines()[-4].strip())
