"""Strict-reader tests (post-shim adversarial verify): the reader must
reject every non-canonical shape the writer cannot produce, with typed
errors — no raw builtins escaping, no coercion accepting drift."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from salus.ops.replay import OpsLogError, ReplayOps, dump_ops  # noqa: E402
from salus.ops.shim import OpsLogWriter  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402


def _valid_lines() -> list[str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ops.jsonl"
        dump_ops(SyntheticOps(seed=3, ticks=4, scattered_start=2), p)
        return p.read_text(encoding="utf-8").splitlines()


def _load_text(text: str) -> ReplayOps:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ops.jsonl"
        p.write_text(text, encoding="utf-8", newline="")
        return ReplayOps(p)


def _mutate_line0(**changes) -> str:
    lines = _valid_lines()
    rec = json.loads(lines[0])
    rec.update(changes)
    lines[0] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return "\n".join(lines) + "\n"


class TestStrictFraming(unittest.TestCase):
    def test_crlf_rejected(self):
        text = "\r\n".join(_valid_lines()) + "\r\n"
        with self.assertRaises(OpsLogError):
            _load_text(text)

    def test_missing_final_newline_rejected(self):
        text = "\n".join(_valid_lines())  # no trailing \n
        with self.assertRaises(OpsLogError):
            _load_text(text)

    def test_non_ascii_rejected(self):
        lines = _valid_lines()
        rec = json.loads(lines[0])
        rec["accesses"][0]["target"] = "b z"
        lines[0] = json.dumps(rec, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False)
        with self.assertRaises(OpsLogError):
            _load_text("\n".join(lines) + "\n")


class TestStrictTypes(unittest.TestCase):
    def test_infinity_token_is_typed_not_overflow(self):
        lines = _valid_lines()
        lines[0] = lines[0].replace('"tick":0', '"tick":Infinity')
        with self.assertRaises(OpsLogError):
            _load_text("\n".join(lines) + "\n")

    def test_float_tick_rejected(self):
        with self.assertRaises(OpsLogError):
            _load_text(_mutate_line0(tick=0.0))

    def test_string_tick_rejected(self):
        with self.assertRaises(OpsLogError):
            _load_text(_mutate_line0(tick="0"))

    def test_bool_capacity_rejected(self):
        with self.assertRaises(OpsLogError):
            _load_text(_mutate_line0(consolidation_capacity=True))


class TestEmptyLogRefusedAtWrite(unittest.TestCase):
    def test_dump_ops_refuses_zero_ticks(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OpsLogError):
                dump_ops(SyntheticOps(seed=1, ticks=0, scattered_start=0),
                         Path(d) / "ops.jsonl")

    def test_writer_zero_append_close_refused(self):
        with tempfile.TemporaryDirectory() as d:
            w = OpsLogWriter(Path(d) / "ops.jsonl")
            with self.assertRaises(OpsLogError):
                w.close()

    def test_exit_does_not_mask_inflight_exception(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                with OpsLogWriter(Path(d) / "ops.jsonl"):
                    raise RuntimeError("in-flight")


if __name__ == "__main__":
    unittest.main()
