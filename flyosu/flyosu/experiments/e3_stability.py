"""
Spectral radius of the blank-field Jacobian across control seeds.

Experiment 2 found the real connectome at radius 2.28 against 0.72 for three
rewired networks.  This measures more seeds in every control family, plus the
composition of the leading mode, so the number has an error bar and a location.

    N_SEEDS=6 python -m experiments.e3_stability
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import model as M  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PATH = os.path.join(RESULTS, "e3_stability.json")
FAMILIES = [("rewired topology", "shuffle_seed"), ("shuffled retinotopy", "retino_seed"),
            ("shuffled channel labels", "channel_seed")]


def leading_mode(fly, r):
    net = fly.net
    x = net.Wt @ r
    z = net.slope * (x - net.mu) / net.sigma + net.offset
    phi = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
    g = phi * (1 - phi) * net.slope / net.sigma
    g[net.is_input] = 0.0
    J = sp.diags(g.astype(np.float64)) @ net.Wt.astype(np.float64)
    vals, vecs = spl.eigs(J, k=1, which="LM", maxiter=5000)
    v = np.abs(vecs[:, 0]); v /= v.sum()
    sc = fly.class_of("super_class")
    mass = {str(c): float(v[sc == c].sum()) for c in np.unique(sc.astype(str))}
    top = np.argsort(-v)[:200]
    types = fly.cx.ann.iloc[fly.node_ids[top]].cell_type.value_counts().head(5)
    return {"mass_by_superclass": mass, "top_cell_types": {str(k): int(c) for k, c in types.items()},
            "participation": float(1.0 / (v ** 2).sum() / len(v))}


def measure(label, kw):
    t0 = time.time()
    fly = M.build(regime="play", **kw)
    r = fly.settle()
    st = fly.stability(r0=r)
    st.update(leading_mode(fly, r))
    st["label"] = label
    st["seconds"] = round(time.time() - t0, 1)
    print(f"  {label:<28s} radius {st['spectral_radius']:.2f}  Re {st['max_real']:+.2f}  "
          f"fixed point {st['fixed_point']}  leading mode in optic {st['mass_by_superclass'].get('optic', 0):.2f}"
          f"  ({st['seconds']:.0f}s)", flush=True)
    return st


def main():
    n = int(os.environ.get("N_SEEDS", 6))
    results = {"runs": []}
    if os.path.exists(PATH):
        with open(PATH) as fh:
            results = json.load(fh)
    done = {r["label"] for r in results["runs"]}
    plan = [("real connectome", "real", {})]
    for fam, kwarg in FAMILIES:
        for s in range(1, n + 1):
            plan.append((f"{fam} #{s}", fam, {kwarg: s}))
    for label, fam, kw in plan:
        if label in done:
            continue
        st = measure(label, kw)
        st["family"] = fam
        results["runs"].append(st)
        with open(PATH, "w") as fh:
            json.dump(results, fh, indent=1)
    print("\n--- spectral radius by family ---")
    for fam in ["real"] + [f for f, _ in FAMILIES]:
        v = np.array([r["spectral_radius"] for r in results["runs"] if r["family"] == fam])
        fp = sum(r["fixed_point"] for r in results["runs"] if r["family"] == fam)
        if len(v):
            print(f"  {fam:<26s} {v.mean():.2f} +- {v.std():.2f}  (n={len(v)}, min {v.min():.2f}, "
                  f"max {v.max():.2f}, fixed points {fp}/{len(v)})")


if __name__ == "__main__":
    main()
