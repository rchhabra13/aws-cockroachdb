-- Demo data for the mini scenario (docs/MINI_SCENARIO.md).
-- Idempotent, and identifiers are fixed literals so scripts and tests stay valid
-- across database resets.

INSERT INTO branches (id, name)
SELECT '0a5e0000-0000-4000-8000-000000000001', 'Meridian Street Branch'
WHERE NOT EXISTS (SELECT 1 FROM branches WHERE id = '0a5e0000-0000-4000-8000-000000000001');

INSERT INTO players (id, name)
SELECT '0a5e0000-0000-4000-8000-0000000000ff', 'Player One'
WHERE NOT EXISTS (SELECT 1 FROM players WHERE id = '0a5e0000-0000-4000-8000-0000000000ff');

-- permissions.can_publish gates which event types a character may publish. It is the
-- field the Phase 5 extraction gate reads. Everything in personality is flavour.

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
