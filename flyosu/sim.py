"""
Leaky integrate-and-fire simulation over the FlyWire connectome.

Parameters follow the published whole-brain Drosophila leaky-integrate-and-fire
model of Shiu, Sterne et al. (2024, Nature), which was fitted to and validated
against this same FlyWire dataset:

    resting / reset potential   -52 mV
    spike threshold             -45 mV
    membrane time constant       20 ms
    refractory period           2.2 ms
    synaptic delay              1.8 ms
    unit synaptic weight      0.275 mV per synapse

Edge sign comes from the FlyWire neurotransmitter prediction: acetylcholine is
excitatory, GABA and glutamate inhibitory (glutamate is inhibitory in the fly
via GluCl-alpha).  An edge of ``s`` synapses therefore steps the postsynaptic
membrane by ``sign * s * 0.275 mV``.

Propagation is sparse in the spike vector: each step only touches the outgoing
edges of neurons that actually fired, which is ~1-3 ms of wall clock for the
full 139k-neuron / 15M-edge graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from .connectome import Connectome

V_REST = -52.0
V_RESET = -52.0
V_THRESH = -45.0
TAU_M = 20.0          # ms
T_REF = 2.2           # ms
DELAY = 1.8           # ms
W_SYNAPSE = 0.275     # mV per synapse

# Spike-frequency adaptation.  Not part of the Shiu et al. parameter set, but
# required here: with the raw connectome weights the network has no stable
# operating point between "signal dies in layer 1" and "the whole brain
# saturates at the refractory ceiling" (see docs/CALIBRATION.md).  Adaptation is
# ubiquitous in real neurons and is what buys a usable dynamic range.
TAU_ADAPT = 150.0     # ms
B_ADAPT = 1.2         # mV threshold increment per spike


def extract(cx: Connectome, subset: np.ndarray | None, scale: float):
    """Re-index the connectome onto a subset.  Returns (pre, post, w, node_ids)."""
    if subset is None:
        node_ids = np.arange(cx.n_neurons, dtype=np.int32)
        pre, post, keep = cx.pre, cx.post, slice(None)
    else:
        node_ids = np.unique(np.asarray(subset, dtype=np.int32))
        lut = np.full(cx.n_neurons, -1, dtype=np.int32)
        lut[node_ids] = np.arange(len(node_ids), dtype=np.int32)
        keep = (lut[cx.pre] >= 0) & (lut[cx.post] >= 0)
        pre, post = lut[cx.pre[keep]], lut[cx.post[keep]]
    w = (cx.syn[keep].astype(np.float32)
         * cx.sign[keep].astype(np.float32) * np.float32(scale))
    return pre, post, w, node_ids


def normalise_input(w: np.ndarray, post: np.ndarray, n: int,
                    total: float) -> np.ndarray:
    """Give every neuron the same total synaptic budget.

    ``w`` is rescaled per postsynaptic neuron so ``sum |w| == total``.  This is
    a modelling assumption the connectome cannot supply: raw synapse counts give
    in-degrees spanning three orders of magnitude, and with a fixed 7 mV spike
    threshold that makes the network either silent or globally epileptic.
    Normalising says each neuron has a fixed synaptic budget and the connectome
    determines how it is *divided*, not how large it is.  Relative weights
    within a neuron's input -- the part the connectome actually measures -- and
    every edge sign are preserved exactly.
    """
    s = np.bincount(post, weights=np.abs(w), minlength=n)
    s[s == 0] = 1.0
    return (w * (np.float32(total) / s[post])).astype(np.float32)


@dataclass
class Result:
    """Outcome of one simulation run."""

    spikes: np.ndarray            # (N,) int32 spike count per neuron
    duration_ms: float
    rate: np.ndarray = field(init=False)   # (N,) float32 Hz
    trace: np.ndarray | None = None        # (T, len(record)) spike raster
    record: np.ndarray | None = None       # neuron indices in ``trace``

    def __post_init__(self):
        self.rate = (self.spikes / (self.duration_ms / 1000.0)).astype(np.float32)


class Network:
    """LIF network over a (sub)set of connectome neurons."""

    def __init__(self, n: int, pre: np.ndarray, post: np.ndarray,
                 weight: np.ndarray, label: str = "network"):
        self.n = int(n)
        self.label = label
        W = sp.csr_matrix((weight.astype(np.float32), (pre, post)),
                          shape=(n, n), dtype=np.float32)
        W.sum_duplicates()
        W.sort_indices()
        self.W = W                          # row = presynaptic neuron
        self._indptr = W.indptr
        self._indices = W.indices
        self._data = W.data

    # -- construction ------------------------------------------------------

    @classmethod
    def from_connectome(cls, cx: Connectome, subset: np.ndarray | None = None,
                        w_synapse: float = W_SYNAPSE, gain: float = 1.0,
                        norm: str | None = None, w_total: float = 30.0,
                        label: str = "flywire783") -> tuple["Network", np.ndarray]:
        """Build a network.  Returns (network, node_ids) where ``node_ids[i]``
        is the Connectome index of network neuron ``i``.

        ``norm="input"`` rescales each postsynaptic neuron's incoming weights so
        their absolute values sum to ``w_total`` mV.  See ``normalise_input``.
        """
        pre, post, w, node_ids = extract(cx, subset, w_synapse * gain)
        if norm == "input":
            w = normalise_input(w, post, len(node_ids), w_total)
        elif norm not in (None, "none"):
            raise ValueError(norm)
        return cls(len(node_ids), pre, post, w, label=label), node_ids

    @property
    def n_edges(self) -> int:
        return int(self.W.nnz)

    # -- dynamics ----------------------------------------------------------

    def _propagate(self, fired: np.ndarray) -> np.ndarray:
        """Summed synaptic input (mV) delivered by the given firing neurons."""
        if fired.size == 0:
            return np.zeros(self.n, dtype=np.float32)
        return np.asarray(self.W[fired].sum(axis=0), dtype=np.float32).ravel()

    def run(self, duration_ms: float = 500.0, dt: float = 0.5,
            drive_idx: np.ndarray | None = None,
            drive_rate: np.ndarray | None = None,
            drive_schedule=None,
            noise_hz: float = 0.0,
            b_adapt: float = B_ADAPT,
            tau_adapt: float = TAU_ADAPT,
            seed: int = 0,
            record: np.ndarray | None = None,
            warmup_ms: float = 0.0) -> Result:
        """Simulate.

        ``drive_idx`` / ``drive_rate``  neurons driven as independent Poisson
        sources at the given rates in Hz (used for photoreceptors).
        ``drive_schedule``  optional ``f(t_ms) -> rates`` overriding
        ``drive_rate`` each step, for time-varying stimuli.
        ``noise_hz``  background Poisson drive applied to every neuron.
        ``record``  neuron indices whose spikes are kept as a raster.
        ``warmup_ms``  leading interval excluded from the returned counts.
        """
        rng = np.random.default_rng(seed)
        n, steps = self.n, int(round(duration_ms / dt))
        warm = int(round(warmup_ms / dt))

        v = np.full(n, V_REST, dtype=np.float32)
        ref = np.zeros(n, dtype=np.float32)
        adapt = np.zeros(n, dtype=np.float32)
        counts = np.zeros(n, dtype=np.int32)
        adapt_decay = np.float32(np.exp(-dt / tau_adapt))

        n_delay = max(1, int(round(DELAY / dt)))
        buffer: list[np.ndarray] = [np.empty(0, np.int32) for _ in range(n_delay)]

        decay = np.float32(np.exp(-dt / TAU_M))
        drive_idx = None if drive_idx is None else np.asarray(drive_idx, np.int32)
        p_noise = noise_hz * dt / 1000.0

        trace = None
        if record is not None:
            record = np.asarray(record, np.int32)
            trace = np.zeros((steps, len(record)), dtype=np.uint8)

        for t in range(steps):
            arrived = buffer[t % n_delay]
            v = V_REST + (v - V_REST) * decay
            if arrived.size:
                v += self._propagate(arrived)

            if drive_idx is not None:
                rates = (drive_schedule(t * dt) if drive_schedule is not None
                         else drive_rate)
                p = np.clip(np.asarray(rates, np.float32) * dt / 1000.0, 0, 1)
                hit = drive_idx[rng.random(len(drive_idx)) < p]
                if hit.size:
                    # clear the refractory/adaptation state so a commanded
                    # sensory spike always lands at the requested rate
                    v[hit] = V_THRESH + adapt[hit] + 1.0
                    ref[hit] = 0.0
            if p_noise > 0:
                nz = np.flatnonzero(rng.random(n) < p_noise)
                v[nz] = V_THRESH + adapt[nz] + 1.0

            adapt *= adapt_decay
            active = ref <= 0
            fired = np.flatnonzero((v > V_THRESH + adapt) & active).astype(np.int32)
            if fired.size:
                v[fired] = V_RESET
                ref[fired] = T_REF
                adapt[fired] += b_adapt
                if t >= warm:
                    counts[fired] += 1
                if trace is not None:
                    trace[t] = np.isin(record, fired)
            v[~active] = V_RESET
            ref -= dt
            buffer[t % n_delay] = fired

        eff = (steps - warm) * dt
        return Result(spikes=counts, duration_ms=eff, trace=trace, record=record)


def summarise(res: Result, node_ids: np.ndarray, cx: Connectome,
              top: int = 10) -> str:
    """Human-readable summary of a run."""
    r = res.rate
    lines = [f"mean rate {r.mean():6.2f} Hz | active(>1Hz) "
             f"{int((r > 1).sum()):,}/{len(r):,} | max {r.max():.0f} Hz"]
    order = np.argsort(-r)[:top]
    lines.append("  most active:")
    for i in order:
        a = cx.ann.iloc[node_ids[i]]
        lines.append(f"    {r[i]:7.1f} Hz  {str(a.cell_type):<14s} "
                     f"{str(a.super_class):<18s} {str(a.side)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Graded rate engine
# ---------------------------------------------------------------------------

class RateNetwork:
    """Continuous-rate network over the signed, weighted connectome graph.

    Input neurons (the photoreceptors) are clamped to the stimulus.  Every other
    neuron follows

        x_i        = sum_j  w_ij r_j                  (normalised weights)
        z_i        = slope * (x_i - mu_i) / sigma_i + offset
        tau dr/dt  = -r_i + logistic(z_i)

    ``mu_i`` and ``sigma_i`` are that neuron's operating point: the mean and
    spread of the synaptic input it receives across a representative ensemble of
    stimuli, measured by ``calibrate``.  Everything the connectome measures --
    the graph, the relative weight of each input, and every excitatory /
    inhibitory sign -- enters through ``x_i`` and is untouched.  What the
    calibration adds is two scalars per neuron: how excitable it is and how
    steeply it responds.

    This is not decoration.  Raw connectome weights have no usable operating
    point: with a fixed threshold, roughly three quarters of neurons receive net
    inhibition and fall silent while the rest saturate, and a stimulus either
    dies in the first layer or ignites the whole brain.  Setting each cell's
    excitability to match its typical input is what real intrinsic homeostatic
    plasticity does, and it is the minimum needed to make the wiring diagram
    run.  ``docs/CALIBRATION.md`` records what was tried before this.
    """

    def __init__(self, n: int, pre: np.ndarray, post: np.ndarray,
                 weight: np.ndarray, input_idx: np.ndarray | None = None,
                 slope: float = 2.5, offset: float = -1.2, tau: float = 20.0,
                 label: str = "rate"):
        W = sp.csr_matrix((weight.astype(np.float32), (post, pre)),
                          shape=(n, n), dtype=np.float32)
        W.sum_duplicates()
        W.sort_indices()
        self.Wt = W                 # row = postsynaptic neuron
        self.n = int(n)
        self.tau = float(tau)
        self.slope = float(slope)
        self.offset = float(offset)
        self.label = label
        self.mu = np.zeros(n, np.float32)
        self.sigma = np.ones(n, np.float32)
        self.is_input = np.zeros(n, bool)
        if input_idx is not None:
            self.is_input[np.asarray(input_idx, np.int32)] = True

    @classmethod
    def from_connectome(cls, cx: Connectome, subset: np.ndarray | None = None,
                        input_global: np.ndarray | None = None, **kw):
        pre, post, w, node_ids = extract(cx, subset, 1.0)
        w = normalise_input(w, post, len(node_ids), 1.0)
        inp = None
        if input_global is not None:
            lut = np.full(cx.n_neurons, -1, np.int32)
            lut[node_ids] = np.arange(len(node_ids), dtype=np.int32)
            inp = lut[np.asarray(input_global)]
            inp = inp[inp >= 0]
        return cls(len(node_ids), pre, post, w, input_idx=inp,
                   label="flywire783-rate", **kw), node_ids

    @property
    def n_edges(self) -> int:
        return int(self.Wt.nnz)

    # -- dynamics ----------------------------------------------------------

    def activation(self, x: np.ndarray) -> np.ndarray:
        # ``x`` is (n,) for one state or (n, B) for B states stepped together
        # (``Player.play_many``); the per-neuron operating point then broadcasts
        # along the batch.  Elementwise, so each column is bit-identical to
        # stepping that state alone.
        mu, sigma = self.mu, self.sigma
        if x.ndim == 2 and np.ndim(mu) == 1:
            mu, sigma = mu[:, None], (sigma[:, None] if np.ndim(sigma) == 1 else sigma)
        z = self.slope * (x - mu) / sigma + self.offset
        return (1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))).astype(np.float32)

    def step(self, r: np.ndarray, ext: np.ndarray, dt: float) -> np.ndarray:
        x = self.Wt @ r
        r = r + (dt / self.tau) * (self.activation(x) - r)
        r[self.is_input] = ext[self.is_input]
        return r

    def run(self, ext, duration_ms: float = 300.0, dt: float = 5.0,
            r0: np.ndarray | None = None, record_every: int = 0):
        """Integrate.  ``ext`` is a fixed (N,) vector or ``f(t_ms) -> (N,)``."""
        r = (np.zeros(self.n, np.float32) if r0 is None
             else r0.astype(np.float32).copy())
        static = not callable(ext)
        e = np.asarray(ext, np.float32) if static else None
        trace = [] if record_every else None
        for t in range(int(round(duration_ms / dt))):
            r = self.step(r, e if static else np.asarray(ext(t * dt), np.float32), dt)
            if record_every and t % record_every == 0:
                trace.append(r.copy())
        return r, (np.array(trace) if trace else None)

    # -- operating-point calibration ---------------------------------------

    def calibrate(self, stimuli, rounds: int = 8, duration_ms: float = 300.0,
                  dt: float = 5.0, sigma_floor: float = 0.05,
                  damping: float = 0.5, verbose: bool = False) -> list[float]:
        """Measure each neuron's operating point over a stimulus ensemble.

        ``mu_i`` becomes the mean synaptic input neuron i receives across the
        ensemble and ``sigma_i`` its spread, so after calibration every neuron
        sits in the responsive part of its activation function and the part of
        its input that *varies with the stimulus* is what drives it.  Neurons
        whose input barely varies get a floored sigma so they stay quiet instead
        of amplifying nothing.

        Repeated because changing the operating point changes the rates.
        Returns the median across-stimulus input spread at each round.
        """
        stimuli = [np.asarray(s, np.float32) for s in stimuli]
        hist = []
        for k in range(rounds):
            X = np.empty((len(stimuli), self.n), np.float32)
            for j, ext in enumerate(stimuli):
                r, _ = self.run(ext, duration_ms=duration_ms, dt=dt)
                X[j] = self.Wt @ r
            mu = X.mean(axis=0)
            sd = X.std(axis=0)
            free = ~self.is_input
            floor = sigma_floor * float(np.median(sd[free & (sd > 0)]) or 1.0)
            sd = np.maximum(sd, floor)
            # damped update: the operating point changes the rates that are
            # used to measure it, so an undamped update oscillates
            a = 1.0 if k == 0 else damping
            self.mu = ((1 - a) * self.mu + a * mu).astype(np.float32)
            self.sigma = np.exp((1 - a) * np.log(self.sigma)
                                + a * np.log(sd)).astype(np.float32)
            hist.append(float(np.median(sd[free])))
            if verbose:
                print(f"   calib round {k + 1}: median input spread "
                      f"{hist[-1]:.5f}  floored "
                      f"{int((sd <= floor)[free].sum()):,}/{int(free.sum()):,}")
        return hist
