"""
Extract the visual -> descending pathway from the whole-brain connectome.

Simulating all 139,262 neurons is possible but wasteful: most of the brain is
olfactory, mechanosensory, gustatory or motor circuitry that a photoreceptor
stimulus never meaningfully reaches.  We therefore rank neurons by how strongly
they sit *on the path* between the retina and the descending neurons, using a
linear signal-flow cascade on the magnitude graph.

    forward  F  =  sum_k  alpha^k * (|W|^T)^k  s      s = photoreceptors
    backward B  =  sum_k  alpha^k * (|W|)^k    t      t = descending neurons
    score       =  sqrt(F * B)

``F[i]`` measures how much retinal signal reaches neuron i; ``B[i]`` how much of
neuron i's output reaches a descending neuron.  Their product is large only for
neurons that are both driven by the eye and able to influence the motor output,
which is exactly the pathway we want.  Photoreceptors and descending neurons are
always retained.

The magnitude graph ignores edge sign on purpose: an inhibitory neuron in the
pathway is as much part of the circuit as an excitatory one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from .connectome import Connectome
from .sim import extract, normalise_input


@dataclass
class Pathway:
    node_ids: np.ndarray      # (M,) connectome indices, sorted
    score: np.ndarray         # (M,) pathway score of each kept neuron
    forward: np.ndarray       # (N,) full-brain forward influence
    backward: np.ndarray      # (N,) full-brain backward influence
    n_hops: int
    alpha: float

    def composition(self, cx: Connectome, top: int = 12) -> str:
        a = cx.ann.iloc[self.node_ids]
        lines = [f"subgraph: {len(self.node_ids):,} neurons"]
        lines.append("  super_class:")
        for k, v in a.super_class.value_counts(dropna=False).items():
            lines.append(f"    {str(k):<20s} {v:>6,}")
        lines.append("  top cell types:")
        for k, v in a.cell_type.value_counts(dropna=False).head(top).items():
            lines.append(f"    {str(k):<20s} {v:>6,}")
        return "\n".join(lines)


def _cascade(A: sp.csr_matrix, seed: np.ndarray, hops: int,
             alpha: float) -> np.ndarray:
    """sum_k alpha^k A^k seed, normalised at each hop to avoid under/overflow."""
    x = seed.astype(np.float32)
    x /= max(x.sum(), 1e-12)
    acc = x.copy()
    for _ in range(hops):
        x = A @ x
        s = x.sum()
        if s <= 0:
            break
        x = x / s * np.float32(alpha)
        acc += x
    return acc


def build(cx: Connectome, source: np.ndarray, sink: np.ndarray,
          n_keep: int = 20000, hops: int = 8, alpha: float = 1.0) -> Pathway:
    """Rank and select the pathway between ``source`` and ``sink`` neurons."""
    pre, post, w, _ = extract(cx, None, 1.0)
    w = np.abs(normalise_input(w, post, cx.n_neurons, 1.0))

    # A_fwd[j, i] = weight of edge i -> j   (propagates activity downstream)
    A_fwd = sp.csr_matrix((w, (post, pre)), shape=(cx.n_neurons,) * 2,
                          dtype=np.float32)
    A_bwd = sp.csr_matrix((w, (pre, post)), shape=(cx.n_neurons,) * 2,
                          dtype=np.float32)

    s = np.zeros(cx.n_neurons, np.float32); s[source] = 1.0
    t = np.zeros(cx.n_neurons, np.float32); t[sink] = 1.0

    F = _cascade(A_fwd, s, hops, alpha)
    B = _cascade(A_bwd, t, hops, alpha)
    score = np.sqrt(np.maximum(F, 0) * np.maximum(B, 0))

    must = np.union1d(np.asarray(source), np.asarray(sink))
    order = np.argsort(-score)
    keep = np.union1d(must, order[:max(n_keep - len(must), 0)])
    return Pathway(node_ids=keep.astype(np.int32), score=score[keep],
                   forward=F, backward=B, n_hops=hops, alpha=alpha)


def visual_to_descending(cx: Connectome, retina_idx: np.ndarray,
                         n_keep: int = 20000, **kw) -> Pathway:
    """Convenience wrapper: retina -> descending neurons."""
    return build(cx, retina_idx, cx.where(super_class="descending"),
                 n_keep=n_keep, **kw)


if __name__ == "__main__":
    from . import connectome as C, retina as R

    cx = C.load()
    ret = R.build(cx)
    for n in (5000, 20000, 50000):
        pw = visual_to_descending(cx, ret.idx, n_keep=n)
        a = cx.ann.iloc[pw.node_ids]
        print(f"\nn_keep={n}: kept {len(pw.node_ids):,}  "
              f"DN kept {(a.super_class == 'descending').sum()}/1303  "
              f"VPN kept {(a.super_class == 'visual_projection').sum()}/8038  "
              f"central {(a.super_class == 'central').sum()}")
