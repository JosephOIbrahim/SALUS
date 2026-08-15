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
from salus.ops.interface import AccessEvent, BeliefState, OpsSnapshot  # noqa: E402
from salus.ops.synthetic import SyntheticOps  # noqa: E402
from salus.setpoints import Hysteresis, absolute_band, calibrate_entropy_band  # noqa: E402
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

    def test_probe_fails_on_empty_proof_span(self):
        """An event at the final vitals tick has nothing after it to
        compare — no evidence must read as no proof, not as YES."""
        from salus.wake.predicate import hash_vitals

        last_tick = _R.vitals[-1].tick
        vacuous = dataclasses.replace(
            _R.events[0], tick=last_tick, counterfactual_hash=hash_vitals([])
        )
        doctored = dataclasses.replace(_R, events=(vacuous,))
        self.assertFalse(probes.counterfactual_divergence_zero(_M, doctored))


class TestProbeFalsification(unittest.TestCase):
    """Every judge must be able to say NO."""

    def test_dormant_fails_on_early_wake(self):
        early = dataclasses.replace(_R.events[0], tick=0)
        doctored = dataclasses.replace(_R, events=(early,))
        name, ok, _ = probes.probe_dormant(_M, doctored)
        self.assertFalse(ok)

    def test_crossing_fails_on_zero_wakes(self):
        doctored = dataclasses.replace(_R, events=())
        name, ok, _ = probes.probe_crossing(_M, doctored)
        self.assertFalse(ok)

    def test_replay_fails_on_hash_mismatch(self):
        name, ok, _ = probes.probe_replay("a" * 64, "b" * 64)
        self.assertFalse(ok)


class _NegativeUtilityOps:
    """Minimal OpsReader whose belief utility jumps below zero — the
    maximally-stale case a real adapter can produce (SyntheticOps
    clamps at u_floor, so it can never exercise this)."""

    def __init__(self, ticks: int) -> None:
        self._ticks = ticks

    @property
    def ticks(self) -> int:
        return self._ticks

    def snapshot(self, tick: int) -> OpsSnapshot:
        u = 0.5 if tick < 6 else -0.1
        return OpsSnapshot(
            tick=tick,
            accesses=(AccessEvent(tick=tick, target="b"),),
            beliefs=(BeliefState(belief_id="b", utility=u, last_access_tick=tick),),
            utility_total=u,
            deposits_since_consolidation=0,
            consolidation_capacity=10,
        )


class TestNegativeUtilityWake(unittest.TestCase):
    def test_down_cross_on_negative_value_wakes_instead_of_crashing(self):
        engine = SalusEngine(
            ops=_NegativeUtilityOps(ticks=12),
            bands=(absolute_band("staleness_min_u", -1, 0.02, 0.04),),
            rules=(Rule("R2", "staleness_min_u", -1, "verification_memories"),),
            floors=Floors(refractory_ticks=1, budget_max=1, budget_window=12),
            window=4,
            counterfactual_ticks=2,
        )
        result = engine.run()  # must not raise OutOfRangeError
        self.assertEqual(len(result.events), 1)
        e = result.events[0]
        self.assertLess(e.value, 0.0)
        self.assertLessEqual(e.contract.lo, e.value)


class TestConstructionRejections(unittest.TestCase):
    def test_duplicate_rule_channel_rejected(self):
        ops = SyntheticOps(seed=1, ticks=10, scattered_start=5)
        rules = (
            Rule("RA", "attention_entropy", +1, "orientation_anchors"),
            Rule("RB", "attention_entropy", +1, "something_else"),
        )
        with self.assertRaises(ValueError):
            SalusEngine(ops=ops, bands=(), rules=rules,
                        floors=Floors(1, 1, 1), window=4)

    def test_duplicate_band_channel_rejected(self):
        with self.assertRaises(ValueError):
            Hysteresis([
                absolute_band("attention_entropy", +1, 2.0, 1.0),
                absolute_band("attention_entropy", +1, 99.0, 1.0),
            ])

    def test_inverted_band_rejected(self):
        # exit past enter on the wrong side => the band would flap
        with self.assertRaises(ValueError):
            Hysteresis([absolute_band("staleness_min_u", -1, 0.02, 0.01)])
        with self.assertRaises(ValueError):
            Hysteresis([absolute_band("attention_entropy", +1, 2.0, 3.0)])

    def test_band_enter_outside_channel_bounds_rejected(self):
        """A threshold beyond CHANNEL_BOUNDS would invert the contract
        range (lo > hi) and every wake would raise mid-run."""
        ops = SyntheticOps(seed=1, ticks=10, scattered_start=5)
        band = absolute_band("staleness_min_u", -1, -2e6, -1.5e6)
        with self.assertRaises(ValueError):
            SalusEngine(
                ops=ops, bands=(band,),
                rules=(Rule("RX", "staleness_min_u", -1, "x"),),
                floors=Floors(1, 1, 1), window=4,
            )


