"""Floor tests: causal mask, refractory, budget, end-to-end zero violations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salus.ops.synthetic import SyntheticOps  # noqa: E402
from salus.setpoints import absolute_band, calibrate_entropy_band  # noqa: E402
from salus.wake.floors import FloorGuard, Floors, FloorViolation  # noqa: E402
from salus.wake.policy import DEFAULT_RULES  # noqa: E402
from salus.wake.predicate import SalusEngine  # noqa: E402


class TestFloorGuard(unittest.TestCase):
    def test_causal_mask_raises(self):
        guard = FloorGuard(Floors(10, 2, 100))
        with self.assertRaises(FloorViolation):
            guard.causal_check(query_tick=5, now=4)
        self.assertEqual(guard.violations, 1)

    def test_refractory_blocks(self):
        guard = FloorGuard(Floors(refractory_ticks=10, budget_max=5, budget_window=100))
        guard.record_wake(50)
        self.assertFalse(guard.clear_to_wake(55))
        self.assertTrue(guard.clear_to_wake(60))

    def test_budget_blocks(self):
        guard = FloorGuard(Floors(refractory_ticks=1, budget_max=2, budget_window=100))
        guard.record_wake(10)
        guard.record_wake(20)
        self.assertFalse(guard.clear_to_wake(30))


class TestEngineFloors(unittest.TestCase):
    def test_mini_run_zero_violations_and_wakes(self):
        ops = SyntheticOps(seed=7, ticks=90, scattered_start=50)
        probe = SalusEngine(
            ops=ops, bands=(), rules=(), floors=Floors(1, 1, 1),
            window=16, suppress_wakes=True,
        )
        while probe._tick < 40:
            probe._step()
        bands = (
            calibrate_entropy_band(probe._vitals),
            absolute_band("staleness_min_u", -1, 0.02, 0.04),
            absolute_band("consolidation_pressure", +1, 0.9, 0.8),
        )
        engine = SalusEngine(
            ops=SyntheticOps(seed=7, ticks=90, scattered_start=50),
            bands=bands, rules=DEFAULT_RULES,
            floors=Floors(refractory_ticks=30, budget_max=2, budget_window=90),
            window=16, counterfactual_ticks=5,
        )
        result = engine.run()
        self.assertEqual(result.floor_violations, 0)
        self.assertGreaterEqual(len(result.events), 1)
        for e in result.events:
            self.assertGreaterEqual(e.tick, 50)


if __name__ == "__main__":
    unittest.main()
