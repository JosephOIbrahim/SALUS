"""Live-binding shim: append-only writer for the canonical ops log.

ADR-0005 makes recording the integration seam: a live substrate
binding records one canonical jsonl line per tick, and SALUS replays
the log — it never holds a live mutable handle. This writer is the
recording half. It enforces the same wire contract ReplayOps enforces
at load (contiguous ticks from 0, non-empty beliefs, capacity >= 1,
finite floats), so a log it produces is replayable by construction —
a violation is a typed OpsLogError at append time, not a surprise at
load time.

Serialization goes through replay.snapshot_record / record_line — the
single source of truth for canonical bytes — so writer output is
byte-identical to dump_ops over the same timeline.
"""

from __future__ import annotations

import math
from pathlib import Path

from .interface import OpsSnapshot
from .replay import OpsLogError, record_line, snapshot_record


class OpsLogWriter:
    """Append-only ops-log recorder. One canonical line per append,
    flushed immediately so a crash mid-run leaves a valid prefix."""

    def __init__(self, path: Path, overwrite: bool = False) -> None:
        if path.exists() and not overwrite:
            raise OpsLogError(
                f"{path}: ops log already exists — pass overwrite=True to replace"
            )
        # newline="" so Windows never translates \n into \r\n; the
        # wire format is \n-terminated bytes, identical on every OS.
        self._fh = path.open("w", encoding="utf-8", newline="")
        self._next_tick = 0

    def append(self, snapshot: OpsSnapshot) -> None:
        """Validate against the wire contract, then write one line."""
        if self._fh.closed:
            raise OpsLogError("append on a closed OpsLogWriter")
        if snapshot.tick != self._next_tick:
            raise OpsLogError(
                f"tick {snapshot.tick}: expected {self._next_tick} — "
                "ticks must be contiguous from 0"
            )
        if not snapshot.beliefs:
            raise OpsLogError(
                f"tick {snapshot.tick}: empty belief set — staleness is undefined"
            )
        if snapshot.consolidation_capacity < 1:
            raise OpsLogError(
                f"tick {snapshot.tick}: consolidation_capacity must be >= 1"
            )
        if not math.isfinite(snapshot.utility_total) or any(
            not math.isfinite(b.utility) for b in snapshot.beliefs
        ):
            raise OpsLogError(f"tick {snapshot.tick}: non-finite utility")
        self._fh.write(record_line(snapshot_record(snapshot)) + "\n")
        self._fh.flush()
        self._next_tick += 1

    def close(self) -> None:
        """Close the log. A clean close with zero appends is refused —
        an empty file is exactly the log ReplayOps rejects, and the
        violation belongs at the recording end of the seam."""
        if self._fh.closed:
            return
        empty = self._next_tick == 0
        self._fh.close()
        if empty:
            raise OpsLogError("closed with zero appends — empty ops log")

    def __enter__(self) -> OpsLogWriter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self._fh.close()  # never mask the in-flight exception
        else:
            self.close()
