"""Author the clip_three world: a replay log that fires R2 and R3.

Usage:  python tools\\make_clip_three.py

The synthetic rig cannot reach the staleness or pressure bands by
construction — SyntheticOps clamps every utility at u_floor=0.05 (above
staleness_enter=0.02) and its coin-flip deposits peak near 0.585 of
capacity (below pressure_enter=0.9). So mission-level coverage rode on
R1_entropy alone. This generator writes the world those two rules need,
through the ADR-0005 seam: a canonical ops log, replayed by ReplayOps
exactly as a real substrate's recording would be.

The world, in three acts:

1. CALM. Attention is pinned on four targets, one access each per tick,
   forever. Every window therefore holds a perfectly uniform visit
   distribution -> attention_entropy is exactly 2.0 bits on every
   sample, sigma is exactly zero, and the calibrated band lands at
   2.0 + min_width. Entropy is flat by construction, so R1 can never
   fire and the two quiet channels are the only story.

2. THE FORGOTTEN BELIEF. At DECAY_START one belief stops being
   refreshed and decays geometrically. Nothing clamps it, so it crosses
   staleness_enter from above -> R2 down-cross. At RECOVERY_TICK it is
   touched again and returns to the stable utility, re-arming the band
   past staleness_exit; it never falls again, so R2 fires exactly once.

3. THE UNFILED PILE. Deposits sit flat through the calm, then climb
   from DEPOSIT_RAMP_START until consolidation_pressure crosses 0.9 ->
   R3 up-cross, outside R2's refractory window. The pile then plateaus
   rather than draining, so pressure never re-arms and R3 also fires
   exactly once.

Determinism: no RNG and no wall clock — every value is a module-level
constant or an exact function of the tick. The decay is iterated
multiplication, never math.exp: IEEE 754 specifies multiplication
exactly, while libm transcendentals may differ in the last bit between
platforms, and this log is a committed fixture that CI regenerates.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from salus.ops.interface import AccessEvent, BeliefState, OpsSnapshot  # noqa: E402
from salus.ops.shim import OpsLogWriter  # noqa: E402

LOG_PATH = _REPO / "harness" / "missions" / "logs" / "clip_three.ops.jsonl"

TICKS = 220

# Act 1 — the flat attention pattern. Four targets, one access each,
# every tick: uniform over the whole window, so entropy is pinned.
FOCUS: tuple[str, ...] = (
    "belief_alpha", "belief_beta", "belief_gamma", "belief_delta",
)
STABLE_UTILITY = 0.5

# Act 2 — the belief attention forgets.
WATCHED = "belief_epsilon"
DECAY_START = 130          # last refresh is DECAY_START - 1
DECAY_FACTOR = 0.6         # exact under IEEE 754; ~7 ticks to cross 0.02
RECOVERY_TICK = 150        # touched again; utility returns to stable

# Act 3 — the pile of unfiled work.
CAPACITY = 200
DEPOSIT_BASE = 20          # flat through the calm: pressure 0.10
DEPOSIT_RAMP_START = 160
DEPOSIT_STEP = 5
DEPOSIT_CEILING = 210      # plateau above capacity: pressure never re-arms


def _watched_utility(tick: int, previous: float) -> float:
    """The forgotten belief's utility at `tick`, given its value at
    `tick - 1`. Iterated multiplication keeps the decay bit-identical
    on every platform."""
    if tick < DECAY_START:
        return STABLE_UTILITY
    if tick >= RECOVERY_TICK:
        return STABLE_UTILITY
    return previous * DECAY_FACTOR


def _deposits(tick: int) -> int:
    if tick < DEPOSIT_RAMP_START:
        return DEPOSIT_BASE
    return min(DEPOSIT_BASE + DEPOSIT_STEP * (tick - DEPOSIT_RAMP_START),
               DEPOSIT_CEILING)


def snapshots() -> Iterator[OpsSnapshot]:
    """The authored timeline, one snapshot per tick."""
    watched = STABLE_UTILITY
    watched_last_access = 0
    for tick in range(TICKS):
        watched = _watched_utility(tick, watched)
        if watched == STABLE_UTILITY:
            watched_last_access = tick
        accesses = tuple(AccessEvent(tick=tick, target=t) for t in FOCUS)
        beliefs = tuple(
            BeliefState(belief_id=t, utility=STABLE_UTILITY, last_access_tick=tick)
            for t in FOCUS
        ) + (
            BeliefState(
                belief_id=WATCHED,
                utility=watched,
                last_access_tick=watched_last_access,
            ),
        )
        total = 0.0
        comp = 0.0
        for b in beliefs:  # Kahan, fixed order — doctrine
            y = b.utility - comp
            s = total + y
            comp = (s - total) - y
            total = s
        yield OpsSnapshot(
            tick=tick,
            accesses=accesses,
            beliefs=beliefs,
            utility_total=total,
            deposits_since_consolidation=_deposits(tick),
            consolidation_capacity=CAPACITY,
        )


def write_log(path: Path) -> None:
    """Write the authored world to `path` in canonical wire bytes.
    OpsLogWriter validates every line as it goes and opens with
    newline="" so the log is LF-only on Windows too."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with OpsLogWriter(path, overwrite=True) as writer:
        for snapshot in snapshots():
            writer.append(snapshot)


def main() -> int:
    write_log(LOG_PATH)
    print(f"wrote {TICKS} ticks -> {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
