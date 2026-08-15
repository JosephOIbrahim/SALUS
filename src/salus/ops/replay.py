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


def dump_ops(ops: OpsReader, path: Path) -> None:
    """Serialize an OpsReader's full timeline to the wire format.
    Canonical bytes: sorted keys, compact separators, \\n endings,
    non-finite floats refused."""
    lines = []
    for t in range(ops.ticks):
        s = ops.snapshot(t)
        rec = {
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
        lines.append(
            json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


class ReplayOps:
    """File-backed equivalent of SyntheticOps: precomputed at load,
    snapshot(t) is a pure lookup. Read-only by construction."""

    def __init__(self, path: Path) -> None:
        timeline: list[OpsSnapshot] = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise OpsLogError(f"line {i}: not valid JSON") from exc
            timeline.append(self._parse(i, raw))
        if not timeline:
            raise OpsLogError("empty ops log")
        self._timeline: tuple[OpsSnapshot, ...] = tuple(timeline)

    @staticmethod
    def _parse(i: int, raw: dict) -> OpsSnapshot:
        try:
            tick = int(raw["tick"])
            accesses = tuple(
                AccessEvent(tick=int(a["tick"]), target=str(a["target"]))
                for a in raw["accesses"]
            )
            beliefs = tuple(
                BeliefState(
                    belief_id=str(b["belief_id"]),
                    utility=float(b["utility"]),
                    last_access_tick=int(b["last_access_tick"]),
                )
                for b in raw["beliefs"]
            )
            utility_total = float(raw["utility_total"])
            deposits = int(raw["deposits_since_consolidation"])
            capacity = int(raw["consolidation_capacity"])
        except (KeyError, TypeError, ValueError) as exc:
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
