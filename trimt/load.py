"""Loads trace records. Detectors only see TraceRecords, never where they came from."""

import json
from collections import defaultdict
from pathlib import Path

from .records import TraceRecord


def load_jsonl(path: str | Path) -> list[TraceRecord]:
    records = []
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(TraceRecord.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"{path}:{line_no}: bad trace record ({e})") from e
    return records


def group_by_run(records: list[TraceRecord]) -> dict[str, list[TraceRecord]]:
    runs: dict[str, list[TraceRecord]] = defaultdict(list)
    for rec in records:
        runs[rec.run_id].append(rec)
    for calls in runs.values():
        calls.sort(key=lambda r: r.call_index)
    return dict(runs)


def load_runs(*paths: str | Path) -> dict[str, list[TraceRecord]]:
    records = [rec for path in paths for rec in load_jsonl(path)]
    return group_by_run(records)
