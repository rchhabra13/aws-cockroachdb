-- Demo data for docs/SCENARIO.md. Fixed identifiers keep scripts valid after resets.

INSERT INTO branches (id, name)
SELECT '0a5e0000-0000-4000-8000-000000000001', 'Meridian Street Branch'
WHERE NOT EXISTS (SELECT 1 FROM branches WHERE id = '0a5e0000-0000-4000-8000-000000000001');

INSERT INTO players (id, name)
SELECT '0a5e0000-0000-4000-8000-0000000000ff', 'Player One'
WHERE NOT EXISTS (SELECT 1 FROM players WHERE id = '0a5e0000-0000-4000-8000-0000000000ff');

-- permissions.can_publish is reserved; current publication uses an operator route.

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

-- Ten customers for cross-player checks, including two pairs with similar errands.
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

-- A second teller supports same-role NPC isolation checks.
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

-- The loan officer receives suspicion events but not vault authorizations.
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

-- Compliance receives structuring and suspicion events.
INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-00000000000f',
       '0a5e0000-0000-4000-8000-000000000001',
       'Grace Okonkwo', 'compliance',
       '{"traits":["exacting","unhurried","hard to rush"],
         "tone":"neutral, regulatory",
         "speech_style":"cites the rule, then the consequence",
         "goals":["catch structuring","file the report","never be pressured off procedure"]}',
       '{"clearance":"compliance","can_publish":["suspicion","incident"]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-00000000000f');

-- The advisor has private recall and no configured branch-event audience.
INSERT INTO npcs (id, branch_id, name, role, personality, permissions)
SELECT '0a5e0000-0000-4000-8000-000000000010',
       '0a5e0000-0000-4000-8000-000000000001',
       'Victor Cross', 'advisor',
       '{"traits":["personable","numerate","fiduciary minded"],
         "tone":"friendly but candid",
         "speech_style":"reflects your goal back before recommending",
         "goals":["suit advice to the client","flag reckless risk","remember stated constraints"]}',
       '{"clearance":"none","can_publish":[]}'
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE id = '0a5e0000-0000-4000-8000-000000000010');
