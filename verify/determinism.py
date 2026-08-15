"""Determinism gate, standalone: run twice, compare hashes, exit code."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402


def main() -> int:
    mission = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
    _, ha, _, hb = runner.run_twice(mission)
    print(f"run A: {ha}")
    print(f"run B: {hb}")
    print("DETERMINISTIC" if ha == hb else "NONDETERMINISTIC")
    return 0 if ha == hb else 1


if __name__ == "__main__":
    raise SystemExit(main())
