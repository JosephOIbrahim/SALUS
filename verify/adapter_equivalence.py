"""Adapter-faithfulness gate (ADR-0005): dump clip_two's synthetic
world to the canonical wire format, replay it through ReplayOps, run
the mission over both. Same world, same result hash — or the seam is
broken. This is the gate Gate-0 integration will reuse: point it at a
real recorded log instead of a synthetic dump."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402
from salus.ops.replay import ReplayOps, dump_ops  # noqa: E402


def main() -> int:
    mission = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
    synthetic = runner.build_ops(mission)
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "ops.jsonl"
        dump_ops(synthetic, log)
        replay = ReplayOps(log)
        _, h_syn = runner.run_once(mission)
        _, h_rep = runner.run_once(mission, ops=replay)
    print(f"synthetic: {h_syn}")
    print(f"replay:    {h_rep}")
    print("ADAPTER FAITHFUL" if h_syn == h_rep else "ADAPTER DIVERGENT")
    return 0 if h_syn == h_rep else 1


if __name__ == "__main__":
    raise SystemExit(main())
