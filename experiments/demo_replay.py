"""Export a replay of the current best fly playing two real beatmaps.

Builds the round-14 player (250 ms approach, 100 ms refractory, 20 ms
smoothing, k=32 population projection, hold oracle, release levels), plays the
"Easy" and "Hard" tuning difficulties with the trace recorded, and writes
``demo/replay_data.json`` for the browser replay in ``demo/index.html``.

Nothing here is a registered comparison: it is a demonstration of what the fly
plays, fitted on synthetic charts only, as in experiment 20.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPROACH_MS"] = "250"           # must precede the e20 import

import numpy as np

from flyosu import model as M, play as P, reservoir as R, mania
from flyosu.controller import calibration_states

A = 250.0
SPECS = ((4, 600.), (4, 450.), (4, 350.), (4, 250.), (4, 200.), (4, 150.), (4, 125.),
         (7, 600.), (7, 400.))
OUT_DIR = os.path.join(ROOT, "demo")
OUT = os.path.join(OUT_DIR, "replay_data.json")
MAX_PLAY_S = 120.0
WINDOW_S = 80.0
LEAD_MS = 1000.0
PICK = ("Easy", "Hard")


def build_player():
    t0 = time.time()
    fly = M.build(regime="play")
    player = P.Player.untrained(fly, theta=1.5, noise=0.03)
    player.controller.refractory_ms = 100.0
    player.controller.smooth_ms = 20.0
    rr = R.RidgeReadout(player, n_charts=36, n_notes=24, seed=100,
                        chart_specs=tuple((s, i, A) for s, i in SPECS),
                        release_levels=tuple(round(0.05 * i, 2) for i in range(21)),
                        hold_oracle=True)
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=32,
                                             states=calibration_states(fly, player.r0))
    rr.record()
    fit = rr.solve()
    print(f"fit done in {time.time() - t0:.0f} s  n_params={fit['n_params']}", flush=True)
    return player, fit, time.time() - t0


def trim(chart):
    """Keep a ~WINDOW_S stretch of a long chart, whole holds only, shifted so the
    first note lands LEAD_MS in."""
    notes = chart.notes
    if (chart.end_ms - chart.start_ms) / 1000.0 <= MAX_PLAY_S:
        lo, hi = chart.start_ms, chart.end_ms
    else:
        mid = 0.5 * (chart.start_ms + chart.end_ms)
        lo, hi = mid - 500.0 * WINDOW_S, mid + 500.0 * WINDOW_S
    keep = [n for n in notes if n.hit_ms >= lo and (n.end_ms if n.is_hold else n.hit_ms) <= hi]
    shift = LEAD_MS - keep[0].hit_ms
    new = [mania.Note(n.lane, n.hit_ms + shift, None if n.end_ms is None else n.end_ms + shift)
           for n in keep]
    return mania.Chart(new, approach_ms=chart.approach_ms, od=chart.od, name=chart.name)


def key_intervals(res, t, drive):
    """Key-down spans per lane: from each press until the drive falls to <= 0,
    or, for a press on a hold head, until the hold is released."""
    rel = {}
    for h in res.holds:
        n = res.chart.notes[h.note]
        rel[h.note] = n.end_ms + h.tail_error_ms if h.released else None
    out = [[] for _ in range(4)]
    for p in res.presses:
        i = int(np.searchsorted(t, p.t_ms))
        if p.note is not None and p.note in rel:
            end = rel[p.note]
            if end is None:            # never let go before the tail window closed
                n = res.chart.notes[p.note]
                end = n.end_ms + mania.windows(res.chart.od)["MISS"]
        else:
            j = i + 1
            while j < len(t) and drive[j, p.lane] > 0:
                j += 1
            end = float(t[min(j, len(t) - 1)])
        out[p.lane].append([round(float(p.t_ms), 1), round(float(max(end, p.t_ms + 8.0)), 1)])
    return out


def export(res, meta):
    ch = res.chart
    tr = res.trace
    t, drive = np.asarray(tr.t, float), np.asarray(tr.drive, float)
    dt = float(np.median(np.diff(t)))
    step = max(1, int(round(16.0 / dt)))
    holds = []
    for h in res.holds:
        n = ch.notes[h.note]
        holds.append({"note": h.note, "tail": round(n.end_ms, 1),
                      "release": round(n.end_ms + h.tail_error_ms, 1) if h.released else None,
                      "err": round(float(h.tail_error_ms), 1), "head": h.head,
                      "judgment": h.judgment, "released": bool(h.released)})
    return {
        "song": meta["song"], "difficulty": meta["version"], "od": ch.od,
        "approach_ms": ch.approach_ms, "events_per_s": meta["events_per_s"],
        "hold_frac": meta["hold_frac"], "trimmed": meta["trimmed"],
        "accuracy": round(res.accuracy, 4), "counts": res.counts,
        "windows": mania.windows(ch.od),
        "notes": [[n.lane, round(n.hit_ms, 1), None if n.end_ms is None else round(n.end_ms, 1)]
                  for n in ch.notes],
        "judgments": list(res.judgments),
        "presses": [[round(float(p.t_ms), 1), p.lane, p.note,
                     p.judgment, None if p.error_ms is None else round(float(p.error_ms), 1)]
                    for p in res.presses],
        "holds": holds,
        "keys": key_intervals(res, t, drive),
        "trace": {"t0": round(float(t[0]), 1), "dt": round(dt * step, 3),
                  "drive": np.round(drive[::step], 3).tolist()},
    }


def main():
    from experiments import e20_beatmaps as E20
    cs = {c["version"]: c for c in E20.charts()}
    print("difficulties:", {k: v["events_per_s"] for k, v in cs.items()}, flush=True)
    player, fit, fit_s = build_player()
    maps = []
    for name in PICK:
        c = cs[name]
        chart = trim(c["chart"])
        meta = dict(c, trimmed=len(chart) != len(c["chart"]))
        res = player.play(chart, record=True, seed=4242)
        print(f"{name}: {len(chart)} notes  acc={res.accuracy:.4f}  {res.counts}", flush=True)
        maps.append(export(res, meta))
        del res
    os.makedirs(OUT_DIR, exist_ok=True)
    data = {"about": {"n_params": int(fit["n_params"]), "neurons": 19367,
                      "synapses": 729558, "photoreceptors": 8452,
                      "fit_seconds": round(fit_s), "refractory_ms": 100.0,
                      "smooth_ms": 20.0, "dt_ms": 2.0},
            "maps": maps}
    with open(OUT, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"wrote {OUT}  {os.path.getsize(OUT) / 1e6:.2f} MB", flush=True)
    for m in maps:
        print(f"  {m['difficulty']}: accuracy {m['accuracy']:.4f}", flush=True)


if __name__ == "__main__":
    main()
