"""
FlyWire v783 whole-brain connectome loader.

Data sources (both fetched from public GitHub mirrors, see data/SOURCES.md):
  * Connectivity_783.parquet  - 15,091,983 signed, weighted synaptic edges
                                (Shiu et al. 2024 mirror of the FlyWire v783 release)
  * neuron_annotations.tsv    - 139,248 neuron annotations from Schlegel et al. 2024
                                (super_class / cell_type / side / soma position / NT)

The cache produced here is a compact, index-aligned representation:

    root_id[i]          int64    FlyWire segment id of neuron i
    ann                 DataFrame  annotations, row i == neuron i
    pre, post           int32    edge endpoints as neuron indices
    syn                 int32    synapse count of the edge
    sign                int8     +1 excitatory (ACh), -1 inhibitory (GABA/Glu)

Neuron indices are stable: they are assigned by sorting root_id ascending over
the union of (annotated neurons) and (neurons appearing in the edge list).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
CACHE = os.path.join(DATA_DIR, "flywire783_cache.npz")
ANN_CACHE = os.path.join(DATA_DIR, "flywire783_ann.parquet")

PARQUET = os.path.join(DATA_DIR, "Connectivity_783.parquet")
ANNOTATIONS = os.path.join(DATA_DIR, "neuron_annotations.tsv")

ANN_COLS = [
    "root_id", "pos_x", "pos_y", "pos_z", "soma_x", "soma_y", "soma_z",
    "flow", "super_class", "cell_class", "cell_sub_class", "supertype",
    "cell_type", "hemibrain_type", "top_nt", "side", "nerve",
]


@dataclass
class Connectome:
    """Index-aligned whole-brain connectome."""

    root_id: np.ndarray          # (N,) int64
    ann: pd.DataFrame            # (N, ...) row i describes neuron i
    pre: np.ndarray              # (E,) int32
    post: np.ndarray             # (E,) int32
    syn: np.ndarray              # (E,) int32
    sign: np.ndarray             # (E,) int8

    @property
    def n_neurons(self) -> int:
        return self.root_id.shape[0]

    @property
    def n_edges(self) -> int:
        return self.pre.shape[0]

    # -- selection helpers -------------------------------------------------

    def where(self, **kw) -> np.ndarray:
        """Boolean-AND selection over annotation columns.

        Values may be a scalar or a list/tuple of accepted values.
        ``cx.where(super_class="descending", side="left")``
        """
        mask = np.ones(self.n_neurons, dtype=bool)
        for col, val in kw.items():
            series = self.ann[col]
            if isinstance(val, (list, tuple, set, np.ndarray)):
                mask &= series.isin(list(val)).to_numpy()
            else:
                mask &= (series == val).to_numpy()
        return np.flatnonzero(mask)

    def signed_matrix(self, weight: str = "syn") -> sp.csr_matrix:
        """Sparse (N, N) matrix ``M[pre, post]`` of signed synaptic weight."""
        if weight == "syn":
            data = self.syn.astype(np.float32) * self.sign.astype(np.float32)
        elif weight == "count":
            data = self.syn.astype(np.float32)
        else:
            raise ValueError(weight)
        n = self.n_neurons
        return sp.csr_matrix((data, (self.pre, self.post)), shape=(n, n))

    def describe(self) -> str:
        sc = self.ann.super_class.value_counts(dropna=False)
        exc = int((self.sign > 0).sum())
        lines = [
            f"neurons : {self.n_neurons:,}",
            f"edges   : {self.n_edges:,}  ({exc/self.n_edges:.1%} excitatory)",
            f"synapses: {int(self.syn.sum()):,}",
            "super_class:",
        ]
        lines += [f"   {str(k):<20s} {v:>7,}" for k, v in sc.items()]
        return "\n".join(lines)


def _build_cache(verbose: bool = True) -> None:
    ann = pd.read_csv(ANNOTATIONS, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann = ann.drop_duplicates(subset="root_id", keep="first")

    pf = pq.ParquetFile(PARQUET)
    cols = ["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"]

    # pass 1 - collect the set of root ids that actually appear in the edge list
    seen: list[np.ndarray] = []
    for batch in pf.iter_batches(batch_size=2_000_000,
                                 columns=["Presynaptic_ID", "Postsynaptic_ID"]):
        a = batch.column(0).to_numpy(zero_copy_only=False)
        b = batch.column(1).to_numpy(zero_copy_only=False)
        seen.append(np.unique(np.concatenate([a, b])))
    edge_ids = np.unique(np.concatenate(seen))
    del seen

    root_id = np.union1d(ann.root_id.to_numpy(dtype=np.int64), edge_ids)
    if verbose:
        print(f"[connectome] {len(root_id):,} neurons "
              f"({len(edge_ids):,} in edge list, {len(ann):,} annotated)")

    # align annotations to the index (neurons without annotations get NaN rows)
    ann = ann.set_index("root_id").reindex(root_id)
    ann.index.name = "root_id"
    ann = ann.reset_index()

    # pass 2 - map edges onto indices
    pre_l, post_l, syn_l, sign_l = [], [], [], []
    for batch in pf.iter_batches(batch_size=2_000_000, columns=cols):
        a = batch.column(0).to_numpy(zero_copy_only=False)
        b = batch.column(1).to_numpy(zero_copy_only=False)
        w = batch.column(2).to_numpy(zero_copy_only=False)
        e = batch.column(3).to_numpy(zero_copy_only=False)
        pre_l.append(np.searchsorted(root_id, a).astype(np.int32))
        post_l.append(np.searchsorted(root_id, b).astype(np.int32))
        syn_l.append(w.astype(np.int32))
        sign_l.append(np.sign(e).astype(np.int8))

    pre = np.concatenate(pre_l);   del pre_l
    post = np.concatenate(post_l); del post_l
    syn = np.concatenate(syn_l);   del syn_l
    sign = np.concatenate(sign_l); del sign_l

    np.savez_compressed(CACHE, root_id=root_id, pre=pre, post=post,
                        syn=syn, sign=sign)
    ann.to_parquet(ANN_CACHE)
    if verbose:
        print(f"[connectome] cached -> {CACHE}")


def load(rebuild: bool = False, verbose: bool = True) -> Connectome:
    if rebuild or not (os.path.exists(CACHE) and os.path.exists(ANN_CACHE)):
        _build_cache(verbose=verbose)
    z = np.load(CACHE)
    ann = pd.read_parquet(ANN_CACHE)
    return Connectome(root_id=z["root_id"], ann=ann, pre=z["pre"],
                      post=z["post"], syn=z["syn"], sign=z["sign"])


if __name__ == "__main__":
    cx = load(rebuild=True)
    print(cx.describe())
