"""
osu! beatmap files (.osu, format v14) <-> ``mania.Chart``.

Step 11.  Only the osu!mania parts of the format are handled:

    [General]      Mode: 3  (mania)
    [Difficulty]   CircleSize = key count, OverallDifficulty = judgment windows
    [HitObjects]   x,y,time,type,hitSound,[endTime:]extras
                     lane    = floor(x * keys / 512)
                     hold    = type & 128, end time is the first field of extras

Charts with a key count other than 4 are refused rather than silently
squeezed -- the fly has four keys.  Timing points, hit sounds, slider velocity
and everything else the format carries are ignored: a mania note's time is
absolute in ms and needs none of it.

``write`` produces a minimal but valid .osu so that a generated curriculum
chart can be opened in the real client (with a silent audio file alongside).
"""

from __future__ import annotations

import os

from .mania import N_LANES, Chart, Note


def _sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def _kv(lines: list[str]) -> dict[str, str]:
    d = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def parse(text: str, approach_ms: float = 800.0, keys: int = N_LANES) -> Chart:
    sec = _sections(text)
    general = _kv(sec.get("General", []))
    meta = _kv(sec.get("Metadata", []))
    diff = _kv(sec.get("Difficulty", []))
    if int(float(general.get("Mode", "0"))) != 3:
        raise ValueError("not an osu!mania beatmap (Mode != 3)")
    n_keys = int(round(float(diff.get("CircleSize", "4"))))
    if n_keys != keys:
        raise ValueError(f"{n_keys}K beatmap; the fly plays {keys}K")
    od = float(diff.get("OverallDifficulty", "8"))

    notes = []
    for line in sec.get("HitObjects", []):
        f = line.split(",")
        if len(f) < 5:
            continue
        x, t, typ = int(float(f[0])), float(f[2]), int(f[3])
        lane = min(keys - 1, max(0, x * keys // 512))
        end = None
        if typ & 128 and len(f) > 5:
            end = float(f[5].split(":")[0])
        notes.append(Note(lane, t, end))
    name = " - ".join(v for v in (meta.get("Artist"), meta.get("Title"),
                                  meta.get("Version")) if v)
    return Chart(notes, approach_ms=approach_ms, od=od, name=name or "beatmap")


def load(path: str, **kw) -> Chart:
    with open(path, encoding="utf-8-sig") as fh:
        return parse(fh.read(), **kw)


def write(chart: Chart, path: str, title: str = "flyosu", artist: str = "connectome",
          version: str | None = None, audio: str = "audio.mp3",
          keys: int = N_LANES) -> None:
    """Minimal osu!mania .osu file.  The client needs an audio file of at least
    the chart's length next to it; a silent one is fine."""
    version = version or (chart.name or "fly")
    lines = [
        "osu file format v14", "",
        "[General]", f"AudioFilename: {audio}", "AudioLeadIn: 0", "PreviewTime: -1",
        "Countdown: 0", "SampleSet: Soft", "StackLeniency: 0.7", "Mode: 3",
        "LetterboxInBreaks: 0", "SpecialStyle: 0", "WidescreenStoryboard: 0", "",
        "[Editor]", "DistanceSpacing: 1", "BeatDivisor: 4", "GridSize: 4", "TimelineZoom: 1", "",
        "[Metadata]", f"Title:{title}", f"TitleUnicode:{title}", f"Artist:{artist}",
        f"ArtistUnicode:{artist}", "Creator:flyosu", f"Version:{version}", "Source:",
        "Tags:flyosu connectome drosophila", "BeatmapID:0", "BeatmapSetID:-1", "",
        "[Difficulty]", "HPDrainRate:5", f"CircleSize:{keys}",
        f"OverallDifficulty:{chart.od:g}", "ApproachRate:5", "SliderMultiplier:1.4",
        "SliderTickRate:1", "",
        "[Events]", "//Background and Video events", "//Break Periods",
        "//Storyboard Layer 0 (Background)", "//Storyboard Layer 1 (Fail)",
        "//Storyboard Layer 2 (Pass)", "//Storyboard Layer 3 (Foreground)",
        "//Storyboard Layer 4 (Overlay)", "//Storyboard Sound Samples", "",
        "[TimingPoints]", "0,500,4,2,0,50,1,0", "",
        "[HitObjects]",
    ]
    for n in chart.notes:
        x = int((n.lane + 0.5) * 512 / keys)
        if n.is_hold:
            lines.append(f"{x},192,{int(round(n.hit_ms))},128,0,{int(round(n.end_ms))}:0:0:0:0:")
        else:
            lines.append(f"{x},192,{int(round(n.hit_ms))},1,0,0:0:0:0:")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    import sys
    from .mania import stage_chart

    if len(sys.argv) > 1:
        c = load(sys.argv[1])
        print(c.describe())
    else:
        c = stage_chart(4, n_notes=32, seed=7)
        out = os.path.join("results", "flyosu_stage4.osu")
        write(c, out)
        back = load(out)
        print(c.describe()); print(back.describe())
        assert [(n.lane, n.hit_ms) for n in c.notes] == [(n.lane, n.hit_ms) for n in back.notes]
        print("round-trip ok ->", out)
