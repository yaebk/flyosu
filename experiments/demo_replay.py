"""Export a replay of the current best fly playing six real beatmap clips.

Builds round 15's player (250 ms approach, 100 ms refractory, 20 ms smoothing,
k=48 population projection, hold oracle, release levels; 196 parameters),
plays the six maps in ``SELECT`` with the trace and a sample of neuron activity
recorded, and writes ``demo/replay_data.json`` and the per-map brain files for
the browser replay in ``demo/index.html``; ``audio`` extracts and aligns the
songs without running the model.

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

from flyosu import mania        # light: the model is imported only by the fit

SONG_OSZ = os.path.join(ROOT, "osumaps",
                        "2600298 Metal Scar Radio - Mirairo Rider (Japanese Ver.) (Game Ver.).osz")

A = 250.0
SPECS = ((4, 600.), (4, 450.), (4, 350.), (4, 250.), (4, 200.), (4, 150.), (4, 125.),
         (7, 600.), (7, 400.))
OUT_DIR = os.path.join(ROOT, "demo")
OUT = os.path.join(OUT_DIR, "replay_data.json")
LEAD_MS = 1000.0
PLAY_S = 90.0              # at most this much play per map
AUDIO_PAD_S = 2.0          # audio kept either side of the window when a song is trimmed
# (page key, map set, song id, difficulty); map set "tune" = the tuning songs
SELECT = (("easy", "tune", "2600298", "Easy"),
          ("hard", "tune", "2600298", "Hard"),
          ("ongeki_adv", "tune", "2543258", "LINQAQ's ADVANCED"),
          ("happyend_normal", "holdout", "171880", "4K Normal"),
          ("boulafacet_mx", "holdout", "254581", "MX"),
          ("empress_sc", "holdout", "315435", "SC"))
SONG_KEYS = {"2600298": "mirairo", "2543258": "ongeki", "171880": "happyend",
             "254581": "boulafacet", "315435": "empress"}
K = 48                      # population-projection components (round 15's best)
# brain view: neurons per class (small classes are kept whole)
SAMPLE = {"photoreceptor": 350, "sensory": 50, "optic": 450, "visual_projection": 250,
          "visual_centrifugal": 200, "central": 300, "descending": 450, "ascending": 200}
SAMPLE_SEED = 7
FLOOR = 0.02                # min per-neuron scale (firing-rate units)
QMAX = 15                   # 31 levels is plenty for dot brightness, and compresses well
DEADZONE = 0.08             # |change| under this fraction of a neuron's range is stored as 0
BRAIN_EVERY = 8             # frames (2 ms each) -> 16 ms


def build_player():
    from flyosu import model as M, play as P, reservoir as R
    from flyosu.controller import calibration_states
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
    """Keep at most PLAY_S of play: a contiguous window that starts on a note.
    It is the opening of the chart unless the opening is sparse, in which case
    it is the first window holding at least 90% of the chart's average number
    of events per window.  Every note whose head falls in the window is kept,
    holds whole.  Times are shifted so the first kept note lands LEAD_MS in.
    Returns the new chart and a record of the window in the map's own time."""
    notes = chart.notes
    t = np.array([n.hit_ms for n in notes])
    span = (chart.end_ms - chart.start_ms) / 1000.0
    W = PLAY_S * 1000.0
    if span <= PLAY_S:
        keep = list(notes)
    else:
        ev = np.unique(t)
        target = 0.9 * len(ev) * W / (ev[-1] - ev[0])
        s = ev[0]
        for x in ev:
            if x + W > ev[-1]:
                break
            if np.searchsorted(ev, x + W) - np.searchsorted(ev, x) >= target:
                s = x
                break
        keep = [n for n in notes if s <= n.hit_ms < s + W]
    first = keep[0].hit_ms
    shift = LEAD_MS - first
    new = [mania.Note(n.lane, n.hit_ms + shift, None if n.end_ms is None else n.end_ms + shift)
           for n in keep]
    last = max((n.end_ms if n.is_hold else n.hit_ms) for n in keep)
    window = {"raw_first_ms": round(first, 1), "raw_last_ms": round(last, 1),
              "n_notes": len(keep), "of_notes": len(notes),
              "full_span_s": round(span, 1), "clipped": len(keep) != len(notes)}
    return mania.Chart(new, approach_ms=chart.approach_ms, od=chart.od, name=chart.name), window


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


def select_charts():
    """The six demo maps, by (map set, song id prefix, difficulty name)."""
    from experiments import e20_beatmaps as E20
    pool = {}
    for ms in ("tune", "holdout"):
        E20.MAP_SET = ms                   # charts() reads this at call time
        for c in E20.charts():
            pool[(ms, c["song"].split(" ")[0], c["version"])] = c
    out = []
    for key, ms, sid, ver in SELECT:
        c = pool.get((ms, sid, ver))
        if c is None:
            names = sorted(v for (m2, s2, v) in pool if m2 == ms and s2 == sid)
            raise SystemExit(f"{key}: no difficulty {ver!r} for song {sid} in {ms}; have {names}")
        print(f"{key}: {c['song']} [{c['version']}]  {c['events_per_s']} ev/s  "
              f"{c['seconds']} s  {c['notes']} notes", flush=True)
        out.append((key, "tuning" if ms == "tune" else "held-out", c))
    return out


