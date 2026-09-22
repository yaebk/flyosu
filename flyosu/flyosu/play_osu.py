#!/usr/bin/env python3
"""
Let the fly play a beatmap in the real osu! client (step 12).

    python play_osu.py path/to/map.osu                  # simulate, print result
    python play_osu.py path/to/map.osu --sink keyboard  # ...then press real keys
    python play_osu.py --stage 3 --sink log             # a curriculum chart

How it works.  The simulation runs at roughly real time with no slack, so the
fly's brain is run on the beatmap *first* (deterministic, given the chart),
producing a list of key-press times.  Those are then replayed against the wall
clock, synchronised to the moment you start the map.  The beatmap is known to
the client in advance too; what is not known in advance is what the connectome
does with it, and that is what is simulated.

This is not screen-capture vision: the fly sees the encoder's rendering of the
beatmap (docs: encoder.py), not pixels from the client.  Closing that loop is a
separate project.

Keyboard output needs ``pip install pynput`` and has not been verified against
a live osu! client in this repository -- treat the ``keyboard`` sink as a
starting point.  Use ``--offset`` to compensate audio/display latency (positive
= press later) and ``--countdown`` to give yourself time to hit play.

Keys: D F J K, mania's default 4K binding.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time

from flyosu import beatmap, mania, model as M, play as P
from flyosu.mania import KEYS


class LogSink:
    """Prints presses as they happen."""

    def __init__(self):
        self.events = []

    def press(self, key: str, t_ms: float) -> None:
        self.events.append((t_ms, key))
        print(f"  {t_ms:8.0f} ms  {key}", flush=True)

    def close(self) -> None:
        pass


class KeyboardSink:
    """Real key presses through pynput; each key is held for ``hold_ms``."""

    def __init__(self, hold_ms: float = 30.0):
        try:
            from pynput.keyboard import Controller  # type: ignore
        except ImportError as e:      # pragma: no cover
            raise SystemExit("keyboard sink needs `pip install pynput`") from e
        self.kb = Controller()
        self.hold = hold_ms / 1000.0
        self.events = []

    def press(self, key: str, t_ms: float) -> None:
        self.events.append((t_ms, key))
        k = key.lower()
        self.kb.press(k)
        threading.Timer(self.hold, self.kb.release, args=(k,)).start()

    def close(self) -> None:
        time.sleep(self.hold * 2)


def simulate(player: P.Player, chart: mania.Chart) -> tuple[mania.PlayResult, list[tuple[float, str]]]:
    res = player.play(chart)
    presses = sorted((p.t_ms, KEYS[p.lane]) for p in res.presses)
    return res, presses


def replay(presses, sink, offset_ms: float = 0.0, speed: float = 1.0) -> None:
    """Fire the presses against the wall clock.  t = 0 is 'now'."""
    t0 = time.perf_counter()
    for t_ms, key in presses:
        due = t0 + (t_ms + offset_ms) / 1000.0 / speed
        while True:
            now = time.perf_counter()
            if now >= due:
                break
            time.sleep(min(0.002, due - now))
        sink.press(key, t_ms)
    sink.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beatmap", nargs="?", help=".osu file (4K mania)")
    ap.add_argument("--stage", type=int, help="use a curriculum chart instead")
    ap.add_argument("--notes", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--approach", type=float, default=800.0, help="scroll time, ms")
    ap.add_argument("--theta", type=float, default=2.0, help="untrained threshold")
    ap.add_argument("--params", help=".npy of 20 learned controller parameters")
    ap.add_argument("--sink", choices=["none", "log", "keyboard"], default="none")
    ap.add_argument("--offset", type=float, default=0.0, help="ms, + = press later")
    ap.add_argument("--countdown", type=float, default=3.0, help="seconds before t=0")
    ap.add_argument("--control", choices=["rewired", "retinotopy", "channels"])
    args = ap.parse_args()

    if args.stage:
        chart = mania.stage_chart(args.stage, n_notes=args.notes, seed=args.seed,
                                  approach_ms=args.approach)
    elif args.beatmap:
        chart = beatmap.load(args.beatmap, approach_ms=args.approach)
    else:
        ap.error("give a .osu file or --stage")
    print(chart.describe())

    kw = {}
    if args.control:
        kw = {{"rewired": "shuffle_seed", "retinotopy": "retino_seed",
               "channels": "channel_seed"}[args.control]: 1}
    print("building the fly (play regime) ...")
    fly = M.build(regime="play", **kw)
    player = P.Player.untrained(fly, theta=args.theta)
    if args.params:
        import numpy as np
        player.controller.params = np.load(args.params)
    print(player.describe())

    print("\nsimulating ...")
    res, presses = simulate(player, chart)
    print(f"predicted: {res.summary()}")
    print(f"{len(presses)} presses; sim {player.stats['seconds']:.0f} s for "
          f"{chart.end_ms / 1000:.0f} s of chart")
    if args.sink == "none":
        return

    sink = LogSink() if args.sink == "log" else KeyboardSink()
    print(f"\nstart the map so that its t=0 lands in {args.countdown:.0f} s ...")
    for i in range(int(args.countdown), 0, -1):
        print(f"  {i}", flush=True)
        time.sleep(1.0)
    print("  go", flush=True)
    replay(presses, sink, offset_ms=args.offset)
    print("done")


if __name__ == "__main__":
    main()
