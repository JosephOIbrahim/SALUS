"""Replay adapter: OpsReader over a recorded canonical ops log.

The integration seam (ADR-0005): the substrate exports its byproducts
as one canonical jsonl line per tick; SALUS replays them without ever
holding a live handle. A recorded log is replayable by definition, so
the determinism doctrine survives integration untouched.

Validation is typed at the boundary — a malformed log is an
OpsLogError at load, not a raw builtin exception mid-run (doctrine:
typed failure is detectable; prose failure isn't).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .interface import AccessEvent, BeliefState, OpsReader, OpsSnapshot


class OpsLogError(Exception):
    """The ops log violates the wire contract."""


def snapshot_record(s: OpsSnapshot) -> dict:
    """The wire dict for one snapshot — the single source of truth for
    field names on the ops-log seam (ADR-0005). dump_ops and the live
    shim (ops/shim.py) both serialize through this shape."""
    return {
        "tick": s.tick,
        "accesses": [{"tick": a.tick, "target": a.target} for a in s.accesses],
        "beliefs": [
            {
                "belief_id": b.belief_id,
                "utility": b.utility,
                "last_access_tick": b.last_access_tick,
            }
            for b in s.beliefs
        ],
        "utility_total": s.utility_total,
        "deposits_since_consolidation": s.deposits_since_consolidation,
        "consolidation_capacity": s.consolidation_capacity,
    }


def record_line(rec: dict) -> str:
    """Canonical json for one wire record: sorted keys, compact
    separators, non-finite floats refused."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)


def dump_ops(ops: OpsReader, path: Path) -> None:
    """Serialize an OpsReader's full timeline to the wire format.
    Canonical bytes: sorted keys, compact separators, \\n endings,
    non-finite floats refused. Refuses a zero-tick timeline — an empty
    log is exactly what ReplayOps rejects, and the violation belongs
    at the recording end of the seam."""
    if ops.ticks == 0:
        raise OpsLogError("refusing to write an empty ops log (zero ticks)")
    lines = [record_line(snapshot_record(ops.snapshot(t))) for t in range(ops.ticks)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


class _NonFiniteTokenError(ValueError):
    """Internal: a non-finite JSON token (Infinity/-Infinity/NaN) was
    seen during parse. Converted to OpsLogError with line context."""


def _reject_nonfinite_token(token: str) -> float:
    raise _NonFiniteTokenError(f"non-finite JSON token {token}")


class ReplayOps:
    """File-backed equivalent of SyntheticOps: precomputed at load,
    snapshot(t) is a pure lookup. Read-only by construction."""

    def __init__(self, path: Path) -> None:
        # Canonical framing is enforced, not assumed: a hand-rolled
        # emitter whose bytes diverge from record_line output must fail
        # here, loudly, or the byte-identity doctrine silently rots.
        # newline="" or universal-newline translation would silently
        # hide the very CRLF bytes this check exists to catch.
        with path.open("r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        if "\r" in text:
            raise OpsLogError("CR byte in log — the wire format is LF-only")
        if text and not text.endswith("\n"):
            raise OpsLogError("missing final newline — not canonical bytes")
        timeline: list[OpsSnapshot] = []
        lines = text.split("\n")[:-1] if text else []
        for i, line in enumerate(lines):
            if not line.isascii():
                raise OpsLogError(
                    f"line {i}: non-ASCII bytes — canonical json escapes to ASCII"
                )
            try:
                raw = json.loads(line, parse_constant=_reject_nonfinite_token)
            except json.JSONDecodeError as exc:
                raise OpsLogError(f"line {i}: not valid JSON") from exc
            except _NonFiniteTokenError as exc:
                raise OpsLogError(f"line {i}: {exc}") from exc
            timeline.append(self._parse(i, raw))
        if not timeline:
            raise OpsLogError("empty ops log")
        self._timeline: tuple[OpsSnapshot, ...] = tuple(timeline)

    @staticmethod
    def _parse(i: int, raw: dict) -> OpsSnapshot:
        # Types are checked, never coerced: int(1.5) truncating a tick
        # or bool passing as capacity accepts bytes the writer could
        # never produce — the asymmetry drift trap.
        def req_int(v: object, name: str) -> int:
            if isinstance(v, bool) or not isinstance(v, int):
                raise OpsLogError(f"line {i}: {name} must be an integer")
            return v

        def req_float(v: object, name: str) -> float:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise OpsLogError(f"line {i}: {name} must be a number")
            return float(v)

        def req_str(v: object, name: str) -> str:
            if not isinstance(v, str):
                raise OpsLogError(f"line {i}: {name} must be a string")
            return v

        try:
            tick = req_int(raw["tick"], "tick")
            accesses = tuple(
                AccessEvent(
                    tick=req_int(a["tick"], "access tick"),
                    target=req_str(a["target"], "access target"),
                )
                for a in raw["accesses"]
            )
            beliefs = tuple(
                BeliefState(
                    belief_id=req_str(b["belief_id"], "belief_id"),
                    utility=req_float(b["utility"], "utility"),
                    last_access_tick=req_int(b["last_access_tick"], "last_access_tick"),
                )
                for b in raw["beliefs"]
            )
            utility_total = req_float(raw["utility_total"], "utility_total")
            deposits = req_int(raw["deposits_since_consolidation"], "deposits_since_consolidation")
            capacity = req_int(raw["consolidation_capacity"], "consolidation_capacity")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise OpsLogError(f"line {i}: malformed snapshot: {exc}") from exc
        if tick != i:
            raise OpsLogError(
                f"line {i}: tick {tick} — ticks must be contiguous from 0"
            )
        if not beliefs:
            raise OpsLogError(f"line {i}: empty belief set — staleness is undefined")
        if capacity < 1:
            raise OpsLogError(f"line {i}: consolidation_capacity must be >= 1")
        if not math.isfinite(utility_total) or any(
            not math.isfinite(b.utility) for b in beliefs
        ):
            raise OpsLogError(f"line {i}: non-finite utility")
        return OpsSnapshot(
            tick=tick,
            accesses=accesses,
            beliefs=beliefs,
            utility_total=utility_total,
            deposits_since_consolidation=deposits,
            consolidation_capacity=capacity,
        )

    @property
    def ticks(self) -> int:
        return len(self._timeline)

    def snapshot(self, tick: int) -> OpsSnapshot:
        return self._timeline[tick]
