"""
Assembles the pieces into one runnable fly: connectome -> retina -> pathway
subgraph -> calibrated rate network -> four motor channels.

    fly = build()
    r   = fly.look([(az, el, 1.0)])       # settle the network on a stimulus
    act = fly.channels(r)                 # four actuator activations

Calibrated models are cached under ``data/models/`` keyed by their settings, so
rebuilding is cheap.
"""

from __future__ import annotations

import hashlib
import os
import pickle
from dataclasses import dataclass, field

import numpy as np

from . import connectome as C
from . import outputs as O
from . import retina as R
from . import sim as S
from . import subgraph as SG

MODEL_DIR = os.path.join(C.DATA_DIR, "models")

# the training ensemble the operating points are calibrated on: a coarse sweep
# of single bright points over the frontal-to-lateral visual field
CAL_AZ = np.linspace(-110.0, 110.0, 15)
CAL_EL = np.array([-30.0, -10.0, 10.0, 30.0])


@dataclass
class Fly:
    cx: C.Connectome
    ret: R.Retina
    net: S.RateNetwork
    node_ids: np.ndarray
    readout: O.MotorReadout
    ph_local: np.ndarray
    meta: dict = field(default_factory=dict)

    # -- stimulus / simulation --------------------------------------------

    def stimulus(self, targets, sigma_deg: float = 10.0) -> np.ndarray:
        e = np.zeros(self.net.n, dtype=np.float32)
        if targets:
            e[self.ph_local] = self.ret.drive(targets, sigma_deg=sigma_deg)
        return e

    def look(self, targets, sigma_deg: float = 10.0, duration_ms: float = 300.0,
             r0: np.ndarray | None = None) -> np.ndarray:
        r, _ = self.net.run(self.stimulus(targets, sigma_deg),
                            duration_ms=duration_ms, r0=r0)
        return r

    def channels(self, r: np.ndarray) -> np.ndarray:
        return self.readout.activity(r)

    # -- introspection -----------------------------------------------------

    @property
    def dn(self) -> np.ndarray:
        return self.readout.dn_local

    def class_of(self, key: str) -> np.ndarray:
        return self.cx.ann.iloc[self.node_ids][key].to_numpy()

    def summary(self) -> str:
        sc = self.class_of("super_class")
        lines = [f"network   {self.net.n:,} neurons  {self.net.n_edges:,} edges",
                 f"retina    {len(self.ret):,} R1-6 photoreceptors",
                 f"channels  " + "  ".join(
                     f"{n}={len(g)}" for n, g in
                     zip(self.readout.names, self.readout.groups))]
        lines.append("composition:")
        import collections
        for k, v in collections.Counter(sc.tolist()).most_common():
            lines.append(f"   {str(k):<20s} {v:>6,}")
        return "\n".join(lines)


def _key(**kw) -> str:
    return hashlib.sha1(repr(sorted(kw.items())).encode()).hexdigest()[:16]


def build(n_keep: int = 20000, slope: float = 2.5, offset: float = -1.2,
          tau: float = 20.0, sigma_deg: float = 10.0, rounds: int = 8,
          shuffle_seed: int | None = None, retino_seed: int | None = None,
          channel_seed: int | None = None, cache: bool = True,
          verbose: bool = False) -> Fly:
    """Build (and calibrate) a fly.

    Three independent controls, each isolating one thing the connectome
    supplies.  All keep the neuron count, the degree sequence, the weight and
    sign multiset, the calibration procedure and the channel-definition
    procedure.  Two caveats worth stating: rewiring merges ~1.3% of edges that
    land on an already-existing pair, and channel sizes are re-derived from
    each network's own connectivity, so they land within ~10% of the real
    network's rather than matching exactly.  The *procedure* is matched, not
    the outcome -- matching the outcome would mean importing the real
    network's structure into the control.

    ``shuffle_seed``  rewire the graph at random (degree-preserving).  Tests
                      whether the *topology* matters.
    ``retino_seed``   keep the graph, permute which photoreceptor sees which
                      part of the visual field.  Tests whether the anatomical
                      *retinotopy* matters.
    ``channel_seed``  keep everything, assign descending neurons to the four
                      channels at random (same group sizes).  Tests whether the
                      anatomical *grouping of the output* matters.
    """
    cx = C.load()
    ret = R.build(cx)
    pw = SG.visual_to_descending(cx, ret.idx, n_keep=n_keep)

    tag = _key(n_keep=n_keep, slope=slope, offset=offset, tau=tau,
               sigma=sigma_deg, rounds=rounds, shuffle=shuffle_seed,
               retino=retino_seed, channel=channel_seed, v=4)
    path = os.path.join(MODEL_DIR, f"fly_{tag}.pkl")
    if cache and os.path.exists(path):
        with open(path, "rb") as fh:
            blob = pickle.load(fh)
    else:
        blob = _fit(cx, ret, pw, slope, offset, tau, sigma_deg, rounds,
                    shuffle_seed, retino_seed, channel_seed, verbose)
        if cache:
            os.makedirs(MODEL_DIR, exist_ok=True)
            with open(path, "wb") as fh:
                pickle.dump(blob, fh, protocol=4)

    net = S.RateNetwork(blob["n"], blob["pre"], blob["post"], blob["w"],
                        input_idx=blob["input_idx"], slope=slope,
                        offset=offset, tau=tau, label=blob["label"])
    net.mu, net.sigma = blob["mu"], blob["sigma"]
    readout = O.MotorReadout(groups=blob["groups"], names=blob["names"],
                             dn_local=blob["dn_local"],
                             label_of=blob["label_of"])
    return Fly(cx=cx, ret=ret, net=net, node_ids=blob["node_ids"],
               readout=readout, ph_local=blob["input_idx"],
               meta={"n_keep": n_keep, "slope": slope, "offset": offset,
                     "sigma_deg": sigma_deg, "shuffle_seed": shuffle_seed,
                     "retino_seed": retino_seed, "channel_seed": channel_seed,
                     "cache": path})


