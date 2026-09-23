"""
Experiment 13 -- the male CNS untrained comparison with a readout that is not
known in advance to destroy the signal.

Experiment 7 ran the untrained comparison on the male CNS and got a reversal:
the real network 0.067 accuracy against its controls' 0.237, nine of ten
controls ahead of it.  That number is uninterpretable and the reason is
specific.  The male CNS readout is four *real leg motor pools* grouped by
neuromere and side, and those pools move as a common mode under visual input
(docs/MALECNS.md): lane identity is present in the 348 motor neurons at 0.98
but almost absent from the four pool means.  A threshold policy reading those
means has nothing lane-specific to threshold, so the real network never
reaches the 20-press guard at any theta in the sweep -- 8 presses over 40
notes, against 44-80 for every control.  The result says "this readout is bad
on this dataset", which was known before the run, and says nothing about the
connectome.

So: keep the protocol, change the readout.  The same 348 neurons, read as the
top-k principal components of their activity over the calibration ensemble
(``reservoir.PopulationProjection``) instead of as four anatomical pools.
Experiment 5 showed eight of those components support 0.86 accuracy with a
supervised fit, so the information is there.  The question here is whether an
*untrained* policy can reach it, and whether the real connectome is then
better or worse than its rewired controls.

## Is this still untrained?

The PCs themselves are fitted by SVD on the 61-stimulus calibration ensemble.
That ensemble tiles the visual field and knows nothing about lanes or keys, and
it is the same ensemble the channel normaliser is fitted on, so the projection
is label-free in exactly the sense the rest of the untrained pipeline is.

Which component each key reads is not label-free, and neither is the existing
policy's lane-to-channel permutation.  The project's convention is that lane
knowledge may enter as a small number of parameters read off a *silent,
reward-free, single-note probe*, provided it is declared, counted, and derived
per network from that network's own probe, so that no control inherits the
real network's choice.  That is how the wiring permutation (log2 24 = 4.6
bits, experiments 4/6/7) and the per-key delays (4 numbers, experiment 11)
are handled.  This experiment follows the same rule and pays the same way:

    arm              what each key reads                     declared knowledge
    channels         one of the 4 pools, one-to-one          log2(4!)      = 4.6 bits
    channels_signed  one of the 4 pools, with a sign         log2(4!*2^4)  = 8.6 bits
    pc4              one of the top 4 PCs, with a sign       log2(4!*2^4)  = 8.6 bits
    pc8              one of the top 8 PCs, with a sign       log2(8*7*6*5*2^4) = 14.7 bits

Signs are in the PC arms because the sign of a principal component is an
arbitrary output of the SVD, and because the male CNS pools go *down* under
visual drive; ``channels_signed`` is there so that the PC arms can be compared
against a pool readout with the same number of declared bits rather than
against a strictly less informed one.  Every choice is made by the same
criterion on the same silent probe, separately for every network.

Continuous parameters in the policy: still one shared threshold.  ``W`` is a
selection matrix with one +-1 per row -- no fitted weights anywhere.  This is
not the supervised ridge readout of experiment 5, which spends 4k + 4 real
numbers fitted on labelled play; it is the untrained policy with its
lane-to-feature map generalised from four pools to k components.

## Metric, fixed before any real-network number was looked at

Every network is swept over the same theta grid and scored at *its own best*
(experiment 6 lost a claim to a shared theta chosen on the real network).
"Best" is the threshold maximising

    score = accuracy - 0.4 * strays per note

among the thresholds at which that network reaches ``MIN_COUNTED = 20`` judged
presses.  Accuracy alone cannot be the selection criterion because osu!mania
charges nothing for a press in an empty lane, so a low threshold that mashes
all four keys scores well; 0.4 is the stray penalty ``reservoir.py`` already
uses for exactly this decision, where 0.05 was measured to let mashing win.
The press guard is there because the score by itself has a degenerate optimum
-- never pressing is accuracy 0, strays 0, score 0, which beats any honest
attempt.  (That flaw was found on a rewired control before the real network was
run, and the fix is the guard experiment 6 already imposes on lane-correctness.)
A network with no eligible threshold falls back to its best accuracy and is
named in a warning.  Reported: accuracy at the chosen theta (the headline), the
score, strays per note, lane-correctness under the same guard, and the whole
grid.  ``fly.stability()`` for every network.  The theta grid was widened below
experiment 7's 0.5 after looking at the PC amplitudes on *a rewired control*,
never the real network.

Controls: 10 rewired (degree- and weight-preserving), the family that matters
for a claim about topology and the existing male CNS budget.  p = (n_ge + 1) /
(n + 1), one-sided, so the floor is 1/11 = 0.091 and nothing here can be
significant at 0.05.

## Which arm is the comparison, and multiplicity

``pc8`` is the arm this experiment exists to run: experiment 5 measured 0.856
supervised accuracy from eight components of these 348 neurons, so eight is the
number already on the record as sufficient, and the task was to see whether an
untrained policy can reach it.  ``channels`` is experiment 7's rule re-run on
the same grid, so it is a replication rather than a new test.
``channels_signed`` and ``pc4`` are there to say what ``pc8``'s number *means*
-- they hold the declared bits fixed while the readout changes -- and any
comparison decided by them alone is exploratory.

Four arms on the same eleven networks is four chances at a low p, so the report
prints a Bonferroni-corrected floor alongside the per-arm one.  With ten
controls that corrected floor is 4/11 = 0.36, which is the honest summary of
this experiment's statistical power: **no arm here can reach significance, and
none should be described as if it had.**  What the arms can do is show whether
the readout moves the comparison, which is the question.

    DATASET=malecns N_SEEDS=10 python -m experiments.e13_malecns_readout
    python -m experiments.e13_malecns_readout report
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from itertools import permutations, product

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, probes as PR, reservoir as RS  # noqa: E402
from flyosu.controller import ChannelNormaliser, Controller, calibration_states  # noqa: E402
from flyosu.encoder import Encoder, LANE_AZ  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DATASET = os.environ.get("DATASET", "malecns")
PATH = os.path.join(RESULTS, f"e13_readout_{DATASET}.json")

# wider and finer at the bottom than experiment 7's (0.5 ... 3.0): the PC
# features peak lower than the pooled channels do.  Chosen on rewired #1.
THETA_SWEEP = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0)
SWEEP_STAGE = 3
SWEEP = dict(stage=SWEEP_STAGE, n_charts=2, n_notes=20, interval_ms=600.0,
             seed=7000 + 10 * SWEEP_STAGE)          # experiment 7's charts, exactly
MIN_COUNTED = 20
NOISE = 0.03
STRAY_PENALTY = 0.4                                  # reservoir.STRAY_PENALTY_FIT
N_KEYS = 4
ARMS = ("channels", "channels_signed", "pc4", "pc8")


# -- traces in whatever feature space the arm uses -------------------------

def feature_traces(fly, feat, r0, dt=M.DT_PLAY, approach_ms=800.0,
                   overshoot_ms=PR.OVERSHOOT_MS) -> PR.LaneTraces:
    """``probes.lane_traces`` with the four normalised channels replaced by an
    arbitrary label-free feature map (``feat(r) -> (k,)``).

    Same stimulus, same silent noise-free single note per lane, same window
    convention, so every ``probes`` quantity can be computed on the result.
    With ``reservoir.ChannelFeatures`` it reproduces ``probes.lane_traces``
    exactly; that is asserted per network in ``measure``."""
    enc = Encoder(fly.ret)
    ph = fly.ph_local
    ext = np.zeros(fly.net.n, dtype=np.float32)
    steps = int(round((approach_ms + overshoot_ms) / dt))
    out = np.zeros((len(LANE_AZ), steps, feat.k))
    for lane in range(len(LANE_AZ)):
        enc.reset()
        r = r0.copy()
        for i in range(steps):
            ext[ph] = enc([(lane, i * dt / approach_ms)], dt)
            r = fly.net.step(r, ext, dt)
            out[lane, i] = feat(r)
    return PR.LaneTraces(t=np.arange(steps) * dt - approach_ms, z=out,
                         approach_ms=approach_ms)


# -- the wiring rule, generalised to k features and signs ------------------

def band_select(tr: PR.LaneTraces, signed: bool = True,
                hit_ms: tuple[float, float] = (-160.0, 160.0)) -> dict:
    """Pick one (feature, sign) per lane, one-to-one, maximising the shared-
    threshold band.

    Identical in criterion to ``probes.band_assignment`` (false alarms scored
    in the same hit window): for the chosen mapping, ``hit[lane]`` is the peak
    of that lane's own signed feature while that lane's note falls, and
    ``false[lane]`` is its peak while any other lane's note falls.  One theta
    serves all four keys iff ``min(hit) > max(false)``, and the band is the
    width of the set of thetas that do.  With four features and no signs the
    candidate set is exactly the 24 permutations that rule searches.
    """
    hw = tr.window(*hit_ms)
    Z = tr.z[:, hw, :]                                  # (lane, T, k)
    k = Z.shape[2]
    A = np.stack([Z.max(1), (-Z).max(1)], axis=2)       # (lane, feature, sign)
    # peak of the same signed feature while some *other* lane's note falls
    B = np.empty_like(A)
    for lane in range(A.shape[0]):
        B[lane] = np.delete(A, lane, axis=0).max(0)
    signs = (1.0, -1.0) if signed else (1.0,)
    sign_idx = (0, 1) if signed else (0,)
    best, best_band = None, -np.inf
    for cols in permutations(range(k), A.shape[0]):
        for ss in product(sign_idx, repeat=A.shape[0]):
            hit = min(A[l, cols[l], ss[l]] for l in range(A.shape[0]))
            false = max(B[l, cols[l], ss[l]] for l in range(A.shape[0]))
            if hit - false > best_band:
                best_band, best = hit - false, (cols, ss)
    cols, ss = best
    n_cand = math.perm(k, A.shape[0]) * len(signs) ** A.shape[0]
    return {"features": list(cols), "signs": [signs[s] for s in ss],
            "band": float(best_band), "bits": float(math.log2(n_cand)),
            "n_candidates": int(n_cand),
            "hit": [float(A[l, cols[l], ss[l]]) for l in range(A.shape[0])],
            "false": [float(B[l, cols[l], ss[l]]) for l in range(A.shape[0])],
            "theta_mid": float(0.5 * (min(A[l, cols[l], ss[l]] for l in range(A.shape[0]))
                                      + max(B[l, cols[l], ss[l]] for l in range(A.shape[0]))))}


def selection_matrix(sel: dict, k: int) -> np.ndarray:
    W = np.zeros((N_KEYS, k))
    for lane, (c, s) in enumerate(zip(sel["features"], sel["signs"])):
        W[lane, c] = s
    return W


# -- the sweep -------------------------------------------------------------

def sweep(player, feat, W) -> dict:
    """Play the sweep charts at every theta with this feature map and wiring."""
    saved_feat, saved_ctrl = player.features, player.controller
    player.features = None if isinstance(feat, RS.ChannelFeatures) else feat
    lc, acc, sc, st, n = [], [], [], [], []
    try:
        for th in THETA_SWEEP:
            player.controller = Controller(W=W.copy(), b=np.full(N_KEYS, -float(th)),
                                           refractory_ms=saved_ctrl.refractory_ms,
                                           smooth_ms=saved_ctrl.smooth_ms)
            e = L.evaluate(player, **SWEEP)
            lc.append(e["lane_correct"]); acc.append(e["accuracy"])
            st.append(e["stray_per_note"])
            sc.append(e["accuracy"] - STRAY_PENALTY * e["stray_per_note"])
            n.append(int(np.array(e["confusion"]).sum()))
    finally:
        player.features, player.controller = saved_feat, saved_ctrl
    # the pre-registered criterion, over thresholds at which the policy is
    # actually playing: score alone has a degenerate optimum at "never press"
    # (accuracy 0, strays 0, score 0), which beats any real attempt
    ok = np.array(n) >= MIN_COUNTED
    i = int(np.argmax(np.where(ok, sc, -np.inf))) if ok.any() else int(np.argmax(acc))
    j = int(np.argmax(np.where(ok, lc, -1.0))) if ok.any() else int(np.argmax(lc))
    return {"theta": list(THETA_SWEEP), "lane_correct": lc, "accuracy": acc,
            "score": sc, "stray_per_note": st, "n_counted": n, "eligible": ok.tolist(),
            "best_theta": float(THETA_SWEEP[i]), "best_score": float(sc[i]),
            "accuracy_at_best": float(acc[i]), "lane_correct_at_best": float(lc[i]),
            "stray_at_best": float(st[i]), "n_counted_at_best": int(n[i]),
            "any_eligible": bool(ok.any()),
            # a ratio over presses landing near a note: undefined, not zero and
            # not 1.0, when no threshold reaches MIN_COUNTED.  Experiment 7's
            # male CNS run emitted 0.800 from eight presses; None is what that
            # should have been.
            "lane_correct_guarded": (float(lc[j]) if ok.any() else None),
            "lane_correct_guarded_theta": (float(THETA_SWEEP[j]) if ok.any() else None),
            "max_accuracy": float(max(acc))}


def measure(label, kw) -> dict:
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    states = calibration_states(fly, player.r0)
    out = {"label": label, "dataset": DATASET, "stability": fly.stability(),
           "n_readout": int(len(fly.readout.dn_local)), "arms": {}}

    chan = RS.ChannelFeatures(player)
    feats = {"channels": chan, "channels_signed": chan,
             "pc4": RS.PopulationProjection.fit(fly, player.r0, k=4, states=states),
             "pc8": RS.PopulationProjection.fit(fly, player.r0, k=8, states=states)}
    traces = {}
    for name, f in feats.items():
        if id(f) not in traces:
            traces[id(f)] = feature_traces(fly, f, player.r0)
    out["explained"] = {n: feats[n].explained.tolist() for n in ("pc4", "pc8")}

    # the channels arm must be exactly experiment 7's band rule
    ref = PR.lane_traces(fly, player.norm, player.r0)
    dev = float(np.abs(ref.z - traces[id(chan)].z).max())
    out["channel_trace_deviation"] = dev
    assert dev < 1e-9, f"channel features diverge from probes.lane_traces ({dev:g})"
    ref_band = PR.shared_threshold(ref, PR.band_assignment(ref))["shared_band"]

    for arm in ARMS:
        f = feats[arm]
        sel = band_select(traces[id(f)], signed=(arm != "channels"))
        if arm == "channels":
            # same criterion, same candidate set: must agree with probes
            assert abs(sel["band"] - ref_band) < 1e-9, (sel["band"], ref_band)
        d = {"selection": sel, "k": int(f.k),
             "n_params": int(N_KEYS * f.k + N_KEYS)}
        d.update(sweep(player, f, selection_matrix(sel, f.k)))
        out["arms"][arm] = d
        print(f"  {label:<20s} {arm:<16s} feat {sel['features']} "
              f"sign {[int(s) for s in sel['signs']]}  band {sel['band']:+.2f}  "
              f"acc {d['accuracy_at_best']:.3f} @ th {d['best_theta']:.2f}  "
              f"score {d['best_score']:+.3f}  lane {d['lane_correct_at_best']:.2f}  "
              f"strays/note {d['stray_at_best']:.2f}  presses {d['n_counted_at_best']}",
              flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<20s} radius {out['stability']['spectral_radius']:.2f}  "
          f"fixed point {out['stability']['fixed_point']}  ({out['seconds']:.0f}s)", flush=True)
    return out


# -- phase 2: the same policies on charts they were not tuned on -----------

HELD_OUT = dict(stage=3, n_charts=3, n_notes=20, interval_ms=600.0, seed=999)


def heldout_one(run: dict) -> dict:
    """Replay a finished network's chosen policy (its features, signs and
    theta) on three charts it has never seen.

    Everything about the policy was chosen on the sweep charts -- the
    lane-to-feature map on the silent probe, the threshold on the sweep charts
    themselves -- so the sweep numbers are optimistic for every network in the
    same way experiment 7 flagged.  This is the generalisation test: nothing is
    re-chosen here, the charts are experiment 3's held-out seeds, and the
    ranking is what it is."""
    kw = {} if run["label"] == "real connectome" else {
        "shuffle_seed": int(run["label"].split("#")[1])}
    fly = M.build(regime="play", dataset=DATASET, **kw)
    player = P.Player.untrained(fly, theta=1.5, noise=NOISE)
    states = calibration_states(fly, player.r0)
    chan = RS.ChannelFeatures(player)
    feats = {"channels": chan, "channels_signed": chan,
             "pc4": RS.PopulationProjection.fit(fly, player.r0, k=4, states=states),
             "pc8": RS.PopulationProjection.fit(fly, player.r0, k=8, states=states)}
    out = {"label": run["label"], "arms": {}}
    for arm in ARMS:
        a, f = run["arms"][arm], feats[arm]
        player.features = None if isinstance(f, RS.ChannelFeatures) else f
        player.controller = Controller(W=selection_matrix(a["selection"], f.k),
                                       b=np.full(N_KEYS, -float(a["best_theta"])),
                                       refractory_ms=150.0, smooth_ms=40.0)
        e = L.evaluate(player, **HELD_OUT)
        n_c = int(np.array(e["confusion"]).sum())
        out["arms"][arm] = {
            "theta": a["best_theta"], "accuracy": e["accuracy"],
            "hit_rate": e["hit_rate"], "stray_per_note": e["stray_per_note"],
            "score": e["accuracy"] - STRAY_PENALTY * e["stray_per_note"],
            "n_counted": n_c, "eligible": bool(n_c >= MIN_COUNTED),
            "lane_correct": (e["lane_correct"] if n_c >= MIN_COUNTED else None),
            "sweep_accuracy": a["accuracy_at_best"]}
        d = out["arms"][arm]
        print(f"  {run['label']:<20s} {arm:<16s} th {d['theta']:.2f}  "
              f"sweep acc {d['sweep_accuracy']:.3f} -> held-out {d['accuracy']:.3f}  "
              f"score {d['score']:+.3f}  lane "
              + ("-" if d["lane_correct"] is None else f"{d['lane_correct']:.2f}")
              + f"  presses {d['n_counted']}", flush=True)
    player.features = None
    return out


def phase_heldout():
    with open(PATH) as fh:
        results = json.load(fh)
    runs = results.get("held_out", [])
    done = {r["label"] for r in runs}
    for run in results["runs"]:
        if run["label"] in done:
            continue
        runs.append(heldout_one(run))
        results["held_out"] = runs
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report_heldout(results)


def report_heldout(results):
    runs = results.get("held_out", [])
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"] != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    n = len(ctrl)
    print(f"\n=== experiment 13, held-out charts (nothing re-chosen) ===")
    print(f"  {n} rewired controls, floor {1.0 / (n + 1):.3f}, "
          f"Bonferroni floor over {len(ARMS)} arms {len(ARMS) / (n + 1):.3f}")
    summary = {}
    for arm in ARMS:
        print(f"\n  {arm}")
        summary[arm] = {}
        for key, label in (("accuracy", "accuracy"), ("score", "score"),
                           ("lane_correct", "lane-correct (guarded)")):
            rv = real["arms"][arm][key]
            if rv is None:
                print(f"    {label:<24s} real -   (press guard not met; no comparison)")
                summary[arm][key] = {"real": None, "reason": "press guard not met"}
                continue
            keep = [r for r in ctrl if r["arms"][arm][key] is not None]
            x = np.array([r["arms"][arm][key] for r in keep], dtype=float)
            m = len(x)
            n_ge = int((x >= rv).sum())
            print(f"    {label:<24s} real {rv:+.3f}   rewired {x.mean():+.3f} +- {x.std():.3f}"
                  f"   {n_ge}/{m}   p {_p(n_ge, m):.3f} (floor {1.0 / (m + 1):.3f})")
            summary[arm][key] = {"real": float(rv), "ctrl_mean": float(x.mean()),
                                 "ctrl_sd": float(x.std()), "n_ge": n_ge, "n": m,
                                 "p": _p(n_ge, m), "p_floor": 1.0 / (m + 1)}
    results["held_out_summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


def main():
    n = int(os.environ.get("N_SEEDS", 10))
    results = {"dataset": DATASET, "theta": list(THETA_SWEEP), "sweep": SWEEP,
               "noise": NOISE, "stray_penalty": STRAY_PENALTY,
               "min_counted": MIN_COUNTED, "runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", {})] + [(f"rewired #{s}", {"shuffle_seed": s})
                                        for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done:
            continue
        results["runs"].append(measure(label, kw))
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    report(results)


def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def report(results):
    runs = results["runs"]
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"] != "real connectome"]
    if real is None or len(ctrl) < 3:
        print("not enough networks yet")
        return
    n = len(ctrl)
    floor = 1.0 / (n + 1)
    print(f"\n=== experiment 13, {results['dataset']}: untrained play on {real['n_readout']} "
          f"motor neurons, four readouts ===")
    print(f"  {n} rewired controls, one-sided p = (n_ge + 1)/(n + 1), floor {floor:.3f}")
    print("\n  stability (blank-field fixed point / spectral radius)")
    rad = np.array([r["stability"]["spectral_radius"] for r in ctrl])
    print(f"    real    {real['stability']['spectral_radius']:.2f}  "
          f"fixed point {real['stability']['fixed_point']}")
    print(f"    rewired {rad.mean():.2f} +- {rad.std():.2f}  "
          f"fixed point on {sum(r['stability']['fixed_point'] for r in ctrl)}/{n}")

    bad = [f"{r['label']} / {a}" for r in runs for a in ARMS
           if not r["arms"][a]["any_eligible"]]
    if bad:
        print("\n  !! no threshold reaches " + str(MIN_COUNTED) + " counted presses for: "
              + ", ".join(bad))
        print("     lane-correctness is undefined there (a ratio over too few presses);")
        print("     it is printed as '-' and those networks are dropped from that row.")
        print("     their accuracy is at the threshold maximising accuracy, not the score.")

    # four arms on the same eleven networks.  pc8 is the arm this experiment
    # was built to run; the other three exist to say what pc8's number means.
    # Nothing here can be significant anyway: see the Bonferroni line below.
    print(f"\n  multiplicity: {len(ARMS)} arms on the same networks.  Per-arm floor "
          f"{floor:.3f}; Bonferroni-corrected floor {len(ARMS) * floor:.3f}.")
    summary = {"p_floor": floor, "n_arms": len(ARMS),
               "p_floor_bonferroni": len(ARMS) * floor,
               "primary_arm": "pc8", "guard_failures": bad}
    for arm in ARMS:
        a_real = real["arms"][arm]
        print(f"\n  {arm}  ({a_real['selection']['bits']:.1f} declared bits, "
              f"1 threshold, no fitted weights)"
              + ("" if a_real["any_eligible"] else "   [real network fails the press guard]"))
        summary[arm] = {}
        for key, label, hi in (("accuracy_at_best", "accuracy at own best theta", True),
                               ("best_score", "score = acc - 0.4*strays/note", True),
                               ("max_accuracy", "max accuracy over the grid", True),
                               ("lane_correct_guarded", "lane-correct (guarded)", True),
                               ("band", "shared-threshold band", True)):
            def val(r):
                a = r["arms"][arm]
                if key == "band":
                    return a["selection"]["band"]
                if key == "lane_correct_guarded" and not a["any_eligible"]:
                    return None            # also catches JSON written before the guard
                return a[key]
            rv = val(real)
            if rv is None:
                print(f"    {label:<34s} real -   (undefined: press guard not met; "
                      f"no comparison)")
                summary[arm][key] = {"real": None, "reason": "press guard not met"}
                continue
            keep = [r for r in ctrl if val(r) is not None]
            x = np.array([val(r) for r in keep], dtype=float)
            m = len(x)
            n_ge = int((x >= rv).sum() if hi else (x <= rv).sum())
            drop = "" if m == n else f"  ({n - m} control(s) dropped: guard not met)"
            print(f"    {label:<34s} real {rv:+.3f}   rewired {x.mean():+.3f} +- {x.std():.3f}"
                  f"   {n_ge}/{m} reach real   p {_p(n_ge, m):.3f} (floor {1.0 / (m + 1):.3f})"
                  + drop)
            summary[arm][key] = {"real": float(rv), "ctrl_mean": float(x.mean()),
                                 "ctrl_sd": float(x.std()), "n_ge": n_ge, "n": m,
                                 "p": _p(n_ge, m), "p_floor": 1.0 / (m + 1),
                                 "p_bonferroni": min(1.0, len(ARMS) * _p(n_ge, m))}
    results["summary"] = summary
    with open(PATH, "w") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH) as fh:
            res = json.load(fh)
        report(res)
        if res.get("held_out"):
            report_heldout(res)
    elif os.environ.get("PHASE") == "heldout":
        phase_heldout()
    else:
        main()
