"""Runs the detectors over each run and totals cost before and after all fixes."""

from dataclasses import dataclass, field

from .detectors import DETECTORS
from .pricing import Pricing
from .records import CallChange, Finding, TraceRecord


@dataclass
class RunAnalysis:
    run_id: str
    case_id: str
    calls: list[TraceRecord]
    findings: list[Finding]
    cost_now: float
    cost_after: float
    call_costs_after: dict[int, float] = field(default_factory=dict)

    @property
    def saving(self) -> float:
        return self.cost_now - self.cost_after

    @property
    def percent_saved(self) -> float:
        return 100 * self.saving / self.cost_now if self.cost_now else 0.0


def merge_changes(changes: list[CallChange]) -> CallChange:
    """Combine every fix that touches one call (e.g. cheaper model AND cached prefix)."""
    merged = CallChange()
    for c in changes:
        merged.removed |= c.removed
        merged.drop_reasoning |= c.drop_reasoning
        merged.new_model = c.new_model or merged.new_model
        merged.cached_tokens += c.cached_tokens
        merged.removed_input_tokens += c.removed_input_tokens
    return merged


def analyze_run(run_id: str, calls: list[TraceRecord], pricing: Pricing, config: dict) -> RunAnalysis:
    findings: list[Finding] = []
    for section, detector in DETECTORS:
        findings.extend(detector.detect(run_id, calls, pricing, config[section]))
    findings.sort(key=lambda f: f.saving, reverse=True)

    per_call: dict[int, list[CallChange]] = {}
    for f in findings:
        for idx, change in f.changes.items():
            per_call.setdefault(idx, []).append(change)

    costs_after = {}
    for rec in calls:
        changes = per_call.get(rec.call_index)
        costs_after[rec.call_index] = (
            pricing.changed_cost(rec, merge_changes(changes)) if changes else pricing.call_cost(rec)
        )

    return RunAnalysis(
        run_id=run_id,
        case_id=calls[0].case_id if calls else "",
        calls=calls,
        findings=findings,
        cost_now=sum(pricing.call_cost(r) for r in calls),
        cost_after=sum(costs_after.values()),
        call_costs_after=costs_after,
    )


def analyze(runs: dict[str, list[TraceRecord]], pricing: Pricing, config: dict) -> list[RunAnalysis]:
    return [analyze_run(run_id, calls, pricing, config) for run_id, calls in runs.items()]


def measured_cost(calls: list[TraceRecord], pricing: Pricing) -> float:
    return sum(pricing.call_cost(r) for r in calls)
