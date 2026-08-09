import { API_URL, BRANCH_ID, PLAYER_ID, SESSION_ID } from "../config";

// Thin wrapper over the OmniNPC backend. Only the routes the game needs.
class Api {
  async get(path) {
    const res = await fetch(`${API_URL}${path}`);
    if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
    return res.json();
  }

  async post(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
    return res.json();
  }

  async del(path) {
    const res = await fetch(`${API_URL}${path}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE ${path} -> ${res.status}`);
    return res.json();
  }

  listNpcs() {
    return this.get("/npcs");
  }

  // Returns { reply, recalled_memories: [{source_type, content, similarity}], prompt_sent }.
  dialogue(npcId, message) {
    return this.post("/dialogue", {
      npc_id: npcId,
      player_id: PLAYER_ID,
      session_id: SESSION_ID,
      message,
    });
  }

  // Publish a manager authorization the guard can later recall. Scoped to this session so a
  // guard in another session does not inherit it. Used by the demo control.
  authorize(summary) {
    return this.post("/world/authorize", {
      branch_id: BRANCH_ID,
      player_id: PLAYER_ID,
      session_id: SESSION_ID,
      summary,
    });
  }

  // Wipe all memory/events, keep the branch/npc/player fixtures. Used by the reset button.
  resetWorld() {
    return this.del("/world/reset");
  }

  // Tear down this play session's collection. Called on tab close via keepalive so the
  // request still goes out while the page is unloading; a normal fetch would be cancelled.
  endSession() {
    return fetch(`${API_URL}/world/session/${SESSION_ID}`, {
      method: "DELETE",
      keepalive: true,
    });
  }
}

export default new Api();
