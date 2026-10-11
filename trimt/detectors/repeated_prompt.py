"""Detector 2: a large prompt prefix sent again and again, or context that dwarfs the answer."""

import os
from collections import defaultdict

from ..pricing import Pricing
from ..records import CallChange, Finding, TraceRecord

NAME = "repeated_prompt"
LARGE_CONTEXT = "large_context"


def prefix_tokens(rec: TraceRecord, prefix_chars: int) -> int:
    """Estimate a prefix's tokens from the call's real token count, by character share."""
    if not rec.prompt:
        return 0
    return round(rec.input_tokens * prefix_chars / len(rec.prompt))


def find_shared_prefixes(
    calls: list[TraceRecord], min_tokens: int, min_calls: int
) -> list[tuple[str, list[TraceRecord]]]:
    """Return (prefix, calls that start with it), biggest repeated cost first.

    Candidates are the common prefixes of every pair of calls; a candidate counts when
    at least ``min_calls`` calls share it. Calls already claimed by a bigger prefix are
    left out of later ones.
    """
    candidates = set()
    for i, a in enumerate(calls):
        for b in calls[i + 1 :]:
            p = os.path.commonprefix([a.prompt, b.prompt])
            if p and prefix_tokens(a, len(p)) >= min_tokens:
                candidates.add(p)

    scored = []
    for p in candidates:
        members = [c for c in calls if c.prompt.startswith(p)]
        if len(members) >= min_calls:
            repeated = sum(prefix_tokens(c, len(p)) for c in members[1:])
            scored.append((repeated, p, members))
    scored.sort(key=lambda s: s[0], reverse=True)

    claimed: set[int] = set()
    result = []
    for _, p, members in scored:
        members = [c for c in members if c.call_index not in claimed]
        if len(members) >= min_calls:
            claimed.update(c.call_index for c in members)
            result.append((p, members))
    return result


def _prefix_cost(pricing: Pricing, rec: TraceRecord, tokens: int, cached: int) -> float:
    p = pricing.get(rec.model)
    cached = min(cached, tokens)
    return ((tokens - cached) * p.input + cached * p.cached_input) / 1_000_000


def detect(run_id: str, calls: list[TraceRecord], pricing: Pricing, cfg: dict) -> list[Finding]:
    findings = []
    shared_tokens: dict[int, int] = defaultdict(int)  # call_index -> tokens in a shared prefix

    for prefix, members in find_shared_prefixes(calls, cfg["min_prefix_tokens"], cfg["min_calls"]):
        cost_now = cost_after = 0.0
        changes = {}
        for i, rec in enumerate(members):
            tokens = prefix_tokens(rec, len(prefix))
            shared_tokens[rec.call_index] = tokens
            already_cached = min(rec.cached_input_tokens, tokens)
            cost_now += _prefix_cost(pricing, rec, tokens, already_cached)
            if i == 0:  # the first call sends the prefix in full and fills the cache
                cost_after += _prefix_cost(pricing, rec, tokens, already_cached)
            else:
                cost_after += _prefix_cost(pricing, rec, tokens, tokens)
                changes[rec.call_index] = CallChange(cached_tokens=tokens - already_cached)
        if cost_after >= cost_now:
            continue

        avg = sum(prefix_tokens(r, len(prefix)) for r in members) // len(members)
        steps = sorted({r.step for r in members}, key=[r.step for r in members].index)
        findings.append(
            Finding(
                run_id=run_id,
                step=", ".join(steps),
                detector=NAME,
                evidence=f"{avg:,}-token shared prompt prefix sent in {len(members)} calls",
                cost_now=cost_now,
                cost_after=cost_after,
                suggestion="Cache the shared system prompt so it is billed at the cached rate "
                "after the first call, or trim it to what each step needs.",
                calls=[r.call_index for r in members],
                changes=changes,
            )
        )

    findings.extend(_large_context(run_id, calls, pricing, cfg, shared_tokens))
    return findings


def _large_context(run_id, calls, pricing, cfg, shared_tokens) -> list[Finding]:
    by_step: dict[str, list[tuple[TraceRecord, int]]] = defaultdict(list)
    for rec in calls:
        own = rec.input_tokens - shared_tokens.get(rec.call_index, 0)
        visible = max(rec.visible_output_tokens, 1)
        if own >= cfg["large_context_min_tokens"] and own / visible >= cfg["large_context_ratio"]:
            by_step[rec.step].append((rec, own))

    findings = []
    trim = cfg["context_trim_fraction"]
    for step, hits in by_step.items():
        changes = {rec.call_index: CallChange(removed_input_tokens=int(own * trim)) for rec, own in hits}
        cost_now = sum(_prefix_cost(pricing, rec, own, 0) for rec, own in hits)
        cost_after = sum(_prefix_cost(pricing, rec, own - int(own * trim), 0) for rec, own in hits)
        avg_own = sum(own for _, own in hits) // len(hits)
        avg_out = sum(rec.visible_output_tokens for rec, _ in hits) // len(hits)
        findings.append(
            Finding(
                run_id=run_id,
                step=step,
                detector=LARGE_CONTEXT,
                evidence=f"{avg_own:,} tokens of context for a {avg_out:,}-token answer "
                f"({len(hits)} call{'s' * (len(hits) > 1)})",
                cost_now=cost_now,
                cost_after=cost_after,
                suggestion=f"Send only the top-matching passages instead of the whole context "
                f"(estimate assumes {trim:.0%} of it is dropped).",
                calls=[rec.call_index for rec, _ in hits],
                changes=changes,
            )
        )
    return findings
