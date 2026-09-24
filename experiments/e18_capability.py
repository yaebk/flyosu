"""
Experiment 18 -- capability: make the fly play harder charts.

**This is engineering, not a comparison.**  It uses the real connectome only,
runs no controls, and claims no p-values.  Tuning a readout to play better is
not a protocol violation because nothing here is being tested against a null;
keep it that way, and do not let any number from this file leak into a
registered comparison.

Experiment 5 produced the best fly so far: a `pca16` ridge readout, 68
parameters, connectome frozen, **0.917** on held-out stage-3 charts at 600 ms.
It was fitted on four stage-3 charts at 600 ms and then played everywhere else
without refitting, and that is where it falls over:

    stage 3 @ 600 ms  0.917      the condition it was fitted on
    stage 5 varied    0.608      rhythm it never saw
    stage 4 chords    0.506      chords it never saw
    stage 4 @ 400 ms  0.286      "chord density, not lane identity, is the wall"

Every one of those is a *transfer* number.  `docs/RESULTS_E5.md` named the
obvious follow-up -- "fit on stage 4 and see" -- and nobody ran it.  So the
question here is how much of the wall is the network's capacity and how much is
simply that the readout was only ever shown one kind of chart.

**Arms.**  Four training compositions, each 8 charts x 24 notes, same seed, same
`pca16` features, same solver.  The only thing that varies is what the readout
is shown while being fitted:

    s3_600      stage 3 @ 600           experiment 5's diet, with twice the data
    s4_600      stage 4 @ 600           chords only -- the flagged follow-up
    mixed       3@600, 4@600, 5@600, 3@450   a bit of everything
    mixed_fast  3@600, 4@600, 4@400, 3@450   everything, weighted toward density

**Test battery.**  Held-out charts nobody was fitted on, three per condition at
20 notes, seed 999 -- stage 3 @ 600 and @ 450, stage 4 @ 600 and @ 400, stage 5
@ 600.  The same battery for every arm, so the rows are comparable.

The `s3_600` arm exists to separate "more data helped" from "more *varied* data
helped".  Experiment 5's own 0.917 came from four charts; this arm gets eight of
the same kind, so if it moves, the extra frames are doing it.

    ARM=mixed python -m experiments.e18_capability
    python -m experiments.e18_capability report
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import encoder as E, learn as L, model as M, play as P, reservoir as R  # noqa: E402
from flyosu.controller import calibration_states  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e18_capability.json")

THETA = 1.5
NOISE = 0.03
READOUT_K = 16                       # pca16, experiment 5's best
N_CHARTS = 8
N_NOTES = 24
TRAIN_SEED = 100

ARMS = {
    # round 1: what should the readout be shown while it is fitted?
    "s3_600":     dict(specs=((3, 600.0),)),
    "s4_600":     dict(specs=((4, 600.0),)),
    "mixed":      dict(specs=((3, 600.0), (4, 600.0), (5, 600.0), (3, 450.0))),
    "mixed_fast": dict(specs=((3, 600.0), (4, 600.0), (4, 400.0), (3, 450.0))),
    # round 2: stage 4 won round 1 outright, so push on it three ways --
    # denser training chords, more of them, and a bigger readout.
    "s4_450":     dict(specs=((4, 450.0),)),
    "s4_dense":   dict(specs=((4, 600.0), (4, 450.0), (4, 350.0))),
    "s4_x16":     dict(specs=((4, 600.0),), n_charts=16),
    "s4_pca32":   dict(specs=((4, 600.0),), k=32),
    # round 3: more data and more capacity each helped on their own and in
    # different places -- pca32 is superb near its training condition and
    # brittle away from it, x16 is even -- so combine them, and check whether
    # more data alone keeps paying.
    "s4_x16_pca32": dict(specs=((4, 600.0),), n_charts=16, k=32),
    "s4_x24_pca32": dict(specs=((4, 600.0),), n_charts=24, k=32),
    "s4_x16_var":   dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32),
    # round 4: the refractory is a declared 150 ms that makes two notes in the
    # same lane closer than that physically unpressable, whatever the readout
    # does.  At 3-5 notes/s over four lanes it is plausibly what is now binding,
    # and it has never been varied.  Same winning diet, shorter dead time.
    "var_r100":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, refr=100.0),
    "var_r75":      dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, refr=75.0),
    "var_r50":      dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, refr=50.0),
    # round 5: the approach window is how long a note is visible -- the fly's
    # scroll speed.  At 800 ms and 3+ notes/s a lane holds two or three notes at
    # once and the encoder shows their superposition, which is the thing real
    # players fix by scrolling faster.  `approach` applies to the training
    # charts and the battery together, so the fly is never tested at a scroll
    # speed it was not fitted at.
    "var_a600":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, approach=600.0),
    "var_a400":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, approach=400.0),
    "var_a300":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, approach=300.0),
    # round 6: 400 ms beat both 600 and 300, so bracket it more finely; and the
    # diet's fastest chart is 350 ms, which makes everything past 3 notes/s an
    # extrapolation -- so add a 250 ms chart and see whether the top end lifts.
    "var_a450":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, approach=450.0),
    "var_a350":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0)), n_charts=16, k=32, approach=350.0),
    "fast_a400":    dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0)), n_charts=16, k=32, approach=400.0),
    "fast_a300":    dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0)), n_charts=16, k=32, approach=300.0),
    # round 7: jacks.  `jack_a400` keeps the chord diet and adds stage-6 charts
    # so the readout has seen the pattern; `fast_a400` is the control for it,
    # having never seen a jack, and the difference between them is how much of
    # jack difficulty is unfamiliarity rather than the 150 ms refractory.
    "jack_a400":    dict(specs=((4, 600.0), (4, 350.0), (6, 450.0), (6, 300.0)), n_charts=16, k=32, approach=400.0),
    "jack_r50":     dict(specs=((4, 600.0), (4, 350.0), (6, 450.0), (6, 300.0)), n_charts=16, k=32, approach=400.0, refr=50.0),
    # The best arm, with the refractory cut, scored on jacks fast enough that it
    # has to matter.  If these two differ, the constraint is real and simply out
    # of reach; if they do not, it never mattered at all.
    "fast_r50":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0)), n_charts=16, k=32, approach=400.0, refr=50.0),
    # round 8: five notes a second is the one weak point left (0.718), and the
    # diet's fastest chart is 250 ms, so that condition is still extrapolation.
    # Add a 200 ms chart.  A 300 ms approach beat 400 at that density, so both
    # are tried; 20 charts so five specs cycle evenly.
    "fastest_a400": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0)), n_charts=20, k=32, approach=400.0),
    "fastest_a300": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0)), n_charts=20, k=32, approach=300.0),
    # round 9: hold notes.  `hold_a400` puts stage-7 charts in the diet;
    # `fast_a400` is the control, having never held a key on purpose.  The
    # jack result says to expect the control to do well and the trained arm to
    # pay for whatever the stage-7 charts displaced.
    "hold_a400":    dict(specs=((4, 600.0), (4, 350.0), (7, 600.0), (7, 400.0)), n_charts=16, k=32, approach=400.0),
    # round 10: density and holds each work alone and neither survives being
    # mixed at a fixed chart budget -- the density diet is perfect on density
    # and poor on holds, the hold diet the reverse.  Is that a budget limit or
    # a capacity limit?  Give both a diet big enough to cover everything, and
    # try more readout capacity as well.
    "both_a400":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=32, approach=400.0),
    "both_a300":     dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=32, approach=300.0),
    # round 11: releases.  both_a300 releases a steady 80-90 ms late on every
    # hold, and the fit never saw it -- its judge replay didn't release keys at
    # all, so every hold was scored as never let go.  `_v2` is both_a300 with
    # only that corrected; `_rel` also fits a per-lane release level on the
    # training charts.  The pair separates the two changes.
    "both_a300_v2":  dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=32, approach=300.0),
    "both_a300_rel": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=32, approach=300.0,
                          release=tuple(round(0.05 * i, 2) for i in range(21))),
    # Round 11 made holds worse (0.779 -> 0.728, 0.750 with levels), and the
    # reason was the recordings, not the judge: the silent recorder misses every
    # hold, and a missed hold leaves the screen 164 ms after its head, so the
    # fit never saw the body it has to release on.  Round 12 records holds as a
    # perfect player sees them (``reservoir.HoldOracle``): `_orc` alone, then
    # with the levels, then with stage 8 (holds followed closely in their own
    # lane) in the diet, then with the fixed-grid hold rendering as well.
    "both_a300_orc": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=32, approach=300.0,
                          oracle=True),
    "both_a300_orc_rel": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                     (4, 200.0), (7, 600.0), (7, 400.0)),
                              n_charts=28, k=32, approach=300.0, oracle=True,
                              release=tuple(round(0.05 * i, 2) for i in range(21))),
    "both8_orc_rel": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0), (8, 400.0), (8, 300.0)),
                          n_charts=36, k=32, approach=300.0, oracle=True,
                          release=tuple(round(0.05 * i, 2) for i in range(21))),
    "both8_orc_rel_grid": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                      (4, 200.0), (7, 600.0), (7, 400.0), (8, 400.0),
                                      (8, 300.0)),
                               n_charts=36, k=32, approach=300.0, oracle=True, grid=True,
                               release=tuple(round(0.05 * i, 2) for i in range(21))),
    # round 13: density past five events a second.  Real maps run to 10.2 and
    # the diet stopped at 200 ms, so add 150 and 125 ms chord charts; then a
    # shorter approach, since the approach window was the last density wall;
    # then a shorter refractory for jacks, which bind at 150 ms.
    "fast_orc_a300": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)),
                          n_charts=36, k=32, approach=300.0, oracle=True,
                          release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_orc_a250": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)),
                          n_charts=36, k=32, approach=250.0, oracle=True,
                          release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_orc_a250_r100": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                      (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                      (7, 400.0)),
                               n_charts=36, k=32, approach=250.0, oracle=True, refr=100.0,
                               release=tuple(round(0.05 * i, 2) for i in range(21))),
    # round 14: round 13's winner pushed further on each of its levers, since
    # chords at 6.7-10 events a second (0.83 falling to 0.67) are now the wall:
    # a 200 ms approach, a 75 ms refractory, and more readout capacity now that
    # the diet is broader.
    "fast_orc_a200_r100": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                      (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                      (7, 400.0)),
                               n_charts=36, k=32, approach=200.0, oracle=True, refr=100.0,
                               release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_orc_a250_r75": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                     (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                     (7, 400.0)),
                              n_charts=36, k=32, approach=250.0, oracle=True, refr=75.0,
                              release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_orc_a250_r100_k48": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                          (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                          (7, 400.0)),
                                   n_charts=36, k=48, approach=250.0, oracle=True, refr=100.0,
                                   release=tuple(round(0.05 * i, 2) for i in range(21))),
    # The 200 ms approach helped only at 6.7 events/s and cost the stage-8
    # holds, so the approach is no longer the wall.  At 8-10 events/s accuracy
    # equals hit rate with no strays: the fly is not mistiming notes, it is not
    # pressing them, which is two same-lane pulses merging.  Two knobs set how
    # sharp a pulse can be: the controller's 40 ms smoothing and the fit
    # target's 80 ms width.
    "fast_orc_a250_r100_sm20": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                           (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                           (7, 400.0)),
                                    n_charts=36, k=32, approach=250.0, oracle=True,
                                    refr=100.0, smooth=20.0,
                                    release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_orc_a250_r100_w50": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0),
                                          (4, 200.0), (4, 150.0), (4, 125.0), (7, 600.0),
                                          (7, 400.0)),
                                   n_charts=36, k=32, approach=250.0, oracle=True,
                                   refr=100.0, width=50.0,
                                   release=tuple(round(0.05 * i, 2) for i in range(21))),
    # round 15: round 14's two winners -- 20 ms smoothing (0.929 over 24) and
    # 48 components (0.925) -- act on different things, so combine them, and
    # push each one step further.
    "fast_sm20_k48": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)),
                          n_charts=36, k=48, approach=250.0, oracle=True, refr=100.0,
                          smooth=20.0, release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_sm10_k48": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)),
                          n_charts=36, k=48, approach=250.0, oracle=True, refr=100.0,
                          smooth=10.0, release=tuple(round(0.05 * i, 2) for i in range(21))),
    "fast_sm20_k64": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (4, 150.0), (4, 125.0), (7, 600.0), (7, 400.0)),
                          n_charts=36, k=64, approach=250.0, oracle=True, refr=100.0,
                          smooth=20.0, release=tuple(round(0.05 * i, 2) for i in range(21))),
    "both_a300_k48": dict(specs=((4, 600.0), (4, 450.0), (4, 350.0), (4, 250.0), (4, 200.0),
                                 (7, 600.0), (7, 400.0)), n_charts=28, k=48, approach=300.0),
}

# Held-out battery: the conditions experiment 5 measured, plus a denser
# single-note one.  Same seeds for every arm.
BATTERY = {
    "s3_600": dict(stage=3, interval_ms=600.0),
    "s3_450": dict(stage=3, interval_ms=450.0),
    "s3_350": dict(stage=3, interval_ms=350.0),      # 2.9 notes/s, single notes
    "s4_600": dict(stage=4, interval_ms=600.0),
    "s4_400": dict(stage=4, interval_ms=400.0),
    "s4_300": dict(stage=4, interval_ms=300.0),      # 200 BPM with chords
    "s5_600": dict(stage=5, interval_ms=600.0),
}
BATTERY_KW = dict(n_charts=3, n_notes=20, seed=999)

# The arm was chosen by reading the battery above, so those numbers are
# selection-optimistic in exactly the way experiments 13 and 16 warned about.
# `validate` re-scores one arm on a fresh seed with three times the notes, and
# pushes on past the old conditions to find where the new ceiling is.  Quote
# these numbers, not the battery's.
DEEP = {
    **BATTERY,
    "s3_300": dict(stage=3, interval_ms=300.0),      # 3.3 notes/s, single notes
    "s3_250": dict(stage=3, interval_ms=250.0),      # 4.0 notes/s
    "s4_250": dict(stage=4, interval_ms=250.0),      # 240 BPM with chords
    "s4_200": dict(stage=4, interval_ms=200.0),      # 300 BPM with chords
    # Jacks (stage 6): the same lane twice or more in a row.  Every other stage
    # spreads notes over four lanes, so this is the first condition in the
    # project that asks one channel to resolve two notes in succession -- and
    # the first where the controller's refractory can bind.
    "s6_450": dict(stage=6, interval_ms=450.0),      # 2.2 notes/s, jacks
    "s6_300": dict(stage=6, interval_ms=300.0),      # 3.3 notes/s, jacks
    "s6_250": dict(stage=6, interval_ms=250.0),      # 4.0 notes/s, jacks
    # Below 150 ms the refractory MUST bind: a jack at this interval puts two
    # notes in one lane closer together than the controller's dead time, so the
    # second is unpressable whatever the readout wants.  These two exist to
    # close that question rather than because the fly can play them.
    "s6_150": dict(stage=6, interval_ms=150.0),      # 6.7 notes/s, at the refractory
    "s6_120": dict(stage=6, interval_ms=120.0),      # 8.3 notes/s, inside it
    # Hold notes (stage 7).  These ask the controller something nothing else
    # does -- not when to press but how long to stay pressed -- and the answer
    # comes from the same threshold, since a key is down while its drive is.
    "s7_600": dict(stage=7, interval_ms=600.0),      # 1.7 notes/s, holds
    "s7_400": dict(stage=7, interval_ms=400.0),      # 2.5 notes/s, holds
    "s7_300": dict(stage=7, interval_ms=300.0),      # 3.3 notes/s, holds
    # Holds followed in their own lane 80 / 60 ms after the tail (stage 8),
    # the pattern that sinks the fast real maps.  Arms validated before these
    # were added simply lack the two rows.
    "s8_400": dict(stage=8, interval_ms=400.0),      # 2.5 notes/s
    "s8_300": dict(stage=8, interval_ms=300.0),      # 3.3 notes/s
    # Past five events a second, where half the real maps live (5.5 to 10.2)
    # and where nothing was ever trained or measured.
    "s4_150": dict(stage=4, interval_ms=150.0),      # 6.7 events/s with chords
    "s4_125": dict(stage=4, interval_ms=125.0),      # 8.0
    "s4_100": dict(stage=4, interval_ms=100.0),      # 10.0, the fastest real map
}
DEEP_KW = dict(n_charts=10, n_notes=20, seed=4242)

# What experiment 5's readout scored on the same conditions, for reference.
E5_REFERENCE = {"s3_600": 0.917, "s4_600": 0.506, "s4_400": 0.286, "s5_600": 0.608}


def _approach(cfg) -> dict:
    """``{}`` unless the arm declares a scroll speed, so the default path is
    exactly what every earlier round ran."""
    return {} if "approach" not in cfg else {"approach_ms": float(cfg["approach"])}


def _specs(cfg) -> tuple:
    """Training specs with the arm's approach appended, if it declares one."""
    if "approach" not in cfg:
        return cfg["specs"]
    return tuple((s[0], s[1], float(cfg["approach"])) for s in cfg["specs"])


