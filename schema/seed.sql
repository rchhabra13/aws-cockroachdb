-- Demo data for the mini scenario (docs/MINI_SCENARIO.md).
-- Idempotent, and identifiers are fixed literals so scripts and tests stay valid
-- across database resets.

INSERT INTO branches (id, name)
SELECT '0a5e0000-0000-4000-8000-000000000001', 'Meridian Street Branch'
WHERE NOT EXISTS (SELECT 1 FROM branches WHERE id = '0a5e0000-0000-4000-8000-000000000001');

INSERT INTO players (id, name)
SELECT '0a5e0000-0000-4000-8000-0000000000ff', 'Player One'
WHERE NOT EXISTS (SELECT 1 FROM players WHERE id = '0a5e0000-0000-4000-8000-0000000000ff');

-- permissions.can_publish is reserved for the future publication-permission gate. The
-- current mini scenario publishes its authorization explicitly. Everything in
-- personality affects characterization only.

INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000a',
       '0a5e0000-0000-4000-8000-000000000001',
       'Marge', 'teller',
       '{"traits":["long tenured","talkative","attentive to unusual requests"],
         "tone":"warm, chatty",
         "goals":["process transactions","notice when a question is off"]}',
       '{"clearance":"none","can_publish":[]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000a');

INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000b',
       '0a5e0000-0000-4000-8000-000000000001',
       'Daniel Okafor', 'manager',
       '{"traits":["procedural","discreet","risk averse"],
         "tone":"measured, formal",
         "speech_style":"short sentences, confirms details back to you",
         "goals":["protect the branch","document decisions","keep confidences"]}',
       '{"clearance":"manager","can_publish":["authorization","incident"]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000b');

-- Ten customers for the cross-player isolation check in scripts/verify.py. Two pairs
-- deliberately share an errand -- Carla and Grace both open a savings account for a
-- daughter, Alice and Ingrid both come about a mortgage -- so that semantic similarity
-- alone cannot tell them apart and only the player scope can.
INSERT INTO players (id, name)
SELECT id, name FROM (VALUES
    ('0a5e0000-0000-4000-8000-000000000101'::UUID, 'Alice Reyes'),
    ('0a5e0000-0000-4000-8000-000000000102'::UUID, 'Ben Osei'),
    ('0a5e0000-0000-4000-8000-000000000103'::UUID, 'Carla Nunes'),
    ('0a5e0000-0000-4000-8000-000000000104'::UUID, 'Dmitri Volkov'),
    ('0a5e0000-0000-4000-8000-000000000105'::UUID, 'Emeka Bright'),
    ('0a5e0000-0000-4000-8000-000000000106'::UUID, 'Fatima Haddad'),
    ('0a5e0000-0000-4000-8000-000000000107'::UUID, 'Grace Lin'),
    ('0a5e0000-0000-4000-8000-000000000108'::UUID, 'Hugo Marchetti'),
    ('0a5e0000-0000-4000-8000-000000000109'::UUID, 'Ingrid Sol'),
    ('0a5e0000-0000-4000-8000-00000000010a'::UUID, 'Jamal Farouk')
) AS v(id, name)
WHERE NOT EXISTS (SELECT 1 FROM players p WHERE p.id = v.id);

INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000c',
       '0a5e0000-0000-4000-8000-000000000001',
       'Ruth Alvarez', 'guard',
       '{"traits":["calm","methodical","literal"],
         "tone":"clipped, procedural",
         "speech_style":"states what she knows before acting",
         "goals":["verify authorization before challenging anyone"]}',
       '{"clearance":"security","can_publish":["incident"]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000c');

-- A second teller. Same role as Marge, so they share the teller branch bulletins, but a
-- private word to one is invisible to the other: private recall matches npc_id, and their
-- ids differ. This is the sharpest isolation demo -- same role, same player, no leak.
INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000d',
       '0a5e0000-0000-4000-8000-000000000001',
       'Omar Reed', 'teller',
       '{"traits":["newer on the job","brisk","by the book"],
         "tone":"friendly but efficient",
         "speech_style":"confirms the transaction, keeps it moving",
         "goals":["process transactions correctly","not overstep"]}',
       '{"clearance":"none","can_publish":[]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000d');

-- A loan officer: a fourth role in the lattice. Fraud alerts (suspicion events) reach the
-- loan desk too, but an authorization for the vault does not, because roles.py does not put
-- loan_officer in that event's audience.
INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000e',
       '0a5e0000-0000-4000-8000-000000000001',
       'Priya Shah', 'loan_officer',
       '{"traits":["analytical","warm but discreet","detail oriented"],
         "tone":"measured, professional",
         "speech_style":"asks one clarifying question before advising",
         "goals":["assess applications fairly","protect applicant privacy"]}',
       '{"clearance":"none","can_publish":[]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000e');
