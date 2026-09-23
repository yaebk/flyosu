"""
Experiment 1 -- does the fixed connectome map visual field position to
distinguishable motor output?

This is the question everything else depends on.  Before any learning, before
any osu! integration: stimulate different parts of the simulated visual field
and ask whether the four descending-neuron channels respond differently, and
whether the difference is reliable enough to decode which lane was stimulated.

Four probes:

  A  azimuth tuning      fine sweep of a single bright point across the visual
                         field; per-channel tuning curves
  B  lane decoding       four lanes with trial-to-trial jitter and sensory
                         noise; how well each processing stage identifies the
                         lane, and how well the four pooled channels do
  C  note approach       a note descending toward the judgment line; does the
                         motor output change as it arrives (timing signal)?
  D  chords              two simultaneous notes; is the pair represented, or
                         does one mask the other?

Every probe is run on the real connectome and on three families of matched
control network, 15 seeds each:

  rewired topology         the graph is randomly rewired (degree-preserving)
  shuffled retinotopy      same graph, each photoreceptor sees a random part
                           of the visual field
  shuffled channel labels  same everything, descending neurons assigned to the
                           four channels at random

The controls are what separate "the connectome does something" from "any network
with 19,367 nodes does this".  Three families rather than one because they
destroy different things, and pooling them into a single "control" distribution
answers a question nobody asked.

    python -m experiments.e1_sensorimotor
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import model as M  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results")

# The playfield is projected onto a cylindrical arena around the fly, the
# standard geometry for Drosophila visual experiments (LED arenas span ~270 deg).
# Four lanes at these azimuths; the judgment line sits below the horizon.
LANES = np.array([-60.0, -20.0, 20.0, 60.0])
KEYS = ("D", "F", "J", "K")
EL_SPAWN = 35.0
EL_JUDGE = -25.0
SIGMA = 10.0


# ---------------------------------------------------------------------------

def trial(fly, targets, noise: float, rng, duration_ms: float = 300.0):
    ext = fly.stimulus(targets, sigma_deg=SIGMA)
    if noise:
        p = fly.ph_local
        ext[p] = np.clip(ext[p] + rng.normal(0, noise, len(p)), 0, 1)
    r, _ = fly.net.run(ext, duration_ms=duration_ms)
    return r


def decode(X, y, seed=0):
    """Cross-validated multinomial decoding accuracy."""
    F = (X - X.mean(0)) / (X.std(0) + 1e-8)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    s = cross_val_score(LogisticRegression(max_iter=3000), F, y, cv=cv)
    return float(s.mean()), float(s.std())


def probe_a_tuning(fly, azimuths):
    """Channel and DN responses to a point source swept across azimuth."""
    ch, dn = [], []
    for az in azimuths:
        r = fly.look([(float(az), EL_JUDGE, 1.0)], sigma_deg=SIGMA)
        ch.append(fly.channels(r))
        dn.append(r[fly.dn])
    ch, dn = np.array(ch), np.array(dn)
    chc = ch - ch.mean(0)
    # preferred azimuth of each channel, and how sharply it is tuned
    pref = azimuths[chc.argmax(0)]
    depth = (ch.max(0) - ch.min(0)) / (ch.mean(0) + 1e-9)
    dnc = dn - dn.mean(0)
    sim = np.corrcoef(dnc)
    return {"azimuths": azimuths.tolist(),
            "channels": ch.tolist(),
            "channels_centred": chc.tolist(),
            "preferred_azimuth": pref.tolist(),
            "modulation_depth": depth.tolist(),
            "dn_similarity": sim.tolist(),
            "dn_delta_magnitude": np.abs(dnc).mean(1).tolist()}


def probe_b_lanes(fly, n_trials=40, noise=0.03, seed=0):
    """Decode lane identity from every stage, with jitter and sensory noise."""
    rng = np.random.default_rng(seed)
    sc = fly.class_of("super_class")
    R, y = [], []
    for li, az in enumerate(LANES):
        for _ in range(n_trials):
            a = az + rng.normal(0, 4.0)
            e = EL_JUDGE + rng.normal(0, 6.0)
            amp = rng.uniform(0.8, 1.0)
            R.append(trial(fly, [(a, e, amp)], noise, rng))
            y.append(li)
    R, y = np.array(R), np.array(y)

    stages = {
        "optic lobe": np.flatnonzero(sc == "optic")[:4000],
        "visual projection": np.flatnonzero(sc == "visual_projection"),
        "central brain": np.flatnonzero(sc == "central"),
        "descending (population)": fly.dn,
    }
    out = {}
    for name, idx in stages.items():
        if len(idx) == 0:
            continue
        m, s = decode(R[:, idx], y)
        out[name] = {"dim": int(len(idx)), "acc": m, "sd": s}

    ch = np.array([[r[g].mean() for g in fly.readout.groups] for r in R])
    m, s = decode(ch, y)
    out["4 pooled channels"] = {"dim": 4, "acc": m, "sd": s}

    # confusion of the simplest possible policy: press the key of the channel
    # whose activity deviates most from its own across-trial mean
    z = (ch - ch.mean(0)) / (ch.std(0) + 1e-9)
    pred = z.argmax(1)
    conf = np.zeros((4, 4), int)
    for t, p in zip(y, pred):
        conf[t, p] += 1
    best = _best_assignment(conf)
    out["argmax_policy"] = {
        "confusion": conf.tolist(),
        "channel_for_lane": [fly.readout.names[i] for i in best],
        "accuracy": float(sum(conf[i, best[i]] for i in range(4)) / conf.sum()),
    }
    return out


def _best_assignment(conf):
    """Best lane -> channel assignment (4! = 24 permutations, just enumerate)."""
    from itertools import permutations
    return list(max(permutations(range(4)),
                    key=lambda p: sum(conf[i, p[i]] for i in range(4))))


def probe_c_approach(fly, lane_idx=1, steps=13, seed=0):
    """Does motor output change as a note descends toward the judgment line?

    The network state is carried from step to step, so this is a real
    trajectory rather than a sequence of independent settles.  It starts from
    the blank-field steady state -- starting from zero would put a large
    cold-start transient on the first sample and fake a trend.
    """
    els = np.linspace(EL_SPAWN, EL_JUDGE, steps)
    az = float(LANES[lane_idx])
    r, _ = fly.net.run(fly.stimulus([], sigma_deg=SIGMA), duration_ms=400.0)
    ch = []
    for el in els:
        r, _ = fly.net.run(fly.stimulus([(az, float(el), 1.0)], sigma_deg=SIGMA),
                           duration_ms=60.0, r0=r)
        ch.append(fly.channels(r))
    ch = np.array(ch)
    chc = ch - ch.mean(0)
    # how much of the approach is linearly readable: correlate each channel
    # with elevation and take the strongest
    rho = [float(np.corrcoef(els, chc[:, i])[0, 1]) for i in range(4)]
    return {"elevations": els.tolist(), "channels": ch.tolist(),
            "channels_centred": chc.tolist(), "lane": az, "warmed": True,
            "elevation_correlation": rho,
            "max_abs_correlation": float(np.max(np.abs(rho)))}


def probe_d_chords(fly, seed=0):
    """Are two simultaneous notes represented as their own state?"""
    singles, combos = {}, {}
    for i, az in enumerate(LANES):
        singles[i] = fly.look([(float(az), EL_JUDGE, 1.0)], sigma_deg=SIGMA)[fly.dn]
    base = fly.look([], sigma_deg=SIGMA)[fly.dn]
    rows = []
    for i in range(4):
        for j in range(i + 1, 4):
            r = fly.look([(float(LANES[i]), EL_JUDGE, 1.0),
                          (float(LANES[j]), EL_JUDGE, 1.0)], sigma_deg=SIGMA)[fly.dn]
            d_pair = r - base
            d_sum = (singles[i] - base) + (singles[j] - base)
            rows.append({
                "lanes": [KEYS[i], KEYS[j]],
                "linearity": float(np.corrcoef(d_pair, d_sum)[0, 1]),
                "gain": float(np.linalg.norm(d_pair) / (np.linalg.norm(d_sum) + 1e-12)),
                "vs_lane_i": float(np.corrcoef(d_pair, singles[i] - base)[0, 1]),
                "vs_lane_j": float(np.corrcoef(d_pair, singles[j] - base)[0, 1]),
            })
    combos["pairs"] = rows
    combos["mean_linearity"] = float(np.mean([r["linearity"] for r in rows]))
    combos["mean_gain"] = float(np.mean([r["gain"] for r in rows]))
    return combos


# ---------------------------------------------------------------------------

def run_one(label, fly, n_trials, seed):
    t0 = time.time()
    print(f"\n=== {label}  ({fly.net.n:,} neurons, {fly.net.n_edges:,} edges)")
    out = {"label": label, "n_neurons": fly.net.n, "n_edges": fly.net.n_edges,
           "channels": fly.readout.names, "channel_sizes": fly.readout.sizes()}

    out["A_tuning"] = probe_a_tuning(fly, np.arange(-100, 101, 5.0))
    print("  A  preferred azimuth per channel: "
          + "  ".join(f"{n}={p:+.0f}deg" for n, p in
                      zip(fly.readout.names, out["A_tuning"]["preferred_azimuth"])))
    print("     modulation depth: "
          + "  ".join(f"{d:.3f}" for d in out["A_tuning"]["modulation_depth"]))

    out["B_lanes"] = probe_b_lanes(fly, n_trials=n_trials, seed=seed)
    print("  B  lane decoding (chance 0.250):")
    for k, v in out["B_lanes"].items():
        if k == "argmax_policy":
            continue
        print(f"       {k:<26s} dim={v['dim']:>5d}  {v['acc']:.3f} +/- {v['sd']:.3f}")
    ap = out["B_lanes"]["argmax_policy"]
    print(f"       untrained argmax policy      acc={ap['accuracy']:.3f}  "
          f"lane->channel {ap['channel_for_lane']}")

    out["C_approach"] = probe_c_approach(fly)
    print(f"  C  note approach: max |corr(channel, elevation)| = "
          f"{out['C_approach']['max_abs_correlation']:.3f}")

    out["D_chords"] = probe_d_chords(fly)
    print(f"  D  chords: mean linearity {out['D_chords']['mean_linearity']:.3f}  "
          f"mean gain {out['D_chords']['mean_gain']:.3f}")
    out["seconds"] = round(time.time() - t0, 1)
    return out


CONTROLS = [
    ("rewired topology", "shuffle_seed"),
    ("shuffled retinotopy", "retino_seed"),
    ("shuffled channel labels", "channel_seed"),
]


def main():
    os.makedirs(RESULTS, exist_ok=True)
    n_trials = int(os.environ.get("N_TRIALS", 60))
    n_seeds = int(os.environ.get("N_SEEDS", 5))

    path = os.path.join(RESULTS, "e1_sensorimotor.json")
    results = {"lanes": LANES.tolist(), "keys": list(KEYS),
               "el_judge": EL_JUDGE, "el_spawn": EL_SPAWN, "sigma_deg": SIGMA,
               "n_trials_per_lane": n_trials, "n_control_seeds": n_seeds,
               "runs": []}
    if os.environ.get("RESUME") and os.path.exists(path):
        with open(path) as fh:
            prev = json.load(fh)
        if prev.get("n_trials_per_lane") == n_trials:
            results = prev
            results["n_control_seeds"] = n_seeds
            print(f"resuming: {len(results['runs'])} runs already done")
    done = {r["label"] for r in results["runs"]}

    if "real connectome" not in done:
        print("building real connectome model ...")
        real = M.build(verbose=False)
        r = run_one("real connectome", real, n_trials, 0)
        r["family"] = "real"
        results["runs"].append(r)
        print(real.summary())
        _save(results)

    for family, kwarg in CONTROLS:
        for seed in range(1, n_seeds + 1):
            label = f"{family} #{seed}"
            if label in done:
                continue
            print(f"\nbuilding {family} control (seed {seed}) ...")
            ctrl = M.build(verbose=False, **{kwarg: seed})
            r = run_one(label, ctrl, n_trials, seed)
            r["family"] = family
            results["runs"].append(r)
            del ctrl
            _save(results)

    _save(results)
    _report(results)


def _save(results):
    with open(os.path.join(RESULTS, "e1_sensorimotor.json"), "w") as fh:
        json.dump(results, fh, indent=1)


def _report(results):
    metrics = [("descending (population)", lambda r: r["B_lanes"]["descending (population)"]["acc"]),
               ("4 pooled channels", lambda r: r["B_lanes"]["4 pooled channels"]["acc"]),
               ("argmax policy", lambda r: r["B_lanes"]["argmax_policy"]["accuracy"]),
               ("max channel modulation", lambda r: max(r["A_tuning"]["modulation_depth"])),
               ("note-approach signal", lambda r: r["C_approach"]["max_abs_correlation"]),
               ("chord linearity", lambda r: r["D_chords"]["mean_linearity"])]
    fams = ["real"] + [f for f, _ in CONTROLS]
    print("\n--- summary (mean +/- sd over seeds; chance = 0.250) ----------")
    print(f"{'condition':<26s}" + "".join(f"{n:>26s}" for n, _ in metrics))
    summary = {}
    for fam in fams:
        rows = [r for r in results["runs"] if r.get("family") == fam]
        if not rows:
            continue
        cells, store = [], {}
        for name, fn in metrics:
            v = np.array([fn(r) for r in rows])
            store[name] = {"mean": float(v.mean()), "sd": float(v.std()),
                           "values": v.tolist()}
            cells.append(f"{v.mean():>19.3f}{'':>2s}"
                         + (f"+-{v.std():.3f}" if len(v) > 1 else "      "))
        summary[fam] = store
        print(f"{fam:<26s}" + "".join(cells))

    # Permutation test.  Reported per control family as well as pooled: the
    # three families destroy different things, so pooling them into one "the
    # control" distribution answers a question nobody asked.  The direct test
    # of "does the topology matter" is the rewired-topology family alone.
    def _perm(real, v):
        v = np.asarray(v, float)
        n_ge = int((v >= real).sum())
        return {"real": float(real), "control_mean": float(v.mean()),
                "control_sd": float(v.std()), "n_controls": int(len(v)),
                "n_ge": n_ge, "p": float((n_ge + 1) / (len(v) + 1)),
                "effect_sd": float((real - v.mean()) / (v.std() + 1e-12))}

    print("\n--- permutation test (p floor is 1/(n+1)) ---------------------")
    perm, by_family = {}, {}
    for name, _ in metrics:
        real = summary["real"][name]["mean"]
        pool = np.concatenate([summary[f][name]["values"] for f, _ in CONTROLS])
        perm[name] = _perm(real, pool)
        by_family[name] = {f: _perm(real, summary[f][name]["values"])
                           for f, _ in CONTROLS}
        print(f"  {name}   real {real:.3f}")
        for f, _ in CONTROLS:
            q = by_family[name][f]
            print(f"     vs {f:<24s} {q['control_mean']:.3f}+-{q['control_sd']:.3f}"
                  f" | {q['n_ge']}/{q['n_controls']} reach it"
                  f" | p={q['p']:.3f} | {q['effect_sd']:+.2f} SD")
        q = perm[name]
        print(f"     vs {'all pooled':<24s} {q['control_mean']:.3f}+-{q['control_sd']:.3f}"
              f" | {q['n_ge']}/{q['n_controls']} reach it"
              f" | p={q['p']:.3f} | {q['effect_sd']:+.2f} SD")
    results["permutation_by_family"] = by_family
    results["summary"] = summary
    results["permutation"] = perm
    _save(results)


if __name__ == "__main__":
    main()
