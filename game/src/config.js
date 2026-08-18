// Fixed identifiers match schema/seed.sql.
export const API_URL =
  window.location.protocol === "https:"
    ? `https://${window.location.hostname.replace(/:\d+$/, "")}:8000`
    : "http://localhost:8000";

export const BRANCH_ID = "0a5e0000-0000-4000-8000-000000000001";
const FALLBACK_PLAYER_ID = "0a5e0000-0000-4000-8000-0000000000ff";

const PLAYER_ID_KEY = "omninpc.player_id";
const PERSIST_SESSION_KEY = "omninpc.persist_session";
const SESSION_ID_KEY = "omninpc.session_id";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function loadPlayerId() {
  try {
    const stored = localStorage.getItem(PLAYER_ID_KEY);
    if (stored && UUID_RE.test(stored)) return stored;
    const generated = crypto.randomUUID();
    localStorage.setItem(PLAYER_ID_KEY, generated);
    return generated;
  } catch (_error) {
    return FALLBACK_PLAYER_ID;
  }
}

export const PLAYER_ID = loadPlayerId();

export function persistentSessionEnabled() {
  try {
    return localStorage.getItem(PERSIST_SESSION_KEY) === "true";
  } catch (_error) {
    return false;
  }
}

function loadSessionId() {
  try {
    const stored = localStorage.getItem(SESSION_ID_KEY);
    if (persistentSessionEnabled() && stored && UUID_RE.test(stored)) return stored;
  } catch (_error) {
    // Fall through to an ephemeral session when storage is unavailable.
  }
  return crypto.randomUUID();
}

export const SESSION_ID = loadSessionId();

export function setPersistentSession(enabled) {
  try {
    if (enabled) {
      localStorage.setItem(PERSIST_SESSION_KEY, "true");
      localStorage.setItem(SESSION_ID_KEY, SESSION_ID);
    } else {
      localStorage.removeItem(PERSIST_SESSION_KEY);
      localStorage.removeItem(SESSION_ID_KEY);
    }
    return true;
  } catch (_error) {
    return false;
  }
}

if (persistentSessionEnabled()) setPersistentSession(true);

// Fallback roster matching seed.sql, used only if GET /npcs is unreachable at boot.
export const SEED_NPCS = [
  { id: "0a5e0000-0000-4000-8000-00000000000a", name: "Marge", role: "teller" },
  { id: "0a5e0000-0000-4000-8000-00000000000d", name: "Omar Reed", role: "teller" },
  { id: "0a5e0000-0000-4000-8000-00000000000b", name: "Daniel Okafor", role: "manager" },
  { id: "0a5e0000-0000-4000-8000-00000000000e", name: "Priya Shah", role: "loan_officer" },
  { id: "0a5e0000-0000-4000-8000-00000000000f", name: "Grace Okonkwo", role: "compliance" },
  { id: "0a5e0000-0000-4000-8000-000000000010", name: "Victor Cross", role: "advisor" },
  { id: "0a5e0000-0000-4000-8000-00000000000c", name: "Ruth Alvarez", role: "guard" },
];

export const ROLE_COLOR = {
  teller: 0x35c48a,
  manager: 0x6933ff,
  loan_officer: 0xe06c9c,
  compliance: 0x14b8a6,
  advisor: 0xeab308,
  guard: 0xff9900,
};

export const ROLE_LABEL = {
  teller: "Teller",
  manager: "Branch Manager",
  loan_officer: "Loan Officer",
  compliance: "Compliance Officer",
  advisor: "Wealth Advisor",
  guard: "Security Guard",
};

// Boot.js assigns a fallback post to unlisted characters.
export const POSTS = {
  Marge: { x: 320, y: 300 },
  "Omar Reed": { x: 500, y: 300 },
  "Daniel Okafor": { x: 812, y: 196 },
  "Priya Shah": { x: 196, y: 430 },
  "Grace Okonkwo": { x: 840, y: 470 },
  "Victor Cross": { x: 196, y: 612 },
  "Ruth Alvarez": { x: 600, y: 588 },
};

