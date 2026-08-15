"""End-to-end coverage for the promo-facing surfaces: the instrumented
agent example must actually run and wake, and the log validator CLI
must say yes to a good log and no (typed, exit 1) to a corrupted one.
Both run as real subprocesses — the same invocation a user would type."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from salus.ops.replay import dump_ops  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(_REPO), capture_output=True, text=True,
    )


class TestInstrumentedAgentExample(unittest.TestCase):
    def test_example_exits_zero_and_wakes(self):
        proc = _run(_REPO / "examples" / "instrumented_agent.py")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        # The wake must land as a canonical event record, not just prose.
        self.assertIn('"rule_id"', proc.stdout)
        self.assertIn("orientation_anchors", proc.stdout)
        self.assertIn("wake at tick", proc.stdout)


class TestValidateLogCLI(unittest.TestCase):
    def _write_good_log(self, d: str) -> Path:
        p = Path(d) / "ops.jsonl"
        dump_ops(SyntheticOps(seed=3, ticks=12, scattered_start=6), p)
        return p

    def test_good_log_validates(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_good_log(d)
            proc = _run(_REPO / "tools" / "validate_log.py", str(p))
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("VALID - ready for SALUS", proc.stdout)

    def test_corrupted_log_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_good_log(d)
            lines = p.read_text(encoding="utf-8").splitlines()
            del lines[2]  # tick gap — a contiguity violation
            p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
            proc = _run(_REPO / "tools" / "validate_log.py", str(p))
            self.assertEqual(proc.returncode, 1, msg=proc.stdout + proc.stderr)
            self.assertIn("INVALID ops log", proc.stdout)
            self.assertIn("contiguous", proc.stdout)


if __name__ == "__main__":
    unittest.main()
