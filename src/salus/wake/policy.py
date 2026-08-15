"""Design B: the bootstrap policy table (blueprint section 5).

Conditions map to memory classes by authored rule, in FIXED order.
Design A (stamped deposits) accrues in parallel via deposit stamps and
switches on later without rework.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    channel: str
    direction: int
    summon_class: str


DEFAULT_RULES: tuple[Rule, ...] = (
    Rule("R1_entropy", "attention_entropy", +1, "orientation_anchors"),
    Rule("R2_staleness", "staleness_min_u", -1, "verification_memories"),
    Rule("R3_pressure", "consolidation_pressure", +1, "consolidation_summaries"),
)
