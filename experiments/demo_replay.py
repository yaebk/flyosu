"""Export a replay of the current best fly playing two real beatmaps.

Builds the round-14 player (250 ms approach, 100 ms refractory, 20 ms
smoothing, k=32 population projection, hold oracle, release levels), plays the
"Easy" and "Hard" tuning difficulties with the trace recorded, and writes
``demo/replay_data.json`` for the browser replay in ``demo/index.html``.

Nothing here is a registered comparison: it is a demonstration of what the fly
plays, fitted on synthetic charts only, as in experiment 20.
"""
import base64
import gzip
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
K = 48                      # population-projection components (round 14's best)
# brain view: neurons per class (small classes are kept whole)
SAMPLE = {"photoreceptor": 350, "sensory": 50, "optic": 450, "visual_projection": 250,
          "visual_centrifugal": 200, "central": 300, "descending": 450, "ascending": 200}
SAMPLE_SEED = 7
FLOOR = 0.02                # min per-neuron scale (firing-rate units)
QMAX = 15                   # 31 levels is plenty for dot brightness, and compresses well
DEADZONE = 0.08             # |change| under this fraction of a neuron's range is stored as 0
BRAIN_EVERY = 8             # frames (2 ms each) -> 16 ms


def build_player():
    t0 = time.time()
    fly = M.build(regime="play")
    sample_neurons(fly)                  # fail fast before the long fit
    player = P.Player.untrained(fly, theta=1.5, noise=0.03)
    player.controller.refractory_ms = 100.0
    player.controller.smooth_ms = 20.0
    rr = R.RidgeReadout(player, n_charts=36, n_notes=24, seed=100,
                        chart_specs=tuple((s, i, A) for s, i in SPECS),
                        release_levels=tuple(round(0.05 * i, 2) for i in range(21)),
                        hold_oracle=True)
    rr.features = R.PopulationProjection.fit(fly, player.r0, k=K,
                                             states=calibration_states(fly, player.r0))
    rr.record()
    fit = rr.solve()
    print(f"fit done in {time.time() - t0:.0f} s  n_params={fit['n_params']}", flush=True)
    return fly, player, fit, time.time() - t0


def sample_neurons(fly):
    """A fixed, class-stratified subset of ~2,200 neurons for the brain view.
    Photoreceptors are taken from the input population; every other class from
    ``super_class``.  Small classes are kept whole."""
    ann = fly.cx.ann.iloc[fly.node_ids]
    cls = ann["super_class"].astype(str).to_numpy()
    ph = np.zeros(len(cls), bool)
    ph[np.asarray(fly.ph_local)] = True
    cls = np.where(ph, "photoreceptor", cls)
    readout = np.zeros(len(cls), bool)
    readout[np.asarray(fly.readout.dn_local)] = True
    rng = np.random.default_rng(SAMPLE_SEED)
    pick = []
    for c, n in SAMPLE.items():
        idx = np.flatnonzero(cls == c)
        pick.append(np.sort(rng.choice(idx, size=min(n, len(idx)), replace=False)))
    pick = np.concatenate(pick)
    x = ann["pos_x"].to_numpy(float)[pick]
    y = ann["pos_y"].to_numpy(float)[pick]
    classes = list(SAMPLE)
    neurons = {"classes": classes,
               "x": np.round(x / 1000.0, 1).tolist(),        # FlyWire pos / 1000; only shape matters
               "y": np.round(y / 1000.0, 1).tolist(),
               "cls": [classes.index(c) for c in cls[pick]],
               "readout": readout[pick].astype(int).tolist()}
    print("sampled", {c: int((cls[pick] == c).sum()) for c in classes},
          "readout", int(readout[pick].sum()), flush=True)
    return pick, neurons


def encode_brain(frames, r0, pick, path):
    """Change from rest, scaled per neuron by its own 99th-percentile |change|
    (floored so near-silent neurons stay dark), clipped to [-1, 1], with a small
    dead zone, quantized to int8 in [-QMAX, QMAX].  Stored neuron-major (each
    neuron's time series contiguous) and gzip-compressed: that layout is about
    half the size of frames x neurons for the same data."""
    d = np.asarray(frames, np.float32) - r0[pick][None, :].astype(np.float32)
    p99 = np.percentile(np.abs(d), 99, axis=0)
    scale = np.maximum(p99, FLOOR)
    u = np.clip(d / scale, -1.0, 1.0)
    q = np.where(np.abs(u) < DEADZONE, 0, np.round(u * QMAX)).astype(np.int8)
    # gzip, then base64 text: artifact pages serve .txt but not raw .bin files
    blob = gzip.compress(np.ascontiguousarray(q.T).tobytes(), compresslevel=9, mtime=0)
    with open(path, "w", encoding="ascii") as fh:
        fh.write(base64.b64encode(blob).decode("ascii"))
    print(f"  brain {q.shape}  p99|d| quantiles 10/50/90%: "
          f"{np.round(np.percentile(p99, [10, 50, 90]), 4).tolist()}  "
          f"floored {int((p99 < FLOOR).sum())}  -> {os.path.getsize(path) / 1e6:.2f} MB", flush=True)
    return {"file": os.path.basename(path), "frames": int(q.shape[0]),
            "neurons": int(q.shape[1]), "qmax": QMAX, "gzip": True, "base64": True,
            "layout": "neuron-major"}


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
    fly, player, fit, fit_s = build_player()
    pick, neurons = sample_neurons(fly)
    os.makedirs(OUT_DIR, exist_ok=True)
    maps = []
    for name in PICK:
        c = cs[name]
        chart = trim(c["chart"])
        meta = dict(c, trimmed=len(chart) != len(c["chart"]))
        frames, count = [], [0]

        def tap(r, env):
            if count[0] % BRAIN_EVERY == 0:
                frames.append(r[pick].astype(np.float32))
            count[0] += 1

        res = player.play(chart, record=True, seed=4242, tap=tap)
        print(f"{name}: {len(chart)} notes  acc={res.accuracy:.4f}  {res.counts}", flush=True)
        m = export(res, meta)
        m["brain"] = encode_brain(frames, np.asarray(player.r0), pick,
                                  os.path.join(OUT_DIR, f"brain_{name.lower()}.b64.txt"))
        m["brain"].update(t0=m["trace"]["t0"], dt=round(2.0 * BRAIN_EVERY, 3))
        maps.append(m)
        del res, frames
    data = {"neurons_view": neurons,
            "about": {"n_params": int(fit["n_params"]), "neurons": 19367, "k": K,
                      "synapses": 729558, "photoreceptors": 8452,
                      "fit_seconds": round(fit_s), "refractory_ms": 100.0,
                      "smooth_ms": 20.0, "dt_ms": 2.0},
            "maps": maps}
    with open(OUT, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"wrote {OUT}  {os.path.getsize(OUT) / 1e6:.2f} MB", flush=True)
    tot = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR) if f.endswith((".json", ".txt")))
    print(f"demo data total {tot / 1e6:.2f} MB", flush=True)
    for m in maps:
        print(f"  {m['difficulty']}: accuracy {m['accuracy']:.4f}", flush=True)


if __name__ == "__main__":
    main()
