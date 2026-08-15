"""Unit tests: channels, windows, hysteresis, contract, policy order."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salus.ops.interface import AccessEvent  # noqa: E402
from salus.setpoints import Band, Hysteresis  # noqa: E402
from salus.vitals.channels import attention_entropy  # noqa: E402
from salus.vitals.windows import kahan_sum, slope  # noqa: E402
from salus.wake.contract import (  # noqa: E402
    ExpiredError, OutOfRangeError, WakeContract, validate,
)
from salus.wake.policy import DEFAULT_RULES  # noqa: E402


def ev(targets):
    return [AccessEvent(tick=0, target=t) for t in targets]


class TestChannels(unittest.TestCase):
    def test_entropy_uniform_is_log2_n(self):
        events = ev(["a", "b", "c", "d"])
        self.assertAlmostEqual(attention_entropy(events), 2.0, places=12)

    def test_entropy_single_target_is_zero(self):
        self.assertEqual(attention_entropy(ev(["a", "a", "a"])), 0.0)

    def test_kahan_survives_cancellation(self):
        self.assertEqual(kahan_sum([1e16, 1.0, -1e16]), 1.0)

    def test_slope_linear_exact(self):
        self.assertAlmostEqual(slope([3.0, 5.0, 7.0, 9.0]), 2.0, places=12)


class TestHysteresis(unittest.TestCase):
    def test_fires_once_then_rearms(self):
        band = Band("attention_entropy", +1, enter=2.0, exit=1.0)
        hys = Hysteresis([band])
        seq = [0.5, 2.5, 2.6, 2.7, 0.5, 2.5]
        fires = [hys.update("attention_entropy", v) for v in seq]
        self.assertEqual(fires, [False, True, False, False, False, True])

    def test_down_cross_direction(self):
        band = Band("staleness_min_u", -1, enter=0.1, exit=0.2)
        hys = Hysteresis([band])
        fires = [hys.update("staleness_min_u", v) for v in [0.5, 0.05, 0.05, 0.5, 0.05]]
        self.assertEqual(fires, [False, True, False, False, True])


class TestContract(unittest.TestCase):
    def _contract(self):
        return WakeContract("orientation_anchors", 0.0, 10.0, "salus.policy", 5, 20)

    def test_valid(self):
        self.assertTrue(validate(self._contract(), 3.0, now=10))

    def test_expired(self):
        with self.assertRaises(ExpiredError):
            validate(self._contract(), 3.0, now=25)

    def test_out_of_range(self):
        with self.assertRaises(OutOfRangeError):
            validate(self._contract(), 99.0, now=10)


class TestPolicy(unittest.TestCase):
    def test_rule_order_is_fixed(self):
        self.assertEqual(
            [r.rule_id for r in DEFAULT_RULES],
            ["R1_entropy", "R2_staleness", "R3_pressure"],
        )


if __name__ == "__main__":
    unittest.main()
