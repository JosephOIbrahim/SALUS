"""Deterministic stand-in for the four locked ops.

Everything is precomputed in __init__ from a single seeded RNG, so
snapshot(t) is a pure lookup. Two phases: focused (attention on two
targets, low entropy) then scattered (uniform over twelve, high entropy).
The entropy crossing is the clip-two star; staleness and pressure stay
subcritical by construction.
"""

from __future__ import annotations

import math
import random

from .interface import AccessEvent, BeliefState, OpsSnapshot

TARGETS = tuple(
    "belief_" + name
    for name in (
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
        "eta", "theta", "iota", "kappa", "lam", "mu",
    )
)
FOCUS = TARGETS[:2]


class SyntheticOps:
    """Seeded, precomputed, read-only. Same seed => identical timeline."""

    def __init__(
        self,
        seed: int,
        ticks: int,
        scattered_start: int,
        accesses_per_tick: int = 8,
        u_floor: float = 0.05,
        decay_lambda: float = 0.01,
        capacity: int = 200,
    ) -> None:
        rng = random.Random(seed)
        last_access: dict[str, int] = {t: 0 for t in TARGETS}
        deposits = 0
        timeline: list[OpsSnapshot] = []
        for tick in range(ticks):
            pool = FOCUS if tick < scattered_start else TARGETS
            accesses = tuple(
                AccessEvent(tick=tick, target=rng.choice(pool))
                for _ in range(accesses_per_tick)
            )
            for ev in accesses:
                last_access[ev.target] = tick
            if rng.random() < 0.5:
                deposits += 1
            beliefs = tuple(
                BeliefState(
                    belief_id=t,
                    utility=max(
                        u_floor, math.exp(-decay_lambda * (tick - last_access[t]))
                    ),
                    last_access_tick=last_access[t],
                )
                for t in TARGETS
            )
            total = 0.0
            comp = 0.0
            for b in beliefs:  # Kahan, fixed order
                y = b.utility - comp
                s = total + y
                comp = (s - total) - y
                total = s
            timeline.append(
                OpsSnapshot(
                    tick=tick,
                    accesses=accesses,
                    beliefs=beliefs,
                    utility_total=total,
                    deposits_since_consolidation=deposits,
                    consolidation_capacity=capacity,
                )
            )
        self._timeline: tuple[OpsSnapshot, ...] = tuple(timeline)

    @property
    def ticks(self) -> int:
        return len(self._timeline)

    def snapshot(self, tick: int) -> OpsSnapshot:
        return self._timeline[tick]
