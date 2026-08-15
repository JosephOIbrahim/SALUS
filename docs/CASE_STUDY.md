# Case study: the agent that lost the thread

*The numbers below are real — they come from the shipped `clip_two`
mission, replayable from this repo with one command. The scenario
around them is the intended deployment.*

## The setting

A coding agent is three hours into a refactor across a large repo. Its
memory substrate holds a few hundred beliefs — architecture notes,
decisions made earlier in the session, the original goal. The four
locked ops run as normal: beliefs get accessed, utility decays,
deposits accumulate. SALUS sits beside it, reading. No queries, no new
ops.

## Act 1 — baseline

For the first stretch of the session the agent is locked in. Its
attention log shows the same handful of targets over and over — the
two modules it's refactoring, the test file, the plan. SALUS's
calibration window watches this and learns what focus *looks like* for
this agent: attention entropy hovering around 0.9 bits, tight
distribution, low sigma. The entropy band gets set at baseline + 4σ —
about 1.5 bits. Dormant. SALUS emits vitals every tick and does
nothing else.

**This is yes #1: dormant while entropy is low.**

## Act 2 — the drift

Around the three-hour mark something familiar happens: a failing test
pulls the agent into a rabbit hole. It touches a config file, then a
vendored dependency, then an unrelated module, then old session notes,
then back — twelve different targets in one window where before there
were three. No single access looks wrong. *Every* retrieval system on
the market sees nothing here, because nobody asked a bad query —
there's no query at all. The failure mode is a **shape in the
attention distribution**, and content matching is blind to it.

SALUS isn't. Entropy climbs through 1.52 bits — past the band.
Crossing detected. **Yes #2.**

## Act 3 — the wake

Rule R1 fires: entropy spike → summon class `orientation_anchors`.
The Design-B policy table says: this condition summons the session
goal, the architecture decision record, the "you are here" plan state.
The summon is read-only — those memories get *surfaced* into the
agent's context; nothing is written, nothing evicted. The agent's next
reasoning step happens with the original goal sitting in front of it
again.

The agent never knew it was drifting. It never asked for help. **The
condition did the retrieving.**

## Act 4 — the floors hold

The refactor stays messy for a while and entropy stays elevated — but
the wake doesn't spam. Hysteresis: the band re-arms only after entropy
drops back below the exit threshold. Refractory: a blocked crossing
retries, but nothing lands within the refractory window. Budget: a
hard cap on wakes per window, so even a pathological session can't
turn SALUS into a car alarm — the predicate never feeds itself. And at
the wake itself, the engine forked the timeline, ran ten ticks with
the wake suppressed, and hashed the result: zero divergence. Proof,
per-wake, that surfacing memories changed nothing in the substrate.
**Yes #4.**

## Act 5 — the postmortem

Next morning, the operator scrubs the session like footage. The wake
event is a data record: tick 142, channel, value 1.523 against
threshold 1.498, summon class, a typed contract (authority, validity
window), and the counterfactual hash. Replay the mission and you get
byte-identical evidence — so "why did it wake there?" has an answer
you can check, not a vibe. **Yes #3 and #5.**

## The counterfactual that sells it

Without SALUS, that session ends the way everyone's sessions end — the
agent burns an hour in the rabbit hole, the human notices, scrolls
back, re-pastes the goal. SALUS's pitch is that the re-paste happens
automatically, at tick 142 instead of tick 900, triggered by
measurement instead of frustration.

## The same predicate, re-pointed

Swap the attention log for a human operator's session signals and
`orientation_anchors` for scaffolding — a depleted state wakes
different support than a rolling state. Same engine, different
patient. One instrument, two targets.

---

Run it yourself, from the repo root:

```
python verify\success_signature.py
```
