"""Replay adapter tests: wire-format round trip, mission-hash
equivalence, and typed rejection of every malformed-log class."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

from salus.ops.replay import OpsLogError, ReplayOps, dump_ops  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402

import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402


def _dump_lines(ops) -> list[str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ops.jsonl"
        dump_ops(ops, p)
        return p.read_text(encoding="utf-8").splitlines()


def _load_from_lines(lines: list[str]) -> ReplayOps:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ops.jsonl"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
        return ReplayOps(p)


class TestRoundTrip(unittest.TestCase):
    def test_snapshots_identical_after_round_trip(self):
        ops = SyntheticOps(seed=7, ticks=30, scattered_start=15)
        replay = _load_from_lines(_dump_lines(ops))
        self.assertEqual(replay.ticks, ops.ticks)
        for t in range(ops.ticks):
            self.assertEqual(replay.snapshot(t), ops.snapshot(t))

    def test_mission_hash_identical_synthetic_vs_replay(self):
        m = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
        replay = _load_from_lines(_dump_lines(runner.build_ops(m)))
        _, h_syn = runner.run_once(m)
        _, h_rep = runner.run_once(m, ops=replay)
        self.assertEqual(h_syn, h_rep)


class TestWireValidation(unittest.TestCase):
    def _valid_lines(self) -> list[str]:
        return _dump_lines(SyntheticOps(seed=3, ticks=5, scattered_start=3))

    def test_invalid_json_rejected(self):
        lines = self._valid_lines()
        lines[2] = "{not json"
        with self.assertRaises(OpsLogError):
            _load_from_lines(lines)

    def test_tick_gap_rejected(self):
        lines = self._valid_lines()
        del lines[2]
        with self.assertRaises(OpsLogError):
            _load_from_lines(lines)

    def test_empty_belief_set_rejected(self):
        lines = self._valid_lines()
        rec = json.loads(lines[0])
        rec["beliefs"] = []
        lines[0] = json.dumps(rec)
        with self.assertRaises(OpsLogError):
            _load_from_lines(lines)

    def test_zero_capacity_rejected(self):
        lines = self._valid_lines()
        rec = json.loads(lines[0])
        rec["consolidation_capacity"] = 0
        lines[0] = json.dumps(rec)
        with self.assertRaises(OpsLogError):
            _load_from_lines(lines)

    def test_nonfinite_utility_rejected(self):
        lines = self._valid_lines()
        rec = json.loads(lines[0])
        rec["beliefs"][0]["utility"] = "Infinity"
        lines[0] = json.dumps(rec)  # json.loads round-trips Infinity
        lines[0] = lines[0].replace('"Infinity"', "Infinity")
        with self.assertRaises(OpsLogError):
            _load_from_lines(lines)

    def test_empty_log_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            p.write_text("", encoding="utf-8")
            with self.assertRaises(OpsLogError):
                ReplayOps(p)


if __name__ == "__main__":
    unittest.main()
