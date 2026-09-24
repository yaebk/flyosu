"""
The connectome as a reservoir: a readout fitted in closed form.

The fly is a fixed recurrent network with a small linear readout on top.  That
is the architecture of a reservoir computer (echo-state network, liquid state
machine), and the standard way to train a reservoir's readout is not
trial-and-error but *ridge regression on recorded activity*.  osu!mania makes
the supervision free: the notes fall whether or not the player presses, so the
right answer at every frame -- "press lane l now" -- is known from the chart.
Record the network once while charts fall past it, regress the press target on
the recorded activity, and the same 20 numbers the perturbation learner in
``learn.py`` spends hours on come out of one ``lstsq`` call.

What this buys the project is controls.  Every comparison so far is starved of
them (four rewired networks per family in experiment 3; p = 0.048 on twenty in
experiment 4) because each learned network cost an hour.  A fit that costs one
recording pass per network makes twenty controls per family routine.

What stays fixed, so that the comparison is still about the wiring:

  * The connectome is frozen.  Nothing inside the network changes.
  * The readout's *inputs* are label-free.  Either the four normalised
    channels (``ChannelNormaliser``: 4 x 4 + 4 = 20 parameters, the same
    controller ``learn.py`` trains), or a ``PopulationProjection``: the top k
    principal components of the readout population over the same 61-stimulus
    calibration ensemble, z-scored on it.  Neither sees a lane or a key.  The
    projection exists for the male CNS, whose four leg motor pools move as a
    common mode under visual input (docs/MALECNS.md): PCA puts the common mode
    in one component and lets the regression ignore it.
  * The controller is unchanged: leaky integration, ``u = W z + b``, press on
    an upward zero-crossing, refractory period.  The regression fits ``W`` and
    ``b`` and nothing else.
  * The real network and every control get the identical procedure, the
    identical training charts, and the identical parameter count.

What the number means.  A ridge readout is a *supervised ceiling*: the best a
linear readout of this size can do given what the network makes linearly
available.  It is not a candidate for how a fly learns; ``learn.py`` is.  The
two are complementary -- the ceiling says how much lane and timing information
the wiring exposes, the perturbation learner says how quickly a plausible rule
finds it -- and the controls are what make either one a statement about the
connectome rather than about the readout.

Fitting details.  Recordings are open-loop (a silent controller), so a note
slides past the judgment line before it is retired; in closed-loop play a hit
note vanishes at the press.  The open-loop set is a superset -- the extra
frames are "do not press" frames after a note -- so no second round is taken.
The target for lane l is +1 over a ``width_ms`` window that opens ``lead_ms``
before a note's hit time, -1 elsewhere, weighted so the two classes balance
per lane.  The fitted ``u`` is then a bump around each note; *where* its
rising edge crosses zero is set afterwards by two numbers per lane -- the
window's lead and a threshold offset -- chosen on the training recordings by
replaying the crossing rule offline through the judge.  A linear readout of
instantaneous features cannot delay a signal, but a note's position on the
playfield is in the features, so asking for the window at a different place
along the descent gives a different linear map; that is what the lead search
uses.  Lanes do not interact in the judge, so the four (lead, offset) pairs
are chosen independently from the same replays.

The selection criterion is per-lane accuracy minus ``stray_penalty`` per stray
press per note in the lane, with the penalty deliberately *larger* than the
0.05 the perturbation learner's reward uses.  osu!mania itself charges nothing
for a press in an empty lane, so a readout that fires every lane at every note
scores 1.0 accuracy; at 0.05 that costs 0.15 and the offset search happily
picks it (the first run of experiment 5 did, at 1.5 stray presses per note on
the male CNS).  At 0.4 a stray costs more than a third of a perfect note and
mashing four lanes is a net loss.  Held-out evaluation still reports accuracy,
hit rate, strays per note and lane-correctness separately; the penalty only
decides which threshold the fit installs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
import numpy as np

from .controller import N_KEYS, Controller, calibration_states
from .mania import ACC_WEIGHT, Chart, ManiaEnv, PlayResult, stage_chart
from .model import DT_PLAY, Fly
from .play import Player



# -- label-free features ---------------------------------------------------
#
# A feature object maps the network state to the controller's inputs, online
# (``__call__(r)``, one frame) and offline (``batch(X)``, X = (T, n) recorded
# activity of the readout population ``fly.readout.dn_local``).  One recording
# of the population serves every readout fitted on it.

class ChannelFeatures:
    """The four normalised channels, as the controller normally sees them."""

    def __init__(self, player: Player):
        self.fly, self.norm = player.fly, player.norm
        lut = {int(v): i for i, v in enumerate(self.fly.readout.dn_local)}
        self.pos = [np.array([lut[int(i)] for i in g], dtype=np.int64)
                    for g in self.fly.readout.groups]

    def __call__(self, r: np.ndarray) -> np.ndarray:
        return self.norm.z(self.fly.channels(r))

    def batch(self, X: np.ndarray) -> np.ndarray:
        # float64 here; the online path pools in float32, so the two agree to ~1e-4 z
        A = np.stack([X[:, g].astype(np.float64).mean(1) if len(g) else np.zeros(len(X))
                      for g in self.pos], axis=1)
        return self.norm.z(A)

    @property
    def k(self) -> int:
        return N_KEYS


@dataclass
class PopulationProjection:
    """Top-k principal components of a neuron population over the calibration
    ensemble, z-scored on the same ensemble.  Label-free."""

    idx: np.ndarray             # network-local neurons read
    mean: np.ndarray            # (n,) ensemble mean
    components: np.ndarray      # (k, n)
    mu: np.ndarray              # (k,) projection mean over the ensemble
    sd: np.ndarray              # (k,) projection sd over the ensemble
    explained: np.ndarray       # (k,) fraction of ensemble variance

    def __call__(self, r: np.ndarray) -> np.ndarray:
        return self.batch(np.asarray(r[self.idx], dtype=np.float64)[None])[0]

    def batch(self, X: np.ndarray) -> np.ndarray:
        p = (np.asarray(X, dtype=np.float64) - self.mean) @ self.components.T
        return (p - self.mu) / self.sd

    @property
    def k(self) -> int:
        return len(self.mu)

    @classmethod
    def fit(cls, fly: Fly, r0: np.ndarray, k: int = 8, idx: np.ndarray | None = None,
            dt: float = DT_PLAY, states: list[np.ndarray] | None = None) -> "PopulationProjection":
        """``states`` lets a caller pass the calibration ensemble it already has."""
        idx = fly.readout.dn_local if idx is None else np.asarray(idx)
        states = calibration_states(fly, r0, dt) if states is None else states
        X = np.array([s[idx] for s in states], dtype=np.float64)
        return cls.from_activity(idx, X, k)

    @classmethod
    def from_activity(cls, idx: np.ndarray, X: np.ndarray, k: int) -> "PopulationProjection":
        """The projection fitted on any (samples, len(idx)) activity matrix.
        ``fit`` uses the 61 calibration states; a caller can instead pass the
        activity recorded on the training charts, which is still label-free
        (no target is used) but spans far more than the calibration set's 60
        dimensions."""
        X = np.asarray(X, dtype=np.float64)
        mean = X.mean(0)
        U, S, Vt = np.linalg.svd(X - mean, full_matrices=False)
        # Components past the rank have singular values at rounding level; the
        # z-scoring below would divide by that and turn them into huge noise,
        # which is how a 64-component readout on the 61 calibration states
        # (rank 60) collapsed to 0.02.  Refuse rather than silently cap.
        rank = int((S > S[0] * 1e-9).sum()) if len(S) else 0
        if k > rank:
            raise ValueError(f"asked for {k} components but the activity has rank {rank} "
                             f"({len(X)} samples)")
        comp = Vt[:k]
        P = (X - mean) @ comp.T
        sd = P.std(0)
        sd[sd <= 0] = 1.0
        var = S ** 2
        return cls(idx=idx, mean=mean, components=comp, mu=P.mean(0), sd=sd,
                   explained=var[:k] / max(var.sum(), 1e-30))


Features = ChannelFeatures | PopulationProjection


# -- recording -------------------------------------------------------------

@dataclass
class Recording:
    chart: Chart
    t: np.ndarray               # (T,) frame times, ms
    X: np.ndarray               # (T, n) readout-population activity per frame
    dt: float
    # True when X already holds features (``record_many(project=...)``), not
    # raw activity: (T, k) float64 instead of (T, n) float32.
    projected: bool = False


class HoldOracle:
    """Recording stand-in that plays the hold notes, and only those, perfectly:
    each hold's key goes down on the first frame at or after its head and comes
    up on the first frame at or after its tail.  Every other note is left alone,
    exactly as the silent controller leaves it.

    Why: the silent controller never presses, so every hold is missed, and a
    missed hold leaves the screen 164 ms after its head -- for a 480 ms hold,
    316 ms before its tail.  The fit then learns when to release from recordings
    in which the body it should be watching has already vanished.  With this the
    fly is shown what a good player sees: the body shrinking down to the line.
    A chart with no holds is untouched, so its recording is bit-identical."""

    def __init__(self, chart: Chart):
        self.holds = sorted((n.hit_ms, n.end_ms, n.lane) for n in chart.notes if n.is_hold)
        self.reset()

    def reset(self) -> None:
        self.i = 0
        self.t = -np.inf
        self.until = np.full(N_KEYS, -np.inf)

    def step(self, z, t_ms: float, dt_ms: float) -> list[int]:
        self.t = t_ms
        keys = []
        while self.i < len(self.holds) and self.holds[self.i][0] <= t_ms:
            _, end, lane = self.holds[self.i]
            self.i += 1
            keys.append(int(lane))
            self.until[lane] = end
        return keys

    def down(self) -> np.ndarray:
        return self.t < self.until

    def drive(self) -> np.ndarray:
        return np.zeros(N_KEYS)


def record(player: Player, chart: Chart, seed: int | None = None) -> Recording:
    """Play ``chart`` with a silent controller and record the readout population."""
    return record_many(player, [chart], [seed])[0]


def record_many(player: Player, charts: list[Chart],
                seeds: list[int | None], hold_oracle: bool = False,
                project=None, chunk: int = 512) -> list[Recording]:
    """``record`` for several charts in one batched play (``Player.play_many``).
    The controller is silent, so the network never feeds back into the chart
    and every recording is exactly what ``record`` would make alone.  With
    ``hold_oracle`` the holds are played perfectly instead (``HoldOracle``);
    that is still fixed in advance, so it does not feed back either.

    ``project`` (e.g. a ``PopulationProjection.batch``) is applied to every
    ``chunk`` frames as they are recorded, so only the features are kept:
    48 float64 components instead of 1,303 float32 neurons is ~14x less memory.  BLAS sums a
    chunk in a different order from the whole recording, so the features
    differ from projecting afterwards at the 1e-13 level; opt-in for that
    reason, so every earlier result reproduces bit for bit."""
    idx = player.fly.readout.dn_local
    ts = [[] for _ in charts]
    xs = [[] for _ in charts]
    buf = [[] for _ in charts]

    def flush(j):
        if buf[j]:
            xs[j].append(project(np.asarray(buf[j], dtype=np.float32)))
            buf[j].clear()

    def tapper(j):
        def tap(r, env):
            ts[j].append(env.t)
            if project is None:
                xs[j].append(r[idx].copy())
            else:
                buf[j].append(r[idx].copy())
                if len(buf[j]) >= chunk:
                    flush(j)
        return tap

    silent = Controller(W=np.zeros((N_KEYS, N_KEYS)), b=np.full(N_KEYS, -1e9),
                        refractory_ms=player.controller.refractory_ms,
                        smooth_ms=player.controller.smooth_ms)
    saved = player.features
    player.features = None
    try:
        ctrls = ([HoldOracle(c) for c in charts] if hold_oracle
                 else [silent] * len(charts))
        player.play_many(charts, controllers=ctrls, seeds=seeds,
                         taps=[tapper(j) for j in range(len(charts))])
    finally:
        player.features = saved
    if project is not None:
        for j in range(len(charts)):
            flush(j)
        return [Recording(chart=c, t=np.asarray(t), X=np.vstack(x), dt=player.dt, projected=True)
                for c, t, x in zip(charts, ts, xs)]
    return [Recording(chart=c, t=np.asarray(t), X=np.asarray(x, dtype=np.float32),
                      dt=player.dt) for c, t, x in zip(charts, ts, xs)]


def smooth(Z: np.ndarray, dt: float, smooth_ms: float) -> np.ndarray:
    """The controller's leaky integrator, applied offline (same recursion, z_s(0) = 0)."""
    if smooth_ms <= 0:
        return Z.copy()
    a = dt / smooth_ms
    out = np.empty_like(Z)
    s = np.zeros(Z.shape[1])
    for i in range(len(Z)):
        s = s + a * (Z[i] - s)
        out[i] = s
    return out


