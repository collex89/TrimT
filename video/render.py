"""Render the narrated Trim-T demo video from the real traces, report and repo.

    python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge
    python video/narration.py              # voice clips + timing
    python video/render.py                 # -> video/trimt-demo.mp4 (+ -voice, -music versions)
    python video/render.py --frame 6,24    # stills -> video/frames/

Scenes are laid out to fit the voiceover, and every line is shown as a caption.
Uses Microsoft Edge through Playwright to draw each frame of video/scenes.html, and the
ffmpeg bundled with imageio-ffmpeg to encode it.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "video"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(VIDEO))

import music  # noqa: E402
from trimt.analyze import analyze  # noqa: E402
from trimt.config import load_config  # noqa: E402
from trimt.detectors.repeated_prompt import find_shared_prefixes  # noqa: E402
from trimt.load import load_runs  # noqa: E402
from trimt.pricing import Pricing  # noqa: E402
from trimt.report import DETECTOR_LABELS, money  # noqa: E402

FPS = 30
SR = 44_100
SHOT_WIDTH = 1200
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TITLES = {
    "overpowered_model": ("Overpowered model", "Simple steps on the premium model"),
    "repeated_prompt": ("Repeated prompt", "The same big prompt, resent every call"),
    "redundant_calls": ("Redundant call", "The same request, made twice"),
    "large_context": ("Bloated context", "Far more context than the answer needs"),
}

# scene order and the least time each needs for its visuals, in seconds
SCENES = [
    ("hook", 5), ("problem", 11), ("logo", 4), ("trace", 6), ("incidents", 12), ("term", 7),
    ("report", 13.5), ("proof", 6.5), ("entire", 8), ("cfo", 7), ("end", 5),
]
LEAD, GAP, TAIL = 0.45, 0.22, 0.5


def load(page, path: Path) -> None:
    """Open a local page with the bundled Geist fonts, so a flaky connection doesn't matter."""
    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded", timeout=120_000)
    fonts = VIDEO / "fonts"
    css = re.sub(r"url\((?!https?:)([^)]+)\)", lambda m: f"url({(fonts / m.group(1)).as_uri()})",
                 (fonts / "fonts.css").read_text(encoding="utf-8"))
    page.add_style_tag(content=css)
    page.evaluate("Promise.all([...document.fonts].map(f => f.load().catch(() => null)))")
    ok = page.evaluate(
        "document.fonts.ready.then(() => document.fonts.check('16px Geist') && document.fonts.check('16px \"Geist Mono\"'))"
    )
    if not ok:
        raise SystemExit(f"Geist fonts did not load for {path.name}")


def schedule(timing: dict) -> tuple[dict, dict, float]:
    """Place every voice line, and size each scene to fit its lines."""
    sched, lines, t = {}, {}, 0.0
    for name, min_dur in SCENES:
        start, cursor, placed = t, t + LEAD, []
        for line in timing["scenes"].get(name, []):
            placed.append({"t": round(cursor, 3), "d": line["dur"], "text": line["text"], "file": line["file"]})
            cursor += line["dur"] + GAP
        end = max(start + min_dur, (placed[-1]["t"] + placed[-1]["d"] + TAIL) if placed else start)
        sched[name] = [round(start, 3), round(end, 3)]
        lines[name] = placed
        t = end
    return sched, lines, round(t, 3)


def failures_from_logs() -> list[dict]:
    """Count the real errors the agent hit, from the run logs."""
    text = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in (ROOT / "traces").glob("*.log"))
    retries = re.findall(r"^\[trimt\] .*", text, re.M)
    count = lambda *keys: sum(any(k in r for k in keys) for r in retries)  # noqa: E731
    crashed = len(re.findall(r"ConnectError|SSL", text)) > 0
    return [
        {"code": "429", "label": "Rate limit and daily quota", "n": count("429"), "fix": "Retry with backoff; budget the quota"},
        {"code": "503", "label": "Model overloaded", "n": count("503"), "fix": "Retry with backoff"},
        {"code": "SSL", "label": "Dropped connection", "n": count("RemoteProtocolError", "ConnectError") + int(crashed),
         "fix": "Retry, and save each finished ticket"},
    ]


