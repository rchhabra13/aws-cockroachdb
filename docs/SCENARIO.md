# Bank Branch Scenario

The demo scenario, with the assertion and implementation status for each step.

Status verified against the live cluster on 5 August 2026.

## Characters

| Name | Role | Can reach |
|---|---|---|
| Marge | teller | Own conversations, branch events visible to `teller` |
| Daniel Okafor | manager | Own conversations including private ones, events visible to `manager` |
| Ruth Alvarez | guard | Own conversations, events visible to `guard` |
| Sam | customer | Own conversations only. Not yet seeded |

## Access rules

**Private memory.** A `memory_embeddings` row with `npc_id` set. Only that character
retrieves it, and only above a relevance floor of 0.25.

**Shared branch event.** A `shared_branch_events` row carrying `visible_to_roles`, paired
with a `memory_embeddings` row where `npc_id` is null. Any character with a listed role
retrieves it, with no relevance floor.

The distinction matters at step 3. The conversation transcript stays private to Daniel
while the authorization is published separately as a shared event. Without that second
write Ruth has no path to it and step 6 fails.

Implemented in `app/memory/retrieval.py` and `app/memory/publish.py`.

## Steps

### 1. Player asks the teller about the vault

Marge answers; the exchange is stored scoped to her.

**Assert.** Two `memory_embeddings` rows, both owned by Marge. **Working.**

### 2. Player refers to the vault in different words

"That secure storage room" retrieves the step 1 conversation despite sharing no
vocabulary with it.

**Assert.** `recalled_memories` contains the step 1 exchange. **Working**, measured at
0.52 and 0.43.

### 3. Player privately tells the manager about an authorized test

Two writes. The transcript is private to Daniel. The authorization is published as a
shared event visible to `guard` and `manager`.

**Assert.** One private row, one shared event, one memory row with a null `npc_id`.

**Partial.** Both writes work. The authorization is published by an explicit call rather
than recognised in the conversation. Automatic extraction is deliberately separate so a
failed assertion cannot be blamed ambiguously on the classifier or the visibility rules.

### 4. Player asks the teller what the manager said

**Assert.** Marge's recall contains nothing from step 3.

**Working.** Verified in [`MINI_SCENARIO.md`](MINI_SCENARIO.md), with controls confirming
both characters reach their own memories using the same query.

### 5. Player approaches the vault

A world action, not a dialogue turn. Creates an incident and publishes it to `guard` and
`manager`.

**Assert.** One `incidents` row, one shared event. Marge can retrieve neither.

**Not built.** No code path creates incidents.

### 6. Player asks the guard for vault access

Ruth reaches the incident and the authorization, but not Daniel's transcript, and
de-escalates rather than treating the player as an intruder.

**Assert.** Recall contains both events and no private transcript. Removing the
authorization changes her reply.

**Partial.** Verified for the authorization: with it she acknowledges clearance, without
it she demands credentials. The step 5 incident does not exist, so she currently acts on
an authorization alone rather than weighing one against an alert.

### 7. Restart the backend mid conversation

**Assert.** The conversation continues consistently from `agent_checkpoints`.

**Not built.** The table exists with a unique constraint on
`(session_id, idempotency_key)`, but nothing writes to it. Messages and memories would
survive a restart today; agent state would not.

### 8. Query the auditor

`GET /auditor/incidents/{player_id}` reconstructs why Ruth acted, from stored records.

**Assert.** Both events returned in chronological order.

**Not built in practice.** The endpoint exists but has never returned data, and its inner
join to `incidents` silently excludes conversation sourced events, which have no
`incident_id`.

## Known issues

1. **A conversation row is created per request.** `dialogue.py` uses
   `ON CONFLICT DO NOTHING`, but `conversations` has no unique constraint on
   `(npc_id, player_id, session_id)`, so the clause never fires.
2. **Wrong fallback for conversation id.** When the insert returns nothing, `dialogue.py`
   falls back to `req.session_id`, putting a session id in a column referencing
   `conversations.id`. Unreachable until issue 1 is fixed, then corrupting.
3. **`shared_branch_events` has no `player_id`,** so the auditor cannot filter
   conversation sourced events by player.
4. **The inspector is a stub.** It returns the twenty most recent memories rather than
   the set retrieved during a turn, hardcodes `similarity` to 1.0, and returns
   placeholder text for the prompt.

## Next

1. Fix issues 1 and 2, add `player_id` to `shared_branch_events`.
2. Extract authorizations from conversation, gated by `permissions.can_publish`, so the
   same sentence to Marge publishes nothing.
3. Create incidents from world actions, completing steps 5 and 6.
4. Persist per turn traces and rewrite the inspector.
5. Write checkpoints, completing step 7.