def target(rec: Recording, lead_ms: float = 20.0, width_ms: float = 80.0,
           tail_lead_ms: float = 0.0) -> np.ndarray:
    """(T, 4) in {-1, +1}: +1 for ``width_ms`` from ``lead_ms`` before each
    note's hit time, in its lane.

    A **hold note** stays +1 through its body, to ``lead_ms + tail_lead_ms``
    before the tail.  The controller keeps a key down while its drive is above
    threshold, so a fixed-width pulse can only ever produce a fixed-length hold
    however long the note is -- which is why experiment 20 found holds scoring
    near zero even after the encoder was taught to draw them.

    ``tail_lead_ms`` exists because the drive does not fall the instant the
    target does: smoothing and the network's own dynamics carry it, and the
    measured result was that the fly released a median 126 ms *late* on every
    hold it took, losing all of them on the tail while its heads were nearly
    perfect.  Dropping the target early by that much pulls the release back
    onto the tail.  It is one declared number, swept like any other.

    An ordinary note has no tail and is unchanged, so a chart without holds
    fits exactly as before whatever ``tail_lead_ms`` is set to.
    """
    Y = -np.ones((len(rec.t), N_KEYS))
    for n in rec.chart.notes:
        start = n.hit_ms - lead_ms
        end = start + width_ms
        if n.is_hold:
            end = max(end, n.end_ms - lead_ms - tail_lead_ms)
        m = (rec.t >= start) & (rec.t <= end)
        Y[m, n.lane] = 1.0
    return Y