def _load(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def run_arm(arm: str) -> dict:
    cfg = ARMS[arm]
    specs = _specs(cfg)
    n_charts = int(cfg.get("n_charts", N_CHARTS))
    k = int(cfg.get("k", READOUT_K))
    t0 = time.time()
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE,
                                encoder=E.Encoder(fly.ret, hold_grid=bool(cfg.get("grid"))))
    if "refr" in cfg:
        player.controller.refractory_ms = float(cfg["refr"])
    if "smooth" in cfg:
        player.controller.smooth_ms = float(cfg["smooth"])
    states = calibration_states(fly, player.r0)
    rr = R.RidgeReadout(player, n_charts=n_charts, n_notes=N_NOTES,
                        seed=TRAIN_SEED, chart_specs=specs,
                        release_levels=tuple(cfg.get("release", ())),
                        hold_oracle=bool(cfg.get("oracle")),
                        width_ms=float(cfg.get("width", 80.0)))
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=k, states=states)
    print(f"[{arm}] recording {n_charts} charts (pca{k}): "
          + ", ".join(f"s{s[0]}@{s[1]:.0f}"
                      + (f"/a{s[2]:.0f}" if len(s) > 2 else "") for s in specs), flush=True)
    rr.record()
    d = rr.solve()
    out = {"arm": arm, "specs": [list(s) for s in specs],
           "n_charts": n_charts, "k": k, "n_params": d["n_params"],
           "train_reward": d["train_reward"], "frames": d["frames"],
           "lanes": d["lanes"], "battery": {}}
    for name, cond in BATTERY.items():
        e = L.evaluate(player, **cond, **BATTERY_KW, **_approach(cfg))
        n_c = int(np.array(e["confusion"]).sum())
        out["battery"][name] = {
            "accuracy": float(e["accuracy"]), "hit_rate": float(e["hit_rate"]),
            "stray_per_note": float(e["stray_per_note"]),
            "lane_correct": (float(e["lane_correct"]) if n_c >= 20 else None),
            "reward": float(e["accuracy"] - L.STRAY_PENALTY * e["stray_per_note"])}
        b = out["battery"][name]
        ref = E5_REFERENCE.get(name)
        print(f"  [{arm}] {name:<8s} acc {b['accuracy']:.3f}"
              + (f" (e5 {ref:.3f}, {b['accuracy'] - ref:+.3f})" if ref else "")
              + f"  hit {b['hit_rate']:.2f}  stray {b['stray_per_note']:.2f}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    arm = os.environ.get("ARM")
    if arm not in ARMS:
        raise SystemExit(f"set ARM to one of: {', '.join(ARMS)}")
    path = PATH[:-5] + f"_{arm}.json"
    with open(path, "w") as fh:
        json.dump(run_arm(arm), fh, indent=1)
    print(f"wrote {os.path.basename(path)}", flush=True)


def report():
    runs = {}
    for f in sorted(glob.glob(PATH[:-5] + "_*.json")):
        r = _load(f, None)
        if r:
            runs[r["arm"]] = r
    if not runs:
        print("no arms finished yet"); return
    order = [a for a in ARMS if a in runs]
    print("\n=== experiment 18: capability, real connectome, pca16 ===")
    print(f"  {N_CHARTS} training charts x {N_NOTES} notes per arm; battery is "
          f"{BATTERY_KW['n_charts']} held-out charts x {BATTERY_KW['n_notes']} notes")
    head = f"  {'condition':<10s}" + "".join(f"{a:>12s}" for a in order) + f"{'e5':>9s}"
    print("\n  ACCURACY\n" + head)
    def cell(a, name, key):
        b = runs[a]["battery"].get(name)
        return None if b is None else b[key]

    for name in BATTERY:
        row = f"  {name:<10s}"
        vals = [v for v in (cell(a, name, "accuracy") for a in order) if v is not None]
        best = max(vals) if vals else None
        for a in order:
            v = cell(a, name, "accuracy")
            row += f"{'-':>12s}" if v is None else \
                   f"{('*' if v == best else ' ') + format(v, '.3f'):>12s}"
        ref = E5_REFERENCE.get(name)
        row += f"{format(ref, '.3f') if ref else '-':>9s}"
        print(row)
    for title, key in (("HIT RATE", "hit_rate"), ("STRAYS PER NOTE", "stray_per_note")):
        print(f"\n  {title}\n" + head[:-9])
        for name in BATTERY:
            print(f"  {name:<10s}" + "".join(
                (f"{'-':>12s}" if cell(a, name, key) is None
                 else f"{cell(a, name, key):>12.3f}") for a in order))
    print("\n  mean accuracy over the battery (arms missing a condition are marked)")
    for a in order:
        vals = [cell(a, n, "accuracy") for n in BATTERY]
        got = [v for v in vals if v is not None]
        print(f"    {a:<12s} {float(np.mean(got)):.3f}"
              + ("" if len(got) == len(vals) else f"  (only {len(got)}/{len(vals)})")
              + f"   ({runs[a]['seconds']:.0f}s, {runs[a]['n_params']} params, "
              + f"{runs[a].get('n_charts', N_CHARTS)} charts, pca{runs[a].get('k', READOUT_K)})")
    with open(PATH, "w") as fh:
        json.dump({"arms": runs, "battery": BATTERY, "e5_reference": E5_REFERENCE}, fh, indent=1)


def validate():
    """Re-score one arm on fresh charts, deeper, and past the old ceiling."""
    arm = os.environ.get("ARM")
    if arm not in ARMS:
        raise SystemExit(f"set ARM to one of: {', '.join(ARMS)}")
    cfg = ARMS[arm]
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=THETA, noise=NOISE,
                                encoder=E.Encoder(fly.ret, hold_grid=bool(cfg.get("grid"))))
    if "refr" in cfg:
        player.controller.refractory_ms = float(cfg["refr"])
    if "smooth" in cfg:
        player.controller.smooth_ms = float(cfg["smooth"])
    states = calibration_states(fly, player.r0)
    rr = R.RidgeReadout(player, n_charts=int(cfg.get("n_charts", N_CHARTS)),
                        n_notes=N_NOTES, seed=TRAIN_SEED, chart_specs=_specs(cfg),
                        release_levels=tuple(cfg.get("release", ())),
                        hold_oracle=bool(cfg.get("oracle")),
                        width_ms=float(cfg.get("width", 80.0)))
    rr.features = R.PopulationProjection.fit(fly, player.r0,
                                             k=int(cfg.get("k", READOUT_K)), states=states)
    print(f"[{arm}] validating on seed {DEEP_KW['seed']}, "
          f"{DEEP_KW['n_charts']} charts x {DEEP_KW['n_notes']} notes per condition", flush=True)
    rr.record()
    fit = rr.solve()
    out = {"arm": arm, "deep_kw": DEEP_KW, "lanes": fit["lanes"],
           "n_params": fit["n_params"], "conditions": {}}
    for name, cond in DEEP.items():
        e = L.evaluate(player, **cond, **DEEP_KW, **_approach(cfg))
        n_c = int(np.array(e["confusion"]).sum())
        nps = 1000.0 / cond["interval_ms"]
        out["conditions"][name] = {
            "notes_per_s": round(nps, 2), **{k: float(e[k]) for k in
            ("accuracy", "hit_rate", "stray_per_note")},
            "lane_correct": (float(e["lane_correct"]) if n_c >= 20 else None)}
        b = out["conditions"][name]
        sel = E5_REFERENCE.get(name)
        print(f"  {name:<8s} {nps:>4.1f}/s  acc {b['accuracy']:.3f}  hit {b['hit_rate']:.2f}  "
              f"stray {b['stray_per_note']:.2f}"
              + (f"   (e5 {sel:.3f})" if sel else ""), flush=True)
    path = PATH[:-5] + f"_validate_{arm}.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {os.path.basename(path)}", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "report":
        report()
    elif cmd == "validate":
        validate()
    else:
        main()
