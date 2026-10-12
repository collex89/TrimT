"""Voiceover script and generator for the explainer.

    python video/narration.py                        # Windows built-in voice (offline)
    python video/narration.py --engine edge --voice en-NG-AbeoNeural

Each line becomes one clip in video/voice/ plus an entry in video/voice/timing.json.
The renderer lays the scenes out to fit these clips, and shows each line as a caption.
`say` is what the voice reads when the caption spelling would be read wrongly.
"""

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

VOICE_DIR = Path(__file__).resolve().parent / "voice"
DEFAULT_VOICE = {"windows": "Microsoft David Desktop", "edge": "en-US-AndrewNeural"}
RATE = "+6%"     # edge voices
WIN_RATE = 2     # Windows voices, -10..10

# scene -> lines. Every claim here matches the real traces, report and repo.
SCRIPT = {
    "hook": [
        {"text": "AI agents quietly overpay for every step."},
        {"text": "Every LLM call is billed by the token, and many agents use the priciest model for everything."},
    ],
    "problem": [
        {"text": "Here's a real support bot I built. One customer ticket runs through six LLM calls."},
        {"text": "All six use the premium model. Classifying the ticket returned one word, but burned 282 thinking tokens."},
        {"text": "The same 2,197-token prompt is resent on every call, and one request is made twice."},
        {"text": "The answers look fine, so nobody notices. At a thousand tickets that's about $21, and most of it is waste.",
         "say": "The answers look fine, so nobody notices. At a thousand tickets that's about twenty-one dollars, and most of it is waste."},
    ],
    "logo": [
        {"text": "So I built Trim-T. It finds the waste in your agent's traces and prices the fix.",
         "say": "So I built Trim T. It finds the waste in your agent's traces, and prices the fix."},
    ],
    "trace": [
        {"text": "Every call the agent makes is traced in neatlogs: model, tokens, prompt and answer.",
         "say": "Every call the agent makes is traced in neat logs: model, tokens, prompt, and answer."},
        {"text": "Those traces are where the incidents showed up."},
    ],
    "incidents": [
        {"text": "Trim-T reads them and runs three detectors: an overpowered model, a repeated prompt and a redundant call.",
         "say": "Trim T reads them, and runs three detectors: an overpowered model, a repeated prompt, and a redundant call."},
        {"text": "Each fix is priced from the provider's real price list, never guessed by a model."},
        {"text": "The runs also hit real failures: rate limits, an overloaded API, and a dropped connection that stopped one ticket halfway.",
         "say": "The runs also hit real failures: rate limits, an overloaded A P I, and a dropped connection that stopped one ticket halfway."},
        {"text": "I made the agent retry those errors and save each finished ticket, so a failure no longer loses work."},
    ],
    "term": [
        {"text": "It's two commands: run the agent, then point Trim-T at its traces.",
         "say": "It's two commands: run the agent, then point Trim T at its traces."},
    ],
    "report": [
        {"text": "The report reads like a receipt: each wasted cost struck out, with the fixed cost beside it."},
    ],
    "proof": [
        {"text": "Then I applied the fixes and reran the same ticket, traced again in neatlogs.",
         "say": "Then I applied the fixes, and reran the same ticket, traced again in neat logs."},
        {"text": "It came out 74% cheaper, and a check confirmed the answer stayed the same.",
         "say": "It came out seventy-four percent cheaper, and a check confirmed the answer stayed the same."},
    ],
    "entire": [
        {"text": "I built Trim-T with Claude Code, and Entire recorded every session.",
         "say": "I built Trim T with Claude Code, and Entire recorded every session."},
        {"text": "Each commit links to the conversation behind it as a checkpoint, so anyone can see why the code changed."},
    ],
    "cfo": [
        {"text": "For the business side, I used cfo.ai to plan pricing, costs and runway over two years.",
         "say": "For the business side, I used C F O dot A I to plan pricing, costs, and runway over two years."},
        {"text": "A free tier converts to paid Pro and Team plans. Trim-T's own model cost is under a tenth of a cent per run.",
         "say": "A free tier converts to paid Pro and Team plans. Trim T's own model cost is under a tenth of a cent per run."},
    ],
    "end": [
        {"text": "Trim-T. Trim the tokens, keep the answers.", "say": "Trim T. Trim the tokens, keep the answers."},
    ],
}


def duration(path: Path) -> float:
    out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def speak_edge(text: str, voice: str, path: Path, attempts: int = 5) -> None:
    import edge_tts

    for i in range(attempts):
        try:
            await edge_tts.Communicate(text, voice, rate=RATE).save(str(path))
            if path.stat().st_size > 0:
                return
        except Exception as e:  # network drops are common here; retry
            print(f"  retry {i + 1}: {e}", file=sys.stderr)
            await asyncio.sleep(2 + 2 * i)
    raise SystemExit(f"Could not generate voice for: {text[:60]}")


def speak_windows(text: str, voice: str, path: Path) -> None:
    """Offline Windows voice via System.Speech."""
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoice('{voice}'); $s.Rate = {WIN_RATE}; "
        f"$s.SetOutputToWaveFile('{path}'); "
        "$s.Speak([Console]::In.ReadToEnd()); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)


async def generate(engine: str, voice: str) -> dict:
    VOICE_DIR.mkdir(exist_ok=True)
    timing = {"engine": engine, "voice": voice, "scenes": {}}
    for scene, lines in SCRIPT.items():
        timing["scenes"][scene] = []
        for line in lines:
            spoken = line.get("say", line["text"])
            rate = RATE if engine == "edge" else WIN_RATE
            key = hashlib.sha1(f"{engine}|{voice}|{rate}|{spoken}".encode()).hexdigest()[:12]
            path = VOICE_DIR / f"{key}.{'mp3' if engine == 'edge' else 'wav'}"
            if not path.exists() or path.stat().st_size == 0:
                print(f"  {scene}: {line['text'][:60]}")
                if engine == "edge":
                    await speak_edge(spoken, voice, path)
                else:
                    speak_windows(spoken, voice, path)
            timing["scenes"][scene].append({"text": line["text"], "file": path.name, "dur": round(duration(path), 3)})
    return timing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["windows", "edge"], default="windows")
    parser.add_argument("--voice", help="voice name (default depends on the engine)")
    args = parser.parse_args(argv)
    timing = asyncio.run(generate(args.engine, args.voice or DEFAULT_VOICE[args.engine]))
    (VOICE_DIR / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")
    total = sum(l["dur"] for lines in timing["scenes"].values() for l in lines)
    print(f"{sum(len(v) for v in timing['scenes'].values())} lines, {total:.1f}s of speech")
    return 0


if __name__ == "__main__":
    sys.exit(main())