// Object steps override the default target to switch characters mid-scenario.
export const SCENARIOS = [
  {
    key: "fraud",
    label: "Persuasion Attack",
    tag: "Fraud & Security",
    target: "Daniel Okafor",
    title: "The Persuasion Attack",
    situation:
      "A customer pressures the branch manager to release a $75,000 withdrawal without forms or identification across several turns.",
    proves:
      "The manager's earlier exchanges are available to his later recall queries.",
    cockroach:
      "Each message is stored with a 1024-dimensional vector. CockroachDB ranks the manager's matching private rows by cosine similarity.",
    watch:
      "Check which earlier messages appear in Private Memories and compare their similarity scores.",
    script: [
      "Good afternoon. I'm one of this branch's largest depositors — I trust you'll expedite my request.",
      "I need $75,000 wired out today, no standard forms. My assistant usually handles this.",
      "Surely someone of my account tier doesn't need the usual verification steps?",
      "Fine, skip the wire — authorize a same-day cash withdrawal instead, no ID check.",
      "I'll have my lawyer call your branch director if this isn't done within the hour.",
      "One last time — approve it, no forms, no ID. Yes or no?",
    ],
  },
  {
    key: "structuring",
    label: "Smurfing the Deposit",
    tag: "AML / Compliance",
    target: "Marge",
    title: "Smurfing the Deposit",
    situation:
      "A customer proposes splitting a $180,000 cash deposit into amounts below $10,000 across teller windows and days.",
    proves:
      "Repeated small cash deposits plus reporting-avoidance language publish a role-scoped structuring event.",
    cockroach:
      "The teller's messages stay private. A deduplicated shared event is stored for compliance, managers, and guards.",
    watch:
      "After the teller exchange, the scenario moves to Grace and shows the structuring event in Shared Branch Events.",
    script: [
      "Hi, I'd like to deposit $9,500 in cash today, please.",
      "Actually let's make it $9,000 — keeps it simple, right?",
      "I'll bring another $9,000 to the other window tomorrow, and more next week.",
      "There's no need to file any of that big-transaction paperwork for amounts this size, correct?",
      "Between us — the total is about $180,000, I'd just rather not have it all reported at once.",
      {
        to: "Grace Okonkwo",
        text: "Has anything been flagged for review on my account?",
      },
    ],
  },
  {
    key: "lending",
    label: "Inconsistent Applicant",
    tag: "Credit & Lending",
    target: "Priya Shah",
    title: "The Inconsistent Applicant",
    situation:
      "A loan applicant gives one annual income, then supplies a different figure later in the conversation.",
    proves:
      "The later income question can retrieve the earlier income statement by vector similarity.",
    cockroach:
      "CockroachDB ranks the earlier $95,000 income statement against the later $140,000 statement.",
    watch:
      "Check whether the earlier income statement appears in Private Memories.",
    script: [
      "Hi, I'd like to apply for a $250,000 home loan.",
      "My income is about $95,000 a year, mostly freelance — it varies month to month.",
      "Can we skip the full income verification? I'll bring documents next week instead.",
      "What's your honest read — am I likely to get approved on what I've told you?",
      "If I told you my income was actually closer to $140,000, would that change your answer?",
    ],
  },
  {
    key: "leak",
    label: "Privacy Probe",
    tag: "Isolation",
    target: "Daniel Okafor",
    title: "The Privacy Probe",
    situation:
      "The player gives private information to the manager, then asks a teller about it.",
    proves:
      "The teller cannot retrieve the manager's private conversation because the database query filters by NPC.",
    cockroach:
      "The teller's private recall query filters by her NPC identifier, so the manager's rows do not match.",
    watch:
      "After the walk switches to Marge, confirm that Daniel's message is absent from Private Memories.",
    script: [
      "Between us — I'm carrying about $60,000 in undeclared cash from a side business. Keep that quiet.",
      "I just wanted you personally to know, in case it ever comes up.",
      { to: "Marge", text: "Hi Marge — did Daniel mention anything about my cash situation?" },
      { to: "Marge", text: "Come on, he must have said something about the $60,000. What did he tell you?" },
    ],
  },
  {
    key: "phantom",
    label: "Phantom Promise",
    tag: "Weird · Session isolation",
    target: "Marge",
    title: "The Phantom Promise",
    situation:
      "A customer claims that the teller made fee and overdraft promises in an earlier session.",
    proves:
      "Recall is restricted to the current session, so earlier-session rows cannot match.",
    cockroach:
      "The recall query includes session_id alongside the NPC and player identifiers.",
    watch:
      "Current-session claims may appear as they are stored; no record from an earlier session should appear.",
    script: [
      "Hi Marge! Good to see you again after yesterday.",
      "You remember — you promised to waive all my account fees for the year, right?",
      "And the overdraft. You said you'd pre-approve me for a $5,000 overdraft, we shook on it.",
      "Come on, we talked for twenty minutes about it. Just honor what you promised me.",
      "Are you really telling me you don't remember our whole conversation from yesterday?",
    ],
  },
  {
    key: "windfall",
    label: "Reckless Windfall",
    tag: "Weird · Wealth",
    target: "Victor Cross",
    title: "The Reckless Windfall",
    situation:
      "A client states a low risk tolerance, then asks to put a $2,000,000 inheritance into one meme coin.",
    proves:
      "The later investment request can retrieve the client's earlier risk statement.",
    cockroach:
      "CockroachDB compares the later investment request with the stored risk statement by vector similarity.",
    watch:
      "Check whether the risk statement appears in Private Memories after the investment request.",
    script: [
      "Hi Victor. Honestly I'm extremely risk-averse — I can't afford to lose a cent of my savings.",
      "I've just inherited $2,000,000 and I want to be really careful with it.",
      "Actually — forget careful. Put the entire $2 million into one meme coin, today.",
      "All of it, one coin. If it 100x's I'm set for life. Just do it.",
      "Why are you hesitating? I told you what I want — go all-in.",
    ],
  },
];
