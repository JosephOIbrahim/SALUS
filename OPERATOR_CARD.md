# SALUS — OPERATOR'S CARD

**One system. One health question. One command.**

```
cd G:\SALUS
python verify\success_signature.py
```

**Healthy =** five YES lines ending `5/5 — v1 SHIPPED`.

---

## Commands

```
python verify\success_signature.py                        THE gate
python -m unittest discover -s tests                      parts check (36)
python verify\determinism.py                              replay identity, cross-process
python harness\runner.py harness\missions\<mission>.json  general runner
```

## Evidence

```
harness\runs\LATEST.txt        name of newest run folder
harness\runs\<name>_<stamp>\   vitals.jsonl · events.jsonl · verdict.json
```

Run folders regenerate — safe to delete.

---

## Break glass

**NO on [3] replay** → nondeterminism entered. Doctrine list: CLAUDE.md.

**ModuleNotFoundError: salus** → wrong folder. Run from `G:\SALUS` root.

**NO on [2], zero wakes** → band swallowed the crossing. Check
`entropy_min_band` / `scattered_start` in the mission JSON.

---

## Touch map

Edit freely ......... `harness\missions\*.json` · `tests\`

Handle with care .... `src\salus\wake\` (floors + doctrine)

Read first .......... `BLUEPRINT.md` · `DESIGN.md` · `NOTICE.md`

**Proprietary — nothing from this repo goes public. (NOTICE.md)**
