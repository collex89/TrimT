"""Wraps the Gemini client: every call goes to neatlogs and to a local JSONL file."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import neatlogs
from google import genai
from google.genai import errors, types

from .records import TraceRecord

MAX_RETRIES = 5


class TraceLogger:
    """Appends one JSON line per LLM call."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: TraceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


class TracedLLM:
    """A Gemini client whose calls are traced by neatlogs and logged locally.

    Call ``start_run`` before each agent run so calls are grouped by run.
    """

    def __init__(self, logger: TraceLogger, client=None, trace_with_neatlogs: bool = True):
        client = client or genai.Client()
        self.client = neatlogs.wrap(client) if trace_with_neatlogs else client
        self.logger = logger
        self.run_id = ""
        self.case_id = ""
        self._call_index = 0

    def start_run(self, run_id: str, case_id: str = "") -> None:
        self.run_id = run_id
        self.case_id = case_id
        self._call_index = 0

    def generate(
        self,
        *,
        step: str,
        model: str,
        prompt: str,
        system: str | None = None,
        thinking_budget: int | None = None,
        thinking_level: str | None = None,
    ) -> str:
        if not self.run_id:
            raise RuntimeError("call start_run() before generate()")

        config: dict[str, Any] = {"temperature": 0}
        if system:
            config["system_instruction"] = system
        if thinking_level is not None:
            config["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
        elif thinking_budget is not None:
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        started = time.perf_counter()
        response = self._call_with_retry(step, model, prompt, types.GenerateContentConfig(**config))
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = response.usage_metadata
        visible = usage.candidates_token_count or 0
        reasoning = usage.thoughts_token_count or 0
        text = response.text or ""

        self.logger.write(
            TraceRecord(
                run_id=self.run_id,
                step=step,
                call_index=self._call_index,
                model=response.model_version or model,
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=visible + reasoning,
                cached_input_tokens=usage.cached_content_token_count or 0,
                reasoning_tokens=reasoning,
                # System prompt first, as the model sees it, so shared prefixes line up.
                prompt=f"{system}\n\n{prompt}" if system else prompt,
                system_chars=len(system) + 2 if system else 0,
                output=text,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                case_id=self.case_id,
            )
        )
        self._call_index += 1
        return text

    def _call_with_retry(self, step: str, model: str, prompt: str, config):
        # One neatlogs span per agent step, so steps are named in the dashboard.
        @neatlogs.span(kind="CHAIN", name=step)
        def call():
            return self.client.models.generate_content(model=model, contents=prompt, config=config)

        for attempt in range(MAX_RETRIES):
            try:
                return call()
            except (errors.APIError, httpx.TransportError) as e:
                # Free-tier rate limits, transient server errors and dropped connections
                # are worth waiting out.
                code = getattr(e, "code", None)
                if (code is not None and code not in (429, 500, 503)) or attempt == MAX_RETRIES - 1:
                    raise
                wait = min(2 ** attempt * 5, 60)
                reason = code or type(e).__name__
                print(f"[trimt] {step}: {model} failed ({reason}), retrying in {wait}s", file=sys.stderr, flush=True)
                time.sleep(wait)
