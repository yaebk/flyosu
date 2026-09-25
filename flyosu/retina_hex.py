"""
Retinotopy for the male CNS, built from the optic-lobe column lattice.

The male CNS volume stops short of the retina: only 13 of the 3,377 R1-R6
photoreceptor bodies have a soma, so ``retina.py``'s sphere fit to
photoreceptor positions has nothing to fit.  What the dataset has instead is
better in one way and worse in another.  Better: twelve columnar cell types
carry an explicit per-eye hexagonal column index (``assignedOlHex1/2``, 879
columns left, 892 right), so the lattice is *annotated* rather than inferred
from soma positions.  Worse: photoreceptor coverage of that lattice is partial
(300/879 left, 525/892 right) and the left eye's photoreceptors sit almost
entirely in its dorsal half, where the game's lanes are not.

So the input layer here is the **lamina monopolar cells L1 and L2**, one of
each per column and complete in both eyes, and not the photoreceptor stubs.
They are the first-order relay of R1-R6, they are the cells the whole motion
pathway hangs off, and driving them directly costs one synapse of fidelity.
Two consequences are declared rather than hidden:

  * L1/L2 are clamped to *light intensity* (bright = active) so that the
    encoder means the same thing on both datasets.  Real L1/L2 hyperpolarise
    to light (histamine from R1-R6 is inhibitory) -- this input layer is a
    retinotopic array, not a model of L1/L2 physiology.
  * The R1-R6 -> L1/L2 synapse is skipped, so the histamine sign flip that
    distinguishes this dataset from FlyWire at the first synapse does not
    enter the model.

Viewing directions.  Per eye, the columnar cells with a soma (Mi1, Tm1, Tm2,
Mi4, Mi9, Tm9, Tm20, C3, T1 -- the medulla cortex, ~15,600 somata) are
averaged per column, a sphere is fitted to the column centres (radius ~145 um,
residual ~12 um, as clean as FlyWire's lamina sheet), and each column's raw
radial direction is expressed in a head frame recovered from the same
landmarks ``retina.py`` used (ocelli dorsal vs SEZ motor neurons ventral,
antennal-lobe PNs anterior vs Kenyon cells posterior, side annotation for
left/right).  A per-eye quadratic map (hex1, hex2) -> (raw az, raw el) is then
fitted to those columns and applied to *every* column, which smooths the
soma-averaging noise and covers the ~50 columns per eye without medulla
somata.  Finally the same monotone per-eye rescaling to published field
extents as ``retina.py`` is applied, for the same reason: the shell's centre
of curvature is not the eye's optical centre, so raw radial spans undershoot
the ~150 deg field.

The result is a ``retina.Retina`` -- same fields, same ``drive()`` -- with
``ptype`` in {"L1", "L2"} so the rest of the pipeline is unchanged.

Caveats, as in retina.py and then some: this is a geometric approximation
calibrated to published extents, not a measured eye map; the hex axes are
oblique to the head frame and the quadratic fit is exactly that; the frontal
acute zone is not reproduced.  The published column -> viewing-direction map
for this dataset would replace all of it.
"""

from __future__ import annotations

import numpy as np

from .connectome import Connectome
from .retina import (AZ_CENTRE, AZ_LIMIT, AZ_SPAN, EL_CENTRE, EL_LIMIT, EL_SPAN,
                     Retina, _fit_sphere, unit_vector)

INPUT_TYPES = ("L1", "L2")
# medulla-cortex columnar types whose somata lie on a clean shell (docs/MALECNS.md)
SHELL_TYPES = ("Mi1", "Tm1", "Tm2", "Mi4", "Mi9", "Tm9", "Tm20", "C3", "T1")


def _unit(v):
    return v / np.linalg.norm(v)


