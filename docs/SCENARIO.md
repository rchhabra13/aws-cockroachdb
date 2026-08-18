# Bank Branch Scenario

This document describes the implemented demo flow and records the parts that remain incomplete.

## Objective

The demo separates a manager's private conversation from an official authorization derived from it. A teller should retrieve neither record. A guard should retrieve the authorization but not the manager's transcript.

## Participants

| Participant | Role | Retrieved records |
|---|---|---|
| Player One | Player | Fixed demo identity |
| Marge | Teller | Private conversations and teller-visible events |
| Omar Reed | Teller | Private conversations and teller-visible events |
| Daniel Okafor | Manager | Private conversations and manager-visible events |
| Priya Shah | Loan officer | Private conversations and loan-officer-visible events |
| Ruth Alvarez | Guard | Private conversations and guard-visible events |
| Grace Okonkwo | Compliance | Private conversations and compliance-visible events |
| Victor Cross | Advisor | Private conversations and advisor-visible events |

All participants have stable identifiers in `schema/seed.sql`. Marge and Omar share a role, which permits same-role NPC isolation checks.

## Memory Model

Private message memories include `npc_id`, `player_id`, and `session_id`. The retrieval query applies those predicates before ranking by vector similarity. It returns at most eight private results with a similarity of at least `0.25`.

The game stores a browser-specific player identity and registers it in CockroachDB. It creates an ephemeral session by default. When **Remember me** is enabled, it also stores the session identifier and does not delete that session on page teardown. Later visits reuse the identifier and can recall the same rows.

The six most recent messages for the same NPC, player, and session are also supplied as conversation history. This fixed window handles references such as “what did I just ask?” that do not contain enough topic information for semantic retrieval.

A shared event has a row in `shared_branch_events` and a `memory_embeddings` row with `source_type = 'shared_event'`. The server maps its event type to an audience in `backend/app/roles.py`. Shared recall filters by player, session, and the requesting NPC's role. Shared results are ranked by similarity but do not use the private-memory similarity floor.

The system prompt labels private memories and official branch bulletins separately. The API returns that prompt in `prompt_sent`, and the client displays it in the memory inspector.

## Walkthrough

### 1. Teller conversation

Ask Marge about an account balance. The API retrieves Marge's relevant memories, generates a reply, and stores both messages for the current player and session.

Status: implemented.

### 2. Short-term and semantic recall

Ask a paraphrased balance question to exercise vector recall. Ask “what did I just ask?” to exercise the six-message conversation window.

Status: implemented.

The `0.25` similarity floor was selected from measurements recorded in `backend/app/memory/retrieval.py`. Those measurements are specific to Titan Text Embeddings V2 at 1024 dimensions.

### 3. Private manager conversation

Tell Daniel that the player is conducting an authorized security test. The exchange is stored under Daniel's NPC identifier.

Status: implemented.

### 4. Publish an authorization

Call `POST /world/authorize` with the branch, player, and optional session identifiers. The route publishes a fixed summary to the `guard` and `manager` roles.

Status: implemented as an operator action. Dialogue does not classify or publish an authorization automatically.

### 5. Check teller isolation

Ask Marge about the manager conversation. Validate the returned source identifiers:

- Marge can retrieve her own matching memories.
- Marge cannot retrieve Daniel's private messages.
- Marge cannot retrieve the authorization.
- Daniel can retrieve his own matching messages.

Status: implemented and covered by `scripts/verify.py`.

### 6. Ask the guard for access

Ask Ruth to enter the vault after publishing the authorization. Her recall includes the shared event but excludes Daniel's private messages.

Status: implemented and covered by `scripts/verify.py`.

Recording a `vault_approach` incident from player movement is not implemented. The schema and role mapping exist, but no route creates the incident.

### 7. Withdraw the authorization

Call `DELETE /world/events/{event_id}` and repeat the guard request. The event and its embedding row are deleted.

Status: implemented. Events have no revocation timestamp or retained history.

### 8. Restart the backend

Messages and memory rows persist in CockroachDB across process restarts. `agent_checkpoints` and its idempotency constraint exist in the schema, but application code does not read or write checkpoints.

Status: message and memory persistence only.

### 9. Publish a structuring event automatically

Run **Smurfing the Deposit**. The teller conversation accumulates multiple cash-deposit amounts below $10,000 and reporting-avoidance language. After the policy matches, the API publishes one `structuring` event for the player and session. The scenario then moves to Grace, whose compliance role can retrieve the event.

The detector is a deterministic policy in `backend/app/policies.py`; it does not ask the dialogue model to classify the conversation. The event key prevents duplicate publications for the same player and session.

Status: implemented and covered by unit tests and `scripts/verify.py`.

## Reset and Session Cleanup

`DELETE /world/reset` deletes interaction and memory data while retaining branches, NPCs, and players. It uses `DELETE FROM` because repeated CockroachDB `TRUNCATE` operations create schema-change jobs.

`DELETE /world/session/{session_id}` deletes records for one browser session. The client sends this request with `keepalive` on `pagehide` only when **Remember me** is disabled. `POST /world/session/sweep` removes conversations with no messages.

When `ADMIN_API_KEY` is set, `/world/authorize`, event withdrawal, `/world/reset`, and `/world/session/sweep` require the `X-Admin-Key` header. The game client does not send this header, so its reset control and authorization helper work only while the key is empty.

## Scripted Client Scenarios

| Scenario | Character | Implemented behavior |
|---|---|---|
| Persuasion Attack | Daniel | Accumulating private recall |
| Smurfing the Deposit | Marge, then Grace | Automatic role-scoped structuring event |
| Inconsistent Applicant | Priya | Semantic recall of an earlier income statement |
| Privacy Probe | Daniel, then Marge | Cross-character query isolation |
| Phantom Promise | Marge | Per-session isolation |
| Reckless Windfall | Victor | Semantic recall of stated risk tolerance |

## Known Limitations

1. Shared-event recall does not constrain events to the requesting NPC's branch.
2. `shared_branch_events` has no `player_id`; the association exists through the matching memory row.
3. Shared-event withdrawal deletes records instead of retaining a revocation history.
4. `relationships`, `promises`, `incidents`, and `agent_checkpoints` are not used by application services.
5. `CORSMiddleware` allows all origins.
6. The short-term history is a fixed six-message window with no summarization.
7. Automatic publication covers only the deterministic structuring policy. Other event types still require explicit application code or the authorization operator route.
8. Persistent identity is stored in browser `localStorage`; there is no login or server-issued identity.
9. `.mcp.json` contains a CockroachDB Cloud MCP configuration, but no repository code uses it.
