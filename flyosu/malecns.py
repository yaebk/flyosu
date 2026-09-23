"""
Male CNS v1.0 connectome loader (brain + optic lobes + ventral nerve cord).

Produces the same index-aligned ``Connectome`` object as ``connectome.py`` does
for FlyWire v783, so everything downstream can be pointed at either dataset.
The reason to want this dataset at all is that it continues below the
descending neurons: 708 ``vnc_motor`` neurons are present, so the four keys can
become four real leg motor pools instead of four k-means clusters.

Data (three Apache Feather files in data/malecns/, see data/SOURCES.md):
  * body-annotations-...-minconf-0.5.feather   211,577 bodies, 36 columns
  * body-neurotransmitters-....feather          1,835,518 bodies, one row each
  * connectome-weights-...-minconf-0.5.feather  151,856,684 (pre, post, weight)
                                                edges in 2,318 record batches

Decisions the data did not make, all measured before being made:

Neuron universe.  The weights file connects 1.8 M bodies, but only 211,577 are
in the annotation table and only 166,700 of those have a ``superclass``; the
rest are glia, orphan fragments, "unimportant" and out-of-scope bodies.  Edges
touching a fragment are 83% of the raw edge list by count but carry no
identity, so the universe here is the 166,700 bodies with a superclass.  That
drops 1.7% of the edges between annotated bodies (glia/orphan endpoints).
Unlike ``connectome.py`` there is no union with edge endpoints: every row of
``ann`` is a real annotated neuron and no row is NaN-filled.

Edge threshold.  The weights file is sorted by weight descending, so a
threshold is a prefix of batches.  Measured counts restricted to the universe:
weight >= 1: 25.58 M edges / 124.2 M synapses; >= 2: 15.28 M / 113.9 M;
>= 3: 10.52 M / 104.4 M; >= 5: 6.24 M / 89.9 M; >= 10: 2.75 M / 67.3 M.
FlyWire v783 has 15.09 M edges (unthresholded, 54.5 M synapses), so
``DEFAULT_MIN_WEIGHT = 2`` gives a graph of the same edge count.  It has twice
the synapses: the male CNS is a larger volume with a VNC and the synapse
detector was run at confidence >= 0.5.

Sign.  One transmitter per body from ``consensus_nt`` (ground truth where
known, else the cell-type-level prediction, else the per-body prediction;
one row per body, so no tie-breaking is needed).  Acetylcholine -> +1; GABA,
glutamate -> -1; histamine -> -1 (the photoreceptor transmitter, which opens
chloride channels on lamina cells -- FlyWire has no histamine class and signed
81% of photoreceptor edges +1, so the first visual synapse flips sign between
the two datasets); dopamine, octopamine, serotonin -> +1, as FlyWire/Shiu et
al. do; ``unclear`` or missing -> +1 and ``top_nt = 'unknown'``.  The 3,177
bodies without a usable transmitter are mostly VNC motor neurons (389, whose
output sign hardly matters: they are the readout) and cb_intrinsic (798).

Super_class vocabulary.  Mapped onto FlyWire's names where an equivalent
exists (optic, central, sensory, visual_projection, visual_centrifugal,
descending, ascending, sensory_ascending, motor, endocrine) and given new
names where FlyWire has nothing: ``vnc_intrinsic``, ``vnc_motor``
(kept separate from ``motor`` = brain motor neurons, so that
``where(super_class="motor")`` means the same thing in both datasets),
``efferent``, ``sensory_descending``, ``ens``.  The "_tbc" (to be confirmed)
superclasses keep a ``_tbc`` suffix so the confident counts (1,314 descending,
708 vnc_motor) are exact.  The original ``superclass`` column is kept.

Side.  ``somaSide`` (L/R/M -> left/right/center), falling back to ``rootSide``
and then to the ``_L``/``_R`` suffix of ``instance``.  The fallbacks matter:
photoreceptors have no soma in the volume, so their side comes from
``rootSide`` (populated for all 6,091).

Positions.  ``somaLocation`` is a [x, y, z] voxel triple at 8 nm isotropic
(https://male-cns.janelia.org/download/).  It is a soma, not FlyWire's
"annotation point", and it is missing for all sensory neurons (the retina and
the peripheral sensory somata are outside the imaged volume).  ``pos_*`` and
``soma_*`` are the same numbers here.  ``hex1``/``hex2`` carry the optic-lobe
column lattice coordinates (``assignedOlHex1/2``) for 23,720 columnar
optic-lobe neurons -- the route to a photoreceptor retinotopy, see
docs/MALECNS.md.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.feather as pf
import pyarrow.ipc as ipc

from .connectome import Connectome

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data", "malecns")

ANNOTATIONS = os.path.join(DATA_DIR, "body-annotations-male-cns-v1.0-minconf-0.5.feather")
NEUROTRANSMITTERS = os.path.join(DATA_DIR, "body-neurotransmitters-male-cns-v1.0.feather")
WEIGHTS = os.path.join(DATA_DIR, "connectome-weights-male-cns-v1.0-minconf-0.5.feather")

ANN_CACHE = os.path.join(DATA_DIR, "malecns_v1_ann.parquet")

DEFAULT_MIN_WEIGHT = 2
VOXEL_NM = 8.0                     # somaLocation units, isotropic

SUPERCLASS_MAP = {
    "ol_intrinsic": "optic",
    "cb_intrinsic": "central",
    "vnc_intrinsic": "vnc_intrinsic",
    "visual_projection": "visual_projection",
    "visual_centrifugal": "visual_centrifugal",
    "ol_sensory": "sensory",
    "cb_sensory": "sensory",
    "vnc_sensory": "sensory",
    "sensory_ascending": "sensory_ascending",
    "sensory_descending": "sensory_descending",
    "ascending_neuron": "ascending",
    "descending_neuron": "descending",
    "cb_motor": "motor",
    "vnc_motor": "vnc_motor",
    "cb_endocrine": "endocrine",
    "vnc_endocrine": "endocrine",
    "cb_efferent": "efferent",
    "vnc_efferent": "efferent",
    "efferent_ascending": "efferent",
    "efferent_descending": "efferent",
    "ENS": "ens",
    # to-be-confirmed variants keep the suffix so confident counts stay exact
    "vnc_tbc": "vnc_intrinsic_tbc",
    "vnc_sensory_tbc": "sensory_tbc",
    "cb_sensory_tbc": "sensory_tbc",
    "visual_projection_tbc": "visual_projection_tbc",
    "sensory_ascending_tbc": "sensory_ascending_tbc",
    "descending_neuron_tbc": "descending_tbc",
}

REGION_OF_PREFIX = {"ol_": "optic_lobe", "visual_": "optic_lobe", "cb_": "brain",
                    "vnc_": "vnc"}

NT_SIGN = {
    "acetylcholine": 1,
    "gaba": -1,
    "glutamate": -1,
    "histamine": -1,
    "dopamine": 1,
    "octopamine": 1,
    "serotonin": 1,
    "unknown": 1,
}

AFFERENT = {"sensory", "sensory_ascending", "sensory_descending", "sensory_tbc",
            "sensory_ascending_tbc"}
EFFERENT = {"motor", "vnc_motor", "efferent", "endocrine", "ens"}


def cache_path(min_weight: int) -> str:
    return os.path.join(DATA_DIR, f"malecns_v1_w{min_weight}.npz")


def _member(x: np.ndarray, sorted_ids: np.ndarray) -> np.ndarray:
    """Boolean membership of ``x`` in a sorted int array (searchsorted, no hashing)."""
    j = np.searchsorted(sorted_ids, x)
    j[j == len(sorted_ids)] = 0
    return sorted_ids[j] == x


def _region(superclass: str) -> str:
    for prefix, region in REGION_OF_PREFIX.items():
        if superclass.startswith(prefix):
            return region
    if superclass.startswith(("descending", "ascending", "sensory_", "efferent")):
        return "neck"            # spans brain and VNC; the name says which way
    return "other"


def _build_annotations(verbose: bool) -> pd.DataFrame:
    raw = pf.read_feather(ANNOTATIONS)
    raw = raw[raw.superclass.notna()].copy()
    assert not raw.bodyId.duplicated().any(), "duplicate bodyId in annotation table"
    raw = raw.sort_values("bodyId").reset_index(drop=True)

    ann = pd.DataFrame({"root_id": raw.bodyId.to_numpy(dtype=np.int64)})

    # soma position: a [x, y, z] voxel triple or None
    loc = raw.somaLocation
    has = loc.notna().to_numpy()
    xyz = np.full((len(raw), 3), np.nan)
    if has.any():
        xyz[has] = np.stack(loc[has].to_numpy()).astype(float)
    for k, c in enumerate("xyz"):
        ann[f"pos_{c}"] = xyz[:, k]
        ann[f"soma_{c}"] = xyz[:, k]

    sc = raw.superclass.map(SUPERCLASS_MAP)
    unmapped = raw.superclass[sc.isna()].unique()
    assert len(unmapped) == 0, f"unmapped superclass values: {unmapped}"
    ann["super_class"] = sc.to_numpy()
    ann["superclass"] = raw.superclass.to_numpy()
    ann["region"] = raw.superclass.map(_region).to_numpy()
    ann["flow"] = np.where(sc.isin(AFFERENT), "afferent",
                           np.where(sc.isin(EFFERENT), "efferent", "intrinsic"))
    ann["cell_class"] = raw["class"].to_numpy()
    ann["cell_sub_class"] = raw.subclass.to_numpy()
    ann["cell_type"] = raw.type.to_numpy()
    ann["hemibrain_type"] = raw.hemibrainType.to_numpy()
    ann["flywire_type"] = raw.flywireType.to_numpy()
    ann["manc_type"] = raw.mancType.to_numpy()
    ann["instance"] = raw.instance.to_numpy()

    # side: somaSide, then rootSide, then the _L/_R suffix of the instance name
    code = {"L": "left", "R": "right", "M": "center"}
    side = raw.somaSide.map(code)
    src = pd.Series(np.where(side.notna(), "soma", None), index=raw.index, dtype=object)
    fb = raw.rootSide.map(code)
    take = side.isna() & fb.notna()
    side[take] = fb[take]; src[take] = "root"
    suffix = raw.instance.fillna("").str.extract(r"_([LRM])$")[0].map(code)
    take = side.isna() & suffix.notna()
    side[take] = suffix[take]; src[take] = "instance"
    ann["side"] = side.to_numpy()
    ann["side_source"] = src.to_numpy()

    ann["neuromere"] = raw.somaNeuromere.to_numpy()
    ann["nerve"] = raw.exitNerve.to_numpy()
    ann["entry_nerve"] = raw.entryNerve.to_numpy()
    ann["hex1"] = raw.assignedOlHex1.to_numpy()
    ann["hex2"] = raw.assignedOlHex2.to_numpy()
    ann["status"] = raw.statusLabel.astype(object).to_numpy()

    # one transmitter per body; the NT file already has exactly one row per body
    nt = pf.read_feather(NEUROTRANSMITTERS,
                         columns=["body", "consensus_nt", "predicted_nt",
                                  "predicted_nt_confidence"])
    nt = nt.set_index("body").reindex(ann.root_id.to_numpy())
    top = nt.consensus_nt.to_numpy(dtype=object)
    top = np.where(pd.isna(top) | (top == "unclear"), "unknown", top)
    ann["top_nt"] = top
    ann["nt_predicted"] = nt.predicted_nt.to_numpy()
    ann["nt_confidence"] = nt.predicted_nt_confidence.to_numpy()
    ann["nt_sign"] = pd.Series(top).map(NT_SIGN).to_numpy(dtype=np.int8)

    if verbose:
        n_side = {k: int((ann.side_source == k).sum()) for k in ("soma", "root", "instance")}
        print(f"[malecns] {len(ann):,} annotated neurons; side from {n_side}; "
              f"{int(ann.side.isna().sum())} without side; "
              f"{int((ann.top_nt == 'unknown').sum())} without transmitter")
    return ann


def _build_edges(root_id: np.ndarray, sign_of: np.ndarray, min_weight: int,
                 verbose: bool) -> dict:
    """Stream the weights file, keep edges with weight >= min_weight between
    bodies in ``root_id``.  One 65,536-row batch is in memory at a time; the
    file is sorted by weight descending so the loop stops at the threshold."""
    pre_l, post_l, syn_l = [], [], []
    t0 = time.time()
    with pa.memory_map(WEIGHTS, "r") as src:
        rd = ipc.open_file(src)
        nb = rd.num_record_batches
        for i in range(nb):
            b = rd.get_batch(i)
            w = b.column("weight").to_numpy()
            if w.max() < min_weight:
                break
            keep = w >= min_weight
            a = b.column("body_pre").to_numpy()[keep]
            c = b.column("body_post").to_numpy()[keep]
            w = w[keep]
            keep = _member(a, root_id) & _member(c, root_id)
            pre_l.append(np.searchsorted(root_id, a[keep]).astype(np.int32))
            post_l.append(np.searchsorted(root_id, c[keep]).astype(np.int32))
            syn_l.append(w[keep].astype(np.int32))
            if verbose and i % 200 == 0:
                print(f"[malecns]   batch {i}/{nb}  min weight in batch {int(w.min()) if len(w) else '-'}"
                      f"  kept so far {sum(len(p) for p in pre_l):,}  {time.time()-t0:.0f}s",
                      flush=True)
    pre = np.concatenate(pre_l); del pre_l
    post = np.concatenate(post_l); del post_l
    syn = np.concatenate(syn_l); del syn_l
    sign = sign_of[pre].astype(np.int8)
    return {"pre": pre, "post": post, "syn": syn, "sign": sign}


def build_cache(min_weight: int = DEFAULT_MIN_WEIGHT, verbose: bool = True) -> None:
    ann = _build_annotations(verbose)
    root_id = ann.root_id.to_numpy()
    edges = _build_edges(root_id, ann.nt_sign.to_numpy(), min_weight, verbose)
    np.savez_compressed(cache_path(min_weight), root_id=root_id, **edges)
    ann.to_parquet(ANN_CACHE)
    if verbose:
        print(f"[malecns] {len(edges['pre']):,} edges at weight >= {min_weight} "
              f"-> {cache_path(min_weight)}")


def load(rebuild: bool = False, min_weight: int = DEFAULT_MIN_WEIGHT,
         verbose: bool = True) -> Connectome:
    path = cache_path(min_weight)
    if rebuild or not (os.path.exists(path) and os.path.exists(ANN_CACHE)):
        build_cache(min_weight=min_weight, verbose=verbose)
    z = np.load(path)
    ann = pd.read_parquet(ANN_CACHE)
    assert len(ann) == len(z["root_id"]), "annotation cache does not match edge cache"
    return Connectome(root_id=z["root_id"], ann=ann, pre=z["pre"], post=z["post"],
                      syn=z["syn"], sign=z["sign"])


def describe(cx: Connectome) -> str:
    """``Connectome.describe()`` plus the columns FlyWire does not have."""
    lines = [cx.describe(), "region:"]
    lines += [f"   {str(k):<20s} {v:>7,}"
              for k, v in cx.ann.region.value_counts(dropna=False).items()]
    lines.append("top_nt:")
    lines += [f"   {str(k):<20s} {v:>7,}"
              for k, v in cx.ann.top_nt.value_counts(dropna=False).items()]
    mn = cx.ann[cx.ann.super_class == "vnc_motor"]
    lines.append("vnc_motor by neuromere x side:")
    tab = pd.crosstab(mn.neuromere.fillna("NA"), mn.side.fillna("NA"))
    lines += ["   " + line for line in tab.to_string().splitlines()]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    mw = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MIN_WEIGHT
    cx = load(rebuild=True, min_weight=mw)
    print(describe(cx))
