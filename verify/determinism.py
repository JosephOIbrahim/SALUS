"""Determinism gate, cross-process: run A in this interpreter, run B in
a fresh interpreter under a different PYTHONHASHSEED, compare hashes.

Replay-identical must hold across processes, not merely within one —
this catches hash-seed-dependent iteration leaking into evidence, the
class a same-process gate is structurally blind to.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402


def one_hash() -> str:
    mission = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
    _, h = runner.run_once(mission)
    return h


def main() -> int:
    if "--hash-only" in sys.argv:
        print(one_hash())
        return 0
    ha = one_hash()
    env = dict(os.environ, PYTHONHASHSEED="4242")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--hash-only"],
        env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr)
        print("SUBPROCESS FAILED")
        return 1
    hb = proc.stdout.strip().splitlines()[-1]
    print(f"run A (in-process):          {ha}")
    print(f"run B (PYTHONHASHSEED=4242): {hb}")
    print("DETERMINISTIC" if ha == hb else "NONDETERMINISTIC")
    return 0 if ha == hb else 1


if __name__ == "__main__":
    raise SystemExit(main())
