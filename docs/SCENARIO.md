# The bank branch scenario

This document describes the demo, explains what each part of it is meant to prove, and
records honestly how much of it is actually built.

Status was checked against the live database on 5 August 2026.

## The idea

A bank branch has four staff members. A player walks in and talks to them.

The interesting part is not that the characters remember the player. It is that they
remember *different things*, and cannot see each other's memories. If the player tells
the manager something in private, the teller must not know it. If a security clearance is
issued, the guard must know it even though nobody told the guard directly.

That is the whole project. Everything else is machinery to make it true.

## The characters

| Name | Role | What they can see |
|---|---|---|
| Marge | teller | Her own conversations, plus branch announcements sent to tellers |
| Daniel Okafor | manager | His own conversations including private ones, plus announcements sent to managers |
| Ruth Alvarez | guard | Her own conversations, plus announcements sent to guards |
| Sam | customer | Only his own conversations. Not built yet |

## How memory is stored

There are two kinds of memory, and the difference between them is what makes the demo
work.

A **private memory** belongs to one character. It is a row in `memory_embeddings` with
that character's id on it. When a character searches its memory, the query only returns
rows carrying its own id, so one character's memories are structurally unreachable by
another. Private memories are also filtered by relevance, so a character does not dredge
up unrelated small talk.

A **branch announcement** belongs to nobody. It is a row in `shared_branch_events` with a
list of the roles allowed to see it, paired with a memory row that has no owner. Any
character whose role is on that list retrieves it. Announcements are deliberately not
filtered by relevance, because a guard should be told about an active security clearance
no matter how the question was phrased.

The important consequence: a character can only be told what its query returns. If a
private memory is never returned, it never reaches the prompt, and the model cannot
mention something it was never given.

The code is in `app/memory/retrieval.py` and `app/memory/publish.py`.

## What happens in the demo

### 1. The player asks the teller about the vault

Marge answers normally. Both her reply and the player's question are saved as her private
memories.

**Built and working.**

### 2. The player mentions it again, using different words

The player says "that secure storage room" without ever saying "vault". Marge still knows
what they mean, because memories are searched by meaning rather than by matching words.

**Built and working.** The earlier conversation was retrieved with similarity scores of
0.52 and 0.43.

### 3. The player privately tells the manager about an authorized security test

This step writes two separate things, and the separation is the point.

The conversation itself is saved as Daniel's private memory. Nobody else will ever
retrieve it. Separately, the *fact* that a clearance now exists is published as a branch
announcement addressed to guards and managers.

If only the conversation were saved, Ruth would have no way of learning about the
clearance, and step 6 would fail. If only the announcement were saved, the private
conversation would not be private.

**Partly built.** Both writes work correctly. What is missing is recognition: right now
the announcement is published by an explicit function call, rather than the system reading
the player's sentence and understanding that a clearance was granted.

### 4. The player asks the teller what the manager said

Marge should genuinely not know. Not refuse to answer, not deflect. The private
conversation is never returned by her query, so it never appears in her prompt, so there
is nothing for her to reveal.

