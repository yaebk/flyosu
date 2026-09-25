"""
Checks for the reservoir readout: the offline machinery has to agree with the
online controller and judge exactly, the ridge fit has to recover a planted
readout, and the population projection has to be label-free and the right
shape.  The network part fits the real FlyWire fly and checks it beats the
untrained wiring on held-out charts.

    python -m tests.test_reservoir            # everything (~3 min, builds the fly)
    python -m tests.test_reservoir --fast     # only the parts that need no network
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flyosu import mania, reservoir as R  # noqa: E402
from flyosu.controller import Controller, N_KEYS  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def _synthetic_recording(chart, dt=2.0, k=6, seed=0):
    """Features that carry each lane's note as a smooth bump 30 ms before the
    hit, buried in k - 4 nuisance dimensions and noise."""
    env = mania.ManiaEnv(chart, dt_ms=dt)
    t = []
    while not env.done:
        t.append(env.t); env.step()
    t = np.asarray(t)
    rng = np.random.default_rng(seed)
    Z = rng.normal(0, 0.3, (len(t), k))
    for n in chart.notes:
        Z[:, n.lane] += 2.0 * np.exp(-0.5 * ((t - (n.hit_ms - 30.0)) / 40.0) ** 2)
    return R.Recording(chart=chart, t=t, X=Z.astype(np.float32), dt=dt)


class _Identity:
    def __init__(self, k): self.k = k
    def __call__(self, r): return np.asarray(r, dtype=np.float64)
    def batch(self, X): return np.asarray(X, dtype=np.float64)


def test_offline_matches_online():
    print("offline replay")
    chart = mania.stage_chart(3, n_notes=16, seed=3)
    rec = _synthetic_recording(chart, k=4)
    ctrl = Controller(W=np.eye(N_KEYS) * 0.8, b=np.full(N_KEYS, -0.6), refractory_ms=150.0, smooth_ms=40.0)
    # online: step the controller frame by frame against the judge
    env = mania.ManiaEnv(chart, dt_ms=rec.dt); ctrl.reset()
    for i in range(len(rec.t)):
        for lane in ctrl.step(rec.X[i], rec.t[i], rec.dt):
            env.press(lane)
        env.step()
    online = env.result()
    # offline: smooth, drive, crossing rule, replay
    u = R.smooth(rec.X.astype(np.float64), rec.dt, ctrl.smooth_ms) @ ctrl.W.T + ctrl.b
    offline = R.replay(rec, R.replay_presses(u, rec.t, ctrl.refractory_ms))
    check("same press times", [p.t_ms for p in online.presses] == [p.t_ms for p in offline.presses],
          f"{len(online.presses)} presses")
    check("same judgments", online.judgments == offline.judgments)
    check("some notes were hit", online.hit_rate > 0.5, online.summary())
    check("lane rewards average to the reward",
          abs(R.lane_rewards(offline, 0.05).mean() - (offline.accuracy - 0.05 * offline.n_stray / len(chart))) < 1e-9)
    # mashing every lane at every note must lose to playing one's own lane
    mash = R.replay(rec, [[0, 1, 2, 3] if any(abs(n.hit_ms - ti) < rec.dt / 2 for n in chart.notes) else []
                          for ti in rec.t])
    check("stray penalty makes four-lane mashing a loss", R.lane_rewards(mash).mean() < 0,
          f"acc {mash.accuracy:.2f}, strays/note {mash.n_stray / len(chart):.2f}, "
          f"lane reward {R.lane_rewards(mash).mean():+.2f}")


def test_fit():
    print("ridge fit")
    recs = [_synthetic_recording(mania.stage_chart(3, n_notes=24, seed=s), k=6, seed=s) for s in range(3)]
    Zs = np.vstack([R.smooth(r.X.astype(np.float64), r.dt, 40.0) for r in recs])
    Y = np.vstack([R.target(r, lead_ms=30.0, width_ms=80.0) for r in recs])
    W, b = R.fit_ridge(Zs, Y, lam=1e-3)
    diag = np.abs(np.diag(W[:, :4])); off = np.abs(W[:, :4] - np.diag(np.diag(W[:, :4])))
    check("each lane reads its own feature", (diag > 3 * off.max(1)).all(), np.array2string(W, precision=2))
    check("nuisance features weigh less than the signal", np.abs(W[:, 4:]).max() < diag.min())
    check("targets are +1 inside the window only", Y.max() == 1 and (Y == 1).mean() < 0.1)

    class _Player:                       # just enough for RidgeReadout.solve()
        controller = Controller.blank(); features = None; fly = None; norm = None
    p = _Player()
    rr = R.RidgeReadout(p, features=_Identity(6), n_charts=3)
    rr.recordings = recs
    d = rr.solve()
    check("solve installs a 4 x 6 controller", p.controller.W.shape == (4, 6) and d["n_params"] == 28)
    check("fitted readout plays the training charts well", d["train_reward"] > 0.8, f"{d['train_reward']:.2f}")
    res = [R.replay(r, R.replay_presses(R.smooth(r.X.astype(np.float64), r.dt, 40.0) @ p.controller.W.T
                                        + p.controller.b, r.t, 150.0)) for r in recs]
    check("presses land in the right lane", all(x.lane_confusion.trace() == x.lane_confusion.sum() for x in res))


def test_with_network():
    from flyosu import learn as L, model as M, play as P
    print("real fly")
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=1.5, noise=0.03)
    before = L.evaluate(player, stage=3, n_charts=2, n_notes=16, seed=4242)
    proj = R.PopulationProjection.fit(fly, player.r0, k=8)
    check("projection covers the descending population", len(proj.idx) == len(fly.readout.dn_local))
    check("components are orthonormal", np.allclose(proj.components @ proj.components.T, np.eye(8), atol=1e-6))
    check("explained variance is ordered", (np.diff(proj.explained) <= 1e-12).all())
    check("blank state maps to finite features", np.isfinite(proj(player.r0)).all())
    rr = R.RidgeReadout(player, features=proj, n_charts=2, n_notes=16)
    d = rr.fit()
    check("one recording, 36 parameters", d["n_params"] == 36 and len(rr.recordings) == 2,
          f"{d['seconds']:.0f} s")
    ch = R.ChannelFeatures(player)
    Xb = rr.recordings[0].X[:5]
    online = np.array([player.norm.z(np.array([Xb[i, g].mean() for g in ch.pos], dtype=np.float32)) for i in range(5)])
    check("channel features agree online/offline", np.allclose(ch.batch(Xb), online, atol=1e-3))
    after = L.evaluate(player, stage=3, n_charts=2, n_notes=16, seed=4242)
    check("fitted readout beats the untrained wiring", after["accuracy"] > before["accuracy"],
          f"{before['accuracy']:.3f} -> {after['accuracy']:.3f}")
    check("and presses in the right lanes", after["lane_correct"] >= 0.9, f"{after['lane_correct']:.2f}")
    # the same recording serves the 20-parameter channel readout
    rr.features = None
    d2 = rr.solve()
    check("channel readout from the same recording", d2["n_params"] == 20 and player.features is None)


def main():
    test_offline_matches_online()
    test_fit()
    if "--fast" not in sys.argv:
        test_with_network()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
