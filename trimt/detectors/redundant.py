"""Detector 3: the same request made more than once in a run."""

import hashlib
import os
import re
from difflib import SequenceMatcher

from ..pricing import Pricing
from ..records import CallChange, Finding, TraceRecord

NAME = "redundant_calls"


def normalise(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt).strip().lower()


def similarity(a: str, b: str) -> float:
    """difflib-style ratio, 2*matches / (len(a)+len(b)).

    Prompts in one run usually share a long system prompt, so the common start and
    end are counted directly and only the differing middle goes through difflib.
    """
    if a == b:
        return 1.0
    total = len(a) + len(b)
    pre = len(os.path.commonprefix([a, b]))
    a, b = a[pre:], b[pre:]
    suf = len(os.path.commonprefix([a[::-1], b[::-1]]))
    a, b = a[: len(a) - suf], b[: len(b) - suf]
    middle = sum(m.size for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return 2 * (pre + suf + middle) / total


def _similar(a: str, b: str, threshold: float) -> bool:
    # The ratio can't reach the threshold if the lengths are too far apart.
    if 2 * min(len(a), len(b)) / max(len(a) + len(b), 1) < threshold:
        return False
    return similarity(a, b) >= threshold


def find_duplicate_groups(calls: list[TraceRecord], threshold: float) -> list[list[TraceRecord]]:
    """Groups of calls to the same model with the same (or near-identical) prompt.

    Near-identical is judged on the request alone, with the same system prompt: a long
    shared system prompt would otherwise make every call in a run look alike.
    """
    norm = [normalise(c.prompt) for c in calls]
    digest = [hashlib.sha256(n.encode()).hexdigest() for n in norm]
    system = [normalise(c.system) for c in calls]
    request = [normalise(c.request) for c in calls]

    parent = list(range(len(calls)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(calls)):
        for j in range(i + 1, len(calls)):
            if calls[i].model != calls[j].model:
                continue
            if digest[i] == digest[j] or (
                system[i] == system[j] and _similar(request[i], request[j], threshold)
            ):
                parent[root(j)] = root(i)

    groups: dict[int, list[TraceRecord]] = {}
    for i, c in enumerate(calls):
        groups.setdefault(root(i), []).append(c)
    return [g for g in groups.values() if len(g) > 1]


def detect(run_id: str, calls: list[TraceRecord], pricing: Pricing, cfg: dict) -> list[Finding]:
    findings = []
    for group in find_duplicate_groups(calls, cfg["similarity"]):
        first, dupes = group[0], group[1:]
        cost_now = sum(pricing.call_cost(c) for c in dupes)
        steps = sorted({c.step for c in group}, key=[c.step for c in group].index)
        exact = all(normalise(c.prompt) == normalise(first.prompt) for c in dupes)
        findings.append(
            Finding(
                run_id=run_id,
                step=", ".join(steps),
                detector=NAME,
                evidence=f"{'Identical' if exact else 'Near-identical'} request to {first.model} "
                f"made {len(group)} times (calls {', '.join(str(c.call_index) for c in group)})",
                cost_now=cost_now,
                cost_after=0.0,
                suggestion=f"Reuse the result of the first {first.step} call instead of asking again.",
                calls=[c.call_index for c in dupes],
                changes={c.call_index: CallChange(removed=True) for c in dupes},
            )
        )
    return findings
