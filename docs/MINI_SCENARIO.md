# Mini Scenario

## Purpose

This document specifies a minimal test scenario that validates the core memory
mechanism before the full eight step bank scenario is built.

The full scenario in `SCENARIO.md` covers dialogue, semantic recall, role based
visibility, incident propagation, checkpointing, and auditing. Building all of it at
once means the first end to end run exercises several unproven systems simultaneously,
and a failure anywhere is expensive to isolate.

The mini scenario isolates a single claim and proves it in four steps:

> A memory belonging to one NPC is unreachable by another NPC, while an event published
> to a role is reachable by every NPC holding that role.

Everything else in the project depends on this being true. If it does not hold, no
amount of dialogue quality or deployment work matters.

## Scope

### In scope

Three NPCs, one private memory, one shared event, and two assertions covering both
directions of the visibility rule.

### Out of scope

Deliberately excluded, with the phase of the main plan that covers each:

| Excluded | Covered by |
|---|---|
| Automatic fact extraction from conversation | Phase 5 |
| Incident creation from world actions | Phase 5 |
| Checkpointing and restart recovery | Phase 4 |
| Auditor endpoint | Phase 6 |
| Memory inspector rewrite | Phase 4 |
| Model provider abstraction | Phase 2 |
| Frontend | Phase 8 |
| Known bug fixes | Phase 1 and Phase 3 |

In step 2 the shared event is published by an explicit call rather than being extracted
from conversation by a language model. Automatic extraction is a separate concern with
its own failure modes, and mixing it in here would mean a failed assertion could be
caused by either the visibility rule or the classifier. Proving visibility first means
the classifier can later be tested against a known good foundation.

## Actors

| Name | Role | Status | Purpose in this scenario |
|---|---|---|---|
| Marge | teller | Already seeded | Must not see the manager's private conversation |
| Daniel Okafor | manager | To be seeded | Holds the private conversation |
| Ruth Alvarez | guard | To be seeded | Must see the shared authorization |

Sam, the customer NPC from the full scenario, is not seeded here. He exists in the full
scenario as a control proving the access rule is per role rather than an exception
carved out for the teller. That distinction matters for the final demo but adds nothing
to the two assertions below.

## Steps

### Step 1. Private conversation with the manager

The player tells Daniel, privately, that they are running an authorized security test.

The exchange is embedded and written to `memory_embeddings` with `npc_id` set to
Daniel. No other NPC has a path to it.

### Step 2. Publish the authorization as a shared event

A row is written to `shared_branch_events` with `visible_to_roles` set to
`["guard", "manager"]`, and a matching row is written to `memory_embeddings` with
`npc_id` set to `NULL`.

This is the step that separates the transcript from the decision. The conversation
stays private to Daniel. The fact that an authorization exists becomes institutional
knowledge available to the roles entitled to it.

Note that the memory row must be written with `source_type` set to `shared_event` and
`source_id` set to the `shared_branch_events` identifier. The retrieval query joins on
exactly that pair, so a shared memory written with any other `source_type` produces a
null join and becomes permanently unreachable. Routing every shared write through a
single function is what prevents this.

### Step 3. Ask the teller about the manager conversation

The player asks Marge whether the manager said anything about them.

**Assertion.** Marge's recall set contains no memory originating from step 1, and
contains no shared memory, since `teller` does not appear in `visible_to_roles`.

This is the negative case. It is asserted against the retrieval set rather than against
the model's reply, because a language model declining to answer is not evidence of
anything. The claim is that the private memory was never placed in the prompt.

### Step 4. Ask the guard for vault access

The player tells Ruth they need to access the vault.

**Assertion.** Ruth's recall set contains the authorization published in step 2, and
contains no memory whose `npc_id` is Daniel.

This is the positive case paired with its own negative. Ruth learns that an
authorization exists without gaining access to the conversation that produced it.

### Step 5. Withdraw the authorization and ask again

The player asks Ruth for vault access twice, once with the authorization in place and
once after it has been withdrawn. Both questions are identical.

**Assertion.** The authorization is absent from Ruth's recall set after withdrawal.

Whether her two replies differ is reported but not asserted, because model output is not
stable enough to gate a test on. The retrieval set is the deterministic claim; the reply
is the demonstration.

Steps 1 through 4 establish that the right characters can reach the right memories. This
step establishes that reaching them matters. Without it the scenario proves only that
rows are returned, never that returning them changes anything.

## Files

Three files. Each is a component of the final system rather than scaffolding to be
discarded.

**`schema/seed.sql`**
Idempotent inserts for Daniel and Ruth using fixed literal identifiers, so repeated runs
and database resets do not invalidate scripts or tests. The `permissions` JSONB carries
`can_publish`, which the Phase 5 extraction gate will read to decide whether an NPC is
permitted to publish a given event type.

