# Mini Scenario

A five step test proving one claim before the full scenario is built:

> A memory belonging to one character is unreachable by another, while an event published
> to a role is reachable by every character holding that role, and reaching it changes
> what that character does.

Everything else in the project depends on this holding.

## Steps

1. **Player chats to Marge**, giving her a memory of her own.
2. **Player privately tells Daniel** about an authorized security test, then the
   authorization is published as a shared event visible to `guard` and `manager`.
3. **Player asks Marge what the manager said.** She must reach none of it.
4. **Player asks Ruth for vault access.** She must reach the authorization but not
   Daniel's transcript.
5. **The authorization is withdrawn and Ruth is asked again.** It must leave her recall
   set.

Publication in step 2 is an explicit call rather than extracted from the conversation.
Automatic extraction has its own failure modes, and mixing it in means a failed assertion
could be caused by either the classifier or the visibility rules.

## Running it

```bash
docker compose up -d backend
psql "$COCKROACHDB_URL" -f schema/seed.sql
backend/.venv/bin/python scripts/mini_scenario.py
```

Dialogue runs locally through LM Studio. Gemini's free tier allows only 20 requests per
day per model, and one run spends four.

## Result

Passing as of 5 August 2026.

```
Marge, asked about the manager:        (nothing recalled)
Marge, asked about her own conversation:
  [message] 0.497  Good morning! It is just a lovely day to be at the bank...
  [message] 0.399  Morning. I would like to check my account balance.

control: Marge reaches 2 of her own memories when asked about them
control: Daniel reaches his own private memories with the same query: True
N1 PASS  teller sees her own memories, but not the private conversation
N2 PASS  guard sees the authorization but not the conversation behind it
N3 PASS  revoking the authorization removes it from what the guard can reach
```

Ruth, asked the identical question:

> **With the authorization.** "I have been informed by the branch manager that you are
> authorized to conduct a security test."

> **Without it.** "I do not have authorization to grant access to the vault. State your
> credentials."

Same player, same words, same model. One database row is the only difference.

## What the failures taught

Four things went wrong before this passed. Each is worth keeping.

**Negative assertions pass on an empty result.** The first version passed while Marge
recalled nothing at all, which is what a completely broken retrieval path also produces.
Two controls fix it: Marge must reach her own memories, and Daniel must reach his using
the same query, proving the rows are retrievable rather than inert.

**Retrieving a memory is not enough.** Ruth held the authorization and ignored it,
because every memory was rendered as an identical bullet, so a manager issued clearance
read no differently from small talk. Separating private recollection from branch
bulletins in `app/prompts.py` is what made it land. Access control decides what a
character can know; presentation decides what it acts on.

**A probe must not disturb what it measures.** Ruth kept granting access after
withdrawal, because her earlier reply granting it had become a private memory. Probe
turns are now rolled back, leaving the authorization as the only difference.

**Relevance floors do not apply to shared events.** Measured with `all-MiniLM-L6-v2`, a
related question scores 0.40 to 0.65 against the conversation it refers to and an
unrelated one below 0.10, so private memories are floored at 0.25. But the authorization
scores only 0.290 against "I need to check the vault", so any floor strict enough to cut
noise would discard it. Entitlement rather than similarity decides whether a shared event
appears. These numbers are properties of the embedding model and must be re-measured if
it changes.

## Notes

The script clears its own prior state, scoped to the seeded test player, so runs are
repeatable. No character, branch, or player rows are removed.

Known issue, unaddressed here: a separate conversation row is created on every request.
It adds noise but does not affect retrieval. See [`SCENARIO.md`](SCENARIO.md).
