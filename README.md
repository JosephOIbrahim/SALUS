# SALUS — operator README

![gates](https://github.com/JosephOIbrahim/SALUS/actions/workflows/gates.yml/badge.svg)

**A smoke detector for a mind's condition.**

Four gauges read from ops that already run. When one crosses its
calibrated band, SALUS wakes a matched class of memories.

**Read-only. Deterministic. Replayable.**

Thesis: **Condition Wakes Memory** — the state is *measured, not reported*.

---

## Is it healthy? One command

From the repo root (system Python ≥ 3.13, zero dependencies):

```
python verify\success_signature.py
```

**Healthy =** five YES lines ending `5/5 — v1 SHIPPED`.

Anything else → the failing line *names the broken property*.

```
SALUS v0.2.0 — success signature — mission: clip_two
  [1] dormant while entropy low ............. YES
  [2] wake fires on the crossing ............ YES
  [3] identical replay, run twice ........... YES
  [4] no floor breached ..................... YES
  [5] wake event visible as data ............ YES
  5/5 — v1 SHIPPED
```

---

## The path — one glance

```mermaid
flowchart LR
    A["four locked ops<br>(run as-is)"] --> B["vitals readers<br>(no new op)"]
    B --> C["setpoints<br>(calibrated + hysteresis)"]
    C --> D["wake predicate<br>(deterministic)"]
    D --> E["summon<br>(read-only)"]
    R["floors rail — never evict · never mutate · t ≤ own now · authority declared"]
    D -.enforced by.-> R
```

**Why the wake never flaps** — each band is a two-state machine.
It fires *exactly once* per crossing episode:

```mermaid
stateDiagram-v2
    [*] --> armed
    armed --> disarmed: value crosses ENTER — wake fires once
    disarmed --> armed: value exits past EXIT — re-arms
```

---

## All commands

```
python verify\success_signature.py                        # THE gate
python -m unittest discover -s tests                      # parts check (47)
python verify\determinism.py                              # replay identity, cross-process
python verify\adapter_equivalence.py                      # wire-format seam faithful
python harness\runner.py harness\missions\clip_two.json   # general runner
ruff check .                                              # lint (CI pins 0.15.10)
```

**Zero dependencies.** System Python ≥ 3.13, run from repo root.
CI runs lint + all three gates on every push.

---

## Evidence

```
harness\runs\LATEST.txt        name of newest run folder
harness\runs\<name>_<stamp>\   vitals.jsonl · events.jsonl · verdict.json
```

**Run folders are disposable** — they regenerate, byte-identical.

---

## When it breaks

- **NO on [3] replay** → nondeterminism got in — wall clock, unsorted
  iteration, a new dependency. Doctrine list: `DESIGN.md`. Diff against
  last green.

- **`ModuleNotFoundError: salus`** → wrong folder. Everything runs from
  the repo root.

- **NO on [2], zero wakes** → calibration band swallowed the crossing.
  Check `entropy_min_band` / `scattered_start` in the mission JSON.

---

## Touch map

| Zone | Paths |
|---|---|
| **Edit freely** | `harness\missions\*.json` · `tests\` |
| **Handle with care** | `src\salus\wake\` — floors + doctrine live there |
| **Read first** | `BLUEPRINT.md` (source of truth) · `DESIGN.md` · `NOTICE.md` |

**History:** `CHANGELOG.md` · **Decisions:** `docs\decisions\ADR-*.md`

**Source-available, all rights reserved — patents pending.** No use,
reuse, or patent rights granted; reading and evaluation only. See
`LICENSE` and `NOTICE.md`. External contributions not accepted.
