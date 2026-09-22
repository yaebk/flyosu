"""
Experiment 7 -- a wiring rule chosen on a quantity that matters.

Experiment 4 found that the untrained wiring rule optimises something that does
not predict play: the summed mean channel response over an isolated falling
note correlates with untrained lane-correctness at rho = -0.03 across rewired
graphs, and the real connectome's value is unremarkable (0.34 against
0.37 +- 0.24).  Experiment 6 found a quantity that does discriminate -- the
width of the band of thresholds that serves all four keys at once, on which the
real network is 0/20 -- and a mechanism for why it matters, since the policy
has one threshold for four keys.

So: keep everything else, change the criterion.  Both rules choose one of the
same 24 lane-to-channel permutations from the same silent single-note probe
(log2(24) = 4.6 bits of stimulus knowledge, declared as always), and nothing
else about the controller changes.

    margin rule   maximise the summed mean response      (controller.best_assignment)
    band rule     maximise the shared-threshold band      (probes.band_assignment)

Two questions, in that order:

  1. Does the band rule play better?  If the criterion is the right one, every
     network should improve, and the real network -- which has a wide band to
     exploit -- should improve most.
  2. Does the real-vs-rewired gap survive it, under experiment 6's fair
     protocol?  Every network is swept over theta and scored at its own best,
     so neither rule is handed a threshold that suits one network.

Experiment 6's phase-3 sweep already measured the margin rule this way, and is
reused rather than repeated.

``PHASE=selectivity`` settles the loose end this experiment's retraction
created.  Experiment 6 reported two quantities on which the real network was
0/20 -- the shared-threshold band and the channel *selectivity* (how much of
the hit window the wired channel spends as the largest of the four).  The band
turned out to be conditional on the wiring rule.  Selectivity was measured
under the same wiring and is owed the same test: give every network its
band-optimal wiring and ask again.  Probes only, no play, so it is cheap.

    N_SEEDS=20 python -m experiments.e7_wiring
    PHASE=selectivity N_SEEDS=20 python -m experiments.e7_wiring
    DATASET=malecns N_SEEDS=10 python -m experiments.e7_wiring
    python -m experiments.e7_wiring report
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, probes as PR  # noqa: E402
from flyosu.controller import best_assignment  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DATASET = os.environ.get("DATASET", "flywire")
PATH = os.path.join(RESULTS, "e7_wiring" + ("" if DATASET == "flywire" else f"_{DATASET}") + ".json")
E6 = os.path.join(RESULTS, "e6_timing.json")
THETA_SWEEP = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
SWEEP_STAGE = 3
MIN_COUNTED = 20            # lane-correct is a ratio; see experiment 6
NOISE = 0.03


def sweep(player, wiring):
    """Lane-correct and accuracy over the threshold grid, for one wiring."""
    W = np.zeros((4, 4))
    for lane, ch in enumerate(wiring):
        W[lane, ch] = 1.0
    player.controller.W = W
    lc, acc, n = [], [], []
    for th in THETA_SWEEP:
        player.controller.b = np.full(4, -float(th))
        e = L.evaluate(player, stage=SWEEP_STAGE, n_charts=2, n_notes=20,
                       interval_ms=600.0, seed=7000 + 10 * SWEEP_STAGE)
        lc.append(e["lane_correct"]); acc.append(e["accuracy"])
        n.append(int(np.array(e["confusion"]).sum()))
    ok = np.array(n) >= MIN_COUNTED
    i = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
    return {"wiring": list(wiring), "lane_correct": lc, "accuracy": acc, "n_counted": n,
            "best_theta": float(THETA_SWEEP[i]), "best_lane_correct": float(lc[i]),
            "best_accuracy": float(max(acc)), "eligible": ok.tolist()}


def measure(label, kw):
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    tr = PR.lane_traces(fly, player.norm, player.r0)
    pre = tr.window(-400.0, 0.0)
    margin_w = best_assignment(tr.z[:, pre].mean(axis=1))
    band_w = PR.band_assignment(tr)
    out = {"label": label, "margin_wiring": list(margin_w), "band_wiring": list(band_w),
           "same": list(margin_w) == list(band_w),
           "margin_band": PR.shared_threshold(tr, margin_w)["shared_band"],
           "band_band": PR.shared_threshold(tr, band_w)["shared_band"],
           "band": sweep(player, band_w)}
    out["seconds"] = round(time.time() - t0, 1)
    b = out["band"]
    print(f"  {label:<24s} margin {margin_w} band {band_w} "
          f"{'(same)' if out['same'] else '(DIFFERENT)'}  "
          f"band width {out['margin_band']:+.2f} -> {out['band_band']:+.2f}  "
          f"lane-correct best {b['best_lane_correct']:.2f}@{b['best_theta']:.1f}  "
          f"acc {b['best_accuracy']:.3f}  ({out['seconds']:.0f}s)", flush=True)
    return out


def selectivity_one(label, kw):
    """Selectivity and the other probe quantities under BOTH wirings."""
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    player = P.Player.untrained(fly, theta=1.5)
    tr = PR.lane_traces(fly, player.norm, player.r0)
    pre = tr.window(-400.0, 0.0)
    m = best_assignment(tr.z[:, pre].mean(axis=1))
    b = PR.band_assignment(tr)
    out = {"label": label, "margin_wiring": list(m), "band_wiring": list(b)}
    for name, w in (("margin", m), ("band", b)):
        out[name] = {"selectivity": PR.selectivity(tr, w)["argmax_mean"],
                     "peak_margin": PR.selectivity(tr, w)["peak_margin_mean"],
                     "band": PR.shared_threshold(tr, w)["shared_band"],
                     "n_false_keys": PR.crossings(tr, w, theta=1.5)["n_false_keys"],
                     "n_on_time": PR.crossings(tr, w, theta=1.5)["n_on_time"]}
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<24s} selectivity {out['margin']['selectivity']:.2f} -> "
          f"{out['band']['selectivity']:.2f}   band {out['margin']['band']:+.2f} -> "
          f"{out['band']['band']:+.2f}   false keys {out['margin']['n_false_keys']} -> "
          f"{out['band']['n_false_keys']}  ({out['seconds']:.0f}s)", flush=True)
    return out


def phase_selectivity():
    results = {"runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    n = int(os.environ.get("N_SEEDS", 20))
    runs = results.setdefault("selectivity", [])
    done = {r["label"] for r in runs}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done:
            continue
        runs.append(selectivity_one(label, kw))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report_selectivity(results)


def report_selectivity(results):
    runs = results.get("selectivity", [])
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"] != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    print(f"\n=== does the selectivity result survive the new wiring rule? ===")
    summary = {}
    for key, label, better_high in (("selectivity", "selectivity (argmax fraction)", True),
                                    ("band", "shared-threshold band", True),
                                    ("peak_margin", "peak margin", True),
                                    ("n_false_keys", "keys falsely driven", False)):
        print(f"\n  {label}")
        summary[key] = {}
        for rule in ("margin", "band"):
            rv = real[rule][key]
            x = np.array([r[rule][key] for r in ctrl], dtype=float)
            n_ge = int((x >= rv).sum() if better_high else (x <= rv).sum())
            p = (n_ge + 1) / (len(x) + 1)
            print(f"    {rule + ' wiring':<14s} real {rv:+.2f}  rewired {x.mean():+.2f} +- {x.std():.2f}  "
                  f"{n_ge}/{len(x)} reach real  p {p:.3f}")
            summary[key][rule] = {"real": float(rv), "ctrl_mean": float(x.mean()),
                                  "ctrl_sd": float(x.std()), "n_ge": n_ge, "n": len(x), "p": p}
    results["selectivity_summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


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
    ctrl = [r for lbl, r in runs.items() if lbl != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    # experiment 6's theta sweep is the margin-rule baseline, and it exists for
    # FlyWire only -- the labels are identical across datasets, so comparing a
    # male CNS run against it would silently mix connectomes.
    margin = {}
    if DATASET == "flywire" and os.path.exists(E6):
        with open(E6) as fh:
            margin = {r["label"]: r for r in json.load(fh).get("theta_sweep", [])}

    # lane-correctness is a ratio over presses landing near a note, so a
    # network that never reaches MIN_COUNTED at any threshold gets a fallback
    # score, not a measurement.  Say so loudly -- on the male CNS the real
    # network is the only one of eleven in that position, and its "0.80" came
    # from eight presses.
    bad = [r["label"] for r in runs.values()
           if not any(n >= MIN_COUNTED for n in r["band"]["n_counted"])]
    if bad:
        msg = ", ".join(bad)
        print("")
        print("  !! no threshold reaches " + str(MIN_COUNTED) + " counted presses for: " + msg)
        print("     their lane-correct is a fallback, not a score; read accuracy instead")
    n_diff = sum(1 for r in runs.values() if not r["same"])
    print(f"\n=== experiment 7: wiring chosen on the shared-threshold band ===")
    print(f"  the two rules disagree on {n_diff}/{len(runs)} networks "
          f"(real: {'different' if not real['same'] else 'same'})")
    widen = np.array([r["band_band"] - r["margin_band"] for r in runs.values()])
    print(f"  band width gained: {widen.mean():+.2f} z on average, max {widen.max():+.2f}")

    rows = []
    for key, label in (("best_lane_correct", "lane-correct, own best theta"),
                       ("best_accuracy", "accuracy, own best theta")):
        b_real = real["band"][key]
        b_ctrl = np.array([r["band"][key] for r in ctrl])
        n_ge = int((b_ctrl >= b_real).sum())
        p = (n_ge + 1) / (len(b_ctrl) + 1)
        line = {"metric": label, "rule": "band", "real": float(b_real),
                "ctrl_mean": float(b_ctrl.mean()), "ctrl_sd": float(b_ctrl.std()),
                "n_ge": n_ge, "n": len(b_ctrl), "p": p}
        print(f"\n  {label}")
        print(f"    band rule    real {b_real:.3f}  rewired {b_ctrl.mean():.3f} +- {b_ctrl.std():.3f}  "
              f"{n_ge}/{len(b_ctrl)}  p {p:.3f}")
        if margin:
            mk = "best_lane_correct" if key == "best_lane_correct" else "best_accuracy"
            m_real = margin["real connectome"][mk]
            m_ctrl = np.array([margin[r["label"]][mk] for r in ctrl if r["label"] in margin])
            m_ge = int((m_ctrl >= m_real).sum())
            print(f"    margin rule  real {m_real:.3f}  rewired {m_ctrl.mean():.3f} +- {m_ctrl.std():.3f}  "
                  f"{m_ge}/{len(m_ctrl)}  p {(m_ge + 1) / (len(m_ctrl) + 1):.3f}   (experiment 6)")
            line["margin_real"] = float(m_real); line["margin_ctrl_mean"] = float(m_ctrl.mean())
            line["margin_n_ge"] = m_ge
            print(f"    change       real {b_real - m_real:+.3f}   rewired {b_ctrl.mean() - m_ctrl.mean():+.3f}")
        rows.append(line)
    results["summary"] = rows
    results["n_disagree"] = n_diff
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            res = json.load(fh)
        report(res)
        if res.get("selectivity"):
            report_selectivity(res)
    elif os.environ.get("PHASE") == "selectivity":
        phase_selectivity()
    else:
        main()
