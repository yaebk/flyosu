"""
Motor readout: descending neurons -> four actuator channels.

The 1,303 FlyWire descending neurons are the brain's only substantial output to
the ventral nerve cord, and hence to the legs.  osu!mania needs four keys, so we
need four groups.

The grouping must not look at the stimulus, or the experiment that follows would
be circular: if you cluster descending neurons by how they respond to the four
lanes, of course the four lanes separate.  So the split uses connectivity and
anatomy only:

  * ``side``    each hemisphere's descending population, from the FlyWire
                ``side`` annotation.  This is the fly's own lateralisation.
  * ``cluster`` within a hemisphere, k-means (k=2) on the descending neurons'
                *input* weight vectors, reduced by truncated SVD.  Two
                descending neurons land in the same group when the rest of the
                brain talks to them in the same way.

That gives (left|right) x (cluster 0|1) = four channels.  Which channel ends up
driving which key is decided afterwards, by measuring the response matrix -- it
is a result, not an assumption.

The labels T1L / T2L / T1R / T2R are kept from the project's original framing.
They are nicknames for the four groups, not claims about which leg neuromere
each group innervates: FlyWire covers the brain only, so the descending
neurons' ventral-nerve-cord targets are not in this dataset.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD

from .connectome import Connectome

KEYS = ("D", "F", "J", "K")


@dataclass
class MotorReadout:
    """Four groups of descending neurons, plus the pooling used to read them."""

    groups: list[np.ndarray]     # 4 arrays of network-local neuron indices
    names: list[str]             # e.g. ['T2L', 'T1L', 'T1R', 'T2R']
    dn_local: np.ndarray         # all descending neurons, network-local
    label_of: np.ndarray         # (len(dn_local),) group index 0..3

    def activity(self, r: np.ndarray) -> np.ndarray:
        """Mean activity of each channel, in the order of ``names``."""
        return np.array([r[g].mean() if len(g) else 0.0 for g in self.groups],
                        dtype=np.float32)

    def sizes(self) -> list[int]:
        return [len(g) for g in self.groups]

    def __repr__(self) -> str:
        return ("MotorReadout(" +
                ", ".join(f"{n}:{len(g)}" for n, g in zip(self.names, self.groups))
                + ")")


def build(cx: Connectome, node_ids: np.ndarray, Wt: sp.csr_matrix,
          n_components: int = 32, seed: int = 0) -> MotorReadout:
    """Split descending neurons into four connectivity-defined channels.

    ``node_ids`` maps network index -> connectome index; ``Wt`` is the
    network's postsynaptic-major weight matrix (row = postsynaptic neuron).
    """
    lut = np.full(cx.n_neurons, -1, dtype=np.int32)
    lut[node_ids] = np.arange(len(node_ids), dtype=np.int32)

    dn_global = cx.where(super_class="descending")
    dn_local = lut[dn_global]
    ok = dn_local >= 0
    dn_local, dn_global = dn_local[ok], dn_global[ok]
    side = cx.ann.iloc[dn_global].side.to_numpy()

    # input connectivity of each descending neuron, magnitude only
    X = abs(Wt[dn_local])
    k = min(n_components, min(X.shape) - 1)
    Z = TruncatedSVD(n_components=k, random_state=seed).fit_transform(X)
    Z /= (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)

    label = np.zeros(len(dn_local), dtype=np.int8)
    for s, base in (("left", 0), ("right", 2)):
        m = side == s
        if m.sum() < 2:
            continue
        km = KMeans(n_clusters=2, n_init=10, random_state=seed).fit(Z[m])
        # deterministic cluster order: larger cluster first
        lab = km.labels_
        if (lab == 0).sum() < (lab == 1).sum():
            lab = 1 - lab
        label[m] = base + lab

    groups = [dn_local[label == i] for i in range(4)]
    names = ["T2L", "T1L", "T1R", "T2R"]
    return MotorReadout(groups=groups, names=names, dn_local=dn_local,
                        label_of=label)


def describe(readout: MotorReadout, cx: Connectome,
             node_ids: np.ndarray, top: int = 6) -> str:
    """What cell types dominate each channel."""
    lines = []
    for name, g in zip(readout.names, readout.groups):
        types = cx.ann.iloc[node_ids[g]].cell_type.value_counts().head(top)
        joined = ", ".join(f"{t}({c})" for t, c in types.items())
        lines.append(f"  {name}  n={len(g):<5d} {joined}")
    return "\n".join(lines)


def build_motor(cx: Connectome, node_ids: np.ndarray, Wt: sp.csr_matrix | None = None,
                neuromeres: tuple = ("T1", "T2")) -> MotorReadout:
    """Four channels from *real* leg motor neurons (male CNS only).

    The male CNS reconstruction continues into the ventral nerve cord, so the
    four keys can be four actual motor pools: the leg motor neurons of the
    first two thoracic neuromeres, split by side.  Nothing is clustered and
    nothing is inferred -- ``super_class == "vnc_motor"``, ``neuromere`` and
    ``side`` are annotations.  T1L / T2L / T1R / T2R are no longer nicknames.

    Grouping is by the *motor neuron's* side, not by the side of the
    descending neurons that drive it: only 42% of DN -> leg-MN synapses are
    ipsilateral to the DN soma (docs/MALECNS.md), so grouping DNs by their own
    side, as ``build`` does for FlyWire, would not lateralise the output.
    ``Wt`` is accepted for signature compatibility and unused.
    """
    lut = np.full(cx.n_neurons, -1, dtype=np.int32)
    lut[node_ids] = np.arange(len(node_ids), dtype=np.int32)
    ann = cx.ann
    names, groups = [], []
    for s, tag in (("left", "L"), ("right", "R")):
        for nm in neuromeres:
            g = cx.where(super_class="vnc_motor", neuromere=nm, side=s)
            g = lut[g]
            groups.append(np.sort(g[g >= 0]).astype(np.int32))
            names.append(f"{nm}{tag}")
    # channel order matches ``build``: (left | right) x (pool 0 | pool 1)
    order = [1, 0, 2, 3] if len(neuromeres) == 2 else list(range(len(groups)))
    groups = [groups[i] for i in order]
    names = [names[i] for i in order]
    dn_local = np.concatenate(groups)
    label = np.zeros(len(dn_local), np.int8)
    pos = {v: i for i, v in enumerate(dn_local)}
    for gi, g in enumerate(groups):
        for v in g:
            label[pos[v]] = gi
    return MotorReadout(groups=groups, names=names, dn_local=dn_local, label_of=label)
