# CHANGELOG — SALUS

## 0.3.1 — 2026-08-15 (mission coverage — clip_three)

No engine changes; clip_two evidence hashes UNCHANGED (result hash
`09ae1bc3…b71d7d23`, first wake t=142). 86 tests (73 -> 86).

Closes the coverage hole the second recheck logged as open work.
R2_staleness and R3_pressure were structurally unfireable on the
synthetic rig — `u_floor=0.05` sits above `staleness_enter=0.02`, and
coin-flip deposits peak near 0.585 of capacity, below
`pressure_enter=0.9` — so every mission-level five-yes green rode on
R1_entropy alone. The two rules had end-to-end unit coverage through
authored OpsReaders; they had no mission.

- **Added:** `clip_three` — a mission driven by an authored replay log
  (ADR-0005 seam) that fires exactly two wakes: a forgotten belief
  decaying past the staleness band (**R2, tick 136**, summoning
  verification memories), then unfiled deposits piling past
  consolidation capacity (**R3, tick 193**, summoning consolidation
  summaries). Attention is pinned on four targets for all 220 ticks,
  so entropy is exactly 2.0 bits on every sample against a 2.5 band —
  R1 stays silent by construction and the two quiet channels are the
  only story.
- **Added:** `tools/make_clip_three.py` — the world's generator. No
  RNG, no wall clock: every value is a module-level constant or an
  exact function of the tick, and the decay is iterated multiplication
  rather than `math.exp`, because IEEE 754 specifies multiplication
  exactly while libm transcendentals may differ in the last bit
  between platforms. The generated log
  (`harness/missions/logs/clip_three.ops.jsonl`) is committed as a
  fixture and a test regenerates it byte for byte — a fixture that
  drifts from its generator is worse than no generator.
- **Changed:** missions may carry one optional key, `ops_log`, naming
  a canonical log to replay instead of the seeded synthetic world.
  Absent, behavior is identical to before; every other unknown key is
  still a hard rejection, so the typo trap stays shut. A named-but-
  absent log is a typed `MissionError` from `runner.build_ops`, not a
  traceback out of the adapter.
- **CI:** both missions now run as explicit gate steps.
- **Tests:** fixture byte-identity, adapter selection per mission,
  the two wake ticks pinned, rule ids and summon classes in order,
  refractory spacing, entropy never reaching its band, and the typed
  rejections for a missing or non-string `ops_log`.

## 0.3.0 — 2026-08-15 (export shim)

No engine changes; clip_two evidence hashes UNCHANGED (verified
byte-for-byte against the last 0.2.x run). 63 tests (47 -> 63).

The other half of the ADR-0005 seam: 0.2.0 taught SALUS to *read* a
recorded ops log; 0.3.0 gives external agents the tools to *write*
one correctly.

- **Added:** `OpsLogWriter` (`src/salus/ops/shim.py`) — appends one
  canonical line per tick, validating each snapshot against the wire
  contract at write time (contiguous ticks from 0, non-empty beliefs,
  capacity >= 1, all floats finite; typed `OpsLogError` rejection
  leaves the file untouched). LF-only on Windows, flush-per-line,
  refuses to clobber an existing file unless told to.
- **Changed:** canonical bytes now have a single source of truth —
  `snapshot_record()` / `record_line()` extracted from `dump_ops`,
  shared by writer and replay. `dump_ops` output is byte-identical.
- **Added:** `docs/WIRE_FORMAT.md` — the v1 wire-format spec:
  file-level rules, field-by-field constraints, validation semantics,
  versioning stance.
- **Added:** `tools/validate_log.py` — pre-flight CLI that loads a
  log through `ReplayOps` itself, so "validator says yes" and "SALUS
  will load it" are the same fact.
- **Added:** `examples/instrumented_agent.py` — end-to-end demo: a
  seeded toy agent writes its own ops log through the shim, SALUS
  replays it and wakes at the scatter point, reproducing the case
  study numbers exactly (one wake, tick 142).
- **Tests:** writer/dump_ops byte-identity, replay round-trip,
  mission-hash equivalence over a writer log, typed rejections,
  partial-write safety, plus subprocess tests running the example
  and validator CLI end-to-end.

**Fixes from the workflow's adversarial verify phase (all three
confirmed findings closed):**

- **Fixed:** non-finite JSON tokens (`Infinity`/`NaN`) in int-coerced
  fields escaped as raw OverflowError, breaking the "always a typed
  OpsLogError" claim; tokens now refused at parse time and
  OverflowError joins the typed boundary.
- **Fixed:** the reader accepted non-canonical logs the spec forbids —
  CRLF endings (universal-newline translation was hiding the CR
  bytes), missing final newline, non-ASCII bytes, float/string/bool
  where integers are required. All now typed rejections; strictness
  test suite added (63 -> 73 tests). The repo's own test helpers were
  producing CRLF logs on Windows — the drift trap, demonstrated.
- **Fixed:** both writers could silently produce the empty log the
  reader rejects; `dump_ops` and a zero-append `OpsLogWriter` close
  now refuse, so the violation surfaces at the recording end.

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