def head_frame(cx: Connectome, voxel_nm: float) -> dict:
    """Orthonormal head axes (in voxel-space directions) from anatomical landmarks."""
    a = cx.ann
    pos = a[["pos_x", "pos_y", "pos_z"]].to_numpy(dtype=float) * voxel_nm
    ok = ~np.isnan(pos).any(axis=1)

    def centroid(mask):
        m = mask.to_numpy() & ok
        if m.sum() == 0:
            raise RuntimeError("landmark population missing")
        return pos[m].mean(axis=0)

    dorsal = centroid(a.cell_type.fillna("").str.startswith("OCG")) - centroid(a.super_class == "motor")
    anterior = centroid(a.cell_class == "ALPN") - centroid(a.cell_class == "Kenyon_Cell")
    right = centroid(a.side == "right") - centroid(a.side == "left")
    right = _unit(right)
    dorsal = _unit(dorsal - (dorsal @ right) * right)
    anterior = _unit(anterior - (anterior @ right) * right - (anterior @ dorsal) * dorsal)
    return {"right": right, "dorsal": dorsal, "anterior": anterior}


def _design(H: np.ndarray) -> np.ndarray:
    """Quadratic design matrix in (hex1, hex2): smooth, and it follows the
    curvature of the radial projection better than an affine map does."""
    h1, h2 = H[:, 0], H[:, 1]
    return np.column_stack([np.ones(len(H)), h1, h2, h1 * h1, h1 * h2, h2 * h2])


def build(cx: Connectome, voxel_nm: float = 8.0) -> Retina:
    a = cx.ann
    frame = head_frame(cx, voxel_nm)
    fit: dict = {}

    inp = a[a.cell_type.isin(INPUT_TYPES) & a.hex1.notna() & a.hex2.notna()
            & a.side.isin(["left", "right"])]
    shell = a[a.cell_type.isin(SHELL_TYPES) & a.hex1.notna() & a.hex2.notna()
              & a.pos_x.notna() & a.side.isin(["left", "right"])]

    idx = inp.index.to_numpy().astype(np.int32)
    side = inp.side.to_numpy().astype(object)
    ptype = inp.cell_type.to_numpy().astype(object)
    az = np.zeros(len(inp)); el = np.zeros(len(inp))

    for s in ("left", "right"):
        sh = shell[shell.side == s]
        col = (sh.groupby(["hex1", "hex2"])[["pos_x", "pos_y", "pos_z"]].mean() * voxel_nm)
        P = col.to_numpy(dtype=float)
        centre, radius = _fit_sphere(P)
        u = P - centre
        d = np.linalg.norm(u, axis=1)
        u = u / d[:, None]
        # outward normal points away from the midline
        if np.sign(u @ frame["right"]).mean() * (-1.0 if s == "left" else 1.0) < 0:
            u = -u
        raw_az = np.rad2deg(np.arctan2(u @ frame["right"], u @ frame["anterior"]))
        raw_el = np.rad2deg(np.arcsin(np.clip(u @ frame["dorsal"], -1, 1)))

        # smooth (hex1, hex2) -> (raw az, raw el), fitted on columns with somata
        H = np.array(col.index.tolist(), dtype=float)
        X = _design(H)
        coef_az, *_ = np.linalg.lstsq(X, raw_az, rcond=None)
        coef_el, *_ = np.linalg.lstsq(X, raw_el, rcond=None)
        fit_az = X @ coef_az; fit_el = X @ coef_el
        resid_ang = float(np.sqrt(np.mean((fit_az - raw_az) ** 2 + (fit_el - raw_el) ** 2)))

        # apply to every input cell's column, then rescale as retina.py does
        m = side == s
        Hi = inp.loc[m, ["hex1", "hex2"]].to_numpy(dtype=float)
        Xi = _design(Hi)
        a_raw = Xi @ coef_az; e_raw = Xi @ coef_el
        a_lo, a_mid, a_hi = np.percentile(fit_az, [2, 50, 98])
        e_lo, e_mid, e_hi = np.percentile(fit_el, [2, 50, 98])
        ga = AZ_SPAN / max(a_hi - a_lo, 1e-6)
        ge = EL_SPAN / max(e_hi - e_lo, 1e-6)
        az[m] = np.clip(AZ_CENTRE[s] + (a_raw - a_mid) * ga, *AZ_LIMIT)
        el[m] = np.clip(EL_CENTRE + (e_raw - e_mid) * ge, *EL_LIMIT)

        fit[s] = {"centre_nm": centre, "radius_um": radius / 1e3,
                  "residual_um": float(np.std(d - radius)) / 1e3,
                  "n_columns_with_soma": int(len(P)), "n_input_cells": int(m.sum()),
                  "fit_residual_deg": resid_ang, "az_gain": ga, "el_gain": ge,
                  "coef_az": coef_az, "coef_el": coef_el}

    # optical axes in the *canonical* head frame that Retina.drive() uses for
    # its target vectors -- the voxel-space frame is only for turning soma
    # positions into angles.  (Mixing the two mirrors the eyes: right is -x in
    # this volume and +x in FAFB.)
    direction = unit_vector(az, el)
    ret = Retina(idx=idx, side=side, ptype=ptype, azimuth=az.astype(np.float32),
                 elevation=el.astype(np.float32), direction=direction.astype(np.float32),
                 fit=fit)
    ret.fit["frame"] = frame
    ret.fit["input_types"] = list(INPUT_TYPES)
    return ret


