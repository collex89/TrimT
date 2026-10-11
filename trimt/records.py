"""Data types shared by the logger, loader, detectors and report."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TraceRecord:
    """One LLM call, as written by the logger (one JSON line per call)."""

    run_id: str
    step: str
    call_index: int
    model: str
    input_tokens: int
    output_tokens: int  # all billed output tokens, including reasoning
    prompt: str
    output: str
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0  # billed "thinking" tokens, part of output_tokens
    latency_ms: int = 0
    timestamp: str = ""
    case_id: str = ""  # same input across runs, so before/after can be paired
    system_chars: int = 0  # length of the system prompt at the start of `prompt`
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def visible_output_tokens(self) -> int:
        return max(self.output_tokens - self.reasoning_tokens, 0)

    @property
    def system(self) -> str:
        return self.prompt[: self.system_chars]

    @property
    def request(self) -> str:
        """The prompt without its system prompt."""
        return self.prompt[self.system_chars :]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TraceRecord":
        known = set(cls.__dataclass_fields__) - {"extra"}
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs["extra"] = {k: v for k, v in data.items() if k not in known}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extra = data.pop("extra")
        data.update(extra)
        return data


@dataclass
class CallChange:
    """How a fix changes one call. Detectors emit these so totals never double count."""

    new_model: str | None = None  # price the call at this model instead
    drop_reasoning: bool = False  # the cheaper model doesn't spend thinking tokens
    cached_tokens: int = 0  # input tokens that would be billed at the cached rate
    removed_input_tokens: int = 0  # input tokens that would no longer be sent
    removed: bool = False  # the whole call would not happen


@dataclass
class Finding:
    run_id: str
    step: str
    detector: str
    evidence: str
    cost_now: float
    cost_after: float
    suggestion: str
    calls: list[int] = field(default_factory=list)
    changes: dict[int, CallChange] = field(default_factory=dict)

    @property
    def saving(self) -> float:
        return self.cost_now - self.cost_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step": self.step,
            "detector": self.detector,
            "evidence": self.evidence,
            "cost_now": round(self.cost_now, 6),
            "cost_after": round(self.cost_after, 6),
            "suggestion": self.suggestion,
            "calls": self.calls,
        }
