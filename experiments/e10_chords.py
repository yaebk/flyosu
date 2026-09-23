"""
Experiment 10 -- is the chord deficit a transfer artefact or a representational
limit?

Experiment 5 fitted the ridge readout on **stage 3** (single notes) and then,
without refitting, played **stage 4** (chords).  The real connectome came out
*worse* than its rewired controls at three of four readout sizes:

    stage-4 accuracy, no refit:  real    0.162 / 0.071 / 0.158 / 0.583
                                 rewired 0.308 / 0.260 / 0.408 / 0.697

The hypothesis on record is that the real network's strongly amplified common
mode responds to both lanes of a chord together, so a readout fitted on single
notes mispredicts when two notes are on screen.  Experiment 5 listed the
follow-up and this is it.

Three things, one pass per network:

  1. **Fit on stage 4, evaluate on stage 4.**  Everything else identical to
     experiment 5 -- same four readouts, same label-free features, same four
     training charts (same seeds, stage swapped), same controller, same
     evaluation charts.  If the deficit is a *transfer* failure it should
     largely vanish.  If the real network simply cannot represent two
     simultaneous notes, it should persist.

  2. **The reverse transfer**, fit on stage 4 and evaluate on stage 3, on the
     same held-out charts experiment 5 used -- so the comparison is symmetric
     and "stage 4 is a harder fitting target for everybody" is separable from
     "stage 4 is harder for the real network".

  3. **The mechanism, measured directly.**  ``probes.lane_traces`` gives each
     channel's response to a single falling note, ``probes.chord_traces`` the
     same for all six two-note chords.  Relative to the blank-field baseline,
     write the chord response A, the sum of the two single-note responses S,
     and their pointwise max M.  Then

         alpha = <A - M, S - M> / <S - M, S - M>

     is 1 for a perfectly additive (linear) network, 0 for one that saturates
     to the stronger of the two inputs, negative for one where two notes
     together produce *less* than one alone, and above 1 for super-additivity.
     Degenerate points, where the two notes drive a channel identically and
     S = M, carry zero weight by construction.  This is the quantity the
     hypothesis is about, and correlating it with each network's chord-transfer
     deficit is the actual content of the experiment; the play numbers on their
     own only restate experiment 5.

Controls: rewired topology (``shuffle_seed``), the family that tests whether
the wiring matters.  Seeds 1..N are the same networks experiment 5 used, so
its fit-on-3 stage-4 numbers can be differenced against these ones per network.

    N_CTRL=12 python -m experiments.e10_chords
    python -m experiments.e10_chords report
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import learn as L, model as M, play as P, probes as PR, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DATASET = os.environ.get("DATASET", "flywire")
PATH = os.path.join(RESULTS, "e10_chords.json")
E5_PATH = os.path.join(RESULTS, "e5_reservoir.json")

READOUTS = ("channels", "pca4", "pca8", "pca16")
THETA = 1.5
NOISE = 0.03
FAM = "rewired topology"

# identical to experiment 5 except that the training stage is 4, not 3
TRAIN4 = dict(stage=4, n_charts=4, n_notes=24, interval_ms=600.0, seed=100)
EVAL4 = dict(stage=4, n_charts=2, n_notes=20, interval_ms=600.0, seed=2999)   # e5 "transfer"
EVAL3 = dict(stage=3, n_charts=3, n_notes=20, interval_ms=600.0, seed=999)    # e5 "held_out"

HIT_MS = (-160.0, 160.0)


# -- the additivity probe --------------------------------------------------

def _alpha(A: np.ndarray, S: np.ndarray, Mx: np.ndarray) -> float:
    """Least-squares position of the chord response between max and sum."""
    d, e = (A - Mx).ravel(), (S - Mx).ravel()
    den = float(e @ e)
    return float(d @ e / den) if den > 1e-12 else float("nan")


def additivity(fly, norm, r0, dt) -> dict:
    """How a two-note chord compares with the two single notes that make it.

    Responses are taken relative to the blank-field channel state, so "sum"
    and "max" mean what they say; z units otherwise.
    """
    t0 = time.time()
    tr = PR.lane_traces(fly, norm, r0, dt=dt)
    pairs, Zc, _ = PR.chord_traces(fly, norm, r0, dt=dt)
    z0 = norm.z(fly.channels(r0))
    Rl = tr.z - z0                       # (4 lanes, T, 4 channels)
    Rc = Zc - z0                         # (6 pairs, T, 4 channels)
    hw = tr.window(*HIT_MS)

    per_pair, a_full, a_win = [], [], []
    ratio_sum, ratio_max, err_sum, err_max = [], [], [], []
    involved_pk, uninvolved_pk, cm_gain = [], [], []
    for (a, b), A in zip(pairs, Rc):
        S = Rl[a] + Rl[b]
        Mx = np.maximum(Rl[a], Rl[b])
        af, aw = _alpha(A, S, Mx), _alpha(A[hw], S[hw], Mx[hw])
        a_full.append(af); a_win.append(aw)
        ratio_sum.append(float(np.linalg.norm(A) / max(np.linalg.norm(S), 1e-12)))
        ratio_max.append(float(np.linalg.norm(A) / max(np.linalg.norm(Mx), 1e-12)))
        err_sum.append(float(np.linalg.norm(A - S) / max(np.linalg.norm(S), 1e-12)))
        err_max.append(float(np.linalg.norm(A - Mx) / max(np.linalg.norm(Mx), 1e-12)))
        # common mode: the four channels' mean, chord against sum of singles
        cm_a = A.mean(1); cm_s = S.mean(1)
        cm_gain.append(float(cm_a @ cm_s / max(cm_s @ cm_s, 1e-12)))
        per_pair.append({"pair": [int(a), int(b)], "alpha": af, "alpha_window": aw})
    # peak-amplitude version, per (pair, channel): where the chord peak sits
    # between the larger single-note peak and the two peaks summed
    pk_num, pk_den = [], []
    for (a, b), A in zip(pairs, Rc):
        for c in range(A.shape[1]):
            pa, pb, pc = Rl[a][:, c].max(), Rl[b][:, c].max(), A[:, c].max()
            s, m = pa + pb, max(pa, pb)
            pk_num.append(pc - m); pk_den.append(s - m)
    pk_num, pk_den = np.array(pk_num), np.array(pk_den)
    alpha_peak = float(pk_num @ pk_den / max(pk_den @ pk_den, 1e-12))

    # how loud are the two channels a chord does not involve, against the two
    # it does (both relative to the same single-note peaks)?
    wiring = PR.best_assignment(Rl[:, tr.window(-400.0, 0.0)].mean(axis=1) + z0)
    for (a, b), A in zip(pairs, Rc):
        for lane in range(4):
            ch = wiring[lane]
            (involved_pk if lane in (a, b) else uninvolved_pk).append(float(A[hw, ch].max()))
    return {"pairs": [list(map(int, p)) for p in pairs],
            "wiring": list(map(int, wiring)),
            "alpha_full": float(np.mean(a_full)), "alpha_full_sd": float(np.std(a_full)),
            "alpha_window": float(np.mean(a_win)),
            "alpha_peak": alpha_peak,
            "norm_ratio_to_sum": float(np.mean(ratio_sum)),
            "norm_ratio_to_max": float(np.mean(ratio_max)),
            "rel_err_to_sum": float(np.mean(err_sum)),
            "rel_err_to_max": float(np.mean(err_max)),
            "common_mode_gain": float(np.mean(cm_gain)),
            "involved_peak_z": float(np.mean(involved_pk)),
            "uninvolved_peak_z": float(np.mean(uninvolved_pk)),
            "per_pair": per_pair,
            "seconds": round(time.time() - t0, 1)}


# -- one network -----------------------------------------------------------

def measure(label, kw) -> dict:
    t0 = time.time()
    fly = M.build(regime="play", dataset=DATASET, **kw)
    out = {"label": label, "dataset": DATASET, "stability": fly.stability(), "readouts": {}}
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE)
    out["additivity"] = additivity(fly, player.norm, player.r0, player.dt)
    ad = out["additivity"]
    print(f"  {label:<26s} alpha {ad['alpha_full']:+.3f} (peak {ad['alpha_peak']:+.3f}, "
          f"win {ad['alpha_window']:+.3f})  |A|/|S| {ad['norm_ratio_to_sum']:.3f}  "
          f"|A|/|M| {ad['norm_ratio_to_max']:.3f}  cm-gain {ad['common_mode_gain']:.3f}", flush=True)

    states = calibration_states(fly, player.r0)
    rr = R.RidgeReadout(player, **TRAIN4)
    rr.record()
    out["seconds_record"] = round(time.time() - t0, 1)
    out["frames"] = int(sum(len(r.t) for r in rr.recordings))
    for name in READOUTS:
        rr.features = (None if name == "channels" else
                       R.PopulationProjection.fit(fly, player.r0, k=int(name[3:]), states=states))
        d = rr.solve()
        d["eval4"] = L.evaluate(player, **EVAL4)
        d["eval3"] = L.evaluate(player, **EVAL3)
        if rr.features is not None:
            d["explained"] = rr.features.explained.tolist()
        out["readouts"][name] = d
        e4, e3 = d["eval4"], d["eval3"]
        print(f"  {label:<26s} {name:<8s} {d['n_params']:>3d} params  train {d['train_reward']:.2f}  "
              f"fit4->4 acc {e4['accuracy']:.3f} hit {e4['hit_rate']:.2f} lane {e4['lane_correct']:.2f}  "
              f"fit4->3 acc {e3['accuracy']:.3f}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<26s} radius {out['stability']['spectral_radius']:.2f}  ({out['seconds']:.0f}s)",
          flush=True)
    return out


def main():
    n = int(os.environ.get("N_CTRL", 12))
    results = {"dataset": DATASET, "train": TRAIN4, "eval4": EVAL4, "eval3": EVAL3,
               "theta": THETA, "noise": NOISE, "family": FAM, "runs": []}
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as fh:
            results = json.load(fh)
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", {})]
    plan += [(f"{FAM} #{s}", {"shuffle_seed": s}) for s in range(1, n + 1)]
    for label, kw in plan:
        if label in done:
            continue
        results["runs"].append(measure(label, kw))       # serial: the cache races otherwise
        with open(PATH, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
    report(results)


# -- reporting -------------------------------------------------------------

def _p(n_ge, n):
    return (n_ge + 1) / (n + 1)


def _spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def _perm_p(x, y, rho, n_perm=20000, seed=0):
    """Two-sided permutation p for a correlation, by shuffling one side."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); y = np.asarray(y, float)
    n_ge = 0
    for _ in range(n_perm):
        if abs(_spearman(x, rng.permutation(y))) >= abs(rho) - 1e-12:
            n_ge += 1
    return (n_ge + 1) / (n_perm + 1)