**Built and working.** See [Verification](#verification) below.

### 5. The player walks toward the vault

This is not a conversation. It is something the player does, which the world reacts to by
recording an incident and announcing it to guards and managers. Marge, whose role is not
on the list, is not told.

**Not built.** Nothing in the code creates incidents yet.

### 6. The player asks the guard for access to the vault

Ruth now has two announcements available to her: that someone approached the vault, and
that a clearance was issued. She has neither of Daniel's private messages. Knowing about
the clearance, she lets the player through instead of treating them as an intruder.

**Partly built.** The clearance half works and is verified below. The incident from step 5
does not exist, so Ruth currently reacts to a clearance on its own rather than weighing a
clearance against an alert.

### 7. The backend is restarted in the middle of the conversation

Everything should carry on as though nothing happened, because none of the memory lives
in the running process.

**Not built.** The `agent_checkpoints` table exists and has the right unique constraint,
but no code writes to it. Messages and memories would survive a restart today because
they are already saved to the database. In-progress conversation state would not.

### 8. Someone asks why the guard let the player through

An auditor endpoint answers from the stored records rather than from the model's
recollection, listing the incident and the clearance in the order they happened.

**Not working in practice.** The endpoint exists, but it has never returned data, and it
uses an inner join to the incidents table. A clearance comes from a conversation and has
no incident attached, so that join silently discards it.

## Verification

A script at `scripts/mini_scenario.py` runs steps 1, 3, 4 and 6 against the real database
and checks the results automatically. It exists so the memory rules could be proven before
the rest of the demo was built.

```bash
docker compose up -d backend
psql "$COCKROACHDB_URL" -f schema/seed.sql
backend/.venv/bin/python scripts/mini_scenario.py
```

It checks three things:

**The teller cannot reach the manager's private conversation.** To make sure this is not
passing simply because the search is broken and returns nothing, two controls run
alongside it. Marge must successfully retrieve her own memories when asked about them, and
Daniel must retrieve his own using the very same query that Marge is denied. Together they
show that the rows are retrievable in principle and that Marge specifically is being
excluded.

**The guard can reach the clearance, but not the conversation that produced it.**

**Withdrawing the clearance removes it from what the guard can reach.** The script asks
Ruth for vault access, deletes the clearance, and asks the identical question again.

The two answers it gets:

> With the clearance in place: "I have been informed by the branch manager that you are
> authorized to conduct a security test."

> After it is deleted: "I do not have authorization to grant access to the vault. State
> your credentials."

Nothing about the question changed, and the model was given no new instructions. The only
difference is that one row had been deleted from the database, so Ruth's search no longer
returned the clearance, so her prompt no longer mentioned it. That is the memory system
visibly deciding what a character knows.

The script deletes its own leftover data before each run, so it can be run repeatedly. It
only touches the test player's rows.

## Four things that went wrong

Recorded because each was a real mistake, and each would be easy to repeat.

**A test that can only pass.** The first version of the teller check passed while Marge
retrieved nothing whatsoever, which is exactly what a completely broken search would also
produce. Negative assertions need positive controls next to them, which is why the two
described above exist.

**Retrieving a memory is not the same as acting on it.** Ruth once had the clearance in
her prompt and ignored it completely, still demanding credentials. Every memory was being
listed as an identical bullet point, so a manager's clearance looked no more important
than a remark about the weather. Splitting the prompt into "what you personally remember"
and "announcements issued to your role", which is what `app/prompts.py` now does, is what
made her act on it. Deciding what a character *can* know is access control; deciding what
it *pays attention to* is presentation, and both have to be right.

**A measurement that changed what it measured.** Ruth kept granting access after the
clearance was deleted, because her own earlier reply granting it had itself been saved as
a private memory, which she then retrieved. The script now undoes the memories a test
question creates.

**Relevance filtering cannot apply to announcements.** Measured with the current embedding
model, a genuinely related question scores between 0.40 and 0.65 against the conversation
it refers to, and an unrelated one scores below 0.10, so private memories are filtered at
0.25. But the clearance scores only 0.290 against "I need to check the vault", low enough
that any filter strict enough to remove noise would also throw the clearance away. So
announcements are never filtered by relevance, only by entitlement. These numbers belong to
this specific embedding model and must be measured again if it is replaced.

## Known bugs

1. **A new conversation row is created on every single request.** `dialogue.py` relies on
   `ON CONFLICT DO NOTHING`, but the `conversations` table has no unique constraint for
   the clause to detect a conflict against, so it never triggers.
2. **The fallback conversation id is wrong.** When that insert returns nothing,
   `dialogue.py` substitutes the session id into a column that points at
   `conversations.id`. Unreachable while bug 1 exists, and corrupting the moment it is
   fixed.
3. **`shared_branch_events` has no `player_id` column,** so the auditor has no way to
   filter announcements by player.
4. **The memory inspector does not inspect anything.** It returns the twenty most recent
   memories instead of the ones actually used in a turn, reports every similarity as 1.0,
   and returns placeholder text where the prompt should be.

## What to build next

1. Fix bugs 1 and 2, and add `player_id` to `shared_branch_events`.
2. Recognise clearances in what the player actually says, checked against each
   character's permission to issue them, so that the same sentence said to Marge publishes
   nothing at all.
3. Create incidents from world actions, which completes steps 5 and 6.
4. Save what was retrieved and what prompt was built for each turn, and rewrite the
   inspector to read it.
5. Write conversation checkpoints, which completes step 7.
