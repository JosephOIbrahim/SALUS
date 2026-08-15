"""The four vitals channels (blueprint section 3), as pure readers.

Mechanical names only in this layer. Affect words live in the profile
layer or not at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence

from ..ops.interface import AccessEvent, OpsSnapshot
from .windows import slope

CHANNELS = (
    "staleness_min_u",
    "attention_entropy",
    "revisit_rate",
    "novel_touch_ratio",
    "utility_trend",
    "consolidation_pressure",
)

# Finite contract bounds per channel. The wake contract needs a
# validatable range; infinity is not one (and is not strict JSON).
# Bounds derive from what the vitals COMPUTATION guarantees, never from
# what the substrate promises: entropy is >= 0 by formula (64 bits =
# 2^64 targets, a generous ceiling) and the ratios are counts/counts in
# [0, 1]. Channels built from adapter-provided floats (staleness,
# trend, pressure) get wide finite sentinels — the OpsReader protocol
# guarantees nothing about their sign or scale, and a legitimate
# down-cross wake on a negative value must validate, not crash.
CHANNEL_BOUNDS: dict[str, tuple[float, float]] = {
    "staleness_min_u": (-1e6, 1e6),
    "attention_entropy": (0.0, 64.0),
    "revisit_rate": (0.0, 1.0),
    "novel_touch_ratio": (0.0, 1.0),
    "utility_trend": (-1e6, 1e6),
    "consolidation_pressure": (-1e6, 1e6),
}


@dataclass(frozen=True, slots=True)
class Vitals:
    """One time-sampled condition snapshot."""

    tick: int
    staleness_min_u: float
    attention_entropy: float
    revisit_rate: float
    novel_touch_ratio: float
    utility_trend: float
    consolidation_pressure: float

    def as_dict(self) -> dict[str, float | int]:
        out: dict[str, float | int] = {"tick": self.tick}
        for c in CHANNELS:
            out[c] = getattr(self, c)
        return out


def attention_entropy(events: Sequence[AccessEvent]) -> float:
    """Shannon entropy (bits) of the visit distribution. Sorted-key
    iteration keeps float accumulation order fixed."""
    if not events:
        return 0.0
    counts: dict[str, int] = {}
    for ev in events:
        counts[ev.target] = counts.get(ev.target, 0) + 1
    n = len(events)
    h = 0.0
    comp = 0.0
    for t in sorted(counts):
        p = counts[t] / n
        term = -p * math.log2(p)
        y = term - comp
        s = h + y
        comp = (s - h) - y
        h = s
    return h


def revisit_rate(events: Sequence[AccessEvent]) -> float:
    if not events:
        return 0.0
    seen: set[str] = set()
    revisits = 0
    for ev in events:
        if ev.target in seen:
            revisits += 1
        else:
            seen.add(ev.target)
    return revisits / len(events)


def novel_touch_ratio(events: Sequence[AccessEvent], seen_before: frozenset[str]) -> float:
    if not events:
        return 0.0
    novel = sum(1 for ev in events if ev.target not in seen_before)
    return novel / len(events)


def compute_vitals(
    tick: int,
    window_snaps: Sequence[OpsSnapshot],
    seen_before: frozenset[str],
) -> Vitals:
    """Assemble one Vitals snapshot from a full window. Pure function."""
    events = [ev for snap in window_snaps for ev in snap.accesses]
    last = window_snaps[-1]
    utilities = [s.utility_total for s in window_snaps]
    return Vitals(
        tick=tick,
        staleness_min_u=min(b.utility for b in last.beliefs),
        attention_entropy=attention_entropy(events),
        revisit_rate=revisit_rate(events),
        novel_touch_ratio=novel_touch_ratio(events, seen_before),
        utility_trend=slope(utilities),
        consolidation_pressure=(
            last.deposits_since_consolidation / last.consolidation_capacity
        ),
    )
