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

    # Stage 6 is the only generator that puts two notes in the same lane at the
    # interval; every other stage spreads them over four lanes, which is why
    # the controller's refractory never binds on stages 1-5 (experiment 18).
    c6 = mania.stage_chart(6, n_notes=40, interval_ms=300.0, seed=1)
    t6, l6 = c6.times(), c6.lanes()
    same = int((np.diff(l6) == 0).sum())
    check("stage 6 makes jacks", same > 5, f"{same} same-lane repeats of 39")
    gaps = [np.diff(np.sort(t6[l6 == k])).min() for k in range(4) if (l6 == k).sum() > 1]
    check("stage 6 reaches the interval in one lane", min(gaps) == 300.0,
          f"min same-lane gap {min(gaps):.0f} ms")
    c3 = mania.stage_chart(3, n_notes=40, interval_ms=300.0, seed=1)
    t3, l3 = c3.times(), c3.lanes()
    g3 = [np.diff(np.sort(t3[l3 == k])).min() for k in range(4) if (l3 == k).sum() > 1]
    check("stage 3 never does", min(g3) >= 300.0)
    check("an unknown stage is rejected", _raises(lambda: mania.stage_chart(8)))
    c7 = mania.stage_chart(7, n_notes=40, interval_ms=600.0, seed=1)
    holds = [n for n in c7.notes if n.is_hold]
    check("stage 7 makes hold notes", 5 < len(holds) < 40, f"{len(holds)} of 40")
    check("no hold outlives its lane's next note",
          all(h.end_ms < min((n.hit_ms for n in c7.notes
                              if n.lane == h.lane and n.hit_ms > h.hit_ms), default=1e9)
              for h in holds))

    # -- hold notes --------------------------------------------------------
    # One 1000 ms hold in lane 0. A hold scores the worse of its head and its
    # tail, so there are four cases worth pinning: clean, early release, never
    # released, and never pressed.
    def _hold_chart():
        return mania.Chart([mania.Note(0, 2000.0, end_ms=3000.0)], od=8.0)

    def _run(press_at, release_at):
        env = mania.ManiaEnv(_hold_chart(), dt_ms=5.0)
        while not env.done:
            if press_at is not None and abs(env.t - press_at) < env.dt / 2:
                env.press(0)
            if release_at is not None and abs(env.t - release_at) < env.dt / 2:
                env.release(0)
            env.step()
        return env.result()

    check("chart end waits for the tail", _hold_chart().end_ms == 3000.0)
    r = _run(2000.0, 3000.0)
    check("clean hold scores MAX", r.judgments == ["MAX"], str(r.judgments))
    r = _run(2000.0, 2500.0)
    check("early release misses the hold", r.judgments == ["MISS"], str(r.judgments))
    r = _run(2000.0, None)
    check("never releasing misses the hold", r.judgments == ["MISS"], str(r.judgments))
    r = _run(None, None)
    check("unpressed hold is a MISS", r.judgments == ["MISS"], str(r.judgments))
    # the head still limits the note: a late head cannot be rescued by a clean tail
    r = _run(2000.0 + 90.0, 3000.0)   # 90 ms is inside the 100 window (103 at OD 8)
    check("a bad head caps the hold", r.judgments == ["100"], str(r.judgments))
    # the tail is more forgiving than a normal note, but not unboundedly
    r = _run(2000.0, 3000.0 + 55.0)
    check("tail leniency is 1.5x", r.judgments == ["300"], str(r.judgments))
    check("worse() orders judgments", mania.worse("MAX", "100") == "100"
          and mania.worse("MISS", "MAX") == "MISS")

    # The fly has to be able to *see* a hold, or no readout on top of the input
    # can learn when to let go -- experiment 20's finding. These pin the
    # rendering: an ordinary note is one point exactly as before, a hold is a
    # head plus a dimmer body, and once the head is taken only the shrinking
    # body remains.
    enc = E.Encoder.__new__(E.Encoder)
    enc.intensity, enc.loom, enc.loom_exp = 1.0, 0.0, 1.0
    enc.hold_intensity, enc.hold_step, enc.hold_points = 0.6, 0.08, 10
    check("an ordinary note is still one point",
          enc.targets([(0, 0.5, 0, None)]) == [(-60.0, 5.0, 1.0)])
    body = enc.targets([(0, 0.5, 0, 0.1)])
    check("a hold is a head plus a body", len(body) > 1 and body[0][2] == 1.0
          and all(p[2] < 1.0 for p in body[1:]), f"{len(body)} points")
    check("the body sits above the head",
          all(p[1] > body[0][1] for p in body[1:]))
    held = enc.targets([(0, 2.5, 0, 0.6)])
    check("a held note drops its head", len(held) > 0
          and all(p[2] < 1.0 for p in held), f"{len(held)} points")
    check("a finished hold renders nothing", enc.targets([(0, 2.5, 0, 1.2)]) == [])
    # and the environment keeps a held note on screen
    env = mania.ManiaEnv(_hold_chart(), dt_ms=5.0)
    while env.t < 2000.0 - env.dt:
        env.step()
    env.press(0)
    env.step()
    check("a held note stays visible", any(v[3] is not None for v in env.visible()))

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

    # Accuracy is a weighted mean over NOTES and cannot see a press that lands
    # on nothing.  Experiment 16 found the rewired controls exploiting exactly
    # this -- 2.21 strays per note against the real network's 0.48, on a
    # measure that charges nothing for them -- and every threshold this project
    # chose by argmax over an accuracy sweep sat at the bottom of the sweep as a
    # result.  These checks pin the semantics so the blindness cannot be
    # quietly fixed, which would silently invalidate every number already
    # published against it, and so that `reward` remains the measure that does
    # charge for strays.
    # Junk presses are confined to the lead-in, before the earliest note is
    # anywhere near its window, so they cannot judge a note by accident; the
    # check above established that a press 600 ms early is stray.  Play is then
    # perfect, so any drop in accuracy would have to come from the strays.
    env = mania.ManiaEnv(c)
    n_junk = 0
    while env.t < c.notes[0].hit_ms - 600:
        env.press(c.notes[0].lane)
        n_junk += 1
        env.step()
    while not env.done:
        for n in c.notes:
            if abs(n.hit_ms - env.t) < env.dt / 2:
                env.press(n.lane)
        env.step()
    r_mash = env.result()
    check("mashing does not cost accuracy", r_mash.accuracy == 1.0 and n_junk > 0,
          f"accuracy {r_mash.accuracy:.3f} after {n_junk} junk presses")
    check("mashing does show up in n_stray", r_mash.n_stray == n_junk,
          f"n_stray {r_mash.n_stray}, junk {n_junk}")
    check("reward does charge for strays", L.reward(r_mash) < r_mash.accuracy,
          f"reward {L.reward(r_mash):+.3f} vs accuracy {r_mash.accuracy:.3f}")

    # visible notes have the right progress at the hit time
    env = mania.ManiaEnv(c)
    while env.t < first.hit_ms:
        env.step()
    vis = {i: prog for _, prog, i, *_ in env.visible()}
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

    # per-key delays (experiment 8's recommendation): a crossing schedules a
    # press instead of making one.  Zero delay must be the old behaviour.
    def run(ctrl, spikes, T=400, dt=2.0):
        ctrl.reset(); out = []
        for i in range(T):
            t = i * dt
            z = np.zeros(N_KEYS)
            for (at, k) in spikes:
                if abs(t - at) < dt / 2:
                    z[k] = 2.0
            for kk in ctrl.step(z, t, dt):
                out.append((t, kk))
        return out
    base = Controller(W=np.eye(N_KEYS), b=np.full(N_KEYS, -1.0), refractory_ms=100.0, smooth_ms=0.0)
    spikes = [(100.0, 0), (300.0, 2)]
    a = run(base, spikes)
    check("zero delay reproduces the undelayed controller",
          run(base.with_delays(np.zeros(N_KEYS)), spikes) == a, str(a))
    d = run(base.with_delays([60.0, 0.0, 20.0, 0.0]), spikes)
    check("each key waits its own delay",
          [(t, k) for t, k in d] == [(160.0, 0), (320.0, 2)], str(d))
    check("delays cannot be negative",
          np.array_equal(base.with_delays([-50.0, 10.0, 0.0, 30.0]).delay_ms,
                         np.array([0.0, 10.0, 0.0, 30.0])))
    check("a delayed controller copies its delays",
          np.array_equal(base.with_delays([1., 2., 3., 4.]).copy().delay_ms,
                         np.array([1., 2., 3., 4.])))


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


