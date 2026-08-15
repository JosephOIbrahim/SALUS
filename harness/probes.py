"""Probes: the five yeses (blueprint section 9), as judges over evidence."""

from __future__ import annotations

from salus.wake.predicate import RunResult, hash_vitals

from mission_schema import Mission


def probe_dormant(m: Mission, r: RunResult) -> tuple[str, bool, str]:
    early = [e for e in r.events if e.tick < m.expectations.dormant_until]
    ok = not early
    detail = f"{len(early)} wakes before tick {m.expectations.dormant_until}"
    return ("dormant while entropy low", ok, detail)


def probe_crossing(m: Mission, r: RunResult) -> tuple[str, bool, str]:
    n = len(r.events)
    ok = m.expectations.min_wakes <= n <= m.expectations.max_wakes
    first = r.events[0].tick if r.events else None
    if first is not None:
        ok = ok and first >= m.scattered_start
    detail = f"{n} wake(s); first at tick {first}"
    return ("wake fires on the crossing", ok, detail)


def probe_replay(hash_a: str, hash_b: str) -> tuple[str, bool, str]:
    ok = hash_a == hash_b
    return ("identical replay, run twice", ok, f"sha256 {'match' if ok else 'MISMATCH'}")


def counterfactual_divergence_zero(m: Mission, r: RunResult) -> bool:
    """Recompute each event's forward span from the MAIN timeline and
    compare with the stored fork hash. Equality proves the wake changed
    nothing downstream — the read-only floor, demonstrated."""
    by_tick = {v.tick: i for i, v in enumerate(r.vitals)}
    for e in r.events:
        start = by_tick[e.tick] + 1
        span = r.vitals[start : start + m.counterfactual_ticks]
        if hash_vitals(span) != e.counterfactual_hash:
            return False
    return True


def probe_floors(m: Mission, r: RunResult, cf_zero: bool) -> tuple[str, bool, str]:
    ok = (r.floor_violations == 0) and cf_zero
    detail = f"{r.floor_violations} violations; counterfactual divergence {'0' if cf_zero else 'NONZERO'}"
    return ("no floor breached", ok, detail)


def probe_event_data(r: RunResult) -> tuple[str, bool, str]:
    if not r.events:
        return ("wake event visible as data", False, "no events emitted")
    rec = r.events[0].to_record()
    needed = {"tick", "rule_id", "channel", "value", "enter_threshold",
              "summon_class", "contract", "counterfactual_hash"}
    missing = sorted(needed - rec.keys())
    ok = not missing and bool(rec.get("counterfactual_hash"))
    detail = (
        "full contract + counterfactual persisted"
        if ok
        else (f"missing fields: {missing}" if missing else "counterfactual_hash empty")
    )
    return ("wake event visible as data", ok, detail)


def run_all(
    m: Mission, ra: RunResult, rb: RunResult, ha: str, hb: str
) -> list[tuple[str, bool, str]]:
    cf = counterfactual_divergence_zero(m, ra)
    return [
        probe_dormant(m, ra),
        probe_crossing(m, ra),
        probe_replay(ha, hb),
        probe_floors(m, ra, cf),
        probe_event_data(ra),
    ]
