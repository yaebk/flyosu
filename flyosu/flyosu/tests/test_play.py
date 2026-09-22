"""
Checks for the game side: environment, judge, encoder, controller, learner,
beatmap I/O, and the play-regime properties the game depends on.

    python -m tests.test_play            # everything (~2 min, builds the fly)
    python -m tests.test_play --fast     # only the parts that need no network
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import beatmap, encoder as E, learn as L, mania  # noqa: E402
from flyosu.controller import Controller, N_KEYS  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def test_mania():
    print("mania")
    w = mania.windows(8.0)
    check("OD 8 windows are osu!mania's", (w["300"], w["50"], w["MISS"]) == (40.0, 127.0, 164.0))
    check("judgment ladder", [mania.judge(e, 8.0) for e in (0, 16.1, 40, 60, 100, 120, 170)]
          == ["MAX", "300", "300", "200", "100", "50", "MISS"])

    for s in mania.STAGES:
        c = mania.stage_chart(s, n_notes=24, seed=1)
        check(f"stage {s} has 24 notes", len(c) == 24)
    c2 = mania.stage_chart(2, n_notes=24, seed=1)
    check("stage 2 uses every lane equally", np.bincount(c2.lanes(), minlength=4).tolist() == [6] * 4)
    c4 = mania.stage_chart(4, n_notes=40, seed=1)
    check("stage 4 has chords", len(np.unique(c4.times())) < 40)
    c5 = mania.stage_chart(5, n_notes=24, seed=1)
    check("stage 5 varies intervals", np.diff(c5.times()).std() > 50)

    # an oracle that presses each note exactly on time gets 100%
    c = mania.stage_chart(3, n_notes=20, seed=1)
    env = mania.ManiaEnv(c)
    while not env.done:
        for n in c.notes:
            if abs(n.hit_ms - env.t) < env.dt / 2:
                env.press(n.lane)
        env.step()
    r = env.result()
    check("oracle scores 1.000", r.accuracy == 1.0 and r.counts["MAX"] == 20)
    check("oracle has no stray presses", r.n_stray == 0)

    # never pressing: every note is retired as a MISS
    env = mania.ManiaEnv(c)
    while not env.done:
        env.step()
    r = env.result()
    check("silence is all MISS", r.counts["MISS"] == 20 and r.accuracy == 0.0)

    # a press far from any note is stray; one 100 ms late is a 100
    env = mania.ManiaEnv(c)
    first = c.notes[0]
    while env.t < first.hit_ms - 600:
        env.step()
    p = env.press(first.lane)
    check("early press is stray", p.note is None)
    while env.t < first.hit_ms + 100:
        env.step()
    p = env.press(first.lane)
    check("100 ms late is a 100", p.judgment == "100" and abs(p.error_ms - 100) < env.dt)
    p2 = env.press(first.lane)
    check("a judged note cannot be hit twice", p2.note is None or p2.note != 0)

    # visible notes have the right progress at the hit time
    env = mania.ManiaEnv(c)
    while env.t < first.hit_ms:
        env.step()
    vis = {i: prog for _, prog, i in env.visible()}
    check("note is at the judgment line at its hit time", abs(vis.get(0, 9) - 1.0) < 0.01,
          f"progress {vis.get(0)}")


def test_beatmap():
    print("beatmap")
    c = mania.stage_chart(4, n_notes=20, seed=3)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.osu")
        beatmap.write(c, p)
        back = beatmap.load(p)
    check("round-trip preserves notes",
          [(n.lane, n.hit_ms) for n in c.notes] == [(n.lane, n.hit_ms) for n in back.notes])
    check("round-trip preserves OD", back.od == c.od)
    txt = ("osu file format v14\n[General]\nMode: 3\n[Difficulty]\nCircleSize:4\n"
           "OverallDifficulty:7\n[HitObjects]\n64,192,1000,1,0,0:0:0:0:\n"
           "448,192,1500,128,0,2000:0:0:0:0:\n")
    c2 = beatmap.parse(txt)
    check("x -> lane", [n.lane for n in c2.notes] == [0, 3])
    check("hold note parsed", c2.notes[1].is_hold and c2.notes[1].end_ms == 2000.0)
    try:
        beatmap.parse(txt.replace("CircleSize:4", "CircleSize:7"))
        check("7K refused", False)
    except ValueError:
        check("7K refused", True)
    try:
        beatmap.parse(txt.replace("Mode: 3", "Mode: 0"))
        check("non-mania refused", False)
    except ValueError:
        check("non-mania refused", True)


def test_encoder_geometry():
    print("encoder")
    check("spawn/judgment elevations", (E.elevation(0.0), E.elevation(1.0)) == (E.EL_SPAWN, E.EL_JUDGE))
    check("lanes match experiment 1", E.LANE_AZ.tolist() == [-60.0, -20.0, 20.0, 60.0])


def test_controller_logic():
    print("controller")
    c = Controller(W=np.eye(N_KEYS), b=np.full(N_KEYS, -1.0), refractory_ms=100.0, smooth_ms=0.0)
    c.reset()
    z = np.zeros(N_KEYS)
    check("below threshold: no press", c.step(z, 0.0, 2.0) == [])
    z[2] = 2.0
    check("crossing fires the key", c.step(z, 2.0, 2.0) == [2])
    check("staying above does not re-fire", c.step(z, 4.0, 2.0) == [])
    z[2] = 0.0; c.step(z, 6.0, 2.0)
    z[2] = 2.0
    check("re-crossing inside the refractory period is blocked", c.step(z, 8.0, 2.0) == [])
    z[2] = 0.0; c.step(z, 200.0, 2.0); z[2] = 2.0
    check("re-crossing after the refractory period fires", c.step(z, 202.0, 2.0) == [2])
    p = c.params
    c2 = Controller.blank(); c2.params = p
    check("params round-trip", np.array_equal(c2.W, c.W) and np.array_equal(c2.b, c.b))
    check("20 parameters", c.n_params == 20)
    m = L.mask_for("thresholds")
    check("threshold mask covers b only", m.sum() == 4 and m[16:].all())


def test_with_network():
    from flyosu import model as M, play as P
    print("play regime")
    fly = M.build(regime="play")
    st = fly.stability()
    check("blank field is a fixed point", st["fixed_point"], f"drift {st['drift']:.1e}")
    check("continuous-time stable (max Re < 1)", st["max_real"] < 1.0, f"Re {st['max_real']:.2f}")
    check("gain is capped", st["max_gain"] < 10.0, f"max gain {st['max_gain']:.1f}")
    e1 = M.build()
    check("experiment-1 regime is unchanged (floor 0.05)", e1.meta["sigma_floor"] == 0.05)

    player = P.Player.untrained(fly, theta=1.5)
    check("normaliser has positive spread", (player.norm.sd > 0).all())
    W = player.controller.W
    check("anatomical wiring is a permutation",
          (W.sum(0) == 1).all() and (W.sum(1) == 1).all())

    chart = mania.stage_chart(1, n_notes=8, seed=1)
    r1 = player.play(chart)
    r2 = player.play(chart)
    check("play is deterministic", r1.judgments == r2.judgments and
          [p.t_ms for p in r1.presses] == [p.t_ms for p in r2.presses])
    check("untrained fly hits most notes in one lane", r1.hit_rate >= 0.5, r1.summary())
    check("its presses land in the right lane",
          all(p.lane == 1 for p in r1.presses if p.note is not None))

    # the readout learner moves only the parameters it is allowed to
    lrn = L.ReadoutLearner(player, stage=1, n_notes=4, interval_ms=500.0,
                           mask=L.mask_for("thresholds"), seed=0)
    W0 = player.controller.W.copy()
    lrn.episode()
    check("masked learning leaves W untouched", np.array_equal(W0, player.controller.W))
    check("episode recorded", len(lrn.history) == 1 and np.isfinite(lrn.history[0].reward))


def main():
    test_mania()
    test_beatmap()
    test_encoder_geometry()
    test_controller_logic()
    if "--fast" not in sys.argv:
        test_with_network()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
