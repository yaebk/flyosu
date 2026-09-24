"""
Sensory encoder: what is on the playfield -> what lands on the eye.

Step 6.  The playfield is wrapped around the fly as a cylindrical arena (see
docs/CALIBRATION.md): the four lanes sit at azimuth -60, -20, +20, +60 deg and
a note travels from +35 deg elevation (spawn) down to -25 deg (the judgment
line).  Those numbers were fixed from eye geometry before experiment 1 and are
imported from the same place it used them, so the game the fly plays is the
one it was measured on.

Four front ends.  The first is the default; the other three are experiment
8's attempt to make the network respond to a note's *arrival* rather than to
its appearance at the top of the playfield:

``Encoder``          static.  Each note is one bright point at its current
                     position, the same stimulus experiment 1 used.  Default.

``Encoder(adapt=..)`` adds photoreceptor adaptation -- a high-pass transient on
                     top of the static response, ``base * s + gain * relu(s -
                     s_slow)`` with ``s_slow`` a low-pass copy of the input.
                     Real fly photoreceptors and the lamina cells behind them
                     (L1/L2) do this, and the lobula columnar neurons in this
                     dataset are small-moving-object detectors for which a
                     static point is a weak stimulus.  ``adapt_base`` weights
                     the sustained term: 1.0 keeps it, 0.0 makes the front end
                     purely transient.  Off by default because the network was
                     calibrated on static points; it is a declared variant, not
                     a silent change.

``Encoder(gate_sigma_deg=..)``  a fixed *elevation gate* on the photoreceptor
                     array: every photoreceptor's drive is scaled by
                     ``exp(-((el - gate_el)^2) / 2 gate_sigma^2)`` -- a band
                     centred on ``gate_el``, the judgment elevation by default
                     -- or, with ``gate_below_deg``, by the ventral half-field
                     sigmoid ``1 / (1 + exp((el - gate_below) / gate_width))``,
                     which leaves the drive at full strength once the note is
                     under the edge instead of attenuating it.  ``gate_gain``
                     multiplies the gated drive before the [0,1] clip, to put
                     the input back on the scale the network was calibrated
                     for.  Experiment 8.  This is a receptive-field
                     weighting, not a spotlight:
                     it is the same fixed vector on every frame, it knows
                     nothing about lanes, notes or time, and it is applied
                     identically to the real connectome and every control.  But
                     it is a *significant added assumption* and is declared as
                     one -- it says the fly only sees the ventral strip of the
                     playfield around the judgment line, which no measurement in
                     this project supports.  A ventral acute zone is the nearest
                     real thing (Drosophila does have regional specialisations),
                     but nothing says it sits at -25 deg or has this width.  Its
                     purpose is mechanical: a note becomes visible only as it
                     enters the band, so the network's onset transient fires at
                     note *arrival* instead of note spawn.  Note that the
                     channel normaliser is still fitted on the ungated
                     calibration ensemble, exactly as for every other front end,
                     so z units stay comparable across variants.

``Encoder(loom=..)`` makes a note *grow* as it falls: its amplitude is
                     ``intensity * (1 + loom * progress**loom_exp)``, so the
                     drive is the calibrated static point at spawn and several
                     times larger at the judgment line (the per-photoreceptor
                     drive saturates at 1, so what actually grows is the blob,
                     as a looming object's image does).  Experiment 8, and also
                     a declared assumption: real osu!mania sprites are a
                     constant size, so this is a change to the *display*, not a
                     property of the fly.  It buys a stimulus whose energy
                     peaks at arrival instead of being flat across the descent,
                     without blanking any part of the visual field.
"""

from __future__ import annotations

import numpy as np

from .retina import Retina

LANE_AZ = np.array([-60.0, -20.0, 20.0, 60.0])   # deg, keys D F J K
EL_SPAWN = 35.0
EL_JUDGE = -25.0
SIGMA_DEG = 10.0


