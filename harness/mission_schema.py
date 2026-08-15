"""Mission schema — declarative scenarios, schema-validated (SYNAPSE
harness pattern: missions as data, a dumb runner, probes as judges)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class MissionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Expectations:
    min_wakes: int
    max_wakes: int
    dormant_until: int
    zero_floor_violations: bool


@dataclass(frozen=True, slots=True)
class Mission:
    name: str
    seed: int
    ticks: int
    scattered_start: int
    window: int
    calibration_ticks: int
    refractory_ticks: int
    budget_max: int
    budget_window: int
    counterfactual_ticks: int
    entropy_k_sigma: float
    entropy_min_band: float
    staleness_enter: float
    staleness_exit: float
    pressure_enter: float
    pressure_exit: float
    expectations: Expectations
    # Optional: a canonical ops log (ADR-0005) to replay instead of the
    # seeded synthetic world. Absent => synthetic, exactly as before.
    ops_log: str | None = None


_REQUIRED = (
    "name", "seed", "ticks", "scattered_start", "window", "calibration_ticks",
    "refractory_ticks", "budget_max", "budget_window", "counterfactual_ticks",
    "entropy_k_sigma", "entropy_min_band", "staleness_enter", "staleness_exit",
    "pressure_enter", "pressure_exit", "expectations",
)

# The only keys a mission may omit. Everything outside _REQUIRED +
# _OPTIONAL is still a hard rejection — the typo trap stays shut.
_OPTIONAL = ("ops_log",)

_REQUIRED_EXPECTATIONS = (
    "min_wakes", "max_wakes", "dormant_until", "zero_floor_violations",
)


def load_mission(path: Path) -> Mission:
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise MissionError(f"mission missing keys: {missing}")
    # Unknown keys are rejected, not ignored: a typo'd key silently
    # falling back to nothing is how missions drift from their authors.
    unknown = sorted(set(raw) - set(_REQUIRED) - set(_OPTIONAL))
    if unknown:
        raise MissionError(f"mission has unknown keys: {unknown}")
    ops_log = raw.get("ops_log")
    if ops_log is not None and not isinstance(ops_log, str):
        raise MissionError("ops_log must be a string path relative to the repo root")
    exp = raw["expectations"]
    missing_exp = [k for k in _REQUIRED_EXPECTATIONS if k not in exp]
    if missing_exp:
        raise MissionError(f"expectations missing keys: {missing_exp}")
    unknown_exp = sorted(set(exp) - set(_REQUIRED_EXPECTATIONS))
    if unknown_exp:
        raise MissionError(f"expectations has unknown keys: {unknown_exp}")
    mission = Mission(
        name=str(raw["name"]),
        seed=int(raw["seed"]),
        ticks=int(raw["ticks"]),
        scattered_start=int(raw["scattered_start"]),
        window=int(raw["window"]),
        calibration_ticks=int(raw["calibration_ticks"]),
        refractory_ticks=int(raw["refractory_ticks"]),
        budget_max=int(raw["budget_max"]),
        budget_window=int(raw["budget_window"]),
        counterfactual_ticks=int(raw["counterfactual_ticks"]),
        entropy_k_sigma=float(raw["entropy_k_sigma"]),
        entropy_min_band=float(raw["entropy_min_band"]),
        staleness_enter=float(raw["staleness_enter"]),
        staleness_exit=float(raw["staleness_exit"]),
        pressure_enter=float(raw["pressure_enter"]),
        pressure_exit=float(raw["pressure_exit"]),
        expectations=Expectations(
            min_wakes=int(exp["min_wakes"]),
            max_wakes=int(exp["max_wakes"]),
            dormant_until=int(exp["dormant_until"]),
            zero_floor_violations=bool(exp["zero_floor_violations"]),
        ),
        ops_log=ops_log,
    )
    if mission.ticks <= 0 or mission.window < 1:
        raise MissionError("require ticks > 0 and window >= 1")
    if mission.refractory_ticks < 0:
        raise MissionError("refractory_ticks must be >= 0")
    if mission.counterfactual_ticks < 1:
        raise MissionError(
            "counterfactual_ticks must be >= 1 — a zero-length fork makes "
            "the read-only proof vacuous"
        )
    if mission.budget_max < 1 or mission.budget_window < 1:
        raise MissionError("require budget_max >= 1 and budget_window >= 1")
    if not (mission.window <= mission.calibration_ticks <= mission.scattered_start):
        raise MissionError("require window <= calibration_ticks <= scattered_start")
    if mission.scattered_start >= mission.ticks:
        raise MissionError("scattered_start must be < ticks")
    e = mission.expectations
    if not (0 <= e.min_wakes <= e.max_wakes):
        raise MissionError("require 0 <= min_wakes <= max_wakes")
    return mission
