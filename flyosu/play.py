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

import copy
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
        return self.play_many([chart], record=record,
                              controllers=None if controller is None else [controller],
                              seeds=[seed], taps=None if tap is None else [tap])[0]

    def play_many(self, charts: list[Chart], record: bool = False,
                  controllers: list[Controller] | None = None,
                  seeds: list[int | None] | None = None,
                  taps: list[Callable[[np.ndarray, ManiaEnv], None]] | None = None,
                  ) -> list[PlayResult]:
        """Play several charts at once, one network state per chart.

        Per chart this is exactly ``play``: each chart gets its own encoder,
        noise stream, controller and judge, and its result is bit-identical to
        playing it alone (the tests check this).  The difference is that the
        network steps every state in one sparse-matrix product, which reads the
        730k-synapse weight matrix once per frame rather than once per chart.
        That read is most of a frame's cost, so evaluating or recording many
        charts is two to three times cheaper per chart this way.

        The first chart uses ``self.encoder`` and its controller object as
        given, so a single-chart call leaves them in the state ``play`` always
        did; any later chart that would share an object gets its own copy.
        """
        fly, net = self.fly, self.fly.net
        B = len(charts)
        seeds = list(seeds) if seeds is not None else [None] * B
        given = list(controllers) if controllers is not None else [self.controller] * B
        ctrls, used = [], set()
        for c in given:
            ctrls.append(c if id(c) not in used else copy.deepcopy(c))
            used.add(id(c))
        encs = [self.encoder] + [copy.copy(self.encoder) for _ in range(B - 1)]
        envs = [ManiaEnv(ch, dt_ms=self.dt) for ch in charts]
        rngs = [np.random.default_rng(self.seed if s is None else s) for s in seeds]
        trs = [Trace([], [], [], [], []) if record else None for _ in range(B)]
        for e, c in zip(encs, ctrls):
            e.reset(); c.reset()
        ph = fly.ph_local
        live = [j for j in range(B) if not envs[j].done]   # column i holds chart live[i]
        R = np.repeat(self.r0[:, None], len(live), axis=1)
        EXT = np.zeros((net.n, len(live)), dtype=np.float32)
        vis = [None] * B
        t0 = time.time()
        n = 0
        while live:
            for i, j in enumerate(live):
                vis[j] = envs[j].visible()
                s = encs[j](vis[j], envs[j].dt)
                if self.noise > 0:
                    s = np.clip(s + rngs[j].normal(0.0, self.noise, len(s)), 0.0, 1.0)
                EXT[ph, i] = s
            R = net.step(R, EXT, envs[live[0]].dt)
            finished = []
            for i, j in enumerate(live):
                env, ctrl = envs[j], ctrls[j]
                r = np.ascontiguousarray(R[:, i])
                if taps is not None:
                    taps[j](r, env)
                a = fly.channels(r)
                z = self.norm.z(a) if self.features is None else self.features(r)
                keys = ctrl.step(z, env.t, env.dt)
                for k in keys:
                    env.press(k)
                # Hold notes: a key stays down while its drive stays above
                # threshold and lifts when it falls.  On a chart with no holds
                # ``release`` only clears a flag nothing reads, so this leaves
                # every earlier result untouched.
                down = ctrl.down()
                for k in range(len(down)):
                    if env.hold[k] and not down[k]:
                        env.release(k)
                tr = trs[j]
                if tr is not None:
                    tr.t.append(env.t); tr.channels.append(a); tr.z.append(z)
                    tr.drive.append(ctrl.drive().copy()); tr.visible.append(vis[j])
                env.step()
                if env.done:
                    finished.append(i)
            n += len(live)
            if finished:
                keep = [i for i in range(len(live)) if i not in finished]
                R, EXT = R[:, keep], EXT[:, keep]
                live = [live[i] for i in keep]
        self.stats = {"frames": n, "seconds": time.time() - t0,
                      "ms_per_frame": 1000.0 * (time.time() - t0) / max(n, 1)}
        out = []
        for env, tr in zip(envs, trs):
            res = env.result()
            if tr is not None:
                tr.t = np.array(tr.t); tr.channels = np.array(tr.channels)
                tr.z = np.array(tr.z); tr.drive = np.array(tr.drive)
                res.trace = tr           # type: ignore[attr-defined]
            out.append(res)
        return out

    def describe(self) -> str:
        return (f"{self.fly.net.label}  regime={self.fly.meta.get('regime')}  "
                f"dt={self.dt} ms  noise={self.noise}\n"
                f"encoder: {self.encoder.describe()}\n"
                f"controller: refractory {self.controller.refractory_ms:.0f} ms, "
                f"smoothing {self.controller.smooth_ms:.0f} ms\n"
                + self.controller.wiring(self.fly.readout.names))
