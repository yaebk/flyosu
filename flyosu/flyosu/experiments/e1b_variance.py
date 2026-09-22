"""
Experiment 1b -- how much of the control spread is real, and how much is noise?

Experiment 1 compares one real network against 45 randomised ones and finds the
real network above every control mean, but not beyond the control spread
(p ~ 0.09 on the best metric).  Before reading anything into that, it is worth
knowing what the spread is made of.  Each control run's score varies for two
reasons stacked on top of each other:

  * network variance   -- a different random rewiring
  * estimation noise   -- a different draw of 240 jittered, noisy trials, and a
                          different cross-validation split

Only the first is interesting.  This script measures the second directly: it
simulates one large trial pool per network, then bootstrap-resamples 240-trial
subsets to get the sampling distribution of the accuracy estimate for a *fixed*
network.  Subtracting that from the observed control spread leaves the part
that is genuinely about the wiring.

It also gives the real network its own error bar, which experiment 1 cannot:
there is only one real connectome, so its single score has no visible
uncertainty even though it is estimated exactly the same way.

    python -m experiments.e1b_variance
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.e1_sensorimotor import (  # noqa: E402
    LANES, EL_JUDGE, RESULTS, SIGMA, _best_assignment, decode, trial)
from flyosu import model as M  # noqa: E402

POOL = 200          # trials per lane simulated once
DRAW = 60           # trials per lane in each resampled estimate (matches exp 1)
N_BOOT = 200


def channel_pool(fly, n_per_lane, noise=0.03, seed=0):
    """Simulate a large pool of trials and keep the four channel activations."""
    rng = np.random.default_rng(seed)
    ch, y = [], []
    for li, az in enumerate(LANES):
        for _ in range(n_per_lane):
            a = az + rng.normal(0, 4.0)
            e = EL_JUDGE + rng.normal(0, 6.0)
            r = trial(fly, [(a, e, rng.uniform(0.8, 1.0))], noise, rng)
            ch.append([r[g].mean() for g in fly.readout.groups])
            y.append(li)
    return np.array(ch, np.float32), np.array(y)


def argmax_accuracy(ch, y):
    z = (ch - ch.mean(0)) / (ch.std(0) + 1e-9)
    pred = z.argmax(1)
    conf = np.zeros((4, 4), int)
    for t, p in zip(y, pred):
        conf[t, p] += 1
    best = _best_assignment(conf)
    return float(sum(conf[i, best[i]] for i in range(4)) / conf.sum())


def bootstrap(ch, y, n_boot=N_BOOT, draw=DRAW, seed=0):
    rng = np.random.default_rng(seed)
    by_lane = [np.flatnonzero(y == i) for i in range(4)]
    dec, arg = [], []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(g, draw, replace=False) for g in by_lane])
        dec.append(decode(ch[idx], y[idx])[0])
        arg.append(argmax_accuracy(ch[idx], y[idx]))
    return np.array(dec), np.array(arg)


def main():
    out = {"pool_per_lane": POOL, "draw_per_lane": DRAW, "n_boot": N_BOOT,
           "networks": {}}
    jobs = [("real connectome", {}),
            ("rewired topology #1", {"shuffle_seed": 1}),
            ("rewired topology #2", {"shuffle_seed": 2})]

    for name, kw in jobs:
        print(f"\n{name}: simulating {POOL * 4} trials ...")
        fly = M.build(verbose=False, **kw)
        ch, y = channel_pool(fly, POOL, seed=hash(name) % 2**31)
        dec, arg = bootstrap(ch, y)
        out["networks"][name] = {
            "decode_mean": float(dec.mean()), "decode_sd": float(dec.std()),
            "decode_ci": [float(np.percentile(dec, 2.5)),
                          float(np.percentile(dec, 97.5))],
            "argmax_mean": float(arg.mean()), "argmax_sd": float(arg.std()),
            "argmax_ci": [float(np.percentile(arg, 2.5)),
                          float(np.percentile(arg, 97.5))],
        }
        d = out["networks"][name]
        print(f"   4-channel decoding {d['decode_mean']:.3f} +/- {d['decode_sd']:.3f}"
              f"  95% CI [{d['decode_ci'][0]:.3f}, {d['decode_ci'][1]:.3f}]")
        print(f"   argmax policy      {d['argmax_mean']:.3f} +/- {d['argmax_sd']:.3f}"
              f"  95% CI [{d['argmax_ci'][0]:.3f}, {d['argmax_ci'][1]:.3f}]")
        del fly

    # compare against the across-network spread measured in experiment 1
    path = os.path.join(RESULTS, "e1_sensorimotor.json")
    if os.path.exists(path):
        with open(path) as fh:
            e1 = json.load(fh)
        for key, metric in (("decode", "4 pooled channels"),
                            ("argmax", "argmax policy")):
            obs = float(e1["permutation"][metric]["control_sd"])
            est = float(np.mean([out["networks"][n][f"{key}_sd"]
                                 for n in out["networks"] if "rewired" in n]))
            true = float(np.sqrt(max(obs ** 2 - est ** 2, 0.0)))
            out.setdefault("decomposition", {})[metric] = {
                "observed_control_sd": obs, "estimation_sd": est,
                "network_sd": true}
            print(f"\n{metric}: control spread {obs:.3f}"
                  f"  =  estimation noise {est:.3f}"
                  f"  +  wiring {true:.3f}  (in quadrature)")

    with open(os.path.join(RESULTS, "e1b_variance.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote results/e1b_variance.json")


if __name__ == "__main__":
    main()