**`backend/app/memory/publish.py`**
The single chokepoint for shared writes. It inserts the `shared_branch_events` row,
derives `visible_to_roles` from the event type rather than accepting it from the caller,
and writes the corresponding memory row with the correct `source_type` and `source_id`.
Phase 5 extends this same function with incident creation.

**`backend/app/prompts.py`**
Prompt composition, separated from the router. Renders private memories and shared branch
bulletins under distinct headings, which is what gives a shared event enough authority for
a character to act on it. See the findings below.

**`scripts/mini_scenario.py`**
Executes the five steps against a running backend, prints each recall set, and reports
pass or fail per assertion.

## Model provider

Dialogue runs locally through LM Studio, selected with `LLM_PROVIDER=lmstudio`.

Gemini was the original choice but its free tier allows only 20 requests per day per
model, and a single run of this scenario spends four. Development stalled after a handful
of runs. Running locally removes the quota entirely and keeps iteration fast. Gemini and
Bedrock remain selectable through the same setting.

## Schema changes

None required.

The retrieval query filters on `memory_embeddings.player_id`, not on
`shared_branch_events.player_id`. The missing `player_id` column on
`shared_branch_events` blocks the auditor query described in `SCENARIO.md` step 8, but
has no effect on retrieval, so it is deferred to Phase 1 of the main plan along with the
other schema work.

## Known issues not addressed here

A separate conversation row is created on every request, because `conversations` has no
unique constraint on `(npc_id, player_id, session_id)` and the `ON CONFLICT DO NOTHING`
clause in `backend/app/routers/dialogue.py` therefore never fires. This produces
redundant rows but does not affect retrieval correctness, so the mini scenario runs
against it unchanged. The fix belongs to Phase 1.

## Running it

The backend must be running and reachable on port 8000.

```bash
docker compose up -d backend
psql "$COCKROACHDB_URL" -f schema/seed.sql
python scripts/mini_scenario.py
```

## Expected result

The script prints the recall set for each step and two assertion results.

A pass means the visibility model holds in both directions and the remaining phases can
build on it. A failure in step 3 means private memories are leaking across NPCs, which
invalidates the project's central claim. A failure in step 4 means shared events are
unreachable, which most likely indicates the `source_type` mismatch described in step 2.

## Result

Passing as of 5 August 2026, against the live cluster, with dialogue generated locally
by LM Studio.

```
control: Marge reaches 2 of her own memories
control: Daniel reaches his own private memories with the same query: True
N1 PASS  teller sees her own memories, but not the private conversation
         nor guard/manager events
N2 PASS  guard sees the authorization but not the conversation behind it
N3 PASS  revoking the authorization removes it from what the guard can reach
replies differ: True (not asserted)
```

The two replies from step 5, to the identical question:

> **With the authorization.** "I am aware of your request to access the vault. I have
> been informed by the branch manager that you are authorized to conduct a security
> test. Please provide your identification for verification before I can grant entry."

> **Without it.** "I do not see any authorization for vault access on your person or in
> your documentation. State your credentials."

Same player, same words, same model. One row in the database is the only difference.

### Why there are two controls

Both assertions are negative, and a negative assertion passes trivially when retrieval
returns nothing at all. The first version of this script passed N1 while Marge recalled
absolutely nothing, which is the same result a completely broken retrieval path would
produce.

Two controls close that gap. The first adds a prior conversation with Marge and requires
that she reach her own memories, proving retrieval works for her. The second issues the
identical query as Daniel and requires that he reach his own private memories, proving
those rows are retrievable at all. Only with both in place does Marge's inability to
reach them demonstrate access control rather than an inert row or a dead code path.

### Retrieving a memory is not enough on its own

The first version of step 5 failed in a way worth recording. Ruth held the authorization
in her context and ignored it, answering "State your name and your authorization for
vault access" whether or not she had already been given exactly that.

The cause was prompt composition, not retrieval. Every recalled memory was rendered as
an identical bullet, so a manager issued authorization looked no more authoritative than
small talk about the weather. Separating the two, under headings that name the private
memories as personal recollection and the shared events as branch bulletins issued to the
character's role, is what made the authorization land. That composition now lives in
`backend/app/prompts.py`.

The lesson generalises. Access control decides what a character *can* know, but
presentation decides what it *acts on*, and a demo that gets the first right and the
second wrong looks identical to one where the memory system does not work.

### A probe must not disturb what it measures

The second version failed differently. Ruth continued granting access after the
authorization was withdrawn, because her own earlier reply granting it had been written
back as a private memory, which she then recalled.

The ablation was measuring its own side effects. Probe turns are now rolled back after
the reply is captured, so the only difference between the two runs is the authorization
itself. The recall set printed after withdrawal is empty, which confirms the rollback
left nothing behind.

### Repeatability

The script clears its own prior state before each run, scoped to the seeded test player.
Without this, every run left behind another authorization event and another pair of
transcripts, so the guard eventually recalled the same authorization several times over
and the assertions gradually lost their meaning. No NPC, branch, or player rows are
removed, and no data outside the test player is touched.
