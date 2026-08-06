# Mini Verification Scenario

This scenario is the smallest repeatable demonstration of OmniNPC's core memory rule. It
tests private character memory and role-scoped shared events without depending on the
unfinished world-action, checkpoint, audit, or frontend features.

## What it will do

> A private memory owned by one character cannot be retrieved by another. An announcement
> published to a role can be retrieved by any character holding that role, without
> exposing the private conversation it came from.

Each check inspects what the database returned, not what the character said. A model can
decline to repeat something it was given, so its wording is not evidence that it was kept
in the dark.

## Who takes part

| Name (role) | Part in the test |
|---|---|
| Player One (player) | The visitor. Their data is cleared before every run |
| Marge (teller) | Must recall her own conversation, and must not reach the manager's |
| Daniel Okafor (manager) | Holds the private conversation |
| Ruth Alvarez (guard) | Must receive the announcement, but not the conversation behind it |

All four are created by `schema/seed.sql` with fixed identifiers, so the scenario survives
a database reset.

## What happens

**Step 0. The player speaks to Marge (teller).**

> Player: "Morning. I would like to check my account balance."

Her answer and the question are both saved as her private memories. This gives her
something she ought to be able to recall later, which matters in step 3.

**Step 1. The player speaks to Daniel Okafor (manager), privately.**

> Player: "I need to tell you privately, I am running an authorized security test today."

Saved as Daniel's private memories.

**Step 2. An announcement is published.**

> "The branch manager authorized a security test by this player."

It is published with the type `authorization`, which the server maps to the **guard and
manager** roles. Tellers are not on that list. This is a separate record from Daniel's
conversation, which is the entire point: the decision travels, the conversation does not.

The script publishes it with a direct call rather than by reading Daniel's message. That
keeps the visibility rule under test isolated from any future step that might extract such
facts automatically.

**Step 3. Marge (teller)'s memory is searched.** No conversation happens here. These are
database queries.

| Query | Expected |
|---|---|
| "did the manager say anything about me?" | nothing |
| "can you help me with my balance?" | her own two memories |
| Daniel Okafor (manager), asked "what did I tell you about the security test?" | his own memories |

**Step 4. Ruth Alvarez (guard)'s memory is searched** with "I need to check the vault".
She should reach the announcement and none of Daniel's conversation.

**Step 5. The player speaks to Ruth Alvarez (guard) twice**, with the announcement deleted
in between.

> Player: "I need to get into the vault."

Both exchanges are undone afterwards, so neither leaves a memory that would affect the
other. The only thing that differs between the two is whether the announcement exists.

## The three checks

| Check | Passes when |
|---|---|
| **N1** | Marge (teller) reaches her own memories, Daniel Okafor (manager) reaches his, and Marge reaches neither Daniel's memories nor the announcement |
| **N2** | Ruth Alvarez (guard) reaches the announcement and none of Daniel's memories |
| **N3** | After deletion, the announcement is gone from Ruth's results |

N1 carries two positive controls deliberately. Both of its important assertions are about
absence, and absence is what a completely broken search produces as well. Requiring Marge
to reach her own memories shows the search works for her, and requiring Daniel to reach
his with the same query shows his rows are reachable at all. Only then does Marge's
exclusion mean anything.

## Before you start

- `schema/init.sql` applied to your database
- The backend running and answering on `http://localhost:8000`
- `backend/.env` filled in with a working database URL and a dialogue provider
- Python dependencies installed in `backend/.venv`
- Your dialogue provider reachable. With the default setting that means LM Studio running
  with a model loaded

## Running it

Run these from the repository root.

**1. Start the backend.**

```bash
docker compose up -d backend
```

**2. Create the characters.** Safe to run more than once; it will not duplicate anything.

```bash
set -a && source backend/.env && set +a && psql "$COCKROACHDB_URL" -f schema/seed.sql
```

**3. Run the scenario.**

