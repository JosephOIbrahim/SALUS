"""The agent that lost the thread — live, end to end.

This is the complete shim loop from docs/CASE_STUDY.md, runnable:

    agent works --> OpsLogWriter.append per tick --> canonical log
    --> ReplayOps --> calibrate --> SalusEngine --> wake event

A toy coding agent refactors two files, locked in, for 140 ticks.
Then a failing test pulls it into a rabbit hole: config files, a
vendored dependency, old notes — twelve targets where there were two.
No single access looks wrong, and nobody asks a bad query, because
nobody asks a query at all. The failure mode is a SHAPE in the
attention distribution — and SALUS is the instrument that reads it.

Everything here is deterministic by doctrine: one seeded RNG, no wall
clock. Run it twice; the wake lands on the same tick with the same
bytes. Exit code 0 means at least one wake fired after the drift began.
"""

from __future__ import annotations

import json
import math
import random
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from salus.ops.interface import AccessEvent, BeliefState, OpsSnapshot  # noqa: E402
from salus.ops.replay import ReplayOps  # noqa: E402
from salus.ops.shim import OpsLogWriter  # noqa: E402
from salus.setpoints import absolute_band, calibrate_entropy_band  # noqa: E402
from salus.wake.floors import Floors  # noqa: E402
from salus.wake.policy import DEFAULT_RULES  # noqa: E402
from salus.wake.predicate import SalusEngine  # noqa: E402

# --- the toy session ---------------------------------------------------
# Same shape as the shipped clip_two mission: focused phase, then drift.

SEED = 20260815
TICKS = 220
SCATTERED_START = 140  # the failing test hits here
WINDOW = 32
CALIBRATION_TICKS = 120  # baseline learned from the focused stretch

# What the agent is *supposed* to be touching...
FOCUS = ("src/parser.py", "tests/test_parser.py")
# ...and where the rabbit hole takes it.
RABBIT_HOLE = FOCUS + (
    "config/settings.toml",
    "vendor/lexer/tokens.py",
    "vendor/lexer/state.py",
    "docs/notes_session_1.md",
    "docs/notes_session_2.md",
    "src/cli.py",
    "src/render.py",
    "tests/test_cli.py",
    "scripts/bench.py",
    "README.md",
)

ACCESSES_PER_TICK = 8
U_FLOOR = 0.05  # keeps staleness subcritical: entropy is the star here
DECAY_LAMBDA = 0.01
CAPACITY = 200


def live_session(writer: OpsLogWriter) -> None:
    """Play the agent's session tick by tick, appending each snapshot
    through the shim exactly as a live substrate instrumentation would.
    The writer validates every line at append time — a malformed tick
    is a typed OpsLogError the moment it happens, not a mystery later."""
    rng = random.Random(SEED)
    last_access: dict[str, int] = {t: 0 for t in RABBIT_HOLE}
    deposits = 0
    for tick in range(TICKS):
        # Act 1: two targets, over and over. Act 2: twelve.
        pool = FOCUS if tick < SCATTERED_START else RABBIT_HOLE
        accesses = tuple(
            AccessEvent(tick=tick, target=rng.choice(pool))
            for _ in range(ACCESSES_PER_TICK)
        )
        for ev in accesses:
            last_access[ev.target] = tick
        if rng.random() < 0.5:
            deposits += 1
        beliefs = tuple(
            BeliefState(
                belief_id=t,
                utility=max(U_FLOOR, math.exp(-DECAY_LAMBDA * (tick - last_access[t]))),
                last_access_tick=last_access[t],
            )
            for t in RABBIT_HOLE
        )
        total = 0.0
        comp = 0.0
        for b in beliefs:  # Kahan, fixed order — doctrine
            y = b.utility - comp
            s = total + y
            comp = (s - total) - y
            total = s
        writer.append(
            OpsSnapshot(
                tick=tick,
                accesses=accesses,
                beliefs=beliefs,
                utility_total=total,
                deposits_since_consolidation=deposits,
                consolidation_capacity=CAPACITY,
            )
        )


def calibrate(ops: ReplayOps) -> tuple:
    """Learn what focus looks like for THIS agent: baseline the focused
    stretch with a suppressed engine, set the entropy band at mean + 4
    sigma. Staleness and pressure get the stock absolute bands."""
    probe = SalusEngine(
        ops=ops, bands=(), rules=(), floors=Floors(1, 1, 1),
        window=WINDOW, suppress_wakes=True,
    )
    baseline = probe.collect_vitals(CALIBRATION_TICKS)
    return (
        calibrate_entropy_band(baseline, k_sigma=4.0, min_width=0.5),
        absolute_band("staleness_min_u", -1, 0.02, 0.04),
        absolute_band("consolidation_pressure", +1, 0.9, 0.8),
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "session_ops.jsonl"

        # 1. The agent runs; the shim records its byproducts.
        with OpsLogWriter(log_path) as writer:
            live_session(writer)
        print(f"[1/4] session recorded: {TICKS} ticks -> canonical ops log")

        # 2. SALUS replays the log — never a live handle (ADR-0005).
        ops = ReplayOps(log_path)
        print(f"[2/4] log replayed: {ops.ticks} ticks validated at load")

        # 3. Calibrate on the focused baseline, then run the predicate.
        bands = calibrate(ops)
        print(f"[3/4] calibrated: entropy band enter={bands[0].enter:.3f} bits")
        engine = SalusEngine(
            ops=ops, bands=bands, rules=DEFAULT_RULES,
            floors=Floors(refractory_ticks=60, budget_max=2, budget_window=200),
            window=WINDOW, counterfactual_ticks=10,
        )
        result = engine.run()

        # 4. The wake, as data — canonical bytes, same every run.
        print(f"[4/4] run complete: {len(result.events)} wake(s), "
              f"{result.floor_violations} floor violations")
        for e in result.events:
            print(json.dumps(
                e.to_record(), sort_keys=True, separators=(",", ":"), allow_nan=False
            ))
            print(
                f"wake at tick {e.tick}: {e.channel} hit {e.value:.3f} "
                f"(threshold {e.enter_threshold:.3f}) -> summon {e.summon_class}. "
                f"The agent never asked for help; the condition did the retrieving."
            )

    # Success means the drift was caught: a wake AFTER the scatter point.
    woke_after_drift = any(e.tick >= SCATTERED_START for e in result.events)
    if not woke_after_drift:
        print("NO WAKE after the scatter point — the drift went unnoticed.")
    return 0 if woke_after_drift else 1


if __name__ == "__main__":
    raise SystemExit(main())
