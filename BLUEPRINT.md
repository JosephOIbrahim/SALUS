# CONDITION WAKES MEMORY — BLUEPRINT · 2026-08-15

*Imported verbatim as source of truth. Subsystem name confirmed by use: SALUS.*

*Public release note: internal project codenames in section 10 generalized; mechanism content unchanged.*

*Where this conflicts with older spec docs, this blueprint wins — it's newer.*

*Build amendments are recorded in DESIGN.md and docs/decisions/ (ADR-0002: Gate-0 re-sequenced).*

---

## 0 · Name block — three tiers

**Thesis / public name:** Condition Wakes Memory (CWM).

**Subsystem name:** **Salus** — she watches the vitals; Moneta keeps the memories.

**Mechanism name (core, mechanical):** wake predicate.

---

## 1 · The claim

Every memory system in the field answers: *what content matches this query?*

This answers: *what state is the knower in, and what does that state summon?*

The state is **measured, not reported** — statistics over ops that already run. No new op. All superpowers are readers.

---

## 2 · The path — one glance

```
four locked ops --> vitals readers --> setpoints --> wake predicate --> summon
   (run as-is)       (no new op)      (calibrated)   (deterministic)   (read-only)

floors rail: never evict - never mutate - t <= own now - authority declared
```

---

## 3 · The four vitals channels

| Channel | Reads from | Status at build |
|---|---|---|
| Per-belief staleness **U** | Moneta decay at access time | Live in substrate ranking; synthetic here |
| Attention stats — entropy, revisit, novel-touch | Attention log | Synthetic here; external reads gated on adapter-vs-§9 fork |
| Aggregate utility trend | Utility records | Reader built (synthetic) |
| Consolidation pressure | Deposit / consolidation op | Reader built (synthetic) |

---

## 4 · The wake path — six steps

1. **Ops run as normal.** The four locked ops emit their existing byproducts. Nothing added.

2. **Readers compute vitals** over sliding windows. Read-only. Mechanical names only in this layer.

3. **Setpoints hold the baseline.** A calibration phase records normal distributions; crossing bands come from those, with hysteresis so the wake doesn't flap.

4. **The predicate fires on a crossing.** Deterministic: same signals → same wake. Fixed evaluation order, batch-invariant stats.

5. **Summon is read-only.** The wake selects memories (§5 fork) and surfaces them. It may never evict, never mutate, never write.

6. **The wake event lands as data.** Time-sampled, addressable — scrubbable later (dailies), replayable (counterfactual-first).

---

## 5 · The selection fork — what does a condition summon?

**Design A — stamped deposits.** Encoding specificity: stamp each deposit with the depositing context's vitals; wake by condition-similarity. Human state-dependent memory, literally.

**Design B — policy table.** The bootstrap: entropy spike → orientation anchors; staleness crossing → verification memories; consolidation pressure → summaries due for compression.

**Recommendation: B now, A accruing.** Ship the table so the wake fires day one; stamp every deposit from day one so A switches on later without rework. (ADR-0003.)

---

## 6 · Floors and contract

The wake output is a **cognitive contract**: type + range + **authority** + **temporal validity**.

Floors — what no wake may ever do:

- evict or mutate anything (read-only summon)

- query t > its own now (causal mask)

- act without declared authority

- fire non-deterministically — same signals, same wake, replay-identical twice, or it's broken

---

## 7 · Inventory at build (honest four buckets)

**Built here:** vitals readers (4 channels), setpoints + hysteresis, wake predicate, Design-B policy, floors (refractory · budget · causal), typed contract, wake events as data, counterfactual fork, canonical jsonl, optional .usda emitter, clip-two mission, five-yes gate.

**Unverified (substrate side):** Phase 0 (attention-weight validation + deposit durability). Internal readability of the real attention log.

**Undetermined:** log *external* readability (adapter vs §9 — gates dailies). Setpoint calibration span for the real substrate. Deposit-stamp schema (Design A).

---

## 8 · Build sequence — as executed and as remaining

**Done 2026-08-15:** standalone deterministic vertical — engine + harness + gates, five yeses green on the rig (first wake t=142).

**Gate 0 (re-sequenced, ADR-0002):** verify Phase 0 — now gates INTEGRATION, not the standalone build.

**Next slices:** ops adapter to the real substrate behind `OpsReader` → deposit stamping on (additive) → policy v2 / Design A when the stamped corpus exists → gain loop LAST, only after activation validates against the real substrate.

---

## 9 · Success signature — v1 done means, on the rig:

1. Dormant while entropy is low.

2. Wake fires on the crossing.

3. Identical replay, run twice.

4. No floor breached.

5. The wake event is visible as data.

Five yeses = v1 shipped. **Achieved 2026-08-15: 5/5.** Push to ship; the last 10% can wait.

---

## 10 · Where it applies

**Dailies (practice).** Wake events + vitals are what the scrubber scrubs; CWM makes *condition* a replayable track. Ship artifact: the AOUSD second post. ⚠ Patent-status check before posting.

**Co-regulation (research).** One agent's wake thresholds adjusted by another under LIVRPS authority + floors. Ship artifact: the paper.

**Instrument.** Wakes as musical events — a voice's memory surfacing *is* a phrase entering.

**ND-OS.** The same predicate pointed at a human operator: depleted-state wakes different scaffolding than rolling-state. One instrument, two targets.

**Generic agent ops.** Anti-drift: entropy spike wakes orientation anchors; staleness wakes verification. Self-healing retrieval without a query.

---

## 11 · Open questions

- Calibration span for the real substrate: how long before setpoints are trustworthy?

- Stamp schema: which vitals, what precision, where in customData?

- Wake budget + refractory tuning against real attention dynamics — the predicate must never feed itself. (Enforced in code today: refractory + budget floors.)
