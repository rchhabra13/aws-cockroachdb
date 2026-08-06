// Resolved in the browser rather than from NEXT_PUBLIC_*, because Next inlines those at
// build time while Docker Compose supplies them at run time. Baking the value into the
// image would ship `undefined` to the client.
function baseUrl(): string {
  if (typeof window === "undefined") return "http://localhost:8000";
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

export type Npc = {
  id: string;
  name: string;
  role: string;
  branch_id: string;
};

export type MemoryHit = {
  source_type: string;
  source_id: string;
  content: string;
  similarity: number;
};

export type DialogueResponse = {
  npc_id: string;
  reply: string;
  recalled_memories: MemoryHit[];
  prompt_sent: string;
};

export type BranchEvent = {
  id: string;
  summary: string;
  visible_to_roles: string[] | string;
  created_at: string;
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  return res.json();
}

export const listNpcs = () => json<Npc[]>("/npcs");

export const listPlayers = () => json<{ id: string; name: string }[]>("/npcs/players");

export const listEvents = (playerId: string) =>
  json<BranchEvent[]>(`/world/events/${playerId}`);

export const authorize = (branchId: string, playerId: string) =>
  json<{ event_id: string }>("/world/authorize", {
    method: "POST",
    body: JSON.stringify({ branch_id: branchId, player_id: playerId }),
  });

export const withdrawEvent = (eventId: string) =>
  json<{ withdrawn: string }>(`/world/events/${eventId}`, { method: "DELETE" });

export const speak = (
  npcId: string,
  playerId: string,
  sessionId: string,
  message: string,
) =>
  json<DialogueResponse>("/dialogue", {
    method: "POST",
    body: JSON.stringify({
      npc_id: npcId,
      player_id: playerId,
      session_id: sessionId,
      message,
    }),
  });
