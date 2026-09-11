"""clips/*.webm + audio/*.mp3 -> ninetyninety-demo.mp4

Each shot is cut to its narration length (plus PAD), so picture and voice
concatenate with no offset arithmetic. Short clips hold their last frame.
"""
import json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).parent
# ponytail: PATH by default, FFMPEG/FFPROBE to point at a portable build that
# is not on it. These were absolute paths that existed on one laptop only.
FF = os.environ.get("FFMPEG", "ffmpeg")
PROBE = os.environ.get("FFPROBE", "ffprobe")
BUILD = HERE / "build"
OUT = HERE / "ninetyninety-demo.mp4"
PAD = 0.6
PUSH = 0.06        # how far the slow zoom travels over a shot
SHOTS = [f"s0{i}" for i in range(1, 10)]
APP_SHOTS = {"s03", "s04", "s05"}   # the ones filmed inside streamlit cloud
DUR = json.loads((HERE / "durations.json").read_text(encoding="utf-8"))


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, cwd=HERE)
    if r.returncode != 0:
        print("FFMPEG FAILED:", " ".join(str(a) for a in args[:8]), "...")
        print(r.stderr[-1500:])
        sys.exit(1)


def seconds(path):
    r = subprocess.run([PROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


BUILD.mkdir(exist_ok=True)
vlist, alist, t = [], [], 0.0
for s in SHOTS:
    clip = HERE / "clips" / f"{s}.webm"
    meta = HERE / "clips" / f"{s}.json"
    trim = json.loads(meta.read_text(encoding="utf-8"))["trim"] if meta.exists() else 0.0
    want = round(DUR[s] + PAD, 2)
    have = seconds(clip) - trim
    if have < want - 0.05:
        print(f"  {s}: clip is {have:.1f}s for a {want:.1f}s line, holding the last frame")
    # the clips were choreographed against a longer script. Cutting them to the
    # shorter line would truncate the reveal - the voice reaches the punchline
    # while the screen is still scrolling - so compress time instead of trimming.
    rate = max(have / want, 1.0)
    v = BUILD / f"v_{s}.mp4"
    # the hosted app sits in streamlit cloud's wrapper, which keeps a "Built with
    # Streamlit" strip along the bottom: crop it off and zoom back to frame
    chrome = "crop=in_w:in_h-46:0:0,scale=-2:1080:flags=lanczos,crop=1920:1080," if s in APP_SHOTS else ""
    # a screen recording that holds still reads as a frozen video, so every shot
    # gets a slow continuous push (alternating in/out) - no frame repeats its
    # predecessor, and the move looks deliberate. Upscale first: zoompan rounds
    # its crop window to whole pixels, which judders at 1080p.
    frames = max(int(want * 30), 1)
    z = (f"1+{PUSH}*on/{frames}" if SHOTS.index(s) % 2 == 0
         else f"{1 + PUSH}-{PUSH}*on/{frames}")
    run([FF, "-y", "-v", "error", "-ss", f"{trim}", "-i", str(clip),
         "-vf", f"setpts=PTS/{rate:.5f},"
                f"tpad=stop_mode=clone:stop_duration=8,scale=1920:1080:flags=lanczos,"
                f"{chrome}fps=30,scale=3840:2160:flags=lanczos,"
                f"zoompan=z='{z}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s=1920x1080:fps=30,"
                f"ass=subs/{s}.ass,format=yuv420p",
         "-t", f"{want}", "-an", "-c:v", "libx264", "-crf", "18", "-preset", "fast", str(v)])
    a = BUILD / f"a_{s}.m4a"
    run([FF, "-y", "-v", "error", "-i", str(HERE / "audio" / f"{s}.mp3"),
         "-af", "apad", "-t", f"{want}", "-ar", "48000", "-ac", "2",
         "-c:a", "aac", "-b:a", "192k", str(a)])
    print(f"  {s}: {want:5.2f}s  x{rate:.2f}  at {int(t//60)}:{t%60:05.2f}")
    vlist.append(v); alist.append(a); t += want

for name, items in (("v", vlist), ("a", alist)):
    (BUILD / f"{name}.txt").write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in items), encoding="utf-8")

run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(BUILD / "v.txt"),
     "-c", "copy", str(BUILD / "video.mp4")])
run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(BUILD / "a.txt"),
     "-c", "copy", str(BUILD / "audio.m4a")])
run([FF, "-y", "-v", "error", "-i", str(BUILD / "video.mp4"), "-i", str(BUILD / "audio.m4a"),
     "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", "-shortest", str(OUT)])

total = seconds(OUT)
print(f"\n{OUT.name}: {int(total//60)}:{total%60:05.2f}  ({OUT.stat().st_size/1e6:.1f} MB)")