def elevation(progress) -> np.ndarray:
    """Elevation of a note at the given progress (0 spawn, 1 judgment line).
    Notes keep sliding past the line at the same speed until retired."""
    return EL_SPAWN + (EL_JUDGE - EL_SPAWN) * np.asarray(progress, dtype=float)


class Encoder:
    def __init__(self, retina: Retina, sigma_deg: float = SIGMA_DEG,
                 intensity: float = 1.0, adapt: float | None = None,
                 adapt_tau_ms: float = 100.0, adapt_gain: float = 1.0,
                 adapt_base: float = 1.0, gate_sigma_deg: float | None = None,
                 gate_el_deg: float = EL_JUDGE, gate_below_deg: float | None = None,
                 gate_width_deg: float = 4.0, gate_gain: float = 1.0,
                 loom: float = 0.0, loom_exp: float = 1.0,
                 hold_intensity: float = 0.6, hold_step: float = 0.08,
                 hold_points: int = 10, hold_grid: bool = False,
                 lane_az=None):
        self.ret = retina
        self.sigma = float(sigma_deg)
        self.intensity = float(intensity)
        self.loom = float(loom)
        self.loom_exp = float(loom_exp)
        # A hold note's body is drawn as points every ``hold_step`` of progress,
        # at ``hold_intensity`` of a head's brightness and at most
        # ``hold_points`` of them, so a long hold is a dimmer bar rather than a
        # row of things that each look like a note to press.
        self.hold_intensity = float(hold_intensity)
        self.hold_step = float(hold_step)
        self.hold_points = int(hold_points)
        # ``hold_grid`` draws the body differently: an explicit tail point, and
        # body points fixed on the screen at multiples of ``hold_step`` rather
        # than spread evenly between tail and head.  A real hold is an
        # untextured bar, so any one spot on the screen is either covered or
        # not; evenly spread points slide every frame and flicker where the bar
        # would not, and they leave the tail implicit.  Fixed positions also
        # recur, so the retina's blob cache covers them -- on a hold-heavy map
        # the sliding points were ~14 full blob computations per frame.  Off by
        # default so every earlier hold result is unchanged.
        self.hold_grid = bool(hold_grid)
        # Where each lane falls in the visual field, degrees of azimuth.  The
        # default +-20/+-60 is a choice, not a fact about the game: lanes that
        # land further apart on the retina reach more separate neurons, so they
        # may interfere less when several are on screen at once.
        self.lane_az = np.asarray(LANE_AZ if lane_az is None else lane_az, dtype=float)
        self.adapt_tau = float(adapt if adapt is not None else adapt_tau_ms)
        self.adapt_gain = float(adapt_gain) if adapt is not None else 0.0
        self.adapt_base = float(adapt_base)
        self.gate_sigma = None if gate_sigma_deg is None else float(gate_sigma_deg)
        self.gate_el = float(gate_el_deg)
        self.gate_below = None if gate_below_deg is None else float(gate_below_deg)
        self.gate_width = float(gate_width_deg)
        self.gate_gain = float(gate_gain)
        self.gate: np.ndarray | None = None
        el = np.asarray(retina.elevation, dtype=np.float32)
        if self.gate_below is not None:
            g = 1.0 / (1.0 + np.exp((el - np.float32(self.gate_below))
                                    / np.float32(self.gate_width)))
        elif self.gate_sigma is not None:
            g = np.exp(-0.5 * ((el - np.float32(self.gate_el))
                               / np.float32(self.gate_sigma)) ** 2)
        else:
            g = None
        if g is not None:
            self.gate = (np.float32(self.gate_gain) * g).astype(np.float32)
        self.slow: np.ndarray | None = None

    def reset(self) -> None:
        self.slow = None

    def _intensity(self, prog: float) -> float:
        if self.loom <= 0:
            return self.intensity
        return self.intensity * (1.0 + self.loom
                                 * min(max(float(prog), 0.0), 1.0) ** self.loom_exp)

    def targets(self, visible) -> list[tuple[float, float, float]]:
        """``visible`` is ``[(lane, progress, note, tail_progress), ...]``.

        A hold note is drawn as a *bar*: its head, plus points spread along the
        body between the tail and the judgment line.  Before experiment 20 only
        the head was drawn, which meant the fly could not see that a note was a
        hold, how long it lasted, or when to let go -- and it duly scored about
        zero on them however it was trained, because the information was not in
        the input at all.  Once the head has been taken the head point is
        dropped and only the shrinking body remains, which is the cue to
        release.

        An ordinary note has ``tail_progress`` of ``None`` and is drawn exactly
        as before, so a chart without holds is bit-identical.
        """
        out = []
        for item in visible:
            lane, prog = item[0], float(item[1])
            tail = item[3] if len(item) > 3 else None
            az = float(self.lane_az[lane])
            if tail is None:
                out.append((az, float(elevation(prog)), self._intensity(prog)))
                continue
            held = prog > 1.0          # head already judged; body is what is left
            if not held:
                out.append((az, float(elevation(prog)), self._intensity(prog)))
            lo, hi = float(tail), min(prog, 1.0)
            if hi <= lo:
                continue
            if self.hold_grid:
                a = self.hold_intensity
                if lo >= 0.0:                      # the tail, once it is on screen
                    out.append((az, float(elevation(lo)), self._intensity(lo) * a))
                j_hi = int(np.ceil(hi / self.hold_step)) - 1         # strictly below hi
                j_lo = max(int(np.floor(lo / self.hold_step)) + 1, 0)  # strictly above lo, on screen
                for j in range(j_hi, max(j_lo, j_hi - self.hold_points + 1) - 1, -1):
                    p = j * self.hold_step
                    out.append((az, float(elevation(p)), self._intensity(p) * a))
                continue
            k = int(min(self.hold_points, max(1, round((hi - lo) / self.hold_step))))
            for j in range(1, k + 1):
                p = lo + (hi - lo) * j / (k + 1)
                out.append((az, float(elevation(p)),
                            self._intensity(p) * self.hold_intensity))
        return out

    def __call__(self, visible, dt_ms: float) -> np.ndarray:
        """Photoreceptor drive vector (len(retina),) for this frame."""
        s = self.ret.drive(self.targets(visible), sigma_deg=self.sigma)
        if self.gate is not None:
            s = np.clip(s * self.gate, 0.0, 1.0)
        if self.adapt_gain <= 0:
            return s
        if self.slow is None:
            self.slow = s.copy()
        out = np.clip(self.adapt_base * s
                      + self.adapt_gain * np.maximum(s - self.slow, 0.0), 0.0, 1.0)
        self.slow += (dt_ms / self.adapt_tau) * (s - self.slow)
        return out.astype(np.float32)

    def describe(self) -> str:
        base = (f"lanes at az {self.lane_az.tolist()} deg, el {EL_SPAWN:+.0f} -> "
                f"{EL_JUDGE:+.0f} deg, sigma {self.sigma:.0f} deg")
        if self.loom > 0:
            base += f", loom x{1.0 + self.loom:g} by arrival (exp {self.loom_exp:g})"
        if self.gate is not None:
            base += (f", ventral gate below {self.gate_below:+.0f} deg "
                     f"(edge {self.gate_width:.0f} deg)" if self.gate_below is not None
                     else f", elevation gate el {self.gate_el:+.0f} sigma "
                          f"{self.gate_sigma:.0f} deg")
            if self.gate_gain != 1.0:
                base += f" x{self.gate_gain:g}"
        if self.adapt_gain > 0:
            base += (f", adaptation tau {self.adapt_tau:.0f} ms gain "
                     f"{self.adapt_gain:g} base {self.adapt_base:g}")
        return base