def checkpoints() -> list[dict]:
    out = subprocess.run(["entire", "checkpoint", "list"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    ids = re.findall(r"●\s+(\S+)\s", out)
    commits = re.findall(r"\d\d-\d\d \d\d:\d\d \((\w+)\) (.+)", out)
    return [{"id": i, "sha": sha, "msg": msg.strip()} for i, (sha, msg) in zip(ids, commits)]


def build_data(browser, before_path: Path, report: Path, timing: dict) -> dict:
    pricing = Pricing.load()
    config = load_config()
    runs = load_runs(before_path)
    results = analyze(runs, pricing, config)
    summary = json.loads(report.with_name(report.stem + ".summary.json").read_text(encoding="utf-8"))

    first = results[0]
    calls = first.calls
    classify = [c for c in calls if c.step == "classify_intent"]
    rp = config["repeated_prompt"]
    prefixes = find_shared_prefixes(calls, rp["min_prefix_tokens"], rp["min_calls"])
    prefix, members = prefixes[0] if prefixes else ("", [])
    prefix_tokens = round(sum(c.input_tokens * len(prefix) / len(c.prompt) for c in members) / max(len(members), 1))

    rows = [r for r in summary["runs"] if r["measured_after"] is not None]
    before = sum(r["cost_now"] for r in rows) / len(rows)
    after = sum(r["measured_after"] for r in rows) / len(rows)
    verdicts = [f"{r['case_id']} same answer" for r in rows if (r["verdict"] or "").upper().startswith("SAME")]

    # screenshot the real report and find where each finding of the first receipt sits
    page = browser.new_page(viewport={"width": SHOT_WIDTH, "height": 900}, device_scale_factor=2)
    load(page, report)
    page.screenshot(path=str(VIDEO / "report.png"), full_page=True)
    boxes = page.evaluate(
        """() => {
          const box = (e) => { const r = e.getBoundingClientRect();
            return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}; };
          const rc = document.querySelector('.receipt');
          return {receipt: box(rc.querySelector('table.calls')),
                  items: [...rc.querySelectorAll('tr.item')].map(box),
                  total: box(rc.querySelector('.grand'))};
        }"""
    )
    page.close()

    findings = []
    for f, box in zip(first.findings, boxes["items"]):
        title, detail = TITLES.get(f.detector, (DETECTOR_LABELS.get(f.detector, f.detector), ""))
        findings.append({"title": title, "short": detail, "now": money(f.cost_now), "after": money(f.cost_after),
                         "detail": f"{detail}<br>{money(f.cost_now)} → {money(f.cost_after)} per ticket", "box": box})

    cli = "python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge"
    terminal = [
        ["p", "$ python -m demo_agent.run wasteful", "type"],
        ["dim", f"  {len(runs)} tickets · {sum(len(c) for c in runs.values())} LLM calls traced to neatlogs", "line"],
        ["", " ", "line"],
        ["p", f"$ {cli}", "type"],
    ]
    for f in first.findings:
        terminal.append(["", f"  - {DETECTOR_LABELS.get(f.detector, f.detector):<18} {f.step.split(',')[0]}", "line"])
        terminal.append(["r", f"      {money(f.cost_now)} -> {money(f.cost_after)}", "line"])
    terminal.append(["ok", f"  run total: {money(first.cost_now)} -> {money(first.cost_after)} (est. {first.percent_saved:.0f}% saved)", "line"])
    if verdicts:
        terminal.append(["ok", f"  answer check: {', '.join(verdicts)}", "line"])

    sched, lines, total = schedule(timing)
    assets = sorted(p.name for p in (VIDEO / "assets").glob("*.png")) if (VIDEO / "assets").exists() else []
    return {
        "total": total,
        "schedule": sched,
        "lines": lines,
        "premium": calls[0].model,
        "cheap": config["overpowered_model"]["cheaper_model"],
        "thinking": round(sum(c.reasoning_tokens for c in classify) / max(len(classify), 1)),
        "prefix_tokens": prefix_tokens,
        "prefix_calls": len(members),
        "terminal": terminal,
        "shot": {"file": "report.png", "width": SHOT_WIDTH},
        "receipt_box": boxes["receipt"],
        "findings": findings,
        "total_box": boxes["total"],
        "before": money(before),
        "after": money(after),
        "pct": round(100 * (before - after) / before),
        "per1k_before": money(before * 1000),
        "per1k_after": money(after * 1000),
        "verdicts": verdicts or ["answers compared"],
        "n_measured": len(rows),
        "run_id": first.run_id,
        "calls": [
            {"step": c.step, "model": c.model, "inp": c.input_tokens, "out": c.output_tokens,
             "think": c.reasoning_tokens, "ms": c.latency_ms, "cost": money(pricing.call_cost(c))}
            for c in calls
        ],
        "ticket_cost": money(first.cost_now),
        "ticket_per1k": money(first.cost_now * 1000),
        "failures": failures_from_logs(),
        "checkpoints": checkpoints(),
        "neatlogs_shots": [a for a in assets if a.startswith("neatlogs")],
        "cfo_shots": [a for a in assets if a.startswith("cfo")],
        "entire_shots": [a for a in assets if a.startswith("entire")],
    }


def decode(path: Path) -> np.ndarray:
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768


def soundtracks(data: dict) -> dict[str, Path]:
    """Voice + quiet music, music only, and voice only."""
    n = int(data["total"] * SR) + SR
    voice = np.zeros((n, 2), dtype=np.float32)
    for lines in data["lines"].values():
        for line in lines:
            clip = decode(VIDEO / "voice" / line["file"])
            i = int(line["t"] * SR)
            voice[i:i + len(clip)] += clip[: n - i]
    peak = np.max(np.abs(voice)) or 1
    voice *= 0.9 / peak
    bed = music.make(data["total"] + 1)[:n]
    bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    tracks = {"voice": voice + 0.16 * bed, "music": bed, "voiceonly": voice}
    paths = {}
    for name, audio in tracks.items():
        paths[name] = VIDEO / f"audio-{name}.wav"
        music.write_wav(paths[name], audio)
    return paths


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", type=Path, default=ROOT / "traces" / "wasteful.jsonl")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "report.html")
    parser.add_argument("--out", type=Path, default=VIDEO / "trimt-demo.mp4")
    parser.add_argument("--frame", help="render stills at these seconds instead, e.g. 6,24.5")
    parser.add_argument("--channel", default="msedge", help="installed browser for Playwright (msedge or chrome)")
    args = parser.parse_args(argv)

    timing = json.loads((VIDEO / "voice" / "timing.json").read_text(encoding="utf-8"))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        data = build_data(browser, args.before, args.report, timing)
        (VIDEO / "data.js").write_text("window.DATA = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
        print(f"Length: {data['total']:.1f}s")

        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        load(page, VIDEO / "scenes.html")
        page.evaluate("window.ready")

        if args.frame:
            for t in args.frame.split(","):
                page.evaluate(f"window.seek({float(t)})")
                path = VIDEO / "frames" / f"frame_{float(t):05.1f}.png"
                path.parent.mkdir(exist_ok=True)
                page.screenshot(path=str(path))
                print(path)
            return 0

        frames = int(data["total"] * FPS)
        ffmpeg = subprocess.Popen(
            [FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
             # JPEG frames are full range; convert to the standard video range for players
             "-vf", "scale=out_range=tv,format=yuv420p", "-color_range", "tv",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", str(args.out)],
            stdin=subprocess.PIPE,
        )
        for i in range(frames):
            page.evaluate(f"window.seek({i / FPS})")
            ffmpeg.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % (FPS * 10) == 0:
                print(f"  {i / FPS:4.0f}s / {data['total']:.0f}s", flush=True)
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            print("ffmpeg failed", file=sys.stderr)
            return 1
        browser.close()

    for name, wav in soundtracks(data).items():
        out = args.out.with_name(f"{args.out.stem}-{name}.mp4")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(args.out), "-i", str(wav), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
        print(f"{name}: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
