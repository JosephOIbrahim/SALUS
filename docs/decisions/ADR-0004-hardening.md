# ADR-0004 — Hardening pass: real contract ranges, sharing fork, cross-process gate

**Status:** accepted (2026-08-15)

**Decisions:**

1. Wake contract ranges derive from the fired band plus finite
   per-channel bounds (`CHANNEL_BOUNDS` in vitals/channels.py):
   up-cross → [enter, channel hi]; down-cross → [channel lo, enter].
   Infinity is banned from evidence (`allow_nan=False` on both emit
   paths).
2. The counterfactual fork SHARES the `OpsReader` and copies only the
   window state it mutates. No deepcopy anywhere in the engine.
3. The determinism gate compares across interpreter processes with
   different `PYTHONHASHSEED`, not within one process.

**Why:** (1) a range that cannot fail validation is not a contract, and
`inf` serialized as the non-JSON literal `Infinity` — the canonical
evidence wasn't strict JSON. (2) deepcopy of the ops reader contradicted
the read-only thesis and would break or bloat against a live substrate
adapter; sharing is the structural read-only claim, exercised. (3) the
same-process gate was structurally blind to hash-seed-dependent
iteration order leaking into evidence — the exact class it exists to
catch.

**Consequences:** result hashes changed; 0.1.0 evidence hashes predate
this ADR (CHANGELOG 0.1.1). A future negative-valued channel rule
(e.g. utility_trend down-cross) now validates instead of crashing.
Adding a new mutable field to `SalusEngine` requires extending the
fork's copy list — guarded by the falsification test plus the five-yes
gate, which fail on fork/main divergence.
