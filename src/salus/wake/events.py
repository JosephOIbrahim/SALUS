"""Wake events land as data (blueprint section 4, step 6): time-sampled,
addressable, replayable. This record is what dailies scrubs later."""

from __future__ import annotations

from dataclasses import dataclass

from .contract import WakeContract


@dataclass(frozen=True, slots=True)
class WakeEvent:
    tick: int
    rule_id: str
    channel: str
    value: float
    enter_threshold: float
    summon_class: str
    contract: WakeContract
    counterfactual_hash: str

    def to_record(self) -> dict[str, object]:
        return {
            "tick": self.tick,
            "rule_id": self.rule_id,
            "channel": self.channel,
            "value": self.value,
            "enter_threshold": self.enter_threshold,
            "summon_class": self.summon_class,
            "contract": self.contract.as_dict(),
            "counterfactual_hash": self.counterfactual_hash,
        }
