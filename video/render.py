"""Render the Trim-T explainer video from the real traces and report.

    python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge
    python video/render.py                 # -> video/trimt-demo.mp4
    python video/render.py --frame 6,24    # stills -> video/frames/

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
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trimt.analyze import analyze  # noqa: E402
from trimt.config import load_config  # noqa: E402
from trimt.detectors.repeated_prompt import find_shared_prefixes  # noqa: E402
from trimt.load import load_runs  # noqa: E402
from trimt.pricing import Pricing  # noqa: E402
from trimt.report import DETECTOR_LABELS, money  # noqa: E402

VIDEO = ROOT / "video"
FPS = 30
TOTAL = 71.0
SHOT_WIDTH = 1200

TITLES = {
    "overpowered_model": ("Overpowered model", "Simple steps on the premium model"),
    "repeated_prompt": ("Repeated prompt", "The same big prompt, resent every call"),
    "redundant_calls": ("Redundant call", "The same request, made twice"),
    "large_context": ("Bloated context", "Far more context than the answer needs"),
}


def load(page, path: Path) -> None:
    """Open a local page and wait for its web fonts, which come from Google Fonts."""
    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded", timeout=120_000)
    # Bundled copies of the fonts, so rendering works on a flaky connection.
    fonts = VIDEO / "fonts"
    css = re.sub(r"url\((?!https?:)([^)]+)\)", lambda m: f"url({(fonts / m.group(1)).as_uri()})",
                 (fonts / "fonts.css").read_text(encoding="utf-8"))
    page.add_style_tag(content=css)
    page.evaluate("Promise.all([...document.fonts].map(f => f.load().catch(() => null)))")
    ok = page.evaluate(
        "document.fonts.ready.then(() => document.fonts.check('16px Geist') && document.fonts.check('16px \"Geist Mono\"'))"
    )
    if not ok:
        raise SystemExit(f"Geist fonts did not load for {path.name}; check the internet connection and retry.")


def build_data(browser, before_path: Path, report: Path) -> dict:
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
    shot = VIDEO / "report.png"
    page.screenshot(path=str(shot), full_page=True)
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
        findings.append({"title": title, "detail": f"{detail}<br>{money(f.cost_now)} → {money(f.cost_after)} per ticket", "box": box})

    cli = f"python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge"
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

    return {
        "total": TOTAL,
        "premium": calls[0].model,
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
        "calls": [
            {"step": c.step, "model": c.model, "inp": c.input_tokens, "out": c.output_tokens,
             "cost": money(pricing.call_cost(c))}
            for c in calls
        ],
        "ticket_cost": money(first.cost_now),
        "ticket_per1k": money(first.cost_now * 1000),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--before", type=Path, default=ROOT / "traces" / "wasteful.jsonl")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "report.html")
    parser.add_argument("--out", type=Path, default=VIDEO / "trimt-demo.mp4")
    parser.add_argument("--frame", help="render stills at these seconds instead, e.g. 6,24.5")
    parser.add_argument("--channel", default="msedge", help="installed browser for Playwright (msedge or chrome)")
    args = parser.parse_args(argv)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel)
        data = build_data(browser, args.before, args.report)
        (VIDEO / "data.js").write_text("window.DATA = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")

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

        frames = int(TOTAL * FPS)
        ffmpeg = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
             "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
             # JPEG frames are full range; convert to the standard video range for players
             "-vf", "scale=out_range=tv,format=yuv420p", "-color_range", "tv",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-movflags", "+faststart", str(args.out)],
            stdin=subprocess.PIPE,
        )
        for i in range(frames):
            page.evaluate(f"window.seek({i / FPS})")
            ffmpeg.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % (FPS * 5) == 0:
                print(f"  {i / FPS:4.0f}s / {TOTAL:.0f}s", flush=True)
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            print("ffmpeg failed", file=sys.stderr)
            return 1
        browser.close()
    print(f"Video: {args.out}")

    music = VIDEO / "music.wav"
    if music.exists():
        with_music = args.out.with_name(args.out.stem + "-music.mp4")
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(args.out), "-i", str(music),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(with_music)],
            check=True,
        )
        print(f"With music: {with_music}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
