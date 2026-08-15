# ADR-0006 — Blocked crossings retry; floors pace wakes, never erase conditions

**Status:** accepted (2026-08-15). Supersedes the v0.1.1-recheck note
that a blocked crossing consumes its hysteresis episode.

**Decision:** a crossing that fires while refractory or budget blocks
the wake re-arms its band and retries each tick, landing as soon as
the floor clears — or never, if the value exits the band first.

**Why:** consume semantics let a muzzled detector go silent forever on
a persistently-true condition. Demonstrated by adversarial recheck:
refractory 50, channel pinned above enter for 400 ticks, zero wakes
ever. A smoke detector that stays quiet because it was briefly muzzled
contradicts the thesis. Floors exist to pace wakes, not to erase the
conditions beneath them.

**Consequences:** a wake can land later than its crossing — at
floor-clear — still fully deterministically. "Fires once per crossing
episode" still holds: the retry is the same episode until it lands or
exits. clip_two evidence is unchanged (the rig has no blocked
crossings).