def test_probes():
    """The time-resolved probes, on a synthetic set of traces."""
    from flyosu import probes as PR
    print("probes")
    t = np.arange(-800.0, 240.0, 2.0)
    z = np.zeros((4, len(t), N_KEYS))
    for lane in range(4):                      # each lane drives its own channel, on time
        z[lane, :, lane] = 3.0 * np.exp(-0.5 * (t / 60.0) ** 2)
    tr = PR.LaneTraces(t=t, z=z, approach_ms=800.0)
    wiring = [0, 1, 2, 3]
    st = PR.shared_threshold(tr, wiring)
    check("clean traces: one threshold works", st["one_theta_works"] and st["shared_band"] > 2.0,
          f"band {st['shared_band']:.2f}")
    cr = PR.crossings(tr, wiring, theta=1.5)
    check("all four lanes cross on time", cr["n_fire"] == 4 and cr["n_on_time"] == 4)
    check("no wrong key is driven", cr["n_false_keys"] == 0)
    check("timing is centred on the line", abs(PR.timing(tr, wiring)["peak_lag_mean_ms"]) < 2.0)
    check("selectivity is total", PR.selectivity(tr, wiring)["argmax_mean"] == 1.0)

    # four lanes at four different scales, each still winning its own channel:
    # perfectly selective, and yet no single threshold serves all four keys,
    # because a loud lane's crosstalk outruns a quiet lane's own response.
    bump = np.exp(-0.5 * (t / 60.0) ** 2)
    z2 = np.zeros_like(z)
    for lane, amp in enumerate((5.0, 1.0, 3.0, 2.0)):
        z2[lane] = 0.9 * amp * bump[:, None]
        z2[lane, :, lane] = amp * bump
    tr2 = PR.LaneTraces(t=t, z=z2, approach_ms=800.0)
    st2 = PR.shared_threshold(tr2, wiring)
    check("a mismatched channel breaks the shared threshold", not st2["one_theta_works"])
    check("but every lane still wins its own channel",
          PR.selectivity(tr2, wiring)["argmax_mean"] == 1.0)
    check("per-key thresholds exist for it",
          all(np.isfinite(st2["theta_per_key"])) and len(st2["theta_per_key"]) == 4)

    # the two wiring rules: the margin rule takes the permutation with the
    # largest summed response, the band rule the one leaving the widest band of
    # thresholds that serves all four keys.  They are different rules -- on
    # random response matrices they disagree about a third of the time.
    from itertools import permutations
    from flyosu.controller import best_assignment
    rng = np.random.default_rng(0)
    n_dis, exact = 0, True
    for _ in range(40):
        A = rng.gamma(1.5, 1.0, (4, N_KEYS))
        tr4 = PR.LaneTraces(t=t, z=A[:, None, :] * bump[None, :, None], approach_ms=800.0)
        m = best_assignment(tr4.z[:, tr4.window(-400.0, 0.0)].mean(axis=1))
        b = PR.band_assignment(tr4)
        best = max(PR.shared_threshold(tr4, list(p))["shared_band"] for p in permutations(range(N_KEYS)))
        exact &= abs(PR.shared_threshold(tr4, b)["shared_band"] - best) < 1e-9
        exact &= sorted(b) == [0, 1, 2, 3]
        n_dis += list(m) != list(b)
    check("band rule is the exact argmax over the 24 permutations", exact)
    check("the two wiring rules are not the same rule", 5 <= n_dis <= 35, f"{n_dis}/40 disagree")

    # a channel that peaks early is selective and useless
    z3 = np.zeros_like(z)
    for lane in range(4):
        z3[lane, :, lane] = 3.0 * np.exp(-0.5 * ((t + 500.0) / 60.0) ** 2)
    tr3 = PR.LaneTraces(t=t, z=z3, approach_ms=800.0)
    cr3 = PR.crossings(tr3, wiring, theta=1.5)
    check("an early channel fires but never on time", cr3["n_fire"] == 4 and cr3["n_on_time"] == 0)


