"""Trim-T: find wasted spend in an AI agent's traces.

    python -m trimt traces/wasteful.jsonl
    python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge

Writes a receipt-style HTML report (default reports/report.html) and prints a summary.
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .analyze import analyze
from .config import load_config
from .load import load_runs
from .pricing import Pricing
from .report import html_report, text_summary

ROOT = Path(__file__).resolve().parent.parent


def _answers_for(trace_path: Path) -> dict:
    path = trace_path.with_name(trace_path.stem + ".answers.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trimt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("traces", nargs="+", type=Path, help="JSONL trace files to analyse")
    parser.add_argument("--after", nargs="+", type=Path, help="traces from the fixed agent on the same inputs")
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "report.html")
    parser.add_argument("--json", type=Path, help="also write findings as JSON")
    parser.add_argument("--pricing", type=Path, default=ROOT / "pricing.yaml")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--llm-suggestions", action="store_true", help="reword suggestions with a cheap model")
    parser.add_argument("--judge", action="store_true", help="check before/after answers match (needs --after)")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    pricing = Pricing.load(args.pricing)
    config = load_config(args.config)
    results = analyze(load_runs(*args.traces), pricing, config)

    if args.llm_suggestions or args.judge:
        from google import genai

        client = genai.Client()
    if args.llm_suggestions:
        from .suggest import rewrite_suggestions

        rewrite_suggestions([f for r in results for f in r.findings], client)

    answers_before = {k: v for p in args.traces for k, v in _answers_for(p).items()}
    after_runs = answers_after = None
    verdicts: dict[str, str] = {}
    if args.after:
        after_runs = load_runs(*args.after)
        answers_after = {k: v for p in args.after for k, v in _answers_for(p).items()}
        if args.judge:
            from .judge import judge_answers

            for case_id, b in answers_after.items():
                if a := answers_before.get(case_id):
                    verdicts[case_id] = judge_answers(a.get("question", ""), a["answer"], b["answer"], client)

    measured = None
    if after_runs:
        measured = {}
        for calls in after_runs.values():
            measured[calls[0].case_id] = measured.get(calls[0].case_id, 0) + sum(pricing.call_cost(c) for c in calls)
    print(text_summary(results, measured))
    for case_id, verdict in verdicts.items():
        print(f"Answer check {case_id}: {verdict}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        html_report(
            results,
            pricing,
            sources=[p.name for p in args.traces + (args.after or [])],
            questions={k: v.get("question", "") for k, v in answers_before.items()},
            after_runs=after_runs,
            answers_before=answers_before,
            answers_after=answers_after,
            verdicts=verdicts,
        ),
        encoding="utf-8",
    )
    print(f"\nReport: {args.out}")

    if args.json:
        args.json.write_text(
            json.dumps([f.to_dict() for r in results for f in r.findings], indent=2), encoding="utf-8"
        )
        print(f"Findings: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
