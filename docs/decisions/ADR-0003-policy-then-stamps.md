# ADR-0003 — Design B now, Design A accruing

**Status:** accepted (2026-08-15)

**Decision:** ship the wake's selection as a fixed-order policy table
(Design B): entropy up-cross -> orientation_anchors; staleness
down-cross -> verification_memories; pressure up-cross ->
consolidation_summaries. Design A — stamped deposits, waking by
similarity between current condition and deposit-time condition
(encoding specificity) — is deferred, not rejected.

**Why:** B fires on day one with three auditable rules. A needs a
stamped corpus that does not exist yet; stamping is cheap additive
metadata, so it can begin at integration and A switches on later
without reworking the predicate.

**Consequences:** `wake/policy.py` stays deliberately dumb. The stamp
schema is an open question tracked in BLUEPRINT.md section 11.
