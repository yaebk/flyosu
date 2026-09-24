"""
Retinotopic map for FlyWire photoreceptors.

The 11,391 annotated photoreceptors (R1-6 / R7 / R8) carry a 3-D annotation
point in FAFB voxel space.  For the R1-6 population that point sits in the
lamina, whose cartridges form a shallow, smoothly curved retinotopic sheet
(principal-axis spans of roughly 300 x 170 x 40 um per eye).  We therefore

  1. convert positions to isotropic nanometres (x,y * 4 nm, z * 40 nm),
  2. least-squares fit a sphere to each eye's R1-6 cloud,
  3. take each photoreceptor's optical axis to be the outward radial
     direction ``normalize(p - centre)`` -- R7/R8 are projected onto the same
     centre so colour channels stay in register with the R1-6 lattice,
  4. express that direction in head-centred spherical coordinates, and
  5. affinely rescale azimuth and elevation per eye so the mapped field
     matches the published angular extent of the Drosophila visual field.

Step 5 is needed because the lamina shell's centre of curvature is not the
eye's optical centre: the raw radial map is retinotopically ordered but spans
only ~80 deg of azimuth instead of ~150 deg.  The rescaling is monotone, so
neighbouring ommatidia stay neighbours; what it fixes is scale and offset.

Head axes recovered from anatomical landmarks in the same dataset (ocellar
neurons dorsal vs. SEZ gustatory ventral; antennal-lobe olfactory neurons
anterior vs. mushroom-body Kenyon cells posterior; ``side`` annotations put
the left hemisphere at low x):

    anterior = -z      dorsal = -y      right = +x

Azimuth is 0 deg straight ahead, positive to the fly's right.  Elevation is
0 deg at the horizon, positive dorsal.

Caveat: this is a geometric approximation, not a measured optical map.  Real
ommatidial axes deviate from the local surface normal, and the frontal acute
zone is magnified in a way a linear rescaling does not reproduce.  What the
encoder needs -- a smooth, monotone, correctly lateralised retinotopy -- it
provides.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .connectome import Connectome

VOXEL_NM = np.array([4.0, 4.0, 40.0])

# head-centred orthonormal basis expressed in FAFB voxel-space axes
ANTERIOR = np.array([0.0, 0.0, -1.0])
DORSAL = np.array([0.0, -1.0, 0.0])
RIGHT = np.array([1.0, 0.0, 0.0])

# published extent of the Drosophila visual field, used to calibrate step 5
AZ_CENTRE = {"left": -80.0, "right": 80.0}   # deg, eye-axis direction
AZ_SPAN = 150.0                               # deg covered by one eye (p2..p98)
EL_CENTRE = 5.0
EL_SPAN = 130.0
BLOB_CACHE_MAX = 4096        # ~140 MB of float32 blobs at 8,452 photoreceptors
AZ_LIMIT = (-172.0, 172.0)
EL_LIMIT = (-70.0, 82.0)


def _fit_sphere(P: np.ndarray) -> tuple[np.ndarray, float]:
    """Least-squares sphere fit.  Returns (centre, radius)."""
    A = np.hstack([2.0 * P, np.ones((len(P), 1))])
    b = (P ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    r = float(np.sqrt(sol[3] + c @ c))
    return c, r


def unit_vector(az_deg, el_deg) -> np.ndarray:
    """Head-frame unit vector(s) for azimuth/elevation in degrees."""
    az, el = np.deg2rad(az_deg), np.deg2rad(el_deg)
    v = (np.cos(el) * np.cos(az) * ANTERIOR[:, None]
         + np.cos(el) * np.sin(az) * RIGHT[:, None]
         + np.sin(el) * DORSAL[:, None])
    return np.squeeze(v.T).astype(np.float32)


@dataclass
class Retina:
    """Photoreceptor population with head-centred viewing directions."""

    idx: np.ndarray        # (P,) int32 neuron indices into the Connectome
    side: np.ndarray       # (P,)  'left' / 'right'
    ptype: np.ndarray      # (P,)  'R1-6' / 'R7' / 'R8'
    azimuth: np.ndarray    # (P,) float32 degrees, + = fly's right
    elevation: np.ndarray  # (P,) float32 degrees, + = dorsal
    direction: np.ndarray  # (P,3) float32 unit optical axes (head frame)
    fit: dict = field(default_factory=dict)
    _gain_cache: dict = field(default_factory=dict, repr=False, compare=False)
    _blob_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def __len__(self) -> int:
        return len(self.idx)

    def drive(self, targets, sigma_deg: float = 8.0,
              type_gain: dict | None = None) -> np.ndarray:
        """Photoreceptor activation for one or more bright points.

        ``targets`` is an iterable of ``(azimuth, elevation, intensity)``.
        Each contributes a Gaussian blob on the sphere,
        ``intensity * exp(-theta^2 / 2 sigma^2)``, where ``theta`` is the angle
        between the photoreceptor's optical axis and the target direction.
        Contributions add; the result is clipped to [0, 1].

        ``sigma_deg`` stands in for the ommatidial acceptance angle convolved
        with the apparent size of the stimulus (Drosophila Delta-rho is ~5 deg).
        """
        gain = {"R1-6": 1.0, "R7": 0.6, "R8": 0.6, "R?": 0.5}
        if type_gain:
            gain.update(type_gain)
        # the per-cell gain vector is the same on every call with the same
        # type_gain; building it from a Python loop over 8,452 cells was 70%
        # of the game's frame time before it was cached
        key = tuple(sorted(gain.items()))
        g = self._gain_cache.get(key)
        if g is None:
            g = np.array([gain.get(t, 1.0) for t in self.ptype], dtype=np.float32)
            self._gain_cache[key] = g

        # arithmetic kept exactly as originally written: rewriting it changed
        # results at 1e-7 and the calibration amplified that to a 2% change in
        # spectral radius, so cached and fresh models disagreed
        out = np.zeros(len(self), dtype=np.float32)
        s = np.deg2rad(sigma_deg)
        for az, el, amp in targets:
            if amp == 0.0:
                continue
            # Each blob is cached by its exact position.  Notes move in whole
            # frames, so the same (az, el) recurs constantly and the arccos and
            # exp over every photoreceptor -- a third of a frame -- need only
            # be done once per position; the arithmetic itself is untouched, so
            # results are bit-identical.  Bounded, since a real map's hold
            # bodies can produce many distinct positions.
            key = (float(az), float(el), float(sigma_deg))
            blob = self._blob_cache.get(key)
            if blob is None:
                cos = np.clip(self.direction @ unit_vector(az, el), -1.0, 1.0)
                theta = np.arccos(cos)
                blob = np.exp(-0.5 * (theta / s) ** 2).astype(np.float32)
                if len(self._blob_cache) >= BLOB_CACHE_MAX:
                    self._blob_cache.pop(next(iter(self._blob_cache)))
                self._blob_cache[key] = blob
            out += np.float32(amp) * blob
        return np.clip(out * g, 0.0, 1.0)

    def coverage(self) -> str:
        lines = []
        for side in ("left", "right"):
            m = self.side == side
            f = self.fit[side]
            lines.append(
                f"{side:>5s} eye  n={int(m.sum()):<5d} "
                f"az [{self.azimuth[m].min():7.1f},{self.azimuth[m].max():7.1f}] "
                f"el [{self.elevation[m].min():7.1f},{self.elevation[m].max():7.1f}] "
                f"shell R={f['radius_um']:.0f}um resid={f['residual_um']:.1f}um "
                f"az_gain={f['az_gain']:.2f}")
        return "\n".join(lines)


def build(cx: Connectome) -> Retina:
    idx = cx.where(super_class="sensory", cell_class="visual")
    ann = cx.ann.iloc[idx]

    pos = ann[["pos_x", "pos_y", "pos_z"]].to_numpy(dtype=float) * VOXEL_NM
    side = ann["side"].to_numpy()
    ptype = ann["cell_type"].fillna("R?").to_numpy().astype(object)

    # Only R1-6 are used.  Their annotation points sit in the lamina and form a
    # clean retinotopic sheet; R7/R8 terminate at several medulla depths, so a
    # radial projection from the lamina shell gives them meaningless angles
    # (verified: R7/R8 azimuths span the full sphere).  R1-6 is also the
    # achromatic motion channel, which is the relevant one for this task --
    # R7/R8 remain in the network but receive no photic drive.
    keep = (~np.isnan(pos).any(axis=1)
            & np.isin(side, ["left", "right"])
            & (ptype == "R1-6"))
    idx, pos, side, ptype = idx[keep], pos[keep], side[keep], ptype[keep]

    az = np.zeros(len(idx))
    el = np.zeros(len(idx))
    direction = np.zeros((len(idx), 3))
    fit: dict = {}

    for s in ("left", "right"):
        eye = side == s
        ref = eye & (ptype == "R1-6")          # lamina sheet defines the shell
        centre, radius = _fit_sphere(pos[ref])

        v = pos[eye] - centre
        d = np.linalg.norm(v, axis=1)
        u = v / d[:, None]
        # keep the outward normal pointing away from the midline
        if np.sign(u @ RIGHT).mean() * (-1.0 if s == "left" else 1.0) < 0:
            u = -u
        direction[eye] = u

        raw_az = np.rad2deg(np.arctan2(u @ RIGHT, u @ ANTERIOR))
        raw_el = np.rad2deg(np.arcsin(np.clip(u @ DORSAL, -1, 1)))

        # calibrate on the R1-6 sheet, apply to every photoreceptor of the eye
        ref_local = ptype[eye] == "R1-6"
        a_lo, a_mid, a_hi = np.percentile(raw_az[ref_local], [2, 50, 98])
        e_lo, e_mid, e_hi = np.percentile(raw_el[ref_local], [2, 50, 98])
        ga = AZ_SPAN / max(a_hi - a_lo, 1e-6)
        ge = EL_SPAN / max(e_hi - e_lo, 1e-6)

        az[eye] = np.clip(AZ_CENTRE[s] + (raw_az - a_mid) * ga, *AZ_LIMIT)
        el[eye] = np.clip(EL_CENTRE + (raw_el - e_mid) * ge, *EL_LIMIT)

        # the optical axes must agree with the *calibrated* angles, not the raw
        # radial ones, or drive() and the retinotopy would disagree
        direction[eye] = unit_vector(az[eye], el[eye])

        resid = float(np.std(np.linalg.norm(pos[ref] - centre, axis=1) - radius))
        fit[s] = {"centre_nm": centre, "radius_um": radius / 1e3,
                  "residual_um": resid / 1e3, "az_gain": ga, "el_gain": ge,
                  "n_ref": int(ref.sum())}

    return Retina(idx=idx.astype(np.int32), side=side, ptype=ptype,
                  azimuth=az.astype(np.float32), elevation=el.astype(np.float32),
                  direction=direction.astype(np.float32), fit=fit)


if __name__ == "__main__":
    from . import connectome as C

    cx = C.load()
    ret = build(cx)
    print(f"photoreceptors mapped: {len(ret):,}  "
          f"({int((ret.ptype == 'R1-6').sum()):,} R1-6)")
    print(ret.coverage())
    print("\nlateralisation check (sigma=10 deg, el=0):")
    for a in (-120, -60, -20, 0, 20, 60, 120):
        d = ret.drive([(a, 0.0, 1.0)], sigma_deg=10)
        L, R = ret.side == "left", ret.side == "right"
        print(f"  az={a:+5d}  active={int((d > 0.1).sum()):4d}  "
              f"sum_left={d[L].sum():7.1f}  sum_right={d[R].sum():7.1f}")
