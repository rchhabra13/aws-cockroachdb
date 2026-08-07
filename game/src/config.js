// Backend + fixed identifiers from schema/seed.sql. The game talks to the same FastAPI
// backend the verification suite does; nothing here is mocked.
export const API_URL =
  window.location.protocol === "https:"
    ? `https://${window.location.hostname.replace(/:\d+$/, "")}:8000`
    : "http://localhost:8000";

export const BRANCH_ID = "0a5e0000-0000-4000-8000-000000000001";
export const PLAYER_ID = "0a5e0000-0000-4000-8000-0000000000ff"; // Player One

// One session per page load, so a turn always upserts the same conversation row.
export const SESSION_ID = crypto.randomUUID();

// Fallback roster matching seed.sql, used only if GET /npcs is unreachable at boot.
export const SEED_NPCS = [
  { id: "0a5e0000-0000-4000-8000-00000000000a", name: "Marge", role: "teller" },
  { id: "0a5e0000-0000-4000-8000-00000000000d", name: "Omar Reed", role: "teller" },
  { id: "0a5e0000-0000-4000-8000-00000000000b", name: "Daniel Okafor", role: "manager" },
  { id: "0a5e0000-0000-4000-8000-00000000000e", name: "Priya Shah", role: "loan_officer" },
  { id: "0a5e0000-0000-4000-8000-00000000000c", name: "Ruth Alvarez", role: "guard" },
];

// Sprite tint per role. Boot.js bakes one textured figure per role from these.
export const ROLE_COLOR = {
  teller: 0x35c48a,
  manager: 0x6933ff,
  loan_officer: 0xe06c9c,
  guard: 0xff9900,
};

// Where each named character stands. Positions are placed against the layout in Bank.js;
// two tellers share the counter. Anyone missing here is auto-placed along the lobby wall.
export const POSTS = {
  Marge: { x: 300, y: 300 },
  "Omar Reed": { x: 490, y: 300 },
  "Daniel Okafor": { x: 780, y: 210 },
  "Priya Shah": { x: 210, y: 440 },
  "Ruth Alvarez": { x: 620, y: 560 },
};
