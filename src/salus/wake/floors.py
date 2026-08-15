"""Floors are code paths, not conventions (blueprint section 6).

READ-ONLY is structural: SALUS holds an OpsReader only, and every record
it sees is a frozen dataclass. There is no write surface to misuse. The
counterfactual probe proves it empirically: zero divergence between the
woken and unwoken timelines.
"""

from __future__ import annotations

from dataclasses import dataclass


class FloorViolation(Exception):
    """A floor was breached. This must never fire in a healthy run."""


@dataclass(frozen=True, slots=True)
class Floors:
    refractory_ticks: int
    budget_max: int
    budget_window: int


class FloorGuard:
    """Causal mask, refractory period, wake budget. Deterministic."""

    def __init__(self, floors: Floors) -> None:
        self.floors = floors
        self.wake_ticks: list[int] = []
        self.violations = 0

    def causal_check(self, query_tick: int, now: int) -> None:
        """An agent may query t <= its own now. Nothing else."""
        if query_tick > now:
            self.violations += 1
            raise FloorViolation(f"causal mask: query t={query_tick} > now={now}")

    def clear_to_wake(self, now: int) -> bool:
        if self.wake_ticks and now - self.wake_ticks[-1] < self.floors.refractory_ticks:
            return False
        recent = [t for t in self.wake_ticks if now - t < self.floors.budget_window]
        if len(recent) >= self.floors.budget_max:
            return False
        return True

    def record_wake(self, now: int) -> None:
        self.wake_ticks.append(now)
