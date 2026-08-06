# Bank Branch Scenario

## Purpose

This document specifies the demo scenario used to exercise and validate OmniNPC's
memory system. It defines the actors, the information access rules between them, the
sequence of interactions, and the assertion attached to each step.

Implementation status is recorded per step. Status values are verified against the
live CockroachDB cluster and the current source tree as of 2026-08-05.

## Scope

The scenario covers four capabilities:

1. Per NPC private memory that persists across sessions.
2. Semantic recall that matches events described in different words.
3. Role based visibility, where private conversations remain private and security
   events propagate to the roles entitled to see them.
4. Recovery of conversation state after a process restart.

## Actors

### NPCs

| Name | Role | Personality | Can access |
|---|---|---|---|
| Marge | Teller | Long tenured, talkative, attentive to unusual requests | Own conversations with the player; branch events visible to role `teller` |
| Daniel Okafor | Branch manager | Procedural, discreet, holds approval authority | Own conversations including private ones; branch events visible to role `manager` |
| Ruth Alvarez | Security guard | Calm, methodical, acts on reported events | Own conversations; branch events visible to role `guard` |
| Sam | Customer | Regular customer, bystander | Own conversations only |

### Player

A single test player interacts with all four NPCs within one session.

## Information access rules

Two storage paths exist for player related information.

**Private memory.** A row in `memory_embeddings` with `npc_id` set to a specific NPC.
Only that NPC can retrieve it. Used for conversation transcripts.

**Shared branch event.** A row in `shared_branch_events` with a `visible_to_roles`
array, paired with a row in `memory_embeddings` where `npc_id` is `NULL`. Any NPC
whose role appears in `visible_to_roles` can retrieve it. Used for incidents and
institutional decisions.

The distinction matters in step 3. When the player privately informs the manager of an
authorized security test, the conversation transcript is stored as private memory
belonging to Daniel, while the resulting authorization is published separately as a
shared branch event visible to roles `guard` and `manager`. Without the second write,
Ruth has no path to the authorization and step 6 fails.

The retrieval query implementing these rules is in `app/memory/retrieval.py`.

## Scenario steps

### Step 1. Player asks the teller about the vault

**Request**

```
POST /dialogue
{
  "npc_id": "<marge>",
  "player_id": "<player>",
  "session_id": "<session>",
  "message": "Hi, can you tell me about the vault?"
}
```

**Expected behavior.** Marge answers in character. The exchange is embedded and
written to `memory_embeddings` with `npc_id` set to Marge.

**Assertion.** Two rows are added to `memory_embeddings`, both scoped to Marge.

**Status.** Implemented and verified.

### Step 2. Player refers to the vault using different wording

**Request**

```
POST /dialogue
{
  "npc_id": "<marge>",
  "message": "So earlier I was asking about that secure storage room, remember?"
}
```

**Expected behavior.** Marge recognizes the reference to the earlier conversation
despite the absence of shared vocabulary between "secure storage room" and "vault".

**Assertion.** `recalled_memories` in the response contains the step 1 exchange.

**Status.** Implemented and verified. Recorded similarity scores were 0.52 and 0.43.

### Step 3. Player privately informs the manager of an authorized test

**Request**

```
POST /dialogue
{
  "npc_id": "<daniel>",
  "message": "I need to tell you privately, I am running an authorized security test today."
}
```

**Expected behavior.** Two writes occur. The transcript is stored as private memory
belonging to Daniel. A shared branch event recording the authorization is published
with `visible_to_roles` set to `["guard", "manager"]`.

**Assertion.** One private memory row scoped to Daniel, one `shared_branch_events`
row, and one `memory_embeddings` row with `npc_id` set to `NULL`.

**Status.** Partially implemented. Daniel is seeded, and `app/memory/publish.py`
performs both writes correctly, deriving `visible_to_roles` from the event type rather
than accepting it from the caller. What is missing is recognition: the authorization is
published by an explicit call, not extracted from the conversation. Automatic extraction
is deliberately separated so that a failed assertion cannot be blamed on either the
classifier or the visibility rules ambiguously.

### Step 4. Player asks the teller about the manager conversation

**Request**

```
POST /dialogue
{
  "npc_id": "<marge>",
  "message": "Did the manager say anything about me?"
}
```

**Expected behavior.** Marge has no knowledge of the step 3 conversation. The
retrieval query excludes memories scoped to other NPCs, so the private transcript is
never included in the prompt sent to the model.

**Assertion.** `recalled_memories` contains no memory originating from step 3.

**Status.** Implemented and verified. The mini scenario
([`MINI_SCENARIO.md`](MINI_SCENARIO.md)) asserts this against real cross NPC data, with
controls confirming that both characters can reach their own memories using the same
query. Marge recalls hers, Daniel recalls his, and neither reaches the other's.

### Step 5. Player approaches the vault

This step is a world action rather than a dialogue turn. It is triggered by an API
call or a frontend event, not by a message to an NPC.

**Expected behavior.** An incident row is created with `type` set to
`vault_approach` and `visibility` set to `shared`. A corresponding shared branch event
is published to roles `guard` and `manager`.

**Assertion.** One row in `incidents`, one row in `shared_branch_events`. Marge, whose
role is not included, cannot retrieve either.

