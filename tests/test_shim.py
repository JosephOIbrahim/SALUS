"""Shim tests: writer bytes identical to dump_ops, writer logs
replayable and mission-hash faithful, and typed rejection of every
contract violation at append time."""

from __future__ import annotations

import dataclasses
import math
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

from salus.ops.replay import OpsLogError, ReplayOps, dump_ops  # noqa: E402
from salus.ops.shim import OpsLogWriter  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402

import runner  # noqa: E402
from mission_schema import load_mission  # noqa: E402


def _write_via_shim(ops, path: Path) -> None:
    with OpsLogWriter(path) as w:
        for t in range(ops.ticks):
            w.append(ops.snapshot(t))


class TestWriterEquivalence(unittest.TestCase):
    def test_writer_bytes_identical_to_dump_ops(self):
        ops = SyntheticOps(seed=7, ticks=30, scattered_start=15)
        with tempfile.TemporaryDirectory() as d:
            p_dump = Path(d) / "dump.jsonl"
            p_shim = Path(d) / "shim.jsonl"
            dump_ops(ops, p_dump)
            _write_via_shim(ops, p_shim)
            self.assertEqual(p_shim.read_bytes(), p_dump.read_bytes())

    def test_replay_of_writer_log_equals_originals(self):
        ops = SyntheticOps(seed=11, ticks=25, scattered_start=12)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            _write_via_shim(ops, p)
            replay = ReplayOps(p)
            self.assertEqual(replay.ticks, ops.ticks)
            for t in range(ops.ticks):
                self.assertEqual(replay.snapshot(t), ops.snapshot(t))

    def test_mission_hash_identical_synthetic_vs_writer_log(self):
        m = load_mission(_REPO / "harness" / "missions" / "clip_two.json")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            _write_via_shim(runner.build_ops(m), p)
            _, h_syn = runner.run_once(m)
            _, h_rep = runner.run_once(m, ops=ReplayOps(p))
            self.assertEqual(h_syn, h_rep)


class TestAppendValidation(unittest.TestCase):
    def setUp(self):
        self._ops = SyntheticOps(seed=3, ticks=5, scattered_start=3)

    def _writer(self, d: str) -> OpsLogWriter:
        return OpsLogWriter(Path(d) / "ops.jsonl")

    def test_out_of_order_tick_rejected(self):
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            with self.assertRaises(OpsLogError):
                w.append(self._ops.snapshot(1))
            w.append(self._ops.snapshot(0))  # non-empty for the close guard

    def test_repeated_tick_rejected(self):
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            w.append(self._ops.snapshot(0))
            with self.assertRaises(OpsLogError):
                w.append(self._ops.snapshot(0))

    def test_empty_belief_set_rejected(self):
        bad = dataclasses.replace(self._ops.snapshot(0), beliefs=())
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            with self.assertRaises(OpsLogError):
                w.append(bad)
            w.append(self._ops.snapshot(0))  # non-empty for the close guard

    def test_zero_capacity_rejected(self):
        bad = dataclasses.replace(self._ops.snapshot(0), consolidation_capacity=0)
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            with self.assertRaises(OpsLogError):
                w.append(bad)
            w.append(self._ops.snapshot(0))  # non-empty for the close guard

    def test_nonfinite_belief_utility_rejected(self):
        s = self._ops.snapshot(0)
        beliefs = (dataclasses.replace(s.beliefs[0], utility=math.inf),) + s.beliefs[1:]
        bad = dataclasses.replace(s, beliefs=beliefs)
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            with self.assertRaises(OpsLogError):
                w.append(bad)
            w.append(self._ops.snapshot(0))  # non-empty for the close guard

    def test_nonfinite_utility_total_rejected(self):
        bad = dataclasses.replace(self._ops.snapshot(0), utility_total=math.nan)
        with tempfile.TemporaryDirectory() as d, self._writer(d) as w:
            with self.assertRaises(OpsLogError):
                w.append(bad)
            w.append(self._ops.snapshot(0))  # non-empty for the close guard

    def test_rejected_append_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            with OpsLogWriter(p) as w:
                w.append(self._ops.snapshot(0))
                with self.assertRaises(OpsLogError):
                    w.append(self._ops.snapshot(3))
            self.assertEqual(len(p.read_text(encoding="utf-8").splitlines()), 1)

    def test_append_after_close_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            w = self._writer(d)
            w.append(self._ops.snapshot(0))
            w.close()
            with self.assertRaises(OpsLogError):
                w.append(self._ops.snapshot(1))


class TestFileHandling(unittest.TestCase):
    def test_existing_file_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            p.write_text("prior\n", encoding="utf-8")
            with self.assertRaises(OpsLogError):
                OpsLogWriter(p)

    def test_overwrite_replaces_existing_file(self):
        ops = SyntheticOps(seed=3, ticks=5, scattered_start=3)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ops.jsonl"
            p.write_text("prior\n", encoding="utf-8")
            with OpsLogWriter(p, overwrite=True) as w:
                for t in range(ops.ticks):
                    w.append(ops.snapshot(t))
            replay = ReplayOps(p)
            self.assertEqual(replay.ticks, ops.ticks)


if __name__ == "__main__":
    unittest.main()
