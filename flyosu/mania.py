"""
A minimal 4-key osu!mania: notes, charts, a clock, and the judge.

Steps 5 and 8 of the plan.  Nothing here knows about the fly; the environment
only answers two questions -- "what is on screen at time t?" and "how good was
that key press?" -- and keeps score.

Timing model.  A note is defined by the lane it falls in and the moment it
should be hit.  It becomes visible ``approach_ms`` before that moment at the top
of the playfield and reaches the judgment line exactly at ``hit_ms``.  Progress
is 0 at spawn and 1 at the judgment line; a missed note keeps sliding past the
line until the miss window closes and it is retired.

Judgment windows are osu!mania's (stable client, per-note, in ms, OD = overall
difficulty), applied symmetrically around ``hit_ms``:

    MAX   16
    300   64  - 3 OD
    200   97  - 3 OD
    100   127 - 3 OD
    50    151 - 3 OD
    MISS  188 - 3 OD      (a press inside this window still consumes the note)

A press with no note in its lane within the miss window is a stray press.  It
costs nothing in osu!mania and costs nothing here, but it is counted, because a
controller that mashes every key would otherwise look competent.

Accuracy is osu!mania's:  (300 MAX + 300 x300 + 200 x200 + 100 x100 + 50 x50)
/ (300 total).

Hold notes are scored on both ends.  ``press`` puts the key down and ``release``
lifts it; the tail is judged on the release error against a window scaled by
``HOLD_TAIL_LENIENCY`` (1.5x, the stable figure), and the note earns the *worse*
of its head and tail.  Overholding past the tail window misses, as does letting
go early, so a key that is pressed and never released scores MISS rather than
keeping its head's judgment.  One judgment per note either way, which is what
lets accuracy stay a mean over notes.  Charts without holds are unaffected in
every respect.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

KEYS = ("D", "F", "J", "K")
N_LANES = 4

JUDGMENTS = ("MAX", "300", "200", "100", "50", "MISS")
ACC_WEIGHT = {"MAX": 300, "300": 300, "200": 200, "100": 100, "50": 50, "MISS": 0}

# osu!mania stable gives a hold note's tail a more forgiving window than a
# normal note.  1.5x is the stable figure.
HOLD_TAIL_LENIENCY = 1.5


def worse(a: str, b: str) -> str:
    """The worse of two judgments.  ``JUDGMENTS`` is ordered best to worst."""
    return a if JUDGMENTS.index(a) >= JUDGMENTS.index(b) else b


def windows(od: float) -> dict[str, float]:
    """Half-width of each judgment window in ms for the given OD."""
    return {"MAX": 16.0, "300": 64.0 - 3 * od, "200": 97.0 - 3 * od,
            "100": 127.0 - 3 * od, "50": 151.0 - 3 * od, "MISS": 188.0 - 3 * od}


def judge(error_ms: float, od: float) -> str:
    """Judgment for a press ``error_ms`` away from a note's hit time."""
    e = abs(error_ms)
    for name, half in windows(od).items():
        if e <= half:
            return name
    return "MISS"


# ---------------------------------------------------------------------------
# chart
# ---------------------------------------------------------------------------

@dataclass
class Note:
    lane: int
    hit_ms: float
    end_ms: float | None = None     # hold note tail; judged on the head only

    @property
    def is_hold(self) -> bool:
        return self.end_ms is not None and self.end_ms > self.hit_ms


@dataclass
class Chart:
    notes: list[Note]
    approach_ms: float = 800.0      # spawn-to-judgment travel time
    od: float = 8.0
    name: str = ""

    def __post_init__(self):
        self.notes = sorted(self.notes, key=lambda n: (n.hit_ms, n.lane))

    def __len__(self) -> int:
        return len(self.notes)

    @property
    def start_ms(self) -> float:
        return self.notes[0].hit_ms if self.notes else 0.0

    @property
    def end_ms(self) -> float:
        """When the last thing on the chart happens -- a hold note's *tail*, not
        its head, or the clock would stop before the tail could be released."""
        if not self.notes:
            return 0.0
        return max((n.end_ms if n.is_hold else n.hit_ms) for n in self.notes)

    def lanes(self) -> np.ndarray:
        return np.array([n.lane for n in self.notes], dtype=np.int64)

    def times(self) -> np.ndarray:
        return np.array([n.hit_ms for n in self.notes], dtype=np.float64)

    def describe(self) -> str:
        if not self.notes:
            return "empty chart"
        lanes = np.bincount(self.lanes(), minlength=N_LANES)
        t = self.times()
        gaps = np.diff(np.unique(t))
        chords = int((np.bincount(np.unique(t, return_inverse=True)[1]) > 1).sum())
        return (f"{self.name or 'chart'}: {len(self):,} notes over "
                f"{(self.end_ms - self.start_ms) / 1000:.1f} s, lanes "
                + "/".join(str(int(c)) for c in lanes)
                + f", median gap {np.median(gaps) if len(gaps) else 0:.0f} ms, "
                f"{chords} chords, approach {self.approach_ms:.0f} ms, OD {self.od:g}")


