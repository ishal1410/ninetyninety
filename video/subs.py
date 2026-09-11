"""narration/sNN.txt + durations.json -> subs/sNN.ass (burned-in captions).

One cue per sentence, timed by character share of the shot. The narration is
TTS of this exact text, so the words on screen are the words spoken.
"""
import json, pathlib, re

HERE = pathlib.Path(__file__).parent
SUBS = HERE / "subs"
DUR = json.loads((HERE / "durations.json").read_text(encoding="utf-8"))
BREAK = "\\" + "N"      # ass line break, kept out of the f-strings below

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Segoe UI Semibold,46,&H00FFFFFF,&H00000000,&HB4000000,0,3,12,0,2,200,200,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def tc(s):
    h, s = divmod(max(s, 0.0), 3600)
    m, s = divmod(s, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def sentences(text):
    parts = [p.strip() for p in re.split(r"(?<=[.?!])\s+", text.strip()) if p.strip()]
    out = []
    for p in parts:
        # a three-word sentence on its own card flickers; glue it to its neighbour
        if out and len(p.split()) <= 3:
            out[-1] += " " + p
        else:
            out.append(p)
    return out


def wrap(c):
    """Split a long cue near its middle so no card runs the full 1920 width."""
    words, half, run, first = c.split(), len(c) // 2, 0, []
    for w in words:
        if run + len(w) > half and first:
            break
        first.append(w)
        run += len(w) + 1
    return " ".join(first) + BREAK + " ".join(words[len(first):])


SUBS.mkdir(exist_ok=True)
for shot, spoken in sorted(DUR.items()):
    text = (HERE / "narration" / f"{shot}.txt").read_text(encoding="utf-8")
    cues = sentences(text)
    total = sum(len(c) for c in cues)
    lines, t = [], 0.0
    for c in cues:
        span = spoken * len(c) / total
        body = c if len(c) <= 62 else wrap(c)
        lines.append(f"Dialogue: 0,{tc(t)},{tc(t + span)},Cap,,0,0,0,,{body}")
        t += span
    (SUBS / f"{shot}.ass").write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {shot}: {len(cues)} cues over {spoken:5.1f}s")