class _PinnedEntropyOps:
    """Attention entropy pinned high, with one low valley — for the
    blocked-crossing retry semantics (ADR-0006)."""

    def __init__(self, ticks: int) -> None:
        self._ticks = ticks

    @property
    def ticks(self) -> int:
        return self._ticks

    def snapshot(self, tick: int) -> OpsSnapshot:
        if 4 <= tick <= 6:  # the valley: one target -> entropy 0
            targets = ("a",) * 4
        else:  # four distinct targets -> entropy 2.0 bits
            targets = ("a", "b", "c", "d")
        return OpsSnapshot(
            tick=tick,
            accesses=tuple(AccessEvent(tick=tick, target=t) for t in targets),
            beliefs=(BeliefState(belief_id="a", utility=0.5, last_access_tick=tick),),
            utility_total=0.5,
            deposits_since_consolidation=0,
            consolidation_capacity=10,
        )


class TestBlockedCrossingRetries(unittest.TestCase):
    def test_refractory_delays_wake_instead_of_erasing_it(self):
        """High -> valley (re-arm) -> high again inside refractory: the
        second crossing must land when the refractory clears, not be
        silently consumed."""
        engine = SalusEngine(
            ops=_PinnedEntropyOps(ticks=30),
            bands=(absolute_band("attention_entropy", +1, 1.5, 1.0),),
            rules=(Rule("R1", "attention_entropy", +1, "orientation_anchors"),),
            floors=Floors(refractory_ticks=10, budget_max=5, budget_window=100),
            window=2,
            counterfactual_ticks=1,
        )
        result = engine.run()
        self.assertEqual(len(result.events), 2)
        first, second = result.events
        self.assertGreaterEqual(second.tick - first.tick, 10)


class _RisingPressureOps:
    """Deposits climb past capacity — exercises R3 end-to-end (the
    synthetic rig never fires it: pressure peaks ~0.585 on clip_two)."""

    def __init__(self, ticks: int) -> None:
        self._ticks = ticks

    @property
    def ticks(self) -> int:
        return self._ticks

    def snapshot(self, tick: int) -> OpsSnapshot:
        return OpsSnapshot(
            tick=tick,
            accesses=(AccessEvent(tick=tick, target="a"),),
            beliefs=(BeliefState(belief_id="a", utility=0.5, last_access_tick=tick),),
            utility_total=0.5,
            deposits_since_consolidation=2 * tick,
            consolidation_capacity=10,
        )


class TestPressureWake(unittest.TestCase):
    def test_r3_fires_on_pressure_crossing(self):
        engine = SalusEngine(
            ops=_RisingPressureOps(ticks=10),
            bands=(absolute_band("consolidation_pressure", +1, 0.9, 0.8),),
            rules=(Rule("R3", "consolidation_pressure", +1, "consolidation_summaries"),),
            floors=Floors(refractory_ticks=1, budget_max=1, budget_window=10),
            window=2,
            counterfactual_ticks=1,
        )
        result = engine.run()
        self.assertEqual(len(result.events), 1)
        e = result.events[0]
        self.assertEqual(e.summon_class, "consolidation_summaries")
        self.assertGreater(e.value, 0.9)


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

    def test_zero_counterfactual_ticks_rejected(self):
        """cft=0 would make the read-only probe compare two empty lists
        — a YES that proves nothing."""
        raw = self._valid_raw()
        raw["counterfactual_ticks"] = 0
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