def main():
    chosen = select_charts()
    fly, player, fit, fit_s = build_player()
    pick, neurons = sample_neurons(fly)
    os.makedirs(OUT_DIR, exist_ok=True)
    maps = []
    for key, map_set, c in chosen:
        name = f"{key} ({c['version']})"
        chart, window = trim(c["chart"])
        meta = dict(c, trimmed=window["clipped"])
        frames, count = [], [0]

        def tap(r, env):
            if count[0] % BRAIN_EVERY == 0:
                frames.append(r[pick].astype(np.float32))
            count[0] += 1

        res = player.play(chart, record=True, seed=4242, tap=tap)
        print(f"{name}: {len(chart)} notes  acc={res.accuracy:.4f}  {res.counts}", flush=True)
        m = export(res, meta)
        m.update(key=key, set=map_set, window=window)
        m["brain"] = encode_brain(frames, np.asarray(player.r0), pick,
                                  os.path.join(OUT_DIR, f"brain_{key}.b64.txt"))
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
    audio()                                  # re-add the song offsets to the fresh JSON


def _raw_hitobjects(txt):
    """(time_ms, lane) of every [HitObjects] entry in a 4K .osu, plus [General]."""
    general, objs, sec = {}, [], None
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("["):
            sec = line
            continue
        if sec == "[General]" and ":" in line:
            k, v = line.split(":", 1)
            general[k.strip()] = v.strip()
        elif sec == "[HitObjects]" and line:
            f = line.split(",")
            objs.append((float(f[2]), min(3, max(0, int(float(f[0])) * 4 // 512))))
    return general, sorted(objs, key=lambda o: (o[0], o[1]))


def _match_window(m, raw):
    """Match the replay's notes, in order, against the raw hit objects of the
    kept window; the offset (raw - replay) must be constant.  Returns it."""
    notes = sorted(((n[1], n[0]) for n in m["notes"]), key=lambda o: (o[0], o[1]))
    w = m["window"]
    i0 = next(i for i, o in enumerate(raw) if o[0] >= w["raw_first_ms"] - 0.5)
    seg = raw[i0:i0 + len(notes)]
    tag = f"{m['key']} [{m['difficulty']}]"
    if len(seg) != len(notes):
        raise SystemExit(f"{tag}: {len(notes)} replay notes vs {len(seg)} raw hit objects")
    if not w["clipped"] and (i0 != 0 or len(raw) != len(notes)):
        raise SystemExit(f"{tag}: unclipped map does not cover every hit object")
    if w["clipped"] and i0 + len(notes) < len(raw) \
            and raw[i0 + len(notes)][0] < w["raw_first_ms"] + PLAY_S * 1000.0:
        raise SystemExit(f"{tag}: window is not contiguous in the raw map")
    lanes_ok = all(a[1] == b[1] for a, b in zip(notes, seg))
    off = np.array([b[0] - a[0] for a, b in zip(notes, seg)])
    dev = float(np.abs(off - np.median(off)).max())
    if dev > 1.0 or not lanes_ok:
        raise SystemExit(f"{tag}: offset not constant (max dev {dev:.2f} ms, lanes match {lanes_ok})")
    return float(np.median(off)), dev


def _ff(*args, pcm=False):
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) if pcm else None


def _duration_s(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _clip_lag_ms(src, clip, start_s):
    """Cross-correlate the clip's first 12 s with the source at start_s; the
    lag should be 0 if the trim kept timing exact."""
    sr = 16000
    a = _ff("-i", src, "-ss", f"{start_s:.3f}", "-t", "12", "-ac", "1", "-ar", str(sr),
            "-f", "s16le", "-", pcm=True)
    b = _ff("-i", clip, "-t", "12", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-", pcm=True)
    n = min(len(a), len(b)) - 2 * sr
    lags = range(-1600, 1601, 4)
    ref = a[sr:sr + n]
    best = max(lags, key=lambda L: float(np.dot(ref, b[sr + L:sr + L + n])))
    fine = max(range(best - 4, best + 5), key=lambda L: float(np.dot(ref, b[sr + L:sr + L + n])))
    return 1000.0 * fine / sr


def _good_hit_sample(blob):
    """A usable hit sample: a readable PCM wav, not silent, not long."""
    import io
    import wave
    try:
        with wave.open(io.BytesIO(blob)) as w:
            n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
            x = np.frombuffer(w.readframes(n), {1: np.uint8, 2: np.int16}[sw]).astype(np.float32)
    except Exception as e:                   # noqa: BLE001 - any unreadable file falls back
        return False, f"unreadable ({e})"
    if sw == 1:
        x -= 128.0
    full = 127.0 if sw == 1 else 32767.0
    dur = n / sr
    peak = float(np.abs(x).max() / full) if len(x) else 0.0
    ok = 0.01 < dur <= 1.0 and peak >= 0.2          # near-silent samples would be inaudible
    return ok, f"{dur:.2f} s, peak {peak:.3f}"


def audio():
    """Light entry point (no model, no fit).  For every map in replay_data.json:
    extract its song and hit sample from the map's own .osz, trim a long song to
    the kept window +-AUDIO_PAD_S (re-encoded to Ogg Vorbis, with the timing
    checked by cross-correlation), and store the offset so that
    file time = replay time + offset."""
    import tempfile
    import zipfile
    with open(OUT) as fh:
        data = json.load(fh)
    by_song = {}
    for m in data["maps"]:
        by_song.setdefault(m["song"], []).append(m)
    tmp = tempfile.mkdtemp(prefix="flyosu_demo_")
    fallback_hit = "soft-hitnormal.wav"
    with zipfile.ZipFile(SONG_OSZ) as z0, open(os.path.join(OUT_DIR, fallback_hit), "wb") as fh:
        fh.write(z0.read("soft-hitnormal.wav"))
    for song, ms in by_song.items():
        skey = SONG_KEYS[song.split(" ")[0]]
        z = zipfile.ZipFile(os.path.join(ROOT, "osumaps", song))
        offs, general = [], None
        for m in ms:
            txt = next(z.read(n).decode("utf-8-sig", errors="replace") for n in z.namelist()
                       if n.endswith(f"[{m['difficulty']}].osu"))
            general, raw = _raw_hitobjects(txt)
            raw_off, dev = _match_window(m, raw)
            offs.append(raw_off)
            print(f"{m['key']}: raw offset {raw_off:.1f} ms over {len(m['notes'])} notes "
                  f"(max dev {dev:.2f} ms), window {m['window']['raw_first_ms']:.0f}-"
                  f"{m['window']['raw_last_ms']:.0f} ms of {m['window']['full_span_s']} s, "
                  f"AudioLeadIn={general.get('AudioLeadIn', '(absent)')}", flush=True)
        src_name = general["AudioFilename"]
        ext = os.path.splitext(src_name)[1].lower()
        src = os.path.join(tmp, "src" + ext)
        with open(src, "wb") as fh:
            fh.write(z.read(src_name))
        dur = _duration_s(src)
        lo = min(m["window"]["raw_first_ms"] for m in ms) / 1000.0 - AUDIO_PAD_S
        hi = max(m["window"]["raw_last_ms"] for m in ms) / 1000.0 + AUDIO_PAD_S
        lo, hi = max(0.0, lo), min(dur, hi)
        if hi - lo < 0.8 * dur:
            out_name = f"song_{skey}.ogg"
            _ff("-i", src, "-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-map", "0:a:0", "-vn",
                "-c:a", "libvorbis", "-q:a", "5", os.path.join(OUT_DIR, out_name))
            lag = _clip_lag_ms(src, os.path.join(OUT_DIR, out_name), lo)
            if abs(lag) > 1.0:
                raise SystemExit(f"{skey}: trimmed audio is misaligned by {lag:.2f} ms")
            clip_ms = lo * 1000.0
            how = f"trimmed {lo:.2f}-{hi:.2f} s of {dur:.1f} s, clip lag {lag:+.2f} ms"
        else:
            out_name = f"song_{skey}{ext}"
            with open(os.path.join(OUT_DIR, out_name), "wb") as fh:
                fh.write(z.read(src_name))
            clip_ms, how = 0.0, f"full file, {dur:.1f} s"
        # hit sample: the archive's own <sampleset>-hitnormal.wav, else the fallback
        ss = general.get("SampleSet", "Normal").lower()
        cands = [f"{ss}-hitnormal.wav"] + sorted(n for n in z.namelist()
                                                 if n.lower().endswith("-hitnormal.wav"))
        hit, why = fallback_hit, "none in archive"
        if skey == "mirairo":                  # its sample *is* the fallback
            cands, why = [], "this archive's soft-hitnormal.wav"
        for n in cands:
            if n in z.namelist():
                ok, why = _good_hit_sample(z.read(n))
                if ok:
                    hit = f"hit_{skey}.wav"
                    with open(os.path.join(OUT_DIR, hit), "wb") as fh:
                        fh.write(z.read(n))
                    why = f"{n}: {why}"
                    break
                why = f"{n} rejected: {why}"
        print(f"  {skey}: {out_name} ({how}, "
              f"{os.path.getsize(os.path.join(OUT_DIR, out_name)) / 1e6:.2f} MB); hit sound {hit} ({why})",
              flush=True)
        for m, raw_off in zip(ms, offs):
            m["audio"] = {"song": out_name, "hit": hit, "raw_offset_ms": round(raw_off, 1),
                          "clip_start_ms": round(clip_ms, 1)}
            m["audio_offset_ms"] = round(raw_off - clip_ms, 1)
    data.pop("audio", None)
    with open(OUT, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"updated {OUT}  {os.path.getsize(OUT) / 1e6:.2f} MB")
    tot = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)
              if not f.endswith(".log"))
    print(f"demo folder total {tot / 1e6:.2f} MB")


if __name__ == "__main__":
    audio() if sys.argv[1:] == ["audio"] else main()
