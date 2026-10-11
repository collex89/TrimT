"""Detector 1: a simple step running on an expensive model."""

import re
from collections import defaultdict

from ..pricing import Pricing
from ..records import CallChange, Finding, TraceRecord

NAME = "overpowered_model"
# Only the end of the prompt holds the instruction; a long system prompt mentioning
# "format" somewhere shouldn't make every step look simple.
INSTRUCTION_TAIL_CHARS = 600


def _keyword_hit(text: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        stem = kw.rstrip("ey")  # route -> rout(ing), classify -> classif(ication)
        if re.search(rf"\b{re.escape(stem)}", text, re.IGNORECASE):
            return kw
    return None


def detect(run_id: str, calls: list[TraceRecord], pricing: Pricing, cfg: dict) -> list[Finding]:
    expensive = set(cfg["expensive_tiers"])
    cheaper = cfg["cheaper_model"]
    cheaper_price = pricing.get(cheaper)

    by_step: dict[str, list[tuple[TraceRecord, str]]] = defaultdict(list)
    for rec in calls:
        if pricing.tier(rec.model) not in expensive:
            continue
        if rec.visible_output_tokens <= cfg["max_output_tokens"]:
            reason = f"{rec.visible_output_tokens}-token answer"
        elif kw := _keyword_hit(rec.step, cfg["simple_keywords"]) or _keyword_hit(
            rec.prompt[-INSTRUCTION_TAIL_CHARS:], cfg["simple_keywords"]
        ):
            reason = f'"{kw}" task'
        else:
            continue
        by_step[rec.step].append((rec, reason))

    # One finding per run, listing each simple step, so the receipt stays readable.
    change = CallChange(new_model=cheaper, drop_reasoning=not cheaper_price.reasoning)
    steps = []
    recs: list[TraceRecord] = []
    for step, hits in by_step.items():
        step_recs = [rec for rec, _ in hits]
        if sum(pricing.changed_cost(r, change) for r in step_recs) >= sum(pricing.call_cost(r) for r in step_recs):
            continue
        recs.extend(step_recs)
        steps.append(f"{step} ({hits[0][1]}{f', x{len(hits)}' if len(hits) > 1 else ''})")
    if not recs:
        return []

    models = sorted({r.model for r in recs})
    reasoning = sum(r.reasoning_tokens for r in recs) // len(recs)
    evidence = f"{len(steps)} simple step{'s' * (len(steps) > 1)} on {', '.join(models)}: {'; '.join(steps)}"
    if reasoning:
        evidence += f". Avg {reasoning} billed thinking tokens per call"
    step_names = list(dict.fromkeys(r.step for r in recs))
    return [
        Finding(
            run_id=run_id,
            step=", ".join(step_names),
            detector=NAME,
            evidence=evidence,
            cost_now=sum(pricing.call_cost(r) for r in recs),
            cost_after=sum(pricing.changed_cost(r, change) for r in recs),
            suggestion=f"Run {', '.join(step_names)} on {cheaper}"
            + ("" if cheaper_price.reasoning else " (no thinking tokens)")
            + "; these are short, simple tasks.",
            calls=sorted(r.call_index for r in recs),
            changes={r.call_index: change for r in recs},
        )
    ]
