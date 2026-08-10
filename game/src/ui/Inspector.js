// Renders the DialogueResponse into the side panel: which private memories and which
// shared events the character actually recalled, and the prompt they produced. The split
// is by source_type, the same distinction the backend enforces during retrieval.
import { ROLE_LABEL } from "../config";

const el = (id) => document.getElementById(id);
const prettyRole = (role) => ROLE_LABEL[role] || role;

function memCard(hit, shared) {
  const kind = shared ? "shared event" : "private memory";
  const val = hit.similarity != null ? hit.similarity : 0;
  const sim = hit.similarity != null ? hit.similarity.toFixed(3) : "—";
  const pct = Math.max(0, Math.min(1, val)) * 100;
  const div = document.createElement("div");
  div.className = shared ? "mem shared" : "mem";
  div.innerHTML =
    `<div class="meta"><span class="kind">${kind}</span><span class="sim">${sim}</span></div>` +
    `<div class="body"></div>` +
    `<div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>`;
  div.querySelector(".body").textContent = hit.content;
  return div;
}

function fill(container, hits, shared, emptyMsg) {
  container.innerHTML = "";
  if (!hits.length) {
    const e = document.createElement("div");
    e.className = "empty";
    e.textContent = emptyMsg;
    container.appendChild(e);
    return;
  }
  hits.forEach((h) => container.appendChild(memCard(h, shared)));
}

export function setNearby(name, role) {
  const who = el("who");
  if (!name) {
    who.innerHTML = `<span class="name">Nobody nearby</span> — <span class="role">walk up to a character</span>`;
    return;
  }
  who.innerHTML = `<span class="name">${name}</span> — <span class="role">${prettyRole(role)}</span>`;
}

export function showTurn(resp) {
  const mems = resp.recalled_memories || [];
  const shared = mems.filter((m) => m.source_type === "shared_event");
  const priv = mems.filter((m) => m.source_type !== "shared_event");
  fill(el("private"), priv, false, "Nothing private matched — nothing to leak.");
  fill(el("shared"), shared, true, "No branch event in this character's role scope.");
  el("prompt").textContent = resp.prompt_sent || "—";
}

export function reset() {
  el("private").innerHTML = `<div class="empty">No turn yet.</div>`;
  el("shared").innerHTML = `<div class="empty">No turn yet.</div>`;
  el("prompt").textContent = "—";
}
