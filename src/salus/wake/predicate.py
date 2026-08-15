"""The wake predicate engine (blueprint section 4).

Deterministic by doctrine: tick-driven (no wall clock), seeded ops only,
fixed rule order, sorted-key serialization, Kahan reductions. Same
signals => same wake, replay-identical, or it's broken.

The counterfactual fork: at each wake the engine forks its window state
— SHARING the ops reader, which is sound precisely because ops is
read-only — suppresses wakes, and runs k ticks forward. Because summon
is read-only, the fork's vitals must equal the main path's vitals
exactly — the stored hash is both the dailies variant and the empirical
read-only proof.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from collections.abc import Sequence

from ..ops.interface import OpsReader, OpsSnapshot
from ..setpoints import Band, Hysteresis
from ..vitals.channels import CHANNEL_BOUNDS, CHANNELS, Vitals, compute_vitals
from .contract import WakeContract, validate
from .events import WakeEvent
from .floors import FloorGuard, Floors
from .policy import Rule


def hash_vitals(slice_: Sequence[Vitals]) -> str:
    payload = json.dumps(
        [v.as_dict() for v in slice_],
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RunResult:
    vitals: tuple[Vitals, ...]
    events: tuple[WakeEvent, ...]
    floor_violations: int


class SalusEngine:
    def __init__(
        self,
        ops: OpsReader,
        bands: Sequence[Band],
        rules: Sequence[Rule],
        floors: Floors,
        window: int,
        counterfactual_ticks: int = 10,
        suppress_wakes: bool = False,
    ) -> None:
        self.ops = ops
        self.rules = tuple(rules)
        self.window = window
        self.cft = counterfactual_ticks
        self.suppress = suppress_wakes
        self.hys = Hysteresis(bands)
        self.guard = FloorGuard(floors)
        self._snaps: list[OpsSnapshot] = []
        self._seen: set[str] = set()
        self._vitals: list[Vitals] = []
        self._events: list[WakeEvent] = []
        self._tick = 0
        for rule in self.rules:
            if rule.channel not in CHANNELS:
                raise ValueError(
                    f"rule {rule.rule_id}: unknown channel {rule.channel!r}"
                )
            if self.hys.has(rule.channel):
                b = self.hys.band(rule.channel)
                if b.direction != rule.direction:
                    raise ValueError(
                        f"rule {rule.rule_id}: direction {rule.direction:+d} "
                        f"disagrees with band direction {b.direction:+d}"
                    )

    def _step(self) -> None:
        t = self._tick
        self.guard.causal_check(t, t)  # the engine only queries its own now
        snap = self.ops.snapshot(t)
        if len(self._snaps) == self.window:
            leaving = self._snaps.pop(0)
            for ev in leaving.accesses:
                self._seen.add(ev.target)
        self._snaps.append(snap)
        vit: Vitals | None = None
        if len(self._snaps) == self.window:
            vit = compute_vitals(t, self._snaps, frozenset(self._seen))
            self._vitals.append(vit)
        self._tick += 1
        if vit is not None and not self.suppress:
            self._evaluate(vit)

    def _evaluate(self, v: Vitals) -> None:
        for rule in self.rules:  # FIXED evaluation order
            if not self.hys.has(rule.channel):
                continue
            fired = self.hys.update(rule.channel, getattr(v, rule.channel))
            if not fired:
                continue
            if not self.guard.clear_to_wake(v.tick):
                continue  # refractory or budget: blocked, not a violation
            cf_hash = self._counterfactual_hash()
            band = self.hys.band(rule.channel)
            # Range is the side of the enter threshold that fired, closed
            # by the channel's finite bound on the other end.
            lo, hi = CHANNEL_BOUNDS[rule.channel]
            if band.direction > 0:
                lo = band.enter
            else:
                hi = band.enter
            contract = WakeContract(
                kind=rule.summon_class,
                lo=lo,
                hi=hi,
                authority="salus.policy",
                valid_from_tick=v.tick,
                valid_until_tick=v.tick + self.guard.floors.refractory_ticks,
            )
            validate(contract, getattr(v, rule.channel), v.tick)
            self._events.append(
                WakeEvent(
                    tick=v.tick,
                    rule_id=rule.rule_id,
                    channel=rule.channel,
                    value=getattr(v, rule.channel),
                    enter_threshold=band.enter,
                    summon_class=rule.summon_class,
                    contract=contract,
                    counterfactual_hash=cf_hash,
                )
            )
            self.guard.record_wake(v.tick)

    def collect_vitals(self, until_tick: int) -> tuple[Vitals, ...]:
        """Public calibration surface: advance to `until_tick` (clamped
        to the ops horizon) and return every vitals sample so far."""
        while self._tick < min(until_tick, self.ops.ticks):
            self._step()
        return tuple(self._vitals)

    def _counterfactual_hash(self) -> str:
        """Fork now, suppress wakes, run k ticks. The branch not taken,
        persisted as data. Read-only floor holds iff it matches the main
        path over the same span.

        The fork SHARES the ops reader — read-only by contract, so
        sharing is sound and is itself the structural claim — and copies
        only the window state it will mutate. Cost is O(window), not
        O(run history), and a live substrate adapter needs no deepcopy."""
        fork = SalusEngine(
            ops=self.ops,
            bands=(),
            rules=(),
            floors=self.guard.floors,
            window=self.window,
            counterfactual_ticks=0,
            suppress_wakes=True,
        )
        fork._snaps = list(self._snaps)
        fork._seen = set(self._seen)
        fork._tick = self._tick
        for _ in range(self.cft):
            if fork._tick >= fork.ops.ticks:
                break
            fork._step()
        return hash_vitals(fork._vitals)

    def run(self) -> RunResult:
        while self._tick < self.ops.ticks:
            self._step()
        return RunResult(
            vitals=tuple(self._vitals),
            events=tuple(self._events),
            floor_violations=self.guard.violations,
        )
