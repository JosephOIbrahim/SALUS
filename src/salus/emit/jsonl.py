"""Canonical JSONL evidence. Deterministic bytes: sorted keys, compact
separators, \n endings. The result hash is the replay-identity check."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..wake.predicate import RunResult


def _canon(obj: object) -> str:
    # allow_nan=False: a non-finite float on the evidence path is a bug;
    # fail loudly instead of emitting the non-JSON literal `Infinity`.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_vitals(path: Path, result: RunResult) -> None:
    lines = [_canon(v.as_dict()) for v in result.vitals]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def write_events(path: Path, result: RunResult) -> None:
    lines = [_canon(e.to_record()) for e in result.events]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def result_hash(result: RunResult) -> str:
    payload = _canon(
        {
            "vitals": [v.as_dict() for v in result.vitals],
            "events": [e.to_record() for e in result.events],
            "floor_violations": result.floor_violations,
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
