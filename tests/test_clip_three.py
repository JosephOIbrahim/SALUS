"""clip_three: the mission-level R2 + R3 fixture.

The second recheck left a hole the unit tests could only half-fill —
R2_staleness and R3_pressure had end-to-end coverage through authored
OpsReaders, but no MISSION could fire them, so every five-yes green
rode on R1_entropy. clip_three closes it with an authored replay log.

Two properties are load-bearing here. The log is a committed fixture,
so the generator must reproduce it byte for byte (a fixture that drifts
from its generator is worse than no generator). And the mission must
fire exactly two wakes, R2 then R3, on exactly the ticks recorded
below — pinning the ticks is what makes a silent policy change loud.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))
sys.path.insert(0, str(_REPO / "tools"))

from salus.ops.replay import ReplayOps  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402

import make_clip_three  # noqa: E402
import probes  # noqa: E402
import runner  # noqa: E402
from mission_schema import MissionError, load_mission  # noqa: E402

_MISSION_PATH = _REPO / "harness" / "missions" / "clip_three.json"
_MISSION = load_mission(_MISSION_PATH)

_RA, _HA = runner.run_once(_MISSION)
_RB, _HB = runner.run_once(_MISSION)


class TestFixtureIntegrity(unittest.TestCase):
    def test_generator_reproduces_the_committed_log_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            fresh = Path(d) / "clip_three.ops.jsonl"
            make_clip_three.write_log(fresh)
            self.assertEqual(
                fresh.read_bytes(), make_clip_three.LOG_PATH.read_bytes()
            )

    def test_mission_selects_the_replay_adapter(self):
        self.assertIsInstance(runner.build_ops(_MISSION), ReplayOps)

    def test_a_mission_without_ops_log_still_gets_the_synthetic_world(self):
        clip_two = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
        self.assertIsNone(clip_two.ops_log)
        self.assertIsInstance(runner.build_ops(clip_two), SyntheticOps)


class TestClipThreeWakes(unittest.TestCase):
    def test_all_probes_pass(self):
        checks = probes.run_all(_MISSION, _RA, _RB, _HA, _HB)
        failed = [f"{n} — {d}" for n, ok, d in checks if not ok]
        self.assertEqual(failed, [])

    def test_exactly_two_wakes_r2_then_r3(self):
        self.assertEqual([e.rule_id for e in _RA.events],
                         ["R2_staleness", "R3_pressure"])
        self.assertEqual([e.summon_class for e in _RA.events],
                         ["verification_memories", "consolidation_summaries"])

    def test_wake_ticks_are_pinned(self):
        self.assertEqual([e.tick for e in _RA.events], [136, 193])

    def test_both_wakes_land_after_the_dormant_window(self):
        for e in _RA.events:
            self.assertGreaterEqual(e.tick, _MISSION.expectations.dormant_until)

    def test_second_wake_respects_the_refractory_floor(self):
        first, second = _RA.events
        self.assertGreaterEqual(second.tick - first.tick, _MISSION.refractory_ticks)
        self.assertEqual(_RA.floor_violations, 0)

    def test_entropy_never_reaches_its_band(self):
        """R1 must stay silent, or clip_three would prove nothing about
        the two quiet channels."""
        entropy_band = runner.calibrate(_MISSION, runner.build_ops(_MISSION))[0]
        peak = max(v.attention_entropy for v in _RA.vitals)
        self.assertLess(peak, entropy_band.enter)

    def test_crossing_values_are_on_the_firing_side(self):
        stale, pressure = _RA.events
        self.assertLess(stale.value, _MISSION.staleness_enter)
        self.assertGreater(pressure.value, _MISSION.pressure_enter)


class TestOpsLogSchema(unittest.TestCase):
    def _raw(self) -> dict:
        return json.loads(_MISSION_PATH.read_text(encoding="utf-8"))

    def _load(self, raw: dict):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.json"
            p.write_text(json.dumps(raw), encoding="utf-8")
            return load_mission(p)

    def test_absent_ops_log_points_at_a_missing_file_typed_not_traceback(self):
        raw = self._raw()
        raw["ops_log"] = "harness/missions/logs/no_such_log.ops.jsonl"
        mission = self._load(raw)
        with self.assertRaises(MissionError) as ctx:
            runner.build_ops(mission)
        self.assertIn("ops_log not found", str(ctx.exception))

    def test_non_string_ops_log_rejected(self):
        raw = self._raw()
        raw["ops_log"] = 7
        with self.assertRaises(MissionError):
            self._load(raw)

    def test_unknown_key_still_rejected_alongside_the_optional_one(self):
        raw = self._raw()
        raw["ops_logs"] = "harness/missions/logs/clip_three.ops.jsonl"  # typo'd
        with self.assertRaises(MissionError):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
