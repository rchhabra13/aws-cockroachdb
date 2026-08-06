# Comprehensive Bank Branch Scenario

This document describes the intended end-to-end OmniNPC demonstration. It serves as both
a product walkthrough and an implementation reference, with each stage identifying the
features available in the repository and the features on the roadmap.

## Objective

The scenario demonstrates a world in which characters remember a shared player but do
not automatically share all information about that player.

The central example separates two records:

- A private conversation in which the player tells a manager about a security test.
- An official authorization derived from that conversation and published to the roles
  that need it.

The teller should receive neither record through recall. The security guard should
receive the authorization but not the manager's private transcript.

## Participants

| Participant | Role | Memory access |
|---|---|---|
| Player One | Player | The fixed test identity used by the seed data and verification script |
| Marge | Teller | Her private conversations with the player; teller-visible events |
| Daniel Okafor | Manager | His private conversations with the player; manager-visible events |
| Ruth Alvarez | Security guard | Her private conversations with the player; guard-visible events |

The three NPCs and the player are created by `schema/seed.sql` with stable identifiers so
the scenario can be repeated after database resets.

## Memory model

### Private character memory

Each player and NPC message is embedded and stored in `memory_embeddings` with both an
`npc_id` and a `player_id`. Private recall requires both identifiers to match. Relevant
memories are ranked with vector similarity, filtered with the current similarity floor,
and limited to eight results.

As a result, a recall request for Marge has no database path to a row owned by Daniel or
Ruth. The restriction is applied before prompt construction.

### Role-scoped branch events

A published branch event consists of:

1. A `shared_branch_events` row containing the summary and allowed roles.
2. A `memory_embeddings` row with `source_type = 'shared_event'`, the event identifier as
   its source, the associated player, and no NPC owner.

The server derives the audience from the event type in `backend/app/roles.py`; callers do
not supply an arbitrary list of roles. Recall joins the two records and checks whether
the requesting NPC's role is present in `visible_to_roles`.

Shared events are ranked but are not subject to the private-memory similarity floor.
This allows an active authorization to reach an entitled role even when the player's
wording is only weakly similar to the event summary.

### Prompt composition

The prompt labels personal memories and official branch bulletins as separate sections.
This provenance matters: visibility determines what a character can receive, while the
prompt structure tells the character which retrieved facts are authoritative.

## Walkthrough

### Stage 1: Start a conversation with the teller

The player asks Marge for help with an account balance. The API retrieves any relevant
memories belonging to Marge, generates her response, and stores both messages as Marge's
private memories for this player.

**Available.**

This stage establishes a positive control: Marge must be able to recall her own relevant
conversation later. A privacy check is not meaningful if the entire retrieval path is
broken.

### Stage 2: Refer to the earlier topic indirectly

The player refers to the earlier request using different wording. Semantic retrieval
should find the relevant exchange even when the new message does not repeat the same
keywords.

**Available.**

Private memories use the local `all-MiniLM-L6-v2` embedding model and CockroachDB vector
distance. The current similarity threshold was selected from observed results for that
model and must be recalibrated if the embedding model changes.

### Stage 3: Speak privately with the manager

The player tells Daniel that they are conducting an authorized security test. The
exchange is stored with Daniel's NPC identifier and is therefore private to Daniel.

**Available.**

At this point, no other character should know about the conversation, and the guard does
not yet have an operational authorization.

### Stage 4: Publish the authorization

The manager's decision is summarized as a branch event of type `authorization`. The
server maps that event type to the `guard` and `manager` roles, then stores a role-scoped
memory without exposing Daniel's transcript.

**In progress.**

`publish_shared_event()` performs the required writes and audience mapping. The current
dialogue route does not classify the manager's message or call this function
automatically; the verification script publishes the event explicitly.

### Stage 5: Confirm the teller's isolation

The player asks Marge whether the manager said anything about them. The system inspects
Marge's recall set rather than judging privacy from her generated wording.

Expected result:

- Marge can retrieve her own relevant memories.
- Marge cannot retrieve Daniel's private messages.
- Marge cannot retrieve the authorization because `teller` is not in its audience.
- Daniel can retrieve his own private messages, proving that those rows are active rather
  than globally unreachable.

**Available and covered by the mini verification script.**

The assertion is made against source identifiers returned by retrieval. A model refusing
to discuss the manager would not, by itself, prove that the private records were absent
from its prompt.

### Stage 6: Record a vault approach

The player walks toward the vault. The world should record a `vault_approach` incident
and publish it to the guard and manager roles.

**Roadmap.**

The database contains `incidents` and `shared_branch_events` tables, and the visibility
map includes a `vault_approach` event type. No route or service currently converts a
world action into an incident or a shared event.

### Stage 7: Ask the guard for access

The player asks Ruth to enter the vault. Ruth should receive the official authorization
without receiving Daniel's private conversation. In the complete scenario, she would
also evaluate the vault-approach incident and authorization together.