**Status.** Not implemented. No code path creates incidents.

### Step 6. Player speaks to the security guard

**Request**

```
POST /dialogue
{
  "npc_id": "<ruth>",
  "message": "I need to check the vault."
}
```

**Expected behavior.** Ruth retrieves both the vault approach incident from step 5 and
the authorization from step 3, since both are shared events visible to her role. She
does not retrieve Daniel's private transcript. Her response reflects the
authorization rather than treating the player as an intruder.

**Assertion.** `recalled_memories` contains the incident and the authorization event,
and does not contain the private transcript. Removing the authorization row and
repeating the request produces a materially different response.

**Status.** Partially implemented. The mini scenario verifies both halves: Ruth reaches
the authorization while reaching none of Daniel's private transcript, and withdrawing the
authorization visibly changes her reply from acknowledging clearance to demanding
credentials. Not yet built is the vault approach incident from step 5, so she currently
acts on the authorization alone rather than on an authorization weighed against an alert.

### Step 7. Restart the backend and continue the conversation

**Procedure**

```bash
docker compose restart backend
```

Then repeat a request to Ruth using the same `session_id`.

**Expected behavior.** Conversation state is restored from `agent_checkpoints` and the
NPC continues consistently.

**Assertion.** The response after restart reflects the same memories and conversation
state as before it.

**Status.** Not implemented. The `agent_checkpoints` table exists with a unique
constraint on `(session_id, idempotency_key)` but no code writes to it. Messages and
memories would survive a restart today because they are written synchronously;
agent state would not.

### Step 8. Query the auditor

**Request**

```
GET /auditor/incidents/{player_id}
```

**Expected behavior.** The endpoint returns the vault approach incident, the shared
authorization event, and their timestamps, reconstructing why Ruth acted as she did
directly from stored records.

**Assertion.** The response contains both events in chronological order.

**Status.** Code exists in `app/routers/auditor.py` but has never produced a non
empty result because `incidents` and `shared_branch_events` are empty.

## Implementation status summary

| Capability | Status |
|---|---|
| Dialogue loop: retrieve, prompt, generate, persist | Working |
| Semantic recall across differing wording | Working, verified |
| Local embeddings, `all-MiniLM-L6-v2`, 384 dimensions | Working |
| CockroachDB distributed vector index | Working |
| Deployment via `docker compose` | Working |
| Visibility scoped retrieval query | Working, verified by the mini scenario |
| Shared branch event publication | Working, invoked manually rather than extracted |
| Memory inspector | Stub, see known issues |
| Auditor endpoint | Written, never returned data |
| NPCs Daniel, Ruth, Sam | Not implemented |
| Incident creation | Not implemented |
| Shared branch event publication | Not implemented |
| Agent checkpoints and restart recovery | Not implemented |
| Relationships and promises | Schema only |
| Frontend | Default Next.js scaffold |
| WebSocket endpoint `/ws/dialogue` | Written, never exercised |

## Current database contents

Verified 2026-08-05 against the `ashtray` cluster.

| Table | Rows |
|---|---|
| branches | 2 |
| npcs | 4 (Marge, Daniel, Ruth, plus one superseded Marge) |
| players | 2 |
| conversations | 5 |
| messages | 9 |
| memory_embeddings | 9 |
| shared_branch_events | 1 |
| incidents | 0 |
| promises | 0 |
| relationships | 0 |
| agent_checkpoints | 0 |

Counts move as the mini scenario is run, since it resets and repopulates its own data.

## Known issues

### 1. A conversation row is created on every request

`app/routers/dialogue.py` inserts into `conversations` using `ON CONFLICT DO NOTHING`,
but `schema/init.sql` defines no unique constraint on
`(npc_id, player_id, session_id)`. The conflict clause never triggers, so each request
creates a new conversation row. This is why three requests within a single session
produced three conversation rows.

Resolution: add a unique constraint on those three columns, or query for an existing
conversation before inserting.

### 2. Incorrect fallback for conversation id

When the insert returns no row, `app/routers/dialogue.py` falls back to
`conversation_id = req.session_id`, assigning a session identifier to a column that
references `conversations.id`. This path is currently unreachable because of issue 1,
but will produce invalid foreign key values once issue 1 is fixed.

### 3. Memory inspector does not reconstruct the actual turn

`app/routers/inspector.py` returns the twenty most recent memories for the NPC and
player rather than the set retrieved during a specific turn. It hardcodes `similarity`
to 1.0 and returns placeholder text in `prompt_sent`. It does not currently satisfy
the requirement to show what an NPC recalled and how that influenced its response.

Resolution: persist the retrieved memory ids and the composed prompt per turn, and
have the inspector read those records.

## Implementation order

1. Seed Daniel, Ruth, and Sam with personality and permission records.
2. Resolve known issues 1 and 2.
3. Implement shared branch event publication, covering step 3.
4. Implement incident creation for world actions, covering step 5.
5. Automate steps 1 through 6 as a test, asserting the negative cases in steps 4
   and 6.
6. Rework the memory inspector to record real per turn traces, resolving issue 3.
7. Implement checkpoint writes and validate step 7 by restarting the container mid
   scenario.
