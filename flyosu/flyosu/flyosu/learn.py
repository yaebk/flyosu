"""
Plasticity: reward-modulated perturbation of the 20 readout parameters.

Step 9.  The design decision experiment 1 forced: a free readout is exactly
what erases the difference between the real connectome and a rewired one, so
learning is confined to the controller's ``W`` (4 x 4) and ``b`` (4) and the
connectome is frozen.  The question is not whether the fly can learn to play
but how fast, and whether the real wiring makes it faster.

The rule is a three-factor perturbation rule, the kind reinforcement learning in
small circuits is usually modelled with (node perturbation / REINFORCE):

    perturb      theta' = theta + eps,     eps ~ N(0, sigma^2)
    act          play one chart with theta', collect reward R
    consolidate  theta += lr * (R - R_baseline) * eps / sigma

Perturbations come in antithetic pairs (+eps, -eps) on the same chart, which
replaces the reward baseline with the paired difference and roughly halves the
variance.  Nothing in the rule needs a gradient through the network; it needs
one scalar per play.  That is what makes it a candidate for how a real fly
could do it.

Reward is osu!mania accuracy minus a small penalty per stray press, because
without the penalty the cheapest strategy is to mash every key.

``mask`` restricts learning to a subset of the 20 parameters ("thresholds
only" isolates timing; "wiring only" isolates the lane mapping).

``lr_decay`` anneals the learning rate geometrically per episode.  The first
run of experiment 2 used none and the real network's blank-start curve rose to
0.44 and fell back to 0.32; 0.97 per episode halves the rate over ~23 episodes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .controller import N_KEYS
from .mania import Chart, PlayResult, stage_chart
from .play import Player

STRAY_PENALTY = 0.05


def reward(res: PlayResult, stray_penalty: float = STRAY_PENALTY) -> float:
    n = max(len(res.chart), 1)
    return float(res.accuracy - stray_penalty * res.n_stray / n)


def mask_for(what: str) -> np.ndarray:
    m = np.zeros(N_KEYS * N_KEYS + N_KEYS, dtype=bool)
    if what in ("all", "wiring"):
        m[:N_KEYS * N_KEYS] = True
    if what in ("all", "thresholds"):
        m[N_KEYS * N_KEYS:] = True
    if not m.any():
        raise ValueError(what)
    return m


@dataclass
class Episode:
    index: int
    reward: float           # mean of the two perturbed plays
    accuracy: float
    hit_rate: float
    n_stray: int
    params: np.ndarray
    seconds: float


@dataclass
class ReadoutLearner:
    player: Player
    sigma: float = 0.3
    lr: float = 1.0
    lr_decay: float = 1.0
    n_pairs: int = 1
    mask: np.ndarray = field(default_factory=lambda: mask_for("all"))
    stage: int = 3
    n_notes: int = 12
    interval_ms: float = 500.0
    seed: int = 0
    history: list[Episode] = field(default_factory=list)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)

    def chart(self, k: int) -> Chart:
        return stage_chart(self.stage, n_notes=self.n_notes, interval_ms=self.interval_ms,
                           seed=100_000 * (self.seed + 1) + k)

    def episode(self) -> Episode:
        t0 = time.time()
        ctrl = self.player.controller
        theta = ctrl.params
        k = len(self.history)
        chart = self.chart(k)
        grad = np.zeros_like(theta)
        rs, accs, hits, strays = [], [], [], []
        for _ in range(self.n_pairs):
            eps = self.rng.normal(0.0, self.sigma, theta.shape) * self.mask
            out = []
            for sign in (+1.0, -1.0):
                trial = ctrl.copy()
                trial.params = theta + sign * eps
                res = self.player.play(chart, controller=trial, seed=k)
                out.append(reward(res))
                accs.append(res.accuracy); hits.append(res.hit_rate)
                strays.append(res.n_stray)
            rs += out
            grad += 0.5 * (out[0] - out[1]) * eps / self.sigma
        ctrl.params = theta + self.lr * self.lr_decay ** k * grad / self.n_pairs
        ep = Episode(k, float(np.mean(rs)), float(np.mean(accs)), float(np.mean(hits)),
                     int(np.mean(strays)), ctrl.params.copy(), time.time() - t0)
        self.history.append(ep)
        return ep

    def run(self, n_episodes: int, verbose: bool = True, every: int = 5) -> list[Episode]:
        for _ in range(n_episodes):
            ep = self.episode()
            if verbose and (ep.index % every == 0 or ep.index == n_episodes - 1):
                print(f"   ep {ep.index:3d}  reward {ep.reward:.3f}  acc {ep.accuracy:.3f}  "
                      f"hit {ep.hit_rate:.3f}  stray {ep.n_stray}  ({ep.seconds:.0f}s)", flush=True)
        return self.history

    def curve(self) -> np.ndarray:
        return np.array([e.reward for e in self.history])


def evaluate(player: Player, stage: int = 3, n_charts: int = 3, n_notes: int = 20,
             interval_ms: float = 600.0, seed: int = 999) -> dict:
    """Held-out performance on fresh charts (fixed seeds, never used in training)."""
    accs, hits, rws, strays, errs, conf = [], [], [], [], [], np.zeros((4, 4), int)
    for c in range(n_charts):
        res = player.play(stage_chart(stage, n_notes=n_notes, interval_ms=interval_ms,
                                      seed=seed + c), seed=seed + c)
        accs.append(res.accuracy); hits.append(res.hit_rate); rws.append(reward(res))
        strays.append(res.n_stray); errs += res.errors_ms.tolist()
        conf += res.lane_confusion
    errs = np.array(errs)
    return {"accuracy": float(np.mean(accs)), "hit_rate": float(np.mean(hits)),
            "reward": float(np.mean(rws)), "stray_per_note": float(np.sum(strays) / (n_charts * n_notes)),
            "lane_correct": float(np.trace(conf) / max(conf.sum(), 1)),
            "confusion": conf.tolist(),
            "error_mean_ms": float(errs.mean()) if len(errs) else None,
            "error_sd_ms": float(errs.std()) if len(errs) else None}
