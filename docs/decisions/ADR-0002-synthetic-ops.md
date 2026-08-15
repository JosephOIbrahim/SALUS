# ADR-0002 — Synthetic ops boundary; Gate-0 re-sequenced

**Status:** accepted (2026-08-15)

**Decision:** SALUS holds one protocol, `OpsReader`, and ships with a
seeded, precomputed `SyntheticOps`. The production adapter to the real
substrate binds later behind the same protocol.

**Why:** the four locked ops live in the substrate, whose Phase-0
status was unverified at build time. A deterministic synthetic world
lets the wake predicate, floors, and counterfactual machinery be built
and PROVEN now, without waiting. It also makes the harness a true
clean room: every crossing is authored, every replay exact.

**Consequences:** Gate 0 (verify Phase 0) moves from "before any vitals
work" to "before integration." The five-yes signature certifies the
machine, not the wiring; integration gets its own gate and mission.
