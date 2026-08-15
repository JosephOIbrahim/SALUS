# CHANGELOG — SALUS

## 0.1.1 — 2026-08-15 (hardening pass)

**Result hashes changed from 0.1.0** (contract range fix altered the
event bytes). All gates green after every change; first wake t=142
unchanged.

- **Fixed:** wake contracts carried placeholder ranges (lo=0, hi=inf);
  the infinity serialized into events.jsonl as the literal `Infinity`,
  which is not strict JSON. Ranges now derive from the fired band plus
  finite per-channel bounds (`CHANNEL_BOUNDS`); both emit paths set
  `allow_nan=False` as a permanent tripwire.
- **Changed:** the counterfactual fork no longer deep-copies the engine.
  It shares the read-only `OpsReader` (sharing is the structural
  read-only claim) and copies only window state — O(window) per wake,
  and a live substrate adapter needs no deepcopy at Gate 0.
- **Changed:** determinism gate now compares an in-process run against a
  fresh interpreter under a different `PYTHONHASHSEED`.
- **Added:** public `SalusEngine.collect_vitals()` calibration surface;
  harness and tests no longer touch engine privates.
- **Added:** engine construction validates rule channels against
  `CHANNELS` and rule/band direction agreement.
- **Added:** mission schema rejects unknown keys (top level and
  expectations) and incoherent values (non-positive ticks/window/budget,
  negative refractory/counterfactual, min_wakes > max_wakes).
- **Added:** hardening test suite — counterfactual-probe falsification,
  strict-JSON evidence, channel semantics, schema rejection,
  construction validation.
- **Added:** CI workflow running all gates + ruff on push/PR.
- **Docs:** DESIGN.md honest record items 3–5; ADR-0004; version read
  from `salus.__version__` instead of hardcoded strings.

## 0.1.0 — 2026-08-15 (first ship)

Deterministic standalone vertical: four vitals readers, calibrated
setpoints with hysteresis, wake predicate with fixed rule order,
Design-B policy table, floors (refractory / budget / causal), typed
cognitive contract, wake events as data, counterfactual fork,
canonical JSONL + optional .usda emitter, clip_two mission, five-yes
signature green (first wake t=142).
