# WIRE_FORMAT — the canonical ops log (v1)

The integration seam (ADR-0005) is a file: one canonical JSON object
per line, one line per tick. A substrate that emits this format needs
nothing from SALUS source — this document is the whole contract. SALUS
replays the file through `ReplayOps` and never holds a live handle.

## File-level rules

| Rule | Value |
|---|---|
| Encoding | UTF-8, **no BOM** |
| Line endings | **LF only** (`\n`) — never CRLF, even on Windows |
| Structure | one JSON object per line; no blank lines; final line ends with `\n` |
| Serialization | canonical: `sort_keys=True`, compact separators `(",", ":")`, `allow_nan=False` |
| Non-finite floats | refused — `NaN` / `Infinity` are not JSON and never appear |
| Empty file | invalid — a log must contain at least one tick |

Canonical bytes matter: the same timeline must serialize to the same
bytes everywhere, because byte-identity is the replay check. If your
emitter is Python, this is exactly
`json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)`.

## Record shape

Each line is one `OpsSnapshot` — the read-only view of the four locked
ops at one tick. Six keys, no more required, sorted order on the wire:

```json
{"accesses":[{"target":"b1","tick":3}],"beliefs":[{"belief_id":"b1","last_access_tick":3,"utility":0.42}],"consolidation_capacity":8,"deposits_since_consolidation":2,"tick":3,"utility_total":0.42}
```

### Fields

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `tick` | int | The snapshot's tick | **must equal the line number** — ticks contiguous from 0, no gaps, no reorder |
| `accesses` | array of objects | Attention-log entries at this tick | each entry: `tick` (int), `target` (string). May be empty. |
| `beliefs` | array of objects | Every belief's decayed utility at snapshot time | **non-empty** — staleness is undefined over zero beliefs. Each entry: `belief_id` (string), `utility` (float, **finite**), `last_access_tick` (int) |
| `utility_total` | float | Sum of belief utilities | **finite** |
| `deposits_since_consolidation` | int | Deposits accrued since last consolidation | — |
| `consolidation_capacity` | int | Consolidation capacity | **>= 1** |

## Validation behavior

`ReplayOps(path)` validates the entire file at load and raises a typed
`OpsLogError` (from `salus.ops.replay`) on any violation — malformed
JSON, missing keys, tick gaps, empty belief set, capacity < 1,
non-finite utility, empty file. Doctrine: typed failure is detectable;
prose failure isn't. A bad log fails at load, never mid-run.

**Canonical framing and types are enforced, not assumed.** The reader
rejects, with typed errors: CR bytes anywhere (LF-only), a missing
final newline, non-ASCII bytes (canonical json escapes to ASCII),
non-finite JSON tokens (`Infinity`/`NaN`), and wrong-typed fields —
ticks and counts must be JSON integers (not floats, strings, or
booleans), utilities must be numbers, ids must be strings. A
hand-rolled emitter's log validates only if its bytes are canonical.
Both writers refuse to produce the empty log the reader rejects:
`dump_ops` raises on a zero-tick timeline, and `OpsLogWriter` raises
on a clean close with zero appends.

**Crash safety falls out of the line discipline.** `OpsLogWriter`
flushes after every line, so a crash mid-write can tear at most the
final line — and a torn line is not valid JSON, so `ReplayOps` reports
it as a parse error at that line. There is no silent partial record.

## Versioning

This is **v1**, and lines carry **no version field by design**. The
reader tolerates extra keys (they are ignored), so additive evolution
costs nothing. Any future breaking change is signaled out-of-band —
filename convention or a sidecar file — never by mutating or
reinterpreting the fields above. A v1 line means the same thing
forever.

## Integration example

Emit (one line per tick, from the live side of the seam):

```python
from salus.ops.shim import OpsLogWriter

with OpsLogWriter(Path("run.ops.jsonl")) as w:
    for snapshot in substrate.run():   # yields OpsSnapshot per tick
        w.append(snapshot)             # validates, writes one canonical line
```

Consume (replay + validate in one step — load IS validation):

```python
from salus.ops.replay import ReplayOps

ops = ReplayOps(Path("run.ops.jsonl"))  # raises OpsLogError if invalid
```

Or from the shell:

```
python -c "from pathlib import Path; from salus.ops.replay import ReplayOps; print(ReplayOps(Path('run.ops.jsonl')).ticks, 'ticks ok')"
```

## Pointers

- `src/salus/ops/replay.py` — `ReplayOps`, `OpsLogError`, `dump_ops`,
  and the canonical-bytes helpers (`snapshot_record`, `record_line`)
- `src/salus/ops/shim.py` — `OpsLogWriter`, the emitting side
- `src/salus/ops/interface.py` — `OpsSnapshot` and friends
- `docs/decisions/ADR-0005-adapter-seam.md` — why the seam is a file
