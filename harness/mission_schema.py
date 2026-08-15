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


_REQUIRED = (
    "name", "seed", "ticks", "scattered_start", "window", "calibration_ticks",
    "refractory_ticks", "budget_max", "budget_window", "counterfactual_ticks",
    "entropy_k_sigma", "entropy_min_band", "staleness_enter", "staleness_exit",
    "pressure_enter", "pressure_exit", "expectations",
)


def load_mission(path: Path) -> Mission:
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise MissionError(f"mission missing keys: {missing}")
    exp = raw["expectations"]
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
    )
    if not (mission.window <= mission.calibration_ticks <= mission.scattered_start):
        raise MissionError("require window <= calibration_ticks <= scattered_start")
    if mission.scattered_start >= mission.ticks:
        raise MissionError("scattered_start must be < ticks")
    return mission
