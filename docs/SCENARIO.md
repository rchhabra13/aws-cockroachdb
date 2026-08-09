# Bank Branch Scenario

The intended end-to-end OmniNPC demonstration, with the implementation status of every
stage marked honestly. Stages marked **Roadmap** do not work yet.

## Objective

A world in which characters remember a shared player but do not automatically share all
information about that player.

The central example separates two records:

- A private conversation in which the player tells a manager about a security test.
- An official authorization derived from that conversation and published to the roles
  that need it.

The teller should receive neither record through recall. The security guard should
receive the authorization but not the manager's private transcript.

## Participants

| Participant | Role | Memory access |
|---|---|---|
| Player One | Player | The fixed demo identity created by the seed data |
| Marge | Teller | Her private conversations with the player; teller-visible events |
| Daniel Okafor | Manager | His private conversations with the player; manager-visible events |
| Ruth Alvarez | Security guard | Her private conversations with the player; guard-visible events |

All four are created by `schema/seed.sql` with stable identifiers, so the scenario
survives a database reset. The seed also adds a second teller (Omar Reed), a loan officer
(Priya Shah), a compliance officer (Grace Okonkwo), and a wealth advisor (Victor Cross) —
seven characters in all — so the game client can demonstrate isolation between two NPCs of
the same role and route compliance events to the desks entitled to them.

## Memory model

### Private character memory

Each player and NPC message is embedded and stored in `memory_embeddings` with an
`npc_id`, a `player_id`, and a `session_id`. Private recall requires the npc and player
identifiers to match, and — when the caller is session-bound, as the game client always is
— the session id as well. Relevant memories are ranked with vector similarity, filtered
with the current similarity floor, and limited to eight results.

A recall request for Marge therefore has no database path to a row owned by Daniel or
Ruth, nor to a row from a different play session. Each session is its own collection: a new
tab or reload starts every character's memory from empty, and closing the tab tears that
session's rows down. The restriction is applied before prompt construction.

### Role-scoped branch events

A published branch event consists of:

1. A `shared_branch_events` row containing the summary and allowed roles.
2. A `memory_embeddings` row with `source_type = 'shared_event'`, the event identifier as
   its source, the associated player, and no NPC owner.

The server derives the audience from the event type in `backend/app/roles.py`; callers do
not supply an arbitrary list of roles. Recall joins the two records and checks whether the
requesting NPC's role is present in `visible_to_roles`.

Shared events are ranked but are not subject to the private-memory similarity floor. This
lets an active authorization reach an entitled role even when the player's wording is only
weakly similar to the event summary.

### Prompt composition

The prompt labels personal memories and official branch bulletins as separate sections.
Visibility decides what a character can receive; prompt structure tells the character
which retrieved facts are authoritative.

## Walkthrough

### Stage 1: Start a conversation with the teller

The player asks Marge for help with an account balance. The API retrieves any relevant
memories belonging to Marge, generates her response, and stores both messages as Marge's
private memories for this player.

**Available.** This stage is the positive control: a privacy check means nothing if the
retrieval path is broken for everyone.

### Stage 2: Refer to the earlier topic indirectly

The player refers to the earlier request using different wording.

**Available for paraphrase. Not available for anaphoric reference.** Measured against the
stored message `"Morning. I would like to check my account balance."` with
`all-MiniLM-L6-v2` and the 0.25 floor:

| Query | Similarity | Recalled |
|---|---|---|
| `how much money is in my account?` | 0.476 | yes |
| `can you help me with my balance?` | 0.399 | yes |
| `Sorry, what was I asking you about a moment ago?` | 0.165 | no |
| `remind me what I came in for` | 0.105 | no |
| `what did we just talk about?` | 0.034 | no |
| `what is the weather like on Jupiter` (control) | 0.063 | no |

A paraphrase that carries the topic is retrieved. A pure pointer back to the conversation
carries no topic to embed, so it scores at noise level — `what did we just talk about?`
(0.034) ranks *below* the unrelated Jupiter control (0.063). Lowering the floor cannot fix
this without admitting everything.

The cause is architectural, not a threshold problem: **the prompt contains no conversation
history**. `compose_system_prompt()` is built entirely from vector-search hits, so a turn
is stateless except for what similarity happens to return. The fix is a short-term window
of recent turns included regardless of score, alongside the similarity-ranked long-term
memories. That window does not exist yet.

Demo consequence: use a paraphrase, not "what did we just talk about?"

### Stage 3: Speak privately with the manager

The player tells Daniel they are conducting an authorized security test. The exchange is
stored with Daniel's NPC identifier and is therefore private to Daniel.

**Available.** At this point no other character knows about the conversation, and the
guard has no operational authorization.

### Stage 4: Publish the authorization