# -- the fit ---------------------------------------------------------------

def fit_ridge(Zs: np.ndarray, Y: np.ndarray, lam: float = 1e-2) -> tuple[np.ndarray, np.ndarray]:
    """Per-lane class-balanced ridge regression of ``Y`` on ``[Zs, 1]``.
    ``lam`` is relative to the mean feature power; the bias is not penalised."""
    T, k = Zs.shape
    X = np.column_stack([Zs, np.ones(T)])
    W = np.zeros((N_KEYS, k)); b = np.zeros(N_KEYS)
    reg = np.eye(k + 1); reg[-1, -1] = 0.0
    for lane in range(N_KEYS):
        y = Y[:, lane]
        pos = y > 0
        w = np.where(pos, 0.5 / max(pos.sum(), 1), 0.5 / max((~pos).sum(), 1))
        Xw = X * w[:, None]
        A = X.T @ Xw
        scale = np.trace(A[:k, :k]) / k
        coef = np.linalg.solve(A + lam * scale * reg, Xw.T @ y)
        W[lane] = coef[:k]; b[lane] = coef[k]
    return W, b


def replay_presses(u: np.ndarray, t: np.ndarray, refractory_ms: float) -> list[list[int]]:
    """The controller's crossing rule run offline on a drive trace: per frame,
    the lanes that fire."""
    T = len(t)
    out: list[list[int]] = [[] for _ in range(T)]
    for lane in range(u.shape[1]):
        v = u[:, lane]
        up = np.flatnonzero((v > 0) & (np.concatenate([[-np.inf], v[:-1]]) <= 0))
        last = -np.inf
        for i in up:
            if t[i] - last >= refractory_ms:
                out[i].append(lane); last = t[i]
    return out


