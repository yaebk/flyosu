"""
Sensory encoder: what is on the playfield -> what lands on the eye.

Step 6.  The playfield is wrapped around the fly as a cylindrical arena (see
docs/CALIBRATION.md): the four lanes sit at azimuth -60, -20, +20, +60 deg and
a note travels from +35 deg elevation (spawn) down to -25 deg (the judgment
line).  Those numbers were fixed from eye geometry before experiment 1 and are
imported from the same place it used them, so the game the fly plays is the
one it was measured on.

Two front ends:

``Encoder``          static.  Each note is one bright point at its current
                     position, the same stimulus experiment 1 used.  Default.

``Encoder(adapt=..)`` adds photoreceptor adaptation -- a high-pass transient on
                     top of the static response, ``s + gain * relu(s - s_slow)``
                     with ``s_slow`` a low-pass copy of the input.  Real fly
                     photoreceptors and the lamina cells behind them (L1/L2) do
                     this, and the lobula columnar neurons in this dataset are
                     small-moving-object detectors for which a static point is a
                     weak stimulus.  Off by default because the network was
                     calibrated on static points; it is a declared variant, not
                     a silent change.
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
                 adapt_tau_ms: float = 100.0, adapt_gain: float = 1.0):
        self.ret = retina
        self.sigma = float(sigma_deg)
        self.intensity = float(intensity)
        self.adapt_tau = float(adapt if adapt is not None else adapt_tau_ms)
        self.adapt_gain = float(adapt_gain) if adapt is not None else 0.0
        self.slow: np.ndarray | None = None

    def reset(self) -> None:
        self.slow = None

    def targets(self, visible) -> list[tuple[float, float, float]]:
        """``visible`` is ``[(lane, progress, ...), ...]`` from the environment."""
        return [(float(LANE_AZ[lane]), float(elevation(prog)), self.intensity)
                for lane, prog, *_ in visible]

    def __call__(self, visible, dt_ms: float) -> np.ndarray:
        """Photoreceptor drive vector (len(retina),) for this frame."""
        s = self.ret.drive(self.targets(visible), sigma_deg=self.sigma)
        if self.adapt_gain <= 0:
            return s
        if self.slow is None:
            self.slow = s.copy()
        out = np.clip(s + self.adapt_gain * np.maximum(s - self.slow, 0.0), 0.0, 1.0)
        self.slow += (dt_ms / self.adapt_tau) * (s - self.slow)
        return out.astype(np.float32)

    def describe(self) -> str:
        base = (f"lanes at az {LANE_AZ.tolist()} deg, el {EL_SPAWN:+.0f} -> "
                f"{EL_JUDGE:+.0f} deg, sigma {self.sigma:.0f} deg")
        if self.adapt_gain > 0:
            base += f", adaptation tau {self.adapt_tau:.0f} ms gain {self.adapt_gain:g}"
        return base
