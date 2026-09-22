"""
Sanity checks for the male CNS loader, pinning the numbers docs/MALECNS.md quotes.

    python -m tests.test_malecns

Needs the cache (python -m flyosu.malecns builds it in ~20 s, peak ~1 GB).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import malecns as MC  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def test_graph(cx):
    print("graph")
    check("neuron count is the 166,700 bodies with a superclass", cx.n_neurons == 166_700,
          f"{cx.n_neurons:,}")
    check("edge count at weight >= 2", cx.n_edges == 15_283_237, f"{cx.n_edges:,}")
    check("synapse count ~113.9M", 113e6 < cx.syn.sum() < 115e6, f"{cx.syn.sum():,}")
    check("no edge below the threshold", cx.syn.min() >= MC.DEFAULT_MIN_WEIGHT)
    check("signs are +/-1 only", set(np.unique(cx.sign)) <= {-1, 1})
    check("annotations are index-aligned", len(cx.ann) == cx.n_neurons)
    check("root ids sorted and unique",
          np.all(np.diff(cx.root_id) > 0))
    check("annotation root_id matches the index",
          np.array_equal(cx.ann.root_id.to_numpy(), cx.root_id))
    check("edge endpoints in range",
          cx.pre.max() < cx.n_neurons and cx.post.max() < cx.n_neurons)
    key = cx.pre.astype(np.int64) * cx.n_neurons + cx.post
    check("no duplicate (pre, post) pairs", len(np.unique(key)) == len(key))
    # sign is a property of the presynaptic body, so it must not vary per edge
    s = pd.Series(cx.sign).groupby(cx.pre).nunique().max()
    check("sign is constant per presynaptic neuron", s == 1)
    nt = cx.ann.top_nt.to_numpy()[cx.pre]
    check("ACh edges are +1", (cx.sign[nt == "acetylcholine"] == 1).all())
    check("GABA/Glu/histamine edges are -1",
          (cx.sign[np.isin(nt, ["gaba", "glutamate", "histamine"])] == -1).all())
    exc = (cx.sign > 0).mean()
    check("excitatory fraction ~62%", 0.58 < exc < 0.66, f"{exc:.1%}")


def test_annotations(cx):
    print("annotations")
    a = cx.ann
    check("no unmapped super_class", a.super_class.notna().all())
    check("original superclass kept", "superclass" in a.columns)
    check("1,314 descending neurons", len(cx.where(super_class="descending")) == 1314)
    check("708 VNC motor neurons", len(cx.where(super_class="vnc_motor")) == 708)
    check("107 brain motor neurons stay 'motor'", len(cx.where(super_class="motor")) == 107)
    check("89,403 optic neurons", len(cx.where(super_class="optic")) == 89_403)
    check("3,377 R1-R6", len(cx.where(cell_type="R1-R6")) == 3377)
    check("6,091 photoreceptors are sensory/visual",
          len(cx.where(super_class="sensory", cell_class="visual")) == 6091)
    check("side vocabulary matches FlyWire",
          set(a.side.dropna().unique()) <= {"left", "right", "center"})
    check("left somata at high x, right at low x (mirror of FAFB)",
          a.pos_x[a.side == "left"].mean() > a.pos_x[a.side == "right"].mean())
    check("hex lattice present on 23,720 columnar neurons", int(a.hex1.notna().sum()) == 23_720)
    check("top_nt vocabulary", set(a.top_nt.unique()) <= set(MC.NT_SIGN))
    check("photoreceptors are histaminergic",
          (a.top_nt[a.cell_class == "visual"] == "histamine").all())


def test_photoreceptors(cx):
    print("photoreceptors")
    a = cx.ann
    r16 = a[a.cell_type == "R1-R6"]
    check("R1-R6 have a side (from rootSide)", r16.side.notna().all(),
          r16.side.value_counts().to_dict().__repr__())
    check("both eyes have R1-R6", set(r16.side.unique()) == {"left", "right"})
    check("R1-R6 have (almost) no soma position -- retina.py cannot be reused as is",
          int(r16.pos_x.notna().sum()) < 50, f"{int(r16.pos_x.notna().sum())} with soma")
    # the route to a retinotopy: R1-R6 -> L1/L2 targets that carry a hex coordinate
    idx = r16.index.to_numpy()
    m = np.isin(cx.pre, idx)
    tgt = cx.post[m]
    check("R1-R6 output goes to the lamina",
          a.cell_type.iloc[tgt].isin(["L1", "L2", "L3"]).mean() > 0.8)
    has_hex = a.hex1.notna().to_numpy()[tgt]
    n_with = len(np.unique(cx.pre[m][has_hex]))
    check("nearly every R1-R6 has a hex-carrying target", n_with >= 3300, f"{n_with}")


def test_motor(cx):
    print("descending -> motor")
    a = cx.ann
    mn = cx.where(super_class="vnc_motor")
    dn = cx.where(super_class="descending")
    side = a.side.iloc[mn]
    check("every motor neuron has a side", side.notna().all())
    check("both sides present, balanced",
          abs(int((side == "left").sum()) - int((side == "right").sum())) < 10,
          side.value_counts().to_dict().__repr__())
    leg = a.neuromere.iloc[mn].isin(["T1", "T2", "T3"])
    check("500 leg motor neurons (T1-T3)", int(leg.sum()) == 500, f"{int(leg.sum())}")
    cells = pd.crosstab(a.neuromere.iloc[mn][leg], side[leg])
    check("every (leg neuromere, side) cell has >= 70 motor neurons",
          (cells.to_numpy() >= 70).all(), cells.to_dict().__repr__())
    m = np.isin(cx.pre, dn) & np.isin(cx.post, mn)
    check("DN -> MN edges exist in bulk", 12_000 < m.sum() < 15_000, f"{int(m.sum()):,} edges")
    check("DN -> MN synapses ~225k", 200_000 < cx.syn[m].sum() < 250_000,
          f"{int(cx.syn[m].sum()):,}")
    hit = np.unique(cx.post[m])
    check("most motor neurons get direct DN input", len(hit) > 650, f"{len(hit)}/{len(mn)}")
    # 3,388 edges out of 708 cells vs 13,448 DN->MN edges in: the readout end
    out = int(np.isin(cx.pre, mn).sum())
    check("motor neurons are the terminal readout: little output", out < 5_000,
          f"{out:,} edges out")


def main():
    if not os.path.exists(MC.cache_path(MC.DEFAULT_MIN_WEIGHT)):
        print("cache missing; building (needs data/malecns/*.feather)")
    cx = MC.load(verbose=False)
    test_graph(cx)
    test_annotations(cx)
    test_photoreceptors(cx)
    test_motor(cx)
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
