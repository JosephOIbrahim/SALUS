"""The wake predicate engine (blueprint section 4).

Deterministic by doctrine: tick-driven (no wall clock), seeded ops only,
fixed rule order, sorted-key serialization, Kahan reductions. Same
signals => same wake, replay-identical, or it's broken.

The counterfactual fork: at each wake the engine deep-copies itself,
suppresses wakes, and runs k ticks forward. Because summon is read-only,
the fork's vitals must equal the main path's vitals exactly — the stored
hash is both the dailies variant and the empirical read-only proof.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from collections.abc import Sequence

from ..ops.interface import OpsReader, OpsSnapshot
from ..setpoints import Band, Hysteresis
from ..vitals.channels import Vitals, compute_vitals
from .contract import WakeContract, validate
from .events import WakeEvent
from .floors import FloorGuard, Floors
from .policy import Rule


def hash_vitals(slice_: Sequence[Vitals]) -> str:
    payload = json.dumps(
        [v.as_dict() for v in slice_], sort_keys=True, separators=(",", ":")
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
            contract = WakeContract(
                kind=rule.summon_class,
                lo=0.0,
                hi=float("inf"),
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

    def _counterfactual_hash(self) -> str:
        """Fork now, suppress wakes, run k ticks. The branch not taken,
        persisted as data. Read-only floor holds iff it matches the main
        path over the same span."""
        fork = copy.deepcopy(self)
        fork.suppress = True
        base = len(fork._vitals)
        for _ in range(self.cft):
            if fork._tick >= fork.ops.ticks:
                break
            fork._step()
        return hash_vitals(fork._vitals[base:])

    def run(self) -> RunResult:
        while self._tick < self.ops.ticks:
            self._step()
        return RunResult(
            vitals=tuple(self._vitals),
            events=tuple(self._events),
            floor_violations=self.guard.violations,
        )