def coverage(ret: Retina) -> str:
    lines = []
    for s in ("left", "right"):
        m = ret.side == s
        f = ret.fit[s]
        lines.append(
            f"{s:>5s} eye  n={int(m.sum()):<5d} "
            f"az [{ret.azimuth[m].min():7.1f},{ret.azimuth[m].max():7.1f}] "
            f"el [{ret.elevation[m].min():7.1f},{ret.elevation[m].max():7.1f}] "
            f"shell R={f['radius_um']:.0f}um resid={f['residual_um']:.1f}um "
            f"fit resid={f['fit_residual_deg']:.1f}deg cols={f['n_columns_with_soma']}")
    return "\n".join(lines)


if __name__ == "__main__":
    from . import malecns as MC

    cx = MC.load(verbose=False)
    ret = build(cx)
    print(f"input layer: {len(ret):,} cells "
          + ", ".join(f"{t}={int((ret.ptype == t).sum())}" for t in INPUT_TYPES))
    print(coverage(ret))
    fr = ret.fit["frame"]
    print("head frame (voxel axes): right", np.round(fr["right"], 2),
          "dorsal", np.round(fr["dorsal"], 2), "anterior", np.round(fr["anterior"], 2))
    print("\nlateralisation check (sigma=10 deg, el=-25):")
    for a in (-120, -60, -20, 0, 20, 60, 120):
        d = ret.drive([(a, -25.0, 1.0)], sigma_deg=10)
        L = ret.side == "left"
        print(f"  az={a:+5d}  active={int((d > 0.1).sum()):4d}  "
              f"sum_left={d[L].sum():7.1f}  sum_right={d[~L].sum():7.1f}")
    # neighbouring columns should land at neighbouring angles
    a_ = cx.ann.iloc[ret.idx]
    for s in ("left", "right"):
        m = (ret.side == s) & (ret.ptype == "L1")
        H = a_[m][["hex1", "hex2"]].to_numpy()
        key = {tuple(h): i for h, i in zip(H, np.flatnonzero(m))}
        gaps = []
        for (h1, h2), i in key.items():
            j = key.get((h1 + 1, h2))
            if j is not None:
                v1 = ret.direction[i]; v2 = ret.direction[j]
                gaps.append(np.rad2deg(np.arccos(np.clip(v1 @ v2, -1, 1))))
        print(f"{s} eye: hex-neighbour angular spacing median {np.median(gaps):.2f} deg "
              f"(p95 {np.percentile(gaps, 95):.2f})")
