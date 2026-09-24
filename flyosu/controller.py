"""
Controller: four channel activations -> key presses.

Step 7.  Everything downstream of the descending neurons.  Kept deliberately
small, because experiment 1 predicts that a free readout is exactly what erases
the difference between the real connectome and a rewired one: the fewer
parameters live here, the more the result is about the wiring.

Two pieces:

``ChannelNormaliser``  puts the four channels on a common scale.  The channels
    have very different baselines and modulation depths (see run_fly.py), so
    each is z-scored against its own mean and spread over the same 61-stimulus
    ensemble the network was calibrated on, settled from the blank fixed
    point.  Label-free, never sees a lane or a key, applied identically to the
    real network and every control.

``Controller``  a leaky integrator on the z-scored channels followed by a
    threshold with hysteresis:

        tau_s dz_s/dt = -z_s + z                 (smoothing, optional)
        u             = W z_s + b                (4 x 4 mixing + 4 thresholds)
        press key k when u_k crosses 0 upward, at most once per refractory
        period, optionally ``delay_ms[k]`` after the crossing

    ``W`` and ``b`` are the *only* learnable parameters in the whole system --
    20 numbers.  The connectome stays frozen.  (``W`` may be 4 x k when the
    controller reads k label-free population features instead of the four
    channels -- see ``reservoir.py``; the rule above is unchanged.)

``Controller.anatomical`` builds the untrained policy: ``W`` is a permutation
matrix that wires each key to the channel that responds most while a single
note falls in its lane (one silent note per lane, no feedback; mean z over the
second half of the descent; best one-to-one assignment over the 24
permutations), ``b`` is one shared threshold.  Static point responses at the
judgment line were tried first and are a poor guide to the moving-note
response, which is dominated by the network's transient dynamics.  That assignment is the
one place stimulus knowledge enters before any learning -- log2(24) = 4.6
bits -- and it is reported as such; the learning experiments also start from
``W = 0`` so the mapping has to be discovered from reward alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations

import numpy as np

from .encoder import EL_JUDGE, EL_SPAWN, LANE_AZ, SIGMA_DEG, Encoder
from .model import CAL_AZ, CAL_EL, DT_PLAY, Fly

N_KEYS = 4


def calibration_states(fly: Fly, r0: np.ndarray, dt: float = DT_PLAY,
                       duration_ms: float = 300.0) -> list[np.ndarray]:
    """Network state after settling on each of the 60 calibration stimuli from
    ``r0``, plus ``r0`` itself.  Label-free: the ensemble tiles the visual
    field and knows nothing about lanes.  Every label-free readout (the channel
    normaliser here, the population projection in ``reservoir.py``) is fitted
    on exactly this set."""
    out = []
    for az in CAL_AZ:
        for el in CAL_EL:
            r, _ = fly.net.run(fly.stimulus([(float(az), float(el), 1.0)],
                                            sigma_deg=SIGMA_DEG),
                               duration_ms=duration_ms, dt=dt, r0=r0)
            out.append(r)
    out.append(r0)
    return out


@dataclass
class ChannelNormaliser:
    mu: np.ndarray
    sd: np.ndarray

    def z(self, a: np.ndarray) -> np.ndarray:
        return (np.asarray(a, dtype=np.float64) - self.mu) / self.sd

    @classmethod
    def fit(cls, fly: Fly, r0: np.ndarray, dt: float = DT_PLAY,
            duration_ms: float = 300.0) -> "ChannelNormaliser":
        """Channel mean and spread over the calibration ensemble, each stimulus
        settled from the blank state ``r0`` for ``duration_ms``."""
        A = np.array([fly.channels(r) for r in calibration_states(fly, r0, dt, duration_ms)],
                     dtype=np.float64)
        sd = A.std(0)
        sd[sd <= 0] = 1.0
        return cls(mu=A.mean(0), sd=sd)


@dataclass
class Controller:
    W: np.ndarray                      # (4, k) key <- feature mixing; k = 4 channels by default
    b: np.ndarray                      # (4,) thresholds (u = W z + b > 0 fires)
    refractory_ms: float = 150.0
    smooth_ms: float = 40.0            # leaky-integrator time constant; 0 = none
    delay_ms: np.ndarray | None = None  # (4,) per-key wait between crossing and press
    # Which edge of the drive fires the key.  "cross" is the rising edge and is
    # the original behaviour, bit for bit.  The other two exist because of
    # experiment 12: given a wide enough note gap the real connectome picks the
    # right lane essentially every time (lane-correct 1.000) and merely presses
    # too early, and the per-key delay fix trades that accuracy away.  "peak"
    # and "fall" move the press later *without declaring a single extra
    # parameter* -- they reuse the same W and the same threshold, where delays
    # need four more numbers off a probe.
    trigger: str = "cross"              # "cross" | "peak" | "fall"
    # Per-key release level for hold notes, or None.  None is the original
    # behaviour: a key lifts when its drive falls back through zero.  Hold
    # releases measured that way land a steady 80-90 ms late, because the
    # drive decays slowly off its plateau, so with a level set the key instead
    # lifts as the drive falls back through ``release[k]`` -- which it must
    # first have exceeded since the press.  Presses are untouched.
    release: np.ndarray | None = None
    z_s: np.ndarray = field(default_factory=lambda: np.zeros(N_KEYS))
    u_prev: np.ndarray = field(default_factory=lambda: np.full(N_KEYS, -np.inf))
    du_prev: np.ndarray = field(default_factory=lambda: np.zeros(N_KEYS))
    last_press: np.ndarray = field(default_factory=lambda: np.full(N_KEYS, -np.inf))
    pending: list = field(default_factory=list)   # [(press time, key), ...]
    armed: np.ndarray = field(default_factory=lambda: np.zeros(N_KEYS, bool))
    relifted: np.ndarray = field(default_factory=lambda: np.zeros(N_KEYS, bool))

    # -- parameters --------------------------------------------------------

    @property
    def params(self) -> np.ndarray:
        return np.concatenate([self.W.ravel(), self.b])

    @params.setter
    def params(self, p: np.ndarray) -> None:
        p = np.asarray(p, dtype=np.float64)
        n_w = self.W.size
        self.W = p[:n_w].reshape(self.W.shape).copy()
        self.b = p[n_w:].copy()

    @property
    def n_features(self) -> int:
        return self.W.shape[1]

    @property
    def n_params(self) -> int:
        return self.W.size + N_KEYS + (0 if self.release is None else N_KEYS)

    def copy(self) -> "Controller":
        return Controller(self.W.copy(), self.b.copy(), self.refractory_ms,
                          self.smooth_ms,
                          None if self.delay_ms is None else self.delay_ms.copy(),
                          self.trigger,
                          None if self.release is None else self.release.copy())

    # -- dynamics ----------------------------------------------------------

    def reset(self) -> None:
        self.z_s = np.zeros(self.n_features)
        self.u_prev = np.full(N_KEYS, -np.inf)
        self.du_prev = np.zeros(N_KEYS)
        self.last_press = np.full(N_KEYS, -np.inf)
        self.pending = []
        self.armed = np.zeros(N_KEYS, bool)
        self.relifted = np.zeros(N_KEYS, bool)

    def step(self, z: np.ndarray, t_ms: float, dt_ms: float) -> list[int]:
        """Feed one frame of z-scored channel activity; return keys pressed."""
        if self.smooth_ms > 0:
            self.z_s += (dt_ms / self.smooth_ms) * (np.asarray(z) - self.z_s)
        else:
            self.z_s = np.asarray(z, dtype=np.float64)
        u = self.W @ self.z_s + self.b
        ready = t_ms - self.last_press >= self.refractory_ms
        if self.trigger == "cross":
            fire = (u > 0) & (self.u_prev <= 0) & ready
            if self.release is not None:
                # A key lifted at its release level presses again when the
                # drive rises back through that level, without first falling
                # to zero.  On the harder real maps over half of all holds
                # have the next same-lane note within 100 ms of the tail, far
                # too soon for the drive to empty, so without this the
                # follower is never pressed at all.
                fire |= (self.relifted & (u > self.release)
                         & (self.u_prev <= self.release) & ready)
        elif self.trigger == "peak":
            # the drive has just turned over while still above threshold: this
            # is the channel's own peak, which arrives later than its crossing
            # and needs no parameter to locate
            du = u - self.u_prev
            fire = (u > 0) & (du < 0) & (self.du_prev >= 0) & np.isfinite(self.u_prev) & ready
            self.du_prev = np.where(np.isfinite(self.u_prev), du, 0.0)
        elif self.trigger == "fall":
            fire = (u <= 0) & (self.u_prev > 0) & ready
        else:
            raise ValueError(f"unknown trigger {self.trigger!r}")
        if self.release is not None:
            self.armed = (u > 0) & (self.armed | (u > self.release))
            lifted = self.armed & (u < self.release)
            self.relifted = (u > 0) & (self.relifted | lifted) & ~fire
        self.u_prev = u
        crossed = np.flatnonzero(fire).tolist()
        for k in crossed:
            self.last_press[k] = t_ms
        if self.delay_ms is None:
            return crossed
        # experiment 8: the channels peak hundreds of ms before the note
        # arrives, and no sensory front end removes the spread between them,
        # so the wait belongs here.  A crossing schedules a press; the press
        # happens delay_ms[k] later.  With delay 0 this is the branch above.
        for k in crossed:
            self.pending.append((t_ms + float(self.delay_ms[k]), k))
        keys = [k for (when, k) in self.pending if when <= t_ms]
        if keys:
            self.pending = [(w, k) for (w, k) in self.pending if w > t_ms]
        return keys

    def drive(self) -> np.ndarray:
        """Current pre-threshold drive, for display."""
        return self.W @ self.z_s + self.b

    def down(self) -> np.ndarray:
        """Which keys the drive is currently holding above threshold.

        Used for hold notes: a key goes down on the crossing that presses it and
        comes back up when its drive falls again, so the same threshold that
        decides *whether* to press also decides *how long* to hold.  Note this
        follows the crossing, not the scheduled press, so it is not meaningful
        together with ``delay_ms`` -- the untrained delay policy and hold notes
        have never been used on the same chart.

        With ``release`` set, a key that has risen above its release level
        lifts as soon as it falls back below it, rather than waiting for zero.
        """
        up = np.asarray(self.u_prev > 0)
        if self.release is None:
            return up
        return up & ~(self.armed & (self.u_prev < self.release))

    # -- construction ------------------------------------------------------

    @classmethod
    def anatomical(cls, fly: Fly, norm: ChannelNormaliser, r0: np.ndarray,
                   theta: float = 1.0, dt: float = DT_PLAY, **kw) -> "Controller":
        """Untrained policy: each key wired to the channel that prefers its lane."""
        Z = lane_response_matrix(fly, norm, r0, dt=dt)
        perm = best_assignment(Z)
        W = np.zeros((N_KEYS, N_KEYS))
        for lane, ch in enumerate(perm):
            W[lane, ch] = 1.0
        return cls(W=W, b=np.full(N_KEYS, -float(theta)), **kw)

    def with_delays(self, delay_ms) -> "Controller":
        """Copy of this controller that waits ``delay_ms[k]`` after each
        crossing before pressing key k.  Negative waits are impossible -- the
        policy cannot act before the evidence -- so they are clipped to 0."""
        c = self.copy()
        c.delay_ms = np.clip(np.asarray(delay_ms, dtype=np.float64), 0.0, None)
        return c

    @classmethod
    def blank(cls, theta: float = 1.0, **kw) -> "Controller":
        """No wiring at all: ``W = 0``.  Learning has to find the mapping."""
        return cls(W=np.zeros((N_KEYS, N_KEYS)), b=np.full(N_KEYS, -float(theta)), **kw)

    def wiring(self, names: list[str]) -> str:
        rows = []
        for k, key in enumerate("DFJK"):
            terms = [f"{self.W[k, c]:+.2f}*{names[c]}" for c in range(N_KEYS)
                     if abs(self.W[k, c]) > 1e-3]
            rows.append(f"  {key}: " + (" ".join(terms) if terms else "(nothing)")
                        + f"  {self.b[k]:+.2f}")
        return "\n".join(rows)


def lane_response_matrix(fly: Fly, norm: ChannelNormaliser, r0: np.ndarray,
                         dt: float = DT_PLAY, approach_ms: float = 800.0,
                         window: tuple[float, float] = (0.5, 1.0)) -> np.ndarray:
    """(lane, channel) mean z-scored response while one note falls in each lane,
    averaged over the part of the descent given by ``window`` (progress units)."""
    enc = Encoder(fly.ret)
    ph = fly.ph_local
    ext = np.zeros(fly.net.n, dtype=np.float32)
    steps = int(round(approach_ms / dt))
    rows = []
    for lane in range(len(LANE_AZ)):
        r = r0.copy()
        acc, n = np.zeros(N_KEYS), 0
        for i in range(steps):
            prog = i / steps
            ext[ph] = enc([(lane, prog)], dt)
            r = fly.net.step(r, ext, dt)
            if window[0] <= prog <= window[1]:
                acc += norm.z(fly.channels(r)); n += 1
        rows.append(acc / max(n, 1))
    return np.array(rows)


def static_response_matrix(fly: Fly, norm: ChannelNormaliser, r0: np.ndarray,
                           dt: float = DT_PLAY, duration_ms: float = 300.0) -> np.ndarray:
    """(lane, channel) z-scored settled response to a point at the judgment line
    (experiment 1's stimulus), kept for comparison."""
    rows = []
    for az in LANE_AZ:
        r, _ = fly.net.run(fly.stimulus([(float(az), EL_JUDGE, 1.0)], sigma_deg=SIGMA_DEG),
                           duration_ms=duration_ms, dt=dt, r0=r0)
        rows.append(norm.z(fly.channels(r)))
    return np.array(rows)


def best_assignment(Z: np.ndarray) -> list[int]:
    """Lane -> channel one-to-one assignment maximising the summed response."""
    return list(max(permutations(range(Z.shape[1])),
                    key=lambda p: sum(Z[i, p[i]] for i in range(Z.shape[0]))))
