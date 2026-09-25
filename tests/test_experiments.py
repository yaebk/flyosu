"""
Checks for the experiment scripts' own logic: the replay export's song
windows and file split, and experiment 21's map loading and freeze guard.
None of these build the network.

    python -m tests.test_experiments      # ~20 s, parses the maps in osumaps/
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

os.environ.setdefault("DIET", "fast_sm20_k48")      # before any e20 import, as e21 needs
os.environ.setdefault("APPROACH_MS", "250")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))

from flyosu import mania  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        FAILED.append(name)


def _raises(fn, exc=Exception):
    try:
        fn()
    except exc:
        return True
    return False


def test_song_window():
    import demo_replay as D
    print("replay export: song windows")
    W = D.PLAY_S * 1000.0
    # A has notes every second from 0 to 200 s; B only between 120 and 150 s.
    a = mania.Chart([mania.Note(i % 4, 1000.0 * i) for i in range(201)])
    b = mania.Chart([mania.Note(i % 4, 120000.0 + 500.0 * i) for i in range(61)])
    s = D.song_window([a, b])
    share = lambda c, x: sum(x <= n.hit_ms < x + W for n in c.notes) / len(c)
    best = max(min(share(a, x), share(b, x)) for x in range(0, 200001, 500))
    check("the shared window gives no difficulty less than the best achievable share",
          abs(min(share(a, s), share(b, s)) - best) < 1e-12, f"start {s / 1000:.1f} s")
    check("so the sparse difficulty is not left thin", share(b, s) >= share(a, s))
    check("and starts on the 500 ms grid from the first note", (s - 0.0) % 500.0 == 0.0)
    check("a single chart shorter than the window starts at its first note",
          D.song_window([mania.Chart([mania.Note(0, 3000.0), mania.Note(1, 9000.0)])]) == 3000.0)


def test_trim():
    import demo_replay as D
    print("replay export: trim")
    c = mania.Chart([mania.Note(0, 5000.0), mania.Note(1, 70000.0, end_ms=90000.0),
                     mania.Note(2, 71000.0), mania.Note(3, 200000.0)])
    new, w = D.trim(c, 60000.0)
    check("keeps exactly the notes whose head is in the window", len(new) == 2 and w["n_notes"] == 2)
    check("shifts the first kept note to LEAD_MS", new.notes[0].hit_ms == D.LEAD_MS)
    hold = [n for n in new.notes if n.is_hold][0]
    check("keeps a hold whole even past the window", hold.end_ms - hold.hit_ms == 20000.0)
    check("records the window start and clipping in map time",
          w["raw_start_ms"] == 60000.0 and w["raw_first_ms"] == 70000.0 and w["clipped"])


def test_split():
    import demo_replay as D
    print("replay export: index and per-replay files")
    heavy = {"notes": [[0, 1.0, None]], "judgments": ["MAX"], "presses": [], "holds": [],
             "keys": [[], [], [], []], "trace": {"t0": 0.0, "dt": 16.0, "drive": [[0, 0, 0, 0]]}}
    data = {"neurons_view": {"x": [1]}, "about": {"n_params": 200},
            "maps": [dict(heavy, key="song_a", accuracy=0.9, stars=2.5),
                     dict(heavy, key="song_b", accuracy=0.8, stars=4.1)]}
    old = (D.OUT_DIR, D.INDEX)
    with tempfile.TemporaryDirectory() as tmp:
        D.OUT_DIR, D.INDEX = tmp, os.path.join(tmp, "replays.json")
        try:
            D.split(data)
            with open(D.INDEX) as fh:
                idx = json.load(fh)
            with open(os.path.join(tmp, "replays", "song_b.json")) as fh:
                one = json.load(fh)
        finally:
            D.OUT_DIR, D.INDEX = old
    check("the index lists every replay without its per-frame data",
          [m["key"] for m in idx["maps"]] == ["song_a", "song_b"]
          and not any(k in m for m in idx["maps"] for k in heavy))
    check("the index keeps what the list shows", idx["maps"][1]["stars"] == 4.1
          and idx["maps"][1]["accuracy"] == 0.8 and idx["about"]["n_params"] == 200)
    check("each replay file holds exactly the per-frame data", set(one) == set(heavy))


def test_replay_selection():
    import demo_replay as D
    print("replay export: every 4K difficulty, with a star rating")
    chosen = D.select_charts()
    check("all 47 4K difficulties are selected", len(chosen) == 47, str(len(chosen)))
    check("every one has an official star rating", all(isinstance(o["stars"], float) for o in chosen))
    check("tuning songs are marked tuning, the rest held-out",
          all((o["set"] == "tuning") == (o["sid"] in ("2298007", "2543258", "2600298")) for o in chosen))


def test_e21_maps():
    import e20_beatmaps as B
    import e20_realfit as RF
    import e21_trained_wiring as X
    print("experiment 21: training clips and held-out maps")
    X._MAPS.clear()
    before = B.MAP_SET
    train, held = X.load_maps()
    t2, _ = RF.pools()
    ref = [c for _, ev in t2 for c in RF.pick(ev, X.RECIPE["per_map"])]
    check("the training clips are round 23's 102", len(train) == 102
          and [c.notes for c in train] == [c.notes for c in ref])
    check("the held-out set is the 30 difficulties with no tuning song", len(held) == 30
          and not any(r["song"].startswith(B.TUNING_SONGS) for r in held))
    check("loading the maps leaves the run's map set alone", B.MAP_SET == before)
    B.MAP_SET = "holdout"             # a run started on the held-out maps ...
    try:
        t4, _ = RF.pools()
    finally:
        B.MAP_SET = before
    check("... still draws its training clips from tuning songs only",
          len(t4) == 17 and all(r["song"].startswith(B.TUNING_SONGS) for r, _ in t4))
    check("an unknown map set is refused", _raises(lambda: B.charts("tuning"), ValueError))
    t3, h3 = X.load_maps()
    check("a second network in the same shard reuses the same maps", t3 is train and h3 is held)


def test_e21_freeze():
    import e21_trained_wiring as X
    print("experiment 21: the freeze guard")
    old = X.PATH
    with tempfile.TemporaryDirectory() as tmp:
        X.PATH = os.path.join(tmp, "e21.json")
        try:
            check("the real network is refused with no controls", _raises(X.run_real, SystemExit))
            runs = [{"label": f"rewired #{s}"} for s in range(1, X.N_CONTROLS)]
            with open(X.PATH, "w") as fh:
                json.dump({"runs": runs}, fh)
            check("and with one control short", _raises(X.run_real, SystemExit))
            runs += [{"label": f"rewired #{X.N_CONTROLS}"}, {"label": "real connectome"}]
            with open(X.PATH, "w") as fh:
                json.dump({"runs": runs}, fh)
            check("and a second time once it is measured", _raises(X.run_real, SystemExit))
        finally:
            X.PATH = old


def main():
    test_song_window()
    test_trim()
    test_split()
    test_replay_selection()
    test_e21_maps()
    test_e21_freeze()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: " + ", ".join(FAILED))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
