"""
Time-resolved probes: what the four channels do while a note falls.

Experiment 4 left a specific question open.  The real connectome's untrained
play is far better than any rewired network's (0/20, p = 0.048), but neither
the recurrent gain nor the *wiring margin* -- each lane's mean channel response
during an isolated falling note -- predicts play across random graphs.  So the
advantage is in something the play protocol exposes and that probe does not.

This module measures the quantities the untrained policy actually depends on.
Three of them, and the first is the one experiment 4's probe could not see:

``shared-threshold separation``
    The untrained controller has **one threshold, shared by all four keys**
    (``Controller.anatomical`` sets ``b = -theta`` for every key).  For that
    policy to work it is not enough that each lane's wired channel responds to
    its own lane: every channel must rise above theta during its own lane's
    note and stay below theta during the other three lanes' notes, *at the same
    theta*.  A network can have four perfectly lane-selective channels and
    still fail, if the four channels sit at different scales -- and a mean
    response per lane, measured lane by lane, cannot tell.  Here the false
    alarms are measured explicitly: for each channel, its peak while its own
    lane falls (``hit``) against its peak while any other lane falls
    (``false``).  The gap between the worst hit and the worst false alarm is
    the width of the band of thetas that plays correctly; if it is negative, no
    single threshold works.

``response timing``
    When the wired channel peaks, and when it first crosses a threshold,
    relative to the moment the note reaches the judgment line.  This turns out
    to be the thing to look at: on every network measured so far the channels
    peak *hundreds of milliseconds before* the note arrives -- the note is
    visible from spawn and the response is dominated by its onset -- while
    osu!mania's windows are tens of milliseconds wide.  A channel that is
    perfectly selective and 400 ms early scores nothing.  Reported per lane,
    plus the spread across lanes: four channels that peak at four different
    times cannot share one threshold *and* be on time.

``chord behaviour``
    With two notes on screen at once, does each channel still do what it does
    alone?  Reported as a difference in z units (not a ratio: a channel whose
    single-note peak is near zero makes a ratio meaningless), which is where a
    network with strong recurrent amplification would be expected to break
    down.

Everything is measured on the same silent, noise-free single-note stimulus
experiment 4 used, with the same normaliser and the same anatomical wiring, so
the numbers are comparable to its ``wired_margin`` -- and the probe runs past
the judgment line, which its did not.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .controller import ChannelNormaliser, N_KEYS, best_assignment
from .encoder import Encoder, LANE_AZ
from .model import DT_PLAY, Fly

OVERSHOOT_MS = 240.0        # how far past the judgment line to keep watching


@dataclass
class LaneTraces:
    """z-scored channel activity while one note falls in each lane."""

    t: np.ndarray               # (T,) ms relative to the judgment line (0 = on the line)
    z: np.ndarray               # (n_lanes, T, 4)
    approach_ms: float

    def window(self, lo_ms: float, hi_ms: float) -> np.ndarray:
        return (self.t >= lo_ms) & (self.t <= hi_ms)


def lane_traces(fly: Fly, norm: ChannelNormaliser, r0: np.ndarray, dt: float = DT_PLAY,
                approach_ms: float = 800.0, overshoot_ms: float = OVERSHOOT_MS,
                lanes: tuple[int, ...] | None = None) -> LaneTraces:
    """One silent falling note per lane, recorded from spawn to past the line."""
    enc = Encoder(fly.ret)
    ph = fly.ph_local
    ext = np.zeros(fly.net.n, dtype=np.float32)
    steps = int(round((approach_ms + overshoot_ms) / dt))
    lanes = tuple(range(len(LANE_AZ))) if lanes is None else lanes
    out = np.zeros((len(lanes), steps, N_KEYS))
    for li, lane in enumerate(lanes):
        r = r0.copy()
        for i in range(steps):
            ext[ph] = enc([(lane, i * dt / approach_ms)], dt)
            r = fly.net.step(r, ext, dt)
            out[li, i] = norm.z(fly.channels(r))
    t = np.arange(steps) * dt - approach_ms
    return LaneTraces(t=t, z=out, approach_ms=approach_ms)


def chord_traces(fly: Fly, norm: ChannelNormaliser, r0: np.ndarray, dt: float = DT_PLAY,
                 approach_ms: float = 800.0, overshoot_ms: float = OVERSHOOT_MS
                 ) -> tuple[list[tuple[int, int]], np.ndarray, np.ndarray]:
    """The same, for all six two-note chords.  Returns the pairs, their traces
    ``(6, T, 4)`` and the time axis."""
    enc = Encoder(fly.ret)
    ph = fly.ph_local
    ext = np.zeros(fly.net.n, dtype=np.float32)
    steps = int(round((approach_ms + overshoot_ms) / dt))
    pairs = list(combinations(range(len(LANE_AZ)), 2))
    out = np.zeros((len(pairs), steps, N_KEYS))
    for pi, (a, b) in enumerate(pairs):
        r = r0.copy()
        for i in range(steps):
            prog = i * dt / approach_ms
            ext[ph] = enc([(a, prog), (b, prog)], dt)
            r = fly.net.step(r, ext, dt)
            out[pi, i] = norm.z(fly.channels(r))
    return pairs, out, np.arange(steps) * dt - approach_ms


# -- the quantities the untrained policy depends on ------------------------

def shared_threshold(tr: LaneTraces, wiring: list[int],
                     hit_ms: tuple[float, float] = (-160.0, 160.0),
                     false_scope: str = "window") -> dict:
    """Can one threshold serve all four keys?

    ``wiring[lane]`` is the channel that lane's key reads.  For each key:
    ``hit`` is its channel's peak while its own lane falls, inside the hit
    window; ``false`` is that channel's peak while any *other* lane falls.  A
    single theta works for every key iff ``max(false) < min(hit)``, and the
    gap between them is the width of the band of thetas that does.

    ``false_scope`` -- ``"window"`` scores the false alarm in the same hit
    window (the apples-to-apples question: at the moment a note is judgeable,
    does the right channel lead at one threshold?), ``"all"`` over the whole
    descent (the stray-press question: with notes 600 ms apart, one note's
    early response lands in the previous note's window).
    """
    hw = tr.window(*hit_ms)
    sel = hw if false_scope == "window" else slice(None)
    hits, falses = np.zeros(N_KEYS), np.zeros(N_KEYS)
    for lane, ch in enumerate(wiring):
        hits[lane] = tr.z[lane, hw, ch].max()
        others = [l for l in range(len(wiring)) if l != lane]
        falses[lane] = max(tr.z[l, sel, ch].max() for l in others) if others else -np.inf
    band = float(hits.min() - falses.max())
    return {"hit": hits.tolist(), "false": falses.tolist(), "false_scope": false_scope,
            "margin_per_key": (hits - falses).tolist(),
            "worst_key_margin": float((hits - falses).min()),
            "shared_band": band, "one_theta_works": bool(band > 0),
            "theta_mid": float(0.5 * (hits.min() + falses.max())),
            # one threshold per key, halfway between its own hit and its worst
            # false alarm: what the shared threshold cannot do when the four
            # channels sit at different scales
            "theta_per_key": (0.5 * (hits + falses)).tolist()}


def crossings(tr: LaneTraces, wiring: list[int], theta: float = 1.5,
              hit_ms: tuple[float, float] = (-160.0, 160.0)) -> dict:
    """What the untrained policy actually does: the first upward crossing of
    ``theta``, per lane, on that lane's own channel.

    ``n_on_time`` counts lanes whose own channel first crosses inside the hit
    window -- a press that would be judged rather than a stray.  ``n_false_keys``
    counts (lane, key) pairs where a *different* lane's note drives a key over
    theta at all, which in play becomes a press in the wrong lane.
    """
    lags: list = []
    for lane, ch in enumerate(wiring):
        v = tr.z[lane, :, ch]
        up = np.flatnonzero((v > theta) & (np.concatenate([[-np.inf], v[:-1]]) <= theta))
        lags.append(float(tr.t[up[0]]) if len(up) else None)
    hit = [l for l in lags if l is not None and hit_ms[0] <= l <= hit_ms[1]]
    fired = [l for l in lags if l is not None]
    false = 0
    for lane in range(len(wiring)):
        for other, ch in enumerate(wiring):
            if other != lane and tr.z[lane, :, ch].max() > theta:
                false += 1
    return {"theta": theta, "first_crossing_ms": lags,
            "n_fire": len(fired), "n_on_time": len(hit),
            "on_time_fraction": len(hit) / len(wiring),
            "mean_crossing_ms": float(np.mean(fired)) if fired else None,
            "n_false_keys": false}


def timing(tr: LaneTraces, wiring: list[int]) -> dict:
    """When each wired channel peaks, relative to the judgment line."""
    lags, heights = [], []
    for lane, ch in enumerate(wiring):
        v = tr.z[lane, :, ch]
        i = int(np.argmax(v))
        lags.append(float(tr.t[i])); heights.append(float(v[i]))
    lags = np.array(lags)
    return {"peak_lag_ms": lags.tolist(), "peak_z": heights,
            "peak_lag_mean_ms": float(lags.mean()),
            "peak_lag_spread_ms": float(lags.std()),
            "peak_lag_abs_mean_ms": float(np.abs(lags).mean())}


def selectivity(tr: LaneTraces, wiring: list[int],
                hit_ms: tuple[float, float] = (-160.0, 160.0)) -> dict:
    """How often the wired channel is the largest of the four, during its own
    lane's note.  Label-free version of "does the right key win"."""
    hw = tr.window(*hit_ms)
    frac, peak_margin = [], []
    for lane, ch in enumerate(wiring):
        Z = tr.z[lane, hw]
        frac.append(float((np.argmax(Z, axis=1) == ch).mean()))
        i = int(np.argmax(Z[:, ch]))
        peak_margin.append(float(Z[i, ch] - np.max(np.delete(Z[i], ch))))
    return {"argmax_fraction": frac, "argmax_mean": float(np.mean(frac)),
            "peak_margin": peak_margin, "peak_margin_mean": float(np.mean(peak_margin))}


def chord_linearity(tr: LaneTraces, pairs, Zc: np.ndarray, wiring: list[int],
                    hit_ms: tuple[float, float] = (-160.0, 160.0)) -> dict:
    """Does a two-note chord still drive both keys?

    For each pair, each of the two keys' peak in the chord, against its peak
    when that note falls alone.  ``retention`` below 1 means the second note
    suppresses the first.
    """
    hw = tr.window(*hit_ms)
    delta, cross, alone_all = [], [], []
    for (a, b), Z in zip(pairs, Zc):
        for lane in (a, b):
            ch = wiring[lane]
            alone = tr.z[lane, hw, ch].max()
            delta.append(float(Z[hw, ch].max() - alone))
            alone_all.append(float(alone))
        # do the two uninvolved keys stay quiet?
        for lane in range(len(wiring)):
            if lane not in (a, b):
                cross.append(float(Z[hw, wiring[lane]].max()))
    return {"delta_mean_z": float(np.mean(delta)), "delta_min_z": float(np.min(delta)),
            "single_peak_mean_z": float(np.mean(alone_all)),
            "uninvolved_peak_mean": float(np.mean(cross))}


def measure(fly: Fly, norm: ChannelNormaliser, r0: np.ndarray, wiring: list[int] | None = None,
            dt: float = DT_PLAY, chords: bool = True, theta: float = 1.5) -> dict:
    """All of the above for one network.  ``wiring`` defaults to the anatomical
    assignment, derived from the same traces (so the probe is self-contained)."""
    tr = lane_traces(fly, norm, r0, dt=dt)
    if wiring is None:
        pre = tr.window(-400.0, 0.0)
        wiring = best_assignment(tr.z[:, pre].mean(axis=1))
    out = {"wiring": list(wiring),
           "shared_threshold": shared_threshold(tr, wiring, false_scope="window"),
           "shared_threshold_all": shared_threshold(tr, wiring, false_scope="all"),
           "crossings": crossings(tr, wiring, theta=theta),
           "timing": timing(tr, wiring), "selectivity": selectivity(tr, wiring)}
    if chords:
        pairs, Zc, _ = chord_traces(fly, norm, r0, dt=dt)
        out["chords"] = chord_linearity(tr, pairs, Zc, wiring)
    return out