def replay_down(u: np.ndarray) -> np.ndarray:
    """The controller's ``down`` run offline on a drive trace, for a
    controller without release levels: (T, 4) bool, which keys are held."""
    return u > 0


def replay_keys(u: np.ndarray, t: np.ndarray, refractory_ms: float,
                release: np.ndarray) -> tuple[list[list[int]], np.ndarray]:
    """``replay_presses`` and ``replay_down`` together for a controller with
    release levels: ``Controller.step`` and ``down`` for the "cross" trigger,
    frame by frame.  The re-press rule makes each lane depend on its own
    history, so the vectorised crossing search above no longer applies."""
    T, K = u.shape
    presses: list[list[int]] = [[] for _ in range(T)]
    down = np.empty((T, K), bool)
    u_prev = np.full(K, -np.inf)
    last = np.full(K, -np.inf)
    armed = np.zeros(K, bool)
    relifted = np.zeros(K, bool)
    for i in range(T):
        ui = u[i]
        ready = t[i] - last >= refractory_ms
        fire = ((ui > 0) & (u_prev <= 0) & ready) | (
            relifted & (ui > release) & (u_prev <= release) & ready)
        armed = (ui > 0) & (armed | (ui > release))
        relifted = (ui > 0) & (relifted | (armed & (ui < release))) & ~fire
        u_prev = ui
        for k in np.flatnonzero(fire):
            presses[i].append(int(k))
            last[k] = t[i]
        down[i] = (ui > 0) & ~(armed & (ui < release))
    return presses, down