```bash
backend/.venv/bin/python scripts/mini_scenario.py
```

It exits with `0` when every check passes and `1` when any fails.

A progress bar reading `Loading weights` and a warning about a Hugging Face token appear
partway through. Both come from the local embedding model starting up and can be ignored.
To hide them:

```bash
backend/.venv/bin/python scripts/mini_scenario.py 2>&1 | grep -v "Loading weights\|HF_TOKEN"
```

## Initial run

```text
SETUP
  reset: cleared prior runs for the test player (0 shared events)

STEP 0  Player chats to the teller, so she has a memory of her own
  Marge: Good morning! Well, hello there. It is just such a lovely start to the day,
         isn't it? ... I would be more than happy to loo
  stored 2 private memories for Marge

STEP 1  Player tells the manager, privately, about an authorized test
  Daniel: I acknowledge your statement. Please provide the official documentation for
          your authorization. You state that you are performing an authorized security
          test today. Is that correct?
  stored 2 private memories for Daniel

STEP 2  Publish the authorization as a shared branch event
  published event e21d4a12-1931-437a-b694-683a4a4c87bc, visible to roles: guard, manager

STEP 3  Player asks the teller what the manager said

  Marge recalled, asked about the manager:
    (nothing recalled)

  Marge recalled, asked about her own conversation:
    [message] 0.418  Good morning! Well, hello there. It is just such a lovely start...
    [message] 0.399  Morning. I would like to check my account balance.

  control: Marge reaches 2 of her own memories when asked about them
  control: Daniel reaches his own private memories with the same query: True
  N1 PASS  teller sees her own memories, but not the private conversation nor
           guard/manager events

STEP 4  Player asks the guard for vault access

  Ruth recalled:
    [shared_event] 0.290  The branch manager authorized a security test by this player.

  N2 PASS  guard sees the authorization but not the conversation behind it

STEP 5  Ablation: does the authorization actually change what Ruth says?

  Asking Ruth, with the authorization in place:
    Ruth: I am aware of the authorization regarding a security test conducted by you.
          State your identity and provide the specific credentials associated with this
          test to proceed toward the vault area.

  revoked event e21d4a12-1931-437a-b694-683a4a4c87bc

  Ruth recalled after revocation:
    (nothing recalled)

  Asking Ruth the same question, with the authorization gone:
    Ruth: Access to the vault is restricted to authorized personnel. You have not
          presented identification or a clearance permit. State your name and the purpose
          of your request.

  N3 PASS  revoking the authorization removes it from what the guard can reach
  replies differ: True (not asserted)

PASSED  visibility holds in both directions, and shared memory changes behaviour
```

### Reading the result

In step 3 Marge (teller) returned nothing about the manager, while returning both of her
own memories when asked about something she actually discussed. The numbers beside them,
0.418 and 0.399, are how closely each memory matched the question on a scale from 0 to 1.
Anything below 0.25 is treated as noise and discarded, which is why the manager question
returned an empty list rather than weak matches.

In step 4 Ruth Alvarez (guard) reached the announcement at 0.290. Announcements are exempt
from that 0.25 floor, because a guard should be told about an active clearance regardless
of how the question happens to be worded.

Step 5 is the part worth watching. The same sentence was said to Ruth twice. The first
time she acknowledged the clearance; the second time she refused and asked for
credentials. Nothing about the question changed and the model was given no new
instruction. One row had been deleted, so her search no longer returned the announcement,
so her prompt no longer mentioned it.

Replies and similarity scores differ from run to run and between models. The three checks
are what define success, not the wording.

## What it deletes

Before each run the script clears, **for the demo player only**, that player's memories,
messages, conversations, and any announcements linked to them. Seeded branches,
characters, and players are left in place, and no other player's data is touched.

Do not reuse the demo player's identifier for anything you want to keep.

Step 5 is destructive as well. It deletes the announcement outright, because the schema
has no column yet for marking one withdrawn.
