"""narration/sNN.txt -> audio/sNN.mp3, and write durations.json (seconds per shot)."""
import asyncio, json, os, pathlib, subprocess, sys
import edge_tts

HERE = pathlib.Path(__file__).parent
VOICE = sys.argv[1] if len(sys.argv) > 1 else "en-US-AndrewNeural"
RATE = "-4%"          # slightly under default: this is a compliance product, not an ad
FFPROBE = os.environ.get("FFPROBE", "ffprobe")

async def main():
    (HERE / "audio").mkdir(exist_ok=True)
    for txt in sorted((HERE / "narration").glob("s*.txt")):
        mp3 = HERE / "audio" / (txt.stem + ".mp3")
        words = txt.read_text(encoding="utf-8").strip()
        await edge_tts.Communicate(words, VOICE, rate=RATE).save(str(mp3))
        print("  ok", mp3.name, mp3.stat().st_size, "bytes")

def durations():
    out = {}
    for mp3 in sorted((HERE / "audio").glob("s*.mp3")):
        r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(mp3)], capture_output=True, text=True)
        out[mp3.stem] = round(float(r.stdout.strip()), 2)
    (HERE / "durations.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    total = sum(out.values())
    print(json.dumps(out, indent=1))
    print(f"TOTAL narration {total:.1f}s = {int(total//60)}:{int(total%60):02d}")
    return out

asyncio.run(main())
durations()
