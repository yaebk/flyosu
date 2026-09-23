"""
Experiment 19 -- pre-registered: the stray test again, with the ties broken.

**Read this first: this is a second run of an endpoint that already failed, and
that needs justifying rather than assuming.**  Experiment 17 pre-registered
strays per note, got p = 0.073 against a Bonferroni floor of 0.049, and failed.
Running a failed test again until it passes is the oldest way to fake a result.
The reason this is not that:

Experiment 17's failure had a single identifiable cause that has nothing to do
with the direction of the effect.  Its charts were 5 x 20 = 100 notes, so
strays per note could only take values k/100.  The real connectome scored
0.220 -- exactly 22 strays -- and **two of the forty controls scored exactly
0.220 as well**.  Ties count against the hypothesis here as everywhere else in
this project, so those two ties alone took n_ge from 0 to 2 and p from 0.024 to
0.073.  With a strict inequality it would have read 0/40.  The fix is not a
different rule, which would be choosing the rule after seeing which way it cut;
it is **more notes**, so that the measure is fine-grained enough for exact ties
to be vanishingly unlikely.  This run uses 20 x 20 = 400 notes, a granularity
of 0.0025 against 0.010.

**Why this endpoint and not accuracy.**  The obvious experiment 19 was to make
accuracy-under-a-declared-threshold the primary, since experiment 17 found the
deficit gone there.  That experiment is futile and should not be run.  A
permutation test against rewired controls can only reach p < 0.05 if the real
network beats 38 of 40 -- the 95th percentile of the control distribution.
Where experiment 17 actually put it:

    endpoint          real    ctl mean    SD above    rank     percentile
    accuracy         0.357       0.299       +0.30    14/40        65%
    reward           0.346       0.262       +0.43    14/40        65%
    hit rate         0.620       0.381       +1.04     6/40        85%
    strays/note      0.220       0.743       +1.45     2/40        95%

The real connectome is a single draw, so this is a fact about effect size, not
about sample size: **more controls make p converge to the true quantile, not to
zero.**  At the 65th percentile accuracy cannot reach significance with any
number of controls, and no amount of compute changes that.  Strays is the only
behavioural endpoint at the boundary, and it is the only one worth powering.

**Policy -- identical to experiment 17, nothing re-chosen.**  Wiring from each
network's own silent probe; theta declared at 1.5, the never-fitted default;
per-key delays from that same probe at that theta, cap 1000 ms.  No chart
chooses any number.

**Charts.**  Stage 3, twenty charts of 20 notes at a 1400 ms interval, seed
20270418 -- never used anywhere in this project, and different from experiment
17's 20260923, so this is a genuinely fresh measurement rather than a re-read
of the same one.

**Primary endpoint, one only, floor 1/41 = 0.024.**  Strays per note, one-sided,
real *lower*, among networks clearing the activity guard of 20 presses near a
note.  A single primary, because experiment 17's two co-primaries cost it a
factor of two in the floor and the reward endpoint was never close.

**Declared sensitivity, as in experiment 17:** the same comparison over all 40
controls regardless of the guard, because the guard removes inactive networks
and inactive networks make few strays, which flatters whoever is tested.  If
the two disagree the write-up reports the disagreement.

**Secondary, reported without inference:** accuracy, hit rate, reward, and the
count of exact ties at the real network's value -- that last one so the
tie-breaking premise of this experiment can be checked rather than assumed.

**Prediction, recorded before the numbers.**  The direction replicates and the
ties mostly vanish: the real connectome makes fewer strays than at least 38 of
the 40 controls, with at most one exact tie, and p lands at or just above 0.024.
I am not confident it passes -- the two networks it tied were *equal* to it, not
worse, so at finer granularity they are close to a coin flip either way, and
0/40 and 2/40 are both entirely plausible.

**Stopping rule.**  If this fails, the stray endpoint is finished and must not
be run a third time.  Two pre-registered failures is an answer.

**The freeze.**  ``controls`` must finish and be committed before ``real`` will
run; ``real`` refuses to overwrite an existing measurement.

    NSHARD=6 SHARD=0 python -m experiments.e19_strays_powered controls
    python -m experiments.e19_strays_powered merge
    python -m experiments.e19_strays_powered real
    python -m experiments.e19_strays_powered report
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
PATH = os.path.join(RESULTS, "e19_strays_powered.json")
SHARD = os.environ.get("SHARD")
NSHARD = int(os.environ.get("NSHARD", 1))
SHARD_PATH = PATH if SHARD is None else PATH[:-5] + f"_shard{int(SHARD)}of{NSHARD}.json"

N_CONTROLS = 40
THETA = 1.5                 # declared, not swept; Player.untrained's default
MIN_COUNTED = 20            # activity guard; experiment 6
NOISE = 0.03
STRAY_PENALTY = L.STRAY_PENALTY
# Four times experiment 17's notes: 400 instead of 100, so strays per note has a
# granularity of 0.0025 rather than 0.010 and exact ties become unlikely.
CHARTS = dict(stage=3, n_charts=20, n_notes=20, interval_ms=1400.0, seed=20270418)


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
    n_notes = CHARTS["n_charts"] * CHARTS["n_notes"]
    out = {"label": label, "wiring": list(wiring), "theta": THETA,
           "delays": [float(d) for d in delays],
           "accuracy": float(e["accuracy"]), "hit_rate": float(e["hit_rate"]),
           "stray_per_note": float(e["stray_per_note"]),
           "n_strays": int(round(e["stray_per_note"] * n_notes)),
           "reward": float(e["accuracy"] - STRAY_PENALTY * e["stray_per_note"]),
           "n_counted": n_c, "eligible": bool(n_c >= MIN_COUNTED),
           "lane_correct": (float(e["lane_correct"]) if n_c >= MIN_COUNTED else None),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<20s} stray/note {out['stray_per_note']:.4f} "
          f"({out['n_strays']}/{n_notes})  acc {out['accuracy']:.3f}  "
          f"hit {out['hit_rate']:.3f}  presses {n_c}"
          f"{'' if out['eligible'] else ' (GUARD FAIL)'}", flush=True)
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
        if got.get("charts") != CHARTS or got.get("theta") != THETA:
            raise SystemExit(f"{f} holds a different condition; refusing to merge")
        for r in got["runs"]:
            if r["label"] not in seen:
                res["runs"].append(r); seen.add(r["label"])
        print(f"  {os.path.basename(f):<44s} {len(got['runs']):>2} runs")
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)
    n = len([r for r in res["runs"] if r["label"].startswith("rewired")])
    print(f"merged -> {n}/{N_CONTROLS} controls")


def report(res):
    runs = {r["label"]: r for r in res["runs"]}
    real = runs.get("real connectome")
    ctl = [r for lbl, r in runs.items() if lbl.startswith("rewired")]
    n = len(ctl)
    print("\n=== experiment 19: strays, powered, pre-registered ===")
    print(f"  theta {THETA} declared; {CHARTS['n_charts']} charts x {CHARTS['n_notes']} "
          f"notes = {CHARTS['n_charts'] * CHARTS['n_notes']} notes at "
          f"{CHARTS['interval_ms']:.0f} ms, seed {CHARTS['seed']}")
    print(f"  {n} rewired controls; one primary endpoint; floor {_p(0, n):.3f}")
    if real is None:
        print("  real network not yet measured (the freeze)"); return

    bad = [r["label"] for r in ctl + [real] if not r["eligible"]]
    if bad:
        print(f"  !! activity guard failed: {', '.join(bad)}")
    rv = real["stray_per_note"]
    print("\n  PRIMARY")
    if not real["eligible"]:
        print("  VOID: the real network never reaches the activity guard")
    else:
        for name, pool in (("guarded", [r for r in ctl if r["eligible"]]),
                           ("all 40 (sensitivity)", ctl)):
            a = np.array([r["stray_per_note"] for r in pool])
            nge = int((a <= rv).sum())
            print(f"  stray/note {name:<22s} real {rv:.4f}   rewired {a.mean():.4f} "
                  f"+- {a.std(ddof=1):.4f}   {nge}/{len(a)} below   p {_p(nge, len(a)):.3f}")
        ties = int(sum(1 for r in ctl if r["n_strays"] == real["n_strays"]))
        print(f"  exact ties at the real network's {real['n_strays']} strays: {ties}"
              f"   (experiment 17 had 2, which is why this run exists)")

    print("\n  SECONDARY (descriptive, no inference claimed)")
    for k in ("accuracy", "hit_rate", "reward"):
        a = np.array([r[k] for r in ctl])
        print(f"  {k:<12s} real {real[k]:.3f}   rewired {a.mean():.3f} +- {a.std(ddof=1):.3f}"
              f"   {int((a >= real[k]).sum())}/{n} reach real"
              f"   ({(real[k] - a.mean()) / a.std(ddof=1):+.2f} SD)")
    res["summary"] = {"real_stray": rv, "n": n,
                      "n_ge_guarded": int(sum(1 for r in ctl if r["eligible"]
                                              and r["stray_per_note"] <= rv)),
                      "n_ge_all": int(sum(1 for r in ctl if r["stray_per_note"] <= rv))}
    with open(PATH, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "controls":
        run_controls()
    elif cmd == "real":
        run_real()
    elif cmd == "merge":
        merge()
    elif cmd == "report":
        report(_load(PATH, _fresh()))
    else:
        raise SystemExit("commands: controls | merge | real | report")