# -- generators for the curriculum -----------------------------------------

STAGES = {
    1: "one lane, regular",
    2: "four lanes in sequence, regular",
    3: "random lanes, regular",
    4: "random lanes with chords",
    5: "random lanes, varied intervals",
    6: "random lanes with jacks",
    7: "random lanes with hold notes",
}


def stage_chart(stage: int, n_notes: int = 24, interval_ms: float = 600.0,
                approach_ms: float = 800.0, od: float = 8.0, seed: int = 0,
                lane: int = 1, chord_p: float = 0.3, lead_ms: float = 1000.0,
                jack_p: float = 0.4, hold_p: float = 0.4,
                hold_frac: float = 0.8) -> Chart:
    """One chart from the staged curriculum (see ``STAGES``).

    ``lane`` is the lane used by stage 1.  ``lead_ms`` is the silence before the
    first note, so the fly starts from a blank field.
    """
    rng = np.random.default_rng(seed)
    t = lead_ms
    notes: list[Note] = []
    if stage == 1:
        for _ in range(n_notes):
            notes.append(Note(lane, t)); t += interval_ms
    elif stage == 2:
        for i in range(n_notes):
            notes.append(Note(i % N_LANES, t)); t += interval_ms
    elif stage == 3:
        for _ in range(n_notes):
            notes.append(Note(int(rng.integers(N_LANES)), t)); t += interval_ms
    elif stage == 4:
        while len(notes) < n_notes:
            k = 2 if rng.random() < chord_p and len(notes) + 2 <= n_notes else 1
            for ln in rng.choice(N_LANES, size=k, replace=False):
                notes.append(Note(int(ln), t))
            t += interval_ms
    elif stage == 5:
        for _ in range(n_notes):
            notes.append(Note(int(rng.integers(N_LANES)), t))
            t += float(rng.uniform(0.5, 1.5) * interval_ms)
    elif stage == 6:
        # Jacks: the same lane twice or more in a row.  Stages 1-5 spread notes
        # over four lanes at a uniform interval, so two notes in one lane are
        # never closer than the interval and the controller's refractory has
        # never had the chance to bind -- experiment 18 found it makes no
        # difference between 150 ms and 50 ms for exactly that reason.  Real
        # beatmaps are full of this pattern, and it asks a different question:
        # not whether the four channels can be told apart, but whether *one*
        # channel can resolve two notes in quick succession.
        prev = int(rng.integers(N_LANES))
        for i in range(n_notes):
            if i and rng.random() < jack_p:
                ln = prev
            else:
                ln = int(rng.integers(N_LANES))
            notes.append(Note(ln, t)); prev = ln; t += interval_ms
    elif stage == 7:
        # Hold notes.  The tail sits ``hold_frac`` of the interval after the
        # head, so it always closes before the next note could land in that
        # lane and no two holds in one lane can overlap.  Holds are the one
        # thing a real beatmap has that this curriculum never did, and they ask
        # the controller a question nothing else does: not when to press, but
        # how long to stay pressed.
        for _ in range(n_notes):
            ln = int(rng.integers(N_LANES))
            end = t + hold_frac * interval_ms if rng.random() < hold_p else None
            notes.append(Note(ln, t, end_ms=end)); t += interval_ms
    else:
        raise ValueError(f"unknown stage {stage}; known: {sorted(STAGES)}")
    return Chart(notes, approach_ms=approach_ms, od=od,
                 name=f"stage {stage} ({STAGES[stage]}) seed {seed}")


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------

@dataclass
class Press:
    t_ms: float
    lane: int
    note: int | None            # index into chart.notes, None for a stray press
    error_ms: float | None
    judgment: str | None


@dataclass
class HoldRelease:
    """How one hold note ended: the head it earned, the release error against
    its tail, and the combined judgment.  ``released`` is False when the key was
    still down as the tail window closed."""
    note: int
    head: str
    tail_error_ms: float
    judgment: str
    released: bool


