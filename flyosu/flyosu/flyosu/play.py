"""
The game loop: chart -> eye -> connectome -> channels -> keys -> judge.

    fly    = model.build(regime="play")
    player = Player.untrained(fly)
    result = player.play(mania.stage_chart(3))
    print(result.summary())

Every frame (``dt`` ms, default 2 ms -- see ``model.DT_PLAY``):

    visible  = env.visible()                    what is on the playfield
    ext      = encoder(visible)  (+ noise)      light on 8,452 photoreceptors
    r        = net.step(r, ext)                 one step of the connectome
    z        = normaliser.z(channels(r))        four channels on a common scale
                                                (or ``features(r)``, if set)
    keys     = controller.step(z, t)            threshold crossings
    env.press(k) for k in keys;  env.step()     judged, clock advances

There is no modelled motor latency: a press is judged at the frame it fires.
The controller's thresholds absorb any systematic lead or lag, which is one of
the things learning has to get right.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .controller import ChannelNormaliser, Controller
from .encoder import Encoder
from .mania import Chart, ManiaEnv, PlayResult
from .model import DT_PLAY, Fly


@dataclass
class Trace:
    t: np.ndarray               # (T,)
    channels: np.ndarray        # (T, 4) raw channel activity
    z: np.ndarray               # (T, 4) normalised
    drive: np.ndarray           # (T, 4) controller pre-threshold drive
    visible: list               # per frame: [(lane, progress, note), ...]


@dataclass
class Player:
    fly: Fly
    encoder: Encoder
    norm: ChannelNormaliser
    controller: Controller
    r0: np.ndarray                      # blank-field state the network starts from
    dt: float = DT_PLAY
    noise: float = 0.0                  # photoreceptor noise sd per frame
    seed: int = 0
    features: Callable[[np.ndarray], np.ndarray] | None = None   # replaces norm.z(channels(r))
    stats: dict = field(default_factory=dict)

    @classmethod
    def untrained(cls, fly: Fly, theta: float = 1.0, encoder: Encoder | None = None,
                  dt: float = DT_PLAY, noise: float = 0.0, seed: int = 0,
                  wired: bool = True, **ctrl_kw) -> "Player":
        """Blank fixed point, label-free normaliser, anatomical (or blank) wiring."""
        r0 = fly.settle(dt=dt)
        norm = ChannelNormaliser.fit(fly, r0, dt=dt)
        ctrl = (Controller.anatomical(fly, norm, r0, theta=theta, dt=dt, **ctrl_kw)
                if wired else Controller.blank(theta=theta, **ctrl_kw))
        return cls(fly=fly, encoder=encoder or Encoder(fly.ret), norm=norm,
                   controller=ctrl, r0=r0, dt=dt, noise=noise, seed=seed)

    def play(self, chart: Chart, record: bool = False,
             controller: Controller | None = None,
             seed: int | None = None,
             tap: Callable[[np.ndarray, ManiaEnv], None] | None = None) -> PlayResult:
        """Play one chart.  ``tap(r, env)`` is called every frame after the
        network step, before the controller acts -- used to record activity."""
        fly, net = self.fly, self.fly.net
        ctrl = controller if controller is not None else self.controller
        env = ManiaEnv(chart, dt_ms=self.dt)
        rng = np.random.default_rng(self.seed if seed is None else seed)
        ph = fly.ph_local
        ext = np.zeros(net.n, dtype=np.float32)
        r = self.r0.copy()
        self.encoder.reset()
        ctrl.reset()
        tr = Trace([], [], [], [], []) if record else None
        t0 = time.time()
        n = 0
        while not env.done:
            vis = env.visible()
            s = self.encoder(vis, env.dt)
            if self.noise > 0:
                s = np.clip(s + rng.normal(0.0, self.noise, len(s)), 0.0, 1.0)
            ext[ph] = s
            r = net.step(r, ext, env.dt)
            if tap is not None:
                tap(r, env)
            a = fly.channels(r)
            z = self.norm.z(a) if self.features is None else self.features(r)
            keys = ctrl.step(z, env.t, env.dt)
            for k in keys:
                env.press(k)
            if tr is not None:
                tr.t.append(env.t); tr.channels.append(a); tr.z.append(z)
                tr.drive.append(ctrl.drive().copy()); tr.visible.append(vis)
            env.step()
            n += 1
        self.stats = {"frames": n, "seconds": time.time() - t0,
                      "ms_per_frame": 1000.0 * (time.time() - t0) / max(n, 1)}
        res = env.result()
        if tr is not None:
            tr.t = np.array(tr.t); tr.channels = np.array(tr.channels)
            tr.z = np.array(tr.z); tr.drive = np.array(tr.drive)
            res.trace = tr           # type: ignore[attr-defined]
        return res

    def describe(self) -> str:
        return (f"{self.fly.net.label}  regime={self.fly.meta.get('regime')}  "
                f"dt={self.dt} ms  noise={self.noise}\n"
                f"encoder: {self.encoder.describe()}\n"
                f"controller: refractory {self.controller.refractory_ms:.0f} ms, "
                f"smoothing {self.controller.smooth_ms:.0f} ms\n"
                + self.controller.wiring(self.fly.readout.names))
