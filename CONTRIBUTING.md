# Contributing

**Issues and discussions are welcome** — bug reports, questions,
ideas, and "I pointed this at X and here's what happened" stories.

For code: **open an issue first.** The engine is governed by a strict
determinism doctrine (`DESIGN.md`) and every change must keep all
gates green (`README.md` → "All commands"). Small, gate-green PRs
only; anything that touches `src\salus\wake\` or the evidence byte
path gets extra scrutiny.

Zero runtime dependencies is a hard rule — PRs adding one will be
declined regardless of merit.
