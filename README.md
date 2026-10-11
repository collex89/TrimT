# Trim-T

**Trim the tokens, keep the answers.**

Trim-T finds wasted spend in AI agents. It reads an agent's traces (every LLM call, with
its model, tokens, prompt and output), spots the steps that cost more than they need to,
and suggests a fix for each one with the cost now and the cost after.

Built solo for neatHack 2026 by Collex ([@collex89](https://github.com/collex89)).

## What it detects

| Detector | Flags | Estimated saving |
|---|---|---|
| Overpowered model | A simple step (short output, or a classify/extract/route/label/format task) on a premium model | Same tokens priced at the cheaper model, without its thinking tokens |
| Repeated prompt | A shared prompt prefix over ~1,000 tokens sent in 3+ calls of one run; also context that dwarfs the answer | Repeats priced at the cached-input rate (or trimmed) |
| Redundant calls | The same request (normalised, or ≥95% similar) made more than once in a run | The duplicate calls' full cost |

Every number comes from the traces and [pricing.yaml](pricing.yaml) (Gemini paid-tier list
prices). Each finding's saving is computed on its own, and run totals apply all fixes
together, so a saving is never counted twice. Thresholds live in [config.yaml](config.yaml).

## Setup

Python 3.12+.

```bash
pip install -r requirements.txt
```

`.env` (never committed):

```
NEATLOGS_API_KEY=...   # neatlogs Project API key (not the nlw_ HTTP key)
GEMINI_API_KEY=...     # Google AI Studio
```

## Run the demo

The demo agent is a support bot for a made-up courier company, SwiftBox. It comes in two versions:

- **wasteful**: every step on `gemini-3.8-flash`, the handbook and whole knowledge base resent on every call, keywords extracted twice.
- **fixed**: simple steps on `gemini-3.1-flash-lite`, keywords extracted once, only the top-matching articles sent.

```bash
python -m demo_agent.run wasteful      # traces -> neatlogs + traces/wasteful.jsonl
python -m demo_agent.run fixed         # traces -> neatlogs + traces/fixed.jsonl
python -m trimt traces/wasteful.jsonl --after traces/fixed.jsonl --judge
```

The last command prints a summary and writes `reports/report.html`, a receipt per run plus a
measured before/after comparison. `--judge` asks a cheap model whether each pair of answers
gives the customer the same facts.

Other options: `--llm-suggestions` rewords the fixes with a cheap model (numbers stay
computed), and `--json findings.json` exports the findings.

### Free-tier budget

Gemini's free tier allows **20 requests a day for `gemini-3.8-flash`**. The default two
questions use 12 (wasteful) + 2 (fixed). Test without spending quota:

```bash
python -m demo_agent.run wasteful --dry-run
python -m demo_agent.run fixed --dry-run
python -m trimt traces/dryrun/wasteful.jsonl --after traces/dryrun/fixed.jsonl --out reports/preview.html
```

Dry runs use a fake client with estimated token counts and are not sent to neatlogs.

## Tests

```bash
python -m pytest -q
```

## How it works

```
demo_agent/   the wasteful and fixed support agent, plus a fake client for dry runs
trimt/
  logger.py   wraps the Gemini client: each call goes to neatlogs and to a JSONL line
  load.py     reads JSONL into TraceRecords grouped by run
  pricing.py  costs from pricing.yaml
  detectors/  overpowered.py, repeated_prompt.py, redundant.py
  analyze.py  runs the detectors and totals before/after per run
  suggest.py  optional model-worded suggestions
  judge.py    optional same-answer check
  report.py   HTML receipt and CLI summary
```

Trim-T reads a local JSONL copy of each call. neatlogs also stores the traces (see the
Traces tab, workflows `swiftbox-support-wasteful` and `swiftbox-support-fixed`). Its CLI
and Public API can read them back, so a neatlogs loader can sit behind the same
`TraceRecord` interface later. The detectors don't care where traces come from.
