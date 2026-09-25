#!/usr/bin/env python3
"""
Watch the fly play in the terminal.

    python run_play.py                         # stage 2, untrained
    python run_play.py --stage 3 --theta 1.5   # random lanes, lower threshold
    python run_play.py --stage 1 --learn 20    # train 20 episodes, then play
    python run_play.py --control rewired       # same, on a rewired network
    python run_play.py --stability             # is the blank field a fixed point?

Each row of the playfield is a 20 ms frame: the four lanes show the note
(``o`` falling, ``=`` at the judgment line), the four drive columns show how
close each key is to firing, and presses are marked with the judgment.
"""

from __future__ import annotations

import argparse


from flyosu import learn as L, mania, model as M, play as P
from flyosu.mania import KEYS


def render(res: mania.PlayResult, every_ms: float = 20.0) -> None:
    tr = res.trace
    presses = {round(p.t_ms): p for p in res.presses}
    step = max(1, int(round(every_ms / (tr.t[1] - tr.t[0]))))
    print("\n     t(ms) | D F J K |" + "".join(f"{k:>7s}" for k in KEYS) + " | presses")
    for i in range(0, len(tr.t), step):
        t = tr.t[i]
        lanes = [" "] * 4
        for lane, prog, *_ in tr.visible[i]:
            lanes[lane] = "=" if abs(prog - 1.0) < 0.05 else ("o" if prog < 1 else ".")
        d = tr.drive[i]
        cells = "".join(f"{v:7.2f}" for v in d)
        window = [presses[k] for k in range(int(round(t)), int(round(t + every_ms))) if k in presses]
        marks = "  ".join(f"{KEYS[p.lane]}:{p.judgment or 'stray'}" for p in window)
        print(f"  {t:8.0f} | {' '.join(lanes)} |{cells} | {marks}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", type=int, default=2, choices=sorted(mania.STAGES))
    ap.add_argument("--notes", type=int, default=12)
    ap.add_argument("--interval", type=float, default=600.0, help="ms between notes")
    ap.add_argument("--theta", type=float, default=2.0, help="press threshold, z units")
    ap.add_argument("--noise", type=float, default=0.0, help="photoreceptor noise sd")
    ap.add_argument("--learn", type=int, default=0, help="episodes of readout learning first")
    ap.add_argument("--blank", action="store_true", help="start learning from W = 0")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--control", choices=["rewired", "retinotopy", "channels"])
    ap.add_argument("--regime", default="play", choices=sorted(M.REGIMES))
    ap.add_argument("--stability", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="no frame-by-frame render")
    args = ap.parse_args()

    kw = {}
    if args.control:
        kw = {{"rewired": "shuffle_seed", "retinotopy": "retino_seed",
               "channels": "channel_seed"}[args.control]: args.seed}
    print(f"loading {'control: ' + args.control if args.control else 'real connectome'} "
          f"({args.regime} regime) ...")
    fly = M.build(regime=args.regime, **kw)
    if args.stability:
        s = fly.stability()
        print(f"blank field: {'fixed point' if s['fixed_point'] else 'NOT a fixed point'}"
              f"  drift {s['drift']:.2e}  spectral radius {s['spectral_radius']:.2f}"
              f"  max Re {s['max_real']:.2f}  max gain {s['max_gain']:.1f}")
        return

    player = P.Player.untrained(fly, theta=args.theta, noise=args.noise, wired=not args.blank)
    print(player.describe())

    if args.learn:
        print(f"\nlearning for {args.learn} episodes on stage {args.stage} ...")
        before = L.evaluate(player, stage=args.stage, n_charts=2)
        print(f"  before: acc {before['accuracy']:.3f}  hit {before['hit_rate']:.3f}  "
              f"lane-correct {before['lane_correct']:.2f}")
        L.ReadoutLearner(player, stage=args.stage, sigma=0.2, seed=args.seed).run(args.learn)
        after = L.evaluate(player, stage=args.stage, n_charts=2)
        print(f"  after : acc {after['accuracy']:.3f}  hit {after['hit_rate']:.3f}  "
              f"lane-correct {after['lane_correct']:.2f}")
        print(player.controller.wiring(fly.readout.names))

    chart = mania.stage_chart(args.stage, n_notes=args.notes, interval_ms=args.interval,
                              seed=args.seed)
    print("\n" + chart.describe())
    res = player.play(chart, record=not args.quiet)
    if not args.quiet:
        render(res)
    print("\n" + res.summary())
    print(f"{player.stats['ms_per_frame']:.2f} ms wall per {player.dt:g} ms frame")
    print("lane confusion (rows: true lane, cols: pressed):")
    print(res.lane_confusion)


if __name__ == "__main__":
    main()
