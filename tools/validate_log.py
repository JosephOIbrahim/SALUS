"""Ops-log validator: the pre-flight check for the integration seam.

Usage:  python tools\\validate_log.py <path-to-log>

A substrate instruments itself with OpsLogWriter (or writes the wire
format by hand), then runs this before pointing SALUS at the log. The
heavy lifting is ReplayOps itself — the same typed boundary validation
SALUS applies at load (ADR-0005), so "this tool said yes" and "SALUS
will load it" are the same fact. On success it prints a shape summary;
on violation it prints the typed OpsLogError message and exits 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from salus.ops.replay import OpsLogError, ReplayOps  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools\\validate_log.py <path-to-log>")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"no such file: {path}")
        return 2
    try:
        ops = ReplayOps(path)
    except OpsLogError as exc:
        print(f"INVALID ops log: {exc}")
        return 1
    belief_counts = [len(ops.snapshot(t).beliefs) for t in range(ops.ticks)]
    access_counts = [len(ops.snapshot(t).accesses) for t in range(ops.ticks)]
    print(f"ticks:             {ops.ticks} (contiguous 0..{ops.ticks - 1})")
    print(f"beliefs per tick:  {min(belief_counts)}..{max(belief_counts)}")
    print(f"accesses per tick: {min(access_counts)}..{max(access_counts)}")
    print("VALID - ready for SALUS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
