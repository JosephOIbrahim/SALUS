# DESIGN — SALUS v0.1.0

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

In this repo: `ops/` is the boundary (synthetic now, substrate adapter
at integration), `vitals/` the readers, `setpoints.py` the bands with
hysteresis, `wake/` the predicate + policy + floors + contract + events,
`emit/` canonical evidence.

## The selection fork (blueprint section 5)

Design B ships now: a fixed-order policy table mapping conditions to
memory classes (entropy -> orientation anchors; staleness ->
verification; pressure -> consolidation summaries). Design A (stamped
deposits, encoding-specificity) accrues via deposit stamps and switches
on later without rework. ADR-0003.

## Floors are code paths

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

## Gate-0 re-sequencing (blueprint amendment)

The original build order gated everything on Phase 0 verification. The
synthetic ops boundary re-sequences it: Gate 0 now gates INTEGRATION
with the real substrate, not this standalone build. The harness runs on
seeded synthetic ops; the production adapter binds later behind the
same `OpsReader` protocol.

## Two fixes made during the build (honest record)

1. Classic Kahan fails the textbook cancellation case
   ([1e16, 1, -1e16]); the unit test caught it. Upgraded to
   Kahan-Babuska-Neumaier. windows.py docstring notes the variant.
2. verify/ scripts initially put only harness/ on sys.path; probes
   imports salus at module load. Both verify scripts now insert src/
   and harness/ explicitly.
