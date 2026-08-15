"""Mission runner (SYNAPSE harness pattern): load mission -> calibrate ->
run -> timestamped evidence under runs/ + LATEST.txt. Runs the mission
twice, independently, for the replay-identity yes."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

from salus.emit.jsonl import result_hash, write_events, write_vitals  # noqa: E402
from salus.ops.interface import OpsReader  # noqa: E402
from salus.ops.replay import ReplayOps  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402
from salus.setpoints import absolute_band, calibrate_entropy_band  # noqa: E402
from salus.wake.floors import Floors  # noqa: E402
from salus.wake.policy import DEFAULT_RULES  # noqa: E402
from salus.wake.predicate import RunResult, SalusEngine  # noqa: E402

from mission_schema import Mission, MissionError, load_mission  # noqa: E402


def build_ops(m: Mission) -> OpsReader:
    """The mission's world: a recorded ops log when the mission names
    one, otherwise the seeded synthetic rig. A named-but-absent log is
    a typed MissionError — the mission is wrong, and saying so beats a
    FileNotFoundError traceback from inside the adapter."""
    if m.ops_log is None:
        return SyntheticOps(seed=m.seed, ticks=m.ticks, scattered_start=m.scattered_start)
    path = _REPO / m.ops_log
    if not path.is_file():
        raise MissionError(f"mission {m.name!r}: ops_log not found: {path}")
    return ReplayOps(path)


def calibrate(m: Mission, ops):
    probe = SalusEngine(
        ops=ops, bands=(), rules=(), floors=Floors(1, 1, 1),
        window=m.window, suppress_wakes=True,
    )
    baseline = probe.collect_vitals(m.calibration_ticks)
    entropy_band = calibrate_entropy_band(
        baseline, k_sigma=m.entropy_k_sigma, min_width=m.entropy_min_band
    )
    return (
        entropy_band,
        absolute_band("staleness_min_u", -1, m.staleness_enter, m.staleness_exit),
        absolute_band("consolidation_pressure", +1, m.pressure_enter, m.pressure_exit),
    )


def run_once(m: Mission, ops=None) -> tuple[RunResult, str]:
    """Run a mission. `ops` defaults to the mission's synthetic world;
    pass any OpsReader (e.g. ReplayOps) to run the same mission over a
    different source — the adapter-equivalence gate does exactly this."""
    if ops is None:
        ops = build_ops(m)
    bands = calibrate(m, ops)
    engine = SalusEngine(
        ops=ops,
        bands=bands,
        rules=DEFAULT_RULES,
        floors=Floors(m.refractory_ticks, m.budget_max, m.budget_window),
        window=m.window,
        counterfactual_ticks=m.counterfactual_ticks,
    )
    result = engine.run()
    return result, result_hash(result)


def run_twice(m: Mission) -> tuple[RunResult, str, RunResult, str]:
    ra, ha = run_once(m)
    rb, hb = run_once(m)
    return ra, ha, rb, hb


def write_evidence(m: Mission, r: RunResult, verdict: dict) -> Path:
    # Microsecond stamp + exist_ok=False: two runs must never silently
    # share (or overwrite) an evidence folder — a failing verdict.json
    # replaced by a passing one is the worst kind of quiet.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out = _REPO / "harness" / "runs" / f"{m.name}_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    write_vitals(out / "vitals.jsonl", r)
    write_events(out / "events.jsonl", r)
    (out / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8"
    )
    (_REPO / "harness" / "runs" / "LATEST.txt").write_text(out.name, encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    import probes

    mission = load_mission(Path(argv[1]))
    ra, ha, rb, hb = run_twice(mission)
    checks = probes.run_all(mission, ra, rb, ha, hb)
    verdict = {
        "mission": mission.name,
        "hash_a": ha,
        "hash_b": hb,
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
        "passed": all(ok for _, ok, _ in checks),
    }
    out = write_evidence(mission, ra, verdict)
    print(f"evidence: {out}")
    for n, ok, d in checks:
        print(f"  [{'YES' if ok else 'NO '}] {n} — {d}")
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