def _e5():
    if not os.path.exists(E5_PATH):
        return {}
    with open(E5_PATH, encoding="utf-8") as fh:
        d = json.load(fh)
    return {r["label"]: r for r in d["runs"]}


def report(results):
    runs = results["runs"]
    real = next((r for r in runs if r["label"] == "real connectome"), None)
    ctrl = [r for r in runs if r["label"].startswith(FAM)]
    if real is None or not ctrl:
        return
    e5 = _e5()
    n = len(ctrl)
    print(f"\n=== experiment 10, {results['dataset']}: chords, fitted on chords ===")
    print(f"control family: {FAM} ({n} seeds).  one-sided permutation "
          f"p = (n_ge + 1) / (n + 1).")

    summary = {"n_ctrl": n, "readouts": {}}
    for tag, key, what in (("fit4 -> eval4", "eval4", "stage-4 accuracy, fitted on stage 4"),
                           ("fit4 -> eval3", "eval3", "stage-3 accuracy, fitted on stage 4")):
        print(f"\n-- {tag}: {what}")
        print(f"   {'readout':<9s} {'real':>7s}   {'rewired mean':>12s} {'sd':>6s}   "
              f"{'n_ge':>5s}  {'p':>6s}")
        for name in READOUTS:
            if name not in real["readouts"]:
                continue
            rv = real["readouts"][name][key]["accuracy"]
            cv = np.array([r["readouts"][name][key]["accuracy"] for r in ctrl])
            n_ge = int((cv >= rv).sum())
            print(f"   {name:<9s} {rv:7.3f}   {cv.mean():12.3f} {cv.std():6.3f}   "
                  f"{n_ge:2d}/{n:<2d}  {_p(n_ge, n):6.3f}")
            summary["readouts"].setdefault(name, {})[key] = {
                "real": rv, "ctrl_mean": float(cv.mean()), "ctrl_sd": float(cv.std()),
                "n_ge": n_ge, "n": n, "p": _p(n_ge, n)}

    # experiment 5's fit-on-3 numbers, for the same networks
    print("\n-- the transfer deficit: e5 fit3 -> eval4 against e10 fit4 -> eval4")
    print(f"   {'readout':<9s} {'real f3':>8s} {'real f4':>8s} {'real d':>7s}   "
          f"{'ctl f3':>7s} {'ctl f4':>7s} {'ctl d':>7s}   {'n_ge(d)':>8s} {'p':>6s}")
    deficits = {}
    for name in READOUTS:
        if name not in real["readouts"] or "real connectome" not in e5:
            continue
        r3 = e5["real connectome"]["readouts"][name]["transfer"]["accuracy"]
        r4 = real["readouts"][name]["eval4"]["accuracy"]
        rows = []
        for r in ctrl:
            lab = r["label"]
            if lab not in e5 or name not in e5[lab]["readouts"]:
                continue
            c3 = e5[lab]["readouts"][name]["transfer"]["accuracy"]
            c4 = r["readouts"][name]["eval4"]["accuracy"]
            rows.append((lab, c3, c4, c4 - c3, r["additivity"]["alpha_full"],
                         r["additivity"]["alpha_peak"]))
        if not rows:
            continue
        c3 = np.array([x[1] for x in rows]); c4 = np.array([x[2] for x in rows])
        dc = np.array([x[3] for x in rows]); rd = r4 - r3
        n_ge = int((dc >= rd).sum())
        print(f"   {name:<9s} {r3:8.3f} {r4:8.3f} {rd:+7.3f}   {c3.mean():7.3f} "
              f"{c4.mean():7.3f} {dc.mean():+7.3f}   {n_ge:3d}/{len(rows):<3d} "
              f"{_p(n_ge, len(rows)):6.3f}")
        deficits[name] = {"real_fit3": r3, "real_fit4": r4, "real_deficit": rd,
                          "ctrl_fit3": float(c3.mean()), "ctrl_fit4": float(c4.mean()),
                          "ctrl_deficit": float(dc.mean()), "n": len(rows),
                          "n_ge": n_ge, "p": _p(n_ge, len(rows)),
                          "rows": [{"label": x[0], "fit3_eval4": x[1], "fit4_eval4": x[2],
                                    "deficit": x[3], "alpha_full": x[4],
                                    "alpha_peak": x[5]} for x in rows]}
    summary["deficit"] = deficits

    # additivity per network
    print("\n-- chord additivity (alpha: 1 = additive, 0 = max-like, <0 = suppressive)")
    print(f"   {'network':<26s} {'alpha':>7s} {'a_peak':>7s} {'a_win':>7s} {'|A|/|S|':>8s} "
          f"{'|A|/|M|':>8s} {'cm gain':>8s} {'radius':>7s}")
    for r in [real] + ctrl:
        a = r["additivity"]
        print(f"   {r['label']:<26s} {a['alpha_full']:+7.3f} {a['alpha_peak']:+7.3f} "
              f"{a['alpha_window']:+7.3f} {a['norm_ratio_to_sum']:8.3f} "
              f"{a['norm_ratio_to_max']:8.3f} {a['common_mode_gain']:8.3f} "
              f"{r['stability']['spectral_radius']:7.2f}")
    al = np.array([r["additivity"]["alpha_full"] for r in ctrl])
    n_ge = int((al >= real["additivity"]["alpha_full"]).sum())
    print(f"   real alpha {real['additivity']['alpha_full']:+.3f} vs rewired "
          f"{al.mean():+.3f} +- {al.std():.3f}, {n_ge}/{n} >= real, p = {_p(n_ge, n):.3f} "
          f"(one-sided, real is highest if p is small)")
    summary["alpha"] = {"real": real["additivity"]["alpha_full"],
                        "ctrl_mean": float(al.mean()), "ctrl_sd": float(al.std()),
                        "n_ge": n_ge, "n": n, "p": _p(n_ge, n)}

    # the correlation this experiment is for
    print("\n-- additivity against the chord-transfer deficit, across rewired controls")
    corrs = {}
    for name, d in deficits.items():
        rows = d["rows"]
        if len(rows) < 4:
            continue
        for aname in ("alpha_full", "alpha_peak"):
            x = [r[aname] for r in rows]
            y = [r["deficit"] for r in rows]
            rho = _spearman(x, y)
            pear = float(np.corrcoef(x, y)[0, 1])
            pp = _perm_p(x, y, rho)
            print(f"   {name:<9s} {aname:<11s} n={len(rows):<3d} rho {rho:+.3f} "
                  f"(pearson {pear:+.3f})  two-sided perm p {pp:.3f}")
            corrs.setdefault(name, {})[aname] = {"n": len(rows), "spearman": rho,
                                                 "pearson": pear, "p_two_sided": pp}
    # pooled: deficit averaged over the four readouts
    if deficits:
        labs = sorted({r["label"] for d in deficits.values() for r in d["rows"]})
        x, y = [], []
        for lab in labs:
            ds = [r["deficit"] for d in deficits.values() for r in d["rows"] if r["label"] == lab]
            al_ = [r["alpha_full"] for d in deficits.values() for r in d["rows"] if r["label"] == lab]
            if ds:
                x.append(float(np.mean(al_))); y.append(float(np.mean(ds)))
        if len(x) >= 4:
            rho = _spearman(x, y)
            pp = _perm_p(x, y, rho)
            print(f"   {'pooled':<9s} {'alpha_full':<11s} n={len(x):<3d} rho {rho:+.3f} "
                  f"(pearson {float(np.corrcoef(x, y)[0, 1]):+.3f})  two-sided perm p {pp:.3f}")
            corrs["pooled"] = {"alpha_full": {"n": len(x), "spearman": rho,
                                              "pearson": float(np.corrcoef(x, y)[0, 1]),
                                              "p_two_sided": pp}}
    summary["correlation"] = corrs

    results["summary"] = summary
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        with open(PATH, encoding="utf-8") as fh:
            report(json.load(fh))
    else:
        main()