@dataclass
class PlayResult:
    chart: Chart
    judgments: list[str]        # one per note, in chart order
    presses: list[Press]
    finished: bool = True
    holds: list = field(default_factory=list)   # HoldRelease, one per held note

    @property
    def counts(self) -> dict[str, int]:
        return {j: sum(1 for x in self.judgments if x == j) for j in JUDGMENTS}

    @property
    def accuracy(self) -> float:
        if not self.judgments:
            return 0.0
        return sum(ACC_WEIGHT[j] for j in self.judgments) / (300.0 * len(self.judgments))

    @property
    def hit_rate(self) -> float:
        """Fraction of notes hit at all (anything but MISS)."""
        if not self.judgments:
            return 0.0
        return sum(1 for j in self.judgments if j != "MISS") / len(self.judgments)

    @property
    def errors_ms(self) -> np.ndarray:
        """Signed timing error of every press that landed on a note (+ = late)."""
        return np.array([p.error_ms for p in self.presses if p.note is not None],
                        dtype=np.float64)

    @property
    def n_stray(self) -> int:
        return sum(1 for p in self.presses if p.note is None)

    @property
    def lane_confusion(self) -> np.ndarray:
        """(true lane, pressed lane) counts for every press near a note in *any*
        lane -- shows whether a wrong key was pressed for a note that was there."""
        M = np.zeros((N_LANES, N_LANES), dtype=int)
        half = windows(self.chart.od)["MISS"]
        for p in self.presses:
            if p.note is not None:
                M[self.chart.notes[p.note].lane, p.lane] += 1
                continue
            near = [n for n in self.chart.notes if abs(n.hit_ms - p.t_ms) <= half]
            if near:
                M[min(near, key=lambda n: abs(n.hit_ms - p.t_ms)).lane, p.lane] += 1
        return M

    def summary(self) -> str:
        c = self.counts
        e = self.errors_ms
        return (f"acc {self.accuracy:.3f}  hit {self.hit_rate:.3f}  "
                + " ".join(f"{k}:{c[k]}" for k in JUDGMENTS)
                + f"  stray {self.n_stray}"
                + (f"  err {e.mean():+.0f}+-{e.std():.0f} ms" if len(e) else ""))


