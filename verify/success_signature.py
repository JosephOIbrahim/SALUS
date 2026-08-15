"""The gate: blueprint section 9. Five yeses = v1 shipped.

Runs clip_two twice, judges with the five probes, writes evidence,
prints the signature, exits 0 only on 5/5.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

import probes  # noqa: E402
import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402

LINES = (
    "dormant while entropy low",
    "wake fires on the crossing",
    "identical replay, run twice",
    "no floor breached",
    "wake event visible as data",
)


def main() -> int:
    mission = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
    ra, ha, rb, hb = runner.run_twice(mission)
    checks = probes.run_all(mission, ra, rb, ha, hb)
    verdict = {
        "mission": mission.name,
        "hash_a": ha,
        "hash_b": hb,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
        "passed": all(ok for _, ok, _ in checks),
    }
    runner.write_evidence(mission, ra, verdict)
    print(f"SALUS v0.1.0 — success signature — mission: {mission.name}")
    for i, (name, ok, detail) in enumerate(checks, start=1):
        dots = "." * (38 - len(name))
        print(f"  [{i}] {name} {dots} {'YES' if ok else 'NO'}  ({detail})")
    score = sum(1 for _, ok, _ in checks if ok)
    print(f"  {score}/5 — {'v1 SHIPPED' if score == 5 else 'NOT SHIPPED'}")
    return 0 if score == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
