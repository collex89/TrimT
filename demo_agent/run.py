"""Run the demo agent on the sample questions.

    python -m demo_agent.run wasteful
    python -m demo_agent.run fixed
    python -m demo_agent.run wasteful --dry-run     # no API calls, for testing

Each ticket is one run. Calls go to neatlogs and to traces/<mode>.jsonl
(dry runs go to traces/dryrun/ and are not sent to neatlogs).

Free-tier budget: gemini-3.8-flash allows 20 requests a day. The default two cases use
12 (wasteful) + 2 (fixed) of them.
"""

import argparse
import json
import os
import sys
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

import neatlogs
from dotenv import load_dotenv

from trimt.logger import TraceLogger, TracedLLM

from .agent import AGENTS
from .knowledge import QUESTIONS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = "q1,q3"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=sorted(AGENTS))
    parser.add_argument("--cases", default=DEFAULT_CASES, help=f"question ids to run (default {DEFAULT_CASES}; 'all' for every one)")
    parser.add_argument("--dry-run", action="store_true", help="use a fake client: no API calls, no quota")
    parser.add_argument("--out", type=Path, help="trace file (default traces/<mode>.jsonl)")
    args = parser.parse_args(argv)

    cases = [q for q in QUESTIONS if args.cases == "all" or q[0] in args.cases.split(",")]
    if not cases:
        parser.error(f"no questions match --cases {args.cases}")

    load_dotenv(ROOT / ".env")
    out = args.out or ROOT / "traces" / ("dryrun" if args.dry_run else "") / f"{args.mode}.jsonl"
    if out.exists():
        out.unlink()  # one file per batch, so before/after compare like for like

    if args.dry_run:
        from .fake import FakeClient

        llm = TracedLLM(TraceLogger(out), client=FakeClient(), trace_with_neatlogs=False)
    else:
        neatlogs.init(
            api_key=os.environ["NEATLOGS_API_KEY"],
            workflow_name=f"swiftbox-support-{args.mode}",
            tags=["trimt-demo", args.mode],
        )
        llm = TracedLLM(TraceLogger(out))

    agent = AGENTS[args.mode]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    answers = {}

    def handle_ticket(question: str):
        return agent(llm, question)

    if not args.dry_run:
        handle_ticket = neatlogs.span(kind="WORKFLOW", name=f"support_ticket_{args.mode}")(handle_ticket)

    try:
        for case_id, question in cases:
            run_id = f"{'dryrun-' * args.dry_run}{args.mode}-{stamp}-{case_id}"
            llm.start_run(run_id, case_id)
            print(f"\n=== {case_id} ({run_id})\nQ: {question}", flush=True)
            with nullcontext() if args.dry_run else neatlogs.identify(session_id=run_id):
                result = handle_ticket(question)
            print(f"intent:  {result.intent}\ncheck:   {result.check}\nsummary: {result.summary}")
            print(f"answer:\n{result.answer}", flush=True)
            answers[case_id] = {"question": question, **result.__dict__}
    finally:
        if not args.dry_run:
            neatlogs.flush()
            neatlogs.shutdown()

    answers_path = out.with_name(f"{args.mode}.answers.json")
    answers_path.write_text(json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTraces: {out}\nAnswers: {answers_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