def replay(rec: Recording, presses: list[list[int]],
           down: np.ndarray | None = None) -> PlayResult:
    """Run recorded press times through the judge (open-loop visuals).

    ``down`` (from ``replay_down``) releases held keys exactly as live play
    does.  Without it a hold is judged as never let go -- which is how every
    fit judged holds until the release level was added, so the fit could not
    see release timing at all.  A chart with no holds never holds a key, so
    for those the two are identical."""
    env = ManiaEnv(rec.chart, dt_ms=rec.dt)
    for i in range(len(rec.t)):
        for lane in presses[i]:
            env.press(lane)
        if down is not None:
            for k in range(N_KEYS):
                if env.hold[k] and not down[i, k]:
                    env.release(k)
        env.step()
    return env.result()


STRAY_PENALTY_FIT = 0.4


def lane_rewards(res: PlayResult, stray_penalty: float = STRAY_PENALTY_FIT,
                 max_bonus: float = 0.0) -> np.ndarray:
    """Per-lane accuracy minus stray penalty; lanes are independent in the judge.

    ``max_bonus`` credits a MAX that much above a 300 (0.0167 is osu!lazer's
    305/300).  Accuracy as scored here treats the two alike, so without it the
    per-lane timing search has no reason to aim for the 16 ms MAX window --
    and round 15's readout lands most hits just outside it."""
    out = np.zeros(N_KEYS)
    for lane in range(N_KEYS):
        idx = [i for i, n in enumerate(res.chart.notes) if n.lane == lane]
        if not idx:
            continue
        acc = sum(ACC_WEIGHT[res.judgments[i]] * (1.0 + max_bonus * (res.judgments[i] == "MAX"))
                  for i in idx) / (300.0 * len(idx))
        stray = sum(1 for p in res.presses if p.note is None and p.lane == lane)
        out[lane] = acc - stray_penalty * stray / len(idx)
    return out


