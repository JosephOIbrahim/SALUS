# CLAUDE.md — agent onboarding for SALUS

SALUS is the vitals layer + deterministic wake predicate for the
Cognitive Substrate. Thesis: **Condition Wakes Memory** — retrieval
triggered by the knower's measured condition, not content match.
Source of truth: `BLUEPRINT.md`. Where any older spec conflicts with
the blueprint, the blueprint wins (it is newer).

## Commands

```
python -m unittest discover -s tests      # unit gates (36)
python verify\determinism.py              # cross-process hash compare
python verify\success_signature.py        # THE gate: five yeses or fail
python harness\runner.py harness\missions\clip_two.json
ruff check .                              # lint (optional locally; CI runs it)
```

All commands run from repo root with system Python >= 3.13. Zero
dependencies. Evidence lands in `harness\runs\<mission>_<stamp>\`,
pointer in `harness\runs\LATEST.txt`.

## Map

```
src\salus\ops        the ONLY boundary — SALUS reads, never writes
src\salus\vitals     the four channels, pure readers, Kahan reductions
src\salus\setpoints  calibration + hysteresis bands
src\salus\wake       predicate, policy (Design B), floors, contract, events
src\salus\emit       canonical jsonl + optional .usda (usd-core extra)
harness\             missions-as-data, runner, probes, timestamped runs
verify\              gates as code — determinism + the five-yes signature
tests\               unit tests (stdlib unittest)
```
