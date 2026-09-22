"""
Sanity checks that catch the ways this pipeline has silently broken before.

    python -m tests.test_pipeline
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import connectome as C, model as M, retina as R, sim as S  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def test_connectome(cx):
    print("connectome")
    check("neuron count matches the v783 release", 139_000 < cx.n_neurons < 140_000,
          f"{cx.n_neurons:,}")
    check("edge count matches", cx.n_edges == 15_091_983, f"{cx.n_edges:,}")
    check("synapse count ~54.5M", 54e6 < cx.syn.sum() < 55e6, f"{cx.syn.sum():,}")
    check("signs are +/-1 only", set(np.unique(cx.sign)) <= {-1, 1})
    check("annotations are index-aligned", len(cx.ann) == cx.n_neurons)
    check("1,303 descending neurons", len(cx.where(super_class="descending")) == 1303)
    check("edge endpoints in range",
          cx.pre.max() < cx.n_neurons and cx.post.max() < cx.n_neurons)


def test_retina(cx):
    print("retina")
    ret = R.build(cx)
    check("R1-6 only", set(np.unique(ret.ptype)) == {"R1-6"}, f"{len(ret):,} cells")
    check("both eyes present", set(np.unique(ret.side)) == {"left", "right"})

    # optical axes must agree with the stored angles -- they disagreed once,
    # which silently made whole regions of the visual field unstimulable
    v = R.unit_vector(ret.azimuth, ret.elevation)
    check("optical axes match stored angles",
          float(np.abs(v - ret.direction).max()) < 1e-4)

    # every part of the field a stimulus can land on must actually reach cells
    counts = [int((ret.drive([(a, 0.0, 1.0)], sigma_deg=10) > 0.05).sum())
              for a in range(-140, 141, 20)]
    check("all azimuths stimulate photoreceptors", min(counts) > 50,
          f"min {min(counts)} cells")

    left = ret.side == "left"
    dl = ret.drive([(-70.0, 0.0, 1.0)], sigma_deg=10)
    dr = ret.drive([(70.0, 0.0, 1.0)], sigma_deg=10)
    check("left field drives the left eye", dl[left].sum() > 20 * dl[~left].sum())
    check("right field drives the right eye", dr[~left].sum() > 20 * dr[left].sum())
    return ret


def test_normalisation(cx):
    print("weights")
    pre, post, w, node_ids = S.extract(cx, np.arange(2000, dtype=np.int32), 1.0)
    wn = S.normalise_input(w, post, len(node_ids), 1.0)
    tot = np.bincount(post, weights=np.abs(wn), minlength=len(node_ids))
    live = tot > 0
    check("input budgets sum to 1", np.allclose(tot[live], 1.0, atol=1e-4))
    check("signs preserved", np.array_equal(np.sign(w), np.sign(wn)))
    # relative weights within a neuron's input are what the connectome measures
    j = post[0]
    m = post == j
    check("relative input weights preserved",
          np.allclose(w[m] / np.abs(w[m]).sum(), wn[m], atol=1e-5))


def test_model():
    print("model")
    fly = M.build()
    check("network is the pathway subgraph", 15000 < fly.net.n < 25000,
          f"{fly.net.n:,} neurons")
    check("all descending neurons kept", len(fly.dn) == 1303)
    check("four channels", len(fly.readout.groups) == 4,
          str(fly.readout.sizes()))
    check("channels partition the descending neurons",
          sum(fly.readout.sizes()) == 1303)

    r = fly.look([(-60.0, -25.0, 1.0)])
    check("activity is finite and bounded",
          np.isfinite(r).all() and 0 <= r.min() and r.max() <= 1.0)
    check("network is not silent", float(r[fly.dn].mean()) > 0.01,
          f"DN mean {r[fly.dn].mean():.3f}")
    check("network is not saturated", float(r[fly.dn].mean()) < 0.95)

    # determinism: same stimulus, same answer
    r2 = fly.look([(-60.0, -25.0, 1.0)])
    check("deterministic", np.array_equal(r, r2))

    # different lanes must produce different descending patterns
    a = fly.look([(-60.0, -25.0, 1.0)])[fly.dn]
    b = fly.look([(60.0, -25.0, 1.0)])[fly.dn]
    check("opposite lanes differ at the output",
          float(np.abs(a - b).mean()) > 1e-3, f"mean |diff| {np.abs(a - b).mean():.4f}")
    return fly


def test_controls():
    print("controls")
    real = M.build()
    ctrl = M.build(shuffle_seed=1)
    check("control has the same neuron count", ctrl.net.n == real.net.n)
    # Channels are re-derived from each network's own connectivity, so the
    # control's group sizes are close but not identical -- that is the point:
    # the *procedure* is matched, not the outcome.
    sz, rs = ctrl.readout.sizes(), real.readout.sizes()
    check("control channels still partition the descending neurons",
          sum(sz) == 1303 and len(sz) == 4, str(sz))
    check("control channel sizes are comparable",
          all(abs(a - b) / b < 0.25 for a, b in zip(sz, rs)),
          f"{sz} vs {rs}")

    # Rewiring permutes presynaptic endpoints, so the degree sequence is
    # preserved except where a rewired edge lands on a pair that already
    # exists and the two merge.  That costs ~1.3% of edges.
    lost = (real.net.n_edges - ctrl.net.n_edges) / real.net.n_edges
    check("rewiring merges few edges", lost < 0.02, f"{lost:.2%} merged")
    din = np.bincount(real.net.Wt.indices, minlength=real.net.n)
    dic = np.bincount(ctrl.net.Wt.indices, minlength=ctrl.net.n)
    dev = float(np.abs(np.sort(din) - np.sort(dic)).sum()) / din.sum()
    check("rewiring preserves the out-degree sequence", dev < 0.02, f"{dev:.2%} off")

    ch = M.build(channel_seed=1)
    check("channel-shuffle keeps group sizes",
          ch.readout.sizes() == real.readout.sizes())
    check("channel-shuffle actually changed the groups",
          not np.array_equal(np.sort(ch.readout.groups[0]),
                             np.sort(real.readout.groups[0])))


def main():
    cx = C.load()
    test_connectome(cx)
    test_retina(cx)
    test_normalisation(cx)
    test_model()
    test_controls()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
