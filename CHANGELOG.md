# CHANGELOG — SALUS

## 0.2.1 — 2026-08-15 (public readiness)

No engine changes; evidence hashes unchanged.

- **License:** MIT (chosen over Apache-2.0 deliberately — Apache
  carries an express patent grant; MIT stays silent on patents while
  filings are pending).
- **NOTICE.md** rewritten for a public audience: MIT pointer,
  informational patents-pending line, issues/discussion welcome.
- **Added:** `docs/CASE_STUDY.md` — the wake narrative with the
  shipped clip_two numbers, linked from README.
- **Docs:** machine-specific paths generalized to "repo root"; CI
  badge in README; internal project codenames in BLUEPRINT section 10
  generalized (mechanism content unchanged, noted in the file).

## 0.2.0 — 2026-08-15 (integration seam + second recheck)

clip_two evidence hashes UNCHANGED. 47 tests. New gate:
`verify\adapter_equivalence.py`.

**The adapter seam (ADR-0005):**

- **Added:** canonical ops-log wire format (one jsonl line per tick)
  with `dump_ops()` serializer and `ReplayOps` adapter implementing
  `OpsReader` over a recorded log. Typed load-time validation
  (`OpsLogError`): tick gaps, empty belief sets, zero capacity,
  non-finite utility, malformed JSON — closing the degenerate-shape
  class found in the first recheck.
- **Added:** adapter-equivalence gate — synthetic world dumped and
  replayed must reproduce the identical result hash. Gate-0 will reuse
  it against real recorded logs.
- **Changed:** `OpsReader` contract now states snapshot(t) must be
  pure; the recorded-log seam makes purity structural for live
  bindings. `runner.run_once(m, ops=...)` accepts any OpsReader.

**Fixes from the second independent recheck:**

- **Fixed:** blocked crossings were consumed — a persistently-true
  condition under refractory could stay silent forever. Blocked
  crossings now re-arm and retry until they land or the value exits
  (ADR-0006, supersedes the consume-as-intent note).
- **Fixed:** a band threshold outside CHANNEL_BOUNDS inverted the
  contract range (lo > hi) and every wake raised mid-run; rejected at
  engine construction.
- **Fixed:** determinism gate never checked the parent's PYTHONHASHSEED
  — running it with PYTHONHASHSEED=4242 compared a value to itself.
  Child seed now always differs from the parent's.
- **Fixed:** same-second evidence dirs silently overwrote (a failing
  verdict.json could be replaced by a passing one). Microsecond stamps
  + exist_ok=False.
- **Added:** end-to-end R3 pressure-wake test and blocked-crossing
  retry test — R2/R3 were structurally unfireable on the synthetic rig
  (u_floor clamps staleness above enter; pressure peaks ~0.585), so
  every prior five-yes green rode on R1 alone. Mission-level R2/R3
  fixtures remain open work.

## 0.1.2 — 2026-08-15 (gate integrity)

Findings from a fresh-context adversarial recheck of 0.1.1. The engine
survived direct attack (fork rewrite and determinism doctrine both
held); the gate did not. clip_two evidence hashes are UNCHANGED — no
fix touches the shipped mission's byte path.

- **Fixed:** `counterfactual_ticks: 0` passed schema validation and
  made the read-only probe compare two empty lists — a YES that proved
  nothing. The schema now requires >= 1, and an empty proof span fails
  the probe (no evidence is not proof).
- **Fixed:** the down-cross contract pinned `lo` to the channel's lower
  bound; a legitimately negative staleness value (possible under a real
  adapter — SyntheticOps clamps at u_floor and can never produce one)
  crashed the run with OutOfRangeError on the shipped R2_staleness
  rule. Bounds now derive only from what the vitals computation itself
  guarantees; adapter-derived channels carry wide finite sentinels.
  ADR-0004 amended — it had recorded the opposite as settled.
- **Fixed:** duplicate rules on one channel silently never fired past
  the first; duplicate bands silently last-won; an inverted band
  (exit on the wrong side of enter) flapped every other tick. All
  three now rejected at construction with typed errors.
- **Fixed:** write_vitals emitted a lone blank line for an empty run
  where write_events correctly emitted an empty file.
- **Added:** falsification tests for probe_dormant, probe_crossing,
  probe_replay, and the empty-span counterfactual; a negative-utility
  OpsReader test proving the R2 wake fires instead of crashing;
  construction-rejection tests (27 -> 36).
- **Docs:** DESIGN.md records blocked-wake edge consumption as intent
  (a crossing blocked by refractory/budget consumes the episode, it
  does not queue); honest-record item 6.

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
