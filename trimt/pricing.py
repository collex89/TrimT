"""Prices from pricing.yaml. All costs in the report are computed here."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from .records import CallChange, TraceRecord

PER_TOKEN = 1_000_000
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "pricing.yaml"


@dataclass(frozen=True)
class ModelPrice:
    tier: str
    reasoning: bool
    input: float
    output: float
    cached_input: float


class UnknownModelError(KeyError):
    pass


class Pricing:
    def __init__(self, models: dict[str, ModelPrice], source: str = ""):
        self.models = models
        self.source = source

    @classmethod
    def load(cls, path: str | Path = DEFAULT_PATH) -> "Pricing":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        models = {
            name: ModelPrice(
                tier=m["tier"],
                reasoning=bool(m.get("reasoning", False)),
                input=float(m["input"]),
                output=float(m["output"]),
                cached_input=float(m["cached_input"]),
            )
            for name, m in data["models"].items()
        }
        return cls(models, data.get("source", ""))

    def get(self, model: str) -> ModelPrice:
        # Providers sometimes report "models/<name>" or a dated suffix.
        name = model.removeprefix("models/")
        if name in self.models:
            return self.models[name]
        for known in self.models:
            if name.startswith(known):
                return self.models[known]
        raise UnknownModelError(f"No price for model {model!r}; add it to pricing.yaml")

    def tier(self, model: str) -> str:
        return self.get(model).tier

    def cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> float:
        p = self.get(model)
        cached = min(cached_input_tokens, input_tokens)
        return (
            (input_tokens - cached) * p.input
            + cached * p.cached_input
            + output_tokens * p.output
        ) / PER_TOKEN

    def call_cost(self, rec: TraceRecord) -> float:
        return self.cost(rec.model, rec.input_tokens, rec.output_tokens, rec.cached_input_tokens)

    def changed_cost(self, rec: TraceRecord, change: CallChange) -> float:
        """Cost of a call after a fix is applied."""
        if change.removed:
            return 0.0
        model = change.new_model or rec.model
        output = rec.visible_output_tokens if change.drop_reasoning else rec.output_tokens
        input_tokens = max(rec.input_tokens - change.removed_input_tokens, 0)
        cached = min(rec.cached_input_tokens + change.cached_tokens, input_tokens)
        return self.cost(model, input_tokens, output, cached)
