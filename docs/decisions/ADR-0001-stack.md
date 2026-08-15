# ADR-0001 — Stack: Python 3.13+, stdlib-only core

**Status:** accepted (2026-08-15)

**Decision:** pure-stdlib core and harness; unittest for tests;
pytest/ruff/mypy declared as optional dev extras; usd-core as optional
[usd] extra behind an import guard.

**Why:** determinism is the load-bearing property. Zero dependencies
means zero float-backend variance, zero install steps on the rig
(system Python 3.14.2), and the five-yes gate runs anywhere. numpy is
explicitly excluded from the wake path: its reduction order can vary
by backend and build, which would break replay-identity.

**Consequences:** Kahan-Babuska-Neumaier reductions are hand-rolled in
`vitals/windows.py`; slightly more code, fully owned numerics.
