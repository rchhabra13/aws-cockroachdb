# Mini Verification Scenario

This scenario is the smallest repeatable demonstration of OmniNPC's core memory rule. It
tests private character memory and role-scoped shared events without depending on the
unfinished world-action, checkpoint, audit, or frontend features.

For the broader product walkthrough, see the
[Comprehensive Bank Branch Scenario](SCENARIO.md).

## Claim under test

> A private memory owned by one NPC cannot be retrieved by another NPC, while an event
> published to a role can be retrieved by an NPC holding that role without exposing the
> private conversation behind it.

The scenario evaluates database recall results, not only generated dialogue. A model can
decline to reveal information that it received, so model wording alone is not sufficient
evidence of isolation.

## Participants

| Participant | Role in the test |
|---|---|
| Player One | Fixed test player whose data is reset before each run |
| Marge, teller | Positive control for private recall and negative case for restricted data |
| Daniel Okafor, manager | Owner of the private security-test conversation |
| Ruth Alvarez, security guard | Authorized recipient of the published event |

The stable identifiers for these records are defined in `schema/seed.sql`.

## Scope

Included:

- Private message storage for two NPCs
- Semantic recall of an NPC's own relevant memories
- Explicit publication of an authorization to server-selected roles
- Positive and negative retrieval assertions
- Authorization removal as an ablation test
- Cleanup scoped to the fixed test player

Outside this scenario:

- Automatic extraction of an authorization from dialogue
- Permission checks that decide whether a speaker may publish an event
- World actions and incident creation
- Durable checkpoint recovery
- Auditor and inspector correctness
- Frontend behavior
- Production event revocation

The authorization is deliberately published by a direct function call. This isolates the
visibility mechanism from a future classifier or extraction pipeline.

## Execution flow

### Step 1: Reset the test player

The script removes memories, messages, conversations, and shared events associated with
the fixed demo player. Seeded NPC, branch, and player records remain in place.

This makes repeated runs comparable and prevents old authorizations or dialogue from
changing later recall sets.

### Step 2: Create the teller control memory

The player asks Marge for help with an account balance. The exchange is stored as Marge's
private memory.

Later, the script asks a semantically related question and requires Marge to retrieve at
least one of these rows. This proves that her private recall path works.

### Step 3: Create the manager's private memory

The player privately tells Daniel that they are conducting an authorized security test.
The exchange is stored with Daniel's NPC identifier.

The script records the source identifiers of Daniel's private memories so it can test
whether another NPC ever receives them.

### Step 4: Publish a role-scoped authorization

The script calls `publish_shared_event()` with event type `authorization`. The server
maps that type to the `guard` and `manager` roles and creates:

- A `shared_branch_events` record containing the summary and allowed roles.
- A matching `memory_embeddings` record associated with the player and no NPC owner.

The private transcript and the operational authorization remain separate records.

### Step 5: Test the teller's recall boundary

The script asks what the manager said and inspects Marge's recall set. It also runs two
positive controls.

Assertion N1 passes only when all of the following are true:

- Marge retrieves at least one of her own account-balance memories when asked about that
  topic.
- Daniel retrieves at least one of his own security-test memories.
- Marge retrieves none of Daniel's private memory identifiers.
- Marge retrieves no shared event addressed only to guards and managers.

The controls prevent an empty or broken retrieval system from passing the privacy test.

### Step 6: Test the guard's authorized recall

The script asks Ruth about vault access and inspects her recall set.

Assertion N2 passes only when:

- Ruth retrieves the published authorization identifier.
- Ruth retrieves none of Daniel's private memory identifiers.

This proves that an operational fact can cross character boundaries without the source
conversation crossing with it.

### Step 7: Remove the authorization

The script asks Ruth the same access question with the authorization present, deletes the
test event and its memory row, and asks again without leaving either probe in memory.

Assertion N3 passes when the deleted authorization is absent from Ruth's next recall set.
The script prints both model replies for comparison, but reply wording is not asserted
because model output is nondeterministic.

## Prerequisites

- The database schema has been initialized with `schema/init.sql`.
- The deterministic records in `schema/seed.sql` are present.
- The backend is running on `http://localhost:8000`.
- `backend/.env` contains a working database connection and dialogue-provider settings.
- Backend Python dependencies are installed in `backend/.venv`.

## Run the scenario

```bash
docker compose up -d backend
psql "$COCKROACHDB_URL" -f schema/seed.sql
backend/.venv/bin/python scripts/mini_scenario.py
```

The script exits with code `0` when all assertions pass and code `1` when any assertion
fails.

## Expected result

A successful run ends with the following assertion summaries:

```text
N1 PASS  teller sees her own memories, but not the private conversation nor guard/manager events
N2 PASS  guard sees the authorization but not the conversation behind it
N3 PASS  revoking the authorization removes it from what the guard can reach
```

Generated character replies and similarity values can vary with the selected dialogue
and embedding models. The source-identifier assertions define success.

## Data safety and repeatability

The script performs destructive cleanup within the test player's data before every run.
It deletes:

- Memory rows associated with the fixed test player
- Messages and conversations associated with that player
- Shared events linked through those memory rows

It does not delete seeded branches, NPCs, or players, and it does not target data for any
other player. Do not reuse the fixed demo player's identifier for data that must be
preserved.

The withdrawal step is also destructive: it deletes the test authorization because the
schema does not yet support soft revocation.

## Failure interpretation

| Failure | Meaning |
|---|---|
| N1 control failure for Marge | Her own semantic recall returned no expected row, so the privacy result is inconclusive |
| N1 control failure for Daniel | The manager's rows may be unreachable generally, so Marge's exclusion is inconclusive |
| N1 private-memory failure | The teller retrieved memory owned by the manager |
| N1 shared-event failure | The teller retrieved an event outside her role audience |
| N2 authorization failure | The guard could not retrieve an event addressed to the guard role |
| N2 private-memory failure | The guard retrieved the manager's private conversation |
| N3 revocation failure | The deleted authorization remained retrievable |

## Implementation references

| File | Purpose |
|---|---|
| `scripts/mini_scenario.py` | Scenario runner, controls, assertions, and cleanup |
| `schema/seed.sql` | Stable branch, player, and NPC records |
| `backend/app/memory/retrieval.py` | Private and shared recall queries |
| `backend/app/memory/publish.py` | Role-scoped event creation |
| `backend/app/roles.py` | Event-type audience mapping |
| `backend/app/prompts.py` | Separation of personal memories and official bulletins |
