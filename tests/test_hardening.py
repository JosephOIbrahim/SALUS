"""Hardening tests: probe falsification (a judge must be able to say
NO), contract finiteness + strict JSON, channel semantics, mission
schema rejection, engine construction validation."""

from __future__ import annotations

import dataclasses
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "harness"))

from salus.emit.jsonl import _canon  # noqa: E402
from salus.ops.interface import AccessEvent  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402
from salus.setpoints import absolute_band, calibrate_entropy_band  # noqa: E402
from salus.vitals.channels import novel_touch_ratio, revisit_rate  # noqa: E402
from salus.wake.floors import Floors  # noqa: E402
from salus.wake.policy import DEFAULT_RULES, Rule  # noqa: E402
from salus.wake.predicate import SalusEngine  # noqa: E402

import probes  # noqa: E402
from mission_schema import Expectations, Mission, MissionError, load_mission  # noqa: E402


def mini_mission() -> Mission:
    return Mission(
        name="mini", seed=7, ticks=90, scattered_start=50, window=16,
        calibration_ticks=40, refractory_ticks=30, budget_max=2,
        budget_window=90, counterfactual_ticks=5, entropy_k_sigma=4.0,
        entropy_min_band=0.5, staleness_enter=0.02, staleness_exit=0.04,
        pressure_enter=0.9, pressure_exit=0.8,
        expectations=Expectations(1, 2, 50, True),
    )


def mini_run(m: Mission):
    ops = SyntheticOps(seed=m.seed, ticks=m.ticks, scattered_start=m.scattered_start)
    probe = SalusEngine(
        ops=ops, bands=(), rules=(), floors=Floors(1, 1, 1),
        window=m.window, suppress_wakes=True,
    )
    baseline = probe.collect_vitals(m.calibration_ticks)
    bands = (
        calibrate_entropy_band(baseline),
        absolute_band("staleness_min_u", -1, m.staleness_enter, m.staleness_exit),
        absolute_band("consolidation_pressure", +1, m.pressure_enter, m.pressure_exit),
    )
    engine = SalusEngine(
        ops=SyntheticOps(seed=m.seed, ticks=m.ticks, scattered_start=m.scattered_start),
        bands=bands, rules=DEFAULT_RULES,
        floors=Floors(m.refractory_ticks, m.budget_max, m.budget_window),
        window=m.window, counterfactual_ticks=m.counterfactual_ticks,
    )
    return engine.run()


_M = mini_mission()
_R = mini_run(_M)


class TestCounterfactualFalsification(unittest.TestCase):
    def test_probe_passes_on_honest_run(self):
        self.assertGreaterEqual(len(_R.events), 1)
        self.assertTrue(probes.counterfactual_divergence_zero(_M, _R))

    def test_probe_fails_on_corrupted_hash(self):
        bad = dataclasses.replace(_R.events[0], counterfactual_hash="0" * 64)
        corrupted = dataclasses.replace(_R, events=(bad,) + _R.events[1:])
        self.assertFalse(probes.counterfactual_divergence_zero(_M, corrupted))


class TestContractRange(unittest.TestCase):
    def test_bounds_finite_and_satisfied_by_firing_value(self):
        for e in _R.events:
            self.assertTrue(math.isfinite(e.contract.lo))
            self.assertTrue(math.isfinite(e.contract.hi))
            self.assertLessEqual(e.contract.lo, e.value)
            self.assertLessEqual(e.value, e.contract.hi)

    def test_event_record_is_strict_json(self):
        line = _canon(_R.events[0].to_record())
        json.loads(line)
        self.assertNotIn("Infinity", line)

    def test_canon_rejects_nonfinite(self):
        with self.assertRaises(ValueError):
            _canon({"x": float("inf")})


class TestChannelSemantics(unittest.TestCase):
    def test_revisit_rate(self):
        evs = [AccessEvent(0, t) for t in ("a", "a", "b", "a")]
        self.assertAlmostEqual(revisit_rate(evs), 0.5)

    def test_novel_touch_is_relative_to_pre_window_history(self):
        evs = [AccessEvent(0, t) for t in ("a", "b", "c", "d")]
        self.assertEqual(novel_touch_ratio(evs, frozenset({"a", "b"})), 0.5)
        self.assertEqual(novel_touch_ratio(evs, frozenset()), 1.0)


class TestMissionSchema(unittest.TestCase):
    def _valid_raw(self) -> dict:
        path = _REPO / "harness" / "missions" / "clip_two.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _load(self, raw: dict) -> Mission:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.json"
            p.write_text(json.dumps(raw), encoding="utf-8")
            return load_mission(p)

    def test_missing_key_rejected(self):
        raw = self._valid_raw()
        del raw["seed"]
        with self.assertRaises(MissionError):
            self._load(raw)

    def test_calibration_past_scattered_start_rejected(self):
        raw = self._valid_raw()
        raw["calibration_ticks"] = raw["scattered_start"] + 1
        with self.assertRaises(MissionError):
            self._load(raw)

    def test_unknown_key_rejected(self):
        raw = self._valid_raw()
        raw["staleness_entre"] = 0.02  # typo'd key must not be ignored
        with self.assertRaises(MissionError):
            self._load(raw)

    def test_incoherent_expectations_rejected(self):
        raw = self._valid_raw()
        raw["expectations"]["max_wakes"] = 0  # below min_wakes=1
        with self.assertRaises(MissionError):
            self._load(raw)


class TestEngineConstruction(unittest.TestCase):
    def test_unknown_channel_rejected(self):
        ops = SyntheticOps(seed=1, ticks=10, scattered_start=5)
        with self.assertRaises(ValueError):
            SalusEngine(
                ops=ops, bands=(), rules=(Rule("RX", "nope", +1, "x"),),
                floors=Floors(1, 1, 1), window=4,
            )

    def test_rule_band_direction_mismatch_rejected(self):
        ops = SyntheticOps(seed=1, ticks=10, scattered_start=5)
        band = absolute_band("attention_entropy", +1, 2.0, 1.0)
        with self.assertRaises(ValueError):
            SalusEngine(
                ops=ops, bands=(band,),
                rules=(Rule("RX", "attention_entropy", -1, "x"),),
                floors=Floors(1, 1, 1), window=4,
            )


if __name__ == "__main__":
    unittest.main()