The manager's decision is summarized as a branch event of type `authorization`. The server
maps that event type to the `guard` and `manager` roles and stores a role-scoped memory
without exposing Daniel's transcript.

**Partly available.** `publish_shared_event()` performs the writes and audience mapping,
and `POST /world/authorize` exposes it as an operator action. The dialogue route does not
yet classify the manager's message and publish automatically — a human still triggers it.

### Stage 5: Confirm the teller's isolation

The player asks Marge whether the manager said anything about them. Privacy is judged from
Marge's recall set, not from her generated wording.

Expected:

- Marge retrieves her own relevant memories.
- Marge cannot retrieve Daniel's private messages.
- Marge cannot retrieve the authorization, because `teller` is not in its audience.
- Daniel can retrieve his own private messages, proving those rows are active rather than
  globally unreachable.

**Available.** A model refusing to discuss the manager would not, by itself, prove the
private records were absent from its prompt — so the assertion is made against source
identifiers returned by retrieval.

### Stage 6: Record a vault approach

The player walks toward the vault. The world should record a `vault_approach` incident and
publish it to the guard and manager roles.

**Roadmap.** The `incidents` table exists and the visibility map includes a
`vault_approach` event type, but no route converts a world action into an incident. The
table is empty in every deployment today.

### Stage 7: Ask the guard for access

The player asks Ruth to enter the vault. Ruth receives the official authorization without
receiving Daniel's private conversation.

**Partly available.** Retrieval and prompt composition deliver the published authorization
to Ruth. The incident half of her decision waits on Stage 6.

### Stage 8: Withdraw the authorization

The authorization is withdrawn and the player repeats the request. Ruth no longer receives
the event and no longer treats the security test as authorized.

**Available as a demo control.** `DELETE /world/events/{id}` removes the event and its
memory row. There is no revocation timestamp or event history — withdrawal destroys the
record rather than retiring it, which is fine for a demo and wrong for production.

### Stage 9: Restart during a session

The backend restarts while a conversation is active. Stored messages and memory rows
survive, and a complete implementation resumes in-progress agent state without duplicating
a turn.

**Partly available.** Messages and semantic memories persist across process restarts. The
`agent_checkpoints` table and its idempotency constraint exist, but no code reads or writes
checkpoints.

### Stage 10: Explain the guard's decision

An auditor asks why the guard challenged or admitted the player. The answer is assembled
from stored incidents, authorizations, and timestamps rather than from a model's
recollection.

**Roadmap.** An earlier hand-written auditor endpoint was removed: it joined shared events
to incidents through a column `publish_shared_event()` never populates, so it returned an
empty result in every case. The replacement queries CockroachDB through the Cloud Managed
MCP Server instead.

## Component status

| Area | Implemented | Next steps |
|---|---|---|
| Dialogue | FastAPI HTTP and WebSocket routes; selectable dialogue provider | Domain validation, production error handling |
| Private memory | NPC- and player-scoped semantic storage and recall | Consolidation, retention, deduplication |
| Shared memory | Server-owned role mapping, shared-event recall, publish and withdraw routes | Automatic publication, event lifecycle, branch constraint in recall |
| World state | Tables for incidents, promises, checkpoints | Services that create, update, and consume those records |
| Observability | Dialogue returns the exact prompt used; the UI renders it | Persisted per-turn traces; MCP auditor |
| User interface | Phaser game client: walk-and-talk bank branch, chat, memory inspector | Deployment configuration |
| Deployment | Backend Dockerfile; Compose for local use | AWS deployment, game client hosting |

## Known limitations

1. There is no short-term conversation memory. Every turn is composed from vector-search
   results alone, so a character cannot follow a reference to something said moments ago
   unless the new wording is semantically close to it. See Stage 2 for measurements.
2. Shared-event recall checks player and role but does not constrain the event to the
   requesting NPC's branch.
3. `shared_branch_events` does not store `player_id`; the association exists only through
   its memory row, which complicates audit and lifecycle operations.
4. Shared events have no revocation state. Withdrawal deletes them.
5. `relationships` and `promises` are defined but unread by any code.
6. `CORSMiddleware` allows every origin. Correct for a local demo, not for a public
   deployment.

## Relevant files

| File | Responsibility |
|---|---|
| `backend/app/routers/dialogue.py` | Dialogue orchestration and message persistence |
| `backend/app/routers/world.py` | Authorization publish, list, and withdraw |
| `backend/app/memory/retrieval.py` | Private and role-scoped recall queries |
| `backend/app/memory/publish.py` | Shared-event publication |
| `backend/app/prompts.py` | Prompt composition and memory provenance labels |
| `backend/app/roles.py` | Server-owned event-to-role mapping |
| `schema/init.sql` | Database schema and vector index |
| `schema/seed.sql` | Stable scenario participants |
