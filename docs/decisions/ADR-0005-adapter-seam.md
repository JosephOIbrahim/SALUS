# ADR-0005 — Integration seam: recorded ops log; reader purity structural

**Status:** accepted (2026-08-15)

**Decision:** substrate integration happens through a recorded jsonl
ops log — one canonical line per tick — replayed via `ReplayOps`
behind the same `OpsReader` protocol. Live bindings record first and
replay second; SALUS never holds a live mutable handle. The `OpsReader`
contract now states that `snapshot(t)` must be a pure function of t.

**Why:**

1. A recorded log is replayable by definition — the determinism
   doctrine survives integration untouched.
2. The counterfactual fork shares the reader and replays overlapping
   spans. An impure reader corrupts the main path silently: an
   adversarial recheck demonstrated a read-counting adapter corrupting
   10 vitals ticks while the probe still reported divergence 0. Purity
   by construction beats purity by convention.
3. Typed boundary validation (`OpsLogError` at load) closes the
   degenerate-shape class — empty belief sets, zero capacity,
   non-finite utility, tick gaps — as load-time failures instead of
   raw builtin exceptions mid-run.
4. The `adapter_equivalence` gate proves the seam faithful: the
   synthetic world dumped to the wire format and replayed must
   reproduce the identical result hash.

**Consequences:** Gate-0 work becomes "make the substrate emit the
wire format", not "bind SALUS to substrate internals". Dailies gets
the ops log as a free scrubbable artifact. Cost: no sub-tick liveness
— SALUS sees the world at log granularity, which is acceptable because
the predicate is tick-driven by doctrine.