def test_triggers():
    """The three press triggers (experiment 15).

    "cross" must stay bit-identical to the committed rising-edge rule, because
    every untrained number in this project was measured with it; "peak" and
    "fall" must fire strictly later, since their whole purpose is to move the
    press back without declaring extra parameters the way per-key delays do.
    """
    print("\ntriggers")
    from flyosu.controller import Controller, N_KEYS
    W = np.eye(N_KEYS); b = np.full(N_KEYS, -1.0)

    def reference(zs, dt=2.0, refractory=150.0, smooth=40.0):
        z_s = np.zeros(N_KEYS); u_prev = np.full(N_KEYS, -np.inf)
        last = np.full(N_KEYS, -np.inf); out = []; t = 0.0
        for z in zs:
            z_s = z_s + (dt / smooth) * (np.asarray(z) - z_s)
            u = W @ z_s + b
            fire = (u > 0) & (u_prev <= 0) & (t - last >= refractory)
            u_prev = u
            k = np.flatnonzero(fire).tolist()
            for i in k:
                last[i] = t
            out.append(k); t += dt
        return out

    zs = np.random.default_rng(0).normal(0.5, 1.5, size=(4000, N_KEYS))
    c = Controller(W=W.copy(), b=b.copy())
    got, t = [], 0.0
    for z in zs:
        got.append(c.step(z, t, 2.0)); t += 2.0
    ref = reference(zs)
    check("default trigger is bit-identical to the committed rule", got == ref,
          f"{sum(len(x) for x in ref)} presses over 4000 frames")

    ramp = np.concatenate([np.linspace(-2, 3, 150), np.linspace(3, -2, 150)])
    zz = np.stack([ramp] * N_KEYS, axis=1)
    first = {}
    for trig in ("cross", "peak", "fall"):
        c = Controller(W=W.copy(), b=b.copy(), trigger=trig)
        f = [i for i, z in enumerate(zz) if c.step(z, i * 2.0, 2.0)]
        first[trig] = f[0] if f else None
        check(f"trigger {trig} fires exactly once on a single bump", len(f) == 1)
    check("peak fires later than cross", first["peak"] > first["cross"],
          f"{first['cross']} -> {first['peak']}")
    check("fall fires later than peak", first["fall"] > first["peak"],
          f"{first['peak']} -> {first['fall']}")
    check("an unknown trigger is rejected",
          _raises(lambda: Controller(W=W.copy(), b=b.copy(),
                                     trigger="nope").step(zz[0], 0.0, 2.0)))
    c = Controller(W=W.copy(), b=b.copy(), trigger="peak")
    check("copy carries the trigger", c.copy().trigger == "peak")


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def main():
    test_mania()
    test_beatmap()
    test_encoder_geometry()
    test_controller_logic()
    test_triggers()
    test_probes()
    if "--fast" not in sys.argv:
        test_with_network()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
