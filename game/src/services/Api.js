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

  // Publish a manager authorization the guard can later recall. Used by the demo control.
  authorize(summary) {
    return this.post("/world/authorize", { branch_id: BRANCH_ID, player_id: PLAYER_ID, summary });
  }
}

export default new Api();