class ManiaEnv:
    """The playfield clock.  ``step()`` advances time; ``visible()`` lists notes
    on screen; ``press(lane)`` judges a key press at the current time."""

    def __init__(self, chart: Chart, dt_ms: float = 5.0, tail_ms: float = 400.0):
        self.chart = chart
        self.dt = float(dt_ms)
        self.tail = float(tail_ms)
        self.win = windows(chart.od)
        self.reset()

    def reset(self) -> None:
        self.t = min(0.0, self.chart.start_ms - self.chart.approach_ms - 200.0)
        self.judged: list[str | None] = [None] * len(self.chart)
        self.presses: list[Press] = []
        self._cursor = 0          # first note that could still be on screen
        self.hold: np.ndarray = np.zeros(N_LANES, dtype=bool)   # key currently down
        # Index of the hold note each lane is currently holding, and the head
        # judgment it earned.  A held note has a *provisional* entry in
        # ``judged`` -- the head's -- which ``release`` replaces with the
        # combined one.  That keeps one judgment per note, so accuracy stays a
        # mean over notes and every existing metric keeps its meaning.
        self.holding: list[int | None] = [None] * N_LANES
        self._head: dict[int, str] = {}
        self.hold_log: list[HoldRelease] = []

    @property
    def done(self) -> bool:
        return self.t > self.chart.end_ms + self.win["MISS"] + self.tail

    @property
    def end_ms(self) -> float:
        return self.chart.end_ms + self.win["MISS"] + self.tail

    def visible(self) -> list[tuple[int, float, int, float | None]]:
        """``(lane, progress, note_index, tail_progress)`` for every note on screen.

        progress = 0 at spawn, 1 at the judgment line, >1 sliding past it.
        A judged note is off screen -- except a hold note currently being held,
        whose body is still on the playfield and still has to be let go of.

        ``tail_progress`` is the same measure for a hold note's tail and is
        ``None`` for an ordinary note, so a chart without holds produces exactly
        the tuples this returned before hold notes existed (plus a trailing
        ``None``, which every consumer ignores).
        """
        out = []
        a = self.chart.approach_ms
        # A held note's head is judged, so the scan below skips it and the
        # cursor has usually moved past it; emit it explicitly or the fly would
        # lose sight of the body at the instant it pressed.
        for i in self.holding:
            if i is not None:
                n = self.chart.notes[i]
                out.append((n.lane, (self.t - (n.hit_ms - a)) / a, i,
                            (self.t - (n.end_ms - a)) / a))
        for i in range(self._cursor, len(self.chart)):
            n = self.chart.notes[i]
            if n.hit_ms - a > self.t:
                break
            if self.judged[i] is not None:
                continue
            out.append((n.lane, (self.t - (n.hit_ms - a)) / a, i,
                        ((self.t - (n.end_ms - a)) / a) if n.is_hold else None))
        return out

    def press(self, lane: int) -> Press:
        """Judge a press in ``lane`` at the current time (earliest live note
        in the lane within the miss window; otherwise a stray press)."""
        half = self.win["MISS"]
        best = None
        for i in range(self._cursor, len(self.chart)):
            n = self.chart.notes[i]
            if n.hit_ms - self.t > half:
                break
            if n.lane != lane or self.judged[i] is not None:
                continue
            if abs(n.hit_ms - self.t) <= half:
                best = i
                break
        if best is None:
            p = Press(self.t, lane, None, None, None)
        else:
            err = self.t - self.chart.notes[best].hit_ms
            j = judge(err, self.chart.od)
            self.judged[best] = j
            p = Press(self.t, lane, best, err, j)
            if self.chart.notes[best].is_hold:
                # Provisional: ``judged[best]`` now holds the head's judgment and
                # is replaced when the key comes back up.
                self.holding[lane] = best
                self._head[best] = j
        self.hold[lane] = True
        self.presses.append(p)
        return p

    def release(self, lane: int) -> str | None:
        """Lift the key in ``lane``.  Finalises a hold note if one is being held.

        A chart with no hold notes never reaches the interesting branch, so this
        is a no-op for every result recorded before hold notes existed.
        """
        self.hold[lane] = False
        i = self.holding[lane]
        if i is None:
            return None
        self.holding[lane] = None
        return self._finish_hold(i, self.t - self.chart.notes[i].end_ms)

    def _finish_hold(self, i: int, err_ms: float, released: bool = True) -> str:
        """Combine a hold note's head and tail into its one judgment.

        The tail is judged on the release error against a window scaled by
        ``HOLD_TAIL_LENIENCY``, and the note scores the *worse* of head and
        tail -- so a clean press followed by an early release is penalised, and
        a hold cannot rescue a badly-timed head.
        """
        od = self.chart.od
        scaled = {k: v * HOLD_TAIL_LENIENCY for k, v in windows(od).items()}
        e = abs(err_ms)
        tail = next((name for name, half in scaled.items() if e <= half), "MISS")
        head = self._head.get(i, "MISS")
        j = worse(head, tail)
        self.judged[i] = j
        self.hold_log.append(HoldRelease(i, head, float(err_ms), j, released))
        return j

    def step(self) -> None:
        """Advance the clock by ``dt`` and retire notes whose miss window closed."""
        self.t += self.dt
        half = self.win["MISS"]
        # A key still down well past its hold note's tail has overheld it: the
        # tail misses.  Without this a never-released key would leave the note
        # on its provisional head judgment and quietly score better than it
        # played -- the same shape of bug as the press-guard fallback.
        late = half * HOLD_TAIL_LENIENCY
        for lane, i in enumerate(self.holding):
            if i is not None and self.t - self.chart.notes[i].end_ms > late:
                self.holding[lane] = None
                self._finish_hold(i, self.t - self.chart.notes[i].end_ms, released=False)
        while self._cursor < len(self.chart):
            i = self._cursor
            n = self.chart.notes[i]
            if self.judged[i] is None:
                if self.t - n.hit_ms > half:
                    self.judged[i] = "MISS"
                else:
                    break
            self._cursor += 1

    def result(self) -> PlayResult:
        j = [x if x is not None else "MISS" for x in self.judged]
        return PlayResult(self.chart, j, list(self.presses), finished=self.done,
                          holds=list(self.hold_log))


if __name__ == "__main__":
    for s in STAGES:
        print(stage_chart(s, seed=1).describe())
    c = stage_chart(3, seed=1)
    env = ManiaEnv(c)
    # an oracle that presses every note exactly on time
    while not env.done:
        for n in c.notes:
            if abs(n.hit_ms - env.t) < env.dt / 2:
                env.press(n.lane)
        env.step()
    print("oracle:", env.result().summary())