@dataclass
class RidgeReadout:
    """Fit the controller by ridge regression on recorded play.

    ``features=None`` uses the four normalised channels (20 parameters, the
    same controller ``learn.ReadoutLearner`` trains); a ``PopulationProjection``
    gives 4k + 4.  ``fit()`` installs the controller on the player and returns
    a diagnostics dict.  ``record()`` once, then ``solve()`` for as many
    feature sets as wanted: the recordings are of the population, not the
    features.
    """
    player: Player
    features: Features | None = None
    lam: float = 1e-2
    stray_penalty: float = STRAY_PENALTY_FIT
    width_ms: float = 80.0
    leads: tuple = (40.0, 20.0, 0.0, -20.0, -40.0, -60.0)     # window start, ms before the hit
    stage: int = 3
    n_charts: int = 4
    n_notes: int = 24
    interval_ms: float = 600.0
    seed: int = 100
    # Optional ``((stage, interval_ms), ...)`` cycled over ``n_charts``, so one
    # readout can be fitted across several conditions at once.  Experiment 5
    # fitted on stage 3 at 600 ms only and then transferred, which cost it
    # chords (0.917 -> 0.506) and varied tempo (-> 0.608); its write-up named
    # "fit on stage 4 and see" as the cheap follow-up.  ``None`` keeps the
    # single-condition behaviour every earlier experiment used, unchanged.
    chart_specs: tuple | None = None
    # Ready-made charts (e.g. clips of real beatmaps) fitted alongside the
    # generated ones; empty by default, so every earlier fit is unchanged.
    extra_charts: tuple = ()
    # Project the activity onto ``features`` while recording (see
    # ``record_many``); needs a PopulationProjection set before ``record``.
    project_on_record: bool = False
    # Drop a hold's target this early; see ``target``.  130 ms is the swept
    # optimum and matches the 126 ms median overhold that motivated it, so it
    # is a measured correction rather than a tuned one.  It does nothing on a
    # chart with no hold notes, which is every chart used before experiment 20.
    tail_lead_ms: float = 130.0
    # Candidate hold-release levels (see ``Controller.release``); empty = off.
    release_levels: tuple = ()
    # Record holds as a perfect player would see them (``HoldOracle``).
    hold_oracle: bool = False
    # Extra credit for a MAX over a 300 in the timing search (``lane_rewards``).
    max_bonus: float = 0.0
    offsets: np.ndarray = field(default_factory=lambda: np.linspace(-2.0, 2.0, 41))
    recordings: list[Recording] = field(default_factory=list)

    def charts(self) -> list[Chart]:
        if self.chart_specs is None:
            return [stage_chart(self.stage, n_notes=self.n_notes, interval_ms=self.interval_ms,
                                seed=self.seed + c)
                    for c in range(self.n_charts)] + list(self.extra_charts)
        specs = list(self.chart_specs)
        out = []
        for c in range(self.n_charts):
            s = specs[c % len(specs)]
            # (stage, interval_ms), (stage, interval_ms, approach_ms), or
            # (stage, interval_ms, approach_ms, {more stage_chart arguments})
            kw = {} if len(s) < 3 else {"approach_ms": float(s[2])}
            if len(s) > 3:
                kw.update(s[3])
            out.append(stage_chart(int(s[0]), n_notes=self.n_notes,
                                   interval_ms=float(s[1]), seed=self.seed + c, **kw))
        return out + list(self.extra_charts)

    def record(self) -> None:
        """Record the training charts (the only expensive step; ~10 s per chart)."""
        charts = self.charts()
        project = None
        if self.project_on_record:
            if not isinstance(self.features, PopulationProjection):
                raise ValueError("project_on_record needs a PopulationProjection first")
            project = self.features.batch
        self.recordings = record_many(self.player, charts,
                                      [self.seed + i for i in range(len(charts))],
                                      hold_oracle=self.hold_oracle, project=project)

    def features_from_recordings(self, k: int, stride: int = 10) -> PopulationProjection:
        """Refit the population projection on the activity recorded on the
        training charts (every ``stride``-th frame) instead of the calibration
        ensemble, and install it.  Call between ``record`` and ``solve``."""
        if any(r.projected for r in self.recordings):
            raise ValueError("the recordings hold features, not activity")
        idx = (self.features.idx if isinstance(self.features, PopulationProjection)
               else self.player.fly.readout.dn_local)
        X = np.vstack([r.X[::stride] for r in self.recordings])
        self.features = PopulationProjection.from_activity(idx, X, k)
        return self.features

    def solve(self) -> dict:
        """Fit W, b and the per-lane (lead, offset) on the recordings; install
        the controller."""
        t0 = time.time()
        p = self.player
        feats = self.features or ChannelFeatures(p)
        sm = p.controller.smooth_ms; refr = p.controller.refractory_ms
        Zs = [smooth(r.X if r.projected else feats.batch(r.X), r.dt, sm)
              for r in self.recordings]
        Zall = np.vstack(Zs)
        k = Zall.shape[1]
        # one ridge fit per lead; per lane, replay every (lead, offset) through the judge
        table = np.zeros((len(self.leads), len(self.offsets), N_KEYS))
        fits = []
        corr = np.zeros((len(self.leads), N_KEYS))
        for i, lead in enumerate(self.leads):
            Y = [target(r, lead, self.width_ms, self.tail_lead_ms)
                 for r in self.recordings]
            W, b = fit_ridge(Zall, np.vstack(Y), self.lam)
            fits.append((W, b))
            U = Zall @ W.T + b
            Yall = np.vstack(Y)
            corr[i] = [np.corrcoef(U[:, l], Yall[:, l])[0, 1] for l in range(N_KEYS)]
            for j, d in enumerate(self.offsets):
                for rec, z in zip(self.recordings, Zs):
                    u = z @ W.T + b + d
                    table[i, j] += lane_rewards(replay(rec, replay_presses(u, rec.t, refr),
                                                       replay_down(u)),
                                                self.stray_penalty, self.max_bonus)
        table /= len(self.recordings)
        W = np.zeros((N_KEYS, k)); b = np.zeros(N_KEYS)
        chosen = []
        for lane in range(N_KEYS):
            i, j = np.unravel_index(np.argmax(table[:, :, lane]), table.shape[:2])
            Wi, bi = fits[i]
            W[lane] = Wi[lane]; b[lane] = bi[lane] + self.offsets[j]
            chosen.append({"lead_ms": float(self.leads[i]), "offset": float(self.offsets[j]),
                           "train_reward": float(table[i, j, lane]),
                           "train_corr": float(corr[i, lane])})
        # Release levels, per lane, chosen the same way as the offsets: replay
        # the training charts through the judge with W and b now fixed.  Level
        # 0 is the original release and wins every tie, so a diet with no
        # holds -- where releases are never judged -- keeps release None.
        release = None
        if len(self.release_levels):
            rel_table = np.zeros((len(self.release_levels), N_KEYS))
            for m, lvl in enumerate(self.release_levels):
                for rec, z in zip(self.recordings, Zs):
                    u = z @ W.T + b
                    pr, dn = replay_keys(u, rec.t, refr, np.full(N_KEYS, float(lvl)))
                    rel_table[m] += lane_rewards(replay(rec, pr, dn), self.stray_penalty,
                                                 self.max_bonus)
            best = np.asarray(self.release_levels, float)[rel_table.argmax(0)]
            for lane in range(N_KEYS):
                chosen[lane]["release"] = float(best[lane])
                chosen[lane]["train_reward_release"] = float(rel_table[:, lane].max()
                                                             / len(self.recordings))
            if np.any(best > 0):
                release = best
        ctrl = Controller(W=W, b=b, refractory_ms=refr, smooth_ms=sm, release=release)
        p.controller = ctrl
        p.features = None if self.features is None else feats
        return {"n_params": int(ctrl.n_params), "n_features": int(ctrl.n_features),
                "frames": int(len(Zall)), "lanes": chosen,
                "train_reward": float(np.mean([c["train_reward"] for c in chosen])),
                "seconds_solve": round(time.time() - t0, 1)}

    def fit(self) -> dict:
        t0 = time.time()
        self.record()
        t_rec = time.time() - t0
        out = self.solve()
        out["seconds_record"] = round(t_rec, 1)
        out["seconds"] = round(time.time() - t0, 1)
        return out
