"""
Experiment 14 -- the pre-registered comparison.

Read ``docs/PREREGISTRATION.md`` first.  This script is committed in the same
state as that document, before any network was run, and its contents are part
of the freeze: the protocol in section 5 and the analysis in section 6 are
implemented here and nowhere else.

The design device is the *ordering*.  Every earlier experiment here measured
the real connectome and its controls together, which leaves room -- however
carefully one behaves -- for a procedure to be adjusted while the real
network's numbers are visible.  Seven times in this project a gap shrank once
someone noticed such an adjustment after the fact.  So:

    python -m experiments.e14_prereg controls     # all 40, writes the null
    python -m experiments.e14_prereg real         # refuses unless 40 are done
    python -m experiments.e14_prereg report

The real network cannot be run until the full control distribution exists and
is committed.  After that point the null is fixed and public, and no procedure
can be tuned to favour the real network using numbers that do not yet exist.

The endpoint is ``probes.selectivity(...)["argmax_mean"]``: how often each
lane's wired channel is the largest of the four during that lane's note,
averaged over lanes.  It is label-free, threshold-free and press-free, so it
cannot inherit experiment 6's threshold error or experiment 7's press-count
degeneracy.  At 1/20 it stood at p = 0.095; at n = 40 the floor is 0.024, so
this design can confirm it below 0.05 or refute it.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import model as M, play as P, probes as PR  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
CONTROLS = os.path.join(RESULTS, "e14_prereg_controls.json")
REAL = os.path.join(RESULTS, "e14_prereg_real.json")
RETINO = os.path.join(RESULTS, "e14_prereg_retino.json")

# --- frozen protocol (docs/PREREGISTRATION.md section 5) ---------------------
DATASET = "flywire"
N_CONTROLS = 40
HIT_MS = (-160.0, 160.0)
FALSE_SCOPE = "window"
APPROACH_MS = 800.0
# ----------------------------------------------------------------------------


def endpoint(label: str, kw: dict) -> dict:
    """One network's primary endpoint, plus the declared secondaries.

    Wiring is derived from this network's own probe.  No control inherits the
    real network's permutation -- the rule experiments 6 and 7 were breaking.
    """
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    # theta is not a parameter of this endpoint: argmax_mean and
    # band_assignment are both threshold-free.  The default is used and
    # never swept.
    player = P.Player.untrained(fly)
    tr = PR.lane_traces(fly, player.norm, player.r0, approach_ms=APPROACH_MS)
    wiring = PR.band_assignment(tr, hit_ms=HIT_MS, false_scope=FALSE_SCOPE)
    sel = PR.selectivity(tr, wiring, hit_ms=HIT_MS)
    st = fly.stability(player.r0)
    out = {"label": label, "wiring": list(wiring),
           "argmax_mean": float(sel["argmax_mean"]),
           "argmax_fraction": [float(v) for v in sel["argmax_fraction"]],
           "peak_margin_mean": float(sel["peak_margin_mean"]),
           "drift": float(st["drift"]), "fixed_point": bool(st["fixed_point"]),
           "spectral_radius": float(st["spectral_radius"]),
           "seconds": round(time.time() - t0, 1)}
    print(f"  {label:<20s} argmax {out['argmax_mean']:.3f}  "
          f"margin {out['peak_margin_mean']:+.2f}  wiring {wiring}  "
          f"drift {out['drift']:.1e}  ({out['seconds']:.0f}s)", flush=True)
    return out


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def run_controls():
    res = _load(CONTROLS, {"protocol": "docs/PREREGISTRATION.md", "runs": []})
    done = {r["label"] for r in res["runs"]}
    for s in range(1, N_CONTROLS + 1):
        label = f"rewired #{s}"
        if label in done:
            continue
        res["runs"].append(endpoint(label, {"shuffle_seed": s}))
        with open(CONTROLS, "w") as fh:
            json.dump(res, fh, indent=1)
    print(f"\n{len(res['runs'])}/{N_CONTROLS} controls done.")
    if len(res["runs"]) == N_CONTROLS:
        v = np.array([r["argmax_mean"] for r in res["runs"]])
        print(f"null: mean {v.mean():.3f}  sd {v.std(ddof=1):.3f}  "
              f"min {v.min():.3f}  max {v.max():.3f}")
        print("Commit this file before running the real network.")


def run_retino():
    """Declared secondary (section 4): the retinotopy-shuffled family, n = 20.

    Run after the primary reported, which is logged as a deviation in section 9
    of the pre-registration.  Reported with a multiplicity warning and not
    eligible for promotion to primary under any outcome.
    """
    res = _load(RETINO, {"protocol": "docs/PREREGISTRATION.md (secondary)", "runs": []})
    done = {r["label"] for r in res["runs"]}
    for k in range(1, 21):
        label = f"retino #{k}"
        if label in done:
            continue
        res["runs"].append(endpoint(label, {"retino_seed": k}))
        with open(RETINO, "w") as fh:
            json.dump(res, fh, indent=1)
    print(f"\n{len(res['runs'])}/20 retinotopy-shuffled done.")


def run_real():
    """Guarded: the null must be complete first (section 7 of the freeze)."""
    res = _load(CONTROLS, {"runs": []})
    if len(res["runs"]) < N_CONTROLS:
        sys.exit(f"refusing: {len(res['runs'])}/{N_CONTROLS} controls done. "
                 "The pre-registration requires the full null distribution to "
                 "exist and be committed before the real network is measured.")
    if os.path.exists(REAL):
        sys.exit(f"refusing: {REAL} already exists. The real network is "
                 "measured once. Delete it deliberately if you mean to.")
    out = endpoint("real connectome", {})
    with open(REAL, "w") as fh:
        json.dump(out, fh, indent=1)


def report():
    ctl = _load(CONTROLS, {"runs": []})["runs"]
    if not ctl:
        sys.exit("no controls yet")
    v = np.array([r["argmax_mean"] for r in ctl])
    n = len(v)
    print(f"\ncontrols (rewired, n = {n})")
    print(f"  argmax_mean  {v.mean():.3f} +- {v.std(ddof=1):.3f}   "
          f"min {v.min():.3f}  max {v.max():.3f}")
    bad = [r["label"] for r in ctl if not r["fixed_point"]]
    if bad:
        print(f"  !! blank field not a fixed point for: {', '.join(bad)} "
              "(reported and KEPT -- no control is excluded)")
    if not os.path.exists(REAL):
        print("\nreal network not yet measured (by design).")
        return
    real = _load(REAL, {})
    r = real["argmax_mean"]
    n_ge = int((v >= r).sum())
    p = (n_ge + 1) / (n + 1)
    sd = v.std(ddof=1)
    print(f"\nreal connectome  argmax_mean {r:.3f}   "
          f"({(r - v.mean()) / sd:+.1f} SD)")
    print(f"  n >= real  {n_ge}/{n}    p = {p:.3f}   (floor {1 / (n + 1):.3f})")
    print(f"  control max {v.max():.3f} vs real {r:.3f} -- "
          f"{'distributions do not approach' if v.max() < r - sd else 'CLOSE: report the distributions, not the count'}")
    print(f"\n  H1 {'SUPPORTED' if p < 0.05 else 'NOT supported'} at the "
          "pre-registered threshold of 0.05.")

    if os.path.exists(RETINO):
        rv = np.array([x["argmax_mean"] for x in _load(RETINO, {"runs": []})["runs"]])
        m = len(rv)
        nge2 = int((rv >= r).sum())
        print("\nSECONDARY (declared; multiplicity applies -- never quote as primary)")
        print(f"  retinotopy-shuffled n = {m}: {rv.mean():.3f} +- {rv.std(ddof=1):.3f}"
              f"   n >= real {nge2}/{m}   p = {(nge2 + 1) / (m + 1):.3f} "
              f"(floor {1 / (m + 1):.3f})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"controls": run_controls, "real": run_real, "retino": run_retino,
     "report": report}[cmd]()
