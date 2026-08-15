"""Ops boundary: SALUS reads, never writes.

The four locked ops live in the substrate. SALUS sees them only through
this read surface. A synthetic implementation drives the harness; the
production adapter binds to the real substrate at integration (Gate 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AccessEvent:
    """One attention-log entry: attention touched `target` at `tick`."""

    tick: int
    target: str


@dataclass(frozen=True, slots=True)
class BeliefState:
    """A belief's decayed utility U at snapshot time (Moneta semantics)."""

    belief_id: str
    utility: float
    last_access_tick: int


@dataclass(frozen=True, slots=True)
class OpsSnapshot:
    """Read-only view of the four locked ops at one tick."""

    tick: int
    accesses: tuple[AccessEvent, ...]
    beliefs: tuple[BeliefState, ...]
    utility_total: float
    deposits_since_consolidation: int
    consolidation_capacity: int


class OpsReader(Protocol):
    """The only surface SALUS is permitted to hold. Read-only by shape.

    CONTRACT: snapshot(t) must be a PURE function of t — idempotent,
    side-effect-free, stable across repeated calls. The counterfactual
    fork shares this reader and replays overlapping spans; an impure
    reader corrupts the main path silently. Live substrate bindings
    must therefore record to the canonical ops log and be replayed
    (ops/replay.py), never served from live mutable state (ADR-0005).
    """

    @property
    def ticks(self) -> int: ...

    def snapshot(self, tick: int) -> OpsSnapshot: ...