**In progress.**

The current retrieval and prompt paths deliver the explicitly published authorization
to Ruth, and the mini script verifies its source identifier. The incident portion of the
decision is unavailable until Stage 6 is complete.

### Stage 8: Withdraw the authorization

The authorization is withdrawn, and the player repeats the same request. Ruth should no
longer receive the event and should no longer treat the security test as authorized.

**Available as a test operation only.**

The mini script deletes the event and its memory row to perform an ablation test. The
application schema does not yet provide a revocation timestamp, lifecycle endpoint, or
event history suitable for production use. Generated replies are displayed for
comparison, but the deterministic assertion checks the retrieval set.

### Stage 9: Restart during a session

The backend restarts while a conversation is active. Stored messages and memory rows
remain in CockroachDB, and a complete implementation should resume any in-progress agent
state without duplicating a turn.

**In progress.**

Messages and semantic memories persist across process restarts. The
`agent_checkpoints` table and idempotency constraint exist, but no application code reads
or writes checkpoints.

### Stage 10: Explain the guard's decision

An auditor asks why the guard challenged or admitted the player. The response should be
assembled from stored incidents, authorizations, and timestamps rather than from a
model's recollection.

**Limited support.**

The auditor endpoint lists incidents for a player and shared events linked to those
incidents. Authorizations created by `publish_shared_event()` do not carry an incident
identifier, so they are omitted from the current shared-event query.

## Component overview

| Area | Implemented | Next steps |
|---|---|---|
| Dialogue | FastAPI HTTP and WebSocket routes; configurable dialogue provider | Domain validation, session-level conversation reuse, production error handling |
| Private memory | NPC- and player-scoped semantic storage and recall | Retention policy and deduplication |
| Shared memory | Server-owned role mapping and shared-event recall | Automatic publication, event lifecycle, branch constraint in recall |
| World state | Tables for incidents, promises, and checkpoints | Services that create, update, and consume those records |
| Observability | Inspector and auditor routes exist | Persist exact turn traces and include all relevant event types |
| User interface | Next.js project is present | Product interface and API integration |
| Deployment | Backend and frontend Dockerfiles; Compose configuration | EKS manifests, operational configuration, and end-to-end deployment validation |

## Verification

The executable subset is documented in
[Mini Verification Scenario](MINI_SCENARIO.md) and implemented by
`scripts/mini_scenario.py`.

Run it with the backend available on port `8000`:

```bash
psql "$COCKROACHDB_URL" -f schema/seed.sql
backend/.venv/bin/python scripts/mini_scenario.py
```

The script validates three deterministic invariants:

1. The teller cannot retrieve the manager's private conversation or a security-only
   event, while both positive controls succeed.
2. The guard retrieves the authorization but not the conversation that produced it.
3. After the authorization is removed, the guard can no longer retrieve it.

Model replies are printed as supporting evidence but are not used as pass/fail criteria,
because generated wording is nondeterministic.

## Known limitations

The following items should be addressed before production use:

1. The dialogue route creates a new `conversations` row for every request. Its
   `ON CONFLICT DO NOTHING` clause has no matching uniqueness constraint.
2. The fallback conversation identifier uses the session identifier where a
   `conversations.id` value is required. This path becomes reachable once conversation
   reuse is corrected.
3. Shared-event recall checks player and role but does not constrain the event to the
   requesting NPC's branch.
4. `shared_branch_events` does not store `player_id`; the association exists only through
   its memory row, which complicates audit and lifecycle operations.
5. The inspector reconstructs a recent eligible-looking memory list rather than storing
   the exact recall set and prompt used for a specific turn. It also does not apply the
   shared-event role filter used by dialogue recall.
6. Shared events have no first-class revocation state. The mini scenario deletes its test
   event to simulate withdrawal.
7. The frontend is the default Next.js starter page and is not connected to the API.

## Recommended implementation sequence

1. Correct conversation identity and reuse.
2. Add player and lifecycle metadata to shared events, then enforce branch scope during
   shared recall.
3. Add permission-aware event extraction and publication to the dialogue flow.
4. Implement world actions and incident creation.
5. Persist exact turn traces and checkpoints; update the inspector and auditor to use
   them.
6. Build the web experience and production deployment configuration.

## Relevant files

| File | Responsibility |
|---|---|
| `backend/app/routers/dialogue.py` | Dialogue orchestration and message persistence |
| `backend/app/memory/retrieval.py` | Private and role-scoped recall queries |
| `backend/app/memory/publish.py` | Shared-event publication |
| `backend/app/prompts.py` | Prompt composition and memory provenance labels |
| `backend/app/roles.py` | Server-owned event-to-role mapping |
| `schema/init.sql` | Database schema and vector index |
| `schema/seed.sql` | Stable scenario participants |
| `scripts/mini_scenario.py` | Repeatable executable verification |
