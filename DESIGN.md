# DESIGN — SALUS

*Version lives in `pyproject.toml` / `salus.__version__`; history in CHANGELOG.md.*

## The claim

Every memory system in the field answers: what content matches this
query? SALUS answers: what state is the knower in, and what does that
state summon? The state is measured, not reported — statistics over
ops that already run. No new op; all superpowers are readers.

## The path

```
four locked ops --> vitals readers --> setpoints --> wake predicate --> summon
  (run as-is)        (no new op)      (calibrated)   (deterministic)   (read-only)

floors rail: never evict - never mutate - t <= own now - authority declared
```

In this repo: `ops/` is the boundary — synthetic world, plus the
replay adapter over the canonical ops log that is the integration seam
(ADR-0005); `vitals/` the readers, `setpoints.py` the bands with
hysteresis, `wake/` the predicate + policy + floors + contract + events,
`emit/` canonical evidence.

## The selection fork (blueprint section 5)

Design B ships now: a fixed-order policy table mapping conditions to
memory classes (entropy -> orientation anchors; staleness ->
verification; pressure -> consolidation summaries). Design A (stamped
deposits, encoding-specificity) accrues via deposit stamps and switches
on later without rework. ADR-0003.

## Floors are code paths

A crossing blocked by refractory or budget re-arms its band and
retries each tick, landing when the floor clears — or never, if the
value exits the band first. Floors pace wakes; they must never erase a
condition that stays true. (ADR-0006, superseding the earlier
consume-as-intent note after a recheck showed a pinned condition could
stay silent forever.)

Refractory, budget, and causal mask are enforced in `FloorGuard` on the
wake path. READ-ONLY is structural: SALUS holds an `OpsReader` only;
every record is a frozen dataclass. The counterfactual fork proves it
empirically each run: at every wake the engine forks itself, suppresses
wakes, runs k ticks, and hashes the fork's vitals. The probe recomputes
the same span from the MAIN timeline — equality means the wake changed
nothing downstream. Divergence zero, demonstrated, every run.

## Determinism doctrine

Same signals => same wake, replay-identical twice, or it's broken.
Enforced habits: tick-driven time (no wall clock in the engine), one
seeded RNG confined to SyntheticOps, fixed rule-evaluation order,
sorted-key canonical serialization, Kahan-Babuska-Neumaier reductions,
no sets on any output path, no numpy in the wake path (reduction order
must not float with backend).

Forbidden introductions: datetime.now() inside src/salus, unseeded
random, dict/set iteration into evidence without sorting, threads in
the engine, any dependency in the core.

The determinism gate compares a fresh-interpreter run under a different
PYTHONHASHSEED against the in-process run — replay-identical must hold
across processes, not merely within one.

## Gate-0 re-sequencing (blueprint amendment)

The original build order gated everything on Phase 0 verification. The
synthetic ops boundary re-sequences it: Gate 0 now gates INTEGRATION
with the real substrate, not this standalone build. The harness runs on
seeded synthetic ops; the production adapter binds later behind the
same `OpsReader` protocol.

## Fixes made during and after the build (honest record)

1. Classic Kahan fails the textbook cancellation case
   ([1e16, 1, -1e16]); the unit test caught it. Upgraded to
   Kahan-Babuska-Neumaier. windows.py docstring notes the variant.
2. verify/ scripts initially put only harness/ on sys.path; probes
   imports salus at module load. Both verify scripts now insert src/
   and harness/ explicitly.
3. Contract ranges were placeholders (lo=0, hi=inf); the inf leaked
   into events.jsonl as the literal `Infinity` — deterministic, but not
   strict JSON. Ranges now derive from the fired band plus finite
   per-channel bounds (CHANNEL_BOUNDS), and both emit paths set
   allow_nan=False as a tripwire. Result hashes changed; v0.1.0
   evidence hashes predate this fix.
4. The counterfactual fork deep-copied the entire engine — ops reader
   and run history included. It now shares the read-only ops reader and
   copies only window state: sharing is the structural read-only claim,
   exercised, and a live substrate adapter at Gate 0 needs no deepcopy.
5. The harness reached into engine privates for calibration; the engine
   now exposes collect_vitals(until_tick). Rule channels and rule/band
   direction agreement are validated at engine construction. The
   counterfactual probe has a falsification test — a judge that has
   never said NO is unproven.
6. A fresh-context adversarial recheck (post-v0.1.1) found the gate
   weaker than the engine: counterfactual_ticks=0 passed validation
   and made the read-only probe compare two empty lists (YES while
   proving nothing); the down-cross contract lo could crash a
   legitimate negative-utility wake at Gate 0 (ADR-0004 amended);
   duplicate rules/bands were silently shadowed; inverted bands
   flapped. All closed in 0.1.2, with falsification tests for every
   probe.
7. A second independent recheck (post-v0.1.2) confirmed the fork copy
   set correct by 1,800-config brute force, then found: reader purity
   was assumed, not contracted (an impure reader corrupts the main
   path silently — now a stated OpsReader contract, made structural by
   the ADR-0005 recorded-log seam); a band threshold outside
   CHANNEL_BOUNDS inverted the contract range (now rejected at
   construction); blocked crossings were consumed (now retry,
   ADR-0006); the determinism gate never checked the parent's hash
   seed (now picks a differing child seed); same-second evidence dirs
   silently overwrote (now microsecond-stamped, exist_ok=False); and
   R2/R3 were structurally unfireable on the synthetic rig — the
   five-yes green rode on R1 alone (R2 and R3 now have end-to-end
   unit coverage via authored OpsReaders; a mission-level fixture for
   them is open work).