def _shuffle_edges(pre, post, w, n, seed):
    """Degree- and weight-preserving rewiring.

    Presynaptic endpoints keep their out-degree and postsynaptic endpoints keep
    their in-degree; which presynaptic neuron connects to which postsynaptic
    neuron is randomised, and the weight/sign multiset is permuted along with
    it.  Everything the real network has except its topology.

    Not quite exactly: about 1.3% of rewired edges land on a pair that already
    exists and get merged, so the degree sequence is preserved to within that.
    """
    rng = np.random.default_rng(seed)
    return rng.permutation(pre), post.copy(), w[rng.permutation(len(w))]


def _fit(cx, ret, pw, slope, offset, tau, sigma_deg, rounds, shuffle_seed,
         retino_seed, channel_seed, verbose):
    pre, post, w, node_ids = S.extract(cx, pw.node_ids, 1.0)
    label = "flywire783"
    if shuffle_seed is not None:
        pre, post, w = _shuffle_edges(pre, post, w, len(node_ids), shuffle_seed)
        label = f"shuffled-{shuffle_seed}"
    w = S.normalise_input(w, post, len(node_ids), 1.0)

    lut = np.full(cx.n_neurons, -1, np.int32)
    lut[node_ids] = np.arange(len(node_ids), dtype=np.int32)
    ph_local = lut[ret.idx]
    ph_local = ph_local[ph_local >= 0].astype(np.int32)
    if retino_seed is not None:
        # same photoreceptors, same graph; each one now sees a random part of
        # the visual field instead of the part its position says it sees
        ph_local = np.random.default_rng(retino_seed).permutation(ph_local)

    net = S.RateNetwork(len(node_ids), pre, post, w, input_idx=ph_local,
                        slope=slope, offset=offset, tau=tau, label=label)

    ens = []
    for az in CAL_AZ:
        for el in CAL_EL:
            e = np.zeros(net.n, np.float32)
            e[ph_local] = ret.drive([(az, el, 1.0)], sigma_deg=sigma_deg)
            ens.append(e)
    ens.append(np.zeros(net.n, np.float32))          # blank field
    net.calibrate(ens, rounds=rounds, verbose=verbose)

    readout = O.build(cx, node_ids, net.Wt)
    if channel_seed is not None:
        rng = np.random.default_rng(channel_seed)
        sizes = readout.sizes()
        shuffled = rng.permutation(readout.dn_local)
        cuts = np.cumsum(sizes)[:-1]
        readout.groups = [np.sort(g) for g in np.split(shuffled, cuts)]
        lab = np.zeros(len(readout.dn_local), np.int8)
        pos = {v: i for i, v in enumerate(readout.dn_local)}
        for gi, g in enumerate(readout.groups):
            for v in g:
                lab[pos[v]] = gi
        readout.label_of = lab
    return {"n": net.n, "pre": pre, "post": post, "w": w, "label": label,
            "input_idx": ph_local, "mu": net.mu, "sigma": net.sigma,
            "node_ids": node_ids, "groups": readout.groups,
            "names": readout.names, "dn_local": readout.dn_local,
            "label_of": readout.label_of}


if __name__ == "__main__":
    fly = build(verbose=True)
    print(fly.summary())
