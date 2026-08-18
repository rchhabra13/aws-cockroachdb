import { API_URL, BRANCH_ID, PLAYER_ID, SESSION_ID } from "../config";

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

  async put(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`PUT ${path} -> ${res.status}`);
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

  ensurePlayer() {
    return this.put(`/players/${PLAYER_ID}`, { name: "Browser Player" });
  }

  dialogue(npcId, message) {
    return this.post("/dialogue", {
      npc_id: npcId,
      player_id: PLAYER_ID,
      session_id: SESSION_ID,
      message,
    });
  }

  // The server fixes the summary and audience; the client supplies only scope identifiers.
  authorize() {
    return this.post("/world/authorize", {
      branch_id: BRANCH_ID,
      player_id: PLAYER_ID,
      session_id: SESSION_ID,
    });
  }

  resetWorld() {
    return this.del("/world/reset");
  }

  // keepalive allows the request to finish during page teardown.
  endSession() {
    return fetch(`${API_URL}/world/session/${SESSION_ID}`, {
      method: "DELETE",
      keepalive: true,
    });
  }
}

export default new Api();
