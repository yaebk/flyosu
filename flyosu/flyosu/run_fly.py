#!/usr/bin/env python3
"""
Poke the fly from the command line.

    python run_fly.py                      # sweep the four lanes
    python run_fly.py --az -60 --el -25    # one point stimulus
    python run_fly.py --sweep              # tuning curve across azimuth
    python run_fly.py --fall D             # watch a note fall in one lane
    python run_fly.py --chord D K          # two notes at once
    python run_fly.py --control rewired    # same, on a randomised network
"""

from __future__ import annotations

import argparse

import numpy as np

from flyosu import model as M

LANES = {"D": -60.0, "F": -20.0, "J": 20.0, "K": 60.0}
EL_JUDGE = -25.0
EL_SPAWN = 35.0
BAR = "█"


def bar(v: float, lo: float, hi: float, width: int = 34) -> str:
    frac = 0.0 if hi <= lo else (v - lo) / (hi - lo)
    return BAR * max(0, min(width, int(round(frac * width))))


def _zscore(A):
    """Per-channel z-score across rows: each channel judged against its own
    baseline and spread, which is what makes the four comparable."""
    A = np.asarray(A, float)
    return (A - A.mean(0)) / (A.std(0) + 1e-12)


def _assign(Z):
    """Best one-to-one lane -> channel assignment (24 permutations)."""
    from itertools import permutations
    return list(max(permutations(range(Z.shape[1])),
                    key=lambda p: sum(Z[i, p[i]] for i in range(Z.shape[0]))))


def show(names, vals, note=""):
    lo, hi = float(np.min(vals)), float(np.max(vals))
    print(f"    {note}")
    for n, v in zip(names, vals):
        print(f"      {n:<5s} {bar(v, lo, hi):<34s} {v:.4f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--az", type=float, help="stimulus azimuth, deg")
    ap.add_argument("--el", type=float, default=EL_JUDGE, help="elevation, deg")
    ap.add_argument("--sweep", action="store_true", help="azimuth tuning curve")
    ap.add_argument("--fall", choices=list(LANES), help="watch a note descend")
    ap.add_argument("--chord", nargs=2, choices=list(LANES), help="two notes")
    ap.add_argument("--control", choices=["rewired", "retinotopy", "channels"],
                    help="run a randomised control instead")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    kw = {}
    if args.control:
        kw = {{"rewired": "shuffle_seed", "retinotopy": "retino_seed",
               "channels": "channel_seed"}[args.control]: args.seed}
    print(f"loading {'control: ' + args.control if args.control else 'real connectome'} ...")
    fly = M.build(**kw)
    print(fly.summary(), "\n")
    names = fly.readout.names

    if args.sweep:
        print("azimuth tuning (channel activity, centred; . = below, # = above)")
        azs = np.arange(-100, 101, 10.0)
        A = np.array([fly.channels(fly.look([(float(a), args.el, 1.0)]))
                      for a in azs])
        A -= A.mean(0)
        hi = np.abs(A).max()
        print("      az  " + "".join(f"{n:>9s}" for n in names))
        for a, row in zip(azs, A):
            cells = "".join(f"{v:>9.4f}" for v in row)
            spark = "".join("#" if v > 0.25 * hi else
                            ("." if v < -0.25 * hi else " ") for v in row)
            print(f"   {a:+6.0f}  {cells}   {spark}")
        return

    if args.fall:
        az = LANES[args.fall]
        print(f"a note falling in lane {args.fall} (azimuth {az:+.0f} deg)")
        r, _ = fly.net.run(fly.stimulus([]), duration_ms=400.0)
        els = np.linspace(EL_SPAWN, EL_JUDGE, 13)
        A = []
        for el in els:
            r, _ = fly.net.run(fly.stimulus([(az, float(el), 1.0)]),
                               duration_ms=60.0, r0=r)
            A.append(fly.channels(r))
        A = np.array(A)
        Z = _zscore(A)
        print("       el  " + "".join(f"{n:>9s}" for n in names) + "   loudest")
        for el, a, z in zip(els, A, Z):
            mark = "  <-- judgment line" if el <= EL_JUDGE else ""
            print(f"   {el:+6.1f}  " + "".join(f"{v:>9.4f}" for v in a)
                  + f"   {names[int(z.argmax())]}{mark}")
        return

    if args.chord:
        a, b = args.chord
        t = [(LANES[a], EL_JUDGE, 1.0), (LANES[b], EL_JUDGE, 1.0)]
        base = fly.channels(fly.look([]))
        show(names, fly.channels(fly.look(t)) - base, f"chord {a}+{b} (vs blank)")
        for k in (a, b):
            show(names, fly.channels(fly.look([(LANES[k], EL_JUDGE, 1.0)])) - base,
                 f"lane {k} alone")
        return

    if args.az is not None:
        show(names, fly.channels(fly.look([(args.az, args.el, 1.0)])),
             f"stimulus az={args.az:+.0f} el={args.el:+.0f}")
        return

    base = fly.channels(fly.look([]))
    D = np.array([fly.channels(fly.look([(az, EL_JUDGE, 1.0)])) - base
                  for az in LANES.values()])
    Z = _zscore(D)
    pick = _assign(Z)
    print("four lanes at the judgment line, activity relative to a blank field.")
    print("Each channel is z-scored against its own spread across the four "
          "lanes, then\nlanes are matched one-to-one to channels -- the same "
          "rule the experiment uses.\n")
    for (key, az), d, c in zip(LANES.items(), D, pick):
        show(names, d, f"lane {key}  (azimuth {az:+.0f} deg)"
                       f"   -> {names[c]}  (z = {Z[list(LANES).index(key), c]:+.2f})")


if __name__ == "__main__":
    main()
