# SALUS — operator README

**One line:** a smoke detector for a mind's condition. Four gauges read

from ops that already run; when one crosses its calibrated band, SALUS

wakes a matched class of memories. Read-only, deterministic, replayable.

Thesis: **Condition Wakes Memory.** The state is measured, not reported.

## Is it healthy? One command

```
cd G:\SALUS
python verify\success_signature.py
```

Five YES lines ending `5/5 — v1 SHIPPED` = healthy. Anything else, read

the failing line — it names the broken property.

## All commands

```
python -m unittest discover -s tests                      # parts check (27)
python verify\determinism.py                              # replay identity, cross-process
python verify\success_signature.py                        # THE gate
python harness\runner.py harness\missions\clip_two.json   # general runner
```

## What you'll see

```
SALUS v0.1.1 — success signature — mission: clip_two
  [1] dormant while entropy low ............. YES
  [2] wake fires on the crossing ............ YES
  [3] identical replay, run twice ........... YES
  [4] no floor breached ..................... YES
  [5] wake event visible as data ............ YES
  5/5 — v1 SHIPPED
```

Evidence: `harness\runs\<mission>_<stamp>\` — newest named in

`harness\runs\LATEST.txt`. Inside: `vitals.jsonl`, `events.jsonl`,

`verdict.json`. Run folders are disposable; they regenerate.

## When it breaks

- **NO on [3]:** nondeterminism got in — wall clock, unsorted iteration,

  a new dependency. Doctrine list is in CLAUDE.md; diff against last green.

- **ModuleNotFoundError: salus** — ran from the wrong folder. Everything

  runs from `G:\SALUS` root.

- **NO on [2], zero wakes:** calibration band swallowed the crossing —

  check `entropy_min_band` / `scattered_start` in the mission JSON.

## Touch map

Safe to edit freely: `harness\missions\*.json`, `tests\`. Handle with

care: `src\salus\wake\` — floors and doctrine live there. Read first:

`BLUEPRINT.md` (source of truth), `DESIGN.md`, `NOTICE.md` (proprietary —

do not publish anything from this repo). History: `CHANGELOG.md`;

decisions: `docs\decisions\`. CI runs lint + all three gates on push.
